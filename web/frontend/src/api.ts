// Client for web/server/server.py (spec 070-02 §2.2, 070-06 §2.2, 070-16).

import type {
  PracticeResetResult,
  PracticeResetScope,
  PracticeStatus,
} from './practice';

export type {
  FileState,
  Mode,
  PracticeFile,
  PracticeResetResult,
  PracticeResetScope,
  PracticeStatus,
} from './practice';

export type Profile = 'quick' | 'long';
export type SpanMeterName = 'wall' | 'cpu';

export interface RunInfo {
  profile: Profile;
  timeout: number;
  build: 'release' | 'debug' | null; // [run] build as written; null = the run profile's default
}

export interface LessonEntry {
  id: string;
  title: string;
  titleEn: string | null;
  summary: string;
  summaryEn: string | null;
  path: string;
  target: string;
  entry: string | null;
  sources: string[];
  readme: string | null;
  readmeEn: string | null;
  uses: string[];
  files: string[];
  tags: string[];
  run: RunInfo;
  exercises: number; // number of exercise definitions (spec 070-17)
}

export interface TrackEntry {
  id: string;
  title: string;
  titleEn: string | null;
  summary: string;
  summaryEn: string | null;
  path: string;
  lessons: LessonEntry[];
}

export interface UnitEntry {
  id: string;
  title: string;
  titleEn: string | null;
  summary: string;
  summaryEn: string | null;
  path: string;
  files: string[];
  readme: string | null;
  readmeEn: string | null;
  uses: string[];
  usedBy: string[];
}

export interface TagInfo {
  ko: string;
  en: string;
  aliases: string[];
}

export type TagVocabulary = Record<string, TagInfo>;

export interface LessonIndex {
  version: number;
  tracks: TrackEntry[];
  units: UnitEntry[];
  problems: string[];
  tags: TagVocabulary;
}

export interface FileData {
  path: string;
  content: string;
  sha: string;
  eol: 'lf' | 'crlf';
  writable: boolean;
}

export type SaveResult =
  | { ok: true; sha: string }
  | { ok: false; content: string | null; sha: string | null };

export interface Diagnostic {
  file: string;
  line: number;
  col: number;
  severity: 'error' | 'warning' | 'note';
  message: string;
}

/** One 020-05 event line (message, transition or node). */
export interface TraceEvent {
  v: number;
  kind: 'message' | 'transition' | 'node';
  seq: number;
  tracer: number;
  file: string;
  line: number;
  func: string;
  tUs: number;
  [field: string]: string | number;
}

/** One 020-05 `diagram` line. */
export interface DiagramLine {
  kind: 'diagram';
  tracer: number;
  part: number;
  parts: number;
  diagram: 'sequence' | 'state' | 'structure';
  backend: string;
  title: string;
  overBudget: boolean;
  source: string;
}

export interface PhaseData {
  phase: 'configure' | 'build' | 'run';
  profile: Profile;
  requested: Profile;
  limitSec: number;
  buildType: 'Debug' | 'RelWithDebInfo';
}

/** One span key's aggregate over the run so far (070-06 §2.2). Durations in ns. */
export interface SpanRow {
  file: string;
  line: number;
  label: string;
  meter: string;
  count: number;
  totalNs: number;
  minNs: number;
  maxNs: number;
  p50Ns: number;
  p95Ns: number;
  hist: { loNs: number; hiNs: number; bins: number[] };
}

/** `spans` event: the changed keys (full = every key, sent last). */
export interface SpansData {
  full: boolean;
  rows: SpanRow[];
  spanLines: number;
  lagBytes: number;
}

export interface RunOptions {
  profileOverride?: Profile;
  spanMeter?: SpanMeterName;
  practice?: boolean;
}

export interface DoneData {
  build: { ok: boolean; ms: number; diagnostics: Diagnostic[]; timedOut: boolean };
  run: null | {
    exitCode: number | null;
    signal: string | null;
    timedOut: boolean;
    stopped: boolean;
    traceLimit: boolean;
    ms: number;
    truncated: boolean;
    diagnostics?: Diagnostic[]; // GoogleTest failure lines of the run (spec 070-15 §2.5)
  };
  diagrams: DiagramLine[];
  skippedTraceLines: number;
  stopped: boolean;
  exercises?: ExerciseResult[]; // spec 070-17, practice runs only
  exercisesError?: string; // spec 070-17, practice runs only
}

export interface ExerciseDef {
  id: string;
  title: string;
  titleEn: string | null;
  kind: 'auto' | 'self';
  hint: string | null;
  hintEn: string | null;
  answer: string | null;
  answerEn: string | null;
  failHint: string | null;
  failHintEn: string | null;
}

export interface ExerciseProgress {
  passed: string;
  how: 'auto' | 'self';
}

export interface ExerciseFailure {
  rule: string;
  pattern?: string;
  file?: string;
  line?: string;
  expected?: string | number;
  actual?: string | number;
}

export interface ExerciseResult {
  id: string;
  passed: boolean;
  checked: boolean;
  new?: boolean;
  failures: ExerciseFailure[];
}

export interface ExerciseData {
  lesson: string;
  exercises: ExerciseDef[];
  progress: Record<string, ExerciseProgress>;
  error: string | null;
}

export interface StreamHandlers {
  phase(data: PhaseData): void;
  build(text: string): void;
  stdout(text: string): void;
  stderr(text: string): void;
  trace(events: TraceEvent[]): void;
  spans(data: SpansData): void;
  done(data: DoneData): void;
  lost(): void;
}

