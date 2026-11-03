// atugcc playground page (spec 070-02, 070-06): lesson tree, editor, run with streaming output,
// diagrams, events, span timings and README.

import './theme.css';
import { api, openRunStream, type DoneData, type LessonEntry, type LessonIndex, type PhaseData, type Profile, type RunOptions,
  type SpanMeterName, type UnitEntry } from './api';
import { DiagramsPanel } from './diagrams';
import { EditorArea, type ConflictChoice } from './editor';
import { EventsPanel } from './events';
import { applyStatic, lang, localized, onLangChange, setLang, t } from './i18n';
import { LessonTree } from './lessonTree';
import { OutputPanel } from './output';
import { ReadmePanel, type ReadmeOptions } from './readme';
import { queryTerms } from './search';
import { LAG_SHOWN_BYTES, TimingsPanel, effectiveBuild, inlineByLine } from './timings';

const $ = <T extends HTMLElement>(id: string) => document.getElementById(id) as T;

const LONG_OUTPUT_LINES = 5000; // 070-06 Assumption 8

const runButton = $<HTMLButtonElement>('run');
const stopButton = $<HTMLButtonElement>('stop');
const longToggle = $<HTMLInputElement>('long-run');
const meterSelect = $<HTMLSelectElement>('meter');
const statusLine = $('status');
const dialog = $<HTMLDialogElement>('dialog');
const langButton = $<HTMLButtonElement>('lang');
const searchBox = $<HTMLInputElement>('search');
const searchCount = $('search-count');

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
    title.textContent = t('dialog.conflictTitle');
    const text = document.createElement('p');
    text.textContent = deleted
      ? t('dialog.conflictDeleted', { path })
      : t('dialog.conflictChanged', { path });
    const row = document.createElement('div');
    row.className = 'dialog-actions';
    const choices: [ConflictChoice, string][] = deleted
      ? [['overwrite', t('dialog.recreate')], ['cancel', t('dialog.cancel')]]
      : [['reload', t('dialog.reload')], ['overwrite', t('dialog.overwrite')], ['cancel', t('dialog.cancel')]];
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

/** The status line as a function of the language, so a switch draws the same status again (070-10 Assumption 11). */
let statusText: () => string = () => '';
function setStatus(text: () => string, tone: '' | 'ok' | 'bad' = ''): void {
  statusText = text;
  statusLine.textContent = text();
  statusLine.className = tone ? `status ${tone}` : 'status';
}

