#pragma once

#include <filesystem>
#include <format>
#include <cstddef>
#include <mutex>
#include <ostream>
#include <source_location>
#include <string>
#include <utility>
#include <vector>

#include "atugcc/core/error.hpp"
#include "atugcc/core/memory_dump.hpp"
#include "atugcc/core/ring_buffer.hpp"

namespace atugcc::core {

class Logger {
public:
    struct Config {
        std::size_t bufferCapacity = kDefaultBlockCount;
        std::ostream* liveOutput = nullptr;
        std::filesystem::path dumpDir = "log";
        bool enableCrashDump = true;
    };

    explicit Logger(Config cfg = {});
    ~Logger() = default;

    // Default: log at Debug level
    template <typename... Args>
    void log(std::format_string<Args...> fmt, Args&&... args) {
        log(Level::Debug, fmt, std::forward<Args>(args)...);
    }

    // Log with explicit Level (uses current source location)
    template <typename... Args>
    void log(Level lv, std::format_string<Args...> fmt, Args&&... args) {
        log(std::source_location::current(), lv, fmt, std::forward<Args>(args)...);
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
            history_.push_back(line);
            if (history_.size() > cfg_.bufferCapacity) {
                const auto overflow = history_.size() - cfg_.bufferCapacity;
                history_.erase(history_.begin(), history_.begin() + static_cast<std::ptrdiff_t>(overflow));
            }
        }

        m_buffer.write(line, lv);
        DbgBuf::log(line, lv);

        if (cfg_.liveOutput != nullptr) {
            (*cfg_.liveOutput) << line << '\n';
            cfg_.liveOutput->flush();
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
    mutable RingBuffer<> m_buffer;
    alog::MemoryDump m_dump;
    mutable std::mutex mutex_;
    mutable std::vector<std::string> history_;
};

} // namespace atugcc::core

#ifndef ATUGCC_LOG
#define ATUGCC_LOG(...) ::atugcc::core::Logger::global().log(__VA_ARGS__)
#endif
