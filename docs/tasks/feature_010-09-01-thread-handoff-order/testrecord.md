# Test record: 010-09-01 Logger 전달 순서 — 먼저 일어난 기록을 먼저 전달 (KI-030)

- Spec: [/docs/specs/010_09_01_thread_handoff_order.md](/docs/specs/010_09_01_thread_handoff_order.md) (approved 2026-10-30)
- Plan: [plan.md](/docs/tasks/feature_010-09-01-thread-handoff-order/plan.md)
- Hosts: Windows 11 (MSVC, VS 2026), WSL2 Ubuntu (GCC 13) on the same machine, 2026-10-30

## Runs
| # | Test | Expected | Actual | Status |
|---|---|---|---|---|
| R1 | **AC-1**: U1 (`crash_probe handoff` + `check_handoff`) on the unfixed `drainLocked` (branch base `d327e90` + U1 only), `check_crash_dump.py --modes handoff`, `windows-x64-debug` × 6, `linux-x64-debug` × 3 | FAIL (hypothesis, spec Assumption 1) | FAIL in every run: 497–500 of 500 rounds out of order, 40,000 lines, 0 missing, 0 duplicates. In every round the order breaks after A's L19 (the flush): B's L40–L79 come first, then A's L20–L39, whose time stamps are earlier than B's first line (round 0 Windows: A L21 `…880054`, B L40 `…880569`) | Pass (cause confirmed) |
| R2 | `--modes normal --lines 100000` on the same Windows build | pass | ok, 800,000 lines; 13,099 cross-thread time inversions (counted, not checked) | Pass |
| R3 | U2 per-unit: `--modes handoff` on `windows-x64-debug` × 5, `linux-x64-debug` × 3 | pass | ok in every run, 0 warnings on both builds | Pass |
| R4 | Mutant (spec §12): the cutoff left out of the bound for buffers below half (`holdbackLimitNs` for them, `limitNs` for buffers taken without holdback), Windows, reverted after the run | `handoff` FAIL | FAIL 2 of 2 (500 and 480 of 500 rounds out of order) | Pass |
| R5 | **Gate** (AC-4), `build.py --preset <p> --test`, sequential, nothing else running | 0 warnings, all pass | `windows-x64-debug` 16 / 16, `linux-x64-debug` 17 / 17, `linux-x64-asan` 17 / 17, `linux-x64-tsan` 17 / 17; `CrashDump` includes `handoff` on every preset (TSan: 65 s, no report) | Pass |
| R6 | **AC-3** Release `logger_contention_probe 100000 3`, 3 runs per host, nothing else running (table below) | ≥ 90 % throughput, p99 ≤ 1.5× of 010-10 R11 "map off" | see table | Pass |
| R7 | **AC-2** `--modes handoff` 10 runs in a row, `windows-x64-debug` and `linux-x64-debug` (run at the same time) | 10 / 10 each | 10 / 10 each | Pass |
| R8 | **AC-2** `--modes normal --lines 100000` 10 runs in a row on `windows-x64-debug` while `windows-x64-release` and `linux-x64-release` rebuild from scratch in a loop | 10 / 10 | 10 / 10, about a minute each under the load; cross-thread time inversions 678–1,077 per run (R2 before the fix, idle: 13,099) | Pass |
| R9 | `lint_docs.py`, `naming_check.py` after the doc units | exit 0 | 0 errors; 0 names | Pass |

Header comments (`logger.hpp`) were corrected after the Windows gate run started (U4 review); comment-only, the Linux gate built them.

## AC-3 measurement (Release, shared Logger, live output off, best of 3 runs)
| Host | Threads | 010-10 lines/s | now lines/s | ratio | 010-10 p99 ns | now p99 ns | ratio |
|---|---|---|---|---|---|---|---|
| Windows MSVC | 4 | 675 k | 633 k | 94 % | 3,400 | 3,000 | 0.88× |
| | 8 | 639 k | 608 k | 95 % | 4,300 | 4,200 | 0.98× |
| Linux GCC 13 | 4 | 914 k | 879 k | 96 % | 2,201 | 914 | 0.42× |
| | 8 | 951 k | 885 k | 93 % | 1,053 | 1,283 | 1.22× |

## Acceptance criteria
| AC | Criterion (short) | Evidence | Result |
|---|---|---|---|
| AC-1 | `handoff` fails before the fix | R1 (both hosts, every run, cause seen in the log) | Pass |
| AC-2 | after the fix `handoff` 10 in a row on both hosts; `normal` 10 in a row under load | R7, R8; mutant R4 shows `handoff` catches the cutoff being left out | Pass |
| AC-3 | shared Logger 4 / 8 threads ≥ 90 % throughput, p99 ≤ 1.5× | R6 table: 93–96 %, 0.42–1.22× | Pass |
| AC-4 | 4 presets, no warnings, `handoff` also on TSan | R5 | Pass |
| AC-5 | order contract in `logger.hpp`, KI-030 CLOSED | `logger.hpp` Contract "Order (spec 010-09-01)"; `known_issues.md` KI-030 row and **Closed** line; R9; U4 review | Pass |

## Reviews
| Unit | Reviewer | Question | Findings | Resolution |
|---|---|---|---|---|
| U1 | cpp-reviewer | does the diff implement plan D1; can `handoff` pass trivially or fail for a reason other than order? | 2, failure message only: (1) prints 8 line numbers around the break, D1 said "first 12"; (2) rounds interleaved but each in order → message names no culprit. Pass/fail logic, probe sequence, constants, naming: no finding | lead (small): D1 reworded to the code; interleaved case prints the `(round, line)` pairs around the first differing position (checked on a synthetic log with two rounds swapped). Re-review: none |
| U2 | codex luna (high) | does the change match plan D2 / spec Assumption 2; correct under concurrency (published slot, liveness, order, held-back time, TSan)? | item 4: order can break through the emergency buffer (threads stamp before its lock, so its times can decrease); items 2, 5: such a buffer can stop early (delay). Slot read, liveness, TSan, D2 conformance: no finding | lead's counter-argument (every record ahead of a in its buffer was published before a, so its time ≤ publish(a) ≤ b.time ≤ bound); codex withdrew item 4 and confirmed 2, 5 are delay only (5 was there before). No code change; plan D2 text corrected |
| U3 + U4 | cpp-reviewer | `handoff` in both CTest lists; contract and docs faithful to Assumption 3 and the code? | U3: none. U4: equal clock ticks sort by `threadNo`, not by happens-before, so the contract over-promised; per-Logger scope missing in the evolution page; proof skipped the 1 ms case; "절반 넘게" vs `>=`; KI wording | lead: contract names the exception (calls on different threads that read one tick are not ordered; lines of different Loggers are not ordered), spec History records it (strict order would need the shared counter 010-09 Assumption 9 rejected). Re-review: "join always is" only half true (joining thread is older; emergency buffer number 0) → reworded with the reviewer's option |
