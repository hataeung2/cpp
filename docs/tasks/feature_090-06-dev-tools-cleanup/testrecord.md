# Test Record: 090-06 개발 도구 정비 (KI-008, KI-011, KI-012)

- Spec: [/docs/specs/090_06_dev_tools_cleanup.md](/docs/specs/090_06_dev_tools_cleanup.md)
- Plan: [plan.md](plan.md)
- Branch: `feature/090-06-dev-tools-cleanup`; hosts: Windows 11 (MSVC, VS 2026), WSL2 Ubuntu 24.04 (GCC 13); Python 3.15 on Windows.

## Runs

| # | Test | Expected | Actual | Status |
|---|---|---|---|---|
| R1 | Baseline probe of the old guard, 13 sample commands (scratch `guard_probe.py`) | — | 7 wrongly denied (heredoc data, `grep "cmake -B"`, `grep -n cmake -B 3`, `echo "git commit"`, `git log --grep commit`, commit message mentioning a configure, heredoc with `git commit`), 1 missed (`& cmake "-S" "." "-B" "out"`). Drafting the spec, a Bash call whose heredoc held `git commit` text was itself refused | recorded |
| R2 | Baseline KI-012: `build.py --preset linux-x64-tsan --target atugcc_tests --gtest-filter LoggerTest.RecordsCallerLocation` | — | no output, exit 66 | recorded |
| R3 | Baseline KI-011: hidden cp949 console, UTF-8 bytes printed, screen read back (scratch `screen_probe.py`, U3a) | — | at 949: `=== ?곕???異붿쟻 寃곌낵 횞 쨉s ??===`; at 65001: `=== 터미널 추적 결과 × µs ⏱ ===` | recorded |
| R4 | U1a table tests on the old code | new rows fail | 17 guard-level wrong denials plus missing `simple_commands` / `is_git_commit` | Pass (tests can fail) |
| R5 | `test_agent_scripts.py` after U1b round 1 | all pass | 57 OK; review then found 10 missed classes (compound commands a regression), 3 over-denials | superseded |
| R6 | Review cases added to the table, before round 2 | fail on round 1 | 46 failing rows | Pass (tests can fail) |
| R7 | `test_agent_scripts.py` after round 2, move to `shell_commands.py`, lead fixes | all pass | 58 OK (1.6 s) | Pass |
| R8 | Mutants U1: M1 old regex instead of splitting; M2 no recursion into shell strings | both fail the table | M1: 33 failing subtests; M2: 13 | Pass |
| R9 | Extra adversarial cases (scratch `u1b_extra.py`, 38 cases incl. `<<-`, `$'…'`, `wsl -d X --`, PowerShell `<# #>`, `--%`) | as expected | 38/38; 100k-word command 0.2 s; 20-deep `$(` → `None` (regex fallback) | Pass |
| R10 | Move of the scanner from `agent_common.py` to `shell_commands.py` (scratch `move_parser.py`) | no block lost | `ast` comparison: 0 top-level blocks lost; tests pass | Pass |
| R11 | AC-4 live hook (Bash): heredoc data with `git commit -m "never run cmake -S …"` and `cmake -S . -B build` | runs | ran, 2 lines written | Pass |
| R12 | AC-4 live hook (Bash): real `cmake -S . -B <scratch>` | refused | `Ad-hoc CMake configure is not allowed (non-negotiable rule 2)…` | Pass |
| R13 | AC-4 live hook (PowerShell): here-string data with both texts | runs | ran, output `2` | Pass |
| R14 | U2 unit tests (`test_steps_and_batch`, `test_bad_filter`, `test_run_passes_step_environment`) | pass | pass | Pass |
| R15 | AC-5: `build.py --preset linux-x64-tsan --target atugcc_tests --gtest-filter LoggerTest.RecordsCallerLocation` | launcher, 1 test, exit 0 | `1: Test command: /usr/bin/setarch "x86_64" "-R" …/atugcc_tests`, `Running 1 test`, `PASSED 1 test`, exit 0 | Pass |
| R16 | AC-5 failure side: temporary mutant `ASSERT_EQ(lines.size(), 4u)` in `LoggerTest.RecordsCallerLocation`, same command; file restored after | exit ≠ 0 | `test_logger.cpp:100: Failure`, exit 8; `git diff` of the test file empty after restore | Pass |
| R17 | AC-6: `build.py --preset windows-x64-debug --target atugcc_tests --gtest-filter "LoggerTest.*"`; then `Nothing.Matches` | N ≥ 1; 0 visible | `GTEST_FILTER=LoggerTest.* ctest … -R ^AllTests$ --verbose`, `Running 8 tests`, exit 0; `Running 0 tests from 0 test suites`, exit 0 | Pass |
| R18 | AC-6 dry run `--preset windows-x64-debug --gtest-filter Nothing.Matches --dry-run` | batch shows `set` and ctest | `set "GTEST_FILTER=Nothing.Matches"` then `ctest --preset windows-x64-debug -R ^AllTests$ --verbose` | Pass |
| R19 | AC-7: `build.py --preset linux-x64-debug --gtest-filter 'A%B'` | exit 2 before any step | `error: --gtest-filter must not contain %`, exit 2 (unit test covers `"`, `\n`, `\r` on a Windows and a Linux preset with `subprocess.run` not called) | Pass |
| R20 | U3b builds: `lesson_device_state_machine` on `windows-x64-debug` and `linux-x64-debug` | 0 warnings | built (warnings are errors in every preset) | Pass |
| R21 | AC-8/AC-9 driver on the first U3c version, mutants M3–M5 | each mutant fails | M3 (no restore) **survived**: `chcp` without arguments did not show the output code page. Driver changed to read `GetConsoleOutputCP()` from a child in the same console | Fail → fixed |
| R22 | Same, after the change; restored code also failed check 3 | restored passes | rows of the screen buffer drift after wide characters (a Korean character fills two cells, read back once); screen now searched unsplit | Fail → fixed |
| R23 | AC-8/AC-9 mutants M3–M5 on the final driver | each fails, restored passes | M3: check 1 `after=65001`, check 3 `after=65001`; M4: check 1 `dtor=949`; M5: check 1 `run=949`, check 3 `found=False`; restored: all three PASS, exit 0 | Pass |
| R24 | `windows-x64-debug --test` (before the Python 3.10 gate and the U1b lead fixes, which do not touch C++) | all pass | 17/17, `LessonConsoleCodePage` passed 0.96 s | Pass |
| R25 | `linux-x64-debug --test` | all pass | 17/17, exit 0 | Pass |
| R26 | `linux-x64-tsan --test` | all pass, no TSan warning | 17/17, exit 0, no `ThreadSanitizer` line | Pass |
| R27 | U2 review finding checked: a batch file with `echo -R ^AllTests$` and `echo -R "^AllTests$"` | — | prints `-R AllTests$` (caret removed by cmd) and `-R "^AllTests$"`: the Windows filter run had lost the `^` anchor | Fail → fixed (`batch_arg` quotes arguments with cmd metacharacters) |
| R28 | `test_batch_arguments_reach_the_program_unchanged` (runs a real batch: `^AllTests$`, `a b`, `x&y`, `Tracer*:-Tracer.Slow`) and its mutant (plain `list2cmdline`) | passes; mutant fails | passes; mutant: cmd error `'y' is not recognized…`, test fails | Pass |
| R29 | `windows-x64-debug --test` on the final C++ and CMake tree (Python 3.10 gate included) | all pass | 17/17, `LessonConsoleCodePage` passed 0.98 s, exit 0 | Pass |
| R30 | AC-6 again after the batch quoting change: `--gtest-filter "LoggerTest.*"` on `windows-x64-debug` | 8 tests, exit 0 | `Running 8 tests`, exit 0 | Pass |
| R31 | `test_agent_scripts.py`, `naming_check.py`, `lint_docs.py` on the final tree | all pass | 59 OK; 0 snake_case function names; 0 errors, 0 warnings | Pass |

