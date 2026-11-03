// 070-10 i18n tests: AC-7, AC-8 (blocked storage), Assumptions 9, 10, §4. The README choice (Assumption 12) is checked in the browser (AC-8).
// @ts-ignore
import fs from 'node:fs';
// @ts-ignore
import path from 'node:path';
// @ts-ignore
import { fileURLToPath } from 'node:url';
import { afterAll, afterEach, describe, expect, it, vi } from 'vitest';
import {
  LANG_KEY,
  applyStatic,
  initialLang,
  lang,
  localized,
  onLangChange,
  setLang,
  t,
  type MessageKey,
} from '../src/i18n';

const HANGUL_RE = /[\uAC00-\uD7A3\u1100-\u11FF\u3131-\u318E]/;
const frontendDir = path.resolve(fileURLToPath(import.meta.url), '../..');

afterEach(() => {
  vi.unstubAllGlobals();
  try {
    localStorage.clear();
  } catch {
    /* ignore if storage was blocked */
  }
  setLang('ko');
});

afterAll(() => {
  vi.unstubAllGlobals();
  try {
    localStorage.clear();
  } catch {
    /* ignore if storage was blocked */
  }
  setLang('ko');
});

describe('i18n', () => {
  it('scans frontend src files and index.html for Hangul characters (AC-7)', () => {
    const srcDir = path.join(frontendDir, 'src');
    const indexHtml = path.join(frontendDir, 'index.html');
    const tsFiles: string[] = fs
      .readdirSync(srcDir)
      .filter((file: string) => file.endsWith('.ts') && file !== 'i18n.ts')
      .map((file: string) => path.join(srcDir, file));
    const allFiles = [...tsFiles, indexHtml];

    expect(allFiles.length).toBeGreaterThanOrEqual(10);

    for (const file of allFiles) {
      const content = fs.readFileSync(file, 'utf8');
      const lines = content.split('\n');
      for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        if (HANGUL_RE.test(line)) {
          expect.fail(`${file}:${i + 1} contains Hangul: ${line.trim()}`);
        }
      }
    }
  });

  it('verifies that ko and en dictionaries have the same keys and placeholders', () => {
    const i18nPath = path.join(frontendDir, 'src/i18n.ts');
    const i18nContent: string = fs.readFileSync(i18nPath, 'utf8');
    const koBlockMatch = i18nContent.match(/const ko = \{([\s\S]*?)\} as const;/);
    expect(koBlockMatch).not.toBeNull();

    const enBlockMatch = i18nContent.match(/const en: Record<keyof typeof ko, string> = \{([\s\S]*?)\n\};/);
    expect(enBlockMatch).not.toBeNull();
    const keysOf = (block: string) => [...block.matchAll(/^\s*'([a-zA-Z]+\.[a-zA-Z0-9]+)'\s*:/gm)].map((m) => m[1]);
    const keys = keysOf(koBlockMatch![1]) as MessageKey[];
    // the regex must see every entry: compare with the number of entry lines, and the two blocks with each other
    expect(keys.length).toBe(koBlockMatch![1].split('\n').filter((l) => /^\s*'/.test(l)).length);
    expect(new Set(keysOf(enBlockMatch![1]))).toEqual(new Set(keys));
    expect(keys.length).toBeGreaterThan(50);

    const extractPlaceholders = (text: string): Set<string> => {
      const matches = [...text.matchAll(/\{([a-zA-Z0-9_]+)\}/g)];
      return new Set(matches.map((m) => m[1]));
    };

    for (const key of keys) {
      setLang('ko');
      const koText = t(key);
      expect(koText.length).toBeGreaterThan(0);

      setLang('en');
      const enText = t(key);
      expect(enText.length).toBeGreaterThan(0);

      if (enText === koText) {
        if (key === 'lang.toKorean') {
          expect(enText).toBe('한');
        } else {
          expect(HANGUL_RE.test(koText)).toBe(false);
        }
      } else {
        expect(enText).not.toBe('');
      }

      const koPlaceholders = extractPlaceholders(koText);
      const enPlaceholders = extractPlaceholders(enText);
      expect(enPlaceholders).toEqual(koPlaceholders);
    }
  });

  it('interpolates t() placeholders and preserves unsupplied ones', () => {
    setLang('ko');
    expect(t('search.count', { lessons: 2, units: 1 })).toBe('레슨 2 · 유닛 1');
    expect(t('search.count', {})).toBe('레슨 {lessons} · 유닛 {units}');

    setLang('en');
    expect(t('search.count', { lessons: 2, units: 1 })).toBe('Lessons 2 · Units 1');
    expect(t('search.count', {})).toBe('Lessons {lessons} · Units {units}');
  });

  it('returns localized text with appropriate fallback flag', () => {
    setLang('ko');
    expect(localized('한국어', 'English')).toEqual({ text: '한국어', fallback: false });
    expect(localized('한국어', null)).toEqual({ text: '한국어', fallback: false });
    expect(localized('한국어', '')).toEqual({ text: '한국어', fallback: false });

    setLang('en');
    expect(localized('한국어', 'English')).toEqual({ text: 'English', fallback: false });
    expect(localized('한국어', null)).toEqual({ text: '한국어', fallback: true });
    expect(localized('한국어', '')).toEqual({ text: '한국어', fallback: true });
    expect(localized('한국어', '   ')).toEqual({ text: '한국어', fallback: true });
  });

  it('determines initialLang from stored preference, browser language, or storage errors', () => {
    expect(initialLang(() => 'en', 'ko-KR')).toBe('en');
    expect(initialLang(() => 'ko', 'en-US')).toBe('ko');
    expect(initialLang(() => null, 'ko-KR')).toBe('ko');
    expect(initialLang(() => null, 'en-US')).toBe('en');
    expect(initialLang(() => null, '')).toBe('en');
    expect(initialLang(() => 'fr', 'ko-KR')).toBe('ko');
    expect(initialLang(() => 'fr', 'en-US')).toBe('en');

    const throwingRead = (): string | null => {
      throw new Error('blocked storage');
    };
    expect(initialLang(throwingRead, 'ko-KR')).toBe('ko');
    expect(initialLang(throwingRead, 'en-US')).toBe('en');
  });

  it('handles setLang() gracefully when storage is blocked (AC-8)', () => {
    setLang('ko');

    const blockedStorage = {
      getItem: () => {
        throw new DOMException('blocked', 'SecurityError');
      },
      setItem: () => {
        throw new DOMException('blocked', 'SecurityError');
      },
      removeItem: () => {
        throw new DOMException('blocked', 'SecurityError');
      },
      clear: () => {
        throw new DOMException('blocked', 'SecurityError');
      },
      key: () => {
        throw new DOMException('blocked', 'SecurityError');
      },
      length: 0,
    };
    vi.stubGlobal('localStorage', blockedStorage);

    const listener = vi.fn();
    onLangChange(listener);

    expect(() => setLang('en')).not.toThrow();
    expect(lang()).toBe('en');
    expect(document.documentElement.lang).toBe('en');
    expect(listener).toHaveBeenCalledTimes(1);
    expect(listener).toHaveBeenCalledWith('en');
  });

  it('handles setLang() when reading window.localStorage itself throws (blocked site data)', () => {
    const original = Object.getOwnPropertyDescriptor(window, 'localStorage');
    Object.defineProperty(window, 'localStorage', {
      configurable: true,
      get() {
        throw new DOMException('blocked', 'SecurityError');
      },
    });
    try {
      expect(() => setLang('en')).not.toThrow();
      expect(lang()).toBe('en');
      expect(initialLang(() => localStorage.getItem(LANG_KEY), 'ko-KR')).toBe('ko');
    } finally {
      if (original) Object.defineProperty(window, 'localStorage', original);
    }
  });

  it('persists selected language in localStorage under LANG_KEY', () => {
    setLang('en');
    expect(localStorage.getItem(LANG_KEY)).toBe('en');
    expect(localStorage.getItem('atugcc.lang')).toBe('en');

    setLang('ko');
    expect(localStorage.getItem(LANG_KEY)).toBe('ko');
    expect(localStorage.getItem('atugcc.lang')).toBe('ko');
  });

  it('applies translations to DOM fragment via applyStatic()', () => {
    const root = document.createElement('div');
    root.innerHTML = `
      <span data-i18n="top.intro">원래 소개</span>
      <button data-i18n-title="top.themeTitle" title="원래 테마">테마</button>
      <input data-i18n-placeholder="search.placeholder" placeholder="원래 검색" />
      <span data-i18n="unknown.nonexistent.key">원래 텍스트 유지</span>
    `;

    setLang('en');
    document.documentElement.lang = 'xx'; // so the check below sees applyStatic's own update
    applyStatic(root);

    const textEl = root.querySelector('[data-i18n="top.intro"]')!;
    const titleEl = root.querySelector('[data-i18n-title="top.themeTitle"]')! as HTMLButtonElement;
    const placeholderEl = root.querySelector(
      '[data-i18n-placeholder="search.placeholder"]',
    )! as HTMLInputElement;
    const unknownEl = root.querySelector('[data-i18n="unknown.nonexistent.key"]')!;

    expect(textEl.textContent).toBe('ⓘ About');
    expect(titleEl.title).toBe('Toggle light/dark theme');
    expect(placeholderEl.placeholder).toBe('Search lessons, features (/)');
    expect(unknownEl.textContent).toBe('원래 텍스트 유지');
    expect(document.documentElement.lang).toBe('en');
  });
});
