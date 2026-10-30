#pragma once
/**
 * @file thread_log_buffer.hpp
 * @brief Thread-safe per-thread SPSC fixed-slot log buffer for atugcc logging.
 *
 * Memory Layout (Design D1):
 *   One contiguous, pointer-free, little-endian block per buffer, suitable for
 *   placing directly in a memory-mapped file (spec 010-09 / 010-10):
 *
 *   BufferHeader (64 bytes, alignas(64))
 *     char                   magic[8]   "ATGLBUF1"
 *     uint32                 slotCount  power of two (kMinSlots .. kMaxSlots)
 *     uint32                 slotBytes  256
 *     uint32                 threadNo   process-unique number of owning thread
 *     atomic<uint32>         flags      bit0 = retired (owning thread ended)
 *     atomic<uint64>         writePos   producer only; monotonic
 *     atomic<uint64>         readPos    consumer only; monotonic
 *     uint64                 reserved[3]
 *   Slot[slotCount] (256 bytes each)
 *     SlotHeader (24 bytes)
 *       uint64               timeNs     steady_clock nanoseconds since epoch
 *       uint32               threadSeq  record sequence in owning thread
 *       uint16               loggerId   0 = DbgBuf (no sink), else registered Logger
 *       uint8                level      atugcc::core::Level
 *       uint8                flags      bit0 = first slot, bit1 = last slot
 *       uint16               len        payload bytes in this slot (0..232)
 *       uint16               reserved0
 *       uint32               reserved1
 *     uint8                  payload[232]
 *
 * Concurrency & Call Permissions:
 *   - Producer (owning thread):
 *       Calls tryWrite(), setThreadNo(), setRetired(). Sole writer of writePos.
 *   - Consumer (the log thread):
 *       Calls writePos(), readPos(), advanceRead(), slotHeader(), slotPayload(),
 *       usedSlots(). Sole writer of readPos.
 *   - Crash reader (any thread):
 *       Read-only access via rawBytes(), rawSize(), and retainedText(). Signal-safe
 *       raw inspection without locks or heap allocation.
 *
 * Delivery & Overwrite Guarantee:
 *   Undelivered slots are NEVER overwritten; space check (writePos + n - readPos <= slotCount)
 *   guarantees that unconsumed slots are never touched by tryWrite(). Delivered slots (< readPos)
 *   may be reused when writePos wraps around.
 */

#include <atomic>
#include <cstddef>
#include <cstdint>
#include <string>
#include <string_view>

#include "atugcc/core/ring_buffer.hpp"

namespace atugcc::core::detail {

// ─── Layout & Boundary Constants ─────────────────────────────────────────────
inline constexpr std::string_view kMagic = "ATGLBUF1";
inline constexpr std::size_t kMagicBytes = 8;

inline constexpr std::uint32_t kSlotBytes = 256;
inline constexpr std::uint32_t kSlotPayloadBytes = 232;
inline constexpr std::uint32_t kMinSlots = 64;
inline constexpr std::uint32_t kMaxSlots = 65536;

inline constexpr std::uint32_t kBufferFlagRetired = 1u << 0;

inline constexpr std::uint8_t kSlotFlagFirst = 1u << 0;
inline constexpr std::uint8_t kSlotFlagLast  = 1u << 1;

// ─── Header Structs ──────────────────────────────────────────────────────────
struct alignas(64) BufferHeader {
    char magic[8]{'A', 'T', 'G', 'L', 'B', 'U', 'F', '1'};
    std::uint32_t slotCount{0};
    std::uint32_t slotBytes{kSlotBytes};
    std::uint32_t threadNo{0};
    std::atomic<std::uint32_t> flags{0};
    std::atomic<std::uint64_t> writePos{0};
    std::atomic<std::uint64_t> readPos{0};
    std::uint64_t reserved[3]{0, 0, 0};
};

static_assert(sizeof(BufferHeader) == 64);
static_assert(alignof(BufferHeader) == 64);
static_assert(std::atomic<std::uint64_t>::is_always_lock_free && sizeof(std::atomic<std::uint64_t>) == 8);

struct SlotHeader {
    std::uint64_t timeNs{0};
    std::uint32_t threadSeq{0};
    std::uint16_t loggerId{0};
    Level level{Level::Debug};
    std::uint8_t flags{0};
    std::uint16_t len{0};
    std::uint16_t reserved0{0};
    std::uint32_t reserved1{0};
};

static_assert(sizeof(SlotHeader) == 24);

struct Slot {
    SlotHeader header;
    std::uint8_t payload[kSlotPayloadBytes];
};

static_assert(sizeof(Slot) == 256);

// ─── ThreadLogBuffer Class ───────────────────────────────────────────────────
class alignas(64) ThreadLogBuffer {
public:
    ThreadLogBuffer(const ThreadLogBuffer&) = delete;
    ThreadLogBuffer& operator=(const ThreadLogBuffer&) = delete;
    ThreadLogBuffer(ThreadLogBuffer&&) = delete;
    ThreadLogBuffer& operator=(ThreadLogBuffer&&) = delete;

    [[nodiscard]] static ThreadLogBuffer* create(std::uint32_t slotCount) noexcept;

    [[nodiscard]] bool tryWrite(std::uint64_t timeNs,
                                std::uint32_t threadSeq,
                                std::uint16_t loggerId,
                                Level level,
                                std::string_view text) noexcept;

    // Consumer side
    [[nodiscard]] std::uint64_t writePos() const noexcept;
    [[nodiscard]] std::uint64_t readPos() const noexcept;
    void advanceRead(std::uint64_t newReadPos) noexcept;
    [[nodiscard]] const SlotHeader& slotHeader(std::uint64_t pos) const noexcept;
    [[nodiscard]] std::string_view slotPayload(std::uint64_t pos) const noexcept;

    // Properties and thread lifecycle
    [[nodiscard]] std::uint32_t slotCount() const noexcept;
    [[nodiscard]] std::size_t usedSlots() const noexcept;
    [[nodiscard]] std::uint32_t threadNo() const noexcept;
    void setThreadNo(std::uint32_t no) noexcept;
    void setRetired(bool retired) noexcept;
    [[nodiscard]] bool retired() const noexcept;

    // Crash-time raw access (signal-safe, no allocation, no locks)
    [[nodiscard]] const void* rawBytes() const noexcept;
    [[nodiscard]] std::size_t rawSize() const noexcept;

    [[nodiscard]] const BufferHeader& header() const noexcept;

private:
    explicit ThreadLogBuffer(std::uint32_t slotCount) noexcept;
    ~ThreadLogBuffer() = default;

    Slot* slots() noexcept;
    const Slot* slots() const noexcept;

    BufferHeader header_;
};

static_assert(sizeof(ThreadLogBuffer) == 64);

// ─── Retained Text Helper ────────────────────────────────────────────────────
[[nodiscard]] std::string retainedText(const ThreadLogBuffer& b);

} // namespace atugcc::core::detail
