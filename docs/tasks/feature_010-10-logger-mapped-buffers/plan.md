# Plan: 010-10 메모리 매핑 파일 로그 버퍼와 다음 실행 때 복구

- Spec: [/docs/specs/010_10_logger_mapped_buffers.md](/docs/specs/010_10_logger_mapped_buffers.md) (approved 2026-10-30)
- Branch: `feature/010-10-logger-mapped-buffers` (from `main` at `c4caa62`)
- Delegation: first task under the 2026-10-30 rule ([delegation.md](/.agent/rules/delegation.md) §1): agy `flash` writes code, test and tool units; the lead writes docs.

## Platform facts checked before the plan (scratch experiments, 2026-10-30)
- Windows: a file opened with `FILE_SHARE_READ | FILE_SHARE_DELETE` makes a second open with write access fail with `ERROR_SHARING_VIOLATION` (32) while the owner lives. `SetFileInformationByHandle(FileDispositionInfoEx, DELETE | POSIX_SEMANTICS)` succeeds while the file is mapped; the view stays writable and the file is gone after the process exits. After `TerminateProcess` the mapped bytes are in the file.
- WSL (`/mnt/c` drvfs and ext4): `posix_fallocate` works, `flock(LOCK_EX | LOCK_NB)` from a second process fails while the owner lives and succeeds after SIGKILL, and the `MAP_SHARED` bytes are in the file after SIGKILL.

## Design decisions (fixed here; units implement them, they do not decide them)

### D1 Mapped file (`src/core/mapped_file.hpp`, `src/core/log_map_posix.cpp`, `src/core/log_map_win.cpp`)
```cpp
namespace atugcc::core::detail {
class MappedFile {                     // move-only; the destructor unmaps and closes
public:
    // New file (fails if it exists), locked for the life of the handle, space reserved, mapped read-write.
    static Expected<MappedFile> createLocked(const std::filesystem::path& path, std::size_t bytes) noexcept;
    // Existing file: std::nullopt when another process holds it (a live run). Mapped read-only.
    // Size 0 or above kMaxMappedFileBytes (1 GiB + 64 KiB): FileIOFailure.
    static Expected<std::optional<MappedFile>> openIfEnded(const std::filesystem::path& path) noexcept;
    const std::byte* data() const noexcept;  std::byte* data() noexcept;  std::size_t size() const noexcept;
    // POSIX: unlink now. Windows: delete disposition with POSIX semantics (gone when the last handle
    // closes). The mapping stays valid in both cases.
    Result removeFile() noexcept;
};
}
```
- POSIX `createLocked`: `open(O_RDWR | O_CREAT | O_EXCL | O_CLOEXEC, 0644)`, `flock(LOCK_EX | LOCK_NB)`, `posix_fallocate(fd, 0, bytes)` (on `EOPNOTSUPP` / `EINVAL` use `ftruncate`; other errors fail and unlink the file), `mmap(PROT_READ | PROT_WRITE, MAP_SHARED)`. `openIfEnded`: `open(O_RDWR | O_CLOEXEC)`, `flock(LOCK_EX | LOCK_NB)` with `EWOULDBLOCK` → `nullopt`, `fstat`, `mmap(PROT_READ, MAP_PRIVATE)`.
- Windows `createLocked`: `CreateFileW(GENERIC_READ | GENERIC_WRITE | DELETE, FILE_SHARE_READ | FILE_SHARE_DELETE, CREATE_NEW)`, `SetFilePointerEx` + `SetEndOfFile`, `CreateFileMappingW(PAGE_READWRITE)`, `MapViewOfFile(FILE_MAP_WRITE)`. `openIfEnded`: `CreateFileW(GENERIC_READ | GENERIC_WRITE | DELETE, share 0, OPEN_EXISTING)` with `ERROR_SHARING_VIOLATION` → `nullopt`, `GetFileSizeEx`, `CreateFileMappingW(PAGE_READONLY)`, `MapViewOfFile(FILE_MAP_READ)`. `removeFile`: `FileDispositionInfoEx` with `FILE_DISPOSITION_FLAG_DELETE | FILE_DISPOSITION_FLAG_POSIX_SEMANTICS`.
- Every OS error is `FileIOFailure`. Only these two files include OS headers.

