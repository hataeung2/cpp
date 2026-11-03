// Lesson and unit search matching functions (spec 070-10 §2.4).

import type { LessonEntry, TrackEntry, UnitEntry, TagVocabulary } from './api';

/** Normalizes Unicode (NFC), lowercases, replaces control chars, and collapses whitespace. */
export function normalize(s: string): string {
  return s
    .normalize('NFC')
    .toLowerCase()
    .replace(/[\u0000-\u001f\u007f]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function pushField(fields: string[], raw: string | null): void {
  const norm = raw ? normalize(raw) : '';
  if (norm) fields.push(norm);
}

/** Builds a NUL-separated searchable haystack of normalized fields for a lesson. */
export function lessonHaystack(
  lesson: LessonEntry,
  track: TrackEntry,
  tags: TagVocabulary,
): string {
  const fields: string[] = [];
  pushField(fields, lesson.id);
  pushField(fields, lesson.title);
  pushField(fields, lesson.titleEn);
  pushField(fields, lesson.summary);
  pushField(fields, lesson.summaryEn);
  pushField(fields, track.title);
  pushField(fields, track.titleEn);
  for (const tagId of lesson.tags) {
    pushField(fields, tagId);
    const info = tags[tagId]; // a tag missing from the vocabulary still contributes its id
    if (!info) continue;
    pushField(fields, info.ko);
    pushField(fields, info.en);
    for (const alias of info.aliases) pushField(fields, alias);
  }
  for (const use of lesson.uses) pushField(fields, use);
  return fields.join('\u0000');
}

/** Builds a NUL-separated searchable haystack of normalized fields for a unit. */
export function unitHaystack(unit: UnitEntry): string {
  const fields: string[] = [];
  pushField(fields, unit.id);
  pushField(fields, unit.title);
  pushField(fields, unit.titleEn);
  pushField(fields, unit.summary);
  pushField(fields, unit.summaryEn);
  for (const file of unit.files) pushField(fields, file);
  for (const use of unit.uses) pushField(fields, use);
  return fields.join('\u0000');
}

/** Splits a normalized query string into search terms. */
export function queryTerms(query: string): string[] {
  // normalize turns the field separator U+0000 into a space, so no term can span two fields
  return normalize(query).split(' ').filter(Boolean);
}

/** Returns true if all query terms match as substrings of the haystack (AND matching). */
export function matches(haystack: string, query: string): boolean {
  return queryTerms(query).every((term) => haystack.includes(term)); // never a RegExp: the query is literal
}
