// Timings panel (spec 070-06 §2.5): span aggregates from the server's `spans` events, sorted
// columns, comparison with the previous run of the same lesson, and per-key distribution bars.
// The server aggregates (§2.4 design record); this file only merges rows by key and shows them.

import type { SpanRow, SpansData } from './api';
import { t, type MessageKey } from './i18n';

// --- pure helpers (tested in test/timings.test.ts) --------------------------------------------

/** Duration text with the unit that fits, the rule of 020-06 §2.3 (ns, µs, ms, s; 3 decimals). */
export function formatNs(ns: number): string {
  if (Math.round(ns) < 1_000) return `${Math.round(ns)} ns`;
  if (ns < 1_000_000) return `${(ns / 1_000).toFixed(3)} µs`;
  if (ns < 1_000_000_000) return `${(ns / 1_000_000).toFixed(3)} ms`;
  return `${(ns / 1_000_000_000).toFixed(3)} s`;
}

/** Build kind of a run, the rule of tools/lessons.py effective_build(): the manifest's, else by profile. */
export function effectiveBuild(profile: 'quick' | 'long', build: 'release' | 'debug' | null): 'release' | 'debug' {
  return build ?? (profile === 'long' ? 'release' : 'debug');
}

/** Key of a row: (file, line, label, meter), the key of 020-06 spanStats(). */
export const rowKey = (r: Pick<SpanRow, 'file' | 'line' | 'label' | 'meter'>): string =>
  JSON.stringify([r.file, r.line, r.label, r.meter]);

export const meanNs = (r: Pick<SpanRow, 'count' | 'totalNs'>): number => (r.count ? r.totalNs / r.count : 0);

/** Merge a `spans` payload into the rows by key; a full payload replaces everything. */
export function mergeRows(rows: Map<string, SpanRow>, data: SpansData): Map<string, SpanRow> {
  const out = data.full ? new Map<string, SpanRow>() : new Map(rows);
  for (const row of data.rows) out.set(rowKey(row), row);
  return out;
}

/** What the previous run of a lesson leaves for the next one: mean per key and its build type. */
export interface PreviousRun {
  buildType: string;
  means: Record<string, number>;
}

export type Change = { kind: 'none' } | { kind: 'build' } | { kind: 'pct'; pct: number };

export function summarizeRun(rows: Iterable<SpanRow>, buildType: string): PreviousRun {
  const means: Record<string, number> = {};
  for (const row of rows) means[rowKey(row)] = meanNs(row);
  return { buildType, means };
}

/** Mean change of `row` against the previous run (070-06 §4: another build type is not compared). */
export function compareToPrevious(row: SpanRow, previous: PreviousRun | null, buildType: string): Change {
  if (!previous) return { kind: 'none' };
  if (previous.buildType !== buildType) return { kind: 'build' };
  const before = previous.means[rowKey(row)];
  if (before === undefined || before <= 0) return { kind: 'none' };
  return { kind: 'pct', pct: ((meanNs(row) - before) / before) * 100 };
}

export function changeText(change: Change): string {
  switch (change.kind) {
    case 'build':
      return t('timings.buildDiff');
    case 'pct':
      return `${change.pct >= 0 ? '+' : '−'}${Math.abs(change.pct).toFixed(1)}%`;
    default:
      return '—';
  }
}

/** One inline text per source line: rows on the same line are merged (count sum, weighted mean). */
export function inlineByLine(rows: Iterable<SpanRow>): Map<string, Map<number, string>> {
  const sums = new Map<string, Map<number, { count: number; total: number }>>();
  for (const row of rows) {
    const lines = sums.get(row.file) ?? new Map<number, { count: number; total: number }>();
    const sum = lines.get(row.line) ?? { count: 0, total: 0 };
    sum.count += row.count;
    sum.total += row.totalNs;
    lines.set(row.line, sum);
    sums.set(row.file, lines);
  }
  const out = new Map<string, Map<number, string>>();
  for (const [file, lines] of sums) {
    const texts = new Map<number, string>();
    for (const [line, sum] of lines) texts.set(line, `⏱ ${formatNs(meanNs({ count: sum.count, totalNs: sum.total }))} avg ×${sum.count}`);
    out.set(file, texts);
  }
  return out;
}

