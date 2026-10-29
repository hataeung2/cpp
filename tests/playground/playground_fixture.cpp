/**
 * @file playground_fixture.cpp
 * @brief Fixture program for web/server/test_server.py (spec 070-02 AC-5, AC-11, AC-12)
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
 */
#include <chrono>
#include <cstdlib>
#include <iostream>
#include <string>
#include <string_view>
#include <thread>

#include "atugcc/pattern/visualizer.hpp"

using namespace std::chrono_literals;

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
    std::cerr << "usage: playground_fixture loop|flood|tick|spawn|crash|trace\n";
    return 2;
}
