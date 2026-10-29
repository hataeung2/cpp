// 070-06 AC-5 (comparison with the previous run) and the Timings helpers (§2.5).
import { describe, expect, it } from 'vitest';
import type { SpanRow } from '../src/api';
import {
  TimingsPanel, changeText, compareToPrevious, effectiveBuild, formatNs, inlineByLine, loadPrevious, meanNs, mergeRows,
  rowKey, savePrevious, summarizeRun,
} from '../src/timings';

const row = (label: string, count: number, totalNs: number, extra: Partial<SpanRow> = {}): SpanRow => ({
  file: 'lessons/x/main.cpp', line: 10, label, meter: 'wall', count, totalNs, minNs: 1, maxNs: totalNs,
  p50Ns: 1, p95Ns: 1, hist: { loNs: 1, hiNs: totalNs, bins: [count] }, ...extra,
});

class MemoryStorage implements Storage {
  private data = new Map<string, string>();
  get length() { return this.data.size; }
  clear() { this.data.clear(); }
  getItem(key: string) { return this.data.get(key) ?? null; }
  key(i: number) { return [...this.data.keys()][i] ?? null; }
  removeItem(key: string) { this.data.delete(key); }
  setItem(key: string, value: string) { this.data.set(key, value); }
}

class BlockedStorage extends MemoryStorage {
  getItem(): string | null { throw new DOMException('blocked', 'SecurityError'); }
  setItem(): void { throw new DOMException('blocked', 'SecurityError'); }
}

describe('formatNs (020-06 §2.3 rule)', () => {
  it('picks the unit that fits, with three decimals above ns', () => {
    expect(formatNs(999)).toBe('999 ns');
    expect(formatNs(1_500)).toBe('1.500 µs');
    expect(formatNs(1_234_567)).toBe('1.235 ms');
    expect(formatNs(2_500_000_000)).toBe('2.500 s');
    expect(formatNs(0)).toBe('0 ns');
    expect(formatNs(999.6)).toBe('1.000 µs'); // a mean that rounds up to 1000 changes unit
  });
});

describe('effectiveBuild (the runner rule of tools/lessons.py)', () => {
  it('uses the manifest build, else release for long and debug for quick', () => {
    expect(effectiveBuild('long', null)).toBe('release');
    expect(effectiveBuild('quick', null)).toBe('debug');
    expect(effectiveBuild('long', 'debug')).toBe('debug');
    expect(effectiveBuild('quick', 'release')).toBe('release');
  });
});

describe('rows', () => {
  it('merges partial payloads by key and replaces everything on a full one', () => {
    let rows = mergeRows(new Map(), { full: false, rows: [row('a', 1, 10), row('b', 1, 5)], spanLines: 2, lagBytes: 0 });
    rows = mergeRows(rows, { full: false, rows: [row('a', 3, 40)], spanLines: 4, lagBytes: 0 });
    expect([...rows.values()].map((r) => [r.label, r.count])).toEqual([['a', 3], ['b', 1]]);
    rows = mergeRows(rows, { full: true, rows: [row('b', 2, 9)], spanLines: 5, lagBytes: 0 });
    expect([...rows.values()].map((r) => [r.label, r.count])).toEqual([['b', 2]]);
  });

  it('keys on file, line, label and meter (a colon in a label cannot collide)', () => {
    expect(rowKey(row('a:1', 1, 1))).not.toBe(rowKey(row('a', 1, 1, { line: 1 })));
    expect(rowKey(row('a', 1, 1))).not.toBe(rowKey(row('a', 1, 1, { meter: 'cpu' })));
  });

  it('mean is total / count', () => {
    expect(meanNs(row('a', 4, 10))).toBe(2.5);
    expect(meanNs(row('a', 0, 0))).toBe(0);
  });
});

