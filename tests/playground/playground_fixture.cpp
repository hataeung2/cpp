/**
 * @file playground_fixture.cpp
 * @brief Fixture program for web/server/test_server.py (spec 070-02 AC-5, AC-11, AC-12; 070-06)
 *
 * Plays a misbehaving or slow lesson, chosen by the first argument:
 *   loop  — never ends (time limit, Stop)
 *   flood — writes 2 MiB to stdout (output limit)
 *   tick  — one line per second for 5 seconds through std::cout without flushing, so the lines
 *           reach the pipe one by one only when stdout is line buffered (stdbuf -oL)
 *   spawn — starts a background `sleep 987` in its own process group's shell, then exits
 *           (no process may survive the run)
 *   crash — std::abort() (signal reporting)
 *   trace — records three transitions on a Tracer, 300 ms apart (trace lines while running)
 *   sleep25    — sleeps 25 s and exits 0 (long profile limit, 070-06 AC-1)
 *   span_tick  — five rounds 1 s apart: a timeScope("tick") around 20 ms and a
 *                recordSpan("io", i ms, …, "perf"); then prints every spanStats() row as
 *                "STATS {json}" (070-06 AC-3, AC-4)
 *   span_flood — recordSpan("flood", …) 100,000 times per second for 30 s (070-06 AC-7, AC-10)
 *   build_info — prints "sanitized" or "plain": a sanitizer build cannot keep span_flood's rate,
 *                so the AC-7 test skips there
 */
#include <chrono>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <source_location>
#include <string>
#include <string_view>
#include <thread>

#include "atugcc/pattern/visualizer.hpp"

using namespace std::chrono_literals;
namespace viz = atugcc::pattern::viz;

namespace {

int spanTick() {
    viz::Tracer tracer;
    const auto here = std::source_location::current();
    bool ok = true;
    for (int i = 1; i <= 5; ++i) {
        {
            auto span = tracer.timeScope("tick");
            std::this_thread::sleep_for(20ms);
        }
        ok = tracer.recordSpan("io", std::chrono::milliseconds(i), here, "perf").has_value() && ok;
        std::this_thread::sleep_for(1s);
    }
    for (const auto& row : tracer.spanStats()) {
        std::cout << "STATS {\"file\":\"" << viz::detail::jsonEscape(row.file) << "\",\"line\":" << row.line
                  << ",\"label\":\"" << viz::detail::jsonEscape(row.label) << "\",\"meter\":\""
                  << viz::detail::jsonEscape(row.meter) << "\",\"count\":" << row.count
                  << ",\"totalNs\":" << row.totalNs << ",\"minNs\":" << row.minNs
                  << ",\"maxNs\":" << row.maxNs << "}\n";
    }
    return ok ? 0 : 1;
}

int spanFlood() {
    constexpr int kSeconds = 30;
    constexpr int kPerMillisecond = 100;
    viz::Tracer tracer;
    const auto start = std::chrono::steady_clock::now();
    std::uint64_t n = 0;
    for (int ms = 0; ms < kSeconds * 1000; ++ms) {
        for (int i = 0; i < kPerMillisecond; ++i, ++n) {
            (void)tracer.recordSpan("flood", std::chrono::nanoseconds(n % 1000));
        }
        std::this_thread::sleep_until(start + std::chrono::milliseconds(ms + 1));
    }
    std::cout << "flood done " << n << '\n';
    return 0;
}

} // namespace

int main(int argc, char** argv) {
    const std::string_view mode = argc > 1 ? argv[1] : "";
    if (mode == "loop") {
        for (;;) {
            std::this_thread::sleep_for(50ms);
        }
    }
    if (mode == "flood") {
        const std::string line(1023, 'x');
        for (int i = 0; i < 2048; ++i) {
            std::cout << line << '\n';
        }
        return 0;
    }
    if (mode == "tick") {
        for (int i = 1; i <= 5; ++i) {
            std::cout << "tick " << i << '\n';  // no std::flush, no std::endl
            std::this_thread::sleep_for(1s);
        }
        return 0;
    }
    if (mode == "spawn") {
        return std::system("sleep 987 &");
    }
    if (mode == "crash") {
        std::abort();
    }
    if (mode == "trace") {
        atugcc::pattern::viz::Tracer tracer;
        bool ok = tracer.recordTransition("IDLE", "STANDBY", "power").has_value();
        std::this_thread::sleep_for(300ms);
        ok = tracer.recordTransition("STANDBY", "RUN", "start").has_value() && ok;
        std::this_thread::sleep_for(300ms);
        ok = tracer.recordTransition("RUN", "IDLE", "stop").has_value() && ok;
        std::cout << "trace done\n";
        return ok ? 0 : 1;
    }
    if (mode == "sleep25") {
        std::this_thread::sleep_for(25s);
        std::cout << "slept\n";
        return 0;
    }
    if (mode == "span_tick") {
        return spanTick();
    }
    if (mode == "span_flood") {
        return spanFlood();
    }
    if (mode == "build_info") {
#if defined(__SANITIZE_ADDRESS__) || defined(__SANITIZE_THREAD__)
        std::cout << "sanitized\n";
#else
        std::cout << "plain\n";
#endif
        return 0;
    }
    std::cerr << "usage: playground_fixture loop|flood|tick|spawn|crash|trace|sleep25|span_tick|span_flood|build_info\n";
    return 2;
}
