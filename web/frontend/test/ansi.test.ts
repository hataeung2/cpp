import { describe, expect, it } from 'vitest';
import { AnsiParser, toHtml } from '../src/ansi';

const html = (...chunks: string[]) => {
  const p = new AnsiParser();
  return chunks.map((c) => toHtml(p.feed(c))).join('');
};

describe('AnsiParser', () => {
  it('maps SGR colors to token classes and resets', () => {
    expect(html('\x1b[31mred\x1b[0m plain')).toBe('<span class="ansi-fg-1">red</span> plain');
    expect(html('\x1b[1;92mok\x1b[22m!\x1b[39m')).toBe('<span class="ansi-fg-10 ansi-bold">ok</span><span class="ansi-fg-10">!</span>');
    expect(html('\x1b[44mbg\x1b[49m')).toBe('<span class="ansi-bg-4">bg</span>');
    expect(html('\x1b[mafter-empty-reset')).toBe('after-empty-reset');
  });

  it('completes an escape sequence split across chunks', () => {
    expect(html('a\x1b', '[3', '3mb')).toBe('a<span class="ansi-fg-3">b</span>');
    expect(html('x\x1b[3', '1my\x1b[0mz')).toBe('x<span class="ansi-fg-1">y</span>z');
  });

  it('keeps the style across chunks until reset', () => {
    expect(html('\x1b[35mone', ' two', '\x1b[0m three')).toBe(
      '<span class="ansi-fg-5">one</span><span class="ansi-fg-5"> two</span> three');
  });

  it('reduces 256 and RGB colors to the 16 tokens', () => {
    expect(html('\x1b[38;5;196mx')).toBe('<span class="ansi-fg-9">x</span>');
    expect(html('\x1b[38;5;2mx')).toBe('<span class="ansi-fg-2">x</span>');
    expect(html('\x1b[38;2;0;0;255mx')).toBe('<span class="ansi-fg-12">x</span>');
  });

  it('drops other control sequences and carriage returns', () => {
    expect(html('a\x1b[2Kb\x1b[1Ac\r\nd')).toBe('abc\nd');
  });

  it('escapes HTML in the text', () => {
    expect(html(`<b>&"'</b>`)).toBe('&lt;b&gt;&amp;&quot;&#39;&lt;/b&gt;');
    expect(html('\x1b[31m<script>')).toBe('<span class="ansi-fg-1">&lt;script&gt;</span>');
  });
});
