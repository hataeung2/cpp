# Walkthrough: 020-06 Tracer 구간 시간 측정 (span)

- Spec: [/docs/specs/020_06_tracer_span_timing.md](/docs/specs/020_06_tracer_span_timing.md)
- Evidence: [testrecord.md](/docs/tasks/feature_020-06-tracer-span-timing/testrecord.md) (AC-1–AC-9 all Pass)
- Branch: `feature/020-06-tracer-span-timing`, merged into `main` by fast-forward

## Result
- `auto span = tracer.timeScope("parse");` (or `ScopedSpan`) times a code range and records it when the scope ends or at `stop()` (once). `recordSpan(label, duration, loc, meter)` takes values measured another way into the same record.
- Meters behind `SpanMeter`: `wall` (steady_clock, default) and `cpu` (thread CPU time: `clock_gettime(CLOCK_THREAD_CPUTIME_ID)` / `GetThreadTimes`). `setSpanMeter()` or `ATUGCC_SPAN_METER`; the meter is an `std::atomic<std::shared_ptr>` read without the Tracer lock, and a span ends with the meter it started with.
- Spans are not stored: the Tracer keeps per-(file, line, label, meter) aggregates (`spanStats()`, `formatTimings()` table) and hands each span to the sinks: a live `⏱` line on the text sink, a `span` line on the JSON Lines stream (spec §2.2).
- `JsonLinesEventSink` gets a flush interval (`open(path, interval)`, `ATUGCC_TRACE_FLUSH_MS`); 0 keeps 020-05's flush per line.
- Code: [visualizer.hpp](/include/atugcc/pattern/visualizer.hpp) (declarations, `recordSpan`), [span_timing.hpp](/include/atugcc/pattern/detail/span_timing.hpp) (meters, `ScopedSpan`, stats, table, JSON), [event_stream.hpp](/include/atugcc/pattern/detail/event_stream.hpp) (flush interval, environment parsing, lifetime assert).
- Tests: 22 GoogleTest cases (the death test runs on Linux Debug only) in [test_span_timing.cpp](/tests/pattern/test_span_timing.cpp); `TraceStream` now also checks span lines, the cpu meter, an unknown meter and the flush variable (incl. stderr warnings); ctest `SpanCost` runs [span_cost_probe.cpp](/tests/pattern/span_cost_probe.cpp). Six mutants, all killed.
- Verified on MSVC `/W4 /WX` (Debug, Release), GCC `-Werror` (Debug, Release), ASan+UBSan, TSan.
- Release cost per span: 150–280 ns (wall, no sink), 2.4–4.1 µs with the JSON stream and a 100 ms flush interval; table in [lessons/README.md](/lessons/README.md).

## Notes
- Interpretations recorded in plan.md: `threadId` is a small per-thread ordinal (JSON consumers lose precision above 2^53); `recordSpan` rejects negative durations; `clear()` also clears span aggregates.
- AC-5's "faster" is decided by the Release runs. At -O0 JSON formatting dominates and the gap is noise, so the Debug/sanitizer ctest checks line counts only.
- `naming_check.py` `ALLOWED` gained three std names used by the tests (`adjacent_find`, `fetch_add`, `find_first_not_of`).

## Follow-ups
- KI-016: with a flush interval, the tail of a burst can stay buffered while the program is quiet (070-06).
- KI-011: `⏱` and `µs` in span output on non-UTF-8 Windows consoles (note added).
- KI-001: `docs/cpp_evolution/source_location.md` still missing (unchanged).
- `lead (fallback)`: U3's review finding (`ATUGCC_TRACE_FLUSH_MS` diagnostics) was fixed by the lead instead of a second agy round.
