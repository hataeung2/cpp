// Output panel: build log, stdout and stderr with ANSI colors mapped to page tokens.
// Long runs keep only the last lines (070-06 Assumption 8): whole chunks are dropped from the top.

import { AnsiParser, escapeHtml, toHtml } from './ansi';

export type OutputKind = 'build' | 'stdout' | 'stderr';

const countLines = (text: string) => text.split('\n').length - 1;

export class OutputPanel {
  private parsers = new Map<OutputKind, AnsiParser>();
  private maxLines: number | null = null;
  private chunks: { node: HTMLElement; lines: number }[] = [];
  private lines = 0;
  private dropped = 0;
  private notice: HTMLElement | null = null;

  constructor(private readonly pre: HTMLElement, private readonly scroller: HTMLElement) {}

  clear(): void {
    this.pre.replaceChildren();
    this.parsers.clear();
    this.chunks = [];
    this.lines = 0;
    this.dropped = 0;
    this.notice = null;
  }

  /** Keep at most `lines` lines (null: keep everything). Applies from the next write. */
  setMaxLines(lines: number | null): void {
    this.maxLines = lines;
  }

  append(kind: OutputKind, text: string): void {
    let parser = this.parsers.get(kind);
    if (!parser) {
      parser = new AnsiParser();
      this.parsers.set(kind, parser);
    }
    this.write(`<span class="out-${kind}">${toHtml(parser.feed(text))}</span>`);
  }

  /** A line written by the page itself (phase headers, the run summary). */
  note(text: string, tone: 'info' | 'ok' | 'bad' = 'info'): void {
    this.write(`<span class="out-note ${tone}">${escapeHtml(text)}</span>\n`);
  }

  text(): string {
    return this.pre.textContent ?? '';
  }

  private write(html: string): void {
    const atBottom = this.scroller.scrollHeight - this.scroller.scrollTop - this.scroller.clientHeight < 24;
    const chunk = document.createElement('span');
    chunk.innerHTML = html;
    this.pre.append(chunk);
    const lines = countLines(chunk.textContent ?? '');
    this.chunks.push({ node: chunk, lines });
    this.lines += lines;
    if (this.maxLines !== null) this.trim(this.maxLines);
    if (atBottom) this.scroller.scrollTop = this.scroller.scrollHeight;
  }

  private trim(max: number): void {
    let removed = false;
    while (this.lines > max && this.chunks.length > 1) {
      const first = this.chunks.shift()!;
      first.node.remove();
      this.lines -= first.lines;
      this.dropped += first.lines;
      removed = true;
    }
    if (!removed) return;
    if (!this.notice) {
      this.notice = document.createElement('span');
      this.notice.className = 'out-note info';
      this.pre.prepend(this.notice);
    }
    this.notice.textContent = `… 앞의 ${this.dropped.toLocaleString()}줄은 생략 (최근 ${max.toLocaleString()}줄만 유지)\n`;
  }
}