### D2 Map format and the run's arena (`include/atugcc/core/detail/log_map.hpp`, `src/core/log_map.cpp`)
Format (all little-endian, no pointers). The structs are plain (trivially copyable) so that recovery and tests can `memcpy` them; the live process updates `flags` and `arenaUsed` through `std::atomic_ref` (C++20).
```text
MapHeader (first 128 bytes of a 4096-byte page; the rest is zero)
  char   magic[8]        "ATGLMAP1"
  uint32 version         1
  uint32 arenaOffset     kArenaOffset = 4096 + 256 * 128 = 36864 (page aligned)
  uint64 fileBytes       mappedBytes
  uint32 pid
  uint32 flags           bit0 = crash handler ran (kMapFlagCrash), bit1 = clean exit (kMapFlagCleanExit)
  uint64 startSystemNs   system_clock ns since 1970 at map start
  uint64 steadyBaseNs    steady_clock ns at map start      } time base pair taken together
  int64  systemBaseNs    system_clock ns at the same moment }
  uint64 arenaUsed       absolute offset of the next free byte (starts at arenaOffset, 64-byte steps)
  uint32 labelCount      256
  uint32 labelBytes      128
  uint8  reserved[56]
LabelEntry[256] at 4096 (128 bytes each)
  uint16 id              0 = empty; entry i holds Logger id i
  uint16 len             0..124
  char   text[124]       UTF-8, cut at a character boundary
Arena at arenaOffset: [ATGLBUF1 block (010-09 D1): 64 + slotCount * 256 bytes] repeated
BufferHeaderDisk: a plain mirror of 010-09 BufferHeader (same offsets, static_assert), used to memcpy
```
- Constants: `kMapMagic`, `kMapVersion`, `kMapHeaderBytes`, `kLabelCount`, `kLabelBytes`, `kLabelTextBytes`, `kArenaOffset`, `kMapFlagCrash`, `kMapFlagCleanExit`, `kMinMappedBytes` = 1 MiB, `kMaxMappedBytes` = 1 GiB, `kDefaultMappedBytes` = 8 MiB. `static_assert(std::atomic_ref<std::uint32_t>::is_always_lock_free)` and the same for `uint64_t`.
- Free functions in `atugcc::core::detail` (state in `log_map.cpp` only, at namespace scope, so the crash path needs no function-local static guard):
  - `Result startLogMap(const std::filesystem::path& dir, std::size_t bytes) noexcept`: once per process. Active with the same directory (compared after `std::filesystem::absolute` + `lexically_normal`) → success, no change; with another → `InvalidArgument`. Otherwise: `create_directories(dir)`, `recoverLogMaps(dir)` (D4; its failure does not stop the start), `createLocked(dir / "atugcc-<pid>-<UTC YYYYMMDDTHHMMSSmmm>.logmap", bytes)`, write the header (pid, clocks, `arenaUsed = kArenaOffset`), publish the base pointer (`std::atomic<std::byte*>`, release), call `republishLoggerLabels()` (D3). The `MappedFile` is held by a never-destroyed object. Any failure → `FileIOFailure`, nothing active. Catches every exception.
  - `bool logMapActive() noexcept`, `std::filesystem::path logMapPath()` (empty when inactive).
  - `ThreadLogBuffer* allocateMappedBuffer(std::uint32_t slotCount) noexcept`: CAS on `arenaUsed`; no room → `nullptr`, and the first time prints `[atugcc] log map full (<bytes> bytes): new thread buffers are not recoverable` to stderr and counts every refusal (`mappedRefusals()`). Success → `ThreadLogBuffer::createIn(base + offset, slotCount)`.
  - `bool isMappedBuffer(const ThreadLogBuffer*) noexcept` (address inside the arena).
  - `void setLogMapLabel(std::uint16_t id, std::string_view text) noexcept` / `clearLogMapLabel(std::uint16_t id) noexcept`: callers hold the service mutex; ids 0 and ≥ 256 are ignored. Write `len` and `text`, then `id` last.
  - `void markLogMapCrash() noexcept`: signal-safe (`atomic_ref` `fetch_or` on `flags`, relaxed), no-op when inactive.
  - `void finishLogMapCleanly() noexcept`: set `kMapFlagCleanExit`, then `removeFile()`. Never unmaps: threads that outlive `shutdown()` and the crash handler still use the buffers (010-09 D2).

