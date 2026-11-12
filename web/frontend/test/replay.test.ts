// Step replay state (spec 070-07 AC-5): which events are steps, how the cursor moves, folding, cache.
import { describe, expect, it } from 'vitest';
import type { DiagramLine, DoneData, TraceEvent } from '../src/api';
import { ReplayCache, ReplayState, foldedParts, replayTracers } from '../src/replay';

function event(seq: number, tracer: number, kind: TraceEvent['kind'] = 'message'): TraceEvent {
  return { v: 1, kind, seq, tracer, file: 'a.cpp', line: seq, func: 'f', tUs: 0, from: 'A', to: 'B', action: `m${seq}` };
}

function done(tracers: Record<string, number>, max = 5000): DoneData {
  return {
    build: { ok: true, ms: 0, diagnostics: [], timedOut: false },
    run: null,
    diagrams: [],
    skippedTraceLines: 0,
    stopped: false,
    replay: { max, tracers },
  };
}

function part(diagram: DiagramLine['diagram'], k: number, n: number): DiagramLine {
  return { kind: 'diagram', tracer: 1, part: k, parts: n, diagram, backend: 'mermaid', title: 'T', overBudget: false, source: '' };
}

describe('replayTracers', () => {
  it('collects the steps of each tracer in seq order and ignores other kinds', () => {
    const events = [event(5, 1), event(2, 2), event(3, 1), { ...event(4, 1), kind: 'span' as never }];
    const got = replayTracers(done({ '1': 2, '2': 1 }), events);
    expect(got.map((t) => [t.tracer, t.steps.map((e) => e.seq), t.off])).toEqual([
      [1, [3, 5], null],
      [2, [2], null],
    ]);
  });

  it('turns a tracer off when it has more events than the server keeps', () => {
    const got = replayTracers(done({ '1': 6 }, 5), [event(1, 1)]);
    expect(got[0].off).toBe('tooMany');
    expect(got[0].steps).toEqual([]);
  });

  it('turns a tracer off when the Events tab lost some of its events', () => {
    const got = replayTracers(done({ '1': 3 }), [event(1, 1), event(2, 1)]);
    expect(got[0].off).toBe('truncated');
  });

  it('has nothing to replay without done.replay or without events', () => {
    expect(replayTracers({ ...done({}), replay: undefined }, [event(1, 1)])).toEqual([]);
    expect(replayTracers(done({ '1': 0 }), [])).toEqual([]);
  });
});

describe('ReplayState', () => {
  const state = (counts: Record<string, number> = { '1': 3, '2': 2 }) => {
    const events = [event(1, 1), event(2, 2), event(3, 1), event(4, 2), event(5, 1)];
    return new ReplayState(replayTracers(done(counts), events));
  };

  it('is off at first and has no current step', () => {
    const s = state();
    expect(s.available).toBe(true);
    expect(s.active).toBe(false);
    expect(s.current).toBeNull();
    expect(s.next()).toBe(false);
  });

  it('starts at the last step of the first tracer when switched on', () => {
    const s = state();
    s.setActive(true);
    expect(s.current).toMatchObject({ tracer: 1, index: 2, total: 3 });
    expect(s.current?.event.seq).toBe(5);
  });

  it('moves with first/prev/next/last and stops at the ends', () => {
    const s = state();
    s.setActive(true);
    expect(s.next()).toBe(false); // already at the last step
    expect(s.prev()).toBe(true);
    expect(s.current?.event.seq).toBe(3);
    expect(s.first()).toBe(true);
    expect(s.current?.event.seq).toBe(1);
    expect(s.prev()).toBe(false);
    expect(s.last()).toBe(true);
    expect(s.current?.index).toBe(2);
  });

  it('clamps setStep', () => {
    const s = state();
    s.setActive(true);
    s.setStep(-7);
    expect(s.current?.index).toBe(0);
    s.setStep(99);
    expect(s.current?.index).toBe(2);
  });

  it('switches tracer at that tracer\'s last step', () => {
    const s = state();
    s.setActive(true);
    s.first();
    expect(s.selectTracer(2)).toBe(true);
    expect(s.current).toMatchObject({ tracer: 2, index: 1, total: 2 });
    expect(s.selectTracer(9)).toBe(false);
  });

  it('follows an Events row: goToSeq finds the step, even in another tracer', () => {
    const s = state();
    s.setActive(true);
    expect(s.goToSeq(4)).toBe(true);
    expect(s.current).toMatchObject({ tracer: 2, index: 1 });
    expect(s.goToSeq(1)).toBe(true);
    expect(s.current).toMatchObject({ tracer: 1, index: 0 });
    expect(s.goToSeq(99)).toBe(false);
  });

  it('does not follow Events rows while off', () => {
    const s = state();
    expect(s.goToSeq(3)).toBe(false);
  });

  it('keeps unavailable tracers out of the cursor and lists their reason', () => {
    const s = state({ '1': 9999, '2': 2 });
    expect(s.unavailable.map((t) => [t.tracer, t.off])).toEqual([[1, 'tooMany']]);
    s.setActive(true);
    expect(s.current?.tracer).toBe(2);
  });

  it('cannot be switched on when nothing is playable', () => {
    const s = new ReplayState(replayTracers(done({ '1': 9999 }), []));
    s.setActive(true);
    expect(s.active).toBe(false);
    expect(s.available).toBe(false);
  });
});

describe('foldedParts', () => {
  it('folds earlier Sequence parts and keeps the last open', () => {
    const parts = [part('sequence', 0, 3), part('sequence', 1, 3), part('sequence', 2, 3), part('state', 0, 1)];
    expect(foldedParts(parts)).toEqual([true, true, false, false]);
  });
  it('does not fold a single Sequence part or other kinds', () => {
    expect(foldedParts([part('sequence', 0, 1), part('structure', 0, 2), part('structure', 1, 2)])).toEqual([false, false, false]);
  });
});

describe('ReplayCache', () => {
  it('keeps parts by (tracer, seq)', () => {
    const cache = new ReplayCache();
    const parts = [part('state', 0, 1)];
    cache.set(1, 5, parts);
    expect(cache.get(1, 5)).toBe(parts);
    expect(cache.get(2, 5)).toBeUndefined();
    cache.clear();
    expect(cache.get(1, 5)).toBeUndefined();
  });
});
