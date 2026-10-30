#include "atugcc/core/logger.hpp"
#include "atugcc/core/memory_dump.hpp"

#include <utility>
#include <vector>

namespace atugcc::core {

Logger::Logger()
    : Logger(Config{}) {
}

Logger::Logger(Config cfg)
    : cfg_(std::move(cfg)) {
    if (0 == cfg_.bufferCapacity) {
        cfg_.bufferCapacity = 1;
    }
    history_.resize(cfg_.bufferCapacity);
    if (cfg_.enableCrashDump) {
        ignoreResult(alog::MemoryDump::ensurePrepared(cfg_.dumpDir));
    }
}

std::vector<std::string> Logger::snapshot() const {
    std::scoped_lock lock(mutex_);
    std::vector<std::string> result;
    result.reserve(history_count_);
    const std::size_t start = (history_count_ < cfg_.bufferCapacity)
        ? 0
        : history_head_;
    for (std::size_t i = 0; i < history_count_; ++i) {
        result.push_back(history_[(start + i) % cfg_.bufferCapacity]);
    }
    return result;
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
