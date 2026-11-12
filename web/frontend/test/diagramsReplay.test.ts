// DiagramsPanel replay bar (spec 070-07 AC-5): the controls, the cursor, the hooks. Mermaid is not
// loaded here (the fixtures have no diagrams); drawing is checked in a real browser.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { DoneData, TraceEvent } from '../src/api';
import { DiagramsPanel } from '../src/diagrams';

function event(seq: number, tracer = 1): TraceEvent {
  return { v: 1, kind: 'message', seq, tracer, file: 'a.cpp', line: 10 + seq, func: 'f', tUs: 0, from: 'A', to: 'B', action: `m${seq}` };
}

function done(tracers: Record<string, number>, max = 5000): DoneData {
  return {
    build: { ok: true, ms: 0, diagnostics: [], timedOut: false },
    run: { exitCode: 0, signal: null, timedOut: false, stopped: false, traceLimit: false, ms: 1, truncated: false },
    diagrams: [],
    skippedTraceLines: 0,
    stopped: false,
    replay: { max, tracers },
  };
}

describe('DiagramsPanel replay bar', () => {
  let host: HTMLElement;
  let steps: number[];
  let panel: DiagramsPanel;

  beforeEach(() => {
    vi.useFakeTimers();
    vi.stubGlobal('ResizeObserver', class { observe() {} disconnect() {} });
    host = document.createElement('div');
    document.body.append(host);
    steps = [];
    panel = new DiagramsPanel(host, document.createElement('dialog'), {
      fetchParts: async () => [],
      onStep: (e) => steps.push(e.seq),
    });
  });

  afterEach(() => {
    panel.clear();
    vi.useRealTimers();
    vi.unstubAllGlobals();
    host.remove();
  });

  const bar = () => host.querySelector<HTMLElement>('.replay-bar')!;
  const count = () => host.querySelector('.replay-count')?.textContent;
  const button = (glyph: string) => [...host.querySelectorAll<HTMLButtonElement>('button')].find((b) => b.textContent === glyph)!;
  const click = (glyph: string) => button(glyph).click();
  const toggle = () => bar().querySelector<HTMLButtonElement>('button')!;
  const events = [event(1), event(2), event(3)];

  it('has no bar for a run without tracer events', () => {
    panel.show(done({}), []);
    expect(bar().hidden).toBe(true);
  });

  it('shows a switch first; the controls come with it, at the last step', () => {
    panel.show(done({ '1': 3 }), events);
    expect(bar().hidden).toBe(false);
    expect(host.querySelector('.replay-count')).toBeNull();
    toggle().click();
    expect(count()).toBe('3 / 3');
    expect(steps).toEqual([3]); // the page is told so it can show the event's line
  });

  it('steps with the buttons and tells the page each time', () => {
    panel.show(done({ '1': 3 }), events);
    toggle().click();
    click('◀');
    expect(count()).toBe('2 / 3');
    click('⏮');
    expect(count()).toBe('1 / 3');
    click('◀'); // already at the first step: nothing moves, nobody is told
    click('⏭');
    expect(count()).toBe('3 / 3');
    expect(steps).toEqual([3, 2, 1, 3]);
  });

  it('keeps the same slider and buttons across a step (focus and drag survive)', () => {
    panel.show(done({ '1': 3 }), events);
    toggle().click();
    const slider = host.querySelector('input.replay-slider');
    const prev = button('◀');
    click('◀');
    expect(host.querySelector('input.replay-slider')).toBe(slider);
    expect(button('◀')).toBe(prev);
    expect((slider as HTMLInputElement).value).toBe('1');
  });

  it('follows an Events row without telling the page again', () => {
    panel.show(done({ '1': 3 }), events);
    toggle().click();
    steps.length = 0;
    panel.goToSeq(1);
    expect(count()).toBe('1 / 3');
    expect(steps).toEqual([]);
  });

  it('moves with ←/→ on the panel, ignores them in a field and with a modifier', () => {
    panel.show(done({ '1': 3 }), events);
    toggle().click();
    host.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowLeft', bubbles: true }));
    expect(count()).toBe('2 / 3');
    host.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowLeft', altKey: true, bubbles: true }));
    expect(count()).toBe('2 / 3');
    host.querySelector('input')!.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowLeft', bubbles: true }));
    expect(count()).toBe('2 / 3');
    host.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowRight', bubbles: true }));
    expect(count()).toBe('3 / 3');
  });

  it('offers a tracer choice when two tracers can be replayed', () => {
    panel.show(done({ '1': 2, '2': 1 }), [event(1), event(3), event(2, 2)]);
    toggle().click();
    const select = host.querySelector('select')!;
    expect([...select.options].map((o) => o.textContent)).toEqual(['Tracer #1', 'Tracer #2']);
    select.value = '2';
    select.dispatchEvent(new Event('change'));
    expect(count()).toBe('1 / 1');
  });

  it('says why a tracer over the cap cannot be replayed', () => {
    panel.show(done({ '1': 5001 }), events);
    expect(bar().hidden).toBe(false);
    expect(bar().textContent).toContain('5001');
    expect(bar().textContent).toContain('5000');
    expect(bar().querySelector('button')).toBeNull();
  });

  it('says why when the Events tab lost events of the tracer', () => {
    panel.show(done({ '1': 4 }), events);
    expect(bar().textContent).toContain('Events');
    expect(bar().querySelector('button')).toBeNull();
  });

  it('switches off and goes back to the finished diagrams', () => {
    panel.show(done({ '1': 3 }), events);
    toggle().click();
    toggle().click();
    expect(host.querySelector('.replay-count')).toBeNull();
  });

  it('clear() removes the bar for the next run', () => {
    panel.show(done({ '1': 3 }), events);
    toggle().click();
    panel.clear();
    expect(bar().hidden).toBe(true);
    expect(bar().childElementCount).toBe(0);
  });
});