describe('comparison with the previous run (AC-5)', () => {
  const previous = summarizeRun([row('a', 10, 1000), row('b', 1, 50)], 'RelWithDebInfo');

  it('shows the mean change in percent for the same build type', () => {
    // other counts than the previous run (10 spans, mean 100 ns): a total-based change would differ
    const change = compareToPrevious(row('a', 20, 2500), previous, 'RelWithDebInfo');
    expect(change).toEqual({ kind: 'pct', pct: 25 });
    expect(changeText(change)).toBe('+25.0%');
    expect(changeText(compareToPrevious(row('a', 5, 450), previous, 'RelWithDebInfo'))).toBe('−10.0%');
  });

  it('says "빌드 다름" and hides the change when the build type differs', () => {
    const change = compareToPrevious(row('a', 10, 1250), previous, 'Debug');
    expect(change).toEqual({ kind: 'build' });
    expect(changeText(change)).toBe('빌드 다름');
  });

  it('has nothing to compare for a new key, another meter, or no previous run', () => {
    expect(changeText(compareToPrevious(row('new', 1, 5), previous, 'RelWithDebInfo'))).toBe('—');
    expect(compareToPrevious(row('a', 10, 1250, { meter: 'cpu' }), previous, 'RelWithDebInfo')).toEqual({ kind: 'none' });
    expect(compareToPrevious(row('a', 10, 1250), null, 'RelWithDebInfo')).toEqual({ kind: 'none' });
  });

  it('round-trips through storage per lesson', () => {
    const storage = new MemoryStorage();
    expect(savePrevious(storage, 'span_timing', previous)).toBe(true);
    expect(loadPrevious(storage, 'span_timing')).toEqual(previous);
    expect(loadPrevious(storage, 'other')).toBeNull();
  });

  it('works without storage (blocked, broken data): no comparison, no error', () => {
    expect(savePrevious(new BlockedStorage(), 'l', previous)).toBe(false);
    expect(loadPrevious(new BlockedStorage(), 'l')).toBeNull();
    expect(loadPrevious(null, 'l')).toBeNull();
    const broken = new MemoryStorage();
    broken.setItem('atugcc.playground.timings.l', '{not json');
    expect(loadPrevious(broken, 'l')).toBeNull();
    broken.setItem('atugcc.playground.timings.l', '{"buildType":1}');
    expect(loadPrevious(broken, 'l')).toBeNull();
  });
});

describe('inline text per source line (§2.5)', () => {
  it('merges rows on one line with a count sum and a weighted mean', () => {
    const lines = inlineByLine([
      row('a', 3, 3_000_000),                 // 1 ms each
      row('b', 1, 5_000_000),                 // 5 ms, same line, another label
      row('c', 2, 2_000, { line: 20 }),
      row('d', 1, 1, { file: 'lessons/x/other.hpp' }),
    ]);
    expect(lines.get('lessons/x/main.cpp')).toEqual(new Map([[10, '⏱ 2.000 ms avg ×4'], [20, '⏱ 1.000 µs avg ×2']]));
    expect(lines.get('lessons/x/other.hpp')?.get(10)).toBe('⏱ 1 ns avg ×1');
  });
});

describe('TimingsPanel', () => {
  const flush = () => new Promise((resolve) => requestAnimationFrame(() => resolve(null)));

  it('renders one row per key with the mean column and selects the source line on click', async () => {
    const host = document.createElement('div');
    const picked: [string, number][] = [];
    const panel = new TimingsPanel(host, (file, line) => picked.push([file, line]));
    panel.start('t');
    panel.setBuildType('Debug');
    panel.update({ full: false, rows: [row('a', 4, 10_000), row('b', 1, 3, { line: 42 })], spanLines: 5, lagBytes: 0 });
    await flush();
    let rows = [...host.querySelectorAll('tbody tr')];
    expect(rows).toHaveLength(2);
    expect(rows[0].textContent).toContain('2.500 µs'); // mean of "a" (sorted by total, descending)
    (rows[1] as HTMLElement).click();
    expect(picked).toEqual([['lessons/x/main.cpp', 42]]);
    expect(host.querySelector('.timings-notes')?.textContent).toContain('span 5개');
    // the selection survives the next live update (the table is rebuilt)
    panel.update({ full: false, rows: [row('a', 5, 12_000)], spanLines: 6, lagBytes: 0 });
    await flush();
    rows = [...host.querySelectorAll('tbody tr')];
    expect(rows[1].classList.contains('selected')).toBe(true);
    expect(rows[1].textContent).toContain('main.cpp:42');
  });

  it('leaves out the comparison column when storage is blocked', async () => {
    const host = document.createElement('div');
    const panel = new TimingsPanel(host, () => {});
    const original = Object.getOwnPropertyDescriptor(window, 'localStorage')!;
    Object.defineProperty(window, 'localStorage', {
      configurable: true,
      get: () => {
        throw new DOMException('blocked', 'SecurityError');
      },
    });
    try {
      panel.start('t');
      panel.update({ full: false, rows: [row('a', 1, 1)], spanLines: 1, lagBytes: 0 });
      await flush();
      expect([...host.querySelectorAll('th')].map((th) => th.textContent)).not.toContain('이전 대비');
      expect(host.querySelectorAll('tbody td')).toHaveLength(10);
    } finally {
      Object.defineProperty(window, 'localStorage', original);
    }
  });

  it('shows the lag while the server is behind', async () => {
    const host = document.createElement('div');
    const panel = new TimingsPanel(host, () => {});
    panel.start('t');
    panel.update({ full: false, rows: [row('a', 1, 1)], spanLines: 1, lagBytes: 3 << 20 });
    await flush();
    expect(host.querySelector('.timings-notes')?.textContent).toContain('집계 지연 3.0 MiB');
  });
});