/** Lag shown in notes from this size on: below it, it is only the unfinished last line. */
export const LAG_SHOWN_BYTES = 1 << 20;

const PREVIOUS_KEY = (lessonId: string) => `atugcc.playground.timings.${lessonId}`;

/** localStorage, or null when the page may not use it (private window, blocked site data, full). */
export function pageStorage(): Storage | null {
  try {
    const storage = window.localStorage;
    storage.setItem('atugcc.playground.probe', '1');
    storage.removeItem('atugcc.playground.probe');
    return storage;
  } catch {
    return null;
  }
}

export function loadPrevious(storage: Storage | null, lessonId: string): PreviousRun | null {
  try {
    const raw = storage?.getItem(PREVIOUS_KEY(lessonId));
    if (!raw) return null;
    const data = JSON.parse(raw) as PreviousRun;
    if (typeof data?.buildType !== 'string' || typeof data.means !== 'object' || data.means === null) return null;
    return data;
  } catch {
    return null; // unreadable or blocked storage: the comparison column is left out
  }
}

export function savePrevious(storage: Storage | null, lessonId: string, run: PreviousRun): boolean {
  try {
    if (!storage) return false;
    storage.setItem(PREVIOUS_KEY(lessonId), JSON.stringify(run));
    return true;
  } catch {
    return false;
  }
}

// --- panel -------------------------------------------------------------------------------------

type SortKey = 'label' | 'where' | 'meter' | 'count' | 'total' | 'mean' | 'p50' | 'p95' | 'min' | 'max' | 'change';

const COLUMNS: { key: SortKey; titleKey: MessageKey; numeric: boolean }[] = [
  { key: 'label', titleKey: 'timings.colLabel', numeric: false },
  { key: 'where', titleKey: 'timings.colWhere', numeric: false },
  { key: 'meter', titleKey: 'timings.colMeter', numeric: false },
  { key: 'count', titleKey: 'timings.colCount', numeric: true },
  { key: 'total', titleKey: 'timings.colTotal', numeric: true },
  { key: 'mean', titleKey: 'timings.colMean', numeric: true },
  { key: 'p50', titleKey: 'timings.colP50', numeric: true },
  { key: 'p95', titleKey: 'timings.colP95', numeric: true },
  { key: 'min', titleKey: 'timings.colMin', numeric: true },
  { key: 'max', titleKey: 'timings.colMax', numeric: true },
  { key: 'change', titleKey: 'timings.colChange', numeric: true },
];

const baseName = (path: string) => path.slice(path.lastIndexOf('/') + 1);
const SVG_NS = 'http://www.w3.org/2000/svg';

/** Distribution bars of a row's sample (log scale from loNs to hiNs). */
export function histogramSvg(hist: SpanRow['hist']): SVGSVGElement {
  const width = 260;
  const height = 56;
  const svg = document.createElementNS(SVG_NS, 'svg');
  svg.setAttribute('viewBox', `0 0 ${width} ${height}`);
  svg.setAttribute('class', 'timing-hist');
  svg.setAttribute('role', 'img');
  svg.setAttribute('aria-label', t('timings.histAria', { lo: formatNs(hist.loNs), hi: formatNs(hist.hiNs) }));
  const top = Math.max(1, ...hist.bins);
  const barArea = height - 16;
  const step = width / hist.bins.length;
  hist.bins.forEach((count, i) => {
    const h = (count / top) * barArea;
    const rect = document.createElementNS(SVG_NS, 'rect');
    rect.setAttribute('x', String(i * step + 1));
    rect.setAttribute('y', String(barArea - h));
    rect.setAttribute('width', String(Math.max(1, step - 2)));
    rect.setAttribute('height', String(h));
    rect.setAttribute('class', 'bar');
    const title = document.createElementNS(SVG_NS, 'title');
    title.textContent = String(count);
    rect.append(title);
    svg.append(rect);
  });
  for (const [x, anchor, text] of [[0, 'start', formatNs(hist.loNs)], [width, 'end', formatNs(hist.hiNs)]] as const) {
    const label = document.createElementNS(SVG_NS, 'text');
    label.setAttribute('x', String(x));
    label.setAttribute('y', String(height - 2));
    label.setAttribute('text-anchor', anchor);
    label.textContent = text;
    svg.append(label);
  }
  return svg;
}

export class TimingsPanel {
  private rows = new Map<string, SpanRow>();
  private previous: PreviousRun | null = null;
  private storage: Storage | null = null; // null: no comparison column (070-06 §4)
  private selectedKey: string | null = null;
  private lessonId: string | null = null;
  private buildType = '';
  private lagBytes = 0;
  private spanLines = 0;
  private ended: (() => string | null) | null = null; // a function so relabel() shows it in the new language
  private sort: { key: SortKey; desc: boolean } = { key: 'total', desc: true };
  private expanded = new Set<string>();
  private pending = false;
  /** Called after each render with the current rows (inline times in the editor). */
  onRows: (rows: SpanRow[]) => void = () => {};

  constructor(private readonly host: HTMLElement, private readonly onSelect: (file: string, line: number) => void) {
    this.render();
  }

  /** A new run of `lessonId`: clears the rows and loads the previous run for the comparison. */
  start(lessonId: string): void {
    this.rows = new Map();
    this.expanded.clear();
    this.lessonId = lessonId;
    this.selectedKey = null;
    this.storage = pageStorage();
    this.previous = loadPrevious(this.storage, lessonId);
    this.buildType = '';
    this.lagBytes = 0;
    this.spanLines = 0;
    this.ended = null;
    this.schedule();
  }

  setBuildType(buildType: string): void {
    this.buildType = buildType;
    this.schedule();
  }

  update(data: SpansData): void {
    this.rows = mergeRows(this.rows, data);
    this.lagBytes = data.lagBytes;
    this.spanLines = data.spanLines;
    this.schedule();
  }

  /** The run ended: keep its means for the next run's comparison (when there were spans). */
  finish(note: string | null | (() => string | null)): void {
    this.ended = typeof note === 'function' ? note : () => note;
    this.lagBytes = 0;
    if (this.lessonId && this.rows.size && this.buildType) {
      savePrevious(this.storage, this.lessonId, summarizeRun(this.rows.values(), this.buildType));
    }
    this.schedule();
  }

  rowCount(): number {
    return this.rows.size;
  }

  relabel(): void {
    this.render(false);
  }

  private schedule(): void {
    if (this.pending) return;
    this.pending = true;
    requestAnimationFrame(() => {
      this.pending = false;
      this.render();
    });
  }

  private value(row: SpanRow, key: SortKey): number | string {
    switch (key) {
      case 'label': return row.label;
      case 'where': return `${row.file}:${String(row.line).padStart(6, '0')}`;
      case 'meter': return row.meter;
      case 'count': return row.count;
      case 'total': return row.totalNs;
      case 'mean': return meanNs(row);
      case 'p50': return row.p50Ns;
      case 'p95': return row.p95Ns;
      case 'min': return row.minNs;
      case 'max': return row.maxNs;
      case 'change': {
        const c = compareToPrevious(row, this.previous, this.buildType);
        return c.kind === 'pct' ? c.pct : Number.NEGATIVE_INFINITY;
      }
    }
  }

  private sorted(): SpanRow[] {
    const { key, desc } = this.sort;
    return [...this.rows.values()].sort((a, b) => {
      const x = this.value(a, key);
      const y = this.value(b, key);
      const order = typeof x === 'number' && typeof y === 'number' ? x - y : String(x).localeCompare(String(y));
      return desc ? -order : order;
    });
  }

  private render(notifyOnRows = true): void {
    const notes = document.createElement('div');
    notes.className = 'timings-notes';
    const parts = [
      this.buildType ? t('timings.build', { build: this.buildType }) : '',
      this.spanLines ? t('timings.spansCount', { count: this.spanLines.toLocaleString() }) : '',
    ];
    if (this.lagBytes >= LAG_SHOWN_BYTES) parts.push(t('timings.lag', { mib: (this.lagBytes / (1 << 20)).toFixed(1) }));
    const ended = this.ended?.();
    if (ended) parts.push(ended);
    notes.textContent = parts.filter(Boolean).join(' · ');
    notes.classList.toggle('warn', this.lagBytes >= LAG_SHOWN_BYTES);

    if (!this.rows.size) {
      const empty = document.createElement('p');
      empty.className = 'muted';
      empty.textContent = t('timings.empty');
      this.host.replaceChildren(notes, empty);
      if (notifyOnRows) this.onRows([]);
      return;
    }

    const columns = COLUMNS.filter((c) => c.key !== 'change' || this.storage !== null);
    const table = document.createElement('table');
    table.className = 'timings-table';
    const head = document.createElement('tr');
    for (const col of columns) {
      const th = document.createElement('th');
      th.textContent = t(col.titleKey) + (this.sort.key === col.key ? (this.sort.desc ? ' ▼' : ' ▲') : '');
      if (col.numeric) th.className = 'num';
      th.tabIndex = 0;
      const resort = () => {
        this.sort = this.sort.key === col.key ? { key: col.key, desc: !this.sort.desc } : { key: col.key, desc: col.numeric };
        this.render();
      };
      th.addEventListener('click', resort);
      th.addEventListener('keydown', (ev) => {
        if (ev.key === 'Enter') resort();
      });
      head.append(th);
    }
    const thead = document.createElement('thead');
    thead.append(head);
    const body = document.createElement('tbody');
    const rows = this.sorted();
    for (const row of rows) {
      const key = rowKey(row);
      const tr = document.createElement('tr');
      tr.tabIndex = 0;
      if (key === this.selectedKey) tr.classList.add('selected'); // the table is rebuilt on every update
      tr.title = t('timings.rowTooltip', { where: `${row.file}:${row.line}` });
      const change = compareToPrevious(row, this.previous, this.buildType);
      const cells: [string, string][] = [
        [`${this.expanded.has(key) ? '▾' : '▸'} ${row.label}`, 'label'],
        [`${baseName(row.file)}:${row.line}`, 'mono'],
        [row.meter, ''],
        [row.count.toLocaleString(), 'num'],
        [formatNs(row.totalNs), 'num'],
        [formatNs(meanNs(row)), 'num'],
        [formatNs(row.p50Ns), 'num'],
        [formatNs(row.p95Ns), 'num'],
        [formatNs(row.minNs), 'num'],
        [formatNs(row.maxNs), 'num'],
        [changeText(change), `num change ${change.kind === 'pct' ? (change.pct > 0 ? 'up' : 'down') : change.kind}`],
      ].slice(0, columns.length) as [string, string][];
      for (const [text, cls] of cells) {
        const td = document.createElement('td');
        td.textContent = text;
        if (cls) td.className = cls;
        tr.append(td);
      }
      const toggle = (ev: Event) => {
        ev.stopPropagation();
        if (this.expanded.has(key)) this.expanded.delete(key);
        else this.expanded.add(key);
        this.render();
      };
      tr.firstElementChild!.addEventListener('click', toggle);
      const select = () => {
        this.selectedKey = key;
        this.host.querySelector('tr.selected')?.classList.remove('selected');
        tr.classList.add('selected');
        this.onSelect(row.file, row.line);
      };
      tr.addEventListener('click', select);
      tr.addEventListener('keydown', (ev) => {
        if (ev.key === 'Enter') select();
        if (ev.key === ' ') {
          ev.preventDefault(); // no page scroll
          toggle(ev);
        }
      });
      body.append(tr);
      if (this.expanded.has(key)) {
        const detail = document.createElement('tr');
        detail.className = 'timing-detail';
        const td = document.createElement('td');
        td.colSpan = columns.length;
        td.append(histogramSvg(row.hist));
        detail.append(td);
        body.append(detail);
      }
    }
    table.append(thead, body);
    const hint = document.createElement('p');
    hint.className = 'muted';
    hint.textContent = t('timings.hint');
    this.host.replaceChildren(notes, table, hint);
    if (notifyOnRows) this.onRows(rows);
  }
}
