// Exercises panel: exercise list, verification status, hints, answers, and progress (spec 070-17 §2.1, AC-3, AC-7).

import DOMPurify from 'dompurify';
import { marked } from 'marked';
import type {
  ExerciseData,
  ExerciseFailure,
  ExerciseResult,
} from './api';
import { localized, t, type MessageKey } from './i18n';
import type { Mode } from './practice';

const KNOWN_RULES = new Set([
  'unmodified',
  'not_finished',
  'build_fail',
  'build_ok',
  'build_expect',
  'not_run',
  'exit',
  'expect',
  'forbid',
  'truncated',
  'missing_file',
  'has',
  'lacks',
]);

export interface LocalizedText {
  text: string;
  fallback: boolean;
}

export interface Row {
  id: string;
  number: string;
  title: LocalizedText;
  kind: 'auto' | 'self';
  status: 'passed' | 'failed' | 'unchecked' | 'none';
  passedAt: string | null;
  messages: string[];
  hint: LocalizedText | null;
  answer: LocalizedText | null;
}

/** Compute README item numbers (e.g. values_a, values_b -> 1a, 1b; plain -> 1, 2). */
export function exerciseNumbers(ids: string[]): string[] {
  const parsed = ids.map((id) => {
    const m = id.match(/^(.+)_([a-z])$/);
    return m ? { id, base: m[1], letter: m[2] } : { id, base: id, letter: null };
  });

  const baseCounts = new Map<string, number>();
  for (const p of parsed) {
    if (p.letter !== null) {
      baseCounts.set(p.base, (baseCounts.get(p.base) ?? 0) + 1);
    }
  }

  const baseToNum = new Map<string, number>();
  let nextNum = 1;
  const result: string[] = [];

  for (const p of parsed) {
    let num = baseToNum.get(p.base);
    if (num === undefined) {
      num = nextNum++;
      baseToNum.set(p.base, num);
    }
    if (p.letter !== null && (baseCounts.get(p.base) ?? 0) > 1) {
      result.push(`${num}${p.letter}`);
    } else {
      result.push(`${num}`);
    }
  }

  return result;
}

/** Translate a failure rule with params to localized user text. */
export function failureText(f: ExerciseFailure): string {
  if (f.rule === 'exit' && f.expected === 'nonzero') {
    return t('exercise.fail.exitNonzero');
  }

  if (!KNOWN_RULES.has(f.rule)) {
    return f.rule;
  }

  const params: Record<string, string | number> = {
    pattern: f.pattern ?? '',
    file: f.file ?? '',
    line: f.line ?? '',
    expected: f.expected ?? '',
    actual: f.actual ?? '',
  };

  return t(('exercise.fail.' + f.rule) as MessageKey, params);
}

/** Produce display rows combining exercise definitions, recorded progress, and last run results. */
export function exerciseRows(
  data: ExerciseData,
  results: ExerciseResult[] | null,
): Row[] {
  if (!data || !data.exercises) {
    return [];
  }

  const numbers = exerciseNumbers(data.exercises.map((e) => e.id));
  const rows: Row[] = [];

  for (let i = 0; i < data.exercises.length; i++) {
    const def = data.exercises[i];
    const num = numbers[i] ?? `${i + 1}`;
    const title = localized(def.title, def.titleEn);
    const hint = def.hint ? localized(def.hint, def.hintEn) : null;
    const answer = def.answer ? localized(def.answer, def.answerEn) : null;

    let status: 'passed' | 'failed' | 'unchecked' | 'none' = 'none';
    let passedAt: string | null = null;

    const progress = data.progress?.[def.id];
    const res = results ? results.find((r) => r.id === def.id) : undefined;

    if (progress) {
      status = 'passed';
      passedAt = progress.passed;
    } else if (res) {
      if (res.passed) {
        status = 'passed';
        passedAt = null;
      } else if (res.checked === false) {
        status = 'unchecked';
        passedAt = null;
      } else {
        status = 'failed';
        passedAt = null;
      }
    } else {
      status = 'none';
      passedAt = null;
    }

    const messages: string[] = [];
    if (def.kind !== 'self' && res && res.failures && res.failures.length > 0) {
      for (const f of res.failures) {
        messages.push(failureText(f));
      }
      if (def.failHint) {
        messages.push(localized(def.failHint, def.failHintEn).text);
      }
    }

    rows.push({
      id: def.id,
      number: num,
      title,
      kind: def.kind,
      status,
      passedAt,
      messages,
      hint,
      answer,
    });
  }

  return rows;
}

