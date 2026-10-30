#pragma once
/**
 * @file ring_buffer.hpp
 * @brief Thread-safe-per-thread fixed-block ring buffer for the atugcc logging system.
 *
 * Design:
 *   - Each thread owns one RingBuffer<> (thread_local, no-lock writes).
 *   - Block layout: [2B header][125B payload][1B sentinel '\0'] = 128 bytes.
 *   - Header bits: [15:14]=Level  [13]=Continuation  [12:0]=payload len (max 125).
 *   - Messages longer than kPayloadSize bytes are split across continuation blocks.
 *   - Eviction policy: when write catches read, read_idx is advanced past the
 *     incoming write range so the newest blocks are always preserved.
 *   - A plain single-thread container: write() and read() are called by the owning
 *     thread. The logging system's per-thread buffers are detail::ThreadLogBuffer
 *     (spec 010-09); DbgBuf below writes into those.
 *
 * @author atugcc
 */

#include <atomic>
#include <concepts>
#include <cstdint>
#include <cstring>
#include <optional>
#include <string>
#include <string_view>

#include "atugcc/core/error.hpp"

namespace atugcc::core {

// ─── Log Level ────────────────────────────────────────────────────────────────
enum class Level : uint8_t {
    Debug = 0b00,
    Info  = 0b01,
    Warn  = 0b10,
    Error = 0b11,
};

// ─── Block Layout Constants ───────────────────────────────────────────────────
inline constexpr std::size_t kDefaultBlockSize  = 128;
inline constexpr std::size_t kDefaultBlockCount = 256; // MUST be power-of-two

// Header bit masks (uint16_t)
inline constexpr uint16_t kLevelShift = 14;
inline constexpr uint16_t kLevelMask  = 0xC000u; // bit[15:14]
inline constexpr uint16_t kContFlag   = 0x2000u; // bit[13]
inline constexpr uint16_t kLenMask    = 0x1FFFu; // bit[12:0]  (max 8191; actual max=125)

// ─── Header helpers ──────────────────────────────────────────────────────────
[[nodiscard]] inline constexpr uint16_t
encodeHeader(Level lv, bool cont, uint16_t len) noexcept {
    return static_cast<uint16_t>(
        (static_cast<uint16_t>(lv) << kLevelShift)
      | (cont ? kContFlag : 0u)
      | (len & kLenMask)
    );
}

[[nodiscard]] inline constexpr Level    decodeLevel(uint16_t h) noexcept {
    return static_cast<Level>((h & kLevelMask) >> kLevelShift);
}
[[nodiscard]] inline constexpr bool     decodeCont (uint16_t h) noexcept { return (h & kContFlag) != 0; }
[[nodiscard]] inline constexpr uint16_t decodeLen  (uint16_t h) noexcept { return h & kLenMask; }

#ifdef _MSC_VER
#pragma warning(push)
#pragma warning(disable: 4324) // structure was padded due to alignment specifier
#endif

// ─── RingBuffer ───────────────────────────────────────────────────────────────
/**
 * Fixed-block single-thread ring buffer.
 *
 * @tparam BlockSize   Bytes per block (header + payload + sentinel). Default 128.
 * @tparam BlockCount  Number of blocks. MUST be a power of two. Default 256.
 */
template <std::size_t BlockSize  = kDefaultBlockSize,
          std::size_t BlockCount = kDefaultBlockCount>
    requires (BlockCount > 1 && (BlockCount & (BlockCount - 1)) == 0)
          && (BlockSize >= 4) // 2B header + 1B payload + 1B sentinel minimum
class RingBuffer {
public:
    // ── Public layout constants ──────────────────────────────────────────────
    static constexpr std::size_t kHeaderBytes  = 2;
    static constexpr std::size_t kSentinelByte = 1;
    static constexpr std::size_t kPayloadBytes = BlockSize - kHeaderBytes - kSentinelByte;
    static constexpr uint32_t    kMask         = static_cast<uint32_t>(BlockCount - 1);

    // ── ReadResult returned by read() ────────────────────────────────────────
    struct ReadResult {
        std::string_view payload;        ///< Points directly into buf_[]; valid until next write.
        Level            level;
        bool             isContinuation; ///< True if this block continues the previous message.
    };

    // ── Construction ─────────────────────────────────────────────────────────
    RingBuffer() noexcept {
        std::memset(buf_, 0, sizeof(buf_));
    }
    ~RingBuffer() = default;

