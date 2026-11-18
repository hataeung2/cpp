# Test record 023-02: Observer — 알림 재진입 안전성, 시나리오 테스트, patterns 레슨

Spec: [023_02_observer_lesson.md](/docs/specs/023_02_observer_lesson.md). Plan: [plan.md](plan.md).

## Runs
| # | Where | State | Result | Notes |
|---|---|---|---|---|
| R1 | `linux-x64-asan --target atugcc_tests --gtest-filter "ObserverTest.*"` | U1 tests, header **not** fixed | exit 8 (intended) | `AddressSanitizer: heap-use-after-free … observer.hpp:117:36 in Subject::notifyObservers()` (`e.handle.lock()`) in `SubscribeDuringNotifyStartsNextTime`. windows-x64-debug: SEH 0xc0000005 in the same test (author's run) |
| R2 | same filter, `linux-x64-asan`, `windows-x64-debug`, `linux-x64-debug` | U1 (rewritten) + U2 | exit 0 each, 6/6 `ObserverTest` | |
| R3 | mutation: `notifyObservers()` as an index loop over `entries_` (no copy), `linux-x64-debug` | temporary, header restored after (`git diff --stat` = U2 only) | exit 8 (intended) | `SubscribeDuringNotifyStartsNextTime` fails (C notified in the first round), `NestedSetDataIsSafe` fails (C notified once, not twice) |
| R4 | `--label scenario`, `windows-x64-debug` | U3 | 4/4 | `scenario.TracedObserver.SubscribeNotifyExpireDiagram` passed |
| R5 | `lesson_sensor_observers` on `windows-x64-debug` and `linux-x64-debug`, output diff (CR stripped) | U5 | identical | both outputs carry the same ANSI colour codes from `formatTerminal()` (6 lines), as `device_state_machine` does |
| R6 | `exercises.py check sensor_observers`, each solution in the practice copy, `windows-x64-debug` and `linux-x64-debug` (WSL) | final `exercises.toml` | each exercise `pass` with its solution on both | solution 1 `FanControl`; solution 2 `display()` removed (build fails; Clang and MSVC texts below); solution 3 `keep` outside the block |
| R7 | reviewer's bypass edits, `windows-x64-debug` | final `exercises.toml` | both fail (intended) | subscribe `alarm` twice → `third_receiver` fails on the `static_assert` source rule; Step 2 value `23.0`→`30.0` → `keep_panel` fails on `messages sent: 6` |
| R8 | `exercises.py verify sensor_observers`, both presets | final | "no automatic exercise passes on the unchanged lesson" | |
| R9 | `build.py --preset windows-x64-debug --test --report` | all units | exit 0, 70/70, no warnings | report `out/test-reports/windows-x64-debug/20261118-103849/` |
| R10 | `build.py --preset linux-x64-debug --test --report` | all units | exit 0, 70/70, no warnings | unit 4, scenario 4, probe 12, lesson 50 (long 4, playground 1 extra labels); report `out/test-reports/linux-x64-debug/20261118-104225/` |
| R11 | `linux-x64-asan --gtest-filter "ObserverTest.*"` | all units | exit 0 | |
| R12 | `lessons.py check`, `lint_docs.py` | final | 0 errors, 0 warnings | |

Solution 2 compiler output (R6):
- Clang 20: `static assertion failed: PanelDisplay must satisfy ObserverOf`; `because 'obs.display()' would be invalid: no member named 'display' in '(anonymous namespace)::PanelDisplay'`; `no matching function for call to 'subscribe'`, `candidate template ignored: constraints not satisfied`.
- MSVC: `C2338: static assertion failed: 'PanelDisplay must satisfy ObserverOf'`; `C2672: 'atugcc::pattern::observer::subscribe': no matching overloaded function found`; notes `'display': is not a member of …PanelDisplay`, `the concept 'atugcc::pattern::observer::ObserverOf<…PanelDisplay>' evaluated to false`.

R9–R10 ran before the last `exercises.toml` rule change (U7 review fixes). That change touches only the exercise rules, which R6–R8 checked afterwards on both presets.

## Acceptance criteria
| AC | Criterion | Evidence | Result |
|---|---|---|---|
| AC-1 | existing `ObserverTest` pass unchanged | R2, R9, R10; `git diff` of `test_visualizer.cpp` adds tests and two includes only | pass |
| AC-2 | the two new tests pass; one fails on the unfixed header under ASan | R1 (fails before), R2, R11 (pass after); R3 shows both tests fail on a contract-breaking implementation | pass |
| AC-3 | scenario `TracedObserver` passes step by step | R4, R9, R10 (scenario 4/4) | pass |
| AC-4 | lesson builds without warnings, smoke and `exercises_verify` pass, same output on both OS | R5, R9, R10 (lesson 50/50) | pass |
| AC-5 | each automatic exercise passes with its solution; the original passes none | R6, R7, R8 | pass |
| AC-6 | `lessons.py check`, `lint_docs.py` exit 0 | R12 | pass |
| AC-7 | full suite on both presets; CI on `main` | R9, R10; CI on `main`: Revision 1 | pass |

## Deviations from the spec
- `NestedSetDataIsSafe` does not fail on the unfixed header under ASan (`erase_if` does not reallocate). AC-2 asks for "one or more" of the two; `SubscribeDuringNotifyStartsNextTime` is that one (R1). The nested test is shown able to fail by R3.
- `lesson.toml` has no `profile = "quick"` line (spec §2.2): `quick` is the default and lives under `[run]`; `device_state_machine` leaves it out too.
- The concepts README link (spec §8 "연습 또는 끝") went into the intro sentence that already introduces `observer.hpp`'s `ObserverOf`; the 연습 items are unchanged.
- `keep_panel` expects `messages sent: 6`, which holds when the file was reset after exercise 1 (the README says to reset after each). A copy that still has exercise 1's `FanControl` prints 8 and does not pass until reset.

## Reviews
| Unit | Reviewer | Question | Findings | Resolution |
|---|---|---|---|---|
| U1 | cpp-reviewer | do the tests check §2.1/AC-2; can they pass trivially or on a broken implementation? | 4: nested test passes on an index loop; `b_count == 0` cannot fail (`subscribe`'s lambda locks); `c_count >= 1` too weak; two checks add no power | lead rewrote the test (order B, A, C, D; exact counts; Tracer message counts); re-review none; R3 confirms |
| U2 | codex luna (high) | does the change match §2.1/A6; any remaining invalidation; copy lifetime issues? | 1: a callback can destroy the Subject, the loop then uses `*this` / `tracer_` | precondition comment (two lines) above `notifyObservers()`, listed in KI-058; re-review (luna, resumed) none |
| U3 | cpp-reviewer | does the scenario check AC-3; trivial passes; scenario rules? | none | — |
| U5 | cpp-reviewer | A5, A9, A13; safe Step 1; stable output; comments true to `observer.hpp`? | none | — |
| U6, U7 | cpp-reviewer | README and exercise text vs code and run facts; two languages alike; rules fail on the original; unrelated edits? | 5: wrong expiry wording (`lock()` vs `expired()`); `keep_panel` bypass; `third_receiver` bypass; no `concepts.md` link (A12); `data1()` reference sentence imprecise; plus A8 paragraph missing, `profile` line | all fixed by the lead except `profile` (deviation above); re-review none; R6–R8 |
| U8 | cpp-reviewer | §8 rows, link targets, KI-058 accuracy and form, concepts 연습 count | 1: concepts link placement differs from §8 wording | kept, recorded as a deviation |

Cross-family review: U2 (risky) by codex luna (GPT), author agy flash (Gemini). Other units by `cpp-reviewer` (Claude, the lead's family), allowed for ordinary units (delegation.md §1).

## Revision 1 — 2026-11-18
AC-7, CI on `main` after the user approved the push: GitHub run 44374678372, commit `85c2619` (merge of `feature/023-02-observer-lesson`), **success**. `Docs gate` success (18:54:01–18:54:10Z), `Linux Clang 20 (linux-x64-debug)` success (18:54:01–18:59:35Z, 5 min 34 s).
