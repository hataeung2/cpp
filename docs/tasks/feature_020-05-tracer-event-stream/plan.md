# Plan: 020-05 Tracer 이벤트 스트림 (JSON Lines)

- Spec: [/docs/specs/020_05_tracer_event_stream.md](/docs/specs/020_05_tracer_event_stream.md) (approved 2026-10-28)
- Branch: `feature/020-05-tracer-event-stream` (from `main` at `c528d3b`)
- AC-1 baseline: `atugcc_pattern_example` stdout on `linux-x64-debug` captured before any change (173 lines; the log-path line holds pid and time and is normalized before comparison)

## Design (fixed by the lead; units implement exactly this)

### D1. `include/atugcc/pattern/visualizer.hpp`
- Includes: add `<cstdint>`, `<filesystem>`, `<fstream>`, `<optional>`.
- `EventMeta` gains two fields after `timestamp`: `std::uint64_t seq{ 0 };` and `std::uint32_t tracerId{ 0 };`. Existing designated initializers (`EventMeta{ .location = loc }`) keep compiling.
- After the `EventSink` concept, before `TraceOutputSink`:
  ```cpp
  inline constexpr std::string_view kTraceOutEnv = "ATUGCC_TRACE_OUT";

  class TraceEventSink {
  public:
      virtual ~TraceEventSink() = default;
      virtual void onEvent(const Message& event) = 0;
      virtual void onEvent(const Transition& event) = 0;
      virtual void onEvent(const Node& event) = 0;
      virtual void onDiagramParts(std::uint32_t tracerId, const std::vector<DiagramPart>& parts) = 0;
  };

  [[nodiscard]] inline std::string toJsonLine(const Message& event);
  [[nodiscard]] inline std::string toJsonLine(const Transition& event);
  [[nodiscard]] inline std::string toJsonLine(const Node& event);
  // part = 0-based index within parts of the same DiagramKind, parts = count of that kind
  [[nodiscard]] inline std::string toJsonLine(std::uint32_t tracerId, std::size_t part, std::size_t parts, const DiagramPart& diagram);

  class JsonLinesEventSink final : public TraceEventSink {
  public:
      [[nodiscard]] static std::shared_ptr<JsonLinesEventSink> open(const std::filesystem::path& path); // nullptr on failure
      void onEvent(const Message& event) override;      // writeLine(toJsonLine(event))
      void onEvent(const Transition& event) override;
      void onEvent(const Node& event) override;
      void onDiagramParts(std::uint32_t tracerId, const std::vector<DiagramPart>& parts) override;
  private:
      explicit JsonLinesEventSink(std::ofstream stream) noexcept;
      void writeLine(std::string_view line);            // lock; write line + '\n'; flush
      std::mutex    mutex_;
      std::ofstream stream_;
  };

  // ATUGCC_TRACE_OUT set and openable -> one process-wide sink; otherwise nullptr. Opened once.
  [[nodiscard]] inline std::shared_ptr<TraceEventSink> environmentEventSink();

  namespace detail {
  [[nodiscard]] inline std::uint64_t nextEventSeq() noexcept;    // 1, 2, 3, ... process-wide
  [[nodiscard]] inline std::uint32_t nextTracerId() noexcept;    // 1, 2, 3, ... process-wide
  }
  ```
  Member function bodies of `JsonLinesEventSink` live in D2, not in the class.
- `Tracer`:
  - members: `std::uint32_t id_;` declared right after `capacity_`; `std::shared_ptr<TraceEventSink> event_sink_;` right after `output_sink_`.
  - constructor: `: capacity_(capacity), id_(detail::nextTracerId()), event_sink_(environmentEventSink())`.
  - `~Tracer();` declared (defined in D2). Copy constructor and copy assignment `= delete` (explicit; the mutex already prevents them).
  - `void setEventSink(std::shared_ptr<TraceEventSink> sink)` (unique_lock), `[[nodiscard]] std::shared_ptr<TraceEventSink> eventSink() const` (shared_lock), `[[nodiscard]] std::uint32_t id() const noexcept`.
  - `recordMessage` / `recordTransition` / `pushNode`: inside the existing unique_lock and **after** the capacity check, set `event.meta.seq = detail::nextEventSeq(); event.meta.tracerId = id_;`, then push and copy `event_sink_` into a local. After the lock, the existing text-sink call stays as is, then `if (event_sink) { event_sink->onEvent(event); }`. A rejected event (capacity) consumes no seq and reaches no sink.
