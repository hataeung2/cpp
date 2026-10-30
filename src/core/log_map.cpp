#include "atugcc/core/detail/log_map.hpp"

#include <atomic>
#include <chrono>
#include <cstdio>
#include <cstring>
#include <filesystem>
#include <format>
#include <mutex>
#include <new>
#include <string>
#include <string_view>

#include "atugcc/core/log_buffer_config.hpp"
#include "mapped_file.hpp"

namespace atugcc::core::detail {

namespace {

std::atomic<std::byte*> gMapBase{nullptr};
std::atomic<std::size_t> gMapBytes{0};
std::atomic<std::uint64_t> gRefusals{0};
std::atomic_flag gFullReported = ATOMIC_FLAG_INIT;

std::mutex gStartMutex;
std::filesystem::path gActiveDir{};
std::filesystem::path gActivePath{};
std::atomic<MappedFile*> gMappedFile{nullptr};  // set once, before gMapBase is published

// MapHeader is stored as raw mapped bytes; std::launder/reinterpret_cast yields the aligned field address for atomic_ref.
inline std::uint64_t& getMappedArenaUsed(std::byte* base) noexcept {
    return *std::launder(reinterpret_cast<std::uint64_t*>(base + offsetof(MapHeader, arenaUsed)));
}

// MapHeader is stored as raw mapped bytes; std::launder/reinterpret_cast yields the aligned field address for atomic_ref.
inline std::uint32_t& getMappedFlags(std::byte* base) noexcept {
    return *std::launder(reinterpret_cast<std::uint32_t*>(base + offsetof(MapHeader, flags)));
}

std::size_t truncateUtf8(std::string_view s, std::size_t maxBytes) noexcept {
    if (s.size() <= maxBytes) {
        return s.size();
    }
    std::size_t cut = maxBytes;
    while (cut > 0 && (static_cast<unsigned char>(s[cut]) & 0xC0) == 0x80) {
        --cut;
    }
    if (cut < maxBytes) {
        const auto lead = static_cast<unsigned char>(s[cut]);
        std::size_t charLen = 1;
        if ((lead & 0x80) == 0) {
            charLen = 1;
        } else if ((lead & 0xE0) == 0xC0) {
            charLen = 2;
        } else if ((lead & 0xF0) == 0xE0) {
            charLen = 3;
        } else if ((lead & 0xF8) == 0xF0) {
            charLen = 4;
        }
        if (cut + charLen > maxBytes) {
            // Cut point lands inside multi-byte character; exclude this leading byte.
        } else {
            cut += charLen;
        }
    }
    return cut;
}

} // namespace

Result startLogMap(const std::filesystem::path& dir, std::size_t bytes) noexcept {
    if (bytes < kMinMappedBytes || bytes > kMaxMappedBytes) {
        return std::unexpected(CoreError::InvalidArgument);
    }

    try {
        bool shouldRepublish = false;
        {
            std::lock_guard lock(gStartMutex);

            std::error_code ec;
            const auto reqNorm = std::filesystem::absolute(dir, ec).lexically_normal();
            if (ec) {
                return std::unexpected(CoreError::FileIOFailure);
            }

            if (gMapBase.load(std::memory_order_relaxed) != nullptr) {
                if (reqNorm == gActiveDir) {
                    return {};
                }
                return std::unexpected(CoreError::InvalidArgument);
            }

            std::filesystem::create_directories(dir, ec);
            if (ec) {
                return std::unexpected(CoreError::FileIOFailure);
            }

            // A failed recovery does not stop the start; recoverLogMaps reports on stderr and never throws.
            // It must not call logMapPath() (gStartMutex is held): this run's own file is skipped by its lock.
            (void)recoverLogMaps(dir);

            const auto nowSys = std::chrono::system_clock::now();
            const auto nowNs = static_cast<std::int64_t>(
                std::chrono::duration_cast<std::chrono::nanoseconds>(nowSys.time_since_epoch()).count());
            const auto pid = MappedFile::currentProcessId();
            const std::string name = "atugcc-" + std::to_string(pid) + "-" + formatCompactUtc(nowNs) + ".logmap";
            const auto filePath = dir / name;

            auto mappedRes = MappedFile::createLocked(filePath, bytes);
            if (!mappedRes.has_value()) {
                return std::unexpected(CoreError::FileIOFailure);
            }

            auto* mappedFile = new (std::nothrow) MappedFile(std::move(*mappedRes));
            if (mappedFile == nullptr) {
                return std::unexpected(CoreError::Unexpected);
            }
            std::byte* base = mappedFile->data();

            const auto steadyNow = std::chrono::steady_clock::now();
            const auto sysNow = std::chrono::system_clock::now();
            const auto steadyNs = static_cast<std::uint64_t>(
                std::chrono::duration_cast<std::chrono::nanoseconds>(steadyNow.time_since_epoch()).count());
            const auto sysNs = static_cast<std::int64_t>(
                std::chrono::duration_cast<std::chrono::nanoseconds>(sysNow.time_since_epoch()).count());

            MapHeader header{};
            std::memcpy(header.magic, kMapMagic.data(), kMapMagicBytes);
            header.version = kMapVersion;
            header.arenaOffset = kArenaOffset;
            header.fileBytes = static_cast<std::uint64_t>(bytes);
            header.pid = pid;
            header.flags = 0;
            header.startSystemNs = static_cast<std::uint64_t>(nowNs);
            header.steadyBaseNs = steadyNs;
            header.systemBaseNs = sysNs;
            header.arenaUsed = kArenaOffset;
            header.labelCount = kLabelCount;
            header.labelBytes = kLabelBytes;

            std::memcpy(base, &header, sizeof(MapHeader));

            gMappedFile.store(mappedFile, std::memory_order_relaxed);  // gMapBase's release store publishes it
            gActiveDir = reqNorm;
            gActivePath = filePath;
            gMapBytes.store(bytes, std::memory_order_relaxed);
            gMapBase.store(base, std::memory_order_release);
            shouldRepublish = true;
        }

        if (shouldRepublish) {
            republishLoggerLabels();
        }
        return {};
    } catch (...) {
        return std::unexpected(CoreError::Unexpected);
    }
}

bool logMapActive() noexcept {
    return gMapBase.load(std::memory_order_acquire) != nullptr;
}

std::filesystem::path logMapPath() noexcept {
    try {
        std::lock_guard lock(gStartMutex);
        return gActivePath;
    } catch (...) {
        return {};
    }
}

ThreadLogBuffer* allocateMappedBuffer(std::uint32_t slotCount) noexcept {
    std::byte* base = gMapBase.load(std::memory_order_acquire);
    if (base == nullptr) {
        return nullptr;
    }
    const std::size_t fileBytes = gMapBytes.load(std::memory_order_relaxed);
    const std::size_t need = sizeof(BufferHeader) + static_cast<std::size_t>(slotCount) * kSlotBytes;

    auto& arenaUsedField = getMappedArenaUsed(base);
    std::atomic_ref<std::uint64_t> arenaUsedRef(arenaUsedField);

    std::uint64_t currentUsed = arenaUsedRef.load(std::memory_order_relaxed);
    while (true) {
        if (static_cast<std::uint64_t>(need) > fileBytes || currentUsed > fileBytes - need) {
            gRefusals.fetch_add(1, std::memory_order_relaxed);
            if (!gFullReported.test_and_set(std::memory_order_relaxed)) {
                try {
                    const std::string msg = std::format(
                        "[atugcc] log map full ({} bytes): new thread buffers are not recoverable\n",
                        fileBytes);
                    std::fputs(msg.c_str(), stderr);
                } catch (...) {
                    std::fputs("[atugcc] log map full: new thread buffers are not recoverable\n", stderr);
                }
            }
            return nullptr;
        }

        const std::uint64_t nextUsed = currentUsed + need;
        if (arenaUsedRef.compare_exchange_weak(currentUsed, nextUsed,
                                               std::memory_order_acq_rel,
                                               std::memory_order_relaxed)) {
            return ThreadLogBuffer::createIn(base + currentUsed, slotCount);
        }
    }
}

bool isMappedBuffer(const void* ptr) noexcept {
    const std::byte* base = gMapBase.load(std::memory_order_acquire);
    if (base == nullptr || ptr == nullptr) {
        return false;
    }
    const std::size_t bytes = gMapBytes.load(std::memory_order_relaxed);
    const auto* p = static_cast<const std::byte*>(ptr);
    return (p >= base + kArenaOffset && p < base + bytes);
}

bool isMappedBuffer(const ThreadLogBuffer* buffer) noexcept {
    return isMappedBuffer(static_cast<const void*>(buffer));
}

std::uint64_t mappedRefusals() noexcept {
    return gRefusals.load(std::memory_order_relaxed);
}

void setLogMapLabel(std::uint16_t id, std::string_view text) noexcept {
    std::byte* base = gMapBase.load(std::memory_order_acquire);
    if (base == nullptr || id == 0 || id >= kLabelCount) {
        return;
    }
    const std::size_t cutLen = truncateUtf8(text, kLabelTextBytes);
    std::byte* entryPtr = base + kLabelTableOffset + static_cast<std::size_t>(id) * sizeof(LabelEntry);

    auto* lenPtr = reinterpret_cast<std::uint16_t*>(entryPtr + offsetof(LabelEntry, len));
    char* textPtr = reinterpret_cast<char*>(entryPtr + offsetof(LabelEntry, text));

    *lenPtr = static_cast<std::uint16_t>(cutLen);
    if (cutLen > 0) {
        std::memcpy(textPtr, text.data(), cutLen);
    }
    if (cutLen < kLabelTextBytes) {
        std::memset(textPtr + cutLen, 0, kLabelTextBytes - cutLen);
    }

    auto& idField = *std::launder(reinterpret_cast<std::uint16_t*>(entryPtr + offsetof(LabelEntry, id)));
    std::atomic_ref<std::uint16_t> idRef(idField);
    idRef.store(id, std::memory_order_release);
}

void clearLogMapLabel(std::uint16_t id) noexcept {
    std::byte* base = gMapBase.load(std::memory_order_acquire);
    if (base == nullptr || id == 0 || id >= kLabelCount) {
        return;
    }
    std::byte* entryPtr = base + kLabelTableOffset + static_cast<std::size_t>(id) * sizeof(LabelEntry);

    auto& idField = *std::launder(reinterpret_cast<std::uint16_t*>(entryPtr + offsetof(LabelEntry, id)));
    std::atomic_ref<std::uint16_t> idRef(idField);
    idRef.store(0, std::memory_order_release);

    auto* lenPtr = reinterpret_cast<std::uint16_t*>(entryPtr + offsetof(LabelEntry, len));
    *lenPtr = 0;
}

void markLogMapCrash() noexcept {
    std::byte* base = gMapBase.load(std::memory_order_relaxed);
    if (base == nullptr) {
        return;
    }
    auto& flagsField = getMappedFlags(base);
    std::atomic_ref<std::uint32_t> flagsRef(flagsField);
    flagsRef.fetch_or(kMapFlagCrash, std::memory_order_relaxed);
}

void finishLogMapCleanly() noexcept {
    std::byte* base = gMapBase.load(std::memory_order_acquire);
    if (base == nullptr) {
        return;
    }
    auto& flagsField = getMappedFlags(base);
    std::atomic_ref<std::uint32_t> flagsRef(flagsField);
    flagsRef.fetch_or(kMapFlagCleanExit, std::memory_order_release);

    MappedFile* mappedFile = gMappedFile.load(std::memory_order_relaxed);  // ordered by the acquire load of gMapBase
    if (mappedFile != nullptr) {
        (void)mappedFile->removeFile();
    }
}

std::string formatCompactUtc(std::int64_t systemNs) {
    const std::chrono::sys_time<std::chrono::nanoseconds> tp{std::chrono::nanoseconds{systemNs}};
    const auto msTime = std::chrono::floor<std::chrono::milliseconds>(tp);
    const std::chrono::sys_days days = std::chrono::floor<std::chrono::days>(msTime);
    const std::chrono::year_month_day ymd{days};
    const auto timeOfDay = msTime - days;
    const auto hours = std::chrono::floor<std::chrono::hours>(timeOfDay);
    const auto mins = std::chrono::floor<std::chrono::minutes>(timeOfDay - hours);
    const auto secs = std::chrono::floor<std::chrono::seconds>(timeOfDay - hours - mins);
    const auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(timeOfDay - hours - mins - secs);

    return std::format("{:04}{:02}{:02}T{:02}{:02}{:02}{:03}",
                       static_cast<int>(ymd.year()),
                       static_cast<unsigned>(ymd.month()),
                       static_cast<unsigned>(ymd.day()),
                       hours.count(),
                       mins.count(),
                       secs.count(),
                       ms.count());
}

std::string formatIsoUtcMicros(std::int64_t systemNs) {
    const std::chrono::sys_time<std::chrono::nanoseconds> tp{std::chrono::nanoseconds{systemNs}};
    const auto usTime = std::chrono::floor<std::chrono::microseconds>(tp);
    const std::chrono::sys_days days = std::chrono::floor<std::chrono::days>(usTime);
    const std::chrono::year_month_day ymd{days};
    const auto timeOfDay = usTime - days;
    const auto hours = std::chrono::floor<std::chrono::hours>(timeOfDay);
    const auto mins = std::chrono::floor<std::chrono::minutes>(timeOfDay - hours);
    const auto secs = std::chrono::floor<std::chrono::seconds>(timeOfDay - hours - mins);
    const auto us = std::chrono::duration_cast<std::chrono::microseconds>(timeOfDay - hours - mins - secs);

    return std::format("{:04}-{:02}-{:02}T{:02}:{:02}:{:02}.{:06}Z",
                       static_cast<int>(ymd.year()),
                       static_cast<unsigned>(ymd.month()),
                       static_cast<unsigned>(ymd.day()),
                       hours.count(),
                       mins.count(),
                       secs.count(),
                       us.count());
}

} // namespace atugcc::core::detail
