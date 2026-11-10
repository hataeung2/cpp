// Tests for practice workspace helpers and API calls (spec 070-16 U7).
import { afterEach, describe, expect, it, vi } from 'vitest';
import { api } from '../src/api';
import {
  MODE_KEY,
  changedFiles,
  isPracticePath,
  loadMode,
  practiceFiles,
  saveMode,
  stateMap,
  toOrigin,
  toPractice,
  type PracticeStatus,
} from '../src/practice';

afterEach(() => {
  vi.unstubAllGlobals();
  try {
    localStorage.clear();
  } catch {
    // Ignore storage errors if blocked
  }
});

describe('practice mode storage (loadMode / saveMode)', () => {
  it('returns practice by default when localStorage is empty', () => {
    expect(loadMode()).toBe('practice');
  });

  it("returns 'original' when stored value is 'original'", () => {
    localStorage.setItem(MODE_KEY, 'original');
    expect(loadMode()).toBe('original');
  });

  it("returns 'practice' for unknown or empty values", () => {
    localStorage.setItem(MODE_KEY, 'custom');
    expect(loadMode()).toBe('practice');

    localStorage.setItem(MODE_KEY, '');
    expect(loadMode()).toBe('practice');

    localStorage.setItem(MODE_KEY, 'practice');
    expect(loadMode()).toBe('practice');
  });

  it("returns 'practice' when getItem throws", () => {
    vi.stubGlobal('localStorage', {
      getItem: () => {
        throw new DOMException('storage blocked', 'SecurityError');
      },
      setItem: () => {},
    });
    expect(loadMode()).toBe('practice');
  });

  it('saves mode to localStorage', () => {
    saveMode('original');
    expect(localStorage.getItem(MODE_KEY)).toBe('original');

    saveMode('practice');
    expect(localStorage.getItem(MODE_KEY)).toBe('practice');
  });

  it('swallows errors when setItem throws', () => {
    vi.stubGlobal('localStorage', {
      getItem: () => null,
      setItem: () => {
        throw new DOMException('storage blocked', 'SecurityError');
      },
    });
    expect(() => saveMode('original')).not.toThrow();
  });
});

describe('path conversions (toPractice, toOrigin, isPracticePath)', () => {
  it('maps lessons/ paths to practice/lessons/ paths', () => {
    expect(toPractice('lessons/tracks/core/hello/main.cpp')).toBe(
      'practice/lessons/tracks/core/hello/main.cpp'
    );
  });

  it('leaves include/ and other non-lessons paths unchanged', () => {
    expect(toPractice('include/tracer/tracer.hpp')).toBe('include/tracer/tracer.hpp');
    expect(toPractice('tests/test_main.cpp')).toBe('tests/test_main.cpp');
  });

  it('leaves already-mapped practice paths unchanged', () => {
    expect(toPractice('practice/lessons/tracks/core/hello/main.cpp')).toBe(
      'practice/lessons/tracks/core/hello/main.cpp'
    );
  });

  it('maps practice/lessons/ paths back to lessons/ paths', () => {
    expect(toOrigin('practice/lessons/tracks/core/hello/main.cpp')).toBe(
      'lessons/tracks/core/hello/main.cpp'
    );
  });

  it('leaves non-practice paths unchanged in toOrigin', () => {
    expect(toOrigin('lessons/tracks/core/hello/main.cpp')).toBe(
      'lessons/tracks/core/hello/main.cpp'
    );
    expect(toOrigin('include/tracer/tracer.hpp')).toBe('include/tracer/tracer.hpp');
  });

  it('round-trips lesson paths through toPractice and toOrigin', () => {
    const origin = 'lessons/units/timer/timer.hpp';
    expect(toOrigin(toPractice(origin))).toBe(origin);

    const practice = 'practice/lessons/units/timer/timer.hpp';
    expect(toPractice(toOrigin(practice))).toBe(practice);
  });

  it('identifies practice paths with isPracticePath', () => {
    expect(isPracticePath('practice/lessons/tracks/core/hello/main.cpp')).toBe(true);
    expect(isPracticePath('practice/lessons/units/timer/timer.hpp')).toBe(true);
    expect(isPracticePath('lessons/tracks/core/hello/main.cpp')).toBe(false);
    expect(isPracticePath('include/tracer/tracer.hpp')).toBe(false);
    // the workspace's own files are not copies
    expect(isPracticePath('practice/state.json')).toBe(false);
    expect(isPracticePath('practice/backup/20260101-000000/practice/lessons/a/main.cpp')).toBe(false);
  });
});

