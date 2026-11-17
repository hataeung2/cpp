# Test record: 070-25 무인 확인을 흐리는 KI 정리 (KI-050, KI-052, KI-053)

- Spec: [/docs/specs/070_25_unattended_check_fixes.md](/docs/specs/070_25_unattended_check_fixes.md)
- Plan: [plan.md](plan.md)
- Hosts: Windows 11 (MSVC, `windows-x64-debug`, `windows-x64-release`), WSL2 Ubuntu 24.04 (Clang 20, libstdc++ 14, `linux-x64-debug`). 2026-11-16.

## Runs
| # | What | Expected | Result | Verdict |
|---|---|---|---|---|
| R1 | `lesson_device_state_machine` (`windows-x64-debug`) run 20 times in a row | every run reaches 6 ticks and `final state: RUN` | 20 / 20 (`total ticks:` ≥ 6) | Pass |
| R2 | `practice_error_expected` with the `remove_catch` answer applied, run directly (`windows-x64-debug`, no debugger) | no dialog, nonzero exit within 5 s, one stderr line | exit 3 after 114 ms, stderr `abort() has been called` | Pass |
| R3 | solve script (scratch, outside the repo): applies the answers of `remove_catch`, `remove_join`, `emergency_state` to practice copies, runs `tools/exercises.py check <id> --preset windows-x64-debug`, then resets the copies and puts `practice/progress.json` back | the three exercises pass, no time-out | all three `pass (new)`; 29 s for three lessons (build + run); `practice.py status` afterwards: every copy `same` | Pass |
| R4 | the same script in WSL, `linux-x64-debug` | the three pass | all three `pass (new)` | Pass |
| R5 | KI-052 reproduction: `npm --prefix web/frontend test` and `cd web/frontend && npm test`, started from cmd after `cd /d` with a lower-case and an upper-case drive letter, before the fix | — | lower case: 13 / 13 files fail ("Vitest failed to find the current suite") in both forms; upper case: 13 / 13 pass. PowerShell (upper case) passed. The Bash tool of this session first started with a lower-case drive and failed the same way | cause found |
| R6 | tried in `vite.config.ts` (not kept): `root` with an upper-case drive, then also `process.chdir` | — | still 13 / 13 fail with a lower-case drive | rejected |
| R7 | after the fix (`scripts/vitest.mjs`): cmd lower-case × both forms, cmd upper-case `--prefix`, Git Bash `/c/…` with `--prefix`, `npm --prefix web/frontend test -- search`, `npm --prefix web/frontend run build` | pass | 13 / 13 files, 164 tests each; the filter run 1 file, 17 tests; build ok | Pass |
| R8 | frontend tests in WSL | — | not runnable: WSL has Node 18.19.1, Vitest 5.0.5 needs `^22.12.0 \|\| ^24 \|\| >=26`; it fails at start-up (`SyntaxError: Missing } in template expression`) with and without the launcher. The frontend tests have only ever run on the Windows host | N/A |
| R9 | `py -3 .agent/scripts/build.py --preset linux-x64-debug --test` (WSL) | all pass, 0 warnings | 61 / 61, no `warning` line | Pass |
| R10 | `py -3 .agent/scripts/build.py --preset windows-x64-debug --test --report` | all pass, 0 warnings | 61 / 61 (`CrashDump`, `lesson.log_recovery`, `lesson.thread_and_log.exercises_verify` included), no `warning C`; report `out/test-reports/windows-x64-debug/20261116-162158/` | Pass |
| R11 | `py -3 .agent/scripts/build.py --preset windows-x64-release --test --label lesson` | all pass | 42 / 42 | Pass |
| R12 | `py -3 tools/lessons.py check`, `py -3 .agent/scripts/lint_docs.py` | 0 errors | 0 errors 0 warnings (21 lessons), 0 errors 0 warnings | Pass |

Note (R8 aside): an earlier WSL frontend attempt hung WSL (even `echo` timed out). Two leftover `wsl.exe` test servers (`web/server/server.py --port 0`, test origin :9000, started 15:36) were stopped and the distribution restarted with `wsl --terminate Ubuntu`; nothing of the user's was listening on the playground ports. WSL answered at once afterwards.

## AC evidence
| AC | Evidence | Verdict |
|---|---|---|
| AC-1 | R2 (exit 3 in 114 ms, one stderr line), R3 `remove_catch` pass on `windows-x64-debug` without a time-out | Pass |
| AC-2 | R3 and R4 `remove_join` pass on both presets; the unchanged lesson fails both rules (`exit 0`, `thread_.join()` present): `lesson.thread_and_log.exercises_verify` passed in R9 and R10 | Pass |
| AC-3 | R10 `CrashDump` and `lesson.log_recovery` passed | Pass |
| AC-4 | `crt_report.cpp` is `#if defined(_WIN32) && defined(_DEBUG)` as a whole; R9 (Clang) and R11 (MSVC Release) pass; codex review: none | Pass |
| AC-5 | R1 (20 / 20), R3 and R4 `emergency_state` pass without changing a wait; README pair and `exercises.toml` no longer mention raising a wait | Pass |
| AC-6 | R5 (cause), R7 (PowerShell, cmd and Git Bash, both forms); WSL: R8, not runnable on this host's Node (no frontend test ever ran there). Documented command unchanged; `web/README.md` names the launcher | Pass (WSL N/A) |
| AC-7 | `git grep` for dialog-waiting sentences: only the "run under a debugger" case is left (reviewer Q2); after the review the stderr line is said for Debug builds only; KI-050, 052, 053 CLOSED and moved by `archive_docs.py`; R12 | Pass |

## Reviews
| Unit | Reviewer | Question | Findings | Resolution |
|---|---|---|---|---|
| U1, U3 | codex `luna` (`--effort high`, read-only) | U1 against Assumptions 2–4, AC-1/AC-4, `init_seg` order, linker dropping, MSVC/Clang; U3 thread safety, one count-down, no endless wait, `constexpr` local in the lambda | VERDICT: none. Not checked: runtime behaviour (read-only) | runtime covered by R2, R3, R10 |
| U2, U4, U5 | `cpp-reviewer` | `remove_join` rules vs. original and answer; no dialog-waiting text, Korean = English; state-machine texts vs. code; launcher passes all arguments, no change on Linux | VERDICT: none. Not confirmed: whether Windows Release prints the `abort()` line | texts narrowed to "a Debug build prints …" (lead, 6 sentences in 3 files); Release prints were not measured |

No `agy` call was made: every unit was `lead (small)` or a doc unit (plan.md).
