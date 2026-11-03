# Walkthrough: 070-10 플레이그라운드 레슨·기능 검색과 한/영 전환

- Spec: [/docs/specs/070_10_lesson_search_i18n.md](/docs/specs/070_10_lesson_search_i18n.md) (approved 2026-11-02)
- Tests and AC evidence: [testrecord.md](/docs/tasks/feature_070-10-lesson-search-i18n/testrecord.md); units: [plan.md](/docs/tasks/feature_070-10-lesson-search-i18n/plan.md)

## Result
- **Lesson format** (for 070-03 and later): manifests take `title_en`, `summary_en`; tags come from the vocabulary [`lessons/tags.toml`](/lessons/tags.toml) (Korean and English name, search aliases). `tools/lessons.py check` warns about missing English, unknown tags and names shared by two tags; the index carries `titleEn`, `summaryEn`, `readmeEn` and `tags`. All existing manifests are filled in (check: 0 errors, 0 warnings).
- **Search**: a box above the lesson tree filters lessons and units as you type, by title, summary (both languages), tag names and aliases, `uses` (unit ids, header paths), ids and track titles. `/` jumps to it, Esc clears, Enter opens the first lesson; a lesson's tags appear as chips above its README and search for that tag.
- **Korean/English**: the `EN` / `한` button switches every UI text (all in [`i18n.ts`](/web/frontend/src/i18n.ts); a missing English entry fails the build), the titles and tag names, and the README (`README.en.md` when present, else the Korean one with a notice; the intro has `lessons/intro.en.md`). Editor tabs, a running lesson and its output stay as they are. The choice is kept in the browser.
- **Rules for lesson work** (written in [`lessons/README.md`](/lessons/README.md) and the [candidate list](/docs/tasks/lesson_candidates.md)): lesson programs print English; English READMEs and the English output of the existing lessons are done by 070-03 together with the existing lessons (user decisions 2026-11-02).

## Verification
Linux and Windows full suites 17/17; tool tests 50; frontend tests 63; browser script 36/36 with screenshots; docs and naming gates clean. Details and review history in the test record.

## Follow-ups
None registered as a KI. The lesson candidate E6 now says to add a `variant` tag (`std::variant`, `std::visit`) and put it on `device_state_machine`: this task took those names out of the `state` tag so a future lesson can own them. Out of scope by the spec: lesson README translations and English output of existing lessons (070-03), full-text code search and fuzzy search (a KI when the lesson count makes it necessary), public use (070-05).

## Notes
- No unit was written by the lead as a fallback. Review fixes were applied by the lead as small changes and re-checked once by the same reviewer (delegation.md §6.1); see the unit table.
- One run order change: U6 before U5 (`main.ts` needed the new `ReadmePanel.show` options).
