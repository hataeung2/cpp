// Diagrams panel: the Mermaid parts a run's Tracers wrote at destruction (020-05 `diagram` lines).
// Viewer policy (diagrams.md §3): natural size, never shrunk below 80 %; a wider part scrolls
// inside its own container; text 14 px or more; every part has a full-size view.

import type { DiagramLine, DoneData } from './api';

export const MIN_SCALE = 0.8;

/** Scale for a diagram `natural` px wide in `available` px: fit when possible, never below 80 %. */
export function fitScale(natural: number, available: number): number {
  if (!(natural > 0) || !(available > 0)) return 1;
  return Math.min(1, Math.max(MIN_SCALE, available / natural));
}

/** Mermaid text of a part: DiagramPart::source is a Markdown block (```mermaid … ```). */
export function mermaidSource(source: string): string {
  const m = /^\s*```[a-z]*\n([\s\S]*?)\n?```\s*$/.exec(source);
  return m ? m[1] : source;
}

type Mermaid = typeof import('mermaid').default;
let mermaidPromise: Promise<Mermaid> | null = null;
let renderCount = 0;

/** Mermaid settings shared by the page and the parse test. */
export function mermaidConfig(dark: boolean) {
  return {
    startOnLoad: false,
    securityLevel: 'strict' as const,
    theme: dark ? ('dark' as const) : ('default' as const),
    fontSize: 14,
    themeVariables: { fontSize: '14px' },
    flowchart: { useMaxWidth: false },
    sequence: { useMaxWidth: false },
    state: { useMaxWidth: false },
    class: { useMaxWidth: false },
  };
}

function loadMermaid(dark: boolean): Promise<Mermaid> {
  mermaidPromise ??= import('mermaid').then((m) => m.default);
  return mermaidPromise.then((m) => {
    m.initialize(mermaidConfig(dark));
    return m;
  });
}

function naturalSize(svg: SVGSVGElement): { w: number; h: number } {
  const vb = svg.viewBox?.baseVal;
  if (vb && vb.width > 0) return { w: vb.width, h: vb.height };
  return { w: Number.parseFloat(svg.getAttribute('width') ?? '0'), h: Number.parseFloat(svg.getAttribute('height') ?? '0') };
}

export class DiagramsPanel {
  private parts: DiagramLine[] = [];
  private note = '';
  private dark = false;
  private generation = 0; // a newer draw() or clear() makes an older draw stop
  private readonly observer = new ResizeObserver(() => this.fitAll());

  constructor(private readonly host: HTMLElement, private readonly dialog: HTMLDialogElement) {
    this.observer.observe(host);
  }

  clear(): void {
    this.generation++;
    this.parts = [];
    this.note = '';
    this.host.replaceChildren();
  }

  setTheme(dark: boolean): void {
    this.dark = dark;
    if (this.parts.length) void this.draw();
  }

  /** Show the diagrams of a finished run. */
  show(done: DoneData): void {
    this.parts = done.diagrams.filter((d) => d.backend === 'mermaid');
    const run = done.run;
    const abnormal = !run || run.timedOut || run.stopped || run.signal !== null;
    this.note = this.parts.length
      ? ''
      : abnormal
        ? '다이어그램 없음: 정상 종료가 아니라서 Tracer 소멸자가 다이어그램을 쓰지 못했습니다.'
        : '이 실행은 Tracer 다이어그램을 만들지 않았습니다.';
    void this.draw();
  }

  private async draw(): Promise<void> {
    const generation = ++this.generation;
    this.host.replaceChildren();
    if (this.note) {
      const p = document.createElement('p');
      p.className = 'muted';
      p.textContent = this.note;
      this.host.append(p);
      return;
    }
    const mermaid = await loadMermaid(this.dark);
    let tracer = -1;
    for (const part of this.parts) {
      if (generation !== this.generation) return;
      if (part.tracer !== tracer) {
        tracer = part.tracer;
        const h = document.createElement('h3');
        h.textContent = `Tracer #${tracer}`;
        this.host.append(h);
      }
      const card = await this.card(mermaid, part);
      if (generation !== this.generation) return;
      this.host.append(card);
    }
    this.fitAll();
  }

  private async card(mermaid: Mermaid, part: DiagramLine): Promise<HTMLElement> {
    const card = document.createElement('figure');
    card.className = 'diagram';
    const head = document.createElement('figcaption');
    const title = document.createElement('span');
    title.textContent = `${part.title}${part.parts > 1 ? ` (${part.part + 1}/${part.parts})` : ''}`;
    head.append(title);
    if (part.overBudget) {
      const warn = document.createElement('span');
      warn.className = 'badge warn';
      warn.textContent = '예산 초과';
      warn.title = '한 조각이 생성 예산보다 큽니다 (020-04)';
      head.append(warn);
    }
    const full = document.createElement('button');
    full.className = 'small';
    full.textContent = '전체 크기';
    head.append(full);
    const box = document.createElement('div');
    box.className = 'diagram-scroll';
    card.append(head, box);

    const id = `mmd-${++renderCount}`;
    const source = mermaidSource(part.source);
    try {
      await mermaid.parse(source);
      const { svg } = await mermaid.render(id, source);
      box.innerHTML = svg;
      full.addEventListener('click', () => this.openFull(part.title, svg));
    } catch (err) {
      document.getElementById(`d${id}`)?.remove(); // mermaid leaves its error render behind
      box.classList.add('diagram-error');
      const msg = document.createElement('div');
      msg.textContent = `Mermaid 오류: ${(err as Error).message ?? String(err)}`;
      const src = document.createElement('pre');
      src.textContent = source;
      box.append(msg, src);
      full.disabled = true;
    }
    return card;
  }

  private fitAll(): void {
    for (const box of this.host.querySelectorAll<HTMLElement>('.diagram-scroll')) {
      const svg = box.querySelector('svg');
      if (!svg) continue;
      const { w, h } = naturalSize(svg);
      const style = getComputedStyle(box);
      const inner = box.clientWidth - Number.parseFloat(style.paddingLeft) - Number.parseFloat(style.paddingRight);
      const scale = fitScale(w, inner);
      svg.style.maxWidth = 'none';
      svg.style.width = `${w * scale}px`;
      svg.style.height = `${h * scale}px`;
      svg.dataset.scale = scale.toFixed(3);
    }
  }

  private openFull(title: string, svg: string): void {
    this.dialog.replaceChildren();
    const head = document.createElement('div');
    head.className = 'dialog-head';
    const t = document.createElement('strong');
    t.textContent = title;
    const close = document.createElement('button');
    close.textContent = '닫기';
    close.addEventListener('click', () => this.dialog.close());
    head.append(t, close);
    const body = document.createElement('div');
    body.className = 'diagram-full';
    body.innerHTML = svg;
    const el = body.querySelector('svg');
    if (el) {
      const { w, h } = naturalSize(el);
      el.style.maxWidth = 'none';
      el.style.width = `${w}px`;
      el.style.height = `${h}px`;
    }
    this.dialog.append(head, body);
    this.dialog.showModal();
  }
}