export class ExercisesPanel {
  private currentData: ExerciseData | null = null;
  private currentMode: Mode = 'practice';
  private currentResults: ExerciseResult[] | null = null;
  private currentRunError: string | null = null;
  private readonly openHints = new Set<string>();
  private readonly openAnswers = new Set<string>();

  constructor(
    private readonly host: HTMLElement,
    private readonly handlers: {
      onSelf(id: string, done: boolean): void;
      onClear(): void;
    },
  ) {}

  show(data: ExerciseData | null, mode: Mode): void {
    this.currentData = data;
    this.currentMode = mode;
    this.currentResults = null;
    this.currentRunError = null;
    this.openHints.clear();
    this.openAnswers.clear();
    this.render();
  }

  setResults(results: ExerciseResult[] | null, error?: string | null): void {
    this.currentResults = results;
    this.currentRunError = error ?? null;
    this.render();
  }

  render(): void {
    const elements: HTMLElement[] = [];

    if (this.currentMode === 'original') {
      const notice = document.createElement('div');
      notice.className = 'exercise-notice';
      notice.textContent = t('exercise.originalMode');
      elements.push(notice);
    }

    if (this.currentData?.error) {
      const errDiv = document.createElement('div');
      errDiv.className = 'exercise-notice error';
      errDiv.textContent = t('exercise.loadError', { error: this.currentData.error });
      elements.push(errDiv);
    }

    if (this.currentRunError) {
      const runErrDiv = document.createElement('div');
      runErrDiv.className = 'exercise-notice error';
      runErrDiv.textContent = t('exercise.runError', { error: this.currentRunError });
      elements.push(runErrDiv);
    }

    if (!this.currentData || !this.currentData.exercises || this.currentData.exercises.length === 0) {
      const noneDiv = document.createElement('div');
      noneDiv.className = 'exercise-notice';
      noneDiv.textContent = t('exercise.noneDefined');
      elements.push(noneDiv);
    } else {
      const list = document.createElement('ol');
      list.className = 'exercises';

      const rows = exerciseRows(this.currentData, this.currentResults);

      for (const row of rows) {
        const item = document.createElement('li');
        item.className = 'exercise';

        const header = document.createElement('div');
        header.className = 'exercise-header';

        const numSpan = document.createElement('span');
        numSpan.className = 'exercise-num';
        numSpan.textContent = row.number;

        const titleSpan = document.createElement('span');
        titleSpan.className = 'exercise-title' + (row.title.fallback ? ' fallback' : '');
        titleSpan.textContent = row.title.text;

        const kindSpan = document.createElement('span');
        kindSpan.className = 'exercise-kind';
        kindSpan.textContent = row.kind === 'auto' ? t('exercise.auto') : t('exercise.self');

        header.append(numSpan, titleSpan, kindSpan);
        item.appendChild(header);

        const statusDiv = document.createElement('div');
        statusDiv.className = `exercise-status ${row.status}`;
        let statusText = '';
        if (row.status === 'passed') {
          const timeStr = row.passedAt
            ? new Date(row.passedAt).toLocaleString()
            : new Date().toLocaleString();
          statusText = t('exercise.passed', { time: timeStr });
        } else if (row.status === 'failed') {
          statusText = t('exercise.failed');
        } else if (row.status === 'unchecked') {
          statusText = t('exercise.unchecked');
        } else {
          statusText = t('exercise.none');
        }
        statusDiv.textContent = statusText;
        item.appendChild(statusDiv);

        if (row.messages.length > 0) {
          const ul = document.createElement('ul');
          ul.className = 'exercise-messages';
          for (const msg of row.messages) {
            const li = document.createElement('li');
            li.className = 'exercise-message';
            li.textContent = msg;
            ul.appendChild(li);
          }
          item.appendChild(ul);
        }

        const actions = document.createElement('div');
        actions.className = 'exercise-actions';

        if (row.kind === 'self') {
          const label = document.createElement('label');
          label.className = 'exercise-self-label';
          const checkbox = document.createElement('input');
          checkbox.type = 'checkbox';
          checkbox.checked = Boolean(this.currentData?.progress?.[row.id]);
          checkbox.addEventListener('change', () => {
            this.handlers.onSelf(row.id, checkbox.checked);
          });
          const span = document.createElement('span');
          span.textContent = t('exercise.selfDone');
          label.append(checkbox, span);
          actions.appendChild(label);
        }

        if (row.hint) {
          const hintBtn = document.createElement('button');
          hintBtn.type = 'button';
          hintBtn.className = 'btn btn-sm exercise-btn-hint';
          hintBtn.textContent = t('exercise.hint');
          hintBtn.addEventListener('click', () => {
            if (this.openHints.has(row.id)) {
              this.openHints.delete(row.id);
            } else {
              this.openHints.add(row.id);
            }
            this.render();
          });
          actions.appendChild(hintBtn);
        }

        if (row.answer) {
          const answerBtn = document.createElement('button');
          answerBtn.type = 'button';
          answerBtn.className = 'btn btn-sm exercise-btn-answer';
          answerBtn.textContent = t('exercise.answer');
          answerBtn.addEventListener('click', () => {
            if (this.openAnswers.has(row.id)) {
              this.openAnswers.delete(row.id);
            } else {
              this.openAnswers.add(row.id);
            }
            this.render();
          });
          actions.appendChild(answerBtn);
        }

        item.appendChild(actions);

        if (this.openHints.has(row.id) && row.hint) {
          const hintBlock = document.createElement('div');
          hintBlock.className = 'exercise-hint';
          if (row.hint.fallback) {
            const notice = document.createElement('div');
            notice.className = 'exercise-notice';
            notice.textContent = t('exercise.fallback');
            hintBlock.appendChild(notice);
          }
          const content = document.createElement('div');
          content.innerHTML = DOMPurify.sanitize(marked.parse(row.hint.text) as string);
          hintBlock.appendChild(content);
          item.appendChild(hintBlock);
        }

        if (this.openAnswers.has(row.id) && row.answer) {
          const answerBlock = document.createElement('div');
          answerBlock.className = 'exercise-answer';
          if (row.answer.fallback) {
            const notice = document.createElement('div');
            notice.className = 'exercise-notice';
            notice.textContent = t('exercise.fallback');
            answerBlock.appendChild(notice);
          }
          const content = document.createElement('div');
          content.innerHTML = DOMPurify.sanitize(marked.parse(row.answer.text) as string);
          answerBlock.appendChild(content);
          item.appendChild(answerBlock);
        }

        list.appendChild(item);
      }

      elements.push(list);
    }

    const hasProgress = Boolean(
      this.currentData?.progress && Object.keys(this.currentData.progress).length > 0,
    );
    if (hasProgress) {
      const clearBtn = document.createElement('button');
      clearBtn.type = 'button';
      clearBtn.className = 'btn btn-sm exercise-btn-clear';
      clearBtn.textContent = t('exercise.clear');
      clearBtn.addEventListener('click', () => {
        this.handlers.onClear();
      });
      elements.push(clearBtn);
    }

    this.host.replaceChildren(...elements);
  }
}
