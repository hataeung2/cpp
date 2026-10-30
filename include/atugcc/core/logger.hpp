#pragma once

#include <concepts>
#include <cstddef>
#include <filesystem>
#include <format>
#include <mutex>
#include <ostream>
#include <source_location>
#include <string>
#include <string_view>
#include <syncstream>
#include <type_traits>
#include <utility>
#include <vector>

#include "atugcc/core/error.hpp"
#include "atugcc/core/memory_dump.hpp"
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
 * @brief Thread-safe logging facade with crash dump support.
 *
 * Contract:
 * - Every public member function may be called from several threads at once on the same Logger.
 * - One Logger per feature is the recommended way to separate settings (live output, history size,
 *   dump() directory). There is no level filter yet.
 * - The crash dump target is prepared once per process and the first Logger (or MemoryDump)
 *   that prepares it decides its directory.
 * - dump() writes to this Logger's own dumpDir.
 */
class Logger {
public:
    struct Config {
        std::size_t bufferCapacity = kDefaultBlockCount;
        std::ostream* liveOutput = nullptr;
        std::filesystem::path dumpDir = "log";
        bool enableCrashDump = true;
    };

    explicit Logger();
    explicit Logger(Config cfg);
    ~Logger() = default;

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

        {
            std::scoped_lock lock(mutex_);
            history_[history_head_] = line;
            history_head_ = (history_head_ + 1) % cfg_.bufferCapacity;
            if (history_count_ < cfg_.bufferCapacity) {
                ++history_count_;
            }
        }

        DbgBuf::log(line, lv);

        if (cfg_.liveOutput != nullptr) {
            std::osyncstream(*cfg_.liveOutput) << line << '\n' << std::flush;
        }
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

    [[nodiscard]] std::vector<std::string> snapshot() const;
    [[nodiscard]] Result dump() const;

    [[nodiscard]] static Logger& global() noexcept;

private:
    Config cfg_;
    mutable std::mutex mutex_;
    std::vector<std::string> history_;
    std::size_t history_head_ = 0;
    std::size_t history_count_ = 0;
};

} // namespace atugcc::core

#ifndef ATUGCC_LOG
#define ATUGCC_LOG(...) ::atugcc::core::Logger::global().log(__VA_ARGS__)
#endif