### D3 Wiring (existing files)
- [`log_buffer_config.hpp`](/include/atugcc/core/log_buffer_config.hpp): spec §2.1 (`mappedDir`, `mappedBytes`, `LogMapRecovery`, `recoverLogMaps`).
- `configureLogBuffers`: validate everything first (slots, drain interval, `mappedBytes` in [1 MiB, 1 GiB] even when `mappedDir` is empty), then store slots and drain interval, then, when `mappedDir` is not empty, return `startLogMap(mappedDir, mappedBytes)`.
- Environment: `ensureConfigInitialized` (first buffer or first `configureLogBuffers`) reads `ATUGCC_LOG_MAP_DIR` once (`readEnvMapDir()` in `thread_crash_prep.cpp`, next to `readEnvSlots`); when set it calls `startLogMap(dir, kDefaultMappedBytes)` and on failure prints `[atugcc] ATUGCC_LOG_MAP_DIR=<dir>: cannot map, logging stays in memory` once.
- `acquireNode` step 2: `allocateMappedBuffer(targetSlots)` first, `ThreadLogBuffer::create` when it returns `nullptr`. Reuse (step 1) and the emergency buffer do not change.
- `log_service.cpp`: `registerLogger` calls `setLogMapLabel(id, label)` with label = `filePath.filename()` as UTF-8, or `logger#<id>` when there is no file; `unregisterLogger` calls `clearLogMapLabel(id)`. New `void republishLoggerLabels() noexcept` (declared in `log_map.hpp`, defined in `log_service.cpp`): `tryLockService()`; if it gets the lock, write the labels of every registered Logger, else skip (avoids a deadlock when the map starts from a thread that holds the service mutex; such Loggers are labelled `logger#<id>` in recovery). `shutdown()` calls `finishLogMapCleanly()` after its final `drainLocked()`. A comment at the `advanceRead` loop in `drainLocked` states the spec 010-10 Assumption 4 contract: sinks first, then `readPos`.
- `memory_dump.cpp` `detail::writeDump`: `markLogMapCrash()` first when the event type is not `"manual"`.
- [`CMakeLists.txt`](/CMakeLists.txt): `log_map.cpp`, `log_map_recover.cpp` in `CORE_SOURCES`; `log_map_win.cpp` / `log_map_posix.cpp` next to the crash handler files.

