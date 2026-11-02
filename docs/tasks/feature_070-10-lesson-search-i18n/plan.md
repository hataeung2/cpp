# Plan: 070-10 플레이그라운드 레슨·기능 검색과 한/영 전환

- Spec: [/docs/specs/070_10_lesson_search_i18n.md](/docs/specs/070_10_lesson_search_i18n.md) (approved 2026-11-02)
- Branch: `feature/070-10-lesson-search-i18n` (from `main` at `6d94d85`)

## Design
Three layers, built in this order so each one can be checked before the next uses it:
1. **Data** (`tools/lessons.py`, manifests, `lessons/tags.toml`): English fields and the tag vocabulary reach the index. The page is not touched yet; `lessons.py check` and `test_lessons.py` prove it.
2. **Language** (`i18n.ts`, then every module's strings): one dictionary per language, typed so a missing English entry fails `tsc`. Modules ask `t(key)` at render time, never at import time, so a language switch only has to re-render.
3. **Search** (`search.ts`, tree filter, search box, tag chips): pure matching functions first (testable without DOM), then the tree uses them.

### Data (spec §2.2, §2.3)
- `Track`, `Lesson`, `Unit` gain `title_en: str = ""`, `summary_en: str = ""` (read with `str_field(..., required=False)`). WARN when `title` is set and `title_en` is empty; WARN when `summary` is set and `summary_en` is empty. Track: only when `track.toml` exists.
- `Tag` dataclass (`id`, `ko`, `en`, `aliases`, `line`); `Catalog.tags: dict[str, Tag] | None` (`None` = no `lessons/tags.toml`). Read by `load_tags()` **before** the units and tracks, so `load()` can check each lesson's `tags` with the manifest text at hand (`line_of(text, "tags")`).
- `load_tags()` findings (spec §2.2 table): file missing → one WARN, tag checks skipped; TOML error → ERROR (existing `read_toml`); top-level value not a table → ERROR; key not `[a-z0-9_]+` → ERROR; `ko`/`en` missing or not a string → ERROR; `aliases` not a list of strings → ERROR. Line = the `[key]` header's line. A tag with a field error is still registered (no cascade of "unknown tag" warnings).
- Duplicate names: each tag's names = key, `ko`, `en`, aliases, normalized (`unicodedata.normalize("NFC")`, `casefold()`, whitespace collapsed). A name that belongs to two tags → WARN at the later tag's header. A name repeated inside one tag is fine.
- Index (`version` stays 1): tracks, lessons, units get `titleEn`, `summaryEn` (`None` when empty); lessons and units get `readmeEn` (`<folder>/README.en.md` when the file exists, else `None`); top level `tags: {id: {ko, en, aliases}}` in file order, `{}` when the vocabulary is missing. No existing key changes.
- Python style follows the file (snake_case functions); the camelCase rule is for C++ (`naming_check.py`).

### Language (spec §2.4, Assumptions 9–12)
`web/frontend/src/i18n.ts`:
```text
type Lang = 'ko' | 'en'                 LANG_KEY = 'atugcc.lang'
ko = { '<module>.<name>': '…', … } as const      en: Record<keyof typeof ko, string>
t(key, params?)        '{name}' placeholders; unknown placeholder left as is
lang(), setLang(l)     setLang stores (try/catch), sets <html lang>, calls listeners
onLangChange(cb)
localized(ko, en)      → { text, fallback }: en mode with empty/null en → ko text, fallback true
applyStatic(root)      data-i18n (textContent), data-i18n-title, data-i18n-placeholder
initialLang(read, navLang)   exported for tests: stored 'ko'|'en', else navLang starts with 'ko' → ko, else en
```
- Keys are grouped by module prefix (`top.`, `tree.`, `readme.`, `run.`, `timings.`, `diagrams.`, `editor.`, `events.`, `output.`, `search.`, `lang.`).
- Module-level constant arrays that hold labels (Timings columns) keep a **key**, and the label is looked up when rendering.
- `main.ts` keeps what the README panel shows (`{kind: 'lesson' | 'unit' | 'intro' | 'other', entry}`) so a language switch re-shows the right file; a Markdown page reached through a link (`other`) is left as it is.
- The phase label is built in `tick()` from the last `phase` event data, so a switch during a run shows in the next tick.
- README choice: English and `readmeEn` → that file; English without it → `readme` with the notice; intro: English → `lessons/intro.en.md`, falling back to `lessons/intro.md` with the notice when it cannot be read (`ReadmePanel.show(path, {notice, alternate, tags})`).
- jsdom reports `navigator.language = 'en-US'`, so tests that assert Korean text call `setLang('ko')` first.

### Search (spec §2.4, Assumptions 5–8)
`web/frontend/src/search.ts` (no DOM):
```text
normalize(s)                     NFC, toLowerCase, control characters → space, whitespace collapsed, trimmed
lessonHaystack(lesson, track, tags)   id, title(+En), summary(+En), track title(+En), tags + each tag's ko/en/aliases, uses
unitHaystack(unit)               id, title(+En), summary(+En), files, uses
matches(haystack, query)         every whitespace-separated term of normalize(query) is a substring; '' matches all
```
Fields are joined with `\u0000` (normalize removes it from the query), so no match spans two fields.
- `LessonTree.render(index, selected?, query = '')` returns `{lessons, units}` visible counts; hides non-matching items, tracks with no visible lesson and the units group with no visible unit; open groups while a query is set; `firstVisibleLesson()` for Enter. The `problems` box is never filtered.
- Keys: `/` focuses the box unless the event target is an input, textarea, select, contenteditable or inside `.monaco-editor`; in the box, Esc clears (and blurs when already empty), Enter opens `firstVisibleLesson()`; both ignored while `isComposing` (or `keyCode === 229`).
- Tag chips: the README panel shows the lesson's tags (`label` = current-language name, `title` = tag id); a click calls `onTag(id)`, which sets the box to the id and filters.

## Units
Order: tool → tool test → content → page language (mechanism, then modules) → search → frontend tests → docs.

| Unit | File | Change (what, where, AC) | Check | Risky | Author | Reviewer | Tokens (in / out) | Status |
|---|---|---|---|---|---|---|---|---|
| U1 | `tools/lessons.py` | English fields + WARNs, `load_tags()` and its checks, lesson tag check, index keys (§2.2, §2.3; AC-1–AC-3) | `grep -c "title_en\|load_tags\|readmeEn"`; `lessons.py check` on the repo shows the expected new WARNs only; `lessons.py index --out -` has the keys; `test_lessons.py` (failures only from the valid tree's missing English) | no | agy flash | | | |
| U2 | `tools/test_lessons.py` | valid tree gets English + `tags.toml`; cases for AC-1–AC-3 | `py -3 tools/test_lessons.py` | no | agy flash | | | |
| U3 | 8 manifests, `lessons/tags.toml` [NEW], `lessons/intro.en.md` [NEW] | English fields, 9 tags with aliases, intro in English (§2.5; AC-4) | `lessons.py check` ERROR 0 / WARN 0; link check of `intro.en.md` | no | lead | | — | |
| U4 | `web/frontend/src/i18n.ts` [NEW], `src/api.ts` | i18n mechanism; index types (`titleEn`, `summaryEn`, `readmeEn`, `tags`) (§2.4; AC-7) | `npm run build` | no | agy flash | | | |
| U5 | `web/frontend/index.html`, `src/main.ts` (+ keys in `i18n.ts`) | static text → `data-i18n`; language button; `main.ts` strings → `t()`; re-render on switch; README/intro choice (AC-8) | `npm run build`; Hangul count 0 in both files | no | agy flash | | | |
| U6 | `src/lessonTree.ts`, `src/readme.ts` (+ keys) | strings → `t()`; `localized()` titles with `fallback` class; README notice, `alternate` (AC-8) | `npm run build`; Hangul count 0 | no | agy flash | | | |
| U7 | `src/timings.ts`, `src/diagrams.ts` (+ keys) | strings → `t()`; column titles by key; `TimingsPanel.relabel()` (AC-8) | `npm run build`; Hangul count 0 | no | agy flash | | | |
| U8 | `src/editor.ts`, `src/events.ts`, `src/output.ts` (+ keys) | 4 strings → `t()` | `npm run build`; Hangul count 0 | no | lead (small) | | — | |
| U9 | `src/search.ts` [NEW] | §2.4 search functions (AC-5) | `npm run build` | no | agy flash | | | |
| U10 | `src/lessonTree.ts` | `render(…, query)` filter, counts, `firstVisibleLesson()` (AC-6) | `npm run build` | no | agy flash | | | |
| U11 | `index.html`, `src/main.ts`, `src/theme.css` | search box, count line, keys and IME guard, ↻ keeps the query; styles for search, fallback, notice, chips (AC-6) | `npm run build` | no | agy flash | | | |
| U12 | `src/readme.ts`, `src/main.ts` | tag chips and `onTag` (Assumption 8; AC-6) | `npm run build` | no | agy flash | | | |
| U13 | `test/search.test.ts` [NEW] | AC-5 cases | `npm test` | no | agy flash | | | |
| U14 | `test/i18n.test.ts` [NEW], `test/timings.test.ts` | AC-7 Hangul scan, `t()`, `localized()`, `initialLang()`, throwing storage (AC-8); timings tests pin `ko` | `npm test` | no | agy flash | | | |
| U15 | `lessons/README.md`, `web/README.md`, `lessons/intro.md`, `intro.en.md`, `docs/specs/070_01_lesson_structure.md`, `docs/tasks/lesson_candidates.md` | spec §8 (AC-10) | `lint_docs.py` exit 0 | no | lead | | — | |

No unit is risky (no C++, no concurrency; the frontend is single-threaded). Reviews: `cpp-reviewer` per unit; units that share files and land in sequence (U4–U8, U9–U12, U13–U14) are reviewed together, one review call per group, each unit named in the question.

## Verification (spec §12)
- `py -3 tools/test_lessons.py`, `py -3 tools/lessons.py check`
- `npm --prefix web/frontend run build`, `npm --prefix web/frontend test`; AC-7 negative check: delete one key from `en`, `npm run build` fails, restore
- `py -3 .agent/scripts/build.py --preset linux-x64-debug --test` (PlaygroundServer, lesson smoke tests)
- `py -3 .agent/scripts/lint_docs.py`
- Browser (AC-6, AC-8): screenshots in `screenshots/`
