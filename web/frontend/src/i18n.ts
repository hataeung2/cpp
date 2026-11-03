// UI internationalization dictionary and helpers (spec 070-10 §2.4).

export type Lang = 'ko' | 'en';
export const LANG_KEY = 'atugcc.lang';

const ko = {
  'top.intro': 'ⓘ 소개',
  'top.introTitle': '이 페이지와 라이브러리·레슨 소개',
  'top.chooseLesson': '레슨을 고르세요',
  'top.runTitle': '수정한 탭을 저장하고 빌드·실행 (Ctrl+Enter)',
  'top.longRun': '길게 실행',
  'top.longRunTitle': '이번 실행만 long 프로필(레슨 timeout, 기본 Release 빌드) 또는 quick(10초, 기본 Debug)으로. 매니페스트의 build가 있으면 그 빌드. 매니페스트는 바뀌지 않습니다',
  'top.meter': '측정기',
  'top.meterTitle': 'span 측정기 (ATUGCC_SPAN_METER): wall = 경과 시간, cpu = 스레드 CPU 시간',
  'top.themeTitle': '라이트/다크 전환',
  'top.lessons': '레슨',
  'top.refreshTitle': '레슨 목록 다시 읽기',
  'lang.toEnglish': 'EN',
  'lang.toEnglishTitle': '영어로 보기',
  'lang.toKorean': '한',
  'lang.toKoreanTitle': '한국어로 보기',
  'tree.manifestProblems': '레슨 manifest 오류',
  'tree.units': '유닛',
  'tree.usedBy': '사용: {ids}',
  'tree.usedByNone': '사용하는 레슨 없음',
  'tree.unitTooltip': '사용하는 레슨: {lessons}',
  'tree.none': '없음',
  'search.placeholder': '레슨·기능 검색 (/)',
  'search.title': '제목, 태그, C++ 기능, 헤더 이름으로 찾기. Enter: 첫 레슨 열기, Esc: 지우기',
  'search.noResults': '검색 결과 없음',
  'search.count': '레슨 {lessons} · 유닛 {units}',
  'readme.none': 'README가 없습니다.',
  'readme.koreanOnly': '이 문서는 한국어로만 있습니다.',
  'readme.openInEditor': '에디터에서 열기',
  'dialog.conflictTitle': '저장 충돌',
  'dialog.conflictDeleted': '{path} 파일이 이 탭을 연 뒤 디스크에서 지워졌습니다.',
  'dialog.conflictChanged': '{path} 파일이 이 탭을 연 뒤 다른 곳(VS Code 등)에서 바뀌었습니다.',
  'dialog.recreate': '내 내용으로 다시 만들기',
  'dialog.reload': '디스크 내용으로 새로 고침',
  'dialog.overwrite': '내 내용으로 덮어쓰기',
  'dialog.cancel': '취소',
  'page.lessonsFailed': '레슨 목록을 읽지 못했습니다: {error}',
  'page.saveFailed': '저장하지 못했습니다: {error}',
  'page.runStartFailed': '실행을 시작하지 못했습니다: {error}',
  'page.serverLost': '서버 연결이 끊겼습니다.',
  'page.stopFailed': '중지 요청을 보내지 못했습니다.',
  'page.serverConnectFailed': '서버에 연결하지 못했습니다.',
  'run.manifestOverride': ' (매니페스트: {profile})',
  'run.limitSec': '실행 {sec}초',
  'run.limitStatus': '{profile}{toggled} · {limit} · {build} 빌드',
  'run.phaseManifest': ' (매니페스트 {requested})',
  'run.phaseLabel': '{phase} · {profile} · {buildType} · {limitSec}s 제한',
  'run.phaseTick': '{phaseLabel} · {elapsed}s · 남은 {left}s{lag}',
  'run.lag': ' · 집계 지연 {mib} MiB',
  'run.saving': '저장 중…',
  'run.cancelled': '취소됨',
  'run.stopped': '중지됨',
  'run.timedOut': '시간 초과',
  'run.errorsCount': '오류 {count}개',
  'run.buildFailedNote': '빌드 실패 ({why}, {ms} ms)',
  'run.buildFailedStatus': '빌드 실패 · {why}',
  'run.stoppedBeforeRun': '실행 전에 중지됨',
  'run.traceLimit': 'trace 1 GiB 초과로 중지: span을 루프 바깥에서 재세요',
  'run.runTimedOut': '시간 제한으로 종료',
  'run.terminatedBySignal': '시그널 {signal}로 종료',
  'run.exitCode': '종료 코드 {code}',
  'run.outputTruncated': '출력이 한도에서 잘림',
  'run.skippedTraceLines': '읽지 못한 trace 줄 {count}개',
  'run.runNote': '실행: {text} ({ms} ms){extra}',
  'run.statusSummary': '{text} · 빌드 {buildMs} ms · 실행 {runMs} ms',
  'run.stoppedTraceLimit': 'trace 한도로 중지',
  'run.signal': '시그널 {signal}',
  'run.completed': '종료',
  'run.cutNote': ' · 마지막 flush 이후 span은 빠졌을 수 있음',
  'timings.buildDiff': '빌드 다름',
  'timings.colLabel': '라벨',
  'timings.colWhere': '파일:줄',
  'timings.colMeter': '측정기',
  'timings.colCount': 'count',
  'timings.colTotal': 'total',
  'timings.colMean': 'mean',
  'timings.colP50': 'p50',
  'timings.colP95': 'p95',
  'timings.colMin': 'min',
  'timings.colMax': 'max',
  'timings.colChange': '이전 대비',
  'timings.histAria': '분포 {lo} – {hi}',
  'timings.build': '빌드 {build}',
  'timings.spansCount': 'span {count}개',
  'timings.lag': '집계 지연 {mib} MiB',
  'timings.empty': '구간 시간이 없습니다. 레슨에서 tracer.timeScope("이름")으로 구간을 재면 실행 중에 여기에 나옵니다.',
  'timings.rowTooltip': '{where} — 누르면 에디터로 이동, ▸ 분포',
  'timings.hint': 'span 하나에도 기록 비용이 있습니다(수백 ns, 스트림 포함 수 µs). 짧은 일은 루프 바깥 구간으로 재세요.',
  'diagrams.abnormal': '다이어그램 없음: 정상 종료가 아니라서 Tracer 소멸자가 다이어그램을 쓰지 못했습니다.',
  'diagrams.none': '이 실행은 Tracer 다이어그램을 만들지 않았습니다.',
  'diagrams.overBudget': '예산 초과',
  'diagrams.overBudgetTitle': '한 조각이 생성 예산보다 큽니다 (020-04)',
  'diagrams.fullSize': '전체 크기',
  'diagrams.error': 'Mermaid 오류: {error}',
  'diagrams.close': '닫기',
  'editor.changedOnDisk': '{path} — 디스크에서 바뀜 (저장하면 충돌 처리)',
  'editor.changedWhileSaving': '{path}: 저장하는 사이에 다시 바뀌었습니다. 다시 시도하세요.',
  'events.firstOnly': '처음 {count}개만 표시합니다.',
  'output.dropped': '… 앞의 {dropped}줄은 생략 (최근 {max}줄만 유지)',
} as const;