## Acceptance Criteria Evidence

| AC | Criterion (short) | Evidence | Result |
|---|---|---|---|
| AC-1 | mentions are allowed | `CommandPositionTest.test_mentions_are_allowed` (R7); before: R1, R4; M1 kills it (R8) | Pass |
| AC-2 | real runs are denied | `test_runs_are_denied` (R7); M2 kills the shell-string rows (R8) | Pass |
| AC-3 | unsplittable → regex; guard fails open on its own errors | `test_unsplittable_falls_back_to_regex`, `GuardHookTest` (R7) | Pass |
| AC-4 | live hook | R11–R13 | Pass |
| AC-5 | TSan filter run | R15, R16 (before: R2) | Pass |
| AC-6 | Windows filter run, 0-match visible, dry run | R17, R18, R14 | Pass |
| AC-7 | bad filter refused | R19, R14 | Pass |
| AC-8 | code page set, kept through static destruction, restored; pipe untouched | `LessonConsoleCodePage` checks 1–2, R23 | Pass |
| AC-9 | real lesson readable on a cp949 console; all lessons link it | check 3 (R23); `lessons/CMakeLists.txt` links `atugcc_lesson_console` into every `lesson_<id>` in the manifest loop | Pass |
| AC-10 | no regression | R25, R26, R29, R31 (zero warnings: every preset builds with warnings as errors) | Pass |

