// 070-10 AC-5: Lesson and unit search matching tests (§2.4, §4).
import { describe, expect, it } from 'vitest';
import type { LessonEntry, RunInfo, TagVocabulary, TrackEntry, UnitEntry } from '../src/api';
import { lessonHaystack, matches, normalize, queryTerms, unitHaystack } from '../src/search';

const defaultRun: RunInfo = {
  profile: 'quick',
  timeout: 5,
  build: null,
};

const makeLesson = (id: string, partial: Partial<LessonEntry> = {}): LessonEntry => ({
  id,
  title: id,
  titleEn: null,
  summary: '',
  summaryEn: null,
  path: `lessons/tracks/01_essentials/${id}`,
  target: id,
  entry: null,
  sources: ['main.cpp'],
  readme: 'README.md',
  readmeEn: null,
  uses: [],
  files: ['main.cpp'],
  tags: [],
  run: defaultRun,
  ...partial,
});

const makeTrack = (id: string, partial: Partial<TrackEntry> = {}): TrackEntry => ({
  id,
  title: id,
  titleEn: null,
  summary: '',
  summaryEn: null,
  path: `lessons/tracks/${id}`,
  lessons: [],
  ...partial,
});

const makeUnit = (id: string, partial: Partial<UnitEntry> = {}): UnitEntry => ({
  id,
  title: id,
  titleEn: null,
  summary: '',
  summaryEn: null,
  path: `lessons/units/${id}`,
  files: [],
  readme: 'README.md',
  readmeEn: null,
  uses: [],
  usedBy: [],
  ...partial,
});

const trackEssentials = makeTrack('01_essentials', {
  title: 'Essentials: 어느 시스템에나 필요한 것',
  titleEn: 'Essentials: what every system needs',
});

const vocabulary: TagVocabulary = {
  thread: {
    ko: '스레드',
    en: 'Thread',
    aliases: ['std::jthread', '동시성', 'concurrency'],
  },
  log: {
    ko: '로그',
    en: 'Logging',
    aliases: ['logger'],
  },
};

const lessonThreadAndLog = makeLesson('thread_and_log', {
  title: 'std::jthread 작업 스레드와 로거 연동',
  titleEn: 'std::jthread workers with the logger',
  summary: '두 개의 PeriodicWorker 스레드와 Logger를 활용한 주기적 작업 및 안전한 협력적 취소',
  summaryEn: 'Periodic work on two PeriodicWorker threads with the Logger, and cooperative cancellation',
  tags: ['thread', 'log'],
  uses: ['unit:jthread_worker', 'lib:atugcc/core/logger.hpp'],
});

const lessonLambdaCapture = makeLesson('lambda_capture', {
  title: '람다 캡처',
  titleEn: 'Lambda capture',
  tags: ['lambda'],
  uses: [],
});

const unitJthreadWorker = makeUnit('jthread_worker', {
  title: 'jthread 워커',
  titleEn: 'jthread worker',
  files: ['lessons/units/jthread_worker/jthread_worker.hpp'],
});