### D4 Recovery (`src/core/log_map_recover.cpp`)
`Expected<std::vector<LogMapRecovery>> recoverLogMaps(const std::filesystem::path& dir)`; `std::error_code` overloads only; `std::bad_alloc` → `Unexpected`.
1. `dir` missing → empty vector. Not a directory → `FileIOFailure`.
2. For each `*.logmap` in name order: `openIfEnded` (this run's own file is locked, so it comes back as `nullopt`; recovery does not call `logMapPath()`, because `startLogMap` calls recovery while holding its mutex). `nullopt` → skip (live). Error → stderr `[atugcc] cannot open <name>: skipped`, skip.
   - Amended during implementation (lead, measured): when the lock is held, read the header's pid without the lock; if that process no longer exists (`MappedFile::processAlive`), retry the lock every 50 ms for up to 1 s. On Linux a SIGKILLed multi-threaded owner kept its `flock` for up to ~200 ms after the parent's `wait()` returned, so a program restarted at once skipped the map (3 of 3 runs). Still locked after the wait: stderr `... is still locked although pid <p> ended: skipped (a later run recovers it)`. The pid only decides whether to wait; whether to skip is still decided by the lock (Assumption 8).
3. Header check (memcpy): size ≥ `kArenaOffset`, magic, version 1, `arenaOffset == kArenaOffset`, `fileBytes == size`, `labelCount == 256`, `labelBytes == 128`. Failing → close, rename to `<name>.corrupt` (replace an existing one), stderr `[atugcc] <name> is not a readable log map: renamed to <name>.corrupt`, not returned.
4. `kMapFlagCleanExit` set → `removeFile`, not returned.
5. Labels: entry i valid when `id == i`, `len ≤ 124`; else `logger#<i>`. Id 0 → `dbgbuf`; id ≥ 256 → `logger#<id>`.
6. Walk `[kArenaOffset, end)` with `end = arenaUsed` if `kArenaOffset ≤ arenaUsed ≤ size`, else `size`. At each offset, a header is valid when: magic `ATGLBUF1`, `slotBytes == 256`, `slotCount` a power of two in [64, 65536], the block fits before `end`, `readPos ≤ writePos ≤ reservePos`, `writePos − readPos ≤ slotCount`. Valid → read it, move past the block. Invalid → `skippedBuffers += 1`, then move in 64-byte steps until a valid header or `end` (one count per bad region).
7. Records of a buffer: positions `[max(0, max(reservePos, writePos) − slotCount), writePos)`. A record is first-flag slot … last-flag slot on consecutive positions with every `len ≤ 232` and at most `slotCount / 2` slots; anything else is skipped up to the next first-flag slot. Record end ≤ `readPos` → delivered, else undelivered.
8. Sort all records by `(timeNs, threadNo, threadSeq)`. Wall time = `systemBaseNs + (timeNs − steadyBaseNs)` (signed), printed `YYYY-MM-DDTHH:MM:SS.uuuuuuZ` (the file sink format, 010-09 D3).
9. Write `<dir>/recovered_<UTC YYYYMMDDTHHMMSSmmm of startSystemNs>_<pid>.log.tmp`, then rename to the name without `.tmp`:
   ```text
   # atugcc recovered log (spec 010-10)
   # pid <pid>, started <wall of startSystemNs>, map <map file name>
   # ended without a clean exit; crash handler: <yes|no>
   # <U> undelivered lines (never reached any sink: not in the log file), <D> delivered lines (context), <S> skipped buffers
   # a line delivered just before the end can appear both here as undelivered and in the log file
   <wall> T<threadNo> [undelivered|delivered] <label> <record text>
   ```
   Write or rename fails → keep the `.logmap`, stderr line, not returned. Success → `removeFile()` and close the map; stderr `[atugcc] recovered <U> undelivered lines from pid <pid> into <path>`; append a `LogMapRecovery`.

### D5 Probe and checker (`tests/core/log_map_probe.cpp`, `tests/core/check_log_map.py`, CTest `LogMap`)
A separate probe keeps the 010-09 `crash_probe` and its checks unchanged (the spec's "Verified by" for AC-1, AC-4, AC-5 names `crash_probe`; the evidence is the same, from this probe). `log_map_probe <mode> <dir>` never deletes `<dir>` (the checker prepares it). Lines are `P<p> L<i>`. Modes:
- `killmap`: `configureLogBuffers({.drainInterval = 1000ms, .mappedDir = dir})`; Logger file `dir/app.log`, Async, `OverflowPolicy::Block`, level Debug; 4 threads × 1,000 lines; join; print `READY`, sleep forever. The checker kills it (`Popen.kill()`: SIGKILL / `TerminateProcess`).
- `startrecover`: `configureLogBuffers({.mappedDir = dir})` (recovers on start, Assumption 7), logs one line, returns 0.
- `recover`: prints `RECOVERED <file> <pid> <undelivered> <delivered> <skipped> <crash 0|1>` per entry of `recoverLogMaps(dir)`; `ERROR` and exit 1 on error.
- `live`: mapping on, one line, print `READY`, sleep forever.
- `normal` / `exit` / `quickexit`: mapping on, 100 lines, end that way.
- `abort`: mapping on, `enableCrashDump`, 100 lines (one Sync), `std::abort()`.
- `config`: AC-7 sequence in one process, prints `OK <step>` / `FAIL <step>`: `mappedBytes` 512 KiB → `InvalidArgument`; `mappedDir` = `<dir>/file.txt/sub` with `file.txt` a regular file → `FileIOFailure` and a Sync line still reaches `snapshot()`; `<dir>/a` → success; `<dir>/b` → `InvalidArgument`; `<dir>/a` again → success; empty → success; `logMapActive()` true.
- `env`: expects `ATUGCC_LOG_MAP_DIR` (set by the checker); logs one line; prints `MAPPED 1` when `isMappedBuffer(&threadBuffer())`.
- `full`: `mappedBytes` = 1 MiB; 12 threads alive together (latch), each logs 1,000 lines to `dir/app.log` (Block); prints `MAPPED <n> HEAP <m>` from `isMappedBuffer` per thread buffer.
- `threads`: mapping on; 50 rounds × 8 threads that log 100 lines and end; ends normally (TSan, AC-11).
Checker cases (every preset; `abort` skipped under sanitizers like 010-09):
- AC-1/AC-2: `killmap` → kill after READY → copy the `.logmap` aside (`killmap.logmap.copy`, for AC-10) → `startrecover`. The union of `app.log` lines and recovered `[undelivered]` lines has every `P<p> L<i>` (4 × 1,000); every line missing from `app.log` is `[undelivered]`; at least one `[undelivered]` line; recovered lines are in time order; each has `T<n>` and label `app.log`; the header counts equal the line counts; no `.logmap` from the killed pid remains; stderr of `startrecover` has the `recovered` line.
- AC-3: `live` → READY → `recover` lists nothing for it and its `.logmap` still exists → kill `live` → `recover` lists it.
- AC-4: `normal`, `exit`, `quickexit` → no `.logmap` remains; `recover` lists nothing.
- AC-5: `abort` → a dump exists; `recover` shows crash 1; the recovered header says `crash handler: yes`.
- AC-7: `config` all `OK`; `env` prints `MAPPED 1`.
- AC-8: `full` → `MAPPED 7 HEAP 5` (arena (1 MiB − 36,864) / 131,136 = 7 buffers), all 12,000 lines in `app.log`, exactly one `log map full` line on stderr.
- AC-11: `threads` → every line in `app.log`, no `.logmap` left.

### D6 GoogleTest (`tests/core/test_log_map.cpp`, AC-6)
Builds map files in a temporary directory from the D2 structs and `ThreadLogBuffer::createIn` on 64-byte-aligned storage (records through `tryWrite`, delivery through `advanceRead`), then calls `recoverLogMaps`. Cases: a valid file (undelivered/delivered counts, file text, time order, labels, `.logmap` removed); clean-exit flag (removed, not returned); crash flag; bad magic, truncated file, wrong `fileBytes` (→ `.corrupt`, not returned); one buffer with `slotCount` out of range, `writePos < readPos`, `len > 232`, a broken continuation (→ other buffers recovered, `skippedBuffers` counted); 1,000 seeded mutations (byte flips, truncations, random files) never crash (ASan/UBSan clean); a missing directory → empty vector.

### D7 `tools/read_dump.py` (AC-10)
Input starting with `ATGLMAP1` is read as a map file: header, labels and arena walk as D4 steps 3, 5, 6, 7 (same validation), records printed with the existing renderer (wall time from the header's base pair). `--undelivered` works the same. `tools/test_read_dump.py` gets a map built in Python.

## Units
| Unit | File | Change (what, where, AC) | Check | Risky | Author | Reviewer | Tokens (in / out) | Status |
|---|---|---|---|---|---|---|---|---|
| U1 | `src/core/mapped_file.hpp`, `src/core/log_map_posix.cpp` | D1 POSIX | `linux-x64-debug` builds `atugcc_core` | yes (platform) | agy flash | codex luna (high) | | |
| U2 | `src/core/log_map_win.cpp` | D1 Windows | `windows-x64-debug` builds `atugcc_core` | yes (platform) | agy flash | codex luna (high) | | |
| U3 | `include/atugcc/core/detail/log_map.hpp`, `src/core/log_map.cpp`, `CMakeLists.txt` | D2 | both presets build | yes (layout, atomics) | agy flash | codex luna (high) | | |
| U4a | `log_buffer_config.hpp`, `log_registry.cpp`, `thread_crash_prep.cpp` | D3 config, env, `acquireNode` | both presets; `LogBufferConfigTest.*` | yes (lifetime) | agy flash | codex luna (high) | | |
| U4b | `log_service.cpp`, `memory_dump.cpp` | D3 labels, shutdown, crash flag | both presets; `Logger*` | yes (locks, crash path) | agy flash | codex luna (high) | | |
| U5 | `src/core/log_map_recover.cpp` | D4 | both presets | yes (untrusted input, layout) | agy flash | codex luna (high) | | |
| U6 | `tests/core/test_log_map.cpp` | D6 (AC-6) | `LogMap*` on 4 presets | no (test) | agy flash | `cpp-reviewer` | | |
| U7 | `tests/core/log_map_probe.cpp`, `tests/CMakeLists.txt` | D5 probe | builds on both presets | no (test) | agy flash | `cpp-reviewer` | | |
| U8 | `tests/core/check_log_map.py` | D5 checker (AC-1 … AC-5, AC-7, AC-8, AC-11) | CTest `LogMap` on 4 presets | no (test) | agy flash | `cpp-reviewer` | | |
| U9 | `tools/read_dump.py`, `tools/test_read_dump.py` | D7 (AC-10) | unittest; run on the AC-1 copy | no (tool) | agy flash | `cpp-reviewer` | | |
| U10 | §8 documents | AC-12, evolution page, KI, lesson candidates | lint | no (doc) | lead | `cpp-reviewer` | | |
| U11 | testrecord | AC-9 Release measurement | `logger_contention_probe` with and without `ATUGCC_LOG_MAP_DIR` | no | lead | — | | |
