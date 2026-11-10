# Test record: 070-17 연습 과제 확인

- Spec: [/docs/specs/070_17_exercise_check.md](/docs/specs/070_17_exercise_check.md)
- Plan: [plan.md](plan.md)
- Hosts: Windows 11 (MSVC 14.51, `windows-x64-debug`), WSL2 Ubuntu 24.04 (Clang 20.1.2, `linux-x64-debug`, `linux-x64-asan`, the web's `linux-x64-playground`). Browser: Chrome through the Claude-in-Chrome extension against `tools/playground.py --port 8790`.
- "Web" in AC-2 means Clang 20 with libstdc++ 14, the web's compiler: `wsl -e python3 tools/exercises.py check <id> --preset linux-x64-debug` runs the same `check_practice` as the server; one exercise was also solved through the page (R9).

## Runs
| # | What | Expected | Result | Verdict |
|---|---|---|---|---|
| R1 | compiler texts for the pilot rules: `lambda_capture` copy without `mutable`, and with `std::function<int()> holder`, `build.py --target practice_lambda_capture` on both presets | real error lines | MSVC `error C3491: 'count': a by copy capture cannot be modified in a non-mutable lambda`; Clang `cannot assign to a variable captured by copy in a non-mutable lambda`. `std::function`: MSVC `C2338 … must be copy constructible`, libstdc++ `std::function target must be copy-constructible` → rules `captured by copy in a non-mutable lambda\|C3491`, `must be copy[- ]constructible` | Pass |
| R2 | `dangling_return` answer on `linux-x64-asan` | ASan `stack-use-after-return` | `return [&local]{…};` is a build error on Clang 20 (`-Wreturn-stack-address`, `-Werror`); through a named variable it builds and `ASAN_OPTIONS=detect_stack_use_after_return=1` reports `stack-use-after-return … main.cpp:20:32`. Hint and answer say both | Pass |
| R3 | `exercises.py verify <id> --preset windows-x64-debug` for the three lessons (builds the original) | exit 0 | 3 × "no automatic exercise passes on the unchanged lesson" | Pass |
| R4 | each automatic exercise solved by its answer in the practice copy, `exercises.py check` on `windows-x64-debug` and (WSL) `linux-x64-debug`; copy reset between exercises | the solved one passes, the others fail with their reasons | table AC-2 below | Pass except `remove_catch` on MSVC Debug (KI-050) |
| R5 | mutation: an extra exercise `expect = ['listen on :8080']` (printed by the unchanged `error_expected`), `verify --exe <built lesson_error_expected.exe>` | exit 1 | `error: exercise 'mutation_probe' … passes on the unchanged lesson`, exit 1; file restored → exit 0 | Pass |
| R6 | `build.py --preset windows-x64-debug --test --label lesson` (U4) | 3 verify tests registered and pass | 20/20, `lesson.{lambda_capture,error_expected,testing}.exercises_verify` passed | Pass |
| R7 | `py -3 tools/test_exercises.py`, `tools/test_lessons.py`, `tools/test_practice.py`; `py -3 tools/lessons.py check` | pass; 0 / 0 | 32 OK, 98 OK, 15 OK; 0 errors, 0 warnings | Pass |
| R8 | `npm --prefix web/frontend test`, `npm --prefix web/frontend run build` (PowerShell; the Git Bash shell cannot start vitest on `main` either) | pass | 9 files, 99 tests; build ok | Pass |
| R9 | browser, `lambda_capture` in practice mode (below) | AC-3, AC-4, AC-7 checks | all pass | Pass |
| R10 | AC-5: after R9, `wsl -e python3 tools/exercises.py check lambda_capture --preset linux-x64-debug` on the same copy | the page's verdicts, same record | `remove_mutable` fail (build log, `lacks`), `function_holder` pass; `list` shows the page's `dangling_return` (self) and `function_holder` (auto) records | Pass |
| R11 | `build.py --preset linux-x64-debug --test` | all pass | 38/38 (incl. `PlaygroundServer` with the fixture and 3 × `exercises_verify`) | Pass |
| R12 | `build.py --preset windows-x64-debug --test` | all pass, 0 warnings | 38/38, 0 warnings (incl. 3 × `exercises_verify`) | Pass |
| R13 | `build.py --preset linux-x64-debug --test --label playground` after U7 (R11 may have started before U7's tests were written) | pass | `PlaygroundServer` passed (130 s: the whole `test_server.py` with the fixture, U7's 11 tests included) | Pass |
| R14 | `py -3 .agent/scripts/lint_docs.py` | 0 / 0 | 0 errors, 0 warnings | Pass |

Browser checks of R9: the panel tab `Exercises`/`연습` follows README; the tree shows `passed/total` for the three pilot lessons; **기록 지우기** asks in the page dialog, clears `lambda_capture` only (tree `0/3`, the other lessons kept `3/3`, `2/5`, AC-4); with the copy's `holder` changed to `std::function<int()>`, Run → build fails (`errors: 2`), the tab gets the news dot, opening the tab removes it; #3 `✓ passed (time)`, #1 `✗ failed in the last run` with the build-log and `lacks` reasons and the `fail_hint`; the answer's text is not in the DOM before **Answer** is clicked and is after (AC-3); in Korean every label and title is Korean (`연습`, `자동 확인`, `스스로 확인`, `힌트`, `해설`); the self box records `how: self` and the tree becomes `2/3`; original mode shows `원본 편집 모드입니다. 과제는 연습 모드에서 확인합니다.`, practice mode removes it. Screenshots: failure/pass, answer expanded, Korean (kept outside the repo).

## AC-2: pilot exercises solved by their answers
| Lesson | Exercise | Change in the practice copy | Clang 20 (web compiler) | MSVC `windows-x64-debug` |
|---|---|---|---|---|
| `lambda_capture` | `remove_mutable` | `lambda_capture.hpp` (unit copy): `mutable` removed | pass | pass |
| | `dangling_return` | observation (ASan, R2) | — | — |
| | `function_holder` | `main.cpp`: `std::function<int()> holder` | pass (and through the page, R9) | pass |
| `error_expected` | `remove_catch` | `main.cpp`: the `out_of_range` catch clause removed | pass (`SIGABRT`) | **not passed**: the Debug CRT `abort()` dialog waits for a click, the check reaches its 10 s limit (`not_finished`). KI-050 |
| | `transform_expected` | `main.cpp`: `.and_then([](std::uint16_t p) -> core::Expected<std::string> {…})` | pass | pass |
| | `port_error` | `main.cpp`: `PortError`, `parsePort` → `std::expected<std::uint16_t, PortError>`, `parsePortCore` with `transform_error` | pass | pass |
| `testing` | `values_a` | `test_version.cpp`: `ASSERT_EQ(result->minor, 5u)`, `EXPECT_EQ(result->patch, 7u)` | pass | pass |
| | `values_b`, `values_c`, `report_read` | observation | — | — |
| | `scenario_steps` | `scenario_version_file.cpp`: `out << "1.2.3\n"` | pass | pass |

In every run the other automatic exercises of the lesson failed with their own reasons (e.g. `unmodified` is never the only reason once a copy changed; a pass recorded earlier stays recorded). Unchanged originals: R3, and `exercises_verify` in R6, R11.

## Acceptance criteria
| AC | Evidence | Verdict |
|---|---|---|
| AC-1 | `test_exercises.py` (R7): every rule passing and failing, `exit` int / `nonzero` (code and signal) / `any`, unchanged copy never passes, any one changed copy counts, Stop and time limit → `not_finished`, cut output → `checked: false`; server tests (R11/R13) pass Stop and time limit through `RunResult.stopped` | Pass |
| AC-2 | table above; R3, R5, R6, R11 | Pass on Clang (web); MSVC Debug: 6 of 7, `remove_catch` blocked by the `abort()` dialog (KI-050) — needs the user's decision |
| AC-3 | R9; `test/exercises.test.ts` (rows, hidden answer until clicked) | Pass |
| AC-4 | `test_exercises.py` (record kept after the copy is reset, `clear` one lesson), `test_server.py` (`test_post_exercises_clear`, `test_practice_reset_preserves_exercise_progress`), R9 (records are in `practice/progress.json`, so every browser sees them), R10 | Pass |
| AC-5 | R10 | Pass |
| AC-6 | `test_lessons.py` (R7): ERROR for broken TOML and an unknown `source.file`, WARN for a README count mismatch, none when it matches; `lessons.py check` on the repository 0 / 0 | Pass |
| AC-7 | R9 (Korean and English labels), `i18n.test.ts` (same keys and placeholders in both dictionaries, no Hangul outside `i18n.ts`), `exercises.test.ts` (English falls back to Korean with the flag) | Pass |
| AC-8 | R7, R8, R11–R14; docs of §8 updated (lessons/README "연습 과제 정의", web/README API and Page, intro pages, lesson_candidates, agent_todo) | Pass |

## Reviews
| Unit | Reviewer | Question | Findings | Resolution |
|---|---|---|---|---|
| U4 | codex luna | CMake test matches §2.2 and is safe on every preset | a 3.11 `find_package` after `tests/` cached a 3.8+ interpreter could leave the tests silently unregistered | same request as `tests/`, then a version check with a warning |
| U1, U2, U3 | codex luna (high) | code matches spec and plan; tests check it | unreadable copy raised out of `check_practice`; missing WARN cases, multi-file `modified`, cross-platform refusal untested | `_practice_texts` + `OSError` → `exercisesError`; 4 tests added |
| U6–U10 | codex luna | server and page match spec and plan | (1) unreadable `exercises.toml` answers 200 with `error`; (2) run results applied to a lesson selected after the run started | (1) kept: spec §4 shows a broken file in the panel; (2) `run()` keeps `runLessonId` |
| lead fixes | codex luna | each fix resolves its finding, tests can fail | none | — |

The Claude `cpp-reviewer` (the plan's fresh reviewer) stopped at its usage limit during its first review; every review went to codex `luna` instead, which is also of another family than the author (agy `flash`).
