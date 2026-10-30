#include "atugcc/core/detail/log_service.hpp"

#include <algorithm>
#include <atomic>
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <exception>
#include <format>
#include <string>
#include <string_view>
#include <thread>
#include <unordered_map>
#include <utility>
#include <vector>

#include "atugcc/core/detail/log_registry.hpp"
#include "atugcc/core/detail/thread_log_buffer.hpp"
#include "atugcc/core/memory_dump.hpp"
#include "log_file.hpp"

namespace atugcc::core::detail {

namespace {

// The handler that was installed before ours. On MSVC the terminate handler is per thread, so every
// thread that logs installs ours (installTerminateHandlerForThisThread) and remembers its own previous
// one; elsewhere the handler is process-wide and the first previous handler is the one to chain.
std::atomic<std::terminate_handler> gPreviousTerminate{nullptr};
thread_local std::terminate_handler tPreviousTerminate = nullptr;

void logServiceTerminateHandler() noexcept {
    static_cast<void>(LogService::instance().emergencyFlush(std::chrono::milliseconds{200}));
    if (!alog::MemoryDump::preparedPath().empty() ||
        alog::MemoryDump::getDumpFd() >= 0 ||
        alog::MemoryDump::getDumpHandle() != nullptr) {
        alog::MemoryDump::writeDumpNow("terminate", 0);
    }
    const std::terminate_handler previous =
        tPreviousTerminate != nullptr ? tPreviousTerminate : gPreviousTerminate.load();
    if (previous != nullptr) {
        previous();
    } else {
        std::abort();
    }
}

} // namespace

void installTerminateHandlerForThisThread() noexcept {
    if (std::get_terminate() == &logServiceTerminateHandler) {
        return;  // already ours (always the case after the first call where the handler is global)
    }
    const std::terminate_handler previous = std::set_terminate(&logServiceTerminateHandler);
    std::terminate_handler none = nullptr;
    if (previous != &logServiceTerminateHandler) {
        tPreviousTerminate = previous;
        gPreviousTerminate.compare_exchange_strong(none, previous);
    }
}

namespace {

void pushHistory(LoggerSinks& sinks, std::string_view line) {
    if (sinks.historyCapacity == 0) {
        return;
    }
    std::lock_guard lock(sinks.historyMutex);
    if (sinks.history.size() < sinks.historyCapacity) {
        sinks.history.emplace_back(line);
        sinks.historyCount = sinks.history.size();
    } else {
        sinks.history[sinks.historyHead] = std::string(line);
        sinks.historyHead = (sinks.historyHead + 1) % sinks.historyCapacity;
        sinks.historyCount = sinks.historyCapacity;
    }
}

struct WallBreakdown {
    int year;
    unsigned month;
    unsigned day;
    long long hours;
    long long minutes;
    long long seconds;
    long long micros;
};

WallBreakdown breakDownWallTime(std::chrono::system_clock::time_point systemBase,
                              std::uint64_t steadyBaseNs,
                              std::uint64_t timeNs) {
    const auto baseUs = std::chrono::duration_cast<std::chrono::microseconds>(
        systemBase.time_since_epoch()).count();
    long long totalUs = 0;
    if (timeNs >= steadyBaseNs) {
        const auto deltaUs = static_cast<long long>((timeNs - steadyBaseNs) / 1000);
        totalUs = baseUs + deltaUs;
    } else {
        const auto deltaUs = static_cast<long long>((steadyBaseNs - timeNs) / 1000);
        totalUs = baseUs - deltaUs;
    }

    const std::chrono::sys_time<std::chrono::microseconds> wallTime{std::chrono::microseconds{totalUs}};
    const std::chrono::sys_days days = std::chrono::floor<std::chrono::days>(wallTime);
    const std::chrono::year_month_day ymd{days};
    const auto timeOfDay = wallTime - days;
    const auto hours = std::chrono::floor<std::chrono::hours>(timeOfDay);
    const auto mins = std::chrono::floor<std::chrono::minutes>(timeOfDay - hours);
    const auto secs = std::chrono::floor<std::chrono::seconds>(timeOfDay - hours - mins);
    const auto micros = std::chrono::duration_cast<std::chrono::microseconds>(timeOfDay - hours - mins - secs);

    return WallBreakdown{
        .year = static_cast<int>(ymd.year()),
        .month = static_cast<unsigned>(ymd.month()),
        .day = static_cast<unsigned>(ymd.day()),
        .hours = hours.count(),
        .minutes = mins.count(),
        .seconds = secs.count(),
        .micros = micros.count(),
    };
}

std::string formatLivePrefix(const WallBreakdown& wb) {
    return std::format("{:02}:{:02}:{:02}.{:06} ", wb.hours, wb.minutes, wb.seconds, wb.micros);
}

std::string formatFilePrefix(const WallBreakdown& wb, std::uint32_t threadNo) {
    return std::format("{:04}-{:02}-{:02}T{:02}:{:02}:{:02}.{:06}Z T{} ",
                       wb.year, wb.month, wb.day,
                       wb.hours, wb.minutes, wb.seconds, wb.micros,
                       threadNo);
}

struct RawRecord {
    std::uint64_t timeNs{0};
    std::uint32_t threadSeq{0};
    std::uint32_t threadNo{0};
    std::uint16_t loggerId{0};
    Level level{Level::Debug};
    std::string text;
};

static thread_local bool tServiceMutexHeld = false;

void recordFileError(LoggerSinks& sinks) noexcept {
    if (sinks.fileErrors.fetch_add(1, std::memory_order_relaxed) == 0) {
        const std::string msg = std::format(
            "[atugcc] log file error: {} (lines may be missing from the file)\n",
            sinks.filePath.string());
        std::fputs(msg.c_str(), stderr);
    }
}

struct ServiceLock {
    LogService& svc;
    bool locked{false};

