/**
 * @file crash_probe.cpp
 * @brief Logs from several threads, then ends in one of the ways of spec 010-09 §2.4
 *        (AC-2 … AC-5, AC-10). tests/core/check_crash_dump.py runs it and checks the results.
 *
 * Usage: crash_probe <mode> <work dir> [lines]
 *   normal         8 producers (4 of them end half-way and are replaced), main returns (AC-2)
 *   exit | quickexit
 *                  as normal, but the Logger is never destroyed and the program ends with
 *                  std::exit / std::quick_exit: the atexit / at_quick_exit drain delivers (§2.4)
 *   segv | abort | terminate | stackoverflow
 *                  4 producers keep logging; one short-lived thread logs and ends (its buffer
 *                  stays retired: the crasher thread took its own buffer before); then the crasher
 *                  logs CRASH-MARKER with every producer's last line number, writes one
 *                  Delivery::Sync line and crashes that way (AC-3, AC-4)
 *   killme         logs BEFORE KILL, waits 50 ms, prints READY and waits to be killed (AC-5)
 *
 * Lines are "P<producer> L<line>". The work dir gets app.log (async Logger), sync.log
 * (Delivery::Sync Logger) and the crash dump. Only logger.hpp is included, and std::min is
 * called unparenthesised: on Windows that only compiles if logger.hpp keeps <Windows.h>
 * out (AC-10, KI-027).
 */
#include <algorithm>
#include <array>
#include <atomic>
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <filesystem>
#include <stdexcept>
#include <string>
#include <string_view>
#include <thread>
#include <vector>

#include "atugcc/core/logger.hpp"

#ifdef _WIN32
#include <crtdbg.h>
#include <cstdlib>
#endif

namespace fs = std::filesystem;
using atugcc::core::Level;
using atugcc::core::Logger;
using namespace std::chrono_literals;

