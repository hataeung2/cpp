# Test Record: 020-06 Tracer 구간 시간 측정 (span)

- Spec: [/docs/specs/020_06_tracer_span_timing.md](/docs/specs/020_06_tracer_span_timing.md)
- Plan: [plan.md](/docs/tasks/feature_020-06-tracer-span-timing/plan.md)
- Date: 2026-10-29
- Hosts: Windows 11 (MSVC 19.51, VS 2026 Community), WSL Ubuntu 24.04 (GCC 13.3, Python 3.12)

## Runs

| # | Command | Expected | Actual | Status |
|---|---|---|---|---|
| R1 | agy flash (U1–U3) self-check: `build.py --preset windows-x64-debug --target atugcc_tests` | builds with `/W4 /WX` | built | Pass |
| R2 | `build.py --preset windows-x64-debug --test` after U1–U6 | 6/6, zero warnings | first run: link of `span_cost_probe.exe` failed with "file is being used by another process" (vcpkg applocal step; compile was clean); rerun 6/6 | Pass |
| R3 | `build.py --preset linux-x64-debug --test` | 7/7, `-Werror` | 7/7; `SpanCost` 14 s | Pass |
| R4 | `atugcc_tests --gtest_filter='Span*'` on both Debug builds | all pass; the death test runs on Linux | Windows 18/18, Linux 19/19 (incl. `SpanLifetimeDeathTest.SpanOutlivingTracerAsserts`) | Pass |
| R5 | `span_cost_probe 50000` on both Debug builds | AC-5 line counts equal | equal; "faster" margin thin: Linux 1696 vs 1640 ms, Windows 2913 vs 2462 ms (JSON formatting at -O0 dominates) → timing check made Release-only (plan "Deviation") | Pass (see note) |
| R6 | `build.py --test` on `linux-x64-asan`, `linux-x64-tsan` | ASan+UBSan and TSan clean | 7/7 each, no sanitizer report | Pass |
| R7 | `build.py --preset linux-x64-release --test` (first configure of this preset) | 7/7 | configure failed: FetchContent could not rename the extracted googletest on `/mnt/c` ("Permission denied", a Windows build ran at the same time); rerun with `--fresh` alone: 7/7 | Pass (environment retry) |
| R8 | `build.py --preset windows-x64-release --test` | 6/6, `/WX` | 6/6 | Pass |

## Revision 1 — 2026-10-29
First-pass reviews: codex luna on U1–U3 found that an empty or non-ASCII `ATUGCC_TRACE_FLUSH_MS` fell back to 0 without the diagnostic of plan D3 (the empty-value branch was unreachable). Fixed by the lead (one-branch change, `lead (fallback)`): unset or empty stays silent like `ATUGCC_TRACE_OUT`, a non-ASCII value is reported. `cpp-reviewer` on U4–U6 found tests that could pass with a wrong implementation; all fixed in one round:
- AC-2 samples now arrive in a scrambled order (min/max are neither first nor last sample).
- wall/cpu "separate rows" check uses one source location for both spans.
- cpu meter scale checked against the wall time of a 50 ms busy loop (≤ wall + 16 ms; Linux ≥ 10 ms).
- new `SpanJson.FlushIntervalHoldsLinesBack` (1 h interval: 0 lines before the sink is destroyed, 1 after).
- new `SpanFormat.TimingsRowColumns` (count 2, distinct total/mean/min/max cells).
- new `SpanTiming.ThrowingSinkDoesNotEscapeStop`; `static_assert`s that `ScopedSpan` is neither copyable nor movable.
- perf-vs-wall ordering uses 1 s (no preemption flake); the concurrent switching test asserts both meters were used.
- `check_trace_stream.py` checks stderr: one warning for an unknown meter and for `ATUGCC_TRACE_FLUSH_MS=100ms`, none for valid values (proves the variables are read).
- `span_cost_probe` exits when a file sink cannot be opened.

| # | Command | Expected | Actual | Status |
|---|---|---|---|---|
| R9 | all six presets in sequence (`linux-x64-release` with `--fresh`, `linux-x64-debug`, `linux-x64-asan`, `linux-x64-tsan`, `windows-x64-debug`, `windows-x64-release`), `--test`, after the test fixes | pass, zero warnings | 7/7, 7/7, 7/7, 7/7, 6/6, 6/6 | Pass |
| R10 | `build.py --test` on `windows-x64-debug` and `linux-x64-debug` after the checker/probe fixes and the header comment; `check_trace_stream.py -- ./bin/trace_stream_probe` (WSL) | pass | 6/6, 7/7; `check_trace_stream: OK (28 events, 3 spans, 5 diagram parts)` | Pass |
| R11 | `span_cost_probe` (no arguments: 200,000 spans, 100,000 for AC-5) on `windows-x64-release` | AC-5 OK | see "Cost measurements"; flush per line 652.5 ms vs 100 ms interval 349.7 ms, 100,000 lines each; `AC-5: OK` | Pass |
| R12 | same on `linux-x64-release` (WSL) | AC-5 OK | flush per line 235.5 ms vs 177.4 ms, 100,000 lines each; `AC-5: OK` | Pass |
| R13 | `naming_check.py` | exit 0 | first run: 3 std names in the test (`adjacent_find`, `fetch_add`, `find_first_not_of`) → added to the `ALLOWED` list (names fixed by std, impl.md §1); then 0 | Pass |
| R14 | `test_agent_scripts.py` (after the `naming_check.py` change), `lint_docs.py` | exit 0 | OK; 0 errors, 0 warnings (19 legacy info) | Pass |
| R15 | mutation check (scratch script: apply one change, `build.py --preset linux-x64-debug` with the target test or `--test`, restore) | every mutant killed by a test failure, not a compile error | 6/6 killed: M1 span ends on the tracer's current meter (`SwitchDuringSpanKeepsStartMeter`), M2 `stop()` without its guard (`SleepIsMeasuredOnce`), M3 min never updated (`StatsAggregatePerSite`), M4 flush every line despite the interval (`FlushIntervalHoldsLinesBack`), M5 `ATUGCC_TRACE_FLUSH_MS` never read (`TraceStream`), M6 span key order swapped (`LineMatchesSchema`) | Pass |

