#include "atugcc/core/logger.hpp"

#include <utility>

namespace atugcc::core {

Logger::Logger(Config cfg)
    : cfg_(std::move(cfg)) {
    if (0 == cfg_.bufferCapacity) {
        cfg_.bufferCapacity = 1;
    }
    history_.reserve(cfg_.bufferCapacity);
}

std::vector<std::string> Logger::snapshot() const {
    std::scoped_lock lock(mutex_);
    return history_;
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
