/**
 * @file log_map_probe.cpp
 * @brief Test probe for memory-mapped log buffers and recovery (spec 010-10, plan D5).
 *        tests/core/check_log_map.py drives it and verifies preservation and recovery.
 *
 * Usage: log_map_probe <mode> <dir>
 *   killmap        configures log map with 1000ms drain, logs 4 x 1000 lines (Debug, Block),
 *                  prints READY, sleeps forever until killed by SIGKILL / TerminateProcess
 *   startrecover   configures log map (recovers ended runs on start), logs 1 line, returns 0
 *   recover        calls recoverLogMaps(<dir>), prints RECOVERED lines or ERROR, returns 0/1
 *   live           configures log map, logs 1 line, prints READY, sleeps forever
 *   normal         configures log map, prints MAP <path>, logs 100 lines, returns 0
 *   exit           configures log map, prints MAP <path>, allocates Logger with new, logs 100 lines, calls std::exit(0)
 *   quickexit      configures log map, prints MAP <path>, allocates Logger with new, logs 100 lines, calls std::quick_exit(0)
 *   abort          configures log map, prints MAP <path>, enableCrashDump = true, logs 100 lines (one Sync), calls std::abort()
 *   segv           configures log map, prints MAP <path>, enableCrashDump = true, logs 100 lines (one Sync), crashes via nullptr write
 *   config         tests configuration sequence in one process, prints OK/FAIL per step, returns 0/1
 *   env            expects ATUGCC_LOG_MAP_DIR in environment, logs 1 line, prints MAPPED 1/0
 *   full           configures 1 MiB log map, runs 12 threads with latch, each logs 1000 lines,
 *                  prints MAPPED <n> HEAP <m>
 *   threads        configures log map, runs 50 rounds x 8 threads logging 100 lines, returns 0
 */
#include <array>
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <latch>
#include <string>
#include <string_view>
#include <thread>
#include <vector>

#include "atugcc/core/detail/log_map.hpp"
#include "atugcc/core/detail/log_registry.hpp"
#include "atugcc/core/error.hpp"
#include "atugcc/core/log_buffer_config.hpp"
#include "atugcc/core/logger.hpp"

#ifdef _WIN32
#include <crtdbg.h>
#include <cstdlib>
#endif

namespace fs = std::filesystem;
using atugcc::core::CoreError;
using atugcc::core::Delivery;
using atugcc::core::Level;
using atugcc::core::Logger;
using atugcc::core::OverflowPolicy;
using namespace std::chrono_literals;

namespace detail = atugcc::core::detail;