    explicit ServiceLock(LogService& s) noexcept : svc(s) {
        svc.lockService();
        locked = true;
    }

    ~ServiceLock() noexcept {
        if (locked) {
            svc.unlockService();
        }
    }

    ServiceLock(const ServiceLock&) = delete;
    ServiceLock& operator=(const ServiceLock&) = delete;
};

} // namespace

LoggerSinks::LoggerSinks() = default;
LoggerSinks::~LoggerSinks() = default;

std::vector<std::string> LoggerSinks::copyHistory() const {
    std::lock_guard lock(historyMutex);
    std::vector<std::string> result;
    if (history.empty() || historyCount == 0) {
        return result;
    }
    result.reserve(historyCount);
    if (history.size() < historyCapacity) {
        for (std::size_t i = 0; i < historyCount; ++i) {
            result.push_back(history[i]);
        }
    } else {
        for (std::size_t i = 0; i < historyCapacity; ++i) {
            std::size_t idx = (historyHead + i) % historyCapacity;
            result.push_back(history[idx]);
        }
    }
    return result;
}

LogService& LogService::instance() {
    static LogService* ptr = new LogService();
    return *ptr;
}

void LogService::lockService() noexcept {
    service_mutex_.lock();
    tServiceMutexHeld = true;
}

void LogService::unlockService() noexcept {
    tServiceMutexHeld = false;
    service_mutex_.unlock();
}

bool LogService::tryLockService() noexcept {
    if (tServiceMutexHeld) {
        return false;
    }
    if (service_mutex_.try_lock()) {
        tServiceMutexHeld = true;
        return true;
    }
    return false;
}

bool LogService::tryLockService(std::chrono::steady_clock::time_point deadline) noexcept {
    if (tServiceMutexHeld) {
        return false;
    }
    if (service_mutex_.try_lock_until(deadline)) {
        tServiceMutexHeld = true;
        return true;
    }
    return false;
}

LogService::LogService() {
    system_base_ = std::chrono::system_clock::now();
    steady_base_ns_ = static_cast<std::uint64_t>(
        std::chrono::duration_cast<std::chrono::nanoseconds>(
            std::chrono::steady_clock::now().time_since_epoch()).count());

    sinks_by_id_.resize(1, nullptr);

    installTerminateHandlerForThisThread();

    std::atexit([]() noexcept {
        LogService::instance().shutdown();
    });
    std::at_quick_exit([]() noexcept {
        LogService::instance().shutdown();
    });

    consumer_thread_ = std::jthread([this](std::stop_token st) {
        consumerLoop(st);
    });
    consumer_thread_id_ = consumer_thread_.get_id();
}

LogService::~LogService() {
    shutdown();
}

std::uint16_t LogService::registerLogger(LoggerSinks& sinks) {
    ServiceLock lock(*this);
    std::uint16_t allocatedId = 0;
    for (std::size_t i = 1; i < sinks_by_id_.size(); ++i) {
        if (sinks_by_id_[i] == nullptr) {
            allocatedId = static_cast<std::uint16_t>(i);
            break;
        }
    }
    if (allocatedId == 0) {
        if (sinks_by_id_.size() <= 65535) {
            allocatedId = static_cast<std::uint16_t>(sinks_by_id_.size());
            sinks_by_id_.push_back(&sinks);
        } else {
            return 0;
        }
    } else {
        sinks_by_id_[allocatedId] = &sinks;
    }

    sinks.droppedReported = 0;
    sinks.file.reset();
    if (!sinks.filePath.empty()) {
        auto openResult = LogFile::open(sinks.filePath);
        if (openResult.has_value()) {
            sinks.file = std::make_unique<LogFile>(std::move(*openResult));
        } else {
            recordFileError(sinks);
        }
    }

    return allocatedId;
}

void LogService::unregisterLogger(std::uint16_t id) noexcept {
    ServiceLock lock(*this);
    if (id > 0 && id < sinks_by_id_.size()) {
        sinks_by_id_[id] = nullptr;
    }
}

void LogService::submit(std::uint16_t id,
                        LoggerSinks* sinks,
                        Level lv,
                        std::string_view line,
                        Delivery delivery,
                        OverflowPolicy overflow,
                        std::chrono::milliseconds wait) noexcept {
    const auto now = std::chrono::steady_clock::now();
    const auto timeNs = static_cast<std::uint64_t>(
        std::chrono::duration_cast<std::chrono::nanoseconds>(now.time_since_epoch()).count());
    const std::uint32_t threadSeq = nextThreadSeq();
    auto& buf = threadBuffer();
    const bool isEmerg = isEmergencyBuffer(&buf);

    auto recordDropped = [&]() noexcept {
        if (sinks != nullptr) {
            sinks->dropped.fetch_add(1, std::memory_order_relaxed);
        } else {
            dropped_global_.fetch_add(1, std::memory_order_relaxed);
        }
    };

    auto attemptWrite = [&]() noexcept -> int {
        if (isEmerg) {
            if (!tryLockEmergencyBuffer()) {
                return -1;
            }
            const bool ok = buf.tryWrite(timeNs, threadSeq, id, lv, line);
            unlockEmergencyBuffer();
            return ok ? 1 : 0;
        }
        return buf.tryWrite(timeNs, threadSeq, id, lv, line) ? 1 : 0;
    };

    int writeRes = attemptWrite();
    if (writeRes == -1 && overflow == OverflowPolicy::BlockThenDrop) {
        recordDropped();
        return;
    }

    bool written = (writeRes == 1);
    if (!written) {
        wake();
        int yields = 0;
        if (overflow == OverflowPolicy::BlockThenDrop) {
            const auto deadline = std::chrono::steady_clock::now() + wait;
            while (!written) {
                if (std::chrono::steady_clock::now() >= deadline) {
                    recordDropped();
                    return;
                }
                if (stopped()) {
                    if (tryLockService()) {
                        drainLocked();
                        unlockService();
                    }
                }
                if (yields < 3) {
                    std::this_thread::yield();
                    ++yields;
                } else {
                    std::this_thread::sleep_for(std::chrono::microseconds{50});
                }
                writeRes = attemptWrite();
                if (writeRes == 1) {
                    written = true;
                } else if (writeRes == -1) {
                    recordDropped();
                    return;
                }
            }
        } else {
            while (!written) {
                if (stopped()) {
                    if (tryLockService()) {
                        drainLocked();
                        unlockService();
                    }
                }
                if (yields < 3) {
                    std::this_thread::yield();
                    ++yields;
                } else {
                    std::this_thread::sleep_for(std::chrono::microseconds{50});
                }
                writeRes = attemptWrite();
                if (writeRes == 1) {
                    written = true;
                }
            }
        }
    }

    if (lv >= Level::Warn || buf.usedSlots() > (buf.slotCount() / 2)) {
        wake();
    }

    const std::uint64_t endPos = buf.writePos();

    if (stopped()) {
        ServiceLock lock(*this);
        drainLocked();
        return;
    }

    if (delivery == Delivery::Sync) {
        if (std::this_thread::get_id() != consumer_thread_id_) {
            wake();
            std::unique_lock syncLock(sync_mutex_);
            while (buf.readPos() < endPos && !stopped()) {
                sync_cv_.wait_for(syncLock, std::chrono::milliseconds{1});
            }
            if (stopped() && buf.readPos() < endPos) {
                ServiceLock sLock(*this);
                drainLocked();
            }
        }
    }
}

void LogService::drainLocked() {
    const bool flushOrShutdown = (flush_pending_.load(std::memory_order_acquire) > 0) ||
                                 stop_requested_.load(std::memory_order_acquire) ||
                                 stopped_.load(std::memory_order_acquire);
    const auto nowNs = static_cast<std::uint64_t>(
        std::chrono::duration_cast<std::chrono::nanoseconds>(
            std::chrono::steady_clock::now().time_since_epoch()).count());
    const std::uint64_t holdbackLimitNs = (nowNs >= 1'000'000) ? (nowNs - 1'000'000) : 0;

    std::vector<RawRecord> batch;
    std::vector<std::pair<ThreadLogBuffer*, std::uint64_t>> advances;

    forEachBuffer([&](ThreadLogBuffer& buf) {
        const std::uint64_t rPos = buf.readPos();
        const std::uint64_t wPos = buf.writePos();
        if (rPos >= wPos) {
            return;
        }

        std::uint64_t scanPos = rPos;
        std::uint64_t lastTakenEnd = rPos;

        while (scanPos < wPos) {
            const auto& firstHdr = buf.slotHeader(scanPos);
            if ((firstHdr.flags & kSlotFlagFirst) == 0) {
                break;
            }

            if (!flushOrShutdown && firstHdr.timeNs > holdbackLimitNs) {
                break;
            }

            std::uint64_t recEnd = scanPos;
            bool foundLast = false;
            while (recEnd < wPos) {
                const auto& curHdr = buf.slotHeader(recEnd);
                if ((curHdr.flags & kSlotFlagLast) != 0) {
                    foundLast = true;
                    ++recEnd;
                    break;
                }
                ++recEnd;
            }

            if (!foundLast) {
                break;
            }

            RawRecord rec;
            rec.timeNs = firstHdr.timeNs;
            rec.threadSeq = firstHdr.threadSeq;
            rec.threadNo = buf.threadNo();
            rec.loggerId = firstHdr.loggerId;
            rec.level = firstHdr.level;

            std::size_t totalBytes = 0;
            for (std::uint64_t s = scanPos; s < recEnd; ++s) {
                totalBytes += buf.slotHeader(s).len;
            }
            rec.text.reserve(totalBytes);
            for (std::uint64_t s = scanPos; s < recEnd; ++s) {
                const auto& sHdr = buf.slotHeader(s);
                std::string_view p = buf.slotPayload(s);
                if (sHdr.len <= p.size()) {
                    rec.text.append(p.data(), sHdr.len);
                }
            }

            batch.push_back(std::move(rec));
            lastTakenEnd = recEnd;
            scanPos = recEnd;
        }

        if (lastTakenEnd > rPos) {
            advances.emplace_back(&buf, lastTakenEnd);
        }
    });

    std::sort(batch.begin(), batch.end(), [](const RawRecord& a, const RawRecord& b) {
        if (a.timeNs != b.timeNs) {
            return a.timeNs < b.timeNs;
        }
        if (a.threadNo != b.threadNo) {
            return a.threadNo < b.threadNo;
        }
        return a.threadSeq < b.threadSeq;
    });

    std::unordered_map<std::uint16_t, std::vector<const RawRecord*>> recordsByLogger;
    for (const auto& rec : batch) {
        if (rec.loggerId > 0 && rec.loggerId < sinks_by_id_.size() && sinks_by_id_[rec.loggerId] != nullptr) {
            recordsByLogger[rec.loggerId].push_back(&rec);
        }
    }

    for (const auto& [loggerId, recs] : recordsByLogger) {
        LoggerSinks* sinks = sinks_by_id_[loggerId];
        if (sinks == nullptr || recs.empty()) {
            continue;
        }

        std::string liveText;
        std::string fileText;

        const std::uint64_t currentDropped = sinks->dropped.load(std::memory_order_relaxed);
        if (currentDropped > sinks->droppedReported) {
            const std::uint64_t diff = currentDropped - sinks->droppedReported;
            sinks->droppedReported = currentDropped;
            const std::string dropMsg = std::format("[atugcc] dropped {} lines", diff);
            pushHistory(*sinks, dropMsg);

            const RawRecord& firstRec = *recs.front();
            const auto dropWb = breakDownWallTime(system_base_, steady_base_ns_, firstRec.timeNs);
            liveText += formatLivePrefix(dropWb) + dropMsg + '\n';
            fileText += formatFilePrefix(dropWb, firstRec.threadNo) + dropMsg + '\n';
        }

        for (const RawRecord* r : recs) {
            pushHistory(*sinks, r->text);

            const auto wb = breakDownWallTime(system_base_, steady_base_ns_, r->timeNs);
            liveText += formatLivePrefix(wb) + r->text + '\n';
            fileText += formatFilePrefix(wb, r->threadNo) + r->text + '\n';
        }

        if (sinks->liveOutput != nullptr && !liveText.empty()) {
            *sinks->liveOutput << liveText;
            sinks->liveOutput->flush();
        }

        if (sinks->file != nullptr && !fileText.empty()) {
            auto res = sinks->file->write(fileText);
            if (!res.has_value()) {
                recordFileError(*sinks);
            } else if (sinks->durability == Durability::System) {
                auto syncRes = sinks->file->sync();
                if (!syncRes.has_value()) {
                    recordFileError(*sinks);
                }
            }
        }
    }

    for (const auto& [buf, newPos] : advances) {
        buf->advanceRead(newPos);
    }

    sync_cv_.notify_all();
    flush_cv_.notify_all();
}

void LogService::consumerLoop(std::stop_token stopToken) {
    while (!stopToken.stop_requested()) {
        const auto drainInterval = currentLogBufferConfig().drainInterval;
        {
            std::unique_lock lock(wake_mutex_);
            wake_cv_.wait_for(lock, drainInterval, [this, &stopToken]() {
                return stopToken.stop_requested() ||
                       wake_pending_.load(std::memory_order_relaxed) ||
                       (flush_pending_.load(std::memory_order_relaxed) > 0);
            });
            wake_pending_.store(false, std::memory_order_relaxed);
        }
        {
            ServiceLock lock(*this);
            drainLocked();
        }
    }

    {
        ServiceLock lock(*this);
        drainLocked();
    }
}

void LogService::flush() noexcept {
    if (std::this_thread::get_id() == consumer_thread_id_) {
        return;
    }
    if (stopped()) {
        ServiceLock lock(*this);
        drainLocked();
        return;
    }

    std::vector<std::pair<ThreadLogBuffer*, std::uint64_t>> targets;
    forEachBuffer([&targets](ThreadLogBuffer& b) {
        targets.emplace_back(&b, b.writePos());
    });

    flush_pending_.fetch_add(1, std::memory_order_release);
    wake();

    {
        std::unique_lock lock(flush_mutex_);
        while (!stopped()) {
            bool allReached = true;
            for (const auto& [buf, targetPos] : targets) {
                if (buf->readPos() < targetPos) {
                    allReached = false;
                    break;
                }
            }
            if (allReached) {
                break;
            }
            flush_cv_.wait_for(lock, std::chrono::milliseconds{1});
        }
    }

    flush_pending_.fetch_sub(1, std::memory_order_release);

    if (stopped()) {
        ServiceLock lock(*this);
        drainLocked();
    }
}

bool LogService::emergencyFlush(std::chrono::milliseconds timeout) noexcept {
    const auto deadline = std::chrono::steady_clock::now() + timeout;
    if (std::this_thread::get_id() == consumer_thread_id_ || stopped()) {
        if (!tryLockService(deadline)) {
            return false;
        }
        drainLocked();
        unlockService();
        return true;
    }

    std::vector<std::pair<ThreadLogBuffer*, std::uint64_t>> targets;
    forEachBuffer([&targets](ThreadLogBuffer& b) {
        targets.emplace_back(&b, b.writePos());
    });

    flush_pending_.fetch_add(1, std::memory_order_release);
    wake();

    bool allReached = false;
    {
        std::unique_lock lock(flush_mutex_);
        while (true) {
            allReached = true;
            for (const auto& [buf, targetPos] : targets) {
                if (buf->readPos() < targetPos) {
                    allReached = false;
                    break;
                }
            }
            if (allReached) {
                break;
            }
            const auto now = std::chrono::steady_clock::now();
            if (now >= deadline) {
                break;
            }
            const auto remaining = std::chrono::duration_cast<std::chrono::milliseconds>(deadline - now);
            flush_cv_.wait_for(lock, std::min(remaining, std::chrono::milliseconds{1}));
        }
    }

    flush_pending_.fetch_sub(1, std::memory_order_release);

    if (!allReached) {
        if (tryLockService(deadline)) {
            drainLocked();
            unlockService();
            allReached = true;
            for (const auto& [buf, targetPos] : targets) {
                if (buf->readPos() < targetPos) {
                    allReached = false;
                    break;
                }
            }
        }
    }

    return allReached;
}

void LogService::shutdown() noexcept {
    if (shutting_down_.exchange(true, std::memory_order_acq_rel)) {
        return;
    }

    flush();

    stop_requested_.store(true, std::memory_order_release);
    if (consumer_thread_.joinable()) {
        consumer_thread_.request_stop();
        wake();
        consumer_thread_.join();
    }

    stopped_.store(true, std::memory_order_release);

    {
        ServiceLock lock(*this);
        drainLocked();
    }

    sync_cv_.notify_all();
    flush_cv_.notify_all();
}

bool LogService::stopped() const noexcept {
    return stopped_.load(std::memory_order_acquire);
}

void LogService::wake() noexcept {
    wake_pending_.store(true, std::memory_order_release);
    wake_cv_.notify_one();
}

} // namespace atugcc::core::detail
