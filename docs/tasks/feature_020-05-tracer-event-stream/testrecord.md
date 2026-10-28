# Test Record: 020-05 Tracer 이벤트 스트림 (JSON Lines)

- Spec: [/docs/specs/020_05_tracer_event_stream.md](/docs/specs/020_05_tracer_event_stream.md)
- Plan: [plan.md](/docs/tasks/feature_020-05-tracer-event-stream/plan.md)
- Date: 2026-10-28
- Hosts: Windows 11 (MSVC 19.51, VS 2026 Community), WSL Ubuntu 24.04 (GCC 13.3, Python 3.12); Windows Python 3.15

## Runs

| # | Command | Expected | Actual | Status |
|---|---|---|---|---|
| R1 | `build.py --preset linux-x64-debug --test` after U1+U2 | builds with `-Werror`, existing suite passes unchanged | AllTests passed | Pass |
| R2 | `build.py --preset windows-x64-debug --test` after U1+U2 | builds with `/W4 /WX`, existing suite passes unchanged | AllTests passed | Pass |
| R3 | `build.py --preset linux-x64-debug --target atugcc_tests --gtest-filter "EventStream.*:JsonLines.*"` | 12 new tests pass | first build failed: two raw strings in the test contained `)"` (`go()"`, `(1/2)"`) and ended early; fixed with a `j` delimiter; then 12/12 passed | Pass (after fix in U3) |
| R4 | same filter on `windows-x64-debug` | 12 pass | 12/12 passed | Pass |
| R5 | `setarch $(uname -m) -R out/build/linux-x64-tsan/bin/atugcc_tests --gtest_filter="EventStream.*:JsonLines.*:TracerConcurrencyTest.*"` (WSL) | no ThreadSanitizer warning | 13/13 passed, no warning. `build.py --gtest-filter` on this preset exits 66 without output because it runs the binary without the `setarch` launcher (KI-012) | Pass |
| R6 | `build.py --preset linux-x64-debug --test` after U4 | AllTests + TraceStream pass | both passed; `check_trace_stream: OK (28 events, 5 diagram parts)` | Pass |
| R7 | `build.py --preset windows-x64-debug --test` after U4 | AllTests + TraceStream pass | both passed | Pass |
| R8 | negative: `check_trace_stream.py -- sh -c "echo {...}"` (a command that writes no stream) | script fails | `FAILED - trace file was not written`, exit 1 | Pass |
| R9 | `build.py --preset linux-x64-asan --test` | ASan + UBSan clean | AllTests + TraceStream passed | Pass |
| R10 | `build.py --preset linux-x64-tsan --test` (ctest uses the `setarch` launcher) | TSan clean | AllTests + TraceStream passed | Pass |
| R11 | `atugcc_pattern_example` on `linux-x64-debug`: baseline from `main` (`c528d3b`) vs this branch, without and with `ATUGCC_TRACE_OUT` | stdout identical | identical, 173 lines each, after normalizing the environment-dependent lines (log path with pid/time, sink kind `desktop window`/`file-only fallback`, the window-failure notice); runs used an empty `DISPLAY` so no terminal window opened | Pass |
| R12 | `ATUGCC_TRACE_OUT=/tmp/ex_trace.jsonl atugcc_pattern_example`, file parsed with `json.loads` | all lines JSON, every Tracer with events has diagram lines | 59 lines, all JSON; 47 events (40 message, 4 transition, 3 node), seq unique; Tracers 1–4 all have diagram lines (4 has 8 sequence parts) | Pass |
| R13 | `naming_check.py`, `lint_docs.py` | exit 0 | 0 snake_case functions; 0 errors, 0 warnings (19 legacy info) | Pass |

## Revision 1 — 2026-10-28
First-pass review of U3–U5 (`cpp-reviewer`) found that the Python label check was circular: the probe built the expected labels with `detail::jsonEscape`, the function under test, so a valid-but-wrong escape would cancel out. Fixed in U3/U4 (one rework round, delegation.md §6.3): expected labels now live in `check_trace_stream.py`; `\b \f \r`, the `0x1f` boundary and `0x7f` pass-through are covered; a 4-threads-on-one-Tracer test was added; CMake requires Python 3.8 and warns when it is missing; the header comment no longer reads as contradicting the stream.

