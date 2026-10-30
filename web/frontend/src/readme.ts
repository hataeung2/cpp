// README panel: lesson and unit READMEs as sanitized Markdown.
// Relative links stay inside the page: a .md link opens in this panel, any other repository
// file opens in the editor; external links open a new browser tab.

import DOMPurify from 'dompurify';
import { marked } from 'marked';
import { api } from './api';

/** `href` resolved against the folder of `from` (both repo-relative); null when it leaves the repo. */
export function resolveRelative(from: string, href: string): string | null {
  const parts = from.split('/').slice(0, -1);
  for (const seg of href.split('#')[0].split('/')) {
    if (seg === '' || seg === '.') continue;
    if (seg === '..') {
      if (!parts.length) return null;
      parts.pop();
    } else {
      parts.push(decodeURIComponent(seg));
    }
  }
  return parts.join('/');
}

export class ReadmePanel {
  private current: string | null = null;

  constructor(private readonly host: HTMLElement, private readonly openFile: (path: string) => void) {}

  path(): string | null {
    return this.current;
  }

  async show(path: string | null, fallback = 'README가 없습니다.'): Promise<void> {
    this.current = path;
    if (!path) {
      this.host.innerHTML = `<p class="muted">${fallback}</p>`;
      return;
    }
    let content: string;
    try {
      content = (await api.readFile(path)).content;
    } catch (err) {
      if (this.current !== path) return;
      this.host.textContent = `${path}: ${(err as Error).message}`;
      return;
    }
    if (this.current !== path) return; // another README was asked for meanwhile
    const html = DOMPurify.sanitize(await marked.parse(content));
    const doc = document.createElement('article');
    doc.className = 'markdown';
    doc.innerHTML = html;
    // the path opens the Markdown file itself in the editor, so it can be edited in the page
    const source = document.createElement('a');
    source.className = 'readme-source mono';
    source.href = '#';
    source.title = '에디터에서 열기';
    source.textContent = path;
    source.addEventListener('click', (ev) => {
      ev.preventDefault();
      this.openFile(path);
    });
    this.host.replaceChildren(source, doc);
    for (const a of doc.querySelectorAll('a[href]')) this.wire(a as HTMLAnchorElement, path);
  }

  private wire(a: HTMLAnchorElement, from: string): void {
    const href = a.getAttribute('href') ?? '';
    if (/^[a-z][a-z0-9+.-]*:/i.test(href)) {
      a.target = '_blank';
      a.rel = 'noopener noreferrer';
      return;
    }
    if (href.startsWith('#')) return;
    const target = href.startsWith('/') ? href.slice(1).split('#')[0] : resolveRelative(from, href);
    a.addEventListener('click', (ev) => {
      ev.preventDefault();
      if (!target) return;
      if (target.endsWith('.md')) void this.show(target);
      else this.openFile(target);
    });
  }
}
