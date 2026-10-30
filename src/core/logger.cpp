#include "atugcc/core/logger.hpp"

#include <cstdio>

#include <utility>
#include <vector>

#include "atugcc/core/detail/log_service.hpp"
#include "atugcc/core/memory_dump.hpp"

namespace atugcc::core {

Logger::Logger()
    : Logger(Config{}) {
}

Logger::Logger(Config cfg)
    : cfg_(std::move(cfg)) {
    if (0 == cfg_.bufferCapacity) {
        cfg_.bufferCapacity = 1;
    }
    sinks_.historyCapacity = cfg_.bufferCapacity;
    sinks_.liveOutput = cfg_.liveOutput;
    sinks_.filePath = cfg_.filePath;
    sinks_.durability = cfg_.durability;
    id_ = detail::LogService::instance().registerLogger(sinks_);
    if (id_ == 0) {
        // No free Logger id (65,535 live Loggers): this Logger's lines reach no sink. Say so once;
        // log() counts them in droppedCount() (spec 010-09 Assumption 2: losses are visible).
        std::fputs("[atugcc] Logger registration failed: no free id, lines of this Logger are dropped\n", stderr);
    }
    if (cfg_.enableCrashDump) {
        ignoreResult(alog::MemoryDump::ensurePrepared(cfg_.dumpDir));
    }
}

Logger::~Logger() {
    flush();
    detail::LogService::instance().unregisterLogger(id_);
}

void Logger::flush() {
    detail::LogService::instance().flush();
}

std::uint64_t Logger::droppedCount() const noexcept {
    return sinks_.dropped.load(std::memory_order_relaxed);
}

std::vector<std::string> Logger::snapshot() const {
    detail::LogService::instance().flush();
    return sinks_.copyHistory();
}

Result Logger::dump() const {
    if (!cfg_.enableCrashDump) {
        return {};
    }
    return alog::MemoryDump::dump(cfg_.dumpDir);
}

Logger& Logger::global() noexcept {
    static Logger instance{};
    return instance;
}

} // namespace atugcc::core
