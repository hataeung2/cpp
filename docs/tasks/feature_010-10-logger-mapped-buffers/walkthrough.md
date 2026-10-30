# Walkthrough: 010-10 메모리 매핑 파일 로그 버퍼와 다음 실행 때 복구

- Spec: [/docs/specs/010_10_logger_mapped_buffers.md](/docs/specs/010_10_logger_mapped_buffers.md) (approved 2026-10-30)
- Evidence: [testrecord.md](/docs/tasks/feature_010-10-logger-mapped-buffers/testrecord.md) (AC-1 … AC-12 Pass; AC-11 with KI-030, pre-existing)
- Branch: `feature/010-10-logger-mapped-buffers`

## Result
- **SIGKILL no longer loses buffered lines** when mapping is on: `configureLogBuffers({.mappedDir = "log"})` (or `ATUGCC_LOG_MAP_DIR`) puts the thread buffers in `log/atugcc-<pid>-<time>.logmap`. The next run that maps the same directory, or `recoverLogMaps(dir)`, writes `recovered_<time>_<pid>.log`: every `[undelivered]` line plus each thread's newest `[delivered]` lines, time-ordered, with the Logger's file name as label. The log file is never changed. A clean exit removes the map; a crash leaves it for the next run (`crash handler: yes`).
- Off by default; no hot-path change: shared Logger p99 with mapping on is 0.93–0.98× of mapping off on both hosts.
- `tools/read_dump.py` reads `.logmap` files without recovering them.
- Recovery treats the file as untrusted input (every size and position checked, `memcpy` only); a corrupt map is renamed `.corrupt`, a live run's map is never touched (file lock).

## Found while implementing
- Linux keeps a SIGKILLed multi-threaded owner's `flock` for a short time after its parent's `wait()` returns; a program restarted at once skipped the map. Recovery now waits up to 1 s when the map's pid no longer exists (plan D4 amendment).
- With `ATUGCC_LOG_MAP_DIR`, the first thread to read the configuration (often the log thread) started the map while the main thread took a heap buffer. Other threads now wait for the start to finish (plan D3).
- `CrashDump` `normal` is flaky under load on `main` too: KI-030 (a thread's last lines can be delivered after the next thread's, across a `join()`).

## Lead (fallback / small) units
- Review fixes too small for another agy round (empty catches, `noexcept` mutex, `strcmp` on the crash path, overflow guards), the two fixes above, and the round-2 test gaps: each reviewed by codex or `cpp-reviewer` (testrecord Reviews).

## Delegation (first task under the 2026-10-30 rule)
- agy flash wrote all 9 code, test and tool units (16 calls, about 5.3 M input / 1.0 M output tokens); codex reviewed the 6 risky units (8 calls, about 1.6 M input); `cpp-reviewer` reviewed tests and docs (3 calls).
- Cost observed: a `--resume` fix round costs as much as the first call (U1: two lines, 115 k input, 7 min; U6–U9 rounds 190–450 k each). For one- or two-line review fixes, `lead (small)` was cheaper; the rule (delegation.md §1, small change) already allows it for ordinary units, and this task applied it to risky-unit review fixes too, each re-reviewed.
- agy's "built cleanly" reports were not evidence: U5 claimed a clean build before its file was in CMake.

## Follow-ups
- KI-029: the arena has a fixed size (threads beyond it are not recoverable).
- KI-030: order across a thread handoff (010-09); waiting for a user decision.