## Reviews

| Unit | Reviewer | Question | Findings | Resolution |
|---|---|---|---|---|
| U1b round 1 | cpp-reviewer | missed runs, over-denials, exceptions, plan deviations, style | 10 missed classes (compound `for`/`if`/`while`/`!` — a regression; `&>`/`>&`; substitutions in redirect targets and `<<<`; unquoted heredoc bodies; `@"…"@`; text piped into a shell; wrapper options; PowerShell `iex`/`.`/`Start-Process`; `git --attr-source`), 3 over-denials (commit idiom `"$(cat <<'EOF' … it's …)"`, `<<\EOF`, `bash tool.sh -c`), no exceptions in 200k fuzz; dense one-line style | plan D1' (R1–R10) written from the findings; author round 2 (`--resume`) |
| U1b round 2 | cpp-reviewer (re-review) | are the findings resolved, new problems | all resolved except: option values before `-c`/`-Command` hide the script (regression: `pwsh -ExecutionPolicy Bypass -Command`), quadratic `words[1:]`, `env -S`, `timeout --signal=`, unrecorded catch-all | review fixes lead (small): shared `_shell_script`, index-based `_strip_wrappers`, catch-all recorded (spec History); scanner moved to `shell_commands.py` (lead, scripted) |
| U1b lead fixes | cpp-reviewer | check the lead's diff once | all round-2 findings fixed (option values, `env -S`, `timeout`, linear time, catch-all recorded, reformatting reverted); still open: PowerShell parameter **prefixes** (`-exec bypass`, `-win hidden`) read as positional; new: nested `env -S` quadratic (k=20,000: 2.6 s). 100k-input fuzz per dialect: no exception, no hang; no new wrong denial | lead (small): value parameters matched by prefix (3+ chars) and aliases; `env -S` split at most 64 times; table rows and a 20,000-deep `env -S` timing row added; 58/58 pass, M2 now 16 failing subtests. Not reviewed again (one round, §6.3); evidence is the tests |
| U3b | codex luna (high) | console-only switch, `init_seg(lib)` order, linker keeps the object, UB/ODR/warnings, CMake | none (named only CRT/compiler-segment objects and earlier `atexit` handlers as able to print after the restore; no lesson output comes from them) | — |
| U3c | cpp-reviewer | can checks pass trivially, handles under ctest, robustness, CMake, style | no trivial pass; console handles inherited correctly; no timeouts; spec/plan still described `>CON & chcp`; unused import, stale names, terse failure output | review fixes lead (small); re-review: one new defect (`ignore_cleanup_errors` needs Python 3.10, test registered for 3.8) → gate raised to 3.10 |

| U2 + U4 | cpp-reviewer | build.py paths, leftovers, trivial tests; each document statement against the code; §8 completeness | U2: Windows batch dropped the unquoted `^` of `-R ^AllTests$` (the string test mirrored the output); misleading `--gtest-filter` help and dead `TEST_EXE`; no test of the filter's WSL forwarding. U4: guard docstring and start prompt said more than the code (heredocs fed to a shell, the regex fallback, the splitter's catch-all); "every preset" → presets that build `atugcc_tests`; KI-011 area name; 020-06 History out of date order; KI-032 not in spec §8; `lessons/README` "새 레슨 추가" | all fixed by the lead (small), see R27, R28; not reviewed again (one round, §6.3) |

No cross-family review for U1b, U2, U3c (cpp-reviewer, same family as the lead): these are ordinary units (delegation.md §1). U3b (risky) had codex.
