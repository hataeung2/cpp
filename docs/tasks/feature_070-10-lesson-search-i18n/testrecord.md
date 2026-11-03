# Test record: 070-10 플레이그라운드 레슨·기능 검색과 한/영 전환

- Spec: [/docs/specs/070_10_lesson_search_i18n.md](/docs/specs/070_10_lesson_search_i18n.md)
- Plan and unit table: [plan.md](/docs/tasks/feature_070-10-lesson-search-i18n/plan.md)
- Date: 2026-11-02, branch `feature/070-10-lesson-search-i18n`

Browser checks: a Node script outside the repository drives the installed Edge (`playwright-core`, headless) against a playground started with `py -3 tools/playground.py --port 18781`. Each page starts in Korean (an init script stores `ko` on a tab's first load). The script asserts on the DOM and takes the screenshots in [`screenshots/`](/docs/tasks/feature_070-10-lesson-search-i18n/screenshots/). It never saves a file: the AC-8 edit check types a line into a tab and closes the page without Ctrl+S or Run, and `git status` shows no lesson file changed afterwards.

## Runs
| # | What | Expected | Actual | Status |
|---|---|---|---|---|
| R1 | `py -3 tools/test_lessons.py` after U1+U2 | all pass | 46 passed | Pass |
| R2 | same after the review fixes (stronger fixture, fixed key lists, CMake case that can fail, 6 new cases) | all pass | 50 passed | Pass |
| R3 | `py -3 tools/lessons.py check` after U3 | 0 errors, 0 warnings | `0 error(s), 0 warning(s); 2 track(s), 4 lesson(s), 2 unit(s)` | Pass |
| R4 | `npm --prefix web/frontend run build` after each frontend unit | `tsc` clean, bundle built | built every time; one failure after the U14 review fix (`TS7006` implicit `any` in `test/i18n.test.ts`, found by the reviewer), fixed with a type annotation | Pass |
| R5 | AC-7 negative check: delete `'tree.none'` from the `en` dictionary, `npx tsc --noEmit`, restore | `tsc` fails | `error TS2741: Property '"tree.none"' is missing in type …`, exit 1; restored file compiles | Pass |
| R6 | mutation check: remove `pushField(fields, info.ko)` from `search.ts`, run `test/search.test.ts`, restore | the ko-name test fails | `× finds a tag by its ko display name alone`, 1 failed / 16 passed; restored | Pass |
| R7 | `npm --prefix web/frontend test`, final | all pass | 7 files, 63 tests passed | Pass |
| R8 | browser script, first run | all pass | 15 search checks passed, then the script timed out: it changed only the URL hash of the same page (no reload). Script fixed (new query string) | script error |
| R9 | browser script, second run | all pass | 35/36; "language kept after reopening" failed because the script's init hook forces Korean on every new tab. Check changed to a reload of the same tab | script error |
| R10 | browser script, final build | all pass | 36/36 passed | Pass |
| R11 | `py -3 .agent/scripts/build.py --preset linux-x64-debug --test` | full suite passes | 17/17 (AllTests, PlaygroundServer 137 s, lesson smoke tests) | Pass |
| R12 | `py -3 .agent/scripts/build.py --preset windows-x64-debug --test` | full suite passes, zero warnings | 17/17, no warnings (warnings are errors in every preset) | Pass |
| R13 | `py -3 .agent/scripts/lint_docs.py`, `py -3 .agent/scripts/naming_check.py` | exit 0 | `0 error(s), 0 warning(s)`; `0 snake_case function name(s)` | Pass |

## Acceptance criteria
| AC | Evidence | Result |
|---|---|---|
| AC-1 | `test_lessons.py` `EnglishFieldsTest`: missing `title_en` (lesson, track) and empty `title_en` → WARN; `summary` without `summary_en` → WARN; `title_en = 3` → ERROR and no extra WARN; a multi-line `summary_en` placed before `id` that CMake's regex would misread → the existing CMake ERROR (R2) | Pass |
| AC-2 | `TagVocabularyTest`, one case per §2.2 row: file missing (one WARN, tag checks skipped), TOML error, bad key, `ko` or `en` missing, `aliases` not a list, non-table value, unknown lesson tag with the `tags` line, duplicate name across tags (NFC/NFD Hangul; and `ALPHA_TAG` vs another tag's key, casefold), alias equal to its own key not reported (R2) | Pass |
| AC-3 | `test_index_english_fields_and_readme_en` (exact `titleEn`/`summaryEn`, `""` → null, lesson and unit `readmeEn`), `test_index_tags_vocabulary` (`tags`, `{}` without the file), `test_index_keys` (fixed key lists: new keys added, existing kept, `version` 1); `PlaygroundServer` CTest passes (R2, R11) | Pass |
| AC-4 | R3: the repository's manifests give 0 errors and 0 warnings | Pass |
| AC-5 | `test/search.test.ts`, 17 cases: AND, case on both sides, NFC on both sides, Korean alias, tag ko name alone, English tag name, `lib:` path, track title and track `titleEn` alone, unit fields, no cross-field match, regex characters literal, empty/whitespace query, unknown tag by id; R6 shows a case fails when its rule is removed (R7) | Pass |
| AC-6 | R10: typing filters the tree (`jthread` → 2 lessons, count line `레슨 2 · 유닛 1`, [ac6-search-jthread.png](/docs/tasks/feature_070-10-lesson-search-i18n/screenshots/ac6-search-jthread.png)); `동시성`, `logger.hpp`, `state machine` (AND) find the right lesson; no results → no track groups and `검색 결과 없음` ([ac6-search-none.png](/docs/tasks/feature_070-10-lesson-search-i18n/screenshots/ac6-search-none.png)); Esc clears; `/` focuses the box from the page but types a slash inside Monaco; Enter with `isComposing` opens nothing; Enter opens the first lesson and highlights it; tag chips `스레드/thread`, `로그/log`, a click sets the query to `log` and filters ([ac6-tag-chips.png](/docs/tasks/feature_070-10-lesson-search-i18n/screenshots/ac6-tag-chips.png)) | Pass |
| AC-7 | R5 (`tsc` fails on a missing English key); `test/i18n.test.ts`: no Hangul in `src/*.ts` except `i18n.ts` and in `index.html`, same key set and placeholders in both dictionaries (> 50 keys, every entry line seen), `t()` placeholders, `localized()` fallback (R7) | Pass |
| AC-8 | R10: on `#thread_and_log` with an unsaved edit (`main.cpp ●`) and the query `thread`, the switch turns the top bar, `<html lang>`, lesson title, tree, tag chips (`Thread`, `Logging`) and placeholder English and shows the Korean-only notice; the ● tab, the query and the hash stay ([ac8-english.png](/docs/tasks/feature_070-10-lesson-search-i18n/screenshots/ac8-english.png)); a selected unit stays selected across a switch; the intro switches to `lessons/intro.en.md`; after a reload the page starts in English. During a run of `lambda_capture` the switch keeps Output, the run ends with `Exit code 0 · build … ms · run … ms`, and switching back redraws `종료 코드 0 · 빌드 … ms · 실행 … ms` ([ac8-english-after-run.png](/docs/tasks/feature_070-10-lesson-search-i18n/screenshots/ac8-english-after-run.png)). Blocked storage: `test/i18n.test.ts` with throwing `getItem`/`setItem` and with a throwing `window.localStorage` getter (R7) | Pass |
| AC-9 | R4, R7, R11, R12, R2 | Pass |
| AC-10 | R13; spec §8 rows: see Reviews (U3, U15) | Pass |

## Reviews
| Unit | Reviewer | Question | Findings | Resolution |
|---|---|---|---|---|
| U1+U2 | `cpp-reviewer` | §2.2/§2.3 conformance, consumers, tests that cannot fail | U1: no spec mismatch; a non-string `title_en` also got a "missing" WARN, duplicated `readme` helper, repeated comments. U2: index test mirrored the implementation, fixture `title_en` equal to `title`, CMake test could not fail, a trivial negative test, 4 rules without a test | all fixed by the lead; re-check: none |
| U4–U8 | `cpp-reviewer` | strings, switch scope, README choice, `relabel`, blocked storage | lesson title blank before a lesson is chosen; status line replaced by the limit text on a switch; unit selection and collapsed groups lost on re-render (moved to U10); Timings end note not translated; English plurals ("1 errors"); notice wording | fixed by the lead; re-check: `notify()` messages stayed in the old language → fixed (functions) |
| U9–U13 | `cpp-reviewer` | matching rules, tree, keys, chips, tests | Enter left a unit highlighted; a late `toggle` event could erase remembered collapsed groups; Ctrl+Enter in the box switched lessons; no chips without a README; tooltip not the tag id; 5 tests could not fail | fixed by the lead (5 tests added, R6); re-check: none |
| U14 | `cpp-reviewer` | AC-7/AC-8 tests | `<html lang>` check could not fail; header claimed Assumption 12; throwing storage getter not covered; regex key extraction unchecked | fixed by the lead; re-check found the fix broke `tsc` (R4), fixed |
| U3+U15 | `cpp-reviewer` | §8 complete and true to the code, translations, aliases, Assumption 14 | search field lists missed the lesson id and unit files; intro bullet did not name `intro.en.md`; English doc named only Korean UI labels; check warnings not listed; aliases: `std::variant`/`std::visit` and `unique_ptr` would block future tags, `std::stop_token`, `move_only_function`, `mutable`, `로깅`, `recordSpan` missing | fixed by the lead; re-check: none (side effect: `variant` finds nothing until E6 adds a `variant` tag, recorded in the [candidate list](/docs/tasks/lesson_candidates.md)) |

The review fixes were small (a line or a function each), so the lead applied them instead of a second agy round (delegation.md §6.1, "Fix rounds take the cheaper path"), and the same reviewer checked the lead's diff once.
