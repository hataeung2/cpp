// AC-6: compile errors become editor markers on the right file and line.
import { describe, expect, it } from 'vitest';
import type { Diagnostic } from '../src/api';
import { MarkerSeverity, groupByFile, toMarkers } from '../src/diagnostics';

const diag = (file: string, line: number, col: number, severity: Diagnostic['severity'], message = 'm'): Diagnostic =>
  ({ file, line, col, severity, message });

describe('diagnostics → markers', () => {
  const list = [
    diag('lessons/a/main.cpp', 7, 5, 'error', "'foo' was not declared in this scope"),
    diag('lessons/units/u/u.hpp', 3, 1, 'warning'),
    diag('/usr/include/c++/13/bits/x.h', 10, 2, 'note'),
    diag('lessons/a/main.cpp', 9, 0, 'note'),
    diag('out/build/linux-x64-playground/gen.cpp', 1, 1, 'error'),
  ];

  it('groups by repository file and leaves out system headers and the build tree', () => {
    const groups = groupByFile(list);
    expect([...groups.keys()]).toEqual(['lessons/a/main.cpp', 'lessons/units/u/u.hpp']);
    expect(groups.get('lessons/a/main.cpp')!.map((d) => d.line)).toEqual([7, 9]);
  });

  it('places each marker on its line, from the column to the end of the line', () => {
    const lengths: Record<number, number> = { 7: 20, 9: 4 };
    const markers = toMarkers(groupByFile(list).get('lessons/a/main.cpp')!, (l) => lengths[l] ?? 0);
    expect(markers).toEqual([
      { severity: MarkerSeverity.Error, message: "'foo' was not declared in this scope", startLineNumber: 7, startColumn: 5,
        endLineNumber: 7, endColumn: 21, source: 'gcc' },
      { severity: MarkerSeverity.Info, message: 'm', startLineNumber: 9, startColumn: 1, endLineNumber: 9, endColumn: 5, source: 'gcc' },
    ]);
  });

  it('maps warning severity and never makes an empty range', () => {
    const [m] = toMarkers([diag('lessons/x.cpp', 2, 30, 'warning')], () => 10);
    expect(m.severity).toBe(MarkerSeverity.Warning);
    expect(m.endColumn).toBeGreaterThan(m.startColumn);
  });
});