namespace {

Logger::Config makeConfig(const fs::path& dir, bool enableCrashDump = false, Delivery delivery = Delivery::Async) {
    Logger::Config cfg;
    cfg.filePath = dir / "app.log";
    cfg.overflow = OverflowPolicy::Block;
    cfg.enableCrashDump = enableCrashDump;
    cfg.dumpDir = dir;
    cfg.delivery = delivery;
    return cfg;
}

int countLogMapFiles(const fs::path& dir) {
    int count = 0;
    std::error_code ec;
    for (const auto& entry : fs::directory_iterator(dir, ec)) {
        if (!ec && !entry.is_directory(ec) && entry.path().extension() == ".logmap") {
            ++count;
        }
    }
    return count;
}

int runKillMap(const fs::path& dir) {
    const auto res = atugcc::core::configureLogBuffers({
        .drainInterval = 1000ms,
        .mappedDir = dir,
    });
    if (!res) {
        std::printf("FAIL configure\n");
        std::fflush(stdout);
        return 1;
    }

    constexpr int kProducers = 4;
    constexpr int kLines = 1000;
    Logger log(makeConfig(dir));
    std::vector<std::jthread> threads;
    threads.reserve(static_cast<std::size_t>(kProducers));
    for (int p = 0; p < kProducers; ++p) {
        threads.emplace_back([&log, p] {
            for (int i = 0; i < kLines; ++i) {
                log.log(Level::Debug, "P{} L{}", p, i);
            }
        });
    }
    for (auto& t : threads) {
        t.join();
    }
    std::printf("READY\n");
    std::fflush(stdout);
    while (true) {
        std::this_thread::sleep_for(1s);
    }
}

int runStartRecover(const fs::path& dir) {
    const auto res = atugcc::core::configureLogBuffers({
        .mappedDir = dir,
    });
    if (!res) {
        std::printf("FAIL configure\n");
        std::fflush(stdout);
        return 1;
    }

    Logger log(makeConfig(dir));
    log.log(Level::Info, "P0 L0");
    return 0;
}

int runRecover(const fs::path& dir) {
    const auto res = atugcc::core::recoverLogMaps(dir);
    if (!res) {
        const std::string_view err = atugcc::core::to_string(res.error());
        std::printf("ERROR %.*s\n", static_cast<int>(err.size()), err.data());
        return 1;
    }
    for (const auto& r : *res) {
        std::printf("RECOVERED %s %u %llu %llu %u %d\n",
                    r.recoveredFile.string().c_str(),
                    static_cast<unsigned int>(r.pid),
                    static_cast<unsigned long long>(r.undeliveredLines),
                    static_cast<unsigned long long>(r.deliveredLines),
                    static_cast<unsigned int>(r.skippedBuffers),
                    r.crashHandlerRan ? 1 : 0);
    }
    return 0;
}

int runLive(const fs::path& dir) {
    const auto res = atugcc::core::configureLogBuffers({
        .mappedDir = dir,
    });
    if (!res) {
        std::printf("FAIL configure\n");
        std::fflush(stdout);
        return 1;
    }

    Logger log(makeConfig(dir));
    log.log(Level::Info, "P0 L0");
    log.flush();  // readPos settles before READY, so the checker's hash of this map stays stable (AC-3)
    std::printf("READY\n");
    std::fflush(stdout);
    while (true) {
        std::this_thread::sleep_for(1s);
    }
}

int runNormal(const fs::path& dir) {
    const auto res = atugcc::core::configureLogBuffers({
        .mappedDir = dir,
    });
    if (!res) {
        std::printf("FAIL configure\n");
        std::fflush(stdout);
        return 1;
    }
    std::printf("MAP %s\n", detail::logMapPath().string().c_str());
    std::fflush(stdout);

    Logger log(makeConfig(dir));
    for (int i = 0; i < 100; ++i) {
        log.log(Level::Info, "P0 L{}", i);
    }
    return 0;
}

[[noreturn]] void runExit(const fs::path& dir, bool quick) {
    const auto res = atugcc::core::configureLogBuffers({
        .mappedDir = dir,
    });
    if (!res) {
        std::printf("FAIL configure\n");
        std::fflush(stdout);
        std::exit(1);
    }
    std::printf("MAP %s\n", detail::logMapPath().string().c_str());
    std::fflush(stdout);

    auto* log = new Logger(makeConfig(dir));
    for (int i = 0; i < 100; ++i) {
        log->log(Level::Info, "P0 L{}", i);
    }
    if (quick) {
        std::quick_exit(0);
    }
    std::exit(0);
}

[[noreturn]] void runAbort(const fs::path& dir) {
    const auto res = atugcc::core::configureLogBuffers({
        .mappedDir = dir,
    });
    if (!res) {
        std::printf("FAIL configure\n");
        std::fflush(stdout);
        std::exit(1);
    }
    std::printf("MAP %s\n", detail::logMapPath().string().c_str());
    std::fflush(stdout);

    Logger log(makeConfig(dir, true, Delivery::Async));
    for (int i = 0; i < 99; ++i) {
        log.log(Level::Info, "P0 L{}", i);
    }
    Logger syncLog(makeConfig(dir, true, Delivery::Sync));
    syncLog.log(Level::Info, "P0 L99");
    std::abort();
}

[[noreturn]] void runSegv(const fs::path& dir) {
    const auto res = atugcc::core::configureLogBuffers({
        .mappedDir = dir,
    });
    if (!res) {
        std::printf("FAIL configure\n");
        std::fflush(stdout);
        std::exit(1);
    }
    std::printf("MAP %s\n", detail::logMapPath().string().c_str());
    std::fflush(stdout);

    Logger log(makeConfig(dir, true, Delivery::Async));
    for (int i = 0; i < 99; ++i) {
        log.log(Level::Info, "P0 L{}", i);
    }
    Logger syncLog(makeConfig(dir, true, Delivery::Sync));
    syncLog.log(Level::Info, "P0 L99");

    volatile int* p = nullptr;
    *p = 1;
    std::abort();
}

int runConfig(const fs::path& dir) {
    bool allOk = true;

    // 1. mappedBytes 512 KiB -> InvalidArgument
    const auto res1 = atugcc::core::configureLogBuffers({
        .mappedBytes = 512 * 1024,
    });
    if (!res1 && res1.error() == CoreError::InvalidArgument) {
        std::printf("OK mappedBytes\n");
    } else {
        std::printf("FAIL mappedBytes\n");
        allOk = false;
    }

    // 2. mappedDir = <dir>/file.txt/sub with file.txt a regular file -> FileIOFailure
    //    and a Sync line still reaches snapshot()
    const fs::path regularFile = dir / "file.txt";
    {
        std::ofstream out(regularFile);
        out << "regular file placeholder";
    }
    const auto res2 = atugcc::core::configureLogBuffers({
        .mappedDir = regularFile / "sub",
    });
    bool syncOk = false;
    if (!res2 && res2.error() == CoreError::FileIOFailure) {
        Logger::Config syncCfg;
        syncCfg.delivery = Delivery::Sync;
        syncCfg.overflow = OverflowPolicy::Block;
        syncCfg.enableCrashDump = false;
        syncCfg.dumpDir = dir;
        syncCfg.filePath = fs::path{};
        Logger syncLogger(syncCfg);
        syncLogger.log(Level::Info, "after failure");
        const auto snap = syncLogger.snapshot();
        for (const auto& line : snap) {
            if (line.find("after failure") != std::string::npos) {
                syncOk = true;
                break;
            }
        }
    }
    if (syncOk) {
        std::printf("OK fileIOFailure\n");
    } else {
        std::printf("FAIL fileIOFailure\n");
        allOk = false;
    }

    // 3. <dir>/a -> success
    const fs::path dirA = dir / "a";
    const auto res3 = atugcc::core::configureLogBuffers({
        .mappedDir = dirA,
    });
    fs::path mapPathA;
    if (res3.has_value()) {
        mapPathA = detail::logMapPath();
        std::printf("OK dirA\n");
    } else {
        std::printf("FAIL dirA\n");
        allOk = false;
    }

    // 4. <dir>/b -> InvalidArgument (mapPath and dir/a *.logmap unchanged)
    const auto res4 = atugcc::core::configureLogBuffers({
        .mappedDir = dir / "b",
    });
    if (!res4 && res4.error() == CoreError::InvalidArgument &&
        detail::logMapPath() == mapPathA && countLogMapFiles(dirA) == 1) {
        std::printf("OK dirB\n");
    } else {
        std::printf("FAIL dirB\n");
        allOk = false;
    }

    // 5. <dir>/a again -> success (mapPath and dir/a *.logmap unchanged)
    const auto res5 = atugcc::core::configureLogBuffers({
        .mappedDir = dirA,
    });
    if (res5.has_value() && detail::logMapPath() == mapPathA && countLogMapFiles(dirA) == 1) {
        std::printf("OK dirAAgain\n");
    } else {
        std::printf("FAIL dirAAgain\n");
        allOk = false;
    }

    // 6. empty -> success (mapPath and dir/a *.logmap unchanged)
    const auto res6 = atugcc::core::configureLogBuffers({
        .mappedDir = fs::path{},
    });
    if (res6.has_value() && detail::logMapPath() == mapPathA && countLogMapFiles(dirA) == 1) {
        std::printf("OK empty\n");
    } else {
        std::printf("FAIL empty\n");
        allOk = false;
    }

    // 7. logMapActive() true
    if (detail::logMapActive()) {
        std::printf("OK logMapActive\n");
    } else {
        std::printf("FAIL logMapActive\n");
        allOk = false;
    }

    return allOk ? 0 : 1;
}

int runEnv(const fs::path& dir) {
    Logger log(makeConfig(dir));
    log.log(Level::Info, "P0 L0");
    if (detail::isMappedBuffer(&detail::threadBuffer())) {
        std::printf("MAPPED 1\n");
        return 0;
    }
    std::printf("MAPPED 0\n");
    return 1;
}

int runFull(const fs::path& dir) {
    const auto res = atugcc::core::configureLogBuffers({
        .mappedDir = dir,
        .mappedBytes = 1024 * 1024,
    });
    if (!res) {
        std::printf("FAIL configure\n");
        std::fflush(stdout);
        return 1;
    }

    constexpr int kFullThreads = 12;
    constexpr int kFullLines = 1000;
    std::array<bool, kFullThreads> isMapped{};
    std::latch syncLatch(kFullThreads);

    Logger log(makeConfig(dir));

    {
        std::vector<std::jthread> workers;
        workers.reserve(static_cast<std::size_t>(kFullThreads));
        for (int p = 0; p < kFullThreads; ++p) {
            workers.emplace_back([&log, &syncLatch, &isMapped, p] {
                log.log(Level::Info, "P{} L0", p);
                syncLatch.arrive_and_wait();
                for (int i = 1; i < kFullLines; ++i) {
                    log.log(Level::Info, "P{} L{}", p, i);
                }
                isMapped[static_cast<std::size_t>(p)] =
                    detail::isMappedBuffer(&detail::threadBuffer());
            });
        }
        for (auto& w : workers) {
            w.join();
        }
    }

    int mappedCount = 0;
    int heapCount = 0;
    for (const bool m : isMapped) {
        if (m) {
            ++mappedCount;
        } else {
            ++heapCount;
        }
    }
    std::printf("MAPPED %d HEAP %d\n", mappedCount, heapCount);
    return 0;
}

int runThreads(const fs::path& dir) {
    const auto res = atugcc::core::configureLogBuffers({
        .mappedDir = dir,
    });
    if (!res) {
        std::printf("FAIL configure\n");
        std::fflush(stdout);
        return 1;
    }

    constexpr int kRounds = 50;
    constexpr int kThreadsPerRound = 8;
    constexpr int kLinesPerThread = 100;

    Logger log(makeConfig(dir));
    for (int r = 0; r < kRounds; ++r) {
        std::vector<std::jthread> threads;
        threads.reserve(static_cast<std::size_t>(kThreadsPerRound));
        for (int p = 0; p < kThreadsPerRound; ++p) {
            threads.emplace_back([&log, p] {
                for (int i = 0; i < kLinesPerThread; ++i) {
                    log.log(Level::Info, "P{} L{}", p, i);
                }
            });
        }
        for (auto& t : threads) {
            t.join();
        }
    }
    return 0;
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
        std::fprintf(stderr, "usage: log_map_probe <mode> <dir>\n");
        return 2;
    }
    const std::string_view mode = argv[1];
    const fs::path dir = argv[2];
    std::error_code ec;
    fs::create_directories(dir, ec);

    if (mode == "killmap") return runKillMap(dir);
    if (mode == "startrecover") return runStartRecover(dir);
    if (mode == "recover") return runRecover(dir);
    if (mode == "live") return runLive(dir);
    if (mode == "normal") return runNormal(dir);
    if (mode == "exit") runExit(dir, false);
    if (mode == "quickexit") runExit(dir, true);
    if (mode == "abort") runAbort(dir);
    if (mode == "segv") runSegv(dir);
    if (mode == "config") return runConfig(dir);
    if (mode == "env") return runEnv(dir);
    if (mode == "full") return runFull(dir);
    if (mode == "threads") return runThreads(dir);

    std::fprintf(stderr, "unknown mode: %.*s\n", static_cast<int>(mode.size()), mode.data());
    return 2;
}
