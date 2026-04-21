# Plan: Dedicated Console Output Control for Tracer

## Scope
Implement the 08_001 dedicated console feature for `atugcc::pattern::viz::Tracer` while preserving existing tracing, formatting, and diagram APIs. The new behavior is opt-in: no sink configured means existing runtime behavior remains unchanged.

## Files
- [MODIFY] `/include/atugcc/pattern/visualizer.hpp`
  - Add output sink interface and concrete console sink.
  - Add tracer APIs for sink registration and live terminal output toggle.
  - Ensure record paths emit outside the tracer write lock.
- [MODIFY] `/include/atugcc/pattern/detail/terminal_formatter.hpp`
  - Add compact per-event terminal formatting helpers for live emission.
- [MODIFY] `/src/pattern/example_visualizer.cpp`
  - Demonstrate dedicated console sink on/off usage without changing existing formatted output examples.
- [MODIFY] `/tests/pattern/test_visualizer.cpp`
  - Add unit tests for no-sink behavior, live output emission, and sink enabled/disabled semantics.
- [MODIFY] `/docs/tasks/agent_todo.md`
  - Mark the dedicated console item complete after verification and include branch name.
- [NEW] `/docs/tasks/feature_dedicated-console/walkthrough.md`
  - Summarize final design, changed files, and manual verification.
- [NEW] `/docs/tasks/feature_dedicated-console/testrecord.md`
  - Capture configure/build/test commands and results.

## C++20/23 Features Applied
- `std::shared_ptr` for output sink ownership across tracer copies/usages.
- `std::atomic_bool` for low-cost sink enabled toggle.
- `std::source_location` continues to flow through recorded events.
- `std::expected` existing result model preserved for record APIs.
- `std::scoped_lock` / `std::lock_guard` for sink stream synchronization.
- `std::format` reused for compact event-line rendering.

## Design Notes
- The dedicated console feature controls output emission only, not trace recording.
- `Tracer` remains the source of truth for stored events and formatted snapshots.
- Live console emission uses compact event lines instead of full `format_terminal()` snapshots to keep overhead low and avoid recursive locking.
- Sink writes are performed after releasing the tracer lock.
- The concrete console sink writes to a caller-provided `std::ostream`, allowing apps to use `std::clog`, `std::cerr`, or a custom stream.

## Verification Targets
- Existing tracer/formatter behavior remains unchanged when no sink is set.
- Live output emits lines only when both tracer live output and sink enabled state are true.
- Disabled sink suppresses writes without affecting stored trace data.
- Example builds and demonstrates toggle behavior.

## Evolution Note
This task replaces direct caller-managed ad-hoc console branching with an explicit sink-based output channel design. If retained long-term, add `/docs/cpp_evolution/trace_console_toggle.md` in a follow-up documentation task.