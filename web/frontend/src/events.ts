// Events panel: Tracer events in seq order (020-05 §2.3: file order may differ from seq).
// Clicking an event opens its source line in the editor.

import type { TraceEvent } from './api';
import { t } from './i18n';

export const MAX_EVENTS = 5000;

export function describe(e: TraceEvent): string {
  switch (e.kind) {
    case 'message':
      return `${e.from} → ${e.to} : ${e.action}`;
    case 'transition':
      return `${e.old} → ${e.new}${e.trigger ? ` (${e.trigger})` : ''}`;
    case 'node':
      return `${e.parent} → ${e.child}${e.relation ? ` [${e.relation}]` : ''}`;
    default:
      return JSON.stringify(e);
  }
}

/** Insert `incoming` into `sorted` (by seq) and keep at most MAX_EVENTS (the first ones). */
export function mergeBySeq(sorted: TraceEvent[], incoming: TraceEvent[]): TraceEvent[] {
  const out = sorted.concat(incoming).sort((a, b) => a.seq - b.seq);
  return out.length > MAX_EVENTS ? out.slice(0, MAX_EVENTS) : out;
}

export class EventsPanel {
  private events: TraceEvent[] = [];
  private pending = false;
  private selectedSeq: number | null = null;

  /** `onPick` hears about a row the user clicked (diagram replay follows it). */
  constructor(
    private readonly host: HTMLElement,
    private readonly onSelect: (file: string, line: number) => void,
    private readonly onPick: (event: TraceEvent) => void = () => {},
  ) {}

  clear(): void {
    this.events = [];
    this.selectedSeq = null;
    this.host.replaceChildren();
  }

  count(): number {
    return this.events.length;
  }

  /** The events held (at most MAX_EVENTS), in seq order. */
  all(): readonly TraceEvent[] {
    return this.events;
  }

  /** Mark the row of `seq` as selected (diagram replay moved there); no editor jump. */
  select(seq: number): void {
    this.selectedSeq = seq;
    this.host.querySelector('tr.selected')?.classList.remove('selected');
    const row = this.host.querySelector<HTMLElement>(`tr[data-seq="${seq}"]`);
    row?.classList.add('selected');
    row?.scrollIntoView?.({ block: 'nearest' });
  }

  add(incoming: TraceEvent[]): void {
    this.events = mergeBySeq(this.events, incoming);
    if (!this.pending) {
      this.pending = true;
      requestAnimationFrame(() => {
        this.pending = false;
        this.render();
      });
    }
  }

  private render(): void {
    const table = document.createElement('table');
    table.className = 'events-table';
    table.innerHTML = '<thead><tr><th>seq</th><th>tracer</th><th>kind</th><th>event</th><th>source</th></tr></thead>';
    const body = document.createElement('tbody');
    for (const e of this.events) {
      const row = document.createElement('tr');
      row.tabIndex = 0;
      row.dataset.seq = String(e.seq);
      if (e.seq === this.selectedSeq) row.classList.add('selected');
      const where = `${e.file}:${e.line}`;
      for (const [text, cls] of [[String(e.seq), 'num'], [String(e.tracer), 'num'], [e.kind, 'kind'], [describe(e), ''], [where, 'mono']] as const) {
        const td = document.createElement('td');
        td.textContent = text;
        if (cls) td.className = cls;
        row.append(td);
      }
      row.title = `${e.func}\n${where}`;
      const pick = () => {
        this.host.querySelector('tr.selected')?.classList.remove('selected');
        row.classList.add('selected');
        this.selectedSeq = e.seq;
        this.onSelect(e.file, e.line);
        this.onPick(e);
      };
      row.addEventListener('click', pick);
      row.addEventListener('keydown', (ev) => {
        if (ev.key === 'Enter') pick();
      });
      body.append(row);
    }
    table.append(body);
    this.host.replaceChildren(table);
    if (this.events.length >= MAX_EVENTS) {
      const p = document.createElement('p');
      p.className = 'muted';
      p.textContent = t('events.firstOnly', { count: MAX_EVENTS });
      this.host.append(p);
    }
  }
}
