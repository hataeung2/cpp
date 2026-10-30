#pragma once

#include <atomic>
#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <string>
#include <string_view>

#include "atugcc/core/detail/thread_log_buffer.hpp"
#include "atugcc/core/error.hpp"

namespace atugcc::core::detail {

// ─── Map Format & Layout Constants (Plan D2) ─────────────────────────────────
inline constexpr std::string_view kMapMagic = "ATGLMAP1";
inline constexpr std::size_t kMapMagicBytes = 8;
inline constexpr std::uint32_t kMapVersion = 1;
inline constexpr std::size_t kMapHeaderBytes = 128;
inline constexpr std::uint32_t kLabelCount = 256;
inline constexpr std::uint32_t kLabelBytes = 128;
inline constexpr std::uint32_t kLabelTextBytes = 124;
inline constexpr std::size_t kLabelTableOffset = 4096;
inline constexpr std::uint32_t kArenaOffset = 36864; // 4096 + 256 * 128 = 36864 (page aligned)

inline constexpr std::uint32_t kMapFlagCrash = 1u << 0;
inline constexpr std::uint32_t kMapFlagCleanExit = 1u << 1;

inline constexpr std::size_t kMinMappedBytes = 1024 * 1024;             // 1 MiB
inline constexpr std::size_t kMaxMappedBytes = 1024 * 1024 * 1024;      // 1 GiB
inline constexpr std::size_t kDefaultMappedBytes = 8 * 1024 * 1024;     // 8 MiB

// ─── Map Header (128 bytes, plain uint fields, no std::atomic) ────────────────
struct alignas(8) MapHeader {
    char magic[8]{'A', 'T', 'G', 'L', 'M', 'A', 'P', '1'};
    std::uint32_t version{kMapVersion};
    std::uint32_t arenaOffset{kArenaOffset};
    std::uint64_t fileBytes{0};
    std::uint32_t pid{0};
    std::uint32_t flags{0};
    std::uint64_t startSystemNs{0};
    std::uint64_t steadyBaseNs{0};
    std::int64_t systemBaseNs{0};
    std::uint64_t arenaUsed{kArenaOffset};
    std::uint32_t labelCount{kLabelCount};
    std::uint32_t labelBytes{kLabelBytes};
    std::uint8_t reserved[56]{};
};

static_assert(sizeof(MapHeader) == 128);
static_assert(alignof(MapHeader) == 8);
static_assert(offsetof(MapHeader, arenaUsed) % 8 == 0);
static_assert(offsetof(MapHeader, flags) % 4 == 0);

// ─── Label Entry (128 bytes) ──────────────────────────────────────────────────
struct LabelEntry {
    std::uint16_t id{0};
    std::uint16_t len{0};
    char text[kLabelTextBytes]{};
};

static_assert(sizeof(LabelEntry) == 128);
static_assert(offsetof(LabelEntry, id) % alignof(std::uint16_t) == 0);
static_assert(offsetof(LabelEntry, len) % alignof(std::uint16_t) == 0);
static_assert(kLabelTableOffset % alignof(std::uint16_t) == 0);

// ─── BufferHeaderDisk (Plain 64-byte mirror of BufferHeader) ─────────────────
struct alignas(64) BufferHeaderDisk {
    char magic[8]{'A', 'T', 'G', 'L', 'B', 'U', 'F', '1'};
    std::uint32_t slotCount{0};
    std::uint32_t slotBytes{kSlotBytes};
    std::uint32_t threadNo{0};
    std::uint32_t flags{0};
    std::uint64_t writePos{0};
    std::uint64_t readPos{0};
    std::uint64_t reservePos{0};
    std::uint64_t reserved[2]{0, 0};
};

static_assert(sizeof(BufferHeaderDisk) == 64);
static_assert(alignof(BufferHeaderDisk) == 64);
static_assert(offsetof(BufferHeaderDisk, writePos) == offsetof(BufferHeader, writePos));
static_assert(offsetof(BufferHeaderDisk, readPos) == offsetof(BufferHeader, readPos));
static_assert(offsetof(BufferHeaderDisk, reservePos) == offsetof(BufferHeader, reservePos));
static_assert(offsetof(BufferHeaderDisk, flags) == offsetof(BufferHeader, flags));
static_assert(offsetof(BufferHeaderDisk, slotCount) == offsetof(BufferHeader, slotCount));
static_assert(offsetof(BufferHeaderDisk, slotBytes) == offsetof(BufferHeader, slotBytes));
static_assert(offsetof(BufferHeaderDisk, threadNo) == offsetof(BufferHeader, threadNo));

// ─── Lock-Free Atomic References ─────────────────────────────────────────────
static_assert(std::atomic_ref<std::uint16_t>::is_always_lock_free);
static_assert(std::atomic_ref<std::uint32_t>::is_always_lock_free);
static_assert(std::atomic_ref<std::uint64_t>::is_always_lock_free);

// ─── Public Detail Functions (noexcept) ───────────────────────────────────────
[[nodiscard]] Result startLogMap(const std::filesystem::path& dir, std::size_t bytes) noexcept;
[[nodiscard]] bool logMapActive() noexcept;
[[nodiscard]] std::filesystem::path logMapPath() noexcept;
[[nodiscard]] ThreadLogBuffer* allocateMappedBuffer(std::uint32_t slotCount) noexcept;
[[nodiscard]] bool isMappedBuffer(const void* ptr) noexcept;
[[nodiscard]] bool isMappedBuffer(const ThreadLogBuffer* buffer) noexcept;
[[nodiscard]] std::uint64_t mappedRefusals() noexcept;
void setLogMapLabel(std::uint16_t id, std::string_view text) noexcept;
void clearLogMapLabel(std::uint16_t id) noexcept;
void markLogMapCrash() noexcept;
void finishLogMapCleanly() noexcept;
void republishLoggerLabels() noexcept;

// ─── Recovery Timestamp Formatting Helpers ────────────────────────────────────
[[nodiscard]] std::string formatCompactUtc(std::int64_t systemNs);
[[nodiscard]] std::string formatIsoUtcMicros(std::int64_t systemNs);

} // namespace atugcc::core::detail
