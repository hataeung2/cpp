/**
 * @file test_span_timing.cpp
 * @brief atugcc::pattern::viz -- span timing (ScopedSpan, recordSpan, SpanMeter, aggregates) tests
 *
 * Test groups:
 *   SpanTiming   -- span recording, stop()/destructor, aggregates, concurrency (spec 020-06 AC-1, AC-2, AC-4)
 *   SpanMeter    -- meter factory, wall vs cpu, recordSpan meter rows, switching meters (AC-8, AC-9)
 *   SpanJson     -- toJsonLine(Span) schema, JSON Lines sink with a flush interval (AC-3, Assumption 6)
 *   SpanFormat   -- live console line and formatTimings() table (§2.3)
 *   SpanLifetime -- a ScopedSpan that outlives its Tracer asserts in Debug (§4)
 *
 * ATUGCC_SPAN_METER and ATUGCC_TRACE_FLUSH_MS are read once per process, so they are covered by
 * check_trace_stream.py. Recording cost and the flush-interval timing (AC-5, AC-6) are measured
 * by span_cost_probe.
 */
#include <gtest/gtest.h>

#include <algorithm>
#include <atomic>
#include <chrono>
#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <format>
#include <fstream>
#include <latch>
#include <memory>
#include <mutex>
#include <source_location>
#include <sstream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <thread>
#include <type_traits>
#include <vector>

#include "atugcc/pattern/visualizer.hpp"

namespace viz = atugcc::pattern::viz;
using namespace std::chrono_literals;

namespace {

class SpanSink final : public viz::TraceEventSink {
public:
    void onEvent(const viz::Message&) override {}
    void onEvent(const viz::Transition&) override {}
    void onEvent(const viz::Node&) override {}
    void onEvent(const viz::Span& event) override {
        std::lock_guard lock(mutex_);
        spans_.push_back(event);
    }
    void onDiagramParts(std::uint32_t, const std::vector<viz::DiagramPart>&) override {}

    [[nodiscard]] std::vector<viz::Span> spans() const {
        std::lock_guard lock(mutex_);
        return spans_;
    }

private:
    mutable std::mutex     mutex_;
    std::vector<viz::Span> spans_;
};

// Ticks 1000 ns per read and counts the reads.
class FakeMeter final : public viz::SpanMeter {
public:
    explicit FakeMeter(std::string name) : name_(std::move(name)) {}
    [[nodiscard]] std::string_view name() const noexcept override { return name_; }
    [[nodiscard]] std::uint64_t nowNs() const noexcept override {
        return (reads_.fetch_add(1, std::memory_order_relaxed) + 1) * 1000;
    }
    [[nodiscard]] std::uint64_t reads() const noexcept { return reads_.load(); }

private:
    std::string                        name_;
    mutable std::atomic<std::uint64_t> reads_{ 0 };
};

struct TracerWithSink {
    TracerWithSink() {
        tracer.setEventSink(sink);
        tracer.setSpanMeter(viz::makeSpanMeter("wall"));
    }
    std::shared_ptr<SpanSink> sink = std::make_shared<SpanSink>();
    viz::Tracer               tracer;
};

std::filesystem::path tempTracePath(const char* tag) {
    const auto ticks = std::chrono::steady_clock::now().time_since_epoch().count();
    return std::filesystem::temp_directory_path() /
        ("atugcc_span_" + std::string(tag) + "_" + std::to_string(ticks) + ".jsonl");
}

std::vector<std::string> readLines(const std::filesystem::path& path) {
    std::ifstream in(path, std::ios::binary);
    std::vector<std::string> lines;
    for (std::string line; std::getline(in, line);) {
        lines.push_back(line);
    }
    return lines;
}

constexpr std::uint64_t kMs = 1'000'000;

} // namespace

// ============================================================================
// SpanTiming
// ============================================================================

TEST(SpanTiming, SleepIsMeasuredOnce) {
    TracerWithSink t;
    {
        viz::ScopedSpan span(t.tracer, "sleep");
        std::this_thread::sleep_for(20ms);
        span.stop();
        span.stop();
    }
    const auto spans = t.sink->spans();
    ASSERT_EQ(spans.size(), 1u);
    EXPECT_EQ(spans[0].label, "sleep");
    EXPECT_EQ(spans[0].meter, "wall");
    EXPECT_GE(spans[0].durationNs, 20 * kMs);
    EXPECT_LT(spans[0].durationNs, 200 * kMs);
    EXPECT_EQ(spans[0].meta.tracerId, t.tracer.id());
    EXPECT_GT(spans[0].meta.seq, 0u);

    const auto stats = t.tracer.spanStats();
    ASSERT_EQ(stats.size(), 1u);
    EXPECT_EQ(stats[0].count, 1u);
    EXPECT_EQ(stats[0].totalNs, spans[0].durationNs);
}