const en: Record<keyof typeof ko, string> = {
  'top.intro': 'ⓘ About',
  'top.introTitle': 'About this page, the library and the lessons',
  'top.chooseLesson': 'Choose a lesson',
  'top.runTitle': 'Save the modified tabs, then build and run (Ctrl+Enter)',
  'top.longRun': 'Run long',
  'top.longRunTitle': 'This run only: the long profile (the lesson timeout, Release build by default) or quick (10 s, Debug by default). A build set in the manifest wins. The manifest is not changed',
  'top.meter': 'Meter',
  'top.meterTitle': 'Span meter (ATUGCC_SPAN_METER): wall = elapsed time, cpu = thread CPU time',
  'top.themeTitle': 'Toggle light/dark theme',
  'top.lessons': 'Lessons',
  'top.refreshTitle': 'Reload the lesson list',
  'lang.toEnglish': 'EN',
  'lang.toEnglishTitle': 'Switch to English',
  'lang.toKorean': '한',
  'lang.toKoreanTitle': 'Show in Korean',
  'tree.manifestProblems': 'Lesson manifest errors',
  'tree.units': 'Units',
  'tree.usedBy': 'Used by: {ids}',
  'tree.usedByNone': 'No lessons use this',
  'tree.unitTooltip': 'Used by lessons: {lessons}',
  'tree.none': 'none',
  'search.placeholder': 'Search lessons, features (/)',
  'search.title': 'Find by title, tag, C++ feature or header name. Enter: open the first lesson, Esc: clear',
  'search.noResults': 'No results',
  'search.count': 'Lessons {lessons} · Units {units}',
  'readme.none': 'No README available.',
  'readme.koreanOnly': 'This document is available in Korean only.',
  'readme.openInEditor': 'Open in editor',
  'dialog.conflictTitle': 'Save conflict',
  'dialog.conflictDeleted': '{path} has been deleted on disk since this tab was opened.',
  'dialog.conflictChanged': '{path} has been modified elsewhere (e.g. VS Code) since this tab was opened.',
  'dialog.recreate': 'Recreate with my content',
  'dialog.reload': 'Reload from disk',
  'dialog.overwrite': 'Overwrite with my content',
  'dialog.cancel': 'Cancel',
  'page.lessonsFailed': 'Failed to read lesson list: {error}',
  'page.saveFailed': 'Failed to save: {error}',
  'page.runStartFailed': 'Failed to start run: {error}',
  'page.serverLost': 'Server connection lost.',
  'page.stopFailed': 'Failed to send stop request.',
  'page.serverConnectFailed': 'Failed to connect to the server.',
  'run.manifestOverride': ' (manifest: {profile})',
  'run.limitSec': 'run {sec}s',
  'run.limitStatus': '{profile}{toggled} · {limit} · {build} build',
  'run.phaseManifest': ' (manifest {requested})',
  'run.phaseLabel': '{phase} · {profile} · {buildType} · {limitSec}s limit',
  'run.phaseTick': '{phaseLabel} · {elapsed}s · {left}s left{lag}',
  'run.lag': ' · lag {mib} MiB',
  'run.saving': 'Saving…',
  'run.cancelled': 'Cancelled',
  'run.stopped': 'Stopped',
  'run.timedOut': 'timed out',
  'run.errorsCount': 'errors: {count}',
  'run.buildFailedNote': 'Build failed ({why}, {ms} ms)',
  'run.buildFailedStatus': 'Build failed · {why}',
  'run.stoppedBeforeRun': 'Stopped before running',
  'run.traceLimit': 'Stopped: trace exceeded 1 GiB — move spans outside tight loops',
  'run.runTimedOut': 'Terminated by timeout',
  'run.terminatedBySignal': 'Terminated by signal {signal}',
  'run.exitCode': 'Exit code {code}',
  'run.outputTruncated': 'output truncated at limit',
  'run.skippedTraceLines': 'unparsed trace lines: {count}',
  'run.runNote': 'Run: {text} ({ms} ms){extra}',
  'run.statusSummary': '{text} · build {buildMs} ms · run {runMs} ms',
  'run.stoppedTraceLimit': 'stopped at trace limit',
  'run.signal': 'Signal {signal}',
  'run.completed': 'Done',
  'run.cutNote': ' · spans after the last flush may be missing',
  'timings.buildDiff': 'different build',
  'timings.colLabel': 'label',
  'timings.colWhere': 'file:line',
  'timings.colMeter': 'meter',
  'timings.colCount': 'count',
  'timings.colTotal': 'total',
  'timings.colMean': 'mean',
  'timings.colP50': 'p50',
  'timings.colP95': 'p95',
  'timings.colMin': 'min',
  'timings.colMax': 'max',
  'timings.colChange': 'vs previous',
  'timings.histAria': 'Distribution {lo} – {hi}',
  'timings.build': 'build {build}',
  'timings.spansCount': 'spans: {count}',
  'timings.lag': 'lag {mib} MiB',
  'timings.empty': 'No span timings. Measure spans in the lesson with tracer.timeScope("name") to see them here during a run.',
  'timings.rowTooltip': '{where} — click to jump to editor, ▸ distribution',
  'timings.hint': 'Every span has recording overhead (hundreds of ns, several µs with streaming). Measure short tasks with an outer span outside tight loops.',
  'diagrams.abnormal': 'No diagram: the run did not exit normally, so Tracer destructors could not write diagrams.',
  'diagrams.none': 'This run did not produce any Tracer diagrams.',
  'diagrams.overBudget': 'Over budget',
  'diagrams.overBudgetTitle': 'A part exceeds the generation budget (020-04)',
  'diagrams.fullSize': 'Full size',
  'diagrams.error': 'Mermaid error: {error}',
  'diagrams.close': 'Close',
  'editor.changedOnDisk': '{path} — changed on disk (saving asks what to do)',
  'editor.changedWhileSaving': '{path}: changed again while saving. Try again.',
  'events.firstOnly': 'Showing the first {count} only.',
  'output.dropped': '… earlier lines dropped: {dropped} (keeping the last {max})',
};

