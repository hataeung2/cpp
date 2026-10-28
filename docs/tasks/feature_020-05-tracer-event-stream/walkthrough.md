# Walkthrough: 020-05 Tracer 이벤트 스트림 (JSON Lines)

- Spec: [/docs/specs/020_05_tracer_event_stream.md](/docs/specs/020_05_tracer_event_stream.md)
- Evidence: [testrecord.md](/docs/tasks/feature_020-05-tracer-event-stream/testrecord.md) (AC-1–AC-7 all Pass)
- Branch: `feature/020-05-tracer-event-stream`, merged into `main` by fast-forward

## Result
- `Tracer` events carry a process-wide `seq` and the `tracerId`; both are assigned under the record lock after the capacity check, so a rejected event consumes no seq and reaches no sink.
- New event-sink path beside the text sink: `TraceEventSink` (interface), `JsonLinesEventSink` (one JSON line per event, flushed per line, whole lines under concurrent writers), `toJsonLine(...)` for the v1 schema (spec §2.2).
- `ATUGCC_TRACE_OUT=<file>` connects every Tracer to one process-wide sink without code changes; stdout is unchanged with or without it, and an unopenable path is ignored. `~Tracer()` writes the Mermaid `diagramParts()` as `diagram` lines.
- Code: [visualizer.hpp](/include/atugcc/pattern/visualizer.hpp) (declarations, Tracer integration), [event_stream.hpp](/include/atugcc/pattern/detail/event_stream.hpp) (definitions, Windows `_wdupenv_s` branch).
- Tests: 13 GoogleTest cases in [test_event_stream.cpp](/tests/pattern/test_event_stream.cpp); ctest `TraceStream` runs [trace_stream_probe.cpp](/tests/pattern/trace_stream_probe.cpp) three times and checks the stream with [check_trace_stream.py](/tests/pattern/check_trace_stream.py) (expected labels fixed in the script; a wrong-escape mutant fails it).
- Verified on MSVC `/W4 /WX`, GCC `-Werror`, ASan+UBSan, TSan.

## Notes
- The first-pass review of the tests found a circular check (expected labels built with the function under test). Fixed once, proven with a mutant (testrecord Revision 1).
- AC-4/AC-5 name the example; the automated check uses a probe that reports its exact expected counts, and the example runs are recorded as R12 and R16.

## Follow-ups
- KI-012: `build.py --gtest-filter` on the TSan preset exits 66 without output (no `setarch` launcher).
- KI-001: `docs/cpp_evolution/source_location.md` still missing (unchanged by this task, spec §6).
- No `lead (fallback)` units.
