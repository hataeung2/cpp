// GCC diagnostics from the `done` event → Monaco marker data (spec 070-02 AC-6).
// Kept free of Monaco imports so it runs in unit tests; severities use Monaco's numbers.

import type { Diagnostic } from './api';

export const MarkerSeverity = { Hint: 1, Info: 2, Warning: 4, Error: 8 } as const;

export interface MarkerData {
  severity: number;
  message: string;
  startLineNumber: number;
  startColumn: number;
  endLineNumber: number;
  endColumn: number;
  source: string;
}

const SEVERITY: Record<Diagnostic['severity'], number> = {
  error: MarkerSeverity.Error,
  warning: MarkerSeverity.Warning,
  note: MarkerSeverity.Info,
};

/** Diagnostics grouped by repo-relative file; files outside the repository are left out. */
export function groupByFile(diagnostics: Diagnostic[]): Map<string, Diagnostic[]> {
  const out = new Map<string, Diagnostic[]>();
  for (const d of diagnostics) {
    if (d.file.startsWith('/') || d.file.startsWith('out/')) continue; // system headers, build tree
    const list = out.get(d.file) ?? [];
    list.push(d);
    out.set(d.file, list);
  }
  return out;
}

/**
 * Markers for one file. A marker spans from the reported column to the end of the line
 * (`lineLength` gives it; Monaco also clamps a column past the end).
 */
export function toMarkers(diagnostics: Diagnostic[], lineLength: (line: number) => number = () => 1000): MarkerData[] {
  return diagnostics.map((d) => {
    const col = Math.max(1, d.col);
    return {
      severity: SEVERITY[d.severity],
      message: d.message,
      startLineNumber: d.line,
      startColumn: col,
      endLineNumber: d.line,
      endColumn: Math.max(col + 1, lineLength(d.line) + 1),
      source: 'gcc',
    };
  });
}
