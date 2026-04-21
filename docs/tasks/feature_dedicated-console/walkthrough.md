# Walkthrough: Dedicated Console Output Control

## Summary
Implemented an opt-in dedicated console output path for `atugcc::pattern::viz::Tracer`.

The tracer continues to record events exactly as before, while applications can now:
- attach an output sink,
- enable or disable live terminal emission at runtime,
- keep snapshot/diagram formatting unchanged.

## Design
- Added `TraceOutputSink` as the output abstraction.
- Added `ConsoleTraceSink` as the standard stream-backed sink implementation.
- Added `Tracer::setOutputSink()` and `Tracer::setLiveTerminalOutputEnabled()`.
- Kept `record_message()`, `record_transition()`, `push_node()`, `format_terminal()`, and diagram APIs backward compatible.
- Emitted live output after releasing the tracer write lock.

## Changed Files
- `/include/atugcc/pattern/visualizer.hpp`
  - Output sink abstraction and live output control.
- `/include/atugcc/pattern/detail/terminal_formatter.hpp`
  - Compact live event line formatting helpers.
- `/src/pattern/example_visualizer.cpp`
  - Dedicated console sink on/off demonstration.
- `/tests/pattern/test_visualizer.cpp`
  - Sink configuration and concurrency coverage.

## Verification Highlights
- Build passed with `linux-x64-relwithdebinfo` preset.
- Test suite passed.
- Manual example run confirmed:
  - Demo 1: live sink ON
  - Demo 2: live sink OFF while formatted snapshots remain visible
  - Demo 3: live sink ON

## Notes
- This task controls output emission only. Trace recording remains active for state/observer integrations.
- OS-specific new console window allocation remains out of scope for this task.