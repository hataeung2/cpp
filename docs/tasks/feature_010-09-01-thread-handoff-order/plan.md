# Plan: 010-09-01 Logger 전달 순서 — 먼저 일어난 기록을 먼저 전달 (KI-030)

- Spec: [/docs/specs/010_09_01_thread_handoff_order.md](/docs/specs/010_09_01_thread_handoff_order.md) (approved 2026-10-30)
- Branch: `feature/010-09-01-thread-handoff-order` (from `main` at `d327e90`)
- Order (spec §11): reproduce first (AC-1), fix only after the probe fails on the current code.

## Code facts checked before the plan
- Producer wakes the consumer when `usedSlots() > slotCount() / 2` or the level is Warn or higher ([log_service.cpp](/src/core/log_service.cpp) `log`); otherwise the consumer runs on its `drainInterval` timer (5 ms) or at the earliest held-back record + 1 ms.
- `drainLocked` takes a buffer without holdback when `usedSlots() >= slotCount() / 2` or a flush / shutdown is pending; otherwise it stops at the first record newer than `now - 1 ms`.
- A retired buffer is reused only when `readPos == writePos` ([log_registry.cpp](/src/core/log_registry.cpp) `acquireNode`). So when the ended thread A still has held-back records, the next thread B gets another buffer: this is the case that inverts.
- If the consumer reads A only after A has finished its 40 lines, A has 40 ≥ 32 used slots and is taken whole, and B then reuses A's buffer: no inversion in that round. Without help, the probe fails only in rounds where the consumer happens to drain A midway.

## Design decisions

### D1 Probe mode `handoff` (`tests/core/crash_probe.cpp`, `tests/core/check_crash_dump.py`)
- `runHandoff(dir)`: `configureLogBuffers({.slotsPerThread = 64})` before the Logger is built (failure → stderr, exit 2). One Async Logger on `app.log` (`config()` as the other modes: Block overflow, so every line counts). 500 rounds (`kHandoffRounds`); in round `r`:
  - thread A logs `P<r> L0` … `P<r> L19`, calls `log.flush()`, logs `P<r> L20` … `P<r> L39`, ends; `join()`;
  - thread B logs `P<r> L40` … `P<r> L79`, ends; `join()`.
- The `flush()` in A makes the midway drain happen in every round, not only when the consumer wakes at the right moment: A's first 20 lines are delivered, its last 20 (20 < 32 slots, younger than 1 ms) are held back, A's buffer is not empty so B takes another one, and B passes half (40 > 32). This is the state the spec's hypothesis names (Assumption 1); it keeps "A writes 40 lines, then B writes 40 after `join`" (spec §2.2) and only fixes when the consumer reads A.
- The `lines` argument is ignored in this mode.
- `check_handoff(work)`: reads `app.log`; every line has the time prefix; the `(r, i)` pairs of the `P<r> L<i>` lines, in file order, must equal `(0,0) … (0,79), (1,0) … (499,79)` (every round's A lines before its B lines, and rounds in order, since round `r + 1` starts after round `r`'s `join`). On failure it prints the number of rounds out of order, the first such round with 8 line numbers starting 2 before its first out-of-place line (or, when every round is in order by itself but rounds interleave, 8 `(round, line)` pairs around the first file position that differs), plus missing / duplicate counts. The constants `HANDOFF_ROUNDS = 500`, `HANDOFF_LINES = 40` repeat the probe's, with a comment pointing at it.
- `handoff` joins the default `--modes` list. It is added to the CTest mode lists only with the fix (U3), so the suite stays green between the units.