- Header comment "학습 포인트": add `[7] 이벤트 스트림 — TraceEventSink / JsonLinesEventSink, ATUGCC_TRACE_OUT` (doc unit U5 covers wording).
- Tail include: add `#include "atugcc/pattern/detail/event_stream.hpp"` **after** `diagram_parts.hpp` (the destructor calls `diagramParts`).

### D2. `include/atugcc/pattern/detail/event_stream.hpp` (new)
Namespace `atugcc::pattern::viz` (helpers in `::detail`). Everything `inline`.
- `detail::nextEventSeq()`: function-local `static std::atomic<std::uint64_t> counter{0}; return counter.fetch_add(1, std::memory_order_relaxed) + 1;` (uniqueness comes from the atomic; per-Tracer order comes from the Tracer lock). `detail::nextTracerId()` the same with `std::uint32_t`.
- `detail::jsonEscape(std::string_view) -> std::string`: `"`→`\"`, `\`→`\\`, `\b \f \n \r \t` as those escapes, any other byte `< 0x20` → `\u00XX` (lowercase hex, 4 digits); every other byte copied unchanged (UTF-8 passes through).
- `detail::kindName(DiagramKind)` → `"sequence" | "state" | "structure"`; `detail::backendName(DiagramBackend)` → `"plantuml" | "mermaid" | "d2"`.
- `detail::appendMeta(std::string& out, const EventMeta& meta)` appends `,"file":"…","line":N,"func":"…","tUs":N` where `tUs` = `duration_cast<microseconds>(meta.timestamp.time_since_epoch()).count()`.
- Line formats (field order fixed, no spaces):
  - `{"v":1,"kind":"message","seq":S,"tracer":T,"from":"…","to":"…","action":"…"` + meta + `}`
  - `{"v":1,"kind":"transition","seq":S,"tracer":T,"old":"…","new":"…","trigger":"…"` + meta + `}`
  - `{"v":1,"kind":"node","seq":S,"tracer":T,"parent":"…","child":"…","relation":"…"` + meta + `}`
  - `{"v":1,"kind":"diagram","tracer":T,"part":K,"parts":N,"diagram":"…","backend":"…","title":"…","overBudget":true|false,"source":"…"}`
- `JsonLinesEventSink::open`: `std::ofstream s(path, std::ios::binary | std::ios::trunc)`; `!s.is_open()` → `nullptr`; else `std::shared_ptr<JsonLinesEventSink>(new JsonLinesEventSink(std::move(s)))`.
- `onDiagramParts`: count parts per `DiagramKind`, then write one line per part in the given order with its per-kind index and count. Empty vector writes nothing.
- `detail::readEnvironmentPath(std::string_view asciiName) -> std::optional<std::filesystem::path>`: Windows `_wdupenv_s` (name widened byte by byte; `free` the buffer), elsewhere `std::getenv`. Unset or empty → `std::nullopt`. This is the only `#ifdef _WIN32` block in the file.
- `environmentEventSink()`: `static const std::shared_ptr<TraceEventSink> sink = []() -> std::shared_ptr<TraceEventSink> { … }(); return sink;` using `readEnvironmentPath(kTraceOutEnv)` and `JsonLinesEventSink::open`.
- `Tracer::~Tracer()`: if `event_sink_` is set, `event_sink_->onDiagramParts(id_, diagramParts(DiagramBackend::Mermaid));` inside `try`; `catch (const std::exception& e)` and `catch (...)` each print one line to `stderr` (`std::fprintf`), never rethrow (impl.md §4: not swallowed silently).
- `static_assert(EventSink<JsonLinesEventSink, Message> && EventSink<JsonLinesEventSink, Transition> && EventSink<JsonLinesEventSink, Node>);` — the existing concept documents the contract.