/** An error on the status line; a function of the language when it comes from this page. */
function notify(message: string | (() => string)): void {
  setStatus(typeof message === 'function' ? message : () => message, 'bad');
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
const timings = new TimingsPanel($('panel-timings'), (file, line) => void editor.open(file, line));
timings.onRows = (rows) => editor.setInlineTimings(inlineByLine(rows));
const readme = new ReadmePanel(
  $('panel-readme'),
  (path) => void editor.open(path),
  (id) => {
    searchBox.value = id;
    renderTree();
  },
);

let index: LessonIndex | null = null;
type ReadmeContext = { kind: 'lesson'; lesson: LessonEntry } | { kind: 'unit'; unit: UnitEntry } | { kind: 'intro' };
let readmeContext: ReadmeContext | null = null;
let lastReadmePath: string | null = null;
let lastReadmeAlternate: string | null = null; // shown instead when lastReadmePath cannot be read

function showReadme(context: ReadmeContext): void {
  readmeContext = context;
  let path: string | null = null;
  const options: ReadmeOptions = {};
  const currentLang = lang();

  if (context.kind === 'intro') {
    if (currentLang === 'en') {
      path = 'lessons/intro.en.md';
      options.alternate = 'lessons/intro.md';
    } else {
      path = 'lessons/intro.md';
    }
  } else {
    const entry = context.kind === 'lesson' ? context.lesson : context.unit;
    if (context.kind === 'lesson') {
      const vocab = index?.tags;
      const isEn = currentLang === 'en';
      options.tags = context.lesson.tags.map((id) => {
        const info = vocab ? vocab[id] : undefined;
        const label = info ? (isEn ? info.en : info.ko) : id;
        return { id, label };
      });
    }
    if (currentLang === 'en') {
      if (entry.readmeEn) {
        path = entry.readmeEn;
      } else if (entry.readme !== null) {
        path = entry.readme;
        options.notice = true;
      } else {
        path = null;
      }
    } else {
      path = entry.readme;
    }
  }
  lastReadmePath = path;
  lastReadmeAlternate = options.alternate ?? null;
  void readme.show(path, options);
}

editor.onSaved = (path) => {
  if (path === readme.path()) void readme.show(path, readme.options());
};

function showIntro(): void {
  showReadme({ kind: 'intro' });
  showPanel('readme');
}
$('intro').addEventListener('click', showIntro);

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

function updateLangButton(): void {
  const isKo = lang() === 'ko';
  langButton.textContent = t(isKo ? 'lang.toEnglish' : 'lang.toKorean');
  langButton.title = t(isKo ? 'lang.toEnglishTitle' : 'lang.toKoreanTitle');
}
langButton.addEventListener('click', () => {
  setLang(lang() === 'ko' ? 'en' : 'ko');
});

// --- lessons -------------------------------------------------------------------------------
let lesson: LessonEntry | null = null;

function updateLessonTitle(): void {
  const el = $('lesson-title');
  if (lesson) {
    el.textContent = localized(lesson.title, lesson.titleEn).text;
  } else {
    el.textContent = t('top.chooseLesson');
  }
}

/** Profile of the next run: the toggle, which starts at the manifest's profile. */
const chosenProfile = (): Profile => (longToggle.checked ? 'long' : 'quick');

function limitText(l: LessonEntry): string {
  const profile = chosenProfile();
  const build = effectiveBuild(profile, l.run.build); // the runner's rule (tools/lessons.py)
  const limit = t('run.limitSec', { sec: profile === 'long' ? l.run.timeout : 10 });
  const toggled = profile !== l.run.profile ? t('run.manifestOverride', { profile: l.run.profile }) : '';
  const buildText = build === 'release' ? 'Release(RelWithDebInfo)' : 'Debug';
  return t('run.limitStatus', { profile, toggled, limit, build: buildText });
}

function selectLesson(l: LessonEntry): void {
  lesson = l;
  updateLessonTitle();
  runButton.disabled = running;
  longToggle.checked = l.run.profile === 'long';
  setStatus(() => limitText(l));
  const files = [...l.sources, ...l.files.filter((f) => !f.endsWith('README.md'))];
  editor.showFiles(files, l.entry ?? undefined);
  showReadme({ kind: 'lesson', lesson: l });
  showPanel('readme');
  history.replaceState(null, '', `#${l.id}`);
}

function selectUnit(u: UnitEntry): void {
  editor.showFiles(u.files);
  showReadme({ kind: 'unit', unit: u });
  showPanel('readme');
}

const tree = new LessonTree($('tree'), { lesson: selectLesson, unit: selectUnit });

function renderTree(): void {
  if (!index) return;
  const query = searchBox.value;
  const { lessons, units } = tree.render(index, lesson?.id, query);
  searchCount.textContent = queryTerms(query).length > 0
    ? t('search.count', { lessons, units })
    : '';
}

searchBox.addEventListener('input', () => {
  renderTree();
});

searchBox.addEventListener('keydown', (ev) => {
  if (ev.isComposing || ev.keyCode === 229) return;
  if (ev.key === 'Escape') {
    ev.preventDefault();
    if (searchBox.value) {
      searchBox.value = '';
      renderTree();
    } else {
      searchBox.blur();
    }
  } else if (ev.key === 'Enter' && !ev.ctrlKey && !ev.metaKey && !ev.altKey && !ev.shiftKey) {
    const first = tree.firstVisibleLesson();
    if (first) {
      ev.preventDefault();
      tree.markLesson(first.id);
      selectLesson(first);
      renderTree();
    }
  }
});

let introDecided = false; // only the page's first load may show the intro; ↻ never replaces the panel

async function loadLessons(): Promise<void> {
  const firstLoad = !introDecided;
  introDecided = true;
  try {
    index = await api.lessons();
  } catch (err) {
    notify(() => t('page.lessonsFailed', { error: (err as Error).message }));
    if (firstLoad) showIntro();
    return;
  }
  const wanted = lesson?.id ?? location.hash.slice(1);

  const found = index.tracks.flatMap((t) => t.lessons).find((l) => l.id === wanted);
  if (found && found.id !== lesson?.id) selectLesson(found);
  else if (found) {
    lesson = found;
    updateLessonTitle();
  }
  else if (firstLoad) showIntro();
  renderTree();
}
$('refresh').addEventListener('click', () => void loadLessons());

// --- run -----------------------------------------------------------------------------------
let running = false;
let runId: string | null = null;
let timer: number | undefined;
let phaseStart = 0;
let phaseLimit = 0;
let lastPhase: PhaseData | null = null;
let sawSpans = false;
let lagBytes = 0;

function setRunning(on: boolean): void {
  running = on;
  runButton.disabled = on || !lesson;
  longToggle.disabled = on;
  meterSelect.disabled = on;
  stopButton.disabled = true; // enabled once the server has the run (runId)
  if (!on && timer !== undefined) {
    clearInterval(timer);
    timer = undefined;
  }
}

function tick(): void {
  if (!lastPhase) return;
  const elapsed = (performance.now() - phaseStart) / 1000;
  const left = Math.max(0, phaseLimit - elapsed);
  const lag = lagBytes >= LAG_SHOWN_BYTES
    ? t('run.lag', { mib: (lagBytes / (1 << 20)).toFixed(1) })
    : '';
  const profileOverride = lastPhase.requested !== lastPhase.profile
    ? t('run.phaseManifest', { requested: lastPhase.requested })
    : '';
  const profile = `${lastPhase.profile}${profileOverride}`;
  const phaseLabel = t('run.phaseLabel', {
    phase: lastPhase.phase,
    profile,
    buildType: lastPhase.buildType,
    limitSec: lastPhase.limitSec,
  });
  statusLine.textContent = t('run.phaseTick', {
    phaseLabel,
    elapsed: elapsed.toFixed(1),
    left: left.toFixed(0),
    lag,
  });
}

longToggle.addEventListener('change', () => {
  const l = lesson;
  if (l && !running) setStatus(() => limitText(l));
});

function summarize(done: DoneData): void {
  const b = done.build;
  if (!b.ok) {
    const errors = b.diagnostics.filter((d) => d.severity === 'error').length;
    const why = () => (done.stopped
      ? t('run.stopped')
      : b.timedOut
        ? t('run.timedOut')
        : t('run.errorsCount', { count: errors }));
    output.note(t('run.buildFailedNote', { why: why(), ms: b.ms }), 'bad');
    setStatus(() => t('run.buildFailedStatus', { why: why() }), 'bad');
    showPanel('output');
    return;
  }
  const r = done.run;
  if (!r) { // stopped between build and run
    output.note(t('run.stoppedBeforeRun'), 'bad');
    setStatus(() => t('run.stopped'), 'bad');
    return;
  }
  const tone: 'ok' | 'bad' = !r.stopped && !r.traceLimit && !r.timedOut && !r.signal && r.exitCode === 0 ? 'ok' : 'bad';
  const text = () => (r.stopped ? t('run.stopped')
    : r.traceLimit ? t('run.traceLimit')
      : r.timedOut ? t('run.runTimedOut')
        : r.signal ? t('run.terminatedBySignal', { signal: r.signal })
          : t('run.exitCode', { code: String(r.exitCode) }));
  const extra = [
    r.truncated ? t('run.outputTruncated') : '',
    done.skippedTraceLines ? t('run.skippedTraceLines', { count: done.skippedTraceLines }) : '',
  ]
    .filter(Boolean)
    .join(', ');
  const extraSuffix = extra ? ` · ${extra}` : '';
  output.note(t('run.runNote', { text: text(), ms: r.ms, extra: extraSuffix }), tone);
  setStatus(() => t('run.statusSummary', { text: text(), buildMs: b.ms, runMs: r.ms }), tone);
}

async function run(): Promise<void> {
  if (!lesson || running) return;
  setRunning(true);
  setStatus(() => t('run.saving'));
  let saved: boolean;
  try {
    saved = await editor.saveAll();
  } catch (err) {
    notify(() => t('page.saveFailed', { error: (err as Error).message }));
    setRunning(false);
    return;
  }
  if (!saved) {
    setStatus(() => t('run.cancelled'));
    setRunning(false);
    return;
  }
  const profile = chosenProfile();
  const options: RunOptions = { spanMeter: meterSelect.value as SpanMeterName };
  if (profile !== lesson.run.profile) options.profileOverride = profile;
  output.clear();
  output.setMaxLines(profile === 'long' ? LONG_OUTPUT_LINES : null);
  events.clear();
  diagrams.clear();
  timings.start(lesson.id);
  sawSpans = false;
  lagBytes = 0;
  lastPhase = null;
  editor.setDiagnostics([]);
  showPanel('output');
  try {
    runId = await api.startRun(lesson.id, options);
  } catch (err) {
    notify(() => t('page.runStartFailed', { error: (err as Error).message }));
    setRunning(false);
    return;
  }
  stopButton.disabled = false;
  timer = window.setInterval(tick, 100);
  openRunStream(runId, {
    phase(d) {
      lastPhase = d;
      phaseStart = performance.now();
      phaseLimit = d.limitSec;
      timings.setBuildType(d.buildType);
      output.note(`── ${d.phase} · ${d.buildType} ──`);
      tick();
    },
    build: (t) => output.append('build', t),
    stdout: (t) => output.append('stdout', t),
    stderr: (t) => output.append('stderr', t),
    trace: (list) => events.add(list),
    spans(d) {
      timings.update(d);
      lagBytes = d.lagBytes;
      if (!sawSpans) {
        sawSpans = true;
        showPanel('timings'); // the first span of a run: show the live table
      }
    },
    done(d) {
      setRunning(false);
      runId = null;
      editor.setDiagnostics(d.build.diagnostics);
      if (d.build.ok) diagrams.show(d);
      const r = d.run;
      const how = () => (!r
        ? null
        : r.stopped
          ? t('run.stopped')
          : r.traceLimit
            ? t('run.stoppedTraceLimit')
            : r.timedOut
              ? t('run.runTimedOut')
              : r.signal
                ? t('run.signal', { signal: r.signal })
                : t('run.completed'));
      // a killed or crashed program never flushed its last trace lines (070-06 §4, KI-016)
      const cutNote = r && (r.stopped || r.traceLimit || r.timedOut || r.signal);
      timings.finish(() => { const h = how(); return h && h + (cutNote ? t('run.cutNote') : ''); });
      summarize(d);
    },
    lost() {
      setRunning(false);
      runId = null;
      notify(() => t('page.serverLost'));
    },
  });
}

onLangChange(() => {
  applyStatic();
  updateLangButton();
  renderTree();
  updateLessonTitle();
  // a document reached through a link inside a README is left as it is
  const shown = readme.path();
  if (readmeContext && (shown === lastReadmePath || (shown !== null && shown === lastReadmeAlternate))) {
    showReadme(readmeContext);
  }
  timings.relabel();
  if (!running) statusLine.textContent = statusText(); // while running, the next tick redraws it
});

runButton.addEventListener('click', () => void run());
stopButton.addEventListener('click', () => {
  if (runId) api.stopRun(runId).catch(() => notify(() => t('page.stopFailed')));
});
window.addEventListener('keydown', (ev) => {
  if ((ev.ctrlKey || ev.metaKey) && ev.key === 'Enter') {
    ev.preventDefault();
    void run();
    return;
  }
  if (!ev.ctrlKey && !ev.metaKey && !ev.altKey && ev.key === '/') {
    const el = ev.target instanceof Element ? ev.target : null;
    const isInput = el ? el.matches('input, textarea, select') : false;
    const isEditable = (el as HTMLElement | null)?.isContentEditable ?? false;
    const inMonaco = el ? el.closest('.monaco-editor') !== null : false;
    if (!isInput && !isEditable && !inMonaco) {
      ev.preventDefault();
      searchBox.focus();
      searchBox.select();
    }
  }
});

applyStatic();
updateLangButton();
updateLessonTitle();

void api.health().then(
  (h) => ($('health').textContent = `${h.preset}${h.compiler ? ` · ${h.compiler}` : ''}`),
  () => notify(() => t('page.serverConnectFailed')),
);
void loadLessons();
