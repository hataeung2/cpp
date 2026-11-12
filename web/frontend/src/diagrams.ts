// Diagrams panel: the Mermaid parts a run's Tracers wrote at destruction (020-05 `diagram` lines),
// and the step-by-step replay of one tracer (spec 070-07: bar, folded earlier Sequence parts).
// Viewer policy (diagrams.md §3): natural size, never shrunk below 80 %; a wider part scrolls
// inside its own container; text 14 px or more; every part has a full-size view.

import type { DiagramLine, DoneData, TraceEvent } from './api';
import { describe } from './events';
import { t } from './i18n';
import { REPLAY_DEBOUNCE_MS, ReplayCache, ReplayState, foldedParts, replayTracers } from './replay';

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

/** What the replay bar needs from the page (spec 070-07). */
export interface ReplayHooks {
  /** The Mermaid parts of `tracer` drawn up to `seq` with the last event marked. */
  fetchParts(tracer: number, seq: number): Promise<DiagramLine[]>;
  /** The cursor moved to `event`: select its Events row and show its source line. */
  onStep(event: TraceEvent): void;
}

export class DiagramsPanel {
  private parts: DiagramLine[] = [];
  private note = '';
  private dark = false;
  private generation = 0; // a newer draw() or clear() makes an older draw stop
  private readonly observer = new ResizeObserver(() => this.fitAll());
  private readonly bar = document.createElement('div');
  private readonly body = document.createElement('div');
  private replay = new ReplayState([]);
  private readonly cache = new ReplayCache();
  private debounce: number | undefined;
  private replayMax = 0;
  private slider: HTMLInputElement | null = null;
  private countEl: HTMLElement | null = null;
  private whatEl: HTMLElement | null = null;

  constructor(
    private readonly host: HTMLElement,
    private readonly dialog: HTMLDialogElement,
    private readonly hooks?: ReplayHooks,
  ) {
    this.bar.className = 'replay-bar';
    this.bar.hidden = true;
    this.host.tabIndex = 0; // ←/→ step the replay while the panel has the focus
    this.host.replaceChildren(this.bar, this.body);
    this.host.addEventListener('keydown', (ev) => this.onKey(ev));
    this.observer.observe(host);
  }

  clear(): void {
    this.generation++;
    window.clearTimeout(this.debounce);
    this.parts = [];
    this.note = '';
    this.replay = new ReplayState([]);
    this.cache.clear();
    this.bar.hidden = true;
    this.bar.replaceChildren();
    this.body.replaceChildren();
  }

  setTheme(dark: boolean): void {
    this.dark = dark;
    this.cache.clear(); // the sources do not change, but the drawing is redone with the new theme
    if (this.replay.current) void this.drawReplay();
    else if (this.parts.length) void this.draw();
  }

  /** Show the diagrams of a finished run; `events` are the Events tab's events (the replay steps). */
  show(done: DoneData, events: readonly TraceEvent[] = []): void {
    this.parts = done.diagrams.filter((d) => d.backend === 'mermaid');
    const run = done.run;
    const abnormal = !run || run.timedOut || run.stopped || run.signal !== null;
    this.note = this.parts.length
      ? ''
      : abnormal
        ? t('diagrams.abnormal')
        : t('diagrams.none');
    this.replay = new ReplayState(replayTracers(done, events));
    this.replayMax = done.replay?.max ?? 0;
    this.renderBar();
    void this.draw();
  }

  /** An Events row was clicked: the replay (if on) follows to that event. */
  goToSeq(seq: number): void {
    if (this.replay.goToSeq(seq)) this.stepped(false);
  }

  // --- replay bar ---------------------------------------------------------------------------
  private renderBar(): void {
    this.bar.replaceChildren();
    this.slider = this.countEl = this.whatEl = null;
    const replay = this.replay;
    this.bar.hidden = !replay.available && replay.unavailable.length === 0;
    if (this.bar.hidden) return;

    const row = document.createElement('div');
    row.className = 'replay-row';
    if (replay.available) {
      const toggle = document.createElement('button');
      toggle.className = 'small';
      toggle.textContent = t(replay.active ? 'replay.off' : 'replay.on');
      toggle.title = t('replay.toggleTitle');
      toggle.addEventListener('click', () => {
        replay.setActive(!replay.active);
        this.renderBar();
        if (replay.active) this.stepped(true);
        else void this.draw();
      });
      row.append(toggle);
    }
    const current = replay.current;
    if (current) {
      if (replay.playable.length > 1) {
        const select = document.createElement('select');
        select.title = t('replay.tracerTitle');
        for (const tr of replay.playable) {
          const option = document.createElement('option');
          option.value = String(tr.tracer);
          option.textContent = `Tracer #${tr.tracer}`;
          option.selected = tr.tracer === current.tracer;
          select.append(option);
        }
        select.addEventListener('change', () => {
          if (replay.selectTracer(Number(select.value))) this.stepped(true);
        });
        row.append(select);
      }
      const button = (label: string, title: string, move: () => boolean) => {
        const b = document.createElement('button');
        b.className = 'small';
        b.textContent = label;
        b.title = title;
        b.addEventListener('click', () => {
          if (move()) this.stepped(true, false);
        });
        return b;
      };
      row.append(
        button('⏮', t('replay.first'), () => replay.first()),
        button('◀', t('replay.prev'), () => replay.prev()),
        button('▶', t('replay.next'), () => replay.next()),
        button('⏭', t('replay.last'), () => replay.last()),
      );
      const slider = document.createElement('input');
      slider.type = 'range';
      slider.className = 'replay-slider';
      slider.min = '0';
      slider.max = String(current.total - 1);
      slider.value = String(current.index);
      slider.addEventListener('input', () => {
        if (replay.setStep(Number(slider.value))) this.stepped(true, false);
      });
      const count = document.createElement('span');
      count.className = 'replay-count';
      row.append(slider, count);
      this.slider = slider;
      this.countEl = count;
    }
    this.bar.append(row);

    if (current) {
      const what = document.createElement('div');
      what.className = 'replay-event muted';
      this.bar.append(what);
      this.whatEl = what;
      this.updateBar();
    }
    for (const tr of replay.unavailable) {
      const why = document.createElement('div');
      why.className = 'replay-why muted';
      why.textContent = t(tr.off === 'tooMany' ? 'replay.tooMany' : 'replay.truncated', {
        tracer: tr.tracer,
        count: tr.count,
        max: this.replayMax,
      });
      this.bar.append(why);
    }
  }

