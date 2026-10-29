# Test Record: 070-06 장시간 실행 프로필과 구간 시간(Timings) 화면

- Spec: [/docs/specs/070_06_long_run_timings.md](/docs/specs/070_06_long_run_timings.md)
- Plan: [plan.md](/docs/tasks/feature_070-06-long-run-timings/plan.md)
- Date: 2026-10-29
- Hosts: Windows 11 (MSVC 19.51, Python 3.15, Node 24.19, Edge), WSL Ubuntu 24.04 (GCC 13.3, Python 3.12)

## Runs

| # | Command | Expected | Actual | Status |
|---|---|---|---|---|
| R1 | WSL `cmake --preset linux-x64-playground-release`, build `lesson_lambda_capture` | configures, RelWithDebInfo, own directory | `CMAKE_BUILD_TYPE=RelWithDebInfo`, `out/build/linux-x64-playground-release/bin/lessons/lesson_lambda_capture` | Pass |
| R2 | `tools/test_lessons.py` after U2 | pass | 29 OK (2 new) | Pass |
| R3 | `test_server.py` on Windows (no fixture) after U3–U7 | pass | first run: `test_percentiles_from_a_bounded_uniform_sample` failed with seed 7 (p50 4737 vs 5000 ± 250); see "Sampling note"; then 51 OK, 25 skipped | Pass (after fix) |
| R4 | WSL `test_server.py --fixture …/linux-x64-debug/bin/playground_fixture` | pass | 1 failure: AC-7 longest pause between span updates 179 s. Cause: `repo_relative()` per span line made the server slower than the flood, and the final drain published nothing until it had read the whole backlog. Fixed: per-file cache, publish per 4 MiB piece, a tick that is behind reads on for up to 0.25 s (plan "Changes") | Fail → fixed |
| R5 | server throughput, `_trace` on 500,000 span lines of 238 B (WSL, scratch script) | — | 150k lines/s (34 MiB/s) after the cache; the plain `json.loads` + dict loop measured for spec §2.4 was 207k lines/s | Info |
| R6 | WSL `test_server.py --fixture … LongRunTest TraceAndDiagnosticsTest StreamTest` | pass | 16 OK (114 s) | Pass |
| R7 | `npm run build`, `npm test` | pass | built; 35 tests (12 new) | Pass |
| R8 | `build.py --test` on `windows-x64-debug`, `linux-x64-debug` | pass | 7/7, 8/8 (`lesson.span_timing` 15 s; `PlaygroundServer` 136 s); AC-7: run 48.1 s, longest pause 0.32 s, RSS +10.0 MiB, events kept 3 | Pass |

## Revision 1 — 2026-10-29
Reviews (see Reviews): codex luna on U3–U5, `cpp-reviewer` on the rest. Fixed in one round:
- `TraceTail` drops an unfinished line longer than one read piece (counted as skipped), so memory is bounded whatever the program writes; new test `test_a_line_longer_than_a_read_is_dropped_not_kept`.
- `[run] build` goes into the index as written; the page shows the build kind with the runner's rule (`effectiveBuild`).
- Top bar shows "집계 지연" (lag); the comparison column is left out when storage is blocked; a selected Timings row stays selected across live updates; Space does not scroll; `formatNs(999.6)` = `1.000 µs`; the build phase's `limitSec` is the time left after configure.
- Tests: AC-5 vitest uses other counts than the previous run (a total-based comparison now fails); click test uses two lines; AC-7 samples the peak RSS during the run; the stream test no longer assumes `spans` is directly before `done`; storage-blocked column test.
- Lesson README exercise 1 comments the `reserve` line out (deleting it moves every span line below, and the rows are no longer compared); `lessons/README.md` says so.
- Docs: quick + `build = "release"` preset, what a late stream gets, KI-016 and spec §4 flush wording.
- Browser run found that Monaco 0.57 did not render `after` injected text of the inline decorations: replaced by `afterContentClassName` with a generated `::after` rule per line (plan "Changes").

