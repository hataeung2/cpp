// 070-19 AC-2 (stored wrap choice), AC-4 (column widths): the DOM-free arithmetic and blocked storage.
import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  DEFAULT_WANT,
  MIN_EDITOR,
  MIN_RIGHT,
  MIN_SIDEBAR,
  clampLayout,
  loadLayout,
  moveRight,
  moveSidebar,
  parseLayout,
  saveLayout,
  wantOf,
} from '../src/layout';
import { EDITOR_WRAP_KEY, OUTPUT_WRAP_KEY, loadWrap, saveWrap } from '../src/wrap';

afterEach(() => {
  vi.unstubAllGlobals();
  localStorage.clear();
});

const blockedStorage = () =>
  vi.stubGlobal('localStorage', {
    getItem: () => {
      throw new Error('blocked');
    },
    setItem: () => {
      throw new Error('blocked');
    },
  });

describe('clampLayout', () => {
  it('uses the request when everything fits', () => {
    expect(clampLayout(1600, { sidebar: 300, rightRatio: 0.3 })).toEqual({ sidebar: 300, right: 480 });
  });

  it('keeps the editor at its minimum by shrinking the right panel first', () => {
    const l = clampLayout(1024, DEFAULT_WANT); // 260 + 430 leaves 334 < 360
    expect(l).toEqual({ sidebar: 260, right: 404 });
    expect(1024 - l.sidebar - l.right).toBe(MIN_EDITOR);
  });

  it('shrinks the sidebar only after the right panel reached its minimum', () => {
    const l = clampLayout(900, { sidebar: 400, rightRatio: 0.5 });
    expect(l.right).toBe(MIN_RIGHT);
    expect(l.sidebar).toBe(900 - MIN_RIGHT - MIN_EDITOR);
  });

  it('never goes below the minimum widths, even on a page narrower than their sum', () => {
    expect(clampLayout(500, DEFAULT_WANT)).toEqual({ sidebar: MIN_SIDEBAR, right: MIN_RIGHT });
  });

  it('raises a too small request to the minimum', () => {
    expect(clampLayout(1600, { sidebar: 10, rightRatio: 0.05 })).toEqual({ sidebar: MIN_SIDEBAR, right: MIN_RIGHT });
  });

  it('gives the wanted widths back when the window grows again', () => {
    const want = { sidebar: 300, rightRatio: 0.4 };
    expect(clampLayout(920, want).right).toBe(MIN_RIGHT);
    expect(clampLayout(1600, want)).toEqual({ sidebar: 300, right: 640 });
  });
});

describe('moving a bar', () => {
  const now = { sidebar: 260, right: 400 };

  it('the sidebar bar changes only the sidebar and stops at the minimums', () => {
    expect(moveSidebar(1280, now, 300)).toEqual({ sidebar: 300, right: 400 });
    expect(moveSidebar(1280, now, 10).sidebar).toBe(MIN_SIDEBAR);
    expect(moveSidebar(1280, now, 1200).sidebar).toBe(1280 - 400 - MIN_EDITOR);
  });

  it('the right bar changes only the right panel and stops at the minimums', () => {
    expect(moveRight(1280, now, 1000)).toEqual({ sidebar: 260, right: 280 });
    expect(moveRight(1280, now, 1100).right).toBe(MIN_RIGHT);
    expect(moveRight(1280, now, 0).right).toBe(1280 - 260 - MIN_EDITOR);
  });

  it('a page too narrow for the maximum keeps the minimum', () => {
    expect(moveSidebar(600, { sidebar: 160, right: 280 }, 500).sidebar).toBe(MIN_SIDEBAR);
  });

  it('turns a layout into a request that gives the same widths back', () => {
    const l = { sidebar: 300, right: 500 };
    expect(clampLayout(1280, wantOf(1280, l))).toEqual(l);
  });
});

describe('parseLayout', () => {
  it('reads a stored request', () => {
    expect(parseLayout('{"sidebar":300,"rightRatio":0.35}')).toEqual({ sidebar: 300, rightRatio: 0.35 });
  });

  it.each([
    ['nothing', null],
    ['not JSON', 'abc'],
    ['null', 'null'],
    ['missing field', '{"sidebar":300}'],
    ['text numbers', '{"sidebar":"300","rightRatio":"0.3"}'],
    ['sidebar too small', '{"sidebar":5,"rightRatio":0.3}'],
    ['sidebar too large', '{"sidebar":99999,"rightRatio":0.3}'],
    ['ratio too large', '{"sidebar":300,"rightRatio":3}'],
    ['ratio negative', '{"sidebar":300,"rightRatio":-0.2}'],
  ])('falls back to the default for %s', (_name, raw) => {
    expect(parseLayout(raw)).toEqual(DEFAULT_WANT);
  });

  it('stores and reads back a choice, and ignores a blocked storage', () => {
    saveLayout({ sidebar: 300, rightRatio: 0.35 });
    expect(localStorage.getItem('atugcc.layout')).not.toBeNull();
    expect(loadLayout()).toEqual({ sidebar: 300, rightRatio: 0.35 });
    blockedStorage();
    expect(loadLayout()).toEqual(DEFAULT_WANT);
    expect(() => saveLayout({ sidebar: 300, rightRatio: 0.35 })).not.toThrow();
  });
});

describe('wrap choice', () => {
  it('is on by default and remembers off and on', () => {
    expect(loadWrap(EDITOR_WRAP_KEY)).toBe(true);
    saveWrap(EDITOR_WRAP_KEY, false);
    expect(localStorage.getItem('atugcc.wrap.editor')).toBe('off');
    expect(loadWrap(EDITOR_WRAP_KEY)).toBe(false);
    saveWrap(EDITOR_WRAP_KEY, true);
    expect(loadWrap(EDITOR_WRAP_KEY)).toBe(true);
  });

  it('keeps the Output choice under its own key', () => {
    saveWrap(OUTPUT_WRAP_KEY, false);
    expect(localStorage.getItem('atugcc.wrap.output')).toBe('off');
    expect(loadWrap(EDITOR_WRAP_KEY)).toBe(true);
  });

  it('turns an unknown stored value into the default', () => {
    localStorage.setItem(EDITOR_WRAP_KEY, 'maybe');
    expect(loadWrap(EDITOR_WRAP_KEY)).toBe(true);
  });

  it('survives blocked storage: default on, no throw', () => {
    blockedStorage();
    expect(loadWrap(EDITOR_WRAP_KEY)).toBe(true);
    expect(() => saveWrap(EDITOR_WRAP_KEY, false)).not.toThrow();
  });
});
