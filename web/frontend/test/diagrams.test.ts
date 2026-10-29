// Viewer policy (diagrams.md §3: never below 80 % of the natural size) and the small pure
// helpers of the panels.
import { describe, expect, it } from 'vitest';
import type { TraceEvent } from '../src/api';
import { MIN_SCALE, fitScale, mermaidSource } from '../src/diagrams';
import { mergeBySeq } from '../src/events';
import { resolveRelative } from '../src/readme';

describe('fitScale', () => {
  it('keeps the natural size when it fits', () => {
    expect(fitScale(400, 800)).toBe(1);
  });
  it('shrinks to fit down to 80 %', () => {
    expect(fitScale(1000, 900)).toBeCloseTo(0.9);
    expect(fitScale(1000, 800)).toBeCloseTo(0.8);
  });
  it('stops at 80 % for wide diagrams (the container scrolls)', () => {
    expect(fitScale(3000, 600)).toBe(MIN_SCALE);
    expect(MIN_SCALE).toBe(0.8);
  });
  it('treats unknown sizes as natural', () => {
    expect(fitScale(0, 500)).toBe(1);
    expect(fitScale(500, 0)).toBe(1);
  });
});

describe('mermaidSource', () => {
  it('unwraps the Markdown block of DiagramPart::source', () => {
    expect(mermaidSource('```mermaid\nstateDiagram-v2\n    A --> B\n```\n')).toBe('stateDiagram-v2\n    A --> B');
  });
  it('leaves bare Mermaid text alone', () => {
    expect(mermaidSource('graph TD\n A-->B')).toBe('graph TD\n A-->B');
  });
});

describe('events order', () => {
  const ev = (seq: number): TraceEvent => ({ v: 1, kind: 'node', seq, tracer: 1, file: 'f', line: 1, func: 'g', tUs: 0 });
  it('sorts by seq across batches (file order may differ from seq)', () => {
    const merged = mergeBySeq(mergeBySeq([], [ev(3), ev(1)]), [ev(2), ev(5), ev(4)]);
    expect(merged.map((e) => e.seq)).toEqual([1, 2, 3, 4, 5]);
  });
});

describe('README links', () => {
  it('resolves relative links against the README folder', () => {
    expect(resolveRelative('lessons/tracks/01_essentials/01_lambda_capture/README.md', '../../../units/lambda_capture/README.md'))
      .toBe('lessons/units/lambda_capture/README.md');
    expect(resolveRelative('lessons/README.md', 'units/a/x.hpp#L3')).toBe('lessons/units/a/x.hpp');
    expect(resolveRelative('README.md', '../outside.md')).toBeNull();
  });
});