## Revision 2 — 2026-10-29
Doc review of U7 (`cpp-reviewer`) found seven statements that said more or less than the code; all corrected: "lock-free" meter swap → "without the Tracer lock"; Windows `cpu` short spans read 0 *or* one tick; the "time the outer range" threshold now follows the cost table (hundreds of ns without a sink, µs with the stream); `recordSpan` examples show `(void)` (it is `[[nodiscard]]`); README aggregation key includes the meter; KI-016 names the buffer-full and interval-passed cases and that 070-06's "100 ms" is not a bound; KI-011 also names `µs`.

| # | Command | Expected | Actual | Status |
|---|---|---|---|---|
| R16 | `build.py --test` on `windows-x64-debug`, `linux-x64-debug` after the header comment change; `lint_docs.py`; `naming_check.py` | pass, exit 0 | 6/6, 7/7; 0 errors, 0 warnings; 0 snake_case | Pass |

## Cost measurements (AC-6, AC-8)
`span_cost_probe`, Release, ns per operation (span = `timeScope` + destructor, two meter calls included):

| Configuration | windows-x64-release | linux-x64-release |
|---|---|---|
| meter read, wall | 18.3 | 22.7 |
| meter read, cpu | 128.5 | 212.5 |
| span, wall, no sink | 278.1 | 147.9 |
| span, cpu, no sink | 494.8 | 546.4 |
| span, wall, JSON sink + 100 ms | 4072.3 | 2367.2 |
| span, wall, JSON sink, flush 0 | 6883.6 | 2997.6 |

## Acceptance Criteria Evidence

| AC | Criterion (short) | Evidence | Result |
|---|---|---|---|
| AC-1 | 20 ms sleep → 20–200 ms; `stop()` then destructor records once | `SpanTiming.SleepIsMeasuredOnce`, `DestructorRecordsWithoutStop`; mutant M2 | Pass |
| AC-2 | 1000 spans at one site: count 1000, min ≤ mean ≤ max, total = sum | `SpanTiming.StatsAggregatePerSite` (scrambled order, exact min/max/total); mutant M3 | Pass |
| AC-3 | span line follows §2.2 and parses; 020-05 lines unchanged | `SpanJson.LineMatchesSchema` (exact prefix and key order), `check_trace_stream.py` (`json.loads`, exact `span` key set, 020-05 checks unchanged and passing), `EventStream.*`/`JsonLines.*` unchanged and passing; mutant M6 | Pass |
| AC-4 | 4 threads × 10,000 spans → count 40,000, TSan clean | `SpanTiming.ConcurrentSpansAggregate` on `linux-x64-tsan` (R6, R9) | Pass |
| AC-5 | `ATUGCC_TRACE_FLUSH_MS=100` faster than flush per line, same line count | `span_cost_probe` Release R11, R12; env path: `check_trace_stream.py` `FLUSH_MS=100` run (same line count) and invalid-value warning; `SpanJson.FlushIntervalHoldsLinesBack`; mutants M4, M5 | Pass |
| AC-6 | per-span cost (no sink / JSON + 100 ms) measured in Release and written in `lessons/README.md` | "Cost measurements" above; [lessons/README.md](/lessons/README.md) "성능 측정 레슨 작성" | Pass |
| AC-7 | `/W4 /WX`, Linux `-Werror`, ASan/UBSan pass | R8, R9 (all presets set `ATUGCC_WARNINGS_AS_ERRORS=ON`) | Pass |
| AC-8 | Linux: 20 ms sleep wall ≥ 20 ms, cpu < 5 ms; `ATUGCC_SPAN_METER=cpu` → `meter:"cpu"`; `recordSpan(…,"perf")` separate row; cost incl. virtual meter call | `SpanMeter.SleepWallVersusCpu` (Linux), `SpanMeter.CpuMeterScaleMatchesBusyTime`, `check_trace_stream.py` cpu run, `SpanMeter.RecordSpanMeterIsSeparateRow`; costs above | Pass |
| AC-9 | switching the meter mid-span keeps the start meter; TSan clean | `SpanMeter.SwitchDuringSpanKeepsStartMeter`, `SpanMeter.ConcurrentSwitchingKeepsEachSpanOnOneMeter` on `linux-x64-tsan`; mutant M1 | Pass |

## Reviews

| Unit | Reviewer | Question | Findings | Resolution |
|---|---|---|---|---|
| U1–U3 | codex luna (high) | match plan D1–D3 / spec §2, §4; races, lifetime, ODR, platform, behaviour | empty / non-ASCII `ATUGCC_TRACE_FLUSH_MS` silently 0 | fixed (Revision 1), `lead (fallback)` |
| U4–U6 | `cpp-reviewer` | does each test check its AC; can any pass trivially; flakes; warnings | 11 (monotonic samples, no-op row check, cpu scale, flush hold-back, mean column, throwing sink, copy/move, 3 ms order flake, both meters used, unchecked `open()`, stderr unchecked) | all fixed (Revision 1) |
| U7 | `cpp-reviewer` | does each document cover spec §8 and match the code and the measured numbers | 7 statements saying more or less than the code (see Revision 2) | all fixed |