    // Non-copyable, non-movable (owns inline array + atomic)
    RingBuffer(const RingBuffer&)            = delete;
    RingBuffer& operator=(const RingBuffer&) = delete;
    RingBuffer(RingBuffer&&)                 = delete;
    RingBuffer& operator=(RingBuffer&&)      = delete;

    // ── Write (single-thread only, no-lock) ──────────────────────────────────
    /**
     * Write a log message at the given level.
     * Long messages are split into continuation blocks automatically.
     * When the buffer is full the oldest blocks are evicted (counted in dropCount()).
     */
    void write(std::string_view msg, Level lv = Level::Debug) noexcept;

    // ── Read (Logger-thread only) ─────────────────────────────────────────────
    /**
     * Read the next block and return its parsed header + payload string_view.
     * Returns std::nullopt when the buffer is empty.
     *
     * WARNING: the string_view inside ReadResult points into buf_[] directly.
     * It is valid only until the next write() call on this buffer.
     */
    [[nodiscard]] std::optional<ReadResult> read() noexcept;

    /**
     * Read all available blocks and concatenated them into a string.
     * This consumes the blocks (advances read_idx_).
     * Useful for crash dumps.
     */
    [[nodiscard]] std::string dump() noexcept;

    /// Write raw blocks to a POSIX file descriptor. Async-signal-safe if fd is valid.
    void rawDumpToFd(int fd) const noexcept;
#ifdef _WIN32
    /// Write raw blocks to a pre-opened Windows HANDLE. Best-effort via WriteFile.
    void rawDumpToHandle(void* h) const noexcept;
#endif

    // ── Diagnostics ──────────────────────────────────────────────────────────
    /// Number of blocks currently written but not yet read.
    [[nodiscard]] std::size_t usedBlocks() const noexcept {
        const uint32_t w = write_idx_.load(std::memory_order_relaxed);
        const uint32_t r = read_idx_;
        return static_cast<std::size_t>((w - r) & kMask);
    }
    /// Ratio of used blocks to total capacity.
    [[nodiscard]] float usageRatio() const noexcept {
        return static_cast<float>(usedBlocks()) / static_cast<float>(BlockCount);
    }
    [[nodiscard]] bool empty() const noexcept {
        return read_idx_ == write_idx_.load(std::memory_order_acquire);
    }
    /// Total blocks evicted because the buffer was full.
    [[nodiscard]] uint64_t dropCount() const noexcept { return drop_count_; }

    /// Raw write index (acquire order).
    [[nodiscard]] uint32_t writeIdx() const noexcept {
        return write_idx_.load(std::memory_order_acquire);
    }

private:
    // ── Internal helpers ─────────────────────────────────────────────────────
    /// Ensure N blocks of space are available starting at write_idx_.
    /// If write would overrun read, advance read_idx_ past the write range.
    void evictIfNeeded(uint32_t blocksNeeded) noexcept;

    /// Write one block: encode header, copy chunk, zero-fill unused bytes + sentinel.
    void writeBlock(uint32_t idx,
                    std::string_view chunk,
                    Level lv,
                    bool  isContinuation) noexcept;

    // ── Memory layout ─────────────────────────────────────────────────────────
    // write_idx_ is atomic so a crash-time reader on another thread sees published blocks.
    // Placed on its own cache line to avoid false sharing with read_idx_ / buf_.
    alignas(64) std::atomic<uint32_t> write_idx_{0};

    // read_idx_ is owned exclusively by the owning thread. No atomicity required.
    alignas(64) uint32_t read_idx_{0};

    uint64_t drop_count_{0};