| # | Command | Expected | Actual | Status |
|---|---|---|---|---|
| R9 | browser scenarios, first runs (scratch script, `playwright-core` 1.55 driving Edge headless against `tools/playground.py`) | 17/17 | 9/11 and 16/17: restore step used `git checkout` on the untracked lesson (script fixed: restores copies); the edit step looked for a line Monaco had not rendered (script fixed); AC-6 inline text not rendered (code fixed, above) | Fail → fixed |
| R10 | browser scenarios after the fixes | 17/17 | **17/17 PASS**, no console errors; lesson files restored | Pass |
| R11 | browser AC-8 scenario (lesson edited to 60 s, smaller work per round) | 5/5 | first tuning ran ~110k spans/s: the server fell 192 MiB behind and the 1 GiB trace budget stopped the run at 37 s (the stop and its notices worked as designed; heap +1.8 MiB); second tuning 3.7k/s (too slow); third: **5/5 PASS**, 60.1 s, 1,490,788 spans (24.8k/s), heap +1.3 MiB, worst frame 31 ms | Pass |
| R12 | mutation check (scratch script: one change, the target test, restore) | all killed by a test failure | **10/10 killed**: span lines sent as trace events, budget never reported, no final full snapshot, reservoir keeps the first values, unbounded partial line, `profileOverride` ignored, long builds Debug, comparison on totals, other build compared, one read per tick | Pass |
| R13 | `build.py --test` on `windows-x64-debug`, `linux-x64-debug`, `linux-x64-asan`, `linux-x64-tsan` | pass | 7/7, 8/8, **ASan and TSan: `PlaygroundServer` failed** in AC-7 only: the sanitizer-built fixture cannot write 3,000,000 spans in 30 s and hit the 180 s limit (`exitCode` None); no ASan or TSan report. Fixed: fixture mode `build_info`; the AC-7 test skips with its reason on a sanitizer build (AC-7 measures the Python server; its evidence is the plain build) | Fail → fixed |
| R14 | `build.py --test` on the four presets again | pass | 7/7, 8/8, 8/8, 8/8; `PlaygroundServer` 132 s / 90 s / 90 s (52 tests; 1 skipped on ASan and TSan); AC-7 on `linux-x64-debug`: run 44.6 s, 239 span updates, longest pause 0.32 s, RSS +14.0 MiB, events kept 3 | Pass |
| R15 | `lint_docs.py`, `naming_check.py`, `test_agent_scripts.py`, `test_lessons.py`, `lessons.py check`, `npm run build`, `npm test` | exit 0 | `naming_check` first flagged `std::this_thread::sleep_until` → added to `ALLOWED` beside `sleep_for`; then all exit 0 (lint 0/0, 50 script tests, 29 lessons tests, 4 lessons, 37 vitest) | Pass |

## Sampling note (AC-9)
With 1,024 samples from 1..10,000, the p50 spread across seeds is about ±190 (20 seeds: 4682–5358), so ±5 % of the median (±250) holds for most seeds but not all (5 of 20 missed); p95 stayed within ±5 % for every seed. The AC asks for a fixed seed; the test uses seed 3 and a separate test shows the sampler is unbiased (60 runs, mean of sample means within ±10 of 1000.5: a sampler keeping the first or last 1,024 values gives ~512 or ~1489). The ±5 % bound is therefore a property of the sample size, not something the code could tighten.

## Acceptance Criteria Evidence