TEST(SpanTiming, DestructorRecordsWithoutStop) {
    TracerWithSink t;
    {
        auto span = t.tracer.timeScope("scope");
    }
    EXPECT_EQ(t.sink->spans().size(), 1u);
}

TEST(SpanTiming, SpanEndedByExceptionIsRecorded) {
    TracerWithSink t;
    EXPECT_THROW({
        auto span = t.tracer.timeScope("throws");
        throw std::runtime_error("boom");
    }, std::runtime_error);
    const auto spans = t.sink->spans();
    ASSERT_EQ(spans.size(), 1u);
    EXPECT_EQ(spans[0].label, "throws");
}

// Copying or moving a span would record it twice (spec §4).
static_assert(!std::is_copy_constructible_v<viz::ScopedSpan>);
static_assert(!std::is_move_constructible_v<viz::ScopedSpan>);
static_assert(!std::is_copy_assignable_v<viz::ScopedSpan>);
static_assert(!std::is_move_assignable_v<viz::ScopedSpan>);

TEST(SpanTiming, ThrowingSinkDoesNotEscapeStop) {
    class ThrowingSink final : public viz::TraceEventSink {
    public:
        void onEvent(const viz::Message&) override {}
        void onEvent(const viz::Transition&) override {}
        void onEvent(const viz::Node&) override {}
        void onEvent(const viz::Span&) override { throw std::runtime_error("sink failed"); }
        void onDiagramParts(std::uint32_t, const std::vector<viz::DiagramPart>&) override {}
    };
    viz::Tracer tracer;
    tracer.setEventSink(std::make_shared<ThrowingSink>());
    {
        auto span = tracer.timeScope("guarded");
        span.stop();                                  // noexcept: a throw here would terminate
    }
    {
        auto span = tracer.timeScope("guarded");    // destructor path
    }
    // The aggregate is updated before the sink is called.
    std::uint64_t counted = 0;
    for (const auto& row : tracer.spanStats()) {
        counted += row.count;
    }
    EXPECT_EQ(counted, 2u);
}

TEST(SpanTiming, TimeScopeUsesStartLine) {
    TracerWithSink t;
    const auto expected_line = std::source_location::current().line() + 1;
    auto span = t.tracer.timeScope("located");
    span.stop();
    const auto spans = t.sink->spans();
    ASSERT_EQ(spans.size(), 1u);
    EXPECT_EQ(spans[0].meta.location.line(), expected_line);
    EXPECT_TRUE(std::string_view(spans[0].meta.location.file_name()).ends_with("test_span_timing.cpp"));
}

TEST(SpanTiming, StatsAggregatePerSite) {
    TracerWithSink t;
    std::uint64_t sum = 0;
    for (std::uint64_t i = 1; i <= 1000; ++i) {
        // 1000..1,000,000 ns in a scrambled order (7919 is coprime to 1000), so min and max are
        // neither the first nor the last sample.
        const auto d = ((i * 7919) % 1000 + 1) * 1000;
        sum += d;
        // Both calls on one line: same file and line, different label -> separate rows.
        ASSERT_TRUE(t.tracer.recordSpan("step", std::chrono::nanoseconds(d)).has_value()); ASSERT_TRUE(t.tracer.recordSpan("other", 7ns).has_value());
    }
    const auto stats = t.tracer.spanStats();
    ASSERT_EQ(stats.size(), 2u);

    // total descending
    EXPECT_EQ(stats[0].label, "step");
    EXPECT_EQ(stats[0].meter, "manual");
    EXPECT_EQ(stats[0].count, 1000u);
    EXPECT_EQ(stats[0].totalNs, sum);
    EXPECT_EQ(stats[0].minNs, 1000u);
    EXPECT_EQ(stats[0].maxNs, 1'000'000u);
    const auto mean = stats[0].totalNs / stats[0].count;
    EXPECT_LE(stats[0].minNs, mean);
    EXPECT_LE(mean, stats[0].maxNs);

    EXPECT_EQ(stats[1].label, "other");
    EXPECT_EQ(stats[1].count, 1000u);
    EXPECT_EQ(stats[1].totalNs, 7000u);
    EXPECT_EQ(stats[1].minNs, 7u);
    EXPECT_EQ(stats[1].maxNs, 7u);
    EXPECT_EQ(stats[0].line, stats[1].line);
    EXPECT_EQ(stats[0].file, stats[1].file);

    EXPECT_EQ(t.sink->spans().size(), 2000u);
}

TEST(SpanTiming, NegativeDurationRejected) {
    TracerWithSink t;
    const auto result = t.tracer.recordSpan("bad", -1ns);
    ASSERT_FALSE(result.has_value());
    EXPECT_EQ(result.error(), atugcc::core::CoreError::InvalidArgument);
    EXPECT_TRUE(t.tracer.spanStats().empty());
    EXPECT_TRUE(t.sink->spans().empty());
}

TEST(SpanTiming, ClearResetsStats) {
    TracerWithSink t;
    ASSERT_TRUE(t.tracer.recordSpan("x", 5ns).has_value());
    ASSERT_EQ(t.tracer.spanStats().size(), 1u);
    t.tracer.clear();
    EXPECT_TRUE(t.tracer.spanStats().empty());
}

TEST(SpanTiming, ConcurrentSpansAggregate) {
    TracerWithSink t;
    constexpr int kThreads = 4;
    constexpr int kPerThread = 10'000;
    std::latch start(kThreads);
    std::vector<std::thread> workers;
    for (int w = 0; w < kThreads; ++w) {
        workers.emplace_back([&t, &start] {
            start.arrive_and_wait();
            for (int i = 0; i < kPerThread; ++i) {
                auto span = t.tracer.timeScope("work");
            }
        });
    }
    for (auto& worker : workers) {
        worker.join();
    }
    const auto stats = t.tracer.spanStats();
    ASSERT_EQ(stats.size(), 1u);
    EXPECT_EQ(stats[0].count, static_cast<std::uint64_t>(kThreads * kPerThread));

    const auto spans = t.sink->spans();
    ASSERT_EQ(spans.size(), static_cast<std::size_t>(kThreads * kPerThread));
    std::vector<std::uint64_t> threads;
    std::vector<std::uint64_t> seqs;
    for (const auto& span : spans) {
        threads.push_back(span.threadId);
        seqs.push_back(span.meta.seq);
    }
    std::ranges::sort(threads);
    EXPECT_EQ(std::ranges::distance(threads.begin(), std::ranges::unique(threads).begin()), kThreads);
    std::ranges::sort(seqs);
    EXPECT_EQ(std::ranges::adjacent_find(seqs), seqs.end());
}

// ============================================================================
// SpanMeter
// ============================================================================

TEST(SpanMeter, FactoryNames) {
    ASSERT_NE(viz::makeSpanMeter("wall"), nullptr);
    ASSERT_NE(viz::makeSpanMeter("cpu"), nullptr);
    EXPECT_EQ(viz::makeSpanMeter("wall")->name(), "wall");
    EXPECT_EQ(viz::makeSpanMeter("cpu")->name(), "cpu");
    EXPECT_EQ(viz::makeSpanMeter("perf"), nullptr);
    EXPECT_EQ(viz::makeSpanMeter(""), nullptr);

    viz::Tracer tracer;
    tracer.setSpanMeter(viz::makeSpanMeter("cpu"));
    EXPECT_EQ(tracer.spanMeter()->name(), "cpu");
    tracer.setSpanMeter(nullptr);
    ASSERT_NE(tracer.spanMeter(), nullptr);
    EXPECT_EQ(tracer.spanMeter()->name(), "wall");
}

