/**
 * @file span_cost_probe.cpp
 * @brief Span recording cost and the flush-interval check (spec 020-06 AC-5, AC-6, AC-8)
 *
 * Usage: span_cost_probe [spans per cost run, default 200000] [spans per flush run, default 100000]
 *
 * Prints the cost of one meter read and of one ScopedSpan (meter calls included) without a sink
 * and with a JSON Lines sink, so the numbers can go into lessons/README.md (run it on a Release
 * preset for that). Then checks AC-5: spans written with a 100 ms flush interval take less time
 * than with a flush per line, and both files hold every line. Each side is the fastest of three
 * runs. Exit 1 if a line is missing, and, in optimized builds (NDEBUG), if the interval is not
 * faster: at -O0 the JSON formatting costs far more than the flush, so the difference is noise
 * there (the AC-5 evidence comes from the Release presets).
 */
#include <algorithm>
#include <chrono>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <memory>
#include <string>

#include "atugcc/pattern/visualizer.hpp"

namespace viz = atugcc::pattern::viz;
using namespace std::chrono_literals;

namespace {

using Clock = std::chrono::steady_clock;

double nsPer(Clock::duration elapsed, std::size_t count) {
    return static_cast<double>(std::chrono::duration_cast<std::chrono::nanoseconds>(elapsed).count()) /
        static_cast<double>(count);
}

std::filesystem::path tempPath(const char* tag) {
    const auto ticks = Clock::now().time_since_epoch().count();
    return std::filesystem::temp_directory_path() /
        ("atugcc_span_cost_" + std::string(tag) + "_" + std::to_string(ticks) + ".jsonl");
}

std::size_t countLines(const std::filesystem::path& path) {
    std::ifstream in(path, std::ios::binary);
    std::size_t lines = 0;
    for (std::string line; std::getline(in, line);) {
        ++lines;
    }
    return lines;
}

double meterReadCost(const viz::SpanMeter& meter, std::size_t count) {
    std::uint64_t checksum = 0;
    const auto start = Clock::now();
    for (std::size_t i = 0; i < count; ++i) {
        checksum += meter.nowNs();
    }
    const auto elapsed = Clock::now() - start;
    if (checksum == 1) {   // keeps the loop from being optimized away
        std::puts("");
    }
    return nsPer(elapsed, count);
}

// One ScopedSpan per iteration on a fresh Tracer. sink == nullptr: aggregates only.
double spanCost(std::shared_ptr<viz::SpanMeter> meter, std::shared_ptr<viz::TraceEventSink> sink, std::size_t count) {
    viz::Tracer tracer;
    tracer.setSpanMeter(std::move(meter));
    tracer.setEventSink(std::move(sink));
    const auto start = Clock::now();
    for (std::size_t i = 0; i < count; ++i) {
        auto span = tracer.timeScope("cost");
    }
    return nsPer(Clock::now() - start, count);
}

struct WriteRun {
    Clock::duration elapsed;
    std::size_t     lines;
};

// Writes `count` spans through a file sink with the given flush interval. The time includes
// closing the file (the final flush).
WriteRun writeSpans(std::chrono::milliseconds interval, std::size_t count) {
    const auto path = tempPath(interval == 0ms ? "flush0" : "flush100");
    Clock::duration elapsed{};
    {
        auto sink = viz::JsonLinesEventSink::open(path, interval);
        if (!sink) {
            std::fprintf(stderr, "span_cost_probe: cannot open %s\n", path.string().c_str());
            std::exit(1);
        }
        const auto start = Clock::now();
        {
            viz::Tracer tracer;
            tracer.setEventSink(sink);
            for (std::size_t i = 0; i < count; ++i) {
                (void)tracer.recordSpan("flush", std::chrono::nanoseconds(i));
            }
        }
        sink.reset();
        elapsed = Clock::now() - start;
    }
    const auto lines = countLines(path);
    std::filesystem::remove(path);
    return { elapsed, lines };
}

WriteRun fastestOfThree(std::chrono::milliseconds interval, std::size_t count) {
    auto best = writeSpans(interval, count);
    for (int i = 0; i < 2; ++i) {
        const auto run = writeSpans(interval, count);
        if (run.lines != best.lines) {
            best.lines = 0;   // inconsistent line counts fail the check below
        }
        best.elapsed = (std::min)(best.elapsed, run.elapsed);
    }
    return best;
}

} // namespace

int main(int argc, char** argv) {
    std::size_t count = 200'000;
    std::size_t flush_spans = 100'000;
    if (argc > 1) {
        count = static_cast<std::size_t>(std::strtoull(argv[1], nullptr, 10));
    }
    if (argc > 2) {
        flush_spans = static_cast<std::size_t>(std::strtoull(argv[2], nullptr, 10));
    }
    if (count == 0 || flush_spans == 0) {
        std::fprintf(stderr, "usage: span_cost_probe [spans per cost run > 0] [spans per flush run > 0]\n");
        return 2;
    }

    const auto wall = viz::makeSpanMeter("wall");
    const auto cpu = viz::makeSpanMeter("cpu");
    const auto discard = tempPath("discard");

    std::printf("span cost, %zu spans per run (ns per operation)\n", count);
    std::printf("  meter read, wall                 %8.1f\n", meterReadCost(*wall, count));
    std::printf("  meter read, cpu                  %8.1f\n", meterReadCost(*cpu, count));
    std::printf("  span, wall, no sink              %8.1f\n", spanCost(wall, nullptr, count));
    std::printf("  span, cpu, no sink               %8.1f\n", spanCost(cpu, nullptr, count));
    const auto fileSink = [&discard](std::chrono::milliseconds interval) {
        auto sink = viz::JsonLinesEventSink::open(discard, interval);
        if (!sink) {
            std::fprintf(stderr, "span_cost_probe: cannot open %s\n", discard.string().c_str());
            std::exit(1);
        }
        return sink;
    };
    std::printf("  span, wall, JSON sink + 100 ms   %8.1f\n", spanCost(wall, fileSink(100ms), count));
    std::printf("  span, wall, JSON sink, flush 0   %8.1f\n", spanCost(wall, fileSink(0ms), count));
    std::filesystem::remove(discard);

    const auto every_line = fastestOfThree(0ms, flush_spans);
    const auto interval = fastestOfThree(100ms, flush_spans);
    const auto ms = [](Clock::duration d) {
        return std::chrono::duration<double, std::milli>(d).count();
    };
    std::printf("AC-5: %zu spans, flush per line %.1f ms (%zu lines), flush 100 ms %.1f ms (%zu lines)\n",
        flush_spans, ms(every_line.elapsed), every_line.lines, ms(interval.elapsed), interval.lines);

    const bool lines_ok = every_line.lines == flush_spans && interval.lines == flush_spans;
#ifdef NDEBUG
    const bool faster = interval.elapsed < every_line.elapsed;
#else
    const bool faster = true;   // informational at -O0, see the file comment
#endif
    if (!lines_ok || !faster) {
        std::printf("AC-5: FAILED (%s%s)\n", lines_ok ? "" : "line counts differ ", faster ? "" : "interval not faster");
        return 1;
    }
    std::printf("AC-5: OK\n");
    return 0;
}