### D3. Tests
- `tests/pattern/test_event_stream.cpp` (GoogleTest, added to `TEST_SOURCES`):
  - `EventStream.SeqStrictlyIncreasesWithinTracer` (AC-3): mixed message/transition/node records; seqs in record order strictly increase; `tracerId == tracer.id()`.
  - `EventStream.SeqDisjointAcrossTracers` (AC-3): two tracers interleaved; seq sets disjoint; ids differ.
  - `EventStream.RejectedEventReachesNoSink` (spec §2.3): capacity 1, second record fails; a counting sink saw 1 event; next accepted event's seq is not skipped relative to the global counter's use by this tracer only (check: count only).
  - `EventStream.DestructorEmitsMermaidParts` (spec §2.1, Assumption 5): counting sink; expected parts = `diagramParts(Mermaid)` taken before destruction; sink got same count, tracerId, all `backend == Mermaid`.
  - `EventStream.NullSinkDisablesStreaming`: `setEventSink(nullptr)` → nothing received.
  - `JsonLines.MessageTransitionNodeFields` (AC-2): each line starts `{"v":1,"kind":"<kind>"`, contains every key of its schema, ends `}`.
  - `JsonLines.EscapesSpecialCharacters` (AC-2): label with `"`, `\`, `\n`, `\t`, `\x01`, `한글` → exact escaped text.
  - `JsonLines.DiagramLinesIndexPartsPerKind` (spec §2.2): sink on a temp file, parts [seq, seq, state] → lines carry `"part":0,"parts":2`, `"part":1,"parts":2`, `"part":0,"parts":1`.
  - `JsonLines.OpenFailsForMissingDirectory` (AC-5): returns nullptr.
  - `JsonLines.ConcurrentWritersProduceWholeLines` (AC-6): 4 threads, each its own Tracer sharing one file sink, 500 records each → 2000 lines, each starts `{` and ends `}`, seq values unique. Runs under `linux-x64-tsan`.
- `tests/pattern/trace_stream_probe.cpp` + `tests/pattern/check_trace_stream.py` (AC-1 analogue, AC-2 cross-check, AC-4, AC-5):
  - probe: two Tracers (A: messages with tricky labels, transitions, nodes; B: messages from 2 threads). Before they are destroyed it prints one JSON object to stdout: total recorded events, the tricky labels, and per tracer id the count of Mermaid parts per kind.
  - script (`check_trace_stream.py -- <command...>`): runs the command (1) without the variable, (2) with `ATUGCC_TRACE_OUT=<tmp file>`, (3) with the variable pointing into a missing directory. Asserts: exit 0 in all three; stdout identical in all three; every file line passes `json.loads`; event-line count = reported total; seq unique; tricky labels round-trip exactly; diagram-line counts per tracer and kind = reported; `file` ends with `trace_stream_probe.cpp` and `line > 0`.
  - `tests/CMakeLists.txt`: `add_executable(trace_stream_probe …)` linked to `atugcc_headers`; `find_package(Python3 COMPONENTS Interpreter)`; if found, `add_test(NAME TraceStream COMMAND ${Python3_EXECUTABLE} <script> -- ${_atugcc_test_launcher} $<TARGET_FILE:trace_stream_probe>)`.

### D4. Docs (spec §8)
Header comment of `visualizer.hpp`; `README.md` Features line; `src/pattern/example_visualizer.cpp` header comment (`ATUGCC_TRACE_OUT=/tmp/trace.jsonl ./bin/atugcc_pattern_example`).

## C++20/23 features
`std::source_location` (existing), `std::atomic` counters, function-local static initialization, concept `EventSink` used in a `static_assert`, `std::format` where convenient. No pre-C++20 pattern is replaced; `docs/cpp_evolution/source_location.md` stays with KI-001.

## Units
| Unit | File | Change (what, where, AC) | Check | Risky | Author | Reviewer | Tokens (in / out) | Status |
|---|---|---|---|---|---|---|---|---|
| U1 | `include/atugcc/pattern/visualizer.hpp` | D1 (declarations, Tracer integration, include of `event_stream.hpp`) | together with U2: both presets build `atugcc_tests`; existing suite passes unchanged | yes (public header, locks, ODR) | agy flash (one call with U2) | codex luna (high): none | 274k / 49k (with U2); review 167k / 3k | done |
| U2 | `include/atugcc/pattern/detail/event_stream.hpp` (new) | D2 | build with U1 on MSVC `/WX` and GCC `-Werror`; `naming_check` = 0 | yes (platform branch, static locals, destructor) | agy flash (with U1) | codex luna (high): none | (see U1) | done |
| U3 | `tests/pattern/test_event_stream.cpp` (new), `tests/CMakeLists.txt` | D3 GoogleTest cases (+ `ConcurrentRecordersOnOneTracer` after review) | `--gtest-filter "EventStream.*:JsonLines.*"` on both presets; TSan with `setarch` | no (test) | lead | `cpp-reviewer`: 3 findings → fixed (testrecord Revision 1) | — | done |
| U4 | `tests/pattern/trace_stream_probe.cpp`, `tests/pattern/check_trace_stream.py` (new), `tests/CMakeLists.txt` | D3 probe + script + ctest | `ctest -R TraceStream` on both presets; negative run; mutant R14 | no (test) | lead | `cpp-reviewer`: circular label check, silent Python skip → fixed | — | done |
| U5 | `visualizer.hpp` comment, `README.md`, `src/pattern/example_visualizer.cpp` comment | D4 | `lint_docs.py` | no (doc) | lead | `cpp-reviewer`: one wording finding → fixed | — | done |