TEST(SpanMeter, SleepWallVersusCpu) {
    TracerWithSink t;
    const auto here = std::source_location::current();
    {
        viz::ScopedSpan span(t.tracer, "sleep", here);
        std::this_thread::sleep_for(20ms);
    }
    t.tracer.setSpanMeter(viz::makeSpanMeter("cpu"));
    {
        viz::ScopedSpan span(t.tracer, "sleep", here);
        std::this_thread::sleep_for(20ms);
    }
    const auto spans = t.sink->spans();
    ASSERT_EQ(spans.size(), 2u);
    EXPECT_EQ(spans[0].meter, "wall");
    EXPECT_GE(spans[0].durationNs, 20 * kMs);
    EXPECT_EQ(spans[1].meter, "cpu");
#ifdef __linux__
    // Spec AC-8 is Linux: Windows charges thread CPU time in scheduler ticks (~15.6 ms).
    EXPECT_LT(spans[1].durationNs, 5 * kMs);
#endif

    // wall and cpu at the same site (same `here`) are separate rows
    EXPECT_EQ(t.tracer.spanStats().size(), 2u);
}

TEST(SpanMeter, CpuMeterScaleMatchesBusyTime) {
    const auto cpu = viz::makeSpanMeter("cpu");
    const auto wall = viz::makeSpanMeter("wall");
    const auto cpu_start = cpu->nowNs();
    const auto wall_start = wall->nowNs();
    const auto deadline = std::chrono::steady_clock::now() + 50ms;
    volatile std::uint64_t sink = 0;
    while (std::chrono::steady_clock::now() < deadline) {
        sink = sink + 1;
    }
    const auto busy_cpu = cpu->nowNs() - cpu_start;
    const auto busy_wall = wall->nowNs() - wall_start;
    // ns scale: never more than the elapsed wall time (plus one Windows tick), ...
    EXPECT_LE(busy_cpu, busy_wall + 16 * kMs);
#ifdef __linux__
    // ... and a 50 ms busy loop gets most of it (a wrong factor would be far off either way).
    EXPECT_GE(busy_cpu, 10 * kMs);
#else
    EXPECT_GT(busy_cpu, 0u);
#endif
}

TEST(SpanMeter, RecordSpanMeterIsSeparateRow) {
    TracerWithSink t;
    const auto here = std::source_location::current();
    {
        viz::ScopedSpan span(t.tracer, "io", here);
    }
    ASSERT_TRUE(t.tracer.recordSpan("io", 1s, here, "perf").has_value());

    const auto spans = t.sink->spans();
    ASSERT_EQ(spans.size(), 2u);
    EXPECT_EQ(spans[0].meter, "wall");
    EXPECT_EQ(spans[1].meter, "perf");
    EXPECT_EQ(spans[1].durationNs, 1000 * kMs);

    const auto stats = t.tracer.spanStats();
    ASSERT_EQ(stats.size(), 2u);
    EXPECT_EQ(stats[0].meter, "perf");   // 1 s > an empty scope, even when preempted
    EXPECT_EQ(stats[1].meter, "wall");
    EXPECT_EQ(stats[0].line, here.line());
    EXPECT_EQ(stats[1].line, here.line());
}

TEST(SpanMeter, SwitchDuringSpanKeepsStartMeter) {
    TracerWithSink t;
    const auto a = std::make_shared<FakeMeter>("A");
    const auto b = std::make_shared<FakeMeter>("B");
    t.tracer.setSpanMeter(a);
    {
        auto span = t.tracer.timeScope("switch");
        t.tracer.setSpanMeter(b);
    }
    const auto spans = t.sink->spans();
    ASSERT_EQ(spans.size(), 1u);
    EXPECT_EQ(spans[0].meter, "A");
    EXPECT_EQ(spans[0].durationNs, 1000u);
    EXPECT_EQ(a->reads(), 2u);
    EXPECT_EQ(b->reads(), 0u);
    EXPECT_EQ(t.tracer.spanMeter(), b);
}

