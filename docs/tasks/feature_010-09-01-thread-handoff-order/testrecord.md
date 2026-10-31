# Test record: 010-09-01 Logger 전달 순서 — 먼저 일어난 기록을 먼저 전달 (KI-030)

- Spec: [/docs/specs/010_09_01_thread_handoff_order.md](/docs/specs/010_09_01_thread_handoff_order.md) (approved 2026-10-30)
- Plan: [plan.md](/docs/tasks/feature_010-09-01-thread-handoff-order/plan.md)
- Hosts: Windows 11 (MSVC, VS 2026), WSL2 Ubuntu (GCC 13) on the same machine, 2026-10-30

## Runs
| # | Test | Expected | Actual | Status |
|---|---|---|---|---|
| R1 | **AC-1**: U1 (`crash_probe handoff` + `check_handoff`) on the unfixed `drainLocked` (branch base `d327e90` + U1 only), `check_crash_dump.py --modes handoff`, `windows-x64-debug` × 6, `linux-x64-debug` × 3 | FAIL (hypothesis, spec Assumption 1) | FAIL in every run: 497–500 of 500 rounds out of order, 40,000 lines, 0 missing, 0 duplicates. In every round the order breaks after A's L19 (the flush): B's L40–L79 come first, then A's L20–L39, whose time stamps are earlier than B's first line (round 0 Windows: A L21 `…880054`, B L40 `…880569`) | Pass (cause confirmed) |
| R2 | `--modes normal --lines 100000` on the same Windows build | pass | ok, 800,000 lines; 13,099 cross-thread time inversions (counted, not checked) | Pass |

## Reviews
| Unit | Reviewer | Question | Findings | Resolution |
|---|---|---|---|---|
| U1 | cpp-reviewer | does the diff implement plan D1; can `handoff` pass trivially or fail for a reason other than order? | 2, failure message only: (1) prints 8 line numbers around the break, D1 said "first 12"; (2) rounds interleaved but each in order → message names no culprit. Pass/fail logic, probe sequence, constants, naming: no finding | lead (small): D1 reworded to the code; interleaved case prints the `(round, line)` pairs around the first differing position (checked on a synthetic log with two rounds swapped). Re-review: none |