namespace {

constexpr int kProducers = 4;

Logger::Config config(const fs::path& dir, const char* file, atugcc::core::Delivery delivery) {
    Logger::Config cfg;
    cfg.bufferCapacity = 64;
    cfg.dumpDir = dir;
    cfg.enableCrashDump = true;
    cfg.filePath = dir / file;
    cfg.delivery = delivery;
    cfg.overflow = atugcc::core::OverflowPolicy::Block;  // the checks count every line
    return cfg;
}

void produce(Logger& log, int producer, int first, int last, std::atomic<int>* progress) {
    for (int i = first; i < last; ++i) {
        log.log(Level::Info, "P{} L{}", producer, i);
        if (progress != nullptr) progress->store(i, std::memory_order_release);
    }
}

void produceAll(Logger& log, int lines) {
    std::vector<std::jthread> threads;
    for (int p = 0; p < 8; ++p) {
        const int end = p < 4 ? lines : lines / 2;
        threads.emplace_back([&log, p, end] { produce(log, p, 0, end, nullptr); });
    }
    // producers 4..7 end half-way; new threads finish their lines (a new thread, a reused buffer)
    for (int p = 4; p < 8; ++p) threads[static_cast<std::size_t>(p)].join();
    for (int p = 4; p < 8; ++p) {
        threads[static_cast<std::size_t>(p)] = std::jthread([&log, p, lines] { produce(log, p, lines / 2, lines, nullptr); });
    }
    threads.clear();
    log.log(Level::Info, "DONE {}", std::min(lines, 8 * lines));
}

int runNormal(const fs::path& dir, int lines) {
    Logger log(config(dir, "app.log", atugcc::core::Delivery::Async));
    produceAll(log, lines);
    return 0;  // the Logger's destructor delivers
}

[[noreturn]] void runExit(const fs::path& dir, int lines, bool quick) {
    // never destroyed: only the service's atexit / at_quick_exit drain can deliver the last lines
    auto* log = new Logger(config(dir, "app.log", atugcc::core::Delivery::Async));
    produceAll(*log, lines);
    if (quick) std::quick_exit(0);
    std::exit(0);
}

[[noreturn]] void crashNow(std::string_view mode);

int depthSink = 0;

int recurse(int n) {
    volatile char frame[4096];
    frame[0] = static_cast<char>(n);
    if (n == 1 << 30) return 0;  // never reached; keeps compilers from calling it endless recursion
    return recurse(n + 1) + frame[0];
}

void crashNow(std::string_view mode) {
    if (mode == "segv") {
        volatile int* p = nullptr;
        *p = 1;
    } else if (mode == "abort") {
        std::abort();
    } else if (mode == "terminate") {
        throw std::runtime_error("unhandled on purpose");
    } else if (mode == "stackoverflow") {
        depthSink = recurse(0);
    }
    std::abort();
}

int runCrash(const fs::path& dir, std::string_view mode) {
    Logger log(config(dir, "app.log", atugcc::core::Delivery::Async));
    Logger syncLog(config(dir, "sync.log", atugcc::core::Delivery::Sync));

    std::array<std::atomic<int>, kProducers> progress{};
    for (auto& p : progress) p.store(-1);
    std::atomic<bool> stop{false};
    std::vector<std::jthread> producers;
    for (int p = 0; p < kProducers; ++p) {
        producers.emplace_back([&, p] {
            for (int i = 0; !stop.load(std::memory_order_relaxed); ++i) {
                log.log(Level::Info, "P{} L{}", p, i);
                progress[static_cast<std::size_t>(p)].store(i, std::memory_order_release);
                if (i % 64 == 0) std::this_thread::sleep_for(1ms);
            }
        });
    }
    // The crasher takes its buffer first, so the short-lived thread's buffer below is not reused
    // by anyone before the crash and stays marked retired in the dump.
    std::atomic<bool> go{false};
    std::atomic<bool> crasherReady{false};
    std::jthread crasher([&] {
        log.log(Level::Info, "crasher ready");
        crasherReady = true;
        while (!go.load()) std::this_thread::sleep_for(1ms);
        std::string marker = "CRASH-MARKER";
        for (int p = 0; p < kProducers; ++p) {
            marker += " P" + std::to_string(p) + "=" + std::to_string(progress[static_cast<std::size_t>(p)].load());
        }
        log.log(Level::Error, "{}", marker);
        // logged right before the crash: only Delivery::Sync can have put it in sync.log (AC-4)
        syncLog.log(Level::Info, "SYNC before crash");
        crashNow(mode);
    });
    while (!crasherReady.load()) std::this_thread::sleep_for(1ms);
    // a thread that ends before the crash: its buffer is retired but must still be in the dump
    std::jthread([&log] { produce(log, 9, 0, 10, nullptr); }).join();

    while (std::any_of(progress.begin(), progress.end(), [](const auto& p) { return p.load() < 500; })) {
        std::this_thread::sleep_for(1ms);
    }
    go = true;
    crasher.join();
    stop = true;
    return 3;  // not reached
}

int runKillMe(const fs::path& dir) {
    Logger log(config(dir, "app.log", atugcc::core::Delivery::Async));
    log.log(Level::Info, "BEFORE KILL");
    std::this_thread::sleep_for(50ms);
    std::printf("READY\n");
    std::fflush(stdout);
    for (;;) std::this_thread::sleep_for(1s);
}

}  // namespace

int main(int argc, char* argv[]) {
#ifdef _WIN32
    // No message boxes from abort() or the debug CRT: the test harness would hang on them.
    _set_abort_behavior(0, _WRITE_ABORT_MSG | _CALL_REPORTFAULT);
    _CrtSetReportMode(_CRT_ASSERT, _CRTDBG_MODE_FILE);
    _CrtSetReportFile(_CRT_ASSERT, _CRTDBG_FILE_STDERR);
    _CrtSetReportMode(_CRT_ERROR, _CRTDBG_MODE_FILE);
    _CrtSetReportFile(_CRT_ERROR, _CRTDBG_FILE_STDERR);
#endif
    if (argc < 3) {
        std::fprintf(stderr, "usage: crash_probe normal|exit|quickexit|segv|abort|terminate|stackoverflow|killme <work dir> [lines]\n");
        return 2;
    }
    const std::string_view mode = argv[1];
    const fs::path dir = argv[2];
    const int lines = argc > 3 ? std::atoi(argv[3]) : 100000;
    std::error_code ec;
    fs::remove_all(dir, ec);
    fs::create_directories(dir);
    if (mode == "normal") return runNormal(dir, lines);
    if (mode == "exit") runExit(dir, lines, false);
    if (mode == "quickexit") runExit(dir, lines, true);
    if (mode == "killme") return runKillMe(dir);
    if (mode == "segv" || mode == "abort" || mode == "terminate" || mode == "stackoverflow") return runCrash(dir, mode);
    std::fprintf(stderr, "unknown mode\n");
    return 2;
}