TEST(SpanMeter, ConcurrentSwitchingKeepsEachSpanOnOneMeter) {
    TracerWithSink t;
    const auto a = std::make_shared<FakeMeter>("A");
    const auto b = std::make_shared<FakeMeter>("B");
    t.tracer.setSpanMeter(a);

    constexpr int kThreads = 3;
    constexpr int kPerThread = 5'000;
    std::atomic_bool done{ false };
    std::latch start(kThreads + 1);
    std::thread switcher([&] {
        start.arrive_and_wait();
        bool use_b = true;
        while (!done.load()) {
            t.tracer.setSpanMeter(use_b ? std::shared_ptr<viz::SpanMeter>(b) : std::shared_ptr<viz::SpanMeter>(a));
            use_b = !use_b;
        }
    });
    std::vector<std::thread> workers;
    for (int w = 0; w < kThreads; ++w) {
        workers.emplace_back([&t, &start] {
            start.arrive_and_wait();
            for (int i = 0; i < kPerThread; ++i) {
                auto span = t.tracer.timeScope("mixed");
            }
        });
    }
    for (auto& worker : workers) {
        worker.join();
    }
    done.store(true);
    switcher.join();

    const auto spans = t.sink->spans();
    ASSERT_EQ(spans.size(), static_cast<std::size_t>(kThreads * kPerThread));
    std::size_t on_a = 0;
    for (const auto& span : spans) {
        ASSERT_TRUE(span.meter == "A" || span.meter == "B") << span.meter;
        if (span.meter == "A") {
            ++on_a;
        }
    }
    // The switcher really interleaved with the workers (otherwise this is a one-meter run).
    EXPECT_GT(on_a, 0u);
    EXPECT_LT(on_a, spans.size());
    // Every span reads its meter exactly twice.
    EXPECT_EQ(a->reads(), 2 * on_a);
    EXPECT_EQ(b->reads(), 2 * (spans.size() - on_a));

    std::uint64_t counted = 0;
    for (const auto& row : t.tracer.spanStats()) {
        counted += row.count;
    }
    EXPECT_EQ(counted, spans.size());
}

// ============================================================================
// SpanJson
// ============================================================================

TEST(SpanJson, LineMatchesSchema) {
    viz::Span span{
        .label      = "pa\"rse",
        .meter      = "wall",
        .durationNs = 1'234'567,
        .threadId   = 3,
        .meta       = viz::EventMeta{ .location = std::source_location::current() },
    };
    span.meta.seq = 17;
    span.meta.tracerId = 1;

    const auto line = viz::toJsonLine(span);
    EXPECT_TRUE(line.starts_with(
        R"({"v":1,"kind":"span","seq":17,"tracer":1,"label":"pa\"rse","meter":"wall","durNs":1234567,"thread":3,"file":")"))
        << line;
    EXPECT_TRUE(line.ends_with("}")) << line;
    EXPECT_EQ(line.find('\n'), std::string::npos);

    std::size_t previous = 0;
    for (const std::string_view key : { "\"file\":", "\"line\":", "\"func\":", "\"tUs\":" }) {
        const auto at = line.find(key);
        ASSERT_NE(at, std::string::npos) << key;
        EXPECT_GT(at, previous) << key;
        previous = at;
    }
    EXPECT_NE(line.find(std::format("\"line\":{},", span.meta.location.line())), std::string::npos);
}

TEST(SpanJson, SinkWritesSpanLines) {
    const auto path = tempTracePath("sink");
    {
        auto sink = viz::JsonLinesEventSink::open(path, 100ms);
        ASSERT_NE(sink, nullptr);
        viz::Tracer tracer;
        tracer.setEventSink(sink);
        for (int i = 0; i < 500; ++i) {
            ASSERT_TRUE(tracer.recordSpan("bulk", std::chrono::nanoseconds(i)).has_value());
        }
    }
    const auto lines = readLines(path);
    const auto span_lines = std::ranges::count_if(lines, [](const std::string& line) {
        return line.starts_with(R"({"v":1,"kind":"span",)");
    });
    EXPECT_EQ(span_lines, 500);
    std::filesystem::remove(path);
}

TEST(SpanJson, FlushIntervalFlushesAfterQuietPeriod) {
    const auto path = tempTracePath("interval");
    {
        auto sink = viz::JsonLinesEventSink::open(path, 100ms);
        ASSERT_NE(sink, nullptr);
        viz::Tracer tracer;
        tracer.setEventSink(sink);
        ASSERT_TRUE(tracer.recordSpan("first", 1ns).has_value());
        std::this_thread::sleep_for(150ms);
        ASSERT_TRUE(tracer.recordSpan("second", 1ns).has_value());
        // The interval has passed since open(): the second write flushes both lines.
        EXPECT_EQ(readLines(path).size(), 2u);
    }
    std::filesystem::remove(path);
}

