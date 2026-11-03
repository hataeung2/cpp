# Walkthrough: 070-03 essentials 트랙 커리큘럼

- Spec: [/docs/specs/070_03_essentials_curriculum.md](/docs/specs/070_03_essentials_curriculum.md) (approved 2026-11-03)
- Evidence: [testrecord.md](/docs/tasks/feature_070-03-essentials-curriculum/testrecord.md) (every AC passes), plan and unit table: [plan.md](/docs/tasks/feature_070-03-essentials-curriculum/plan.md)

## Result
- **Curriculum**: the essentials track has a final order of 14 lessons (syntax → time and files → threads and logs). Folder numbers are the final positions; empty numbers are reserved for 070-11 (E1, E5, E6, E14) and 070-12 (E8, E9, E12). `02_thread_and_log` and `03_span_timing` moved to `11_` and `14_`; lesson ids did not change. The order is in the folder column of [lesson_candidates.md](/docs/tasks/lesson_candidates.md).
- **Four new lessons**, each with Korean and English README:
  - [`format_text`](/lessons/tracks/01_essentials/02_format_text/README.en.md): `std::format` positional arguments, width/fill/alignment, bases and precision, a `std::formatter` for `Vec2`, `std::format_to`, `std::vformat` and `std::format_error`. `std::print` is in the README only (KI-033).
  - [`error_expected`](/lessons/tracks/01_essentials/04_error_expected/README.en.md): the same port parser with exceptions and with `core::Expected`, chained with `and_then` / `transform` / `or_else`.
  - [`source_location`](/lessons/tracks/01_essentials/05_source_location/README.en.md): macro → default argument → forwarding wrapper → location attached to the format string, ending with `Logger::log`.
  - [`log_recovery`](/lessons/tracks/01_essentials/12_log_recovery/README.en.md): a two-run lesson; each run ends with `std::_Exit(0)` before three log lines are drained, and the next run recovers them from the memory-mapped buffer (010-10).
- **Korean/English for the existing material**: `README.en.md` for the 4 existing lessons and 2 units; `intro.en.md` links go to the English READMEs. Program output is English everywhere (`thread_and_log`, `device_state_machine` changed). Lesson and unit code comments are bilingual: a Korean line (or paragraph) followed by the English one (user decision 2026-11-03).
- **Checks**: `lessons.py check` warns when a lesson or unit has no `README.en.md`, and when a lesson source or unit file has Hangul inside a string or character literal (comments are not checked). The repository has 0 warnings.
- **Tags**: `format`, `error`, `source_location`, `recovery`; the page's search finds the new lessons by `expected`, `__LINE__`, `포맷`, `복구`, `std::format`.

## Changes found during the task (spec History has each)
- `std::quick_exit` → `std::_Exit` for `log_recovery`, found by a design probe before the plan: `quick_exit` is a clean exit for the Logger, which then deletes the map file. `_Exit` is "not covered" by the Logger contract; the READMEs say the lesson relies on the OS keeping the mapped file, not on a promise.
- `LessonConsoleCodePage` (090-06 AC-9) used the Korean heading of `device_state_machine` to prove UTF-8 console output. Its expected line is now `══ State Transitions ══`, another non-ASCII line of the same lesson.
- `PlaygroundServer` `test_seed_lessons_and_units_are_listed` asserted the exact lesson list; it now checks the seed lessons in order with other lessons allowed between them.
- Reviews corrected several older README claims in both languages (`std::visit` dispatch, `std::thread` terminate rule, the closure member of the counter) and the U4 review's paragraph-form comments led to the AC-5 wording "each run of Korean comment lines is followed by English".

## Units and authors
Code units U1, U2, U7–U10 were written by agy `flash`; U3–U6 and U11–U13 by the lead. Review fixes were applied by the lead as `review fixes lead (small)` (delegation.md §6.1) and re-checked once by the same reviewer. No `lead (fallback)` unit.

## Follow-ups
- KI-033: `std::print` in lessons once the Linux toolchain has GCC 14.
- KI-034: `lessons.py` does not reject duplicate `sources` / `files` entries (duplicate WARNs).
- 070-11, 070-12: the remaining essentials lessons (BACKLOG; their place in the order of work is the user's decision).
