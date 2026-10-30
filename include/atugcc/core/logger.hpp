#pragma once

#include <chrono>
#include <concepts>
#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <format>
#include <ostream>
#include <source_location>
#include <string>
#include <string_view>
#include <type_traits>
#include <utility>
#include <vector>

#include "atugcc/core/detail/log_service.hpp"
#include "atugcc/core/error.hpp"
#include "atugcc/core/log_buffer_config.hpp"
#include "atugcc/core/ring_buffer.hpp"

namespace atugcc::core {

template <typename... Args>
struct FormatWithLocation {
    std::format_string<Args...> fmt;
    std::source_location loc;

    template <typename S>
        requires std::convertible_to<const S&, std::string_view>
    consteval FormatWithLocation(const S& s,
                                 std::source_location l = std::source_location::current())
        : fmt(s), loc(l) {}

    FormatWithLocation(std::format_string<Args...> f,
                       std::source_location l = std::source_location::current())
        : fmt(f), loc(l) {}
};

/**
 * @brief Thread-safe logging facade backed by lock-free per-thread buffers and a background consumer service.
 *
 * Contract:
 * - Shared across threads: every member function may be called concurrently on the same Logger instance.
 * - No lock on the hot path: log() formats lines outside any lock and writes directly to calling thread's SPSC buffer.
 * - Delivery modes:
 *     - Delivery::Async (default): enqueues record in thread buffer and returns immediately.
 *     - Delivery::Sync: waits until the background consumer delivers the record to all configured sinks.
 * - Overflow policies:
 *     - OverflowPolicy::BlockThenDrop (default): waits up to overflowWait before dropping; dropped lines are reported
 *       by a marker line ("[atugcc] dropped N lines") upon subsequent delivery and via droppedCount().
 *     - OverflowPolicy::Block: blocks indefinitely until buffer space becomes available.
 * - Signal safety & process constraints:
 *     - Do not call log() from a signal handler (log formatting and thread buffer initialization are not async-signal-safe).
 *     - fork() and _exit are not covered (background consumer and unflushed memory buffers do not survive).
 *
 * Preservation Guarantees (Spec 010-09 §2.4):
 * - Clean exit (main return, exit, quick_exit): all lines delivered to file sink.
 * - Thread termination: all lines delivered; retired thread buffer preserved for crash dump.
 * - Logger destruction: all lines for that Logger delivered before destruction completes.
 * - Unhandled exception / std::terminate: lines delivered within 200 ms; crash dump captures recent 512 slots/thd.
 * - abort, assert, SIGSEGV, SIGBUS, SIGFPE, SIGILL, Windows SEH: lines written before crash; crash dump
 *   captures recent 512 slots/thd.
 * - Stack overflow: lines written before crash; crash dump captures recent 512 slots/thd.
 * - Buffer overflow (BlockThenDrop): dropped lines reported by marker line and droppedCount().
 * - Log file write errors: reported once on stderr per Logger; the file may miss lines.
 * ("512 slots" is the default; configureLogBuffers() changes it.)
 * - SIGKILL, TerminateProcess, OOM killer: only lines written before crash (within drain interval) survive; no dump.
 * - OS crash, power loss: lines written under Durability::System survive; no dump.
 * - _exit, fork child: not covered.
 */
class Logger {
public:
    struct Config {
        std::size_t bufferCapacity = kDefaultBlockCount;
        std::ostream* liveOutput = nullptr;
        std::filesystem::path dumpDir = "log";
        bool enableCrashDump = true;
        std::filesystem::path filePath{};
        Delivery delivery = Delivery::Async;
        OverflowPolicy overflow = OverflowPolicy::BlockThenDrop;
        std::chrono::milliseconds overflowWait{100};
        Durability durability = Durability::Process;
    };

    explicit Logger();
    explicit Logger(Config cfg);
    ~Logger();

    Logger(const Logger&) = delete;
    Logger& operator=(const Logger&) = delete;
    Logger(Logger&&) = delete;
    Logger& operator=(Logger&&) = delete;

    // Default: log at Debug level
    template <typename... Args>
    void log(FormatWithLocation<std::type_identity_t<Args>...> fmt, Args&&... args) {
        log(fmt.loc, Level::Debug, fmt.fmt, std::forward<Args>(args)...);
    }

    // Log with explicit Level
    template <typename... Args>
    void log(Level lv, FormatWithLocation<std::type_identity_t<Args>...> fmt, Args&&... args) {
        log(fmt.loc, lv, fmt.fmt, std::forward<Args>(args)...);
    }

    // Primary implementation: explicit source location + level
    template <typename... Args>
    void log(std::source_location loc,
             Level lv,
             std::format_string<Args...> fmt,
             Args&&... args) {
        const std::string payload = std::format(fmt, std::forward<Args>(args)...);
        const std::string line = std::format("[{}] [{}:{} {}] {}",
                                             levelName(lv),
                                             loc.file_name(),
                                             loc.line(),
                                             loc.function_name(),
                                             payload);

        if (id_ == 0) {  // registration failed (see the constructor)
            sinks_.dropped.fetch_add(1, std::memory_order_relaxed);
            return;
        }
        detail::LogService::instance().submit(id_,
                                              &sinks_,
                                              lv,
                                              line,
                                              cfg_.delivery,
                                              cfg_.overflow,
                                              cfg_.overflowWait);
    }

    // Helper to convert Level to human-readable name
    static constexpr const char* levelName(Level lv) noexcept {
        switch (lv) {
            case Level::Debug: return "DEBUG";
            case Level::Info:  return "INFO";
            case Level::Warn:  return "WARN";
            case Level::Error: return "ERROR";
        }
        return "UNKNOWN";
    }

    void flush();  // waits for every line written before the call, by any Logger
    [[nodiscard]] std::uint64_t droppedCount() const noexcept;
    [[nodiscard]] std::vector<std::string> snapshot() const;
    [[nodiscard]] Result dump() const;

    [[nodiscard]] static Logger& global() noexcept;

private:
    Config cfg_;
    detail::LoggerSinks sinks_;
    std::uint16_t id_ = 0;
};

} // namespace atugcc::core

#ifndef ATUGCC_LOG
#define ATUGCC_LOG(...) ::atugcc::core::Logger::global().log(__VA_ARGS__)
#endif
