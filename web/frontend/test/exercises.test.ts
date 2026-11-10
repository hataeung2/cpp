// Tests for exercises panel: numbers, row generation, failure texts, and panel DOM (spec 070-17 U8).

import { afterEach, describe, expect, it, vi } from 'vitest';
import type { ExerciseData, ExerciseResult } from '../src/api';
import {
  exerciseNumbers,
  exerciseRows,
  failureText,
  ExercisesPanel,
} from '../src/exercises';
import { setLang } from '../src/i18n';

afterEach(() => {
  setLang('ko');
});

describe('exerciseNumbers', () => {
  it('computes numbers for ids with shared bases and letters (example from spec)', () => {
    const ids = ['values_a', 'values_b', 'values_c', 'scenario_steps', 'report_read'];
    expect(exerciseNumbers(ids)).toEqual(['1a', '1b', '1c', '2', '3']);
  });

  it('computes numbers for plain ids', () => {
    const plain = ['first_task', 'second_task', 'third_task'];
    expect(exerciseNumbers(plain)).toEqual(['1', '2', '3']);
  });
});

describe('failureText', () => {
  it('formats exit rule with nonzero', () => {
    setLang('en');
    expect(failureText({ rule: 'exit', expected: 'nonzero' })).toBe('The exit code should not be 0.');
    setLang('ko');
    expect(failureText({ rule: 'exit', expected: 'nonzero' })).toBe('종료 코드가 0이 아니어야 합니다.');
  });

  it('formats exit rule with numeric code', () => {
    setLang('en');
    expect(failureText({ rule: 'exit', expected: 1, actual: 0 })).toBe('The exit code should be 1 (now: 0).');
    setLang('ko');
    expect(failureText({ rule: 'exit', expected: 1, actual: 0 })).toBe('종료 코드가 1이어야 합니다(지금: 0).');
  });

  it('formats has rule with its params', () => {
    setLang('en');
    expect(failureText({ rule: 'has', file: 'main.cpp', pattern: 'std::function' })).toBe(
      '`main.cpp` has no line matching `std::function` yet.',
    );
    setLang('ko');
    expect(failureText({ rule: 'has', file: 'main.cpp', pattern: 'std::function' })).toBe(
      '`main.cpp`에 `std::function`에 맞는 줄이 아직 없습니다.',
    );
  });

  it('falls back to rule name for an unknown rule', () => {
    expect(failureText({ rule: 'custom_rule' })).toBe('custom_rule');
  });
});

