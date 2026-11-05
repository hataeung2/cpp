# Lesson: log recovery after an unclean exit (`log_recovery`)

**Press Run twice.** Every run of this lesson ends before some of its log lines reach the screen, and the next run brings those lines back.

With `printf` debugging, the lines still in a buffer die with the process. `atugcc::core::Logger` puts lines into a per-thread buffer and a log thread writes them out later (asynchronous, [11_thread_and_log](../11_thread_and_log/README.en.md)), so by default the lines written just before a SIGKILL or a forced end are lost. With `configureLogBuffers({.mappedDir = …})` those buffers live in a **memory-mapped file**: however the process ends, the OS keeps the file's content, and the next run that maps the same folder writes the lines that were never delivered to `recovered_<time>_<pid>.log` (spec [010-10](/docs/specs/010_10_logger_mapped_buffers.md), in Korean). Background: [lock_free_logging.en.md](/docs/cpp_evolution/lock_free_logging.en.md).

## What the run does
1. `configureLogBuffers({.drainInterval = 1000ms, .mappedDir = "log/map"})`: if the folder holds the `.logmap` of an ended run, it turns it into a recovered file (the library writes `[atugcc] recovered N undelivered lines …` on stderr at that moment), then maps this run's buffers. Call it **before** creating a Logger or logging anything: buffers made before it are not mapped.
2. It shows the `recovered_*.log` files in `log/map` and deletes them. On the first run: `nothing to recover (first run?)`.
3. It writes five lines. After `step 1` and `step 2`, `logger.flush()` sends them to the screen; `step 3`–`step 5` are not flushed. The log thread empties the buffers once a second (`drainInterval`), so these three lines are still only in the buffer.
4. It ends with `std::_Exit(0)`. No destructor, flush or exit handler runs, which for the map file is the same situation as a SIGKILL. The Logger contract lists `_exit`/`_Exit` as not covered: the lesson relies not on a promise but on the OS keeping the mapped file, checked on both OSes. The exit code is 0, so the smoke test and the web run show success.

| How the run ends | What the Logger sees | In the next run |
|---|---|---|
| return from `main`, `std::exit`, `std::quick_exit` | a clean exit: it delivers every remaining line and deletes the map file | nothing to recover |
| SIGKILL, ending the task in the task manager | nothing: it cannot act | the undelivered lines are recovered (promised by the contract) |
| `std::_Exit` (this lesson) | nothing: it cannot act | the undelivered lines are recovered (not covered by the contract, but the map file stays as after a SIGKILL) |
| `std::abort`, a bad memory access (crash dump on) | the crash handler writes a dump | a recovered file appears together with the dump ("crash handler: yes") |

## Run
- Web playground: select it in the lesson tree, press Run, then Run once more. The web runs lessons in the lesson folder, so `log/map` is created under this lesson's folder (ignored through `log/` in `.gitignore`).
- Local: `cmake --build --preset <preset> --target lesson_log_recovery`, then run `bin/lessons/lesson_log_recovery` twice from the same folder. `log/map` is created under the folder you run it from (the current folder).

## What to look for
- First run: the only log lines on the screen are `step 1 (flushed)` and `step 2 (flushed)`.
- Step 2 of the second run: the recovered file's header says `ended without a clean exit; crash handler: no` and `3 undelivered lines`. Each line is marked `[delivered]` (already on the screen, shown for context) or `[undelivered]` (never reached any sink). `step 3`–`step 5` are `[undelivered]`.
- Every recovered line still carries its call location (file and line number, [05_source_location](../05_source_location/README.en.md)).
- After a run, `log/map` holds only that run's `.logmap`. The lesson reads the recovered files and deletes them.
- After `flush()` the lesson waits 100 ms, so the log thread is back in its one-second wait, before writing `step 3`–`step 5`. The wait is not synchronization: on a very busy machine some of those lines may rarely reach the screen, and the next run then shows fewer `undelivered` lines.

## Exercises
1. Change `std::_Exit(0)` in step 4 to `std::quick_exit(0)` and run twice. See whether `step 3`–`step 5` appear on the first run's screen and whether anything is left to recover in the next run, and explain why with the table above.
2. Delete `.mappedDir` in step 1 and run twice. `step 3`–`step 5` are left nowhere. Without the map, the lines written during the last drain interval before a SIGKILL are lost: that is what the Logger contract says (the SIGKILL item in the head comment of `logger.hpp`).
3. Locally: set `enableCrashDump = true` and call `std::abort()` instead of `std::_Exit(0)`. When `log/crash_dump_<time>.log` appears, read it with `py -3 tools/read_dump.py <file>`, and compare with the header of the next run's recovered file (`crash handler: yes`). The exit code is not 0, so the web and the smoke test show a failure. Undo it afterwards.