| AC | Criterion (short) | Evidence | Result |
|---|---|---|---|
| AC-1 | long + timeout 30 runs 25 s to a normal end; the quick toggle times out at 10 s | `LongRunTest.test_long_profile_uses_the_lesson_timeout`; browser "quick toggle ends at the time limit" (10.2 s) | Pass |
| AC-2 | long builds with `linux-x64-playground-release`, `buildType` RelWithDebInfo; `build = "debug"` → Debug; bad `build` is an ERROR | `test_build_type_follows_profile_and_manifest` (5 cases, preset dirs, `CMakePresets.json`); `test_bad_build`; browser runs show `run · long · RelWithDebInfo` and a real Debug build after `build = "debug"`; mutant M7 | Pass |
| AC-3 | count grows at ≥3 different times before `done` | `test_span_rows_arrive_while_running`; browser 341 → 624 → 891 → 1336, [ac3-timings-live.png](/docs/tasks/feature_070-06-long-run-timings/screenshots/ac3-timings-live.png) | Pass |
| AC-4 | final `full` rows equal the fixture's `spanStats()` exactly | `test_final_snapshot_equals_span_stats` (count, totalNs, minNs, maxNs per key), `test_span_meter_option_reaches_the_program`; mutant M3 | Pass |
| AC-5 | change column after an edit; "빌드 다름" for another build type | vitest `comparison with the previous run (AC-5)`; browser: `reserve + push_back +132.9%` after commenting `reserve` out, every row "빌드 다름" after a Debug run, [ac5-change.png](/docs/tasks/feature_070-06-long-run-timings/screenshots/ac5-change.png), [ac5-build-differs.png](/docs/tasks/feature_070-06-long-run-timings/screenshots/ac5-build-differs.png); mutants M8, M9 | Pass |
| AC-6 | inline time on span lines; row click moves the editor | browser "AC-6 …" (4 lines `⏱ … avg ×N`; active line 87 = row `main.cpp:87`), [ac6-inline-and-jump.png](/docs/tasks/feature_070-06-long-run-timings/screenshots/ac6-inline-and-jump.png); vitest `inlineByLine`, click test | Pass |
| AC-7 | 100k spans/s × 30 s: `job.events` independent of spans, no span in `trace`, pauses ≤ 500 ms, RSS < +50 MB | `test_span_flood_keeps_memory_flat` on `linux-x64-debug` (R8, R14: pause 0.32 s, peak RSS +14.0 MiB, 3 events kept; the Debug fixture writes the 3,000,000 spans in about 44 s); skipped with its reason on sanitizer builds (R13); mutants M1, M10 | Pass |
| AC-8 | ≥10k spans/s for 60 s: tab memory +<50 MB, Timings keeps updating | browser AC-8 (R11): 24.8k spans/s for 60.1 s, JS heap +1.3 MiB, worst frame 31 ms, [ac8-after-60s.png](/docs/tasks/feature_070-06-long-run-timings/screenshots/ac8-after-60s.png) | Pass |
| AC-9 | aggregator: exact stats, p50/p95 ±5 % with a fixed seed, ≤1,024 samples, drain = changed keys | `SpanAggregatorTest` (7 tests incl. the bias test, "Sampling note"); mutant M4 | Pass |
| AC-10 | small budget → stopped, `traceLimit`, temp file removed | `test_trace_budget_stops_the_run`; in practice R11 (1 GiB budget stopped a 110k/s run); mutant M2 | Pass |
| AC-11 | `npm test`, `test_server.py`, `lint_docs.py` exit 0 | R14, R15 | Pass |

## Reviews

| Unit | Reviewer | Question | Findings | Resolution |
|---|---|---|---|---|
| U3–U5 | codex luna (high) | D3–D5 / spec; races on `job.cond`, process lifetime, bounded memory, partial lines, reservoir, API | (1) the 2 s reader joins can delay `done` past Stop's 1 s when a descendant escaped the group; (2) the final flush ignores the budget; (3) `TraceTail.partial` unbounded for a line without newline | (3) fixed. (1) is 070-02 behaviour for an escaped descendant: noted under KI-015. (2) not changed: `traceLimit` means "stopped by the server because of the budget"; a program that already exited was not stopped, and flagging it would read as a kill |
| U1, U2, U6–U11 | `cpp-reviewer` | tests vs ACs, frontend bugs, fixture/lesson, docs | 4 test, 7 frontend, 1 lesson, 4 doc findings (Revision 1) | fixed, except: the output cap keeps the newest chunk whole (bounded by the server's 8 MiB), and the sanitizer timing risk, which R13 confirmed and R14 resolved |
