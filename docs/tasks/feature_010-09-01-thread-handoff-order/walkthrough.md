# Walkthrough: 010-09-01 Logger 전달 순서 — 먼저 일어난 기록을 먼저 전달 (KI-030)

- Spec: [/docs/specs/010_09_01_thread_handoff_order.md](/docs/specs/010_09_01_thread_handoff_order.md) (approved 2026-10-30)
- Evidence: [testrecord.md](/docs/tasks/feature_010-09-01-thread-handoff-order/testrecord.md) (AC-1 … AC-5 Pass)
- Branch: `feature/010-09-01-thread-handoff-order`

## Result
- **Cause confirmed before the fix**: new probe mode `crash_probe handoff` (64-slot buffers, 500 rounds: thread A logs 40 lines and ends, then after `join()` thread B logs 40 more) failed in 497–500 of 500 rounds on both hosts. A's last lines, in a buffer below half and younger than 1 ms, were held back while B's half-full buffer was taken at once.
- **Fix**: `drainLocked` runs in two passes. The first reads the time of the last published record of every buffer taken without holdback; the largest is the batch's cutoff. The second takes records from every buffer only up to `max(1 ms limit, cutoff)`. After the fix: `handoff` 10 / 10 on both hosts, `normal` 10 / 10 under build load, and a mutant without the cutoff fails.
- **Throughput kept**: shared Logger 4 / 8 threads at 93–96 % of the 010-10 numbers, p99 0.42–1.22×.
- **Contract** (`logger.hpp`): of two lines of one Logger, the one whose `log()` happens before the other's is delivered first. Exception: two calls on different threads that read the same `steady_clock` tick (100 ns on Windows), because equal times are sorted by thread number. Strict order there would need the shared counter that 010-09 Assumption 9 rejected.
- Side effect: cross-thread time inversions in `normal` fell from about 13,000 to about 700–1,100 per run.

## Found while implementing
- As the spec described it, the probe failed only in rounds where the consumer happened to drain A midway. Otherwise B reused A's emptied buffer and the order could not break. A `flush()` after A's first 20 lines makes this happen in every round (plan D1, spec History).
- The emergency buffer (shared, threads stamp before its lock) can hold decreasing times. The codex review first read this as an order break. It is only a delay, and the order argument does not depend on increasing times (plan D2).
- Equal clock ticks: the U4 review found the contract promised more than the code delivers. The exception is now written in `logger.hpp`, `lock_free_logging.md` and the spec History.

## Lead (small) units
- U1 (probe mode + check, one function each), U3 (two CTest mode lists), and review fixes to the U1 failure message and the U4 docs; each was re-reviewed once.

## Delegation
- agy flash wrote U2 (one call, 211 k input / 25 k output). codex luna reviewed it (2 calls, 479 k input), and the second call was the lead's counter-argument. `cpp-reviewer` reviewed U1, U3 and U4 (2 conversations, one re-review each).

## Follow-ups
- None new. Ordering lines across different Loggers that share one output (grouped per Logger in each batch) is outside the contract, and the contract now says so.