### D2 Two-phase `drainLocked` (`src/core/log_service.cpp`, spec Assumption 2)
- Phase 1 (no allocation): for every buffer with `readPos < writePos` that is taken without holdback (`flushOrShutdown` or `usedSlots >= slotCount / 2`), read `writePos` (acquire) and the `timeNs` of slot `writePos - 1`. That slot is the last slot of the last published record (`writePos` moves only after a whole record is written, and every slot of a record carries the record's `timeNs`). In a per-thread buffer it is also the newest time (one writer at a time; a reused buffer's new owner starts after the old owner ended). In the emergency buffer it may not be: several threads share it and take their time stamps before its lock, so an earlier slot can be newer than the cutoff. The scan then stops there and the rest waits for the 1 ms limit, a delay only; the order argument below does not use it (U2 review). `cutoffNs` = the largest such time; 0 when no buffer qualifies.
- Phase 2: the current collection loop, for every buffer, with one bound: `limitNs = max(holdbackLimitNs, cutoffNs)`; a record with `timeNs > limitNs` stops that buffer's scan and counts as held back (`earliestHeldBackNs`, as now). The per-buffer `bufNoHoldback` flag no longer exempts a buffer from the bound.
- No buffer qualifies → `limitNs = holdbackLimitNs`: same as today. Flush / shutdown → every buffer qualifies, so `cutoffNs` is the newest record published before phase 1: everything published before the flush call is taken, as today (flush waits on positions read before it wakes the consumer).
- Why the order holds (spec Assumption 2): if `log()` call a happens before call b and b is taken in this batch, then either b.time ≤ cutoff, where cutoff is the time of a record y read (acquire) in phase 1; a's publish happened before b's time stamp, which is not later than y's, which was published before phase 1, so phase 2's later read of a's buffer sees a, and a.time ≤ b.time ≤ limit, so a is taken in the same batch; or b.time ≤ now − 1 ms, the same argument with the drain's start time (unchanged from 010-09). Nothing before a in a's buffer can stop the scan short of a: every such record x was published before a, so x.time ≤ publish(x) < publish(a) ≤ b.time ≤ limit.
- Equal times (U4 review): a and b can read the same `steady_clock` tick (100 ns on Windows) if b's formatting and a's write take less than one tick. They are then in the same batch and sorted by `threadNo`, which does not follow happens-before (the joining thread is usually older than the joined one; the emergency buffer has number 0). Strict order there would need a shared counter (010-09 Assumption 9 rejected it), so the contract names this exception (`logger.hpp`, spec History).
- The comment above the loop states the bound and points at spec 010-09-01 Assumption 2.

## Units

| Unit | File | Change (what, where, AC) | Check | Risky | Author | Reviewer | Tokens (in / out) | Status |
|---|---|---|---|---|---|---|---|---|
| U1 | `tests/core/crash_probe.cpp`, `tests/core/check_crash_dump.py` | mode `handoff` and its check (D1, AC-1) | `grep -c "runHandoff"` = 2, `grep -c "check_handoff"` = 2; build `crash_probe` on `windows-x64-debug`; `check_crash_dump.py --modes handoff` **fails** on the current `drainLocked` (AC-1), `--modes normal` passes | no | lead (small); review fixes lead (small) | cpp-reviewer: 2 (failure message only) → fixed; re-review: none | — | done: fails 497–500 / 500 rounds on both hosts (testrecord R1) |
| U2 | `src/core/log_service.cpp` | two-phase `drainLocked` (D2, AC-2) | `--modes handoff` passes; `atugcc_tests --gtest_filter=*Log*` | yes | agy flash | codex luna (high): item 4 (order broken through the emergency buffer) withdrawn after the lead's counter-argument (one round); items 2, 5 delay only, no code change; D2 text corrected | agy 211k / 25k; codex 212k / 6k + 267k / 8k | done: `handoff` 5/5 Windows, 3/3 Linux, 0 warnings; mutant caught 2/2 |
| U3 | `tests/CMakeLists.txt` | `handoff` in both `ATUGCC_CRASH_MODES` lists (AC-4) | `ctest -R CrashDump` on `windows-x64-debug` and `linux-x64-tsan` | no | lead (small) | cpp-reviewer: none | — | done: `CrashDump` with `handoff` passed in the `windows-x64-debug` gate |
| U4 | `include/atugcc/core/logger.hpp`, `docs/known_issues.md`, `docs/specs/010_09_logger_thread_buffers.md`, `docs/cpp_evolution/lock_free_logging.md` | spec §8 (AC-5) | `lint_docs.py` exit 0 | no | lead | cpp-reviewer: 1 contract gap (equal clock ticks sort by thread number, not happens-before) + 5 wording slips → lead fixed; re-review: "join always is" only half true → reworded with the reviewer's option (calls on different threads reading one tick are not ordered) | — | done |

## Verification (spec §12)
- AC-1: U1 run on the commit before U2, recorded in `testrecord.md` with the failing output.
- Mutant (spec §12 "cutoff 조건을 빼면"): U2 with the cutoff left out of the bound for buffers below half (they stop at `holdbackLimitNs`, buffers taken without holdback keep `limitNs`) must fail `handoff`.
- AC-2: `--modes handoff` 10 runs in a row on `windows-x64-debug` and `linux-x64-debug`; `--modes normal` 10 runs in a row while another preset builds.
- AC-3: Release `logger_contention_probe`, shared Logger 4 and 8 threads, both platforms, against the 010-10 testrecord numbers.
- AC-4: `build.py --test` on the 4 presets; `handoff` in the TSan run.
- AC-5: doc review, `lint_docs.py`, `naming_check.py`.