describe('search (AC-5)', () => {
  const haystackThreadAndLog = lessonHaystack(lessonThreadAndLog, trackEssentials, vocabulary);
  const haystackLambdaCapture = lessonHaystack(lessonLambdaCapture, trackEssentials, vocabulary);

  it('matches all terms with AND logic', () => {
    expect(matches(haystackThreadAndLog, 'jthread logger')).toBe(true);
    expect(matches(haystackThreadAndLog, 'jthread lambda')).toBe(false);
  });

  it('matches case-insensitively', () => {
    expect(matches(haystackThreadAndLog, 'JTHREAD')).toBe(true);
    expect(matches(haystackThreadAndLog, 'Logger.HPP')).toBe(true);
    expect(matches(haystackThreadAndLog, 'Logger.CPP')).toBe(false);
  });

  it('normalizes Unicode NFD to NFC in query and strings', () => {
    const nfd = '스레드'.normalize('NFD');
    const nfc = '스레드';
    expect(nfd).not.toBe(nfc);
    expect(normalize(nfd)).toBe(nfc);
    expect(matches(haystackThreadAndLog, nfd)).toBe(true);
    expect(matches(haystackThreadAndLog, '뮤텍스'.normalize('NFD'))).toBe(false);
  });

  it('finds a tag via its Korean alias', () => {
    expect(matches(haystackThreadAndLog, '동시성')).toBe(true);
    expect(matches(haystackLambdaCapture, '동시성')).toBe(false);
  });

  it('finds a tag via its English name', () => {
    expect(matches(haystackThreadAndLog, 'logging')).toBe(true);
    expect(matches(haystackLambdaCapture, 'logging')).toBe(false);
  });

  it('matches lib: header paths', () => {
    expect(matches(haystackThreadAndLog, 'logger.hpp')).toBe(true);
    expect(matches(haystackThreadAndLog, 'core/logger')).toBe(true);
    expect(matches(haystackThreadAndLog, 'state.hpp')).toBe(false);
  });

  it('matches lessons by track title in Korean or English', () => {
    expect(matches(haystackThreadAndLog, 'essentials')).toBe(true);
    expect(matches(haystackThreadAndLog, '시스템')).toBe(true);
    expect(matches(haystackThreadAndLog, '네트워크')).toBe(false);
  });

  it('matches units by files via unitHaystack and does not match lesson-only terms', () => {
    const uHaystack = unitHaystack(unitJthreadWorker);
    expect(matches(uHaystack, 'jthread_worker.hpp')).toBe(true);
    expect(matches(uHaystack, '동시성')).toBe(false);
  });

  it('does not match across field boundaries', () => {
    expect(matches(haystackThreadAndLog, 'workerlib')).toBe(false);
    expect(matches(haystackThreadAndLog, 'worker lib')).toBe(true);
  });

  it('treats regex metacharacters literally without throwing', () => {
    expect(() => matches(haystackThreadAndLog, 'std::jthread (')).not.toThrow();
    expect(matches(haystackThreadAndLog, 'std::jthread (')).toBe(false);

    const dotLesson = makeLesson('dot_lesson', { summary: 'a.b' });
    const dotHaystack = lessonHaystack(dotLesson, trackEssentials, vocabulary);
    expect(matches(dotHaystack, 'a.b')).toBe(true);
    expect(matches(dotHaystack, 'aXb')).toBe(false);

    const xLesson = makeLesson('x_lesson', { summary: 'aXb' });
    const xHaystack = lessonHaystack(xLesson, trackEssentials, vocabulary);
    expect(matches(xHaystack, 'a.b')).toBe(false);
  });

  it('matches everything on empty or whitespace-only queries and splits query terms correctly', () => {
    expect(matches(haystackThreadAndLog, '')).toBe(true);
    expect(matches(haystackThreadAndLog, '   ')).toBe(true);
    expect(matches(haystackThreadAndLog, '\t\n')).toBe(true);
    expect(queryTerms('  a   b ')).toEqual(['a', 'b']);
    expect(queryTerms('a\u0000b')).toEqual(['a', 'b']);
  });

  it('matches a tag missing from vocabulary by its id', () => {
    const lessonWithMissingTag = makeLesson('custom_lesson', {
      tags: ['missing_tag'],
    });
    const customHaystack = lessonHaystack(lessonWithMissingTag, trackEssentials, vocabulary);
    expect(matches(customHaystack, 'missing_tag')).toBe(true);
    expect(matches(customHaystack, 'other_tag')).toBe(false);
  });

  // Each case below isolates one field or one side of the normalization: the word appears nowhere else.
  const plainTrack = makeTrack('99_plain', { title: 'Plain' });

  it('finds a tag by its ko display name alone', () => {
    const tagged = lessonHaystack(makeLesson('x', { tags: ['log'] }), plainTrack, vocabulary);
    expect(matches(tagged, '로그')).toBe(true);
    expect(matches(lessonHaystack(makeLesson('x'), plainTrack, vocabulary), '로그')).toBe(false);
  });

  it('normalizes the haystack side to NFC', () => {
    const nfdTitle = makeLesson('x', { title: '동시성 예제'.normalize('NFD') });
    expect(matches(lessonHaystack(nfdTitle, plainTrack, {}), '동시성')).toBe(true);
  });

  it('lowercases the haystack side', () => {
    const upper = makeLesson('x', { title: 'QWERTY Lesson' });
    expect(matches(lessonHaystack(upper, plainTrack, {}), 'qwerty')).toBe(true);
  });

  it("includes the track's English title", () => {
    const track = makeTrack('98_t', { title: '트랙', titleEn: 'Zebra track' });
    expect(matches(lessonHaystack(makeLesson('x'), track, {}), 'zebra')).toBe(true);
  });

  it("includes a unit's title, English summary and uses", () => {
    const unit = makeUnit('u', { title: '워커 유닛', summaryEn: 'Periodic quokka', uses: ['lib:atugcc/core/ring_buffer.hpp'] });
    const haystack = unitHaystack(unit);
    expect(matches(haystack, '워커')).toBe(true);
    expect(matches(haystack, 'quokka')).toBe(true);
    expect(matches(haystack, 'ring_buffer')).toBe(true);
    expect(matches(haystack, 'jthread')).toBe(false);
  });
});
