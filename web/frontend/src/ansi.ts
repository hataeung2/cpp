// ANSI SGR → spans with token classes (diagrams.md §3: terminal colors map to page tokens).
// Stateful: an escape sequence split across two output chunks is completed by the next feed().
// Other control sequences (cursor moves, erase) are dropped.

export interface Segment {
  text: string;
  classes: string[];
}

interface Style {
  fg: number | null; // 0..15
  bg: number | null;
  bold: boolean;
  dim: boolean;
  italic: boolean;
  underline: boolean;
}

const plain = (): Style => ({ fg: null, bg: null, bold: false, dim: false, italic: false, underline: false });

function classesOf(s: Style): string[] {
  const out: string[] = [];
  if (s.fg !== null) out.push(`ansi-fg-${s.fg}`);
  if (s.bg !== null) out.push(`ansi-bg-${s.bg}`);
  if (s.bold) out.push('ansi-bold');
  if (s.dim) out.push('ansi-dim');
  if (s.italic) out.push('ansi-italic');
  if (s.underline) out.push('ansi-underline');
  return out;
}

/** xterm 256-color index → nearest of the 16 base colors (tokens exist only for those). */
function from256(n: number): number {
  if (n < 16) return n;
  if (n >= 232) return n < 244 ? 8 : 7; // grayscale ramp
  const c = n - 16;
  const r = Math.floor(c / 36), g = Math.floor(c / 6) % 6, b = c % 6;
  const bright = Math.max(r, g, b) > 3;
  const bit = (v: number) => (v >= 2 ? 1 : 0);
  const base = bit(r) | (bit(g) << 1) | (bit(b) << 2);
  return base + (bright ? 8 : 0);
}

function fromRgb(r: number, g: number, b: number): number {
  const bit = (v: number) => (v >= 128 ? 1 : 0);
  const base = bit(r) | (bit(g) << 1) | (bit(b) << 2);
  return base + (Math.max(r, g, b) > 200 ? 8 : 0);
}

export class AnsiParser {
  private style: Style = plain();
  private pending = '';

  /** Parse the next chunk; returns styled segments (empty texts are omitted). */
  feed(chunk: string): Segment[] {
    const input = this.pending + chunk;
    this.pending = '';
    const out: Segment[] = [];
    let text = '';
    const emit = () => {
      if (text) out.push({ text, classes: classesOf(this.style) });
      text = '';
    };
    let i = 0;
    while (i < input.length) {
      const ch = input[i];
      if (ch === '\x1b') {
        if (i + 1 >= input.length) {
          this.pending = input.slice(i);
          break;
        }
        if (input[i + 1] === '[') {
          let j = i + 2;
          while (j < input.length && !/[@-~]/.test(input[j])) j++;
          if (j >= input.length) {
            this.pending = input.slice(i);
            break;
          }
          if (input[j] === 'm') {
            emit();
            this.apply(input.slice(i + 2, j));
          }
          i = j + 1;
          continue;
        }
        i += 2; // two-character escape: drop
        continue;
      }
      if (ch === '\r') {
        i++; // CRLF → LF; a lone CR (progress bars) is dropped
        continue;
      }
      text += ch;
      i++;
    }
    emit();
    return out;
  }

  private apply(params: string): void {
    const codes = params === '' ? [0] : params.split(';').map((p) => (p === '' ? 0 : Number(p)));
    for (let k = 0; k < codes.length; k++) {
      const c = codes[k];
      if (c === 0) this.style = plain();
      else if (c === 1) this.style.bold = true;
      else if (c === 2) this.style.dim = true;
      else if (c === 3) this.style.italic = true;
      else if (c === 4) this.style.underline = true;
      else if (c === 22) { this.style.bold = false; this.style.dim = false; }
      else if (c === 23) this.style.italic = false;
      else if (c === 24) this.style.underline = false;
      else if (c >= 30 && c <= 37) this.style.fg = c - 30;
      else if (c === 39) this.style.fg = null;
      else if (c >= 40 && c <= 47) this.style.bg = c - 40;
      else if (c === 49) this.style.bg = null;
      else if (c >= 90 && c <= 97) this.style.fg = c - 90 + 8;
      else if (c >= 100 && c <= 107) this.style.bg = c - 100 + 8;
      else if (c === 38 || c === 48) {
        let color: number | null = null;
        if (codes[k + 1] === 5 && k + 2 < codes.length) {
          color = from256(codes[k + 2]);
          k += 2;
        } else if (codes[k + 1] === 2 && k + 4 < codes.length) {
          color = fromRgb(codes[k + 2], codes[k + 3], codes[k + 4]);
          k += 4;
        }
        if (color !== null) {
          if (c === 38) this.style.fg = color;
          else this.style.bg = color;
        }
      }
    }
  }
}

const ESCAPES: Record<string, string> = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };

export function escapeHtml(text: string): string {
  return text.replace(/[&<>"']/g, (c) => ESCAPES[c]);
}

/** Segments as HTML: escaped text, a span only where a style applies. */
export function toHtml(segments: Segment[]): string {
  return segments
    .map((s) => (s.classes.length ? `<span class="${s.classes.join(' ')}">${escapeHtml(s.text)}</span>` : escapeHtml(s.text)))
    .join('');
}
