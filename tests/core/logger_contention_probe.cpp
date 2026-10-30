/**
 * @file logger_contention_probe.cpp
 * @brief Shared Logger vs Logger per thread vs DbgBuf only (spec 010-08 AC-10, Assumptions 8 and 9)
 *
 * Usage: logger_contention_probe [lines per thread, default 100000] [runs, default 3]
 *
 *   A  one Logger shared by every thread (mutex around the history)
 *   B  one Logger per thread
 *   C  DbgBuf::log only: the lower bound of per-thread buffers (same std::format, no history,
 *      no lock, no consumer)
 *
 * Each mode runs with 1, 2, 4 and 8 threads, with live output off and on (on: every Logger
 * writes to one shared temporary file; C has no live output). Per configuration the fastest of
 * `runs` runs is reported: wall ns per line, per-call latency p50 / p99 / max, lines per second.
 * Exit 1 if a live-output run did not write every line whole (live-off runs have no output to
 * count; their completeness is the history and DbgBuf tests in test_logger.cpp). Run on a Release preset for numbers;
 * CTest runs it with small counts as a smoke test (no threshold on the numbers).
 */
#include <algorithm>
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <filesystem>
#include <format>
#include <fstream>
#include <latch>
#include <memory>
#include <source_location>
#include <string>
#include <thread>
#include <vector>

#include "atugcc/core/logger.hpp"
#include "atugcc/core/ring_buffer.hpp"

namespace fs = std::filesystem;
using atugcc::core::DbgBuf;
using atugcc::core::Level;
using atugcc::core::Logger;
using Clock = std::chrono::steady_clock;

namespace {

enum class Mode { Shared, PerThread, DbgBufOnly };

struct Result {
    double wallNsPerLine = 0;
    std::uint64_t p50 = 0;
    std::uint64_t p99 = 0;
    std::uint64_t max = 0;
    double linesPerSecond = 0;
    bool complete = true;
};

const char* modeName(Mode m) {
    switch (m) {
        case Mode::Shared: return "A shared";
        case Mode::PerThread: return "B per-thread";
        case Mode::DbgBufOnly: return "C DbgBuf only";
    }
    return "?";
}

Logger::Config config(std::ostream* live) {
    return {.bufferCapacity = 256, .liveOutput = live, .dumpDir = "log", .enableCrashDump = false};
}

// Number of whole lines: each starts with "[INFO] [", holds that prefix once and ends with " t<n> i<n>".
// A line mixed from two writers fails the check, so it is not counted.
std::size_t countWholeLines(const fs::path& p) {
    std::ifstream in(p);
    std::size_t n = 0;
    std::string line;
    while (std::getline(in, line)) {
        const auto tail = line.rfind(" t");
        const bool whole = line.starts_with("[INFO] [") && line.find("[INFO] [", 1) == std::string::npos &&
                           tail != std::string::npos && line.find(" i", tail) != std::string::npos;
        if (whole) ++n;
    }
    return n;
}

Result runOnce(Mode mode, int threads, bool live, int lines, const fs::path& liveFile) {
    std::unique_ptr<std::ofstream> out;
    if (live) out = std::make_unique<std::ofstream>(liveFile, std::ios::trunc);
    std::ostream* liveStream = out.get();

    std::unique_ptr<Logger> shared;
    std::vector<std::unique_ptr<Logger>> own;
    if (mode == Mode::Shared) shared = std::make_unique<Logger>(config(liveStream));
    if (mode == Mode::PerThread) {
        for (int t = 0; t < threads; ++t) own.push_back(std::make_unique<Logger>(config(liveStream)));
    }

    std::vector<std::vector<std::uint32_t>> samples(static_cast<std::size_t>(threads));
    std::latch ready(threads + 1);
    std::latch go(1);
    std::vector<std::jthread> workers;
    for (int t = 0; t < threads; ++t) {
        workers.emplace_back([&, t] {
            auto& mine = samples[static_cast<std::size_t>(t)];
            mine.reserve(static_cast<std::size_t>(lines));
            Logger* logger = mode == Mode::Shared ? shared.get()
                           : mode == Mode::PerThread ? own[static_cast<std::size_t>(t)].get()
                           : nullptr;
            ready.count_down();
            go.wait();
            for (int i = 0; i < lines; ++i) {
                const auto begin = Clock::now();
                if (logger != nullptr) {
                    logger->log(Level::Info, "t{} i{}", t, i);
                } else {
                    const auto loc = std::source_location::current();
                    DbgBuf::log(std::format("[{}] [{}:{} {}] t{} i{}", "INFO", loc.file_name(), loc.line(),
                                            loc.function_name(), t, i),
                                Level::Info);
                }
                const auto ns = std::chrono::duration_cast<std::chrono::nanoseconds>(Clock::now() - begin).count();
                mine.push_back(static_cast<std::uint32_t>(std::min<long long>(ns, UINT32_MAX)));
            }
        });
    }
    ready.arrive_and_wait();
    const auto start = Clock::now();
    go.count_down();
    workers.clear();
    const auto wall = Clock::now() - start;

    shared.reset();
    own.clear();
    if (out) out->close();

    std::vector<std::uint32_t> all;
    for (auto& v : samples) all.insert(all.end(), v.begin(), v.end());
    std::sort(all.begin(), all.end());
    const auto total = static_cast<double>(all.size());
    const double wallNs = static_cast<double>(std::chrono::duration_cast<std::chrono::nanoseconds>(wall).count());

    Result r;
    r.wallNsPerLine = wallNs / total;
    r.p50 = all[all.size() / 2];
    r.p99 = all[(std::min)(all.size() - 1, static_cast<std::size_t>(total * 0.99))];  // (std::min): <Windows.h> min macro, KI-027
    r.max = all.back();
    r.linesPerSecond = total / (wallNs / 1e9);
    if (live) r.complete = countWholeLines(liveFile) == all.size();
    return r;
}

double clockOverheadNs() {
    constexpr int kReps = 100000;
    const auto begin = Clock::now();
    for (int i = 0; i < kReps; ++i) {
        [[maybe_unused]] volatile auto t = Clock::now().time_since_epoch().count();
    }
    return static_cast<double>(std::chrono::duration_cast<std::chrono::nanoseconds>(Clock::now() - begin).count()) / kReps;
}

}  // namespace

