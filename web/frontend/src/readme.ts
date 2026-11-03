// README panel: lesson and unit READMEs as sanitized Markdown.
// Relative links stay inside the page: a .md link opens in this panel, any other repository
// file opens in the editor; external links open a new browser tab.

import DOMPurify from 'dompurify';
import { marked } from 'marked';
import { api } from './api';
import { t } from './i18n';

export interface ReadmeOptions {
  notice?: boolean;
  alternate?: string | null;
  tags?: { id: string; label: string }[];
}

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
  private currentOptions: ReadmeOptions = {};

  constructor(
    private readonly host: HTMLElement,
    private readonly openFile: (path: string) => void,
    private readonly onTag: (id: string) => void = () => {},
  ) {}

  path(): string | null {
    return this.current;
  }

  options(): ReadmeOptions {
    return this.currentOptions;
  }

  async show(path: string | null, options: ReadmeOptions = {}): Promise<void> {
    this.current = path;
    this.currentOptions = options;
    if (!path) {
      const p = document.createElement('p');
      p.className = 'muted';
      p.textContent = t('readme.none');
      this.host.replaceChildren(...this.chips(options), p);
      return;
    }
    let content: string;
    try {
      content = (await api.readFile(path)).content;
    } catch (err) {
      if (this.current !== path) return;
      if (options.alternate) {
        await this.show(options.alternate, { notice: true });
        return;
      }
      const error = document.createElement('p');
      error.textContent = `${path}: ${(err as Error).message}`;
      this.host.replaceChildren(...this.chips(options), error);
      return;
    }
    if (this.current !== path) return; // another README was asked for meanwhile
    const html = DOMPurify.sanitize(await marked.parse(content));
    if (this.current !== path) return;
    const doc = document.createElement('article');
    doc.className = 'markdown';
    doc.innerHTML = html;
    // the path opens the Markdown file itself in the editor, so it can be edited in the page
    const source = document.createElement('a');
    source.className = 'readme-source mono';
    source.href = '#';
    source.title = t('readme.openInEditor');
    source.textContent = path;
    source.addEventListener('click', (ev) => {
      ev.preventDefault();
      this.openFile(path);
    });

    const elements: HTMLElement[] = [source, ...this.chips(options)];
    if (options.notice) {
      const notice = document.createElement('p');
      notice.className = 'readme-notice';
      notice.textContent = t('readme.koreanOnly');
      elements.push(notice);
    }
    elements.push(doc);
    this.host.replaceChildren(...elements);

    for (const a of doc.querySelectorAll('a[href]')) this.wire(a as HTMLAnchorElement, path);
  }

  /** The lesson's tag chips (070-10 Assumption 8): label in the page language, tooltip the tag key. */
  private chips(options: ReadmeOptions): HTMLElement[] {
    if (!options.tags?.length) return [];
    const row = document.createElement('div');
    row.className = 'tag-chips';
    for (const tag of options.tags) {
      const chip = document.createElement('button');
      chip.type = 'button';
      chip.className = 'tag-chip';
      chip.textContent = tag.label;
      chip.title = tag.id;
      chip.addEventListener('click', () => this.onTag(tag.id));
      row.append(chip);
    }
    return [row];
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