async function request<T>(method: string, url: string, body?: unknown): Promise<{ status: number; data: T }> {
  const init: RequestInit = { method, headers: {} };
  if (body !== undefined) {
    init.body = JSON.stringify(body);
    (init.headers as Record<string, string>)['Content-Type'] = 'application/json';
  }
  const res = await fetch(url, init);
  const data = (await res.json()) as T;
  return { status: res.status, data };
}

function fail(status: number, data: unknown): never {
  const message = (data as { error?: string })?.error ?? `HTTP ${status}`;
  throw new Error(message);
}

const fileUrl = (path: string) => `/api/files?path=${encodeURIComponent(path)}`;

export const api = {
  async health(): Promise<{ version: number; preset: string; releasePreset: string; compiler: string | null }> {
    const { status, data } = await request<{ version: number; preset: string; releasePreset: string; compiler: string | null }>('GET', '/api/health');
    return status === 200 ? data : fail(status, data);
  },

  async lessons(): Promise<LessonIndex> {
    const { status, data } = await request<LessonIndex>('GET', '/api/lessons');
    return status === 200 ? data : fail(status, data);
  },

  async readFile(path: string): Promise<FileData> {
    const { status, data } = await request<FileData>('GET', fileUrl(path));
    return status === 200 ? data : fail(status, data);
  },

  async saveFile(path: string, content: string, baseSha: string | null): Promise<SaveResult> {
    const { status, data } = await request<{ sha: string; content: string | null }>('PUT', fileUrl(path), { content, baseSha });
    if (status === 200) return { ok: true, sha: data.sha };
    if (status === 409) return { ok: false, content: data.content, sha: data.sha };
    return fail(status, data);
  },

  async startRun(lesson: string, options: RunOptions = {}): Promise<string> {
    const { status, data } = await request<{ runId: string }>('POST', '/api/runs', { lesson, ...options });
    return status === 202 ? data.runId : fail(status, data);
  },

  async stopRun(runId: string): Promise<void> {
    await request('POST', `/api/runs/${encodeURIComponent(runId)}/stop`, {});
  },

  async practiceStatus(lesson: string): Promise<PracticeStatus> {
    const { status, data } = await request<PracticeStatus>('GET', `/api/practice?lesson=${encodeURIComponent(lesson)}`);
    return status === 200 ? data : fail(status, data);
  },

  async practiceStart(lesson: string): Promise<PracticeStatus> {
    const { status, data } = await request<PracticeStatus>('POST', '/api/practice/start', { lesson });
    return status === 200 ? data : fail(status, data);
  },

  async practiceReset(scope: PracticeResetScope): Promise<PracticeResetResult> {
    const { status, data } = await request<PracticeResetResult>('POST', '/api/practice/reset', scope);
    return status === 200 ? data : fail(status, data);
  },

  async exercises(lesson: string): Promise<ExerciseData> {
    const { status, data } = await request<ExerciseData>('GET', `/api/exercises?lesson=${encodeURIComponent(lesson)}`);
    return status === 200 ? data : fail(status, data);
  },

  async exerciseSummary(): Promise<Record<string, number>> {
    const { status, data } = await request<Record<string, number>>('GET', '/api/exercises/summary');
    return status === 200 ? data : fail(status, data);
  },

  async exerciseSelf(lesson: string, id: string, done: boolean): Promise<{ progress: Record<string, ExerciseProgress> }> {
    const { status, data } = await request<{ progress: Record<string, ExerciseProgress> }>(
      'POST',
      '/api/exercises/self',
      { lesson, id, done },
    );
    return status === 200 ? data : fail(status, data);
  },

  async exerciseClear(lesson: string): Promise<{ progress: Record<string, ExerciseProgress> }> {
    const { status, data } = await request<{ progress: Record<string, ExerciseProgress> }>(
      'POST',
      '/api/exercises/clear',
      { lesson },
    );
    return status === 200 ? data : fail(status, data);
  },
};

/** Follow a run's SSE stream; returns a function that closes it (closing a live run stops it). */
export function openRunStream(runId: string, handlers: StreamHandlers): () => void {
  const source = new EventSource(`/api/runs/${encodeURIComponent(runId)}/stream`);
  let finished = false;
  const on = <T>(name: string, handle: (data: T) => void) =>
    source.addEventListener(name, (e) => handle(JSON.parse((e as MessageEvent<string>).data) as T));
  on<PhaseData>('phase', (d) => handlers.phase(d));
  on<{ text: string }>('build', (d) => handlers.build(d.text));
  on<{ text: string }>('stdout', (d) => handlers.stdout(d.text));
  on<{ text: string }>('stderr', (d) => handlers.stderr(d.text));
  on<{ events: TraceEvent[] }>('trace', (d) => handlers.trace(d.events));
  on<SpansData>('spans', (d) => handlers.spans(d));
  on<DoneData>('done', (d) => {
    finished = true;
    source.close(); // otherwise EventSource reconnects when the server ends the stream
    handlers.done(d);
  });
  source.onerror = () => {
    // The stream ends only after `done`; an error before that means the server or the network
    // went away. No automatic retry: the server stops a run whose stream closed.
    if (finished) return;
    finished = true;
    source.close();
    handlers.lost();
  };
  return () => source.close();
}
