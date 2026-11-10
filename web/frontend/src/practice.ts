// Practice workspace on the page (spec 070-16): mode, path mapping between lessons/ and practice/lessons/, status helpers.

export type Mode = 'practice' | 'original';
export const MODE_KEY = 'atugcc.mode';

export type FileState = 'same' | 'modified' | 'both' | 'origin-changed' | 'missing-origin';

export interface PracticeFile {
  path: string;
  origin: string;
  state: FileState;
}

export interface PracticeStatus {
  lesson: string;
  dir: string;
  files: PracticeFile[];
  units: { id: string; dir: string; files: PracticeFile[] }[];
}

export interface PracticeResetResult {
  reset: string[];
  backup: string | null;
}

export type PracticeResetScope = { lesson: string } | { unit: string } | { path: string };

/** Read stored editing mode. Only 'original' yields 'original'; all other values or errors yield 'practice'. */
export function loadMode(): Mode {
  try {
    const value = localStorage.getItem(MODE_KEY);
    return value === 'original' ? 'original' : 'practice';
  } catch {
    return 'practice';
  }
}

/** Persist editing mode to localStorage, ignoring any storage errors. */
export function saveMode(mode: Mode): void {
  try {
    localStorage.setItem(MODE_KEY, mode);
  } catch {
    // Ignore storage errors (e.g. private mode or disabled storage)
  }
}

/** Check whether a repo-relative path points to a practice copy. */
export function isPracticePath(path: string): boolean {
  return path.startsWith('practice/lessons/');
}

/** Map a repo-relative path to its practice workspace counterpart. */
export function toPractice(path: string): string {
  if (path.startsWith('practice/lessons/')) {
    return path;
  }
  if (path.startsWith('lessons/')) {
    return 'practice/' + path;
  }
  return path;
}

/** Map a practice path back to its origin repo-relative path; leaves other paths unchanged. */
export function toOrigin(path: string): string {
  if (path.startsWith('practice/lessons/')) {
    return path.slice('practice/'.length);
  }
  return path;
}

/**
 * Map paths to practice paths when a practice copy exists in status.
 * Preserves path order. READMEs and non-copied paths stay unchanged.
 */
export function practiceFiles(paths: readonly string[], status: PracticeStatus): string[] {
  const practicePaths = new Set<string>();
  for (const f of status.files) {
    practicePaths.add(f.path);
  }
  for (const u of status.units) {
    for (const f of u.files) {
      practicePaths.add(f.path);
    }
  }

  return paths.map((path) => {
    const candidate = toPractice(path);
    return practicePaths.has(candidate) ? candidate : path;
  });
}

/** Build a lookup map of practice path -> file state across lesson and unit files. */
export function stateMap(status: PracticeStatus): Map<string, FileState> {
  const map = new Map<string, FileState>();
  for (const f of status.files) {
    map.set(f.path, f.state);
  }
  for (const u of status.units) {
    for (const f of u.files) {
      map.set(f.path, f.state);
    }
  }
  return map;
}

/** Collect files from lesson and unit copies whose state is 'modified' or 'both'. */
export function changedFiles(status: PracticeStatus): PracticeFile[] {
  const result: PracticeFile[] = [];
  for (const f of status.files) {
    if (f.state === 'modified' || f.state === 'both') {
      result.push(f);
    }
  }
  for (const u of status.units) {
    for (const f of u.files) {
      if (f.state === 'modified' || f.state === 'both') {
        result.push(f);
      }
    }
  }
  return result;
}
