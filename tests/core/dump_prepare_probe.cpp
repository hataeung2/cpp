/**
 * @file dump_prepare_probe.cpp
 * @brief Crash dump preparation follows the Logger config (spec 010-08 AC-5, AC-6, AC-7)
 *
 * Usage: dump_prepare_probe <mode> <work dir>
 *   off            Loggers with enableCrashDump = false: no directory, no file, no handler.
 *   once           three Loggers and a MemoryDump: one file in the first dumpDir, one descriptor.
 *   replace        an explicit prepare closes the auto-prepared file and removes it while empty.
 *   cleanup        prepares a file and exits normally (CTest fixture setup for check-removed).
 *   check-removed  the file of `cleanup` is gone.
 *   slots          prints the default per-thread log buffer size (ATUGCC_LOG_SLOTS, spec 010-09 AC-6b).
 *
 * The dump target is process-wide, so each check runs in its own process (atugcc_tests has
 * already prepared one by the time any test runs). Exit 0 on success, 1 on a failed check.
 */
#include <cstdint>
#include <cstdio>
#include <filesystem>
#include <string>
#include <string_view>
#include <system_error>

#ifdef __linux__
#include <csignal>
#elif defined(_WIN32)
#include <Windows.h>  // SetUnhandledExceptionFilter (memory_dump.hpp no longer brings it, KI-027)
#endif

#include "atugcc/core/log_buffer_config.hpp"
#include "atugcc/core/logger.hpp"
#include "atugcc/core/memory_dump.hpp"

namespace fs = std::filesystem;
using atugcc::core::Level;
using atugcc::core::Logger;

namespace {

int failures = 0;

void check(bool ok, std::string_view what) {
    std::printf("%s %.*s\n", ok ? "ok  " : "FAIL", static_cast<int>(what.size()), what.data());
    if (!ok) ++failures;
}

Logger::Config config(const fs::path& dumpDir, bool crashDump) {
    return {.bufferCapacity = 8, .liveOutput = nullptr, .dumpDir = dumpDir, .enableCrashDump = crashDump};
}

int dumpFiles(const fs::path& dir) {
    std::error_code ec;
    if (!fs::is_directory(dir, ec)) return 0;
    int n = 0;
    for (const auto& entry : fs::directory_iterator(dir, ec)) {
        if (entry.path().filename().string().starts_with("crash_dump_")) ++n;
    }
    return n;
}

#ifdef __linux__
int openDescriptors() {
    int n = 0;
    std::error_code ec;
    for ([[maybe_unused]] const auto& entry : fs::directory_iterator("/proc/self/fd", ec)) ++n;
    return n;
}
#endif

// The current crash handler as an address. Compared with the value at startup rather than
// with "none": sanitizer runtimes install their own SIGSEGV handler before main().
std::uintptr_t crashHandler() {
#ifdef __linux__
    struct sigaction current{};
    sigaction(SIGSEGV, nullptr, &current);
    return (current.sa_flags & SA_SIGINFO) != 0 ? reinterpret_cast<std::uintptr_t>(current.sa_sigaction)
                                                : reinterpret_cast<std::uintptr_t>(current.sa_handler);
#elif defined(_WIN32)
    const LPTOP_LEVEL_EXCEPTION_FILTER previous = SetUnhandledExceptionFilter(nullptr);
    SetUnhandledExceptionFilter(previous);
    return reinterpret_cast<std::uintptr_t>(previous);
#else
    return 0;
#endif
}

void freshDir(const fs::path& dir) {
    std::error_code ec;
    fs::remove_all(dir, ec);
    fs::create_directories(dir);
    fs::current_path(dir);
}

void modeOff() {
    const std::uintptr_t startup = crashHandler();
    Logger a(config("d_off", false));
    Logger b(config("d_off", false));
    a.log(Level::Info, "a {}", 1);
    b.log(Level::Info, "b {}", 2);
    check(!fs::exists("log"), "no log/ directory");
    check(!fs::exists("d_off"), "no dumpDir directory");
    check(alog::MemoryDump::preparedPath().empty(), "preparedPath() is empty");
    check(crashHandler() == startup, "crash handler unchanged by Loggers with enableCrashDump = false");
}

void modeOnce() {
    const std::uintptr_t startup = crashHandler();
#ifdef __linux__
    const int before = openDescriptors();
#endif
    Logger first(config("d1", true));
    Logger second(config("d2", true));
    Logger third(config("d3", true));
    alog::MemoryDump md;
    first.log(Level::Info, "first");
    check(dumpFiles("d1") == 1, "one dump file in the first dumpDir");
    check(dumpFiles("d2") == 0 && dumpFiles("d3") == 0 && dumpFiles("log") == 0, "no dump file elsewhere");
    check(alog::MemoryDump::preparedPath().parent_path() == fs::path("d1"), "preparedPath() is in d1");
    check(crashHandler() != startup, "crash handler installed");
#ifdef __linux__
    check(openDescriptors() - before == 1, "one descriptor for three Loggers and a MemoryDump");
#endif
}

void modeReplace() {
    Logger logger(config("auto", true));
    const fs::path autoPath = alog::MemoryDump::preparedPath();
    check(!autoPath.empty() && fs::exists(autoPath), "auto-prepared file exists");
    fs::create_directories("explicit");
#ifdef __linux__
    const int before = openDescriptors();
    const auto res = alog::MemoryDump::prepareDumpFile(fs::path("explicit") / "dump.bin");
    check(res.has_value(), "explicit prepare succeeds");
    check(openDescriptors() == before, "the auto-prepared descriptor was closed");
#elif defined(_WIN32)
    const auto res = alog::MemoryDump::prepareDumpFileWin((fs::path("explicit") / "dump.bin").wstring());
    check(res.has_value(), "explicit prepare succeeds");
#endif
    check(!fs::exists(autoPath), "the empty auto-prepared file was removed");
    check(alog::MemoryDump::preparedPath().empty(), "preparedPath() is empty after an explicit prepare");
    check(fs::exists(fs::path("explicit") / "dump.bin"), "the explicit file exists");
}

void modeCleanup() {
    Logger logger(config("dc", true));
    logger.log(Level::Info, "normal exit follows");
    const fs::path p = alog::MemoryDump::preparedPath();
    check(!p.empty() && fs::exists(p) && fs::file_size(p) == 0, "an empty dump file is prepared");
}

void modeCheckRemoved() {
    check(fs::is_directory("dc"), "dumpDir of the cleanup run exists");
    check(dumpFiles("dc") == 0, "no empty dump file left after the normal exit");
}

}  // namespace

int main(int argc, char* argv[]) {
    if (argc != 3) {
        std::fprintf(stderr, "usage: dump_prepare_probe off|once|replace|cleanup|check-removed <work dir>\n");
        return 2;
    }
    const std::string_view mode = argv[1];
    const fs::path work = argv[2];
    if (mode == "slots") {
        std::printf("slots=%zu\n", atugcc::core::currentLogBufferConfig().slotsPerThread);
        return 0;
    }
    if (mode == "check-removed") {
        fs::current_path(work);
        modeCheckRemoved();
    } else {
        freshDir(work);
        if (mode == "off") modeOff();
        else if (mode == "once") modeOnce();
        else if (mode == "replace") modeReplace();
        else if (mode == "cleanup") modeCleanup();
        else {
            std::fprintf(stderr, "unknown mode\n");
            return 2;
        }
    }
    return failures == 0 ? 0 : 1;
}