| # | Command | Expected | Actual | Status |
|---|---|---|---|---|
| R14 | mutant: `jsonEscape` writes `\\t` for TAB (valid JSON, wrong meaning), probe rebuilt, script run; then original restored (`cmp` identical) | mutant fails, original passes | mutant: `FAILED - label 'Tab\tNew\nline\rCR' did not round-trip`, exit 1; restored: OK | Pass |
| R15 | `build.py --test` on `linux-x64-debug` and `windows-x64-debug` after the fixes | AllTests (13 event-stream tests) + TraceStream pass | all passed | Pass |
| R16 | example with `ATUGCC_TRACE_OUT=/tmp/no_such_dir_020_05/trace.jsonl` | exit 0, stdout = baseline, no directory created, nothing on stderr | exit 0, normalized stdout identical to baseline, directory not created, stderr empty | Pass |
| R17 | `linux-x64-asan --test`, `linux-x64-tsan --test`, and `setarch … atugcc_tests --gtest_filter="JsonLines.Concurrent*"` | clean | all passed, no sanitizer report | Pass |
| R18 | `naming_check.py`, `lint_docs.py` (after registering KI-012) | exit 0 | 0 / 0 errors, 0 warnings | Pass |

## Acceptance Criteria Evidence

| AC | Criterion (short) | Evidence | Result |
|---|---|---|---|
| AC-1 | stdout and existing tests unchanged without the variable | R1, R2 (suite unchanged); R11 (example stdout before = after = with variable) | Pass |
| AC-2 | `toJsonLine` has every schema field and escapes `"` `\` newline, control characters, Korean; valid JSON | `JsonLines.MessageTransitionNodeFields`, `JsonLines.EscapesSpecialCharacters`, `JsonLines.DiagramLinesIndexPartsPerKind` (R3, R4); Python cross-check in `TraceStream` (every line `json.loads`, exact key sets, tricky labels round-trip) (R6, R7) | Pass |
| AC-3 | seq strictly increases within a Tracer; disjoint across Tracers | `EventStream.SeqStrictlyIncreasesWithinTracer`, `EventStream.SeqDisjointAcrossTracers` (R3, R4) | Pass |
| AC-4 | with the variable every line parses; event lines = recorded events; diagram lines per Tracer = Mermaid part count | `TraceStream` (probe reports its own counts: 28 events, 5 parts, per Tracer and kind, indices 0..n-1) (R6, R7, R15); example run R12 | Pass |
| AC-5 | unopenable path: normal exit, stdout unchanged | `TraceStream` third run (missing directory: exit 0, stdout identical, directory not created) (R6, R7, R15); `JsonLines.OpenFailsForMissingDirectory`; example run R16 | Pass |
| AC-6 | 4 threads: whole lines, no TSan warning | `JsonLines.ConcurrentWritersProduceWholeLines` (4 Tracers on 4 threads sharing one sink, plus concurrent destructor diagram lines) and `JsonLines.ConcurrentRecordersOnOneTracer` (4 threads on one Tracer: stored order = seq order, streamed seq set = recorded set) under TSan (R5, R10, R17) | Pass |
| AC-7 | zero warnings on MSVC and GCC; ASan/UBSan clean | R1, R2, R9 | Pass |

## Reviews

| Unit | Reviewer | Question | Findings | Resolution |
|---|---|---|---|---|
| U1+U2 | codex luna (effort high) | match plan D1/D2 and spec §2.1–§2.4; thread safety, lifetime, ODR, JSON validity, Windows branch | none | — |
| U3+U4 | `cpp-reviewer` | does each test check its AC; can any pass trivially; CMake on tsan / without Python | (1) label round-trip circular via `jsonEscape`; (2) only `\x01` among other control characters; (3) AC-4/AC-5 name the example, the script runs the probe; (4) AC-6 single-Tracer case only had 2 threads; (5) missing Python silently drops the test, no minimum version | (1)(2)(4)(5) fixed in Revision 1, (1) proven by mutant R14; (3) example evidence added as R12 and R16 (the probe remains the automated check because it knows its exact expected counts) |
| U5 | `cpp-reviewer` | do the doc texts match the behaviour | `visualizer.hpp:8` "output is the caller's job" read as contradicting the stream paragraph | narrowed to human-readable output |
| Tester | lead | every unit diff against its spec section; tests read against ACs | no further findings | — |

No cross-family review gap: risky units U1+U2 were written by agy and reviewed by codex.