describe('practiceFiles', () => {
  it('maps only files present in status and preserves list order', () => {
    const status: PracticeStatus = {
      lesson: '01_hello',
      dir: 'practice/lessons/tracks/core/01_hello',
      files: [
        {
          path: 'practice/lessons/tracks/core/01_hello/lesson.toml',
          origin: 'lessons/tracks/core/01_hello/lesson.toml',
          state: 'same',
        },
        {
          path: 'practice/lessons/tracks/core/01_hello/main.cpp',
          origin: 'lessons/tracks/core/01_hello/main.cpp',
          state: 'modified',
        },
      ],
      units: [
        {
          id: 'timer',
          dir: 'practice/lessons/units/timer',
          files: [
            {
              path: 'practice/lessons/units/timer/timer.hpp',
              origin: 'lessons/units/timer/timer.hpp',
              state: 'same',
            },
          ],
        },
      ],
    };

    const paths = [
      'include/tracer/tracer.hpp',
      'lessons/tracks/core/01_hello/README.md',
      'lessons/tracks/core/01_hello/main.cpp',
      'lessons/tracks/core/01_hello/helper.cpp',
      'lessons/units/timer/timer.hpp',
    ];

    const result = practiceFiles(paths, status);

    expect(result).toEqual([
      'include/tracer/tracer.hpp',
      'lessons/tracks/core/01_hello/README.md',
      'practice/lessons/tracks/core/01_hello/main.cpp',
      'lessons/tracks/core/01_hello/helper.cpp',
      'practice/lessons/units/timer/timer.hpp',
    ]);
  });
});

describe('stateMap', () => {
  it('covers both lesson and unit files with practice path as key', () => {
    const status: PracticeStatus = {
      lesson: 'sample',
      dir: 'practice/lessons/tracks/core/sample',
      files: [
        {
          path: 'practice/lessons/tracks/core/sample/lesson.toml',
          origin: 'lessons/tracks/core/sample/lesson.toml',
          state: 'same',
        },
        {
          path: 'practice/lessons/tracks/core/sample/main.cpp',
          origin: 'lessons/tracks/core/sample/main.cpp',
          state: 'modified',
        },
      ],
      units: [
        {
          id: 'u1',
          dir: 'practice/lessons/units/u1',
          files: [
            {
              path: 'practice/lessons/units/u1/u1.hpp',
              origin: 'lessons/units/u1/u1.hpp',
              state: 'both',
            },
          ],
        },
      ],
    };

    const map = stateMap(status);
    expect(map.size).toBe(3);
    expect(map.get('practice/lessons/tracks/core/sample/lesson.toml')).toBe('same');
    expect(map.get('practice/lessons/tracks/core/sample/main.cpp')).toBe('modified');
    expect(map.get('practice/lessons/units/u1/u1.hpp')).toBe('both');
  });
});

