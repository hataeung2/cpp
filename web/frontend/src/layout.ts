// Column widths of the page (spec 070-19 Assumption 8): drag bars between sidebar | editor | right panel.
// The arithmetic is DOM-free (`clampLayout`, `moveSidebar`, `moveRight`, `parseLayout`) so it can be tested.

export const LAYOUT_KEY = 'atugcc.layout';

/** Smallest widths in px (Assumption 8). */
export const MIN_SIDEBAR = 160;
export const MIN_EDITOR = 360;
export const MIN_RIGHT = 280;
/** Step of the arrow keys on a focused bar. */
export const KEY_STEP = 16;

/** What the user asked for: the sidebar in px, the right panel as a share of the page width. */
export interface Want {
  sidebar: number;
  rightRatio: number;
}
/** Widths in px actually used; the editor takes the rest. */
export interface Layout {
  sidebar: number;
  right: number;
}

export const DEFAULT_WANT: Want = { sidebar: 260, rightRatio: 0.42 };

/** Widths for a page `viewport` px wide. When the page is too narrow, the right panel shrinks first, then the sidebar. */
export function clampLayout(viewport: number, want: Want): Layout {
  let sidebar = Math.max(MIN_SIDEBAR, Math.round(want.sidebar));
  let right = Math.max(MIN_RIGHT, Math.round(want.rightRatio * viewport));
  const excess = sidebar + right + MIN_EDITOR - viewport;
  if (excess > 0) {
    const fromRight = Math.min(excess, right - MIN_RIGHT);
    right -= fromRight;
    sidebar -= Math.min(excess - fromRight, sidebar - MIN_SIDEBAR);
  }
  return { sidebar, right };
}

/** The sidebar bar moved to `px` from the page's left edge: only the sidebar and the editor change. */
export function moveSidebar(viewport: number, current: Layout, px: number): Layout {
  const max = Math.max(MIN_SIDEBAR, viewport - current.right - MIN_EDITOR);
  return { ...current, sidebar: Math.round(Math.min(Math.max(px, MIN_SIDEBAR), max)) };
}

/** The right bar moved to `px` from the page's left edge: only the editor and the right panel change. */
export function moveRight(viewport: number, current: Layout, px: number): Layout {
  const max = Math.max(MIN_RIGHT, viewport - current.sidebar - MIN_EDITOR);
  return { ...current, right: Math.round(Math.min(Math.max(viewport - px, MIN_RIGHT), max)) };
}

export function wantOf(viewport: number, layout: Layout): Want {
  return { sidebar: layout.sidebar, rightRatio: layout.right / viewport };
}

/** Stored text to a request; anything broken or out of range gives the default. */
export function parseLayout(raw: string | null): Want {
  try {
    const data = JSON.parse(raw ?? '') as Partial<Want> | null;
    const sidebar = data?.sidebar;
    const ratio = data?.rightRatio;
    if (typeof sidebar !== 'number' || typeof ratio !== 'number') return DEFAULT_WANT;
    if (!Number.isFinite(sidebar) || !Number.isFinite(ratio)) return DEFAULT_WANT;
    if (sidebar < MIN_SIDEBAR || sidebar > 2000 || ratio < 0.1 || ratio > 0.8) return DEFAULT_WANT;
    return { sidebar, rightRatio: ratio };
  } catch {
    return DEFAULT_WANT;
  }
}

export function loadLayout(): Want {
  try {
    return parseLayout(localStorage.getItem(LAYOUT_KEY));
  } catch {
    return DEFAULT_WANT; // blocked storage
  }
}

export function saveLayout(want: Want): void {
  try {
    localStorage.setItem(LAYOUT_KEY, JSON.stringify(want));
  } catch {
    // blocked storage: the widths last until the page closes
  }
}

/** Connects the two bars to the CSS variables `--sidebar-w` and `--right-w` of `root`. */
export class ColumnLayout {
  private want = loadLayout();
  private layout: Layout = { sidebar: 0, right: 0 };

  constructor(
    private readonly root: HTMLElement,
    private readonly sidebarBar: HTMLElement,
    private readonly rightBar: HTMLElement,
  ) {
    this.bind(sidebarBar, (px) => moveSidebar(this.viewport(), this.layout, px), 'sidebar');
    this.bind(rightBar, (px) => moveRight(this.viewport(), this.layout, px), 'right');
    window.addEventListener('resize', () => this.apply());
    this.apply();
  }

  private viewport(): number {
    return this.root.clientWidth;
  }

  /** Current widths, for checks and screenshots. */
  widths(): Layout {
    return this.layout;
  }

  private apply(): void {
    const viewport = this.viewport();
    if (viewport <= 0) return;
    this.layout = clampLayout(viewport, this.want);
    this.root.style.setProperty('--sidebar-w', `${this.layout.sidebar}px`);
    this.root.style.setProperty('--right-w', `${this.layout.right}px`);
    this.describe(this.sidebarBar, this.layout.sidebar, MIN_SIDEBAR, viewport - this.layout.right - MIN_EDITOR);
    this.describe(this.rightBar, this.layout.right, MIN_RIGHT, viewport - this.layout.sidebar - MIN_EDITOR);
  }

  private describe(bar: HTMLElement, now: number, min: number, max: number): void {
    bar.setAttribute('aria-valuenow', String(now));
    bar.setAttribute('aria-valuemin', String(min));
    bar.setAttribute('aria-valuemax', String(Math.max(min, max)));
  }

  /** The user chose these widths: remember them. */
  private choose(layout: Layout): void {
    this.layout = layout;
    this.want = wantOf(this.viewport(), layout);
    saveLayout(this.want);
    this.apply();
  }

  private bind(bar: HTMLElement, move: (px: number) => Layout, side: 'sidebar' | 'right'): void {
    const edge = () => (side === 'sidebar' ? this.layout.sidebar : this.viewport() - this.layout.right);
    bar.addEventListener('pointerdown', (ev) => {
      if (ev.button !== 0) return;
      ev.preventDefault();
      bar.setPointerCapture(ev.pointerId);
      bar.classList.add('dragging');
      const left = this.root.getBoundingClientRect().left;
      const onMove = (e: PointerEvent) => this.choose(move(e.clientX - left));
      const stop = () => {
        bar.classList.remove('dragging');
        bar.removeEventListener('pointermove', onMove);
        bar.removeEventListener('pointerup', stop);
        bar.removeEventListener('pointercancel', stop);
        if (bar.hasPointerCapture(ev.pointerId)) bar.releasePointerCapture(ev.pointerId);
      };
      bar.addEventListener('pointermove', onMove);
      bar.addEventListener('pointerup', stop);
      bar.addEventListener('pointercancel', stop);
    });
    const reset = () => {
      const viewport = this.viewport();
      const normal = clampLayout(viewport, DEFAULT_WANT);
      this.choose(side === 'sidebar' ? moveSidebar(viewport, this.layout, normal.sidebar) : moveRight(viewport, this.layout, viewport - normal.right));
    };
    bar.addEventListener('keydown', (ev) => {
      if (ev.key === 'Enter') {
        ev.preventDefault();
        reset(); // the keyboard counterpart of the double click
        return;
      }
      const step = ev.key === 'ArrowLeft' ? -KEY_STEP : ev.key === 'ArrowRight' ? KEY_STEP : 0;
      if (!step) return;
      ev.preventDefault();
      this.choose(move(edge() + step));
    });
    bar.addEventListener('dblclick', reset);
  }
}
