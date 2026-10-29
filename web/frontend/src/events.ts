// Events panel: Tracer events in seq order (020-05 §2.3: file order may differ from seq).
// Clicking an event opens its source line in the editor.

import type { TraceEvent } from './api';

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

  constructor(private readonly host: HTMLElement, private readonly onSelect: (file: string, line: number) => void) {}

  clear(): void {
    this.events = [];
    this.host.replaceChildren();
  }

  count(): number {
    return this.events.length;
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
        this.onSelect(e.file, e.line);
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
      p.textContent = `처음 ${MAX_EVENTS}개만 표시합니다.`;
      this.host.append(p);
    }
  }
}