    // Inline 2-D array — no heap allocation, cache-friendly sequential layout.
    char buf_[BlockCount][BlockSize]{};
};

#ifdef _MSC_VER
#pragma warning(pop)
#endif

// ─────────────────────────────────────────────────────────────────────────────
// RingBuffer Implementation (Template)
// ─────────────────────────────────────────────────────────────────────────────

template <std::size_t BS, std::size_t BC>
    requires (BC > 1 && (BC & (BC - 1)) == 0) && (BS >= 4)
void RingBuffer<BS, BC>::evictIfNeeded(uint32_t blocksNeeded) noexcept {
    const uint32_t w = write_idx_.load(std::memory_order_relaxed);
    
    for (uint32_t i = 0; i < blocksNeeded; ++i) {
        // Calculate where the pointer will be AFTER this specific block is written.
        // If that matches read_idx_, it would make the buffer look empty,
        // so we must advance read_idx_ (evict the oldest block).
        if (((w + i + 1) & kMask) == read_idx_) {
            read_idx_ = (read_idx_ + 1) & kMask;
            ++drop_count_; // Track how many local blocks were lost
        }
    }
}

template <std::size_t BS, std::size_t BC>
    requires (BC > 1 && (BC & (BC - 1)) == 0) && (BS >= 4)
void RingBuffer<BS, BC>::writeBlock(uint32_t idx, std::string_view chunk, Level lv, bool isContinuation) noexcept {
    char* block = buf_[idx & kMask];
    const auto payloadLen = static_cast<uint16_t>(chunk.size());
    const uint16_t header = encodeHeader(lv, isContinuation, payloadLen);
    std::memcpy(block, &header, kHeaderBytes);
    std::memcpy(block + kHeaderBytes, chunk.data(), payloadLen);
    const std::size_t unusedBytes = kPayloadBytes - payloadLen + kSentinelByte;
    std::memset(block + kHeaderBytes + payloadLen, 0, unusedBytes);
}

template <std::size_t BS, std::size_t BC>
    requires (BC > 1 && (BC & (BC - 1)) == 0) && (BS >= 4)
void RingBuffer<BS, BC>::write(std::string_view msg, Level lv) noexcept {
    if (msg.empty()) return;
    std::string_view remaining = msg;
    bool first = true;
    while (!remaining.empty()) {
        const std::size_t chunkSize = (remaining.size() > kPayloadBytes) ? kPayloadBytes : remaining.size();
        const auto chunk = remaining.substr(0, chunkSize);
        remaining = remaining.substr(chunkSize);
        const uint32_t w = write_idx_.load(std::memory_order_relaxed);
        evictIfNeeded(1);
        writeBlock(w, chunk, lv, !first);
        write_idx_.store((w + 1u) & kMask, std::memory_order_release);
        first = false;
    }
}

template <std::size_t BS, std::size_t BC>
    requires (BC > 1 && (BC & (BC - 1)) == 0) && (BS >= 4)
std::optional<typename RingBuffer<BS, BC>::ReadResult> RingBuffer<BS, BC>::read() noexcept {
    if (empty()) return std::nullopt;
    const char* block = buf_[read_idx_];
    uint16_t header{};
    std::memcpy(&header, block, kHeaderBytes);
    const Level level = decodeLevel(header);
    const bool isCont = decodeCont(header);
    const auto payloadLen = static_cast<std::size_t>(decodeLen(header));
    read_idx_ = (read_idx_ + 1u) & kMask;
    return ReadResult{std::string_view(block + kHeaderBytes, payloadLen), level, isCont};
}

template <std::size_t BS, std::size_t BC>
    requires (BC > 1 && (BC & (BC - 1)) == 0) && (BS >= 4)
std::string RingBuffer<BS, BC>::dump() noexcept {
    std::string result;
    while (auto r = read()) {
        result.append(r->payload);
        result.push_back('\n');
    }
    
    // Append tracking information if any data was evicted.
    if (drop_count_ > 0) {
        result.append("--- WARNING: ");
        result.append(std::to_string(drop_count_));
        result.append(" logs were EVICTED due to buffer overflow ---\n");
    }
    
    return result;
}

// ─── DbgBuf — thread_local singleton wrapper ─────────────────────────────────
/**
 * Convenience façade that routes dlog() / log() calls to the calling thread's
 * own RingBuffer<> instance.
 *
 * Usage:
 *   DbgBuf::log("hello {}", Level::Info); // writes to this thread's buffer
 */
namespace detail {
class ThreadLogBuffer;
} // namespace detail

class DbgBuf {
public:
    DbgBuf()  = delete; // static-only API
    ~DbgBuf() = delete;

    /// Write to the current thread's buffer at the specified level via LogService (loggerId 0).
    static void log(std::string_view msg, Level lv = Level::Debug) noexcept;

    /// Return the current thread's ThreadLogBuffer instance.
    [[nodiscard]] static detail::ThreadLogBuffer& instance() noexcept;

    /// Read and return all retained items in the current thread's buffer as a string.
    [[nodiscard]] static std::string dump() noexcept;
    /// Async-signal-safe raw dump to an already-open file descriptor / HANDLE.
    static void dumpToFd(int fd) noexcept;
#ifdef _WIN32
    static void dumpToHandle(void* h) noexcept;
#endif
};

// Factory for unified value-based error handling.
// RingBuffer capacity is currently compile-time fixed to kDefaultBlockCount.
[[nodiscard]] Expected<RingBuffer<>> makeRingBuffer(std::size_t capacity);

} // namespace atugcc::core
