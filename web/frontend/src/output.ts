// Output panel: build log, stdout and stderr with ANSI colors mapped to page tokens.

import { AnsiParser, escapeHtml, toHtml } from './ansi';

export type OutputKind = 'build' | 'stdout' | 'stderr';

export class OutputPanel {
  private parsers = new Map<OutputKind, AnsiParser>();

  constructor(private readonly pre: HTMLElement, private readonly scroller: HTMLElement) {}

  clear(): void {
    this.pre.replaceChildren();
    this.parsers.clear();
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
    this.pre.insertAdjacentHTML('beforeend', html);
    if (atBottom) this.scroller.scrollTop = this.scroller.scrollHeight;
  }
}
