# Plan: 020-06 Tracer 구간 시간 측정 (span)

- Spec: [/docs/specs/020_06_tracer_span_timing.md](/docs/specs/020_06_tracer_span_timing.md) (approved 2026-10-29)
- Branch: `feature/020-06-tracer-span-timing` (from `main` at `cf6abb9`)

## Design (fixed by the lead; units implement exactly this)

Interpretations of the spec, decided here:
- `Span::threadId` is a small process-wide ordinal (1, 2, 3, … in order of a thread's first span), not a raw `std::hash` of the thread id. Spec §2.2 shows `"thread":3`, and a 64-bit hash loses precision in the JavaScript consumer (070-06; `Number` is exact only up to 2^53). It is still "derived from `std::this_thread::get_id()`" in the sense the spec needs: one value per thread.
- `recordSpan` gets `[[nodiscard]]` like the other `record*` functions. It fails with `CoreError::InvalidArgument` for a negative duration (spans are never stored, so there is no capacity failure).
- `Tracer::clear()` also clears the span aggregates.
- Spec §2.5 "resolution next to the meter name": the console table shows `cpu (~15.6 ms tick)` for the `cpu` meter on Windows; every other meter shows its name only (wall and Linux cpu are ns-resolution).
- `⏱` stays as the live-line prefix; the `[t]` fallback stays with KI-011 (note added there).

### D1. `include/atugcc/pattern/visualizer.hpp` (declarations and Tracer integration)
- Includes: add `<map>`, `<thread>`.
- Constants next to `kTraceOutEnv`: `kSpanMeterEnv = "ATUGCC_SPAN_METER"`, `kTraceFlushEnv = "ATUGCC_TRACE_FLUSH_MS"`.
- After `struct Node`:
  - `class SpanMeter` exactly as spec §2.1 (pure virtual `name()`, `nowNs()`, both `const noexcept`, `[[nodiscard]]`).
  - `class WallSpanMeter final : public SpanMeter` and `class ThreadCpuSpanMeter final : public SpanMeter`: `name()` defined in class (`"wall"`, `"cpu"`); `nowNs()` declared `override`, defined in D2.
  - `[[nodiscard]] inline std::shared_ptr<SpanMeter> makeSpanMeter(std::string_view name);` (defined in D2).
  - `struct Span` and `struct SpanStats` exactly as spec §2.1 field order (`SpanStats` fields one per line; all integers value-initialized `{ 0 }`).
- `detail::LiveTerminalFormatter` gains `[[nodiscard]] static std::string formatSpan(const Span& span);` (defined in D2).
- `TraceEventSink` gains `virtual void onEvent(const Span& /*event*/) {}` (non-pure, after the three pure ones).
- Declaration `[[nodiscard]] inline std::string toJsonLine(const Span& event);` with the others.
- `JsonLinesEventSink`:
  - `open(const std::filesystem::path& path, std::chrono::milliseconds flushInterval = std::chrono::milliseconds{ 0 })`.
  - `~JsonLinesEventSink() override;` (flushes), `void onEvent(const Span& event) override;`.
  - constructor takes `(std::ofstream stream, std::chrono::milliseconds flushInterval)`; members `std::chrono::milliseconds flush_interval_;` and `std::chrono::steady_clock::time_point last_flush_;` after `stream_`.
- `namespace detail` declarations (defined in D2): `[[nodiscard]] inline std::shared_ptr<SpanMeter> defaultSpanMeter();` (one process-wide `WallSpanMeter`), `[[nodiscard]] inline std::shared_ptr<SpanMeter> environmentSpanMeter();` (`ATUGCC_SPAN_METER` read once), `[[nodiscard]] inline std::uint64_t currentThreadOrdinal() noexcept;`.
- `namespace detail` span aggregate types (defined in visualizer.hpp, before `Tracer`, they are data only):
  ```text
  struct SpanKey     { std::string file; std::uint32_t line; std::string label; std::string meter; };
  struct SpanKeyView { std::string_view file; std::uint32_t line; std::string_view label; std::string_view meter; };
  struct SpanKeyLess { using is_transparent = void; operator() for every pair of (SpanKey, SpanKeyView), comparing std::tie(file, line, label, meter) as string_views };
  struct SpanAggregate { std::uint64_t count{0}, totalNs{0}, minNs{0}, maxNs{0}; };
  ```
  The transparent comparator lets `recordSpan` look up an existing key without allocating.
- `class ScopedSpan` is defined **before** `Tracer`, after a forward declaration `class Tracer;`:
  - spec §2.1 interface; copy constructor and copy assignment `= delete` (no move: none declared).
  - members: `Tracer* tracer_; std::string label_; std::source_location location_; std::shared_ptr<SpanMeter> meter_; std::uint64_t start_ns_{ 0 }; bool active_{ true };`
  - bodies in D2.
- `Tracer`:
  - members after `event_sink_`: `std::atomic<std::shared_ptr<SpanMeter>> span_meter_;`, `std::map<detail::SpanKey, detail::SpanAggregate, detail::SpanKeyLess> span_stats_;`, `std::atomic<std::size_t> live_spans_{ 0 };`. `friend class ScopedSpan;`.
  - constructor: `span_meter_(detail::environmentSpanMeter())` in the init list after `event_sink_`.
  - `setSpanMeter(meter)`: `span_meter_.store(meter ? std::move(meter) : detail::defaultSpanMeter());` (no Tracer lock). `spanMeter() const`: `return span_meter_.load();`.
  - `timeScope(label, loc)` declared here, defined in D2 (`return ScopedSpan(*this, label, loc);`).
  - `recordSpan(label, duration, loc, meter)` defined in class like the other record functions: `duration < 0` → `std::unexpected(core::CoreError::InvalidArgument)`. Build `Span{ label, meter, durationNs, detail::currentThreadOrdinal(), EventMeta{ .location = loc } }`. Under `unique_lock`: `seq`, `tracerId`; find `SpanKeyView{ loc.file_name(), loc.line(), label, meter }` in `span_stats_`, insert `SpanKey` if missing (count 0); update count, total, min (first sample sets it), max; copy `event_sink_`, `output_sink_`, live flag. After the lock: live → `sink->emit(detail::LiveTerminalFormatter::formatSpan(span))`; then `event_sink->onEvent(span)`.
  - `spanStats() const` (shared lock) and `formatTimings() const` declared, defined in D2.
  - `clear()` also clears `span_stats_`.
- Header comment and tail include: `#include "atugcc/pattern/detail/span_timing.hpp"` after `event_stream.hpp`.

### D2. `include/atugcc/pattern/detail/span_timing.hpp` (new)
Namespace `atugcc::pattern::viz` (helpers in `::detail`). Everything `inline`. Same "do not include directly" banner as the other detail headers.
- `WallSpanMeter::nowNs()`: `steady_clock::now().time_since_epoch()` in ns.
- `ThreadCpuSpanMeter::nowNs()`: the file's only `#ifdef _WIN32` block. Windows `GetThreadTimes(GetCurrentThread(), …)`: (kernel + user) as 64-bit from `FILETIME` halves × 100; failure → 0. POSIX `clock_gettime(CLOCK_THREAD_CPUTIME_ID, &ts)` (`<time.h>`): `tv_sec * 1'000'000'000 + tv_nsec`; failure → 0.
- `makeSpanMeter(name)`: `"wall"` → `defaultSpanMeter()`; `"cpu"` → one process-wide `ThreadCpuSpanMeter` (function-local static `shared_ptr`); else `nullptr`.
- `detail::environmentSpanMeter()`: function-local static initialized once: read `kSpanMeterEnv` with `detail::readEnvironmentAscii` (D3); unset → `defaultSpanMeter()`; unknown name → one `stderr` line `atugcc: unknown ATUGCC_SPAN_METER '<v>', using wall` and `defaultSpanMeter()`.
- `detail::currentThreadOrdinal()`: function-local `static std::atomic<std::uint64_t>` counter, `thread_local const std::uint64_t ordinal = counter.fetch_add(1, relaxed) + 1;`.
- `detail::formatDuration(std::uint64_t ns)`: `< 1'000` → `"{} ns"`; `< 1'000'000` → `"{:.3f} µs"`; `< 1'000'000'000` → `"{:.3f} ms"`; else `"{:.3f} s"` (double division).
- `detail::baseName(std::string_view path)`: text after the last `/` or `\`.
- `LiveTerminalFormatter::formatSpan`: `"⏱ {label}  {formatDuration}  ({baseName(file)}:{line})\n"` (spec §2.3; no ANSI colours, it is read in logs too).
- `toJsonLine(const Span&)`: `{"v":1,"kind":"span","seq":S,"tracer":T,"label":"…","meter":"…","durNs":N,"thread":N` + `appendMeta` + `}` (spec §2.2 field order).
- `ScopedSpan(tracer, label, loc)`: `tracer_(&tracer)`, `label_(label)`, `location_(loc)`, `meter_(tracer.spanMeter())`; then `tracer.live_spans_.fetch_add(1, relaxed)`; **last** `start_ns_ = meter_->nowNs()` (setup cost is outside the span).
- `stop() noexcept`: `if (!active_) return; const auto end = meter_->nowNs(); active_ = false;` then in `try`: `(void)tracer_->recordSpan(label_, nanoseconds(end >= start_ns_ ? end - start_ns_ : 0), location_, meter_->name());` `catch (const std::exception&)` / `catch (...)` each print one `stderr` line (impl.md §4). Finally `tracer_->live_spans_.fetch_sub(1, release)`.
- `~ScopedSpan()`: `stop();`.
- `Tracer::timeScope`: `return ScopedSpan(*this, label, loc);`.
- `Tracer::spanStats()`: shared lock; build `SpanStats` from each map entry; sort by `totalNs` descending, ties by (file, line, label, meter) ascending.
- `Tracer::formatTimings()`: from `spanStats()`. Empty → `"(no spans)\n"`. Otherwise a table with columns `label | meter | location | count | total | mean | min | max`; location = `baseName(file):line`; mean = total / count; durations via `formatDuration`; meter via `detail::meterDisplayName(meter)` (`cpu` on Windows → `cpu (~15.6 ms tick)`, else the name). Column widths from the widest cell in display columns (UTF-8 code points: bytes that are not `10xxxxxx`); text columns left-aligned, numbers right-aligned; two spaces between columns; a header line and a dashed rule.

### D3. `include/atugcc/pattern/detail/event_stream.hpp`
- `detail::readEnvironmentAscii(std::string_view name) -> std::optional<std::string>`: from `readEnvironmentPath(name)`; copy `native()` character by character; any character above 0x7F → `std::nullopt` (no throwing conversion).
- `detail::environmentFlushInterval() -> std::chrono::milliseconds`: `kTraceFlushEnv` parsed with `std::from_chars` into `std::uint32_t`, whole string consumed; unset → 0; invalid → one `stderr` line and 0.
- `JsonLinesEventSink`: constructor stores the interval and `last_flush_ = steady_clock::now()`; `open(path, flushInterval)` passes it on. `writeLine`: write line + `'\n'`; if `flush_interval_ == 0ms` flush; else `now = steady_clock::now()`, flush and set `last_flush_ = now` when `now - last_flush_ >= flush_interval_`. `~JsonLinesEventSink()`: lock, flush if open. `onEvent(const Span&)` → `writeLine(toJsonLine(event))`.
- `environmentEventSink()`: `JsonLinesEventSink::open(*path, detail::environmentFlushInterval())`.
- `Tracer::~Tracer()`: first line `assert(live_spans_.load(std::memory_order_acquire) == 0 && "ScopedSpan outlived its Tracer");` (`<cassert>`).
- `static_assert` adds `EventSink<JsonLinesEventSink, Span>`.

### D4. Tests
`tests/pattern/test_span_timing.cpp` (added to `TEST_SOURCES`):
- `SpanTiming.SleepIsMeasuredOnce` (AC-1): wall meter set explicitly; counting sink; `ScopedSpan` around `sleep_for(20ms)`, `stop()`, then scope ends → sink got 1 span, 20 ms ≤ `durationNs` < 200 ms, `spanStats` count 1.
- `SpanTiming.StopTwiceRecordsOnce`, `SpanTiming.SpanEndedByExceptionIsRecorded`, `SpanTiming.TimeScopeUsesStartLine` (`meta.location.line()` = line of the `timeScope` call).
- `SpanTiming.StatsAggregatePerSite` (AC-2): 1000 `recordSpan` with known durations at one site → count 1000, total = sum, min/max exact, min ≤ mean ≤ max; a second label at the same line is a separate row; order total descending.
- `SpanTiming.NegativeDurationRejected`, `SpanTiming.ClearResetsStats`.
- `SpanTiming.ConcurrentSpansAggregate` (AC-4): 4 threads × 10,000 spans released by `std::latch` → count 40,000; TSan preset.
- `SpanMeter.FactoryNames`, `SpanMeter.SleepWallVersusCpu` (AC-8: wall ≥ 20 ms, cpu < 5 ms), `SpanMeter.RecordSpanMeterIsSeparateRow` (AC-8: `"perf"` row separate from `"wall"`), `SpanMeter.SwitchDuringSpanKeepsStartMeter` (AC-9: a counting fake meter A, switch to B mid-span → span's `meter == A`, A read twice, B never; plus a thread that keeps switching meters while others time spans, TSan).
- `SpanJson.LineMatchesSchema` (AC-3): exact prefix and key order; `SpanJson.SinkWritesSpanLines` (file sink, flush interval 100 ms → after sink destruction the file has all lines).
- `SpanFormat.LiveLineAndTimingsTable` (§2.3): live line text; table has a row per stats entry with units.
- `SpanLifetime.SpanOutlivingTracerAsserts` (§4): Linux Debug, no sanitizer: `EXPECT_DEATH`.

`tests/pattern/trace_stream_probe.cpp` + `check_trace_stream.py` (AC-3, AC-8): the probe adds two `timeScope` spans and one `recordSpan(…, "perf")` on the first Tracer and reports `"spans":N`; the script validates `span` keys (exact set), runs once more with `ATUGCC_SPAN_METER=cpu` (scoped spans `meter == "cpu"`, the perf one `"perf"`) and once with `ATUGCC_TRACE_FLUSH_MS=100` (same line count as the default run). Existing event checks are unchanged.

`tests/pattern/span_cost_probe.cpp` (AC-5, AC-6, AC-8 cost): prints ns per span for (wall, no sink), (cpu, no sink), (wall, JSON sink flush 100 ms), (wall, JSON sink flush 0); AC-5: 100,000 spans into a file with flush 0 and with 100 ms, min of 3 runs each; exit 1 unless line counts are equal and 100 ms is faster. ctest `SpanCost` (TIMEOUT 300).

### D5. Docs (spec §8)
`visualizer.hpp` header comment (span usage, lifetime warning); `lessons/README.md` "성능 측정 레슨 작성" (usage, costs from AC-6, measure the outer range of hot loops); `README.md` Features line; KI-011 note about `⏱`; new KI: lines written within the flush interval after the last flush stay buffered until the next write or exit (070-06 liveness).

## C++20/23 features
`std::source_location` default argument (existing), `std::atomic<std::shared_ptr>` (C++20), transparent comparator for heterogeneous `std::map::find`, `thread_local` ordinal, guaranteed copy elision for a non-movable return (`timeScope`), `std::format` with precision. No new `docs/cpp_evolution` page: `source_location.md` stays with KI-001 (Phase 5).

## Units
| Unit | File | Change (what, where, AC) | Check | Risky | Author | Reviewer | Tokens (in / out) | Status |
|---|---|---|---|---|---|---|---|---|
| U1 | `include/atugcc/pattern/visualizer.hpp` | D1 | with U2, U3: `windows-x64-debug` and `linux-x64-debug` build `atugcc_tests`; existing suite passes; `naming_check` | yes (public header, atomics, lifetime) | agy flash (one call with U2, U3) | codex luna (high): 1 finding (U3) | 353k / 77k (with U2, U3); review 319k / 5k | done |
| U2 | `include/atugcc/pattern/detail/span_timing.hpp` (new) | D2 | with U1 | yes (platform branch, thread_local, lifetime) | agy flash (with U1) | codex luna (high): none | (see U1) | done |
| U3 | `include/atugcc/pattern/detail/event_stream.hpp` | D3 | with U1 | yes (lock, destructor) | agy flash (with U1); finding fixed by lead (fallback) | codex luna (high): empty / non-ASCII `ATUGCC_TRACE_FLUSH_MS` silently 0 → fixed | (see U1) | done |
| U4 | `tests/pattern/test_span_timing.cpp` (new), `tests/CMakeLists.txt` | D4 GoogleTest | `--gtest-filter "Span*"` both presets; ASan; TSan | no (test) | lead | `cpp-reviewer`: 11 findings → fixed (testrecord Revision 1) | 81k (reviewer) | done |
| U5 | `tests/pattern/trace_stream_probe.cpp`, `tests/pattern/check_trace_stream.py` | D4 probe + script | `ctest -R TraceStream` both presets | no (test) | lead | `cpp-reviewer` (same call as U4): stderr warnings unchecked → fixed | — | done |
| U6 | `tests/pattern/span_cost_probe.cpp` (new), `tests/CMakeLists.txt` | D4 cost probe | `ctest -R SpanCost`; Release runs | no (test) | lead | `cpp-reviewer` (same call as U4): unchecked `open()` → fixed | — | done |
| U7 | `visualizer.hpp` comment, `lessons/README.md`, `README.md`, `docs/known_issues.md` | D5 | `lint_docs.py` | no (doc) | lead | `cpp-reviewer`: 7 findings → fixed (testrecord Revision 2) | 51k (reviewer) | done |

Deviation recorded after the Debug runs: the AC-5 "interval is faster" check in `span_cost_probe` is enforced only in optimized builds (`NDEBUG`). At -O0 one span line costs about 20–30 µs of JSON formatting, so a flush per line adds only 3–15 % and the comparison is noise (Linux Debug: 1696 vs 1640 ms; Windows Debug: 2913 vs 2462 ms). The ctest `SpanCost` checks line counts everywhere; the AC-5 evidence is the Release run on each platform.
