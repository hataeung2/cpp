# Test record: 010-10 메모리 매핑 파일 로그 버퍼와 다음 실행 때 복구

- Spec: [/docs/specs/010_10_logger_mapped_buffers.md](/docs/specs/010_10_logger_mapped_buffers.md) (approved 2026-10-30)
- Plan: [plan.md](/docs/tasks/feature_010-10-logger-mapped-buffers/plan.md)
- Hosts: Windows 11 (MSVC, VS 2026), WSL2 Ubuntu (GCC 13) on the same machine, 2026-10-30

## Runs
| # | Test | Expected | Actual | Status |
|---|---|---|---|---|
| R1 | Scratch experiments before the plan (Python ctypes / WSL Python) | Windows: delete disposition while mapped, bytes kept after `TerminateProcess`, sharing violation while live; WSL: `MAP_SHARED` bytes kept after SIGKILL, `flock` busy while live | all as expected (plan "Platform facts") | Pass |
| R2 | U1–U5 per-unit builds, `windows-x64-debug` and `linux-x64-debug` | zero warnings | first full Windows build failed on two lead edits (a `\n` turned into a real newline by a shell heredoc) → fixed with the editor | Fail → fixed |
| R3 | Smoke: `log_map_probe killmap`, kill, `startrecover` (Windows) | recovered file; union with `app.log` = 4,000 lines | 3,445 in `app.log` + 555 `[undelivered]`, 0 missing | Pass |
| R4 | Same on Linux | same | nothing recovered, no message (3 of 3 runs); with 0.2 s or 1 s between kill and restart: recovered. A SIGKILLed multi-threaded owner keeps its `flock` briefly after the parent's `wait()` returns | Fail → fixed (plan D4 amendment: wait up to 1 s when the header's pid no longer exists); after the fix 3 of 3 recovered, 0 missing |
| R5 | `log_map_probe env` with `ATUGCC_LOG_MAP_DIR` (Windows) | `MAPPED 1` | `MAPPED 0`: the log thread started the map while the main thread took a heap buffer without waiting | Fail → fixed (3-state start, other threads wait; plan D3) → `MAPPED 1` |
| R6 | Full suite `windows-x64-debug`, first runs | pass | `CrashDump` failed twice (`normal: P6 ... in order False`); reproduced on `main` without 010-10 (2 of 8 runs under load) | pre-existing → **KI-030** |
| R7 | `LogMapRecoveryTest.*` (U6) Windows | pass | 10 / 10, `MutationsNeverCrash` 1,000 inputs 15 s | Pass |
| R8 | Gate run interrupted twice: test files were edited by fix rounds while it ran (mixed old probe / new checker on ASan) | — | discarded | — |
| R9 | **Gate**, commit `2e4c125`, sequential, nothing else running: `build.py --preset <p> --test` | 0 warnings, all pass | `windows-x64-debug` 16 / 16, `linux-x64-debug` 17 / 17, `linux-x64-asan` 17 / 17, `linux-x64-tsan` 17 / 17 (LogMap cases: all; `abort`/`segv` skipped on sanitizer presets by design) | Pass |
| R10 | Mutants (plan §12), each reverted after the run | each caught | M1 recovery judges delivery by `writePos`: `ValidFile…` FAILED and checker `killmap` FAIL (read_dump 454 vs recovered 0). M2 `flock` skipped in `openIfEnded`: checker `live` FAIL (live run's map recovered). M3 size check weakened to the 128-byte header (`linux-x64-asan`): `TruncatedFile` FAILED | Pass |
| R11 | Release measurement (below), nothing else running | AC-9 | see table | Pass |
| R12 | `lint_docs.py`, `naming_check.py` (4 std/POSIX names added to its allow list), `test_agent_scripts.py`, `py -3 -m unittest tools/test_read_dump.py` | exit 0 | 0 errors; 0 names; OK; 11 tests OK | Pass |

Header comments were corrected after R9 (documentation review, comment-only changes in `logger.hpp`, `log_buffer_config.hpp`, `detail/log_service.hpp`).

## AC-9 measurement (Release, `logger_contention_probe 100000 3`, best of 3 runs, live output off)
| Host | Mode | Threads | p99 ns map off | p99 ns map on | ratio | lines/s off → on |
|---|---|---|---|---|---|---|
| Linux GCC 13 | A shared | 4 | 2,201 | 2,051 | 0.93× | 914 k → 921 k |
| | A shared | 8 | 1,053 | 1,025 | 0.97× | 951 k → 950 k |
| Windows MSVC | A shared | 4 | 3,400 | 3,300 | 0.97× | 675 k → 653 k |
| | A shared | 8 | 4,300 | 4,200 | 0.98× | 639 k → 650 k |
"Map on" = `ATUGCC_LOG_MAP_DIR` set; the map directory was empty after the probe ended (clean exit removed the file on both hosts).

## Acceptance criteria
| AC | Criterion (short) | Evidence | Result |
|---|---|---|---|
| AC-1 | after SIGKILL / `TerminateProcess`, `app.log` ∪ recovered `[undelivered]` = every line; missing lines are all `[undelivered]` | CTest `LogMap` case `killmap` on 4 presets (R9): 4 × 1,000 lines, ≥ 1 undelivered, reverse check (`[delivered]` ⊆ `app.log`); R3, R4; mutant M1 | Pass |
| AC-2 | time order, label, `T<n>`, header counts, no `.logmap` left | same case (pid of the recovered header = killed pid) | Pass |
| AC-3 | a live run's map is untouched by another process's recovery | `LogMap` case `live` (name, size, sha256 unchanged; no recovered/corrupt file; recovered after the kill); mutant M2 | Pass |
| AC-4 | clean exit leaves no `.logmap`, nothing recovered next run | `LogMap` cases `normal`, `exit`, `quickexit` (the probe prints the map path; it is gone afterwards), 4 presets; R11 directory empty on both hosts | Pass |
| AC-5 | `abort` / SIGSEGV: dump exists, recovered header `crash handler: yes` | `LogMap` cases `abort`, `segv` on `windows-x64-debug` and `linux-x64-debug` (sanitizer presets skip crash cases, as in 010-09) | Pass |
| AC-6 | corrupt inputs never crash; `.corrupt`; other buffers recovered; `skippedBuffers` | `LogMapRecoveryTest.*` (10 tests incl. 1,000 seeded mutations with `has_value()` asserted) on 4 presets, ASan/UBSan clean; mutant M3 | Pass |
| AC-7 | `configureLogBuffers` errors and no-change cases; env var | `LogMap` cases `config` (map path identical after same-dir / other-dir / empty steps, one `.logmap`) and `env` (`MAPPED 1`) | Pass |
| AC-8 | 1 MiB arena, 12 live threads: 7 mapped, 5 heap, no line lost, one stderr notice | `LogMap` case `full` | Pass |
| AC-9 | map on: shared Logger p99 at 4 / 8 threads ≤ 1.5× map off | table above: 0.93–0.98× | Pass |
| AC-10 | `read_dump.py` reads `.logmap`, `--undelivered` | `tools/test_read_dump.py` (header errors, corrupt buffer, exact wall time, filter); `LogMap` `killmap` runs `read_dump.py --undelivered` on the pre-recovery copy and compares with the recovered `[undelivered]` lines | Pass |
| AC-11 | 010-09 tests, lessons, `PlaygroundServer`, 4 presets, mapped TSan test | R9 (`linux-x64-tsan` `LogMap` case `threads`); `CrashDump` flake KI-030 is pre-existing (R6) | Pass (note: KI-030) |
| AC-12 | §2.4 in `logger.hpp` and README | documentation review (Reviews), corrected | Pass |

## Reviews
| Unit | Reviewer | Question | Findings | Resolution |
|---|---|---|---|---|
| U1 | codex luna (high) | D1 POSIX correct? | errno tested after `close` | flash `--resume` fixed |
| U2 | codex luna (high) | D1 Windows correct? | 3 empty `catch (...) {}` | lead (small) fixed; re-checked in the U3 review: none |
| U3 | codex luna (high) | D2 correct? | mutex lock in `noexcept finishLogMapCleanly` | lead (small): atomic pointer. Lead, before the review: recovery calling `logMapPath()` under the start mutex would self-deadlock → plan D4 step 2 changed (the own map is skipped by its lock) |
| U4a | codex luna (high) | D3 config/env/registry | CAS on every call (hot path); env read failure hidden as "unset" | lead fixed; round 2: Windows `_dupenv_s` failure still "unset" → fixed |
| U4b | codex luna (high) | D3 service/crash path | broken string literal (lead edit), narrow catches in `noexcept`, `strcmp` on the crash path | lead fixed (`isManualEvent`); round 2: none |
| U5 | codex luna (high) | D4 on untrusted input | signed overflow in wall time; `removeFile()` result ignored | flash `--resume` fixed; round 2: `pos + maxSlots` wrap, clean-exit `removeFile()` ignored → lead fixed |
| lead changes | codex luna (high) | lock wait (`openEndedOrWait`, `processAlive`), 3-state env start | none (PID reuse can only cause a wait or a skip, never recover a live run's map) | — |
| U6–U9 | `cpp-reviewer` | can each test fail on the mutant it targets? | 15 (e.g. truncation hit the magic check, no reverse AC-1 check, AC-3 only checked existence, AC-10 not automated, `config` wrote `./log` outside its work dir) | flash `--resume` per unit; round 2: 5 left (slotCount upper bound not isolated, short-map case hit the version check, equal time bases, recovered pid not compared, AC-3 hash race) → lead (fallback) fixed |
| U10 | `cpp-reviewer` | §8 complete and true? | clean-exit / crash rows missing in headers and README, an overstated "same lines as the dump", `[readPos, writePos)` "exactly", the P0593 wording, a wrong reference, the partial apply of `configureLogBuffers` undocumented | lead fixed (the partial apply is now documented in `log_buffer_config.hpp`, spec History) |