TEST(SpanJson, FlushIntervalHoldsLinesBack) {
    const auto path = tempTracePath("hold");
    {
        auto sink = viz::JsonLinesEventSink::open(path, std::chrono::hours{ 1 });
        ASSERT_NE(sink, nullptr);
        viz::Tracer tracer;
        tracer.setEventSink(sink);
        ASSERT_TRUE(tracer.recordSpan("held", 1ns).has_value());
        EXPECT_EQ(readLines(path).size(), 0u);   // within the interval: still buffered
    }
    EXPECT_EQ(readLines(path).size(), 1u);       // the sink flushes when it is destroyed
    std::filesystem::remove(path);
}

// ============================================================================
// SpanFormat
// ============================================================================

TEST(SpanFormat, LiveLineAndTimingsTable) {
    viz::Tracer tracer;
    tracer.setEventSink(nullptr);
    std::ostringstream out;
    tracer.setOutputSink(std::make_shared<viz::ConsoleTraceSink>(out));
    tracer.setLiveTerminalOutputEnabled(true);

    EXPECT_EQ(tracer.formatTimings(), "(no spans)\n");

    const auto line = std::source_location::current().line() + 1;
    ASSERT_TRUE(tracer.recordSpan("parse", 1'234'567ns).has_value());
    EXPECT_EQ(out.str(), std::format("⏱ parse  1.235 ms  (test_span_timing.cpp:{})\n", line));

    out.str("");
    ASSERT_TRUE(tracer.recordSpan("tiny", 999ns).has_value());
    EXPECT_TRUE(out.str().starts_with("⏱ tiny  999 ns  (")) << out.str();
    out.str("");
    ASSERT_TRUE(tracer.recordSpan("small", 1'500ns).has_value());
    EXPECT_TRUE(out.str().starts_with("⏱ small  1.500 µs  (")) << out.str();
    out.str("");
    ASSERT_TRUE(tracer.recordSpan("long", 2'500'000'000ns).has_value());
    EXPECT_TRUE(out.str().starts_with("⏱ long  2.500 s  (")) << out.str();

    const auto table = tracer.formatTimings();
    for (const std::string_view header : { "label", "meter", "location", "count", "total", "mean", "min", "max" }) {
        EXPECT_NE(table.find(header), std::string::npos) << header;
    }
    for (const std::string_view row : { "parse", "tiny", "small", "long", "1.235 ms", "999 ns", "1.500 µs", "2.500 s" }) {
        EXPECT_NE(table.find(row), std::string::npos) << row;
    }
    // total descending: "long" row comes before "parse"
    EXPECT_LT(table.find("long"), table.find("parse"));
}

TEST(SpanFormat, TimingsRowColumns) {
    viz::Tracer tracer;
    tracer.setEventSink(nullptr);
    std::uint32_t line = 0;
    for (const auto d : { 3ms, 1ms }) {
        line = std::source_location::current().line() + 1;
        ASSERT_TRUE(tracer.recordSpan("avg", d).has_value());
    }

    const auto table = tracer.formatTimings();
    const auto row_at = table.find("\navg");
    ASSERT_NE(row_at, std::string::npos) << table;
    const auto row_end = table.find('\n', row_at + 1);
    const auto row = std::string_view(table).substr(row_at + 1, row_end - row_at - 1);

    // Columns are separated by two or more spaces; a duration holds a single space.
    std::vector<std::string> cells;
    std::size_t pos = 0;
    while (pos < row.size()) {
        const auto gap = row.find("  ", pos);
        cells.emplace_back(row.substr(pos, gap == std::string_view::npos ? std::string_view::npos : gap - pos));
        if (gap == std::string_view::npos) {
            break;
        }
        pos = row.find_first_not_of(' ', gap);
    }
    const std::vector<std::string> expected{
        "avg", "manual", std::format("test_span_timing.cpp:{}", line),
        "2", "4.000 ms", "2.000 ms", "1.000 ms", "3.000 ms",
    };
    EXPECT_EQ(cells, expected) << table;
}

// ============================================================================
// SpanLifetime
// ============================================================================

#if !defined(NDEBUG) && defined(__linux__) && !defined(__SANITIZE_THREAD__) && !defined(__SANITIZE_ADDRESS__)
TEST(SpanLifetimeDeathTest, SpanOutlivingTracerAsserts) {
    GTEST_FLAG_SET(death_test_style, "threadsafe");
    EXPECT_DEATH({
        auto* tracer = new viz::Tracer();
        auto* leaked = new viz::ScopedSpan(*tracer, "leaked");
        (void)leaked;
        delete tracer;
    }, "ScopedSpan outlived its Tracer");
}
#endif