export type MessageKey = keyof typeof ko;

/** Determine initial language from stored choice or browser language. */
export function initialLang(read: () => string | null, navLang: string): Lang {
  let stored: string | null = null;
  try {
    stored = read();
  } catch {
    /* blocked storage: fall back to the browser language */
  }
  if (stored === 'ko' || stored === 'en') return stored;
  return navLang.toLowerCase().startsWith('ko') ? 'ko' : 'en';
}

let current: Lang = initialLang(() => localStorage.getItem(LANG_KEY), navigator.language ?? '');

/** Get current language. */
export function lang(): Lang {
  return current;
}

const listeners: Array<(l: Lang) => void> = [];

/** Set active language, persist to localStorage, update DOM lang, and notify listeners. */
export function setLang(l: Lang): void {
  current = l;
  try {
    localStorage.setItem(LANG_KEY, l);
  } catch {
    /* private window: the choice lasts for this page only */
  }
  document.documentElement.lang = l;
  for (const cb of listeners) cb(l);
}

/** Register a listener called whenever the language changes. */
export function onLangChange(cb: (l: Lang) => void): void {
  listeners.push(cb);
}

/** Translate a message key, replacing {name} placeholders with values from params. */
export function t(key: MessageKey, params?: Record<string, string | number>): string {
  const dict = current === 'ko' ? ko : en;
  const raw: string = (dict as Record<string, string>)[key] ?? (ko as Record<string, string>)[key] ?? String(key);
  if (!params) return raw;
  return raw.replace(/\{([a-zA-Z0-9_]+)\}/g, (match, name) => {
    if (Object.prototype.hasOwnProperty.call(params, name) && params[name] !== undefined) {
      return String(params[name]);
    }
    return match;
  });
}

