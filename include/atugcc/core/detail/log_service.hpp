#pragma once

/**
 * @file log_service.hpp
 * @brief Background log consumer service, logger registry, and sink dispatch (Design D3).
 *
 * Thread Model:
 *   - Producers:
 *       Any thread may call LogService::submit() concurrently. Lines are formatted
 *       at the caller site (outside any lock) and written directly into the calling
 *       thread's lock-free SPSC buffer (ThreadLogBuffer).
 *   - Consumer:
 *       A single background thread (std::jthread) drains all registered thread buffers
 *       periodically (drainInterval) or when explicitly awakened (wake()). Drained records
 *       are ordered chronologically by (timeNs, threadNo, threadSeq) and dispatched to
 *       the registered sinks of each logger under the service mutex.
 *   - Mutex Scopes:
 *       serviceMutex_: guards the logger registry (sinksById_), logger registration and
 *       unregistration, consumer-side sink state (file, liveOutput, dropped counts),
 *       and batch dispatch.
 *       historyMutex: per-LoggerSinks mutex guarding copyHistory() and history ring buffer
 *       insertions, allowing lock-free producer logging while supporting concurrent snapshots.
 *
 * Shutdown Order:
 *   - Normal Termination:
 *       Handlers registered via std::atexit and std::at_quick_exit invoke shutdown().
 *       shutdown() flushes all thread buffers, requests consumer stop, joins the consumer
 *       thread, marks the service stopped, and executes a final inline drain.
 *   - Post-Shutdown Logging:
 *       Any submit() or flush() call after stopped() is processed inline on the calling
 *       thread under serviceMutex_, ensuring no log records are lost during process exit.
 *   - Termination / Crash:
 *       A std::set_terminate handler chains the previous handler, performs emergencyFlush(200ms),
 *       writes a crash dump if prepared via alog::MemoryDump::writeDumpNow("terminate", 0),
 *       and delegates to the previous handler or std::abort().
 *
 * Preservation Guarantees (Spec 010-09 §2.4):
 *   +---------------------------------------+-----------------------------+-----------------------+
 *   | Scenario                              | File Sink (if enabled)      | Crash Dump            |
 *   +---------------------------------------+-----------------------------+-----------------------+
 *   | Clean exit (main return, exit, quick) | All lines                   | - (clean exit)        |
 *   | Thread termination                    | All lines (reused after)    | Retired buffer kept   |
 *   | Logger destruction                    | All lines for that Logger   | -                     |
 *   | Unhandled exception / std::terminate  | Delivered within 200 ms     | Recent 512 slots/thd  |
 *   | abort, assert, SIGSEGV, Windows SEH   | Lines written before crash  | Recent 512 slots/thd  |
 *   | Stack overflow                        | Lines written before crash  | Recent 512 slots/thd  |
 *   | Buffer overflow (BlockThenDrop)       | Dropped marker line emitted | - (droppedCount)      |
 *   | SIGKILL, TerminateProcess, OOM killer | Lines written before crash  | None                  |
 *   | Power loss, OS crash                  | System durability: flushed  | None                  |
 *   +---------------------------------------+-----------------------------+-----------------------+
 */

#include <atomic>
#include <chrono>
#include <condition_variable>
#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <memory>
#include <mutex>
#include <ostream>
#include <string>
#include <string_view>
#include <thread>
#include <vector>

#include "atugcc/core/log_buffer_config.hpp"
#include "atugcc/core/ring_buffer.hpp"

namespace atugcc::core::detail {

class LogFile;

/**
 * @brief Sink configuration and consumer state owned by a Logger instance.
 */
struct LoggerSinks {            // owned by a Logger, read by the consumer under the service mutex
    std::size_t historyCapacity = 256;
    std::ostream* liveOutput = nullptr;
    std::filesystem::path filePath{};
    Durability durability = Durability::Process;
    std::atomic<std::uint64_t> dropped{0};
    std::atomic<std::uint64_t> fileErrors{0};
    // consumer-side state (touched only by the consumer, under the service mutex):
    std::uint64_t droppedReported = 0;
    std::unique_ptr<LogFile> file;    // opened by registerLogger when filePath is set
    // history ring, guarded by historyMutex
    mutable std::mutex historyMutex;
    std::vector<std::string> history;
    std::size_t historyHead = 0;
    std::size_t historyCount = 0;
    [[nodiscard]] std::vector<std::string> copyHistory() const;   // oldest first

    LoggerSinks();
    ~LoggerSinks();

    LoggerSinks(const LoggerSinks&) = delete;
    LoggerSinks& operator=(const LoggerSinks&) = delete;
    LoggerSinks(LoggerSinks&&) = delete;
    LoggerSinks& operator=(LoggerSinks&&) = delete;
};

/**
 * @brief Singleton consumer service managing the background log drain thread.
 */
class LogService {
public:
    [[nodiscard]] static LogService& instance();

    LogService(const LogService&) = delete;
    LogService& operator=(const LogService&) = delete;
    LogService(LogService&&) = delete;
    LogService& operator=(LogService&&) = delete;

    [[nodiscard]] std::uint16_t registerLogger(LoggerSinks& sinks);   // 1..65535, 0 = no free id
    void unregisterLogger(std::uint16_t id) noexcept;                  // caller flushed first
    void submit(std::uint16_t id, LoggerSinks* sinks, Level lv, std::string_view line,
                Delivery delivery, OverflowPolicy overflow, std::chrono::milliseconds wait) noexcept;
    void flush() noexcept;
    [[nodiscard]] bool emergencyFlush(std::chrono::milliseconds timeout) noexcept;  // true = all delivered
    void shutdown() noexcept;
    [[nodiscard]] bool stopped() const noexcept;
    void wake() noexcept;

    // Internal: the service mutex, used by the RAII lock helper in log_service.cpp (which lives in
    // an unnamed namespace and so cannot be named as a friend here). Not for Logger code.
    void lockService() noexcept;
    void unlockService() noexcept;
    [[nodiscard]] bool tryLockService() noexcept;
    [[nodiscard]] bool tryLockService(std::chrono::steady_clock::time_point deadline) noexcept;

private:
    LogService();
    ~LogService();

    void consumerLoop(std::stop_token stopToken);
    void drainLocked();

    std::jthread consumer_thread_;
    std::thread::id consumer_thread_id_{};

    std::timed_mutex service_mutex_;

    std::mutex wake_mutex_;
    std::condition_variable wake_cv_;
    std::atomic<bool> wake_pending_{false};

    std::mutex sync_mutex_;
    std::condition_variable sync_cv_;

    std::mutex flush_mutex_;
    std::condition_variable flush_cv_;
    std::atomic<std::size_t> flush_pending_{0};

    std::mutex space_mutex_;
    std::condition_variable space_cv_;
    std::uint64_t space_epoch_{0};

    std::atomic<bool> stop_requested_{false};
    std::atomic<bool> stopped_{false};
    std::atomic<bool> shutting_down_{false};

    std::atomic<std::uint64_t> dropped_global_{0};
    std::vector<LoggerSinks*> sinks_by_id_;

    std::chrono::system_clock::time_point system_base_{};
    std::uint64_t steady_base_ns_{0};
};

} // namespace atugcc::core::detail