  /** Slider, `k / n` and the event line follow the cursor; the controls stay, so focus and a slider drag survive a step. */
  private updateBar(): void {
    const current = this.replay.current;
    if (!current || !this.slider || !this.countEl || !this.whatEl) return;
    this.slider.value = String(current.index);
    this.countEl.textContent = t('replay.step', { k: current.index + 1, n: current.total });
    this.whatEl.textContent = `seq ${current.event.seq} · ${current.event.kind} · ${describe(current.event)} · ${current.event.file}:${current.event.line}`;
  }

  /**
   * The cursor moved: refresh the bar, tell the page, and draw (debounced). `notify` false: the move came from
   * the Events tab. `rebuild` false: only the values changed, the controls stay (a tracer switch rebuilds them).
   */
  private stepped(notify: boolean, rebuild = true): void {
    if (rebuild) this.renderBar();
    else this.updateBar();
    const current = this.replay.current;
    if (!current) return;
    if (notify) this.hooks?.onStep(current.event);
    window.clearTimeout(this.debounce);
    this.debounce = window.setTimeout(() => void this.drawReplay(), REPLAY_DEBOUNCE_MS);
  }

  private onKey(ev: KeyboardEvent): void {
    const target = ev.target;
    if (target instanceof HTMLInputElement || target instanceof HTMLSelectElement) return; // they keep their own arrows
    if (!this.replay.current || ev.altKey || ev.ctrlKey || ev.metaKey || ev.shiftKey) return;
    const moved = ev.key === 'ArrowLeft' ? this.replay.prev() : ev.key === 'ArrowRight' ? this.replay.next() : null;
    if (moved === null) return;
    ev.preventDefault();
    if (moved) this.stepped(true, false);
  }

  private async drawReplay(): Promise<void> {
    const current = this.replay.current;
    if (!current || !this.hooks) return;
    const generation = ++this.generation;
    let parts = this.cache.get(current.tracer, current.event.seq);
    if (!parts) {
      try {
        parts = await this.hooks.fetchParts(current.tracer, current.event.seq);
      } catch (err) {
        if (generation !== this.generation) return;
        this.body.replaceChildren();
        const p = document.createElement('p');
        p.className = 'diagram-error';
        p.textContent = t('replay.error', { error: (err as Error).message ?? String(err) });
        this.body.append(p);
        return;
      }
      if (generation !== this.generation) return; // a newer step or a new run: keep the cache clean of old results
      this.cache.set(current.tracer, current.event.seq, parts);
    }
    if (generation !== this.generation) return;
    const mermaid = await loadMermaid(this.dark);
    this.body.replaceChildren();
    const h = document.createElement('h3');
    h.textContent = `Tracer #${current.tracer}`;
    this.body.append(h);
    const folded = foldedParts(parts);
    for (const [i, part] of parts.entries()) {
      const card = await this.card(mermaid, part);
      if (generation !== this.generation) return;
      if (folded[i]) {
        const details = document.createElement('details');
        details.className = 'replay-fold';
        const summary = document.createElement('summary');
        summary.textContent = `${part.title} (${part.part + 1}/${part.parts})`;
        details.append(summary, card);
        this.body.append(details);
      } else {
        this.body.append(card);
      }
    }
    this.fitAll();
  }

  private async draw(): Promise<void> {
    const generation = ++this.generation;
    this.body.replaceChildren();
    if (this.note) {
      const p = document.createElement('p');
      p.className = 'muted';
      p.textContent = this.note;
      this.body.append(p);
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
        this.body.append(h);
      }
      const card = await this.card(mermaid, part);
      if (generation !== this.generation) return;
      this.body.append(card);
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
      warn.textContent = t('diagrams.overBudget');
      warn.title = t('diagrams.overBudgetTitle');
      head.append(warn);
    }
    const full = document.createElement('button');
    full.className = 'small';
    full.textContent = t('diagrams.fullSize');
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
      msg.textContent = t('diagrams.error', { error: (err as Error).message ?? String(err) });
      const src = document.createElement('pre');
      src.textContent = source;
      box.append(msg, src);
      full.disabled = true;
    }
    return card;
  }

  private fitAll(): void {
    for (const box of this.body.querySelectorAll<HTMLElement>('.diagram-scroll')) {
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
    const titleEl = document.createElement('strong');
    titleEl.textContent = title;
    const close = document.createElement('button');
    close.textContent = t('diagrams.close');
    close.addEventListener('click', () => this.dialog.close());
    head.append(titleEl, close);
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