int main(int argc, char* argv[]) {
    const int lines = argc > 1 ? std::atoi(argv[1]) : 100000;
    const int runs = argc > 2 ? std::atoi(argv[2]) : 3;
    if (lines <= 0 || runs <= 0) {
        std::fprintf(stderr, "usage: logger_contention_probe [lines per thread > 0] [runs > 0]\n");
        return 2;
    }
    const fs::path liveFile = fs::temp_directory_path() / std::format("atugcc_logger_contention_{}.log",
        std::chrono::steady_clock::now().time_since_epoch().count());

    std::printf("lines per thread %d, runs %d, hardware threads %u, clock read %.1f ns\n", lines, runs,
                std::thread::hardware_concurrency(), clockOverheadNs());
    std::printf("%-14s %7s %4s %12s %8s %8s %10s %12s\n", "mode", "threads", "live", "wall ns/line", "p50 ns",
                "p99 ns", "max ns", "lines/s");

    bool ok = true;
    // results[mode][live][threadIndex] for the Assumption 9 comparison
    Result table[3][2][4];
    constexpr int kThreads[] = {1, 2, 4, 8};
    for (int m = 0; m < 3; ++m) {
        for (int live = 0; live < 2; ++live) {
            const auto mode = static_cast<Mode>(m);
            if (mode == Mode::DbgBufOnly && live == 1) continue;
            for (int ti = 0; ti < 4; ++ti) {
                Result best;
                for (int r = 0; r < runs; ++r) {
                    const Result cur = runOnce(mode, kThreads[ti], live == 1, lines, liveFile);
                    ok = ok && cur.complete;
                    if (r == 0 || cur.wallNsPerLine < best.wallNsPerLine) best = cur;
                }
                table[m][live][ti] = best;
                std::printf("%-14s %7d %4s %12.1f %8llu %8llu %10llu %12.0f%s\n", modeName(mode), kThreads[ti],
                            live == 1 ? "on" : "off", best.wallNsPerLine,
                            static_cast<unsigned long long>(best.p50), static_cast<unsigned long long>(best.p99),
                            static_cast<unsigned long long>(best.max), best.linesPerSecond,
                            best.complete ? "" : "  MISSING LINES");
            }
        }
    }

    std::printf("\nAssumption 9 (live off): p99 A/B, throughput A/B\n");
    for (int ti = 2; ti < 4; ++ti) {
        const Result& a = table[0][0][ti];
        const Result& b = table[1][0][ti];
        std::printf("  %d threads: p99 %.2fx, throughput %.0f%%\n", kThreads[ti],
                    b.p99 == 0 ? 0.0 : static_cast<double>(a.p99) / static_cast<double>(b.p99),
                    b.linesPerSecond == 0 ? 0.0 : 100.0 * a.linesPerSecond / b.linesPerSecond);
    }

    std::error_code ec;
    fs::remove(liveFile, ec);
    if (!ok) {
        std::fprintf(stderr, "a live-output run did not write every line\n");
        return 1;
    }
    return 0;
}