describe('changedFiles', () => {
  it('picks only files with state modified or both across lesson and units', () => {
    const status: PracticeStatus = {
      lesson: 'sample',
      dir: 'practice/lessons/tracks/core/sample',
      files: [
        {
          path: 'practice/lessons/tracks/core/sample/lesson.toml',
          origin: 'lessons/tracks/core/sample/lesson.toml',
          state: 'same',
        },
        {
          path: 'practice/lessons/tracks/core/sample/main.cpp',
          origin: 'lessons/tracks/core/sample/main.cpp',
          state: 'modified',
        },
        {
          path: 'practice/lessons/tracks/core/sample/both.cpp',
          origin: 'lessons/tracks/core/sample/both.cpp',
          state: 'both',
        },
      ],
      units: [
        {
          id: 'u1',
          dir: 'practice/lessons/units/u1',
          files: [
            {
              path: 'practice/lessons/units/u1/same.hpp',
              origin: 'lessons/units/u1/same.hpp',
              state: 'same',
            },
            {
              path: 'practice/lessons/units/u1/changed.hpp',
              origin: 'lessons/units/u1/changed.hpp',
              state: 'origin-changed',
            },
            {
              path: 'practice/lessons/units/u1/missing.hpp',
              origin: 'lessons/units/u1/missing.hpp',
              state: 'missing-origin',
            },
            {
              path: 'practice/lessons/units/u1/modified.hpp',
              origin: 'lessons/units/u1/modified.hpp',
              state: 'modified',
            },
            {
              path: 'practice/lessons/units/u1/both.hpp',
              origin: 'lessons/units/u1/both.hpp',
              state: 'both',
            },
          ],
        },
      ],
    };

    const changed = changedFiles(status);
    expect(changed.map((f) => f.path)).toEqual([
      'practice/lessons/tracks/core/sample/main.cpp',
      'practice/lessons/tracks/core/sample/both.cpp',
      'practice/lessons/units/u1/modified.hpp',
      'practice/lessons/units/u1/both.hpp',
    ]);
  });
});

describe('api practice methods', () => {
  it('practiceStatus issues GET to /api/practice with encoded lesson parameter', async () => {
    const mockStatus: PracticeStatus = {
      lesson: 'core/hello',
      dir: 'practice/lessons/tracks/core/hello',
      files: [],
      units: [],
    };

    const fetchMock = vi.fn().mockResolvedValue({
      status: 200,
      json: async () => mockStatus,
    });
    vi.stubGlobal('fetch', fetchMock);

    const result = await api.practiceStatus('core/hello');
    expect(result).toEqual(mockStatus);
    expect(fetchMock).toHaveBeenCalledWith('/api/practice?lesson=core%2Fhello', {
      method: 'GET',
      headers: {},
    });
  });

  it('practiceStatus throws on server error', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        status: 404,
        json: async () => ({ error: 'no such lesson' }),
      })
    );

    await expect(api.practiceStatus('unknown')).rejects.toThrow('no such lesson');
  });

  it('practiceStart issues POST to /api/practice/start with lesson body', async () => {
    const mockStatus: PracticeStatus = {
      lesson: 'demo',
      dir: 'practice/lessons/tracks/demo',
      files: [],
      units: [],
    };

    const fetchMock = vi.fn().mockResolvedValue({
      status: 200,
      json: async () => mockStatus,
    });
    vi.stubGlobal('fetch', fetchMock);

    const result = await api.practiceStart('demo');
    expect(result).toEqual(mockStatus);
    expect(fetchMock).toHaveBeenCalledWith('/api/practice/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ lesson: 'demo' }),
    });
  });

  it('practiceReset issues POST to /api/practice/reset with scope body', async () => {
    const mockResult = { reset: ['practice/lessons/tracks/demo/main.cpp'], backup: 'practice/backup/20261110-120000' };

    const fetchMock = vi.fn().mockResolvedValue({
      status: 200,
      json: async () => mockResult,
    });
    vi.stubGlobal('fetch', fetchMock);

    const result = await api.practiceReset({ lesson: 'demo' });
    expect(result).toEqual(mockResult);
    expect(fetchMock).toHaveBeenCalledWith('/api/practice/reset', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ lesson: 'demo' }),
    });
  });

  it('startRun forwards practice option in POST /api/runs body', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      status: 202,
      json: async () => ({ runId: 'run-123' }),
    });
    vi.stubGlobal('fetch', fetchMock);

    const runId = await api.startRun('demo', { practice: true });
    expect(runId).toBe('run-123');
    expect(fetchMock).toHaveBeenCalledWith('/api/runs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ lesson: 'demo', practice: true }),
    });
  });
});
