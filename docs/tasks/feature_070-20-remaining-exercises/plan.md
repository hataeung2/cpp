# Plan: 070-20 Exercise definitions for the remaining lessons

- Spec: [/docs/specs/070_20_remaining_exercises.md](/docs/specs/070_20_remaining_exercises.md) (approved 2026-11-12)
- Branch: `feature/070-20-remaining-exercises` (from `main` at `2a45516`)

## Model assignment
No C++ source changes: every unit is lesson text (`exercises.toml`, README), a doc unit, so the lead writes them ([delegation.md](/.agent/rules/delegation.md) §1, "Ordinary doc"). The fresh reviewer (`cpp-reviewer`, Agent tool) reads each bundle once. The machine check is the solve-and-check loop of Assumption 8: every automatic exercise is solved on the practice copy with a script (`exverify.py`, kept in the lead's scratch directory, not committed) and checked by `tools/exercises.py check` on `windows-x64-debug` (MSVC) and `linux-x64-debug` (WSL, Clang 20 + libstdc++ 14).

## Design
- Format and rules are those of 070-17; nothing new is added to the tools.
- Naming: ids are the spec's draft ids, except the split items, whose two ids share a base (`println_a` / `println_b`, `import_a` / `import_b`): the group count of `lessons.py check` removes only one trailing `_<letter>`.
- Regex targets were checked against the real sources (no pattern may match a comment line or the unchanged original): `^\s*` anchors for code lines, `source.lacks` on call lines, never on a name that also occurs in comments.
- Compiler wording: `build_expect` carries Clang and MSVC phrases with `|`. Each was confirmed on both compilers when the exercise was solved.
- Classification changes made in DEV (spec Assumption 2): none of the spec's automatic exercises moved to observation, and no observation exercise moved to automatic. `const_return_int` stays observation (MSVC builds `const int makeInt()` fine, Clang fails with `-Wignored-qualifiers`).
- Two answers were corrected by running the code: `emergency_state` needs `sleep_for(250 ms)` in `main` (Windows reaches only 3–4 ticks in 120 ms), and `ranges_to_msvc` (the pipe form of `ranges::to` also fails on Linux, with the `std::forward_like` error of KI-033).

## Unit table
| Unit | File | Change (what, where, AC) | Check | Risky | Author | Reviewer | Tokens | Status |
|---|---|---|---|---|---|---|---|---|
| U1 | `02_format_text`, `03_const_correctness`, `05_source_location`, `06_concepts` `exercises.toml` | bundle 1: 12 exercises, 11 automatic (AC-1, AC-3, AC-5) | `lessons.py check`; solve + `exercises.py check` on both presets | no | lead | cpp-reviewer | — | done |
| U2 | `07_ranges_views`, `08_variant_visit`, `09_chrono_time`, `10_filesystem_paths` `exercises.toml` | bundle 2: 12 exercises | same | no | lead | cpp-reviewer | — | done |
| U3 | `12_log_recovery`, `13_lock_free_buffer`, `14_span_timing` `exercises.toml`; `14_span_timing` `README.md`, `README.en.md` | bundle 3: 9 exercises; exercise 2 sentence (Assumption 6a, AC-6) | same; README read | no | lead | cpp-reviewer | — | done |
| U4 | `15_modules`, `02_patterns/01_device_state_machine` `exercises.toml`; `device_state_machine` `README.md`, `README.en.md` | bundle 4: 7 exercises; section title `## 연습` (Assumption 6b) | same | no | lead | cpp-reviewer | — | done |
| U5 | `lessons/README.md`, `docs/agent_todo.md` | observation criteria sentence, examples (§8) | `lint_docs.py` | no | lead | cpp-reviewer | — | done |

Order: bundle 1 → bundle 4 are independent files; the solve loop ran per bundle, the full suites ran once at the end.