/** Return localized text and whether the Korean fallback was used. */
export function localized(koText: string, enText: string | null | undefined): { text: string; fallback: boolean } {
  if (current === 'ko') {
    return { text: koText, fallback: false };
  }
  if (enText && enText.trim().length > 0) {
    return { text: enText, fallback: false };
  }
  return { text: koText, fallback: true };
}

/** Apply translations to elements with data-i18n, data-i18n-title, or data-i18n-placeholder. */
export function applyStatic(root: ParentNode = document): void {
  document.documentElement.lang = current;
  const dict = current === 'ko' ? ko : en;

  const applyToElement = (el: Element): void => {
    const textKey = el.getAttribute('data-i18n');
    if (textKey && Object.prototype.hasOwnProperty.call(dict, textKey)) {
      el.textContent = t(textKey as MessageKey);
    }
    const titleKey = el.getAttribute('data-i18n-title');
    if (titleKey && Object.prototype.hasOwnProperty.call(dict, titleKey)) {
      if ('title' in el) {
        (el as HTMLElement).title = t(titleKey as MessageKey);
      }
    }
    const placeholderKey = el.getAttribute('data-i18n-placeholder');
    if (placeholderKey && Object.prototype.hasOwnProperty.call(dict, placeholderKey)) {
      if ('placeholder' in el) {
        (el as HTMLInputElement).placeholder = t(placeholderKey as MessageKey);
      }
    }
  };

  if (root instanceof Element) applyToElement(root);
  for (const el of root.querySelectorAll('[data-i18n], [data-i18n-title], [data-i18n-placeholder]')) {
    applyToElement(el);
  }
}
