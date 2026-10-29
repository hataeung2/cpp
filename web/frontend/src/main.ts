// atugcc playground page (spec 070-02): lesson tree, editor, run with streaming output,
// diagrams, events and README.

import './theme.css';
import { api, openRunStream, type DoneData, type LessonEntry, type LessonIndex, type UnitEntry } from './api';
import { DiagramsPanel } from './diagrams';
import { EditorArea, type ConflictChoice } from './editor';
import { EventsPanel } from './events';
import { LessonTree } from './lessonTree';
import { OutputPanel } from './output';
import { ReadmePanel } from './readme';

const $ = <T extends HTMLElement>(id: string) => document.getElementById(id) as T;

const runButton = $<HTMLButtonElement>('run');
const stopButton = $<HTMLButtonElement>('stop');
const statusLine = $('status');
const dialog = $<HTMLDialogElement>('dialog');

// --- theme ---------------------------------------------------------------------------------
const THEME_KEY = 'atugcc.playground.theme';
function storedTheme(): string | null {
  try {
    return localStorage.getItem(THEME_KEY);
  } catch {
    return null;
  }
}
let dark = (storedTheme() ?? (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')) === 'dark';

// --- dialogs -------------------------------------------------------------------------------
function askConflict(path: string, deleted: boolean): Promise<ConflictChoice> {
  return new Promise((resolve) => {
    dialog.replaceChildren();
    const title = document.createElement('strong');
    title.textContent = '저장 충돌';
    const text = document.createElement('p');
    text.textContent = deleted
      ? `${path} 파일이 이 탭을 연 뒤 디스크에서 지워졌습니다.`
      : `${path} 파일이 이 탭을 연 뒤 다른 곳(VS Code 등)에서 바뀌었습니다.`;
    const row = document.createElement('div');
    row.className = 'dialog-actions';
    const choices: [ConflictChoice, string][] = deleted
      ? [['overwrite', '내 내용으로 다시 만들기'], ['cancel', '취소']]
      : [['reload', '디스크 내용으로 새로 고침'], ['overwrite', '내 내용으로 덮어쓰기'], ['cancel', '취소']];
    for (const [choice, label] of choices) {
      const b = document.createElement('button');
      b.textContent = label;
      b.dataset.choice = choice;
      b.addEventListener('click', () => {
        dialog.close();
        resolve(choice);
      });
      row.append(b);
    }
    dialog.onclose = () => resolve('cancel');
    dialog.append(title, text, row);
    dialog.showModal();
  });
}

function notify(message: string): void {
  statusLine.textContent = message;
  statusLine.className = 'status bad';
}

// --- panels ----------------------------------------------------------------------------------
function showPanel(name: string): void {
  for (const b of document.querySelectorAll<HTMLButtonElement>('.panel-tabs button')) {
    b.classList.toggle('active', b.dataset.panel === name);
  }
  for (const p of document.querySelectorAll<HTMLElement>('.panel')) {
    p.classList.toggle('active', p.id === `panel-${name}`);
  }
}
for (const b of document.querySelectorAll<HTMLButtonElement>('.panel-tabs button')) {
  b.addEventListener('click', () => showPanel(b.dataset.panel!));
}

const editor = new EditorArea($('editor'), $('tabs'), askConflict, notify);
const output = new OutputPanel($('output'), $('panel-output'));
const diagrams = new DiagramsPanel($('panel-diagrams'), dialog);
const events = new EventsPanel($('panel-events'), (file, line) => void editor.open(file, line));
const readme = new ReadmePanel($('panel-readme'), (path) => void editor.open(path));
editor.onSaved = (path) => {
  if (path === readme.path()) void readme.show(path);
};

function applyTheme(): void {
  document.documentElement.dataset.theme = dark ? 'dark' : 'light';
  editor.setTheme(dark);
  diagrams.setTheme(dark);
}
$('theme').addEventListener('click', () => {
  dark = !dark;
  try {
    localStorage.setItem(THEME_KEY, dark ? 'dark' : 'light');
  } catch {
    /* private window: the choice lasts for this page only */
  }
  applyTheme();
});
applyTheme();

// --- lessons -------------------------------------------------------------------------------
let index: LessonIndex | null = null;
let lesson: LessonEntry | null = null;

function limitText(l: LessonEntry): string {
  return l.run.profile === 'long'
    ? `long 프로필 → quick 제한(10초)으로 실행 · 긴 실행은 070-06 이후`
    : 'quick · 실행 10초';
}

function selectLesson(l: LessonEntry): void {
  lesson = l;
  $('lesson-title').textContent = l.title;
  runButton.disabled = running;
  statusLine.className = 'status';
  statusLine.textContent = limitText(l);
  const files = [...l.sources, ...l.files.filter((f) => !f.endsWith('README.md'))];
  editor.showFiles(files, l.entry ?? undefined);
  void readme.show(l.readme);
  showPanel('readme');
  history.replaceState(null, '', `#${l.id}`);
}

function selectUnit(u: UnitEntry): void {
  editor.showFiles(u.files);
  void readme.show(u.readme);
  showPanel('readme');
}

const tree = new LessonTree($('tree'), { lesson: selectLesson, unit: selectUnit });

async function loadLessons(): Promise<void> {
  try {
    index = await api.lessons();
  } catch (err) {
    notify(`레슨 목록을 읽지 못했습니다: ${(err as Error).message}`);
    return;
  }
  const wanted = lesson?.id ?? location.hash.slice(1);
  tree.render(index, wanted);
  const found = index.tracks.flatMap((t) => t.lessons).find((l) => l.id === wanted);
  if (found && found.id !== lesson?.id) selectLesson(found);
  else if (found) lesson = found;
}
$('refresh').addEventListener('click', () => void loadLessons());

// --- run -----------------------------------------------------------------------------------
let running = false;
let runId: string | null = null;
let timer: number | undefined;
let phaseStart = 0;
let phaseLabel = '';

function setRunning(on: boolean): void {
  running = on;
  runButton.disabled = on || !lesson;
  stopButton.disabled = true; // enabled once the server has the run (runId)
  if (!on && timer !== undefined) {
    clearInterval(timer);
    timer = undefined;
  }
}

function tick(): void {
  const sec = ((performance.now() - phaseStart) / 1000).toFixed(1);
  statusLine.textContent = `${phaseLabel} · ${sec}s`;
}

function summarize(done: DoneData): void {
  const b = done.build;
  if (!b.ok) {
    const errors = b.diagnostics.filter((d) => d.severity === 'error').length;
    const why = done.stopped ? '중지됨' : b.timedOut ? '시간 초과' : `오류 ${errors}개`;
    output.note(`빌드 실패 (${why}, ${b.ms} ms)`, 'bad');
    statusLine.textContent = `빌드 실패 · ${why}`;
    statusLine.className = 'status bad';
    showPanel('output');
    return;
  }
  const r = done.run;
  if (!r) { // stopped between build and run
    output.note('실행 전에 중지됨', 'bad');
    statusLine.textContent = '중지됨';
    statusLine.className = 'status bad';
    return;
  }
  let text: string;
  let tone: 'ok' | 'bad' = 'bad';
  if (r.stopped) text = '중지됨';
  else if (r.timedOut) text = '시간 제한으로 종료';
  else if (r.signal) text = `시그널 ${r.signal}로 종료`;
  else {
    text = `종료 코드 ${r.exitCode}`;
    tone = r.exitCode === 0 ? 'ok' : 'bad';
  }
  const extra = [r.truncated ? '출력이 1 MiB에서 잘림' : '', done.skippedTraceLines ? `읽지 못한 trace 줄 ${done.skippedTraceLines}개` : '']
    .filter(Boolean).join(', ');
  output.note(`실행: ${text} (${r.ms} ms)${extra ? ` · ${extra}` : ''}`, tone);
  statusLine.textContent = `${text} · 빌드 ${b.ms} ms · 실행 ${r.ms} ms`;
  statusLine.className = `status ${tone}`;
}

async function run(): Promise<void> {
  if (!lesson || running) return;
  setRunning(true);
  statusLine.className = 'status';
  statusLine.textContent = '저장 중…';
  let saved: boolean;
  try {
    saved = await editor.saveAll();
  } catch (err) {
    notify(`저장하지 못했습니다: ${(err as Error).message}`);
    setRunning(false);
    return;
  }
  if (!saved) {
    statusLine.textContent = '취소됨';
    setRunning(false);
    return;
  }
  output.clear();
  events.clear();
  diagrams.clear();
  editor.setDiagnostics([]);
  showPanel('output');
  try {
    runId = await api.startRun(lesson.id);
  } catch (err) {
    notify(`실행을 시작하지 못했습니다: ${(err as Error).message}`);
    setRunning(false);
    return;
  }
  stopButton.disabled = false;
  timer = window.setInterval(tick, 100);
  openRunStream(runId, {
    phase(d) {
      phaseStart = performance.now();
      const limit = d.requested !== d.profile ? `${d.limitSec}s 제한 (${d.requested} → ${d.profile}, 070-06 필요)` : `${d.limitSec}s 제한`;
      phaseLabel = `${d.phase} · ${limit}`;
      output.note(`── ${d.phase} ──`);
      tick();
    },
    build: (t) => output.append('build', t),
    stdout: (t) => output.append('stdout', t),
    stderr: (t) => output.append('stderr', t),
    trace: (list) => events.add(list),
    done(d) {
      setRunning(false);
      runId = null;
      editor.setDiagnostics(d.build.diagnostics);
      if (d.build.ok) diagrams.show(d);
      summarize(d);
    },
    lost() {
      setRunning(false);
      runId = null;
      notify('서버 연결이 끊겼습니다.');
    },
  });
}

runButton.addEventListener('click', () => void run());
stopButton.addEventListener('click', () => {
  if (runId) api.stopRun(runId).catch(() => notify('중지 요청을 보내지 못했습니다.'));
});
window.addEventListener('keydown', (ev) => {
  if ((ev.ctrlKey || ev.metaKey) && ev.key === 'Enter') {
    ev.preventDefault();
    void run();
  }
});

void api.health().then(
  (h) => ($('health').textContent = `${h.preset}${h.compiler ? ` · ${h.compiler}` : ''}`),
  () => notify('서버에 연결하지 못했습니다.'),
);
void loadLessons();
