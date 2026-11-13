# Walkthrough: 070-20 Exercise definitions for the remaining lessons

## Result
Every lesson now has an `exercises.toml`: the 12 remaining essentials lessons and `02_patterns/01_device_state_machine` (13 files, 41 exercises: 28 automatic, 13 observation). Any lesson opens with an Exercises tab and an `n/m` count in the tree. No tool, rule or screen was added; the files use the 070-17 rules only.
- Split items: `format_text` 3 (`println_a`, `println_b`) and `modules` 3 (`import_a`, `import_b`).
- `14_span_timing` README (both languages): exercise 2 now says the practice copy's `lesson.toml` is read-only, so it is done in original-edit mode or locally and restored with `git restore` (Assumption 6a).
- `device_state_machine` README (both languages): the section title `## 4. 연습 과제` / `## 4. Exercises` became `## 연습` / `## Exercises`; `lessons.py check` only counts items under `## 연습` (Assumption 6b).
- [`lessons/README.md`](/lessons/README.md): examples and the criteria for automatic versus observation exercises (§8).

Evidence: [testrecord.md](testrecord.md). Every automatic exercise was solved on the practice copy and passes `tools/exercises.py check` on `windows-x64-debug` (MSVC) and `linux-x64-debug` (Clang 20, libstdc++ 14); the observation exercises whose answers state a compiler or tool result were run once to confirm the statement.

## Notes
- No exercise changed class (automatic ↔ observation) compared with the approved table. The classification test of Assumption 2 was run for the two exercises the spec left open (`const_return_int`: MSVC builds it, Clang fails with `-Wignored-qualifiers`, so it stays observation).
- Answers corrected by running the code: `ranges_to_msvc` (on Linux the pipe form also fails, with the `std::forward_like` error of KI-033, not only the range formatting), `emergency_state` (needs a longer `sleep_for`: KI-053), `relaxed_tsan` (TSan reports the race on the heap block of the ring and the process ends with exit code 66 even though the output says `all cases verified: true`), `parse_invalid_date`, `raw_file_time`, `copy_recursive` (`remove_all` removes 4 more entries).
- The `cpp-reviewer` found ten issues (two weak `source.has` rules, a hint that offered an example that cannot be done, a wrong UI label in the English text, hints that printed the solving code against Assumption 7, and similar); all were fixed in one round. See Reviews in the testrecord.
- `practice/` is untracked; the solve loop used `tools/practice.py reset` after every exercise and removed its progress records.

## Follow-ups
- [KI-053](/docs/known_issues.md): `device_state_machine` waits 120 ms in `main`; the worker may not reach `tick == 4`, which README exercise 1 suggests. The exercise text tells the reader to raise the wait.
- No `lead (fallback)` unit: no sub-agent wrote any code.