describe('exerciseRows', () => {
  const baseData: ExerciseData = {
    lesson: '01_lambda_capture',
    exercises: [
      {
        id: 'remove_mutable',
        title: 'mutable 지우기',
        titleEn: null,
        kind: 'auto',
        hint: '람다 힌트',
        hintEn: 'Lambda hint',
        answer: '람다 해설',
        answerEn: 'Lambda answer',
        failHint: 'mutable만 지우세요',
        failHintEn: 'Remove only mutable',
      },
      {
        id: 'observe_capture',
        title: '참조 캡처 관찰',
        titleEn: 'Observe reference capture',
        kind: 'self',
        hint: null,
        hintEn: null,
        answer: null,
        answerEn: null,
        failHint: null,
        failHintEn: null,
      },
    ],
    progress: {},
    error: null,
  };

  it('retains recorded pass even when last run failed, and still shows run messages', () => {
    const dataWithProgress: ExerciseData = {
      ...baseData,
      progress: {
        remove_mutable: { passed: '2026-11-10T12:00:00Z', how: 'auto' },
      },
    };
    const lastRunFailed: ExerciseResult[] = [
      {
        id: 'remove_mutable',
        passed: false,
        checked: true,
        failures: [{ rule: 'build_fail' }],
      },
    ];

    setLang('ko');
    const rows = exerciseRows(dataWithProgress, lastRunFailed);
    expect(rows[0].status).toBe('passed');
    expect(rows[0].passedAt).toBe('2026-11-10T12:00:00Z');
    expect(rows[0].messages).toEqual([
      failureText({ rule: 'build_fail' }),
      'mutable만 지우세요',
    ]);
  });

  it('marks last-run passed without record as passed with passedAt null', () => {
    const lastRunPassed: ExerciseResult[] = [
      {
        id: 'remove_mutable',
        passed: true,
        checked: true,
        failures: [],
      },
    ];

    const rows = exerciseRows(baseData, lastRunPassed);
    expect(rows[0].status).toBe('passed');
    expect(rows[0].passedAt).toBeNull();
    expect(rows[0].messages).toEqual([]);
  });

  it('marks checked: false as unchecked', () => {
    const lastRunUnchecked: ExerciseResult[] = [
      {
        id: 'remove_mutable',
        passed: false,
        checked: false,
        failures: [{ rule: 'truncated' }],
      },
    ];

    const rows = exerciseRows(baseData, lastRunUnchecked);
    expect(rows[0].status).toBe('unchecked');
  });

  it('marks exercise with no result as none', () => {
    const rows = exerciseRows(baseData, null);
    expect(rows[0].status).toBe('none');
    expect(rows[0].passedAt).toBeNull();
    expect(rows[0].messages).toEqual([]);
  });

  it('appends fail hint only when there are failures', () => {
    const withFailures: ExerciseResult[] = [
      {
        id: 'remove_mutable',
        passed: false,
        checked: true,
        failures: [{ rule: 'build_fail' }],
      },
    ];
    setLang('ko');
    const rowsFail = exerciseRows(baseData, withFailures);
    expect(rowsFail[0].messages).toHaveLength(2);
    expect(rowsFail[0].messages[1]).toBe('mutable만 지우세요');

    const withoutFailures: ExerciseResult[] = [
      {
        id: 'remove_mutable',
        passed: true,
        checked: true,
        failures: [],
      },
    ];
    const rowsPass = exerciseRows(baseData, withoutFailures);
    expect(rowsPass[0].messages).toEqual([]);
  });

  it('falls back to Korean title with fallback flag when titleEn is missing in English mode', () => {
    setLang('en');
    const rows = exerciseRows(baseData, null);
    expect(rows[0].title).toEqual({
      text: 'mutable 지우기',
      fallback: true,
    });
    expect(rows[1].title).toEqual({
      text: 'Observe reference capture',
      fallback: false,
    });
  });
});

describe('ExercisesPanel (DOM via jsdom)', () => {
  it('hides answer text initially and displays it after clicking answer button', () => {
    const host = document.createElement('div');
    const onSelf = vi.fn();
    const onClear = vi.fn();
    const panel = new ExercisesPanel(host, { onSelf, onClear });

    const data: ExerciseData = {
      lesson: '01_lambda_capture',
      exercises: [
        {
          id: 'remove_mutable',
          title: 'mutable 지우기',
          titleEn: 'Remove mutable',
          kind: 'auto',
          hint: '힌트 문구입니다.',
          hintEn: 'Hint content',
          answer: '해설 정답 코드입니다.',
          answerEn: 'Answer solution code',
          failHint: null,
          failHintEn: null,
        },
      ],
      progress: {
        remove_mutable: { passed: '2026-11-10T12:00:00Z', how: 'auto' },
      },
      error: null,
    };

    setLang('ko');
    panel.show(data, 'practice');
    panel.render();

    // Answer text is not in the DOM initially
    expect(host.querySelector('.exercise-answer')).toBeNull();
    expect(host.textContent).not.toContain('해설 정답 코드입니다.');

    // Find and click the answer button
    const answerBtn = host.querySelector<HTMLButtonElement>('.exercise-btn-answer');
    expect(answerBtn).not.toBeNull();
    answerBtn!.click();

    // Answer text is now visible in the DOM
    expect(host.querySelector('.exercise-answer')).not.toBeNull();
    expect(host.textContent).toContain('해설 정답 코드입니다.');

    // Click again to toggle closed
    answerBtn!.click();
    expect(host.querySelector('.exercise-answer')).toBeNull();
    expect(host.textContent).not.toContain('해설 정답 코드입니다.');

    // Clear button triggers onClear handler
    const clearBtn = host.querySelector<HTMLButtonElement>('.exercise-btn-clear');
    expect(clearBtn).not.toBeNull();
    clearBtn!.click();
    expect(onClear).toHaveBeenCalledTimes(1);
  });
});
