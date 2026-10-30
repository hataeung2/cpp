#pragma once

#include <chrono>
#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <vector>

#include "atugcc/core/error.hpp"

namespace atugcc::core {

enum class Delivery : std::uint8_t { Async, Sync };
enum class OverflowPolicy : std::uint8_t { BlockThenDrop, Block };
enum class Durability : std::uint8_t { Process, System };

/**
 * @brief Configuration for per-thread log buffers and consumer drain frequency.
 */
struct LogBufferConfig {
    std::size_t slotsPerThread = 512;               // 010-09: power of two, 64 .. 65536
    std::chrono::milliseconds drainInterval{5};     // 010-09: 1 .. 1000 ms
    // 010-10
    std::filesystem::path mappedDir{};              // empty = leave as is (off by default)
    std::size_t mappedBytes = 8 * 1024 * 1024;      // 1 MiB .. 1 GiB, read when mapping starts
};

// 010-09 + 010-10: the first non-empty mappedDir recovers ended runs in that directory, then maps this
// run's arena there. Same directory again: no change. Another directory while mapped: InvalidArgument.
// Cannot create or map: FileIOFailure (logging continues in memory). Env: ATUGCC_LOG_MAP_DIR.
// An invalid slotsPerThread, drainInterval or mappedBytes is rejected (InvalidArgument) before anything
// changes. A failure of the map part only (another directory, FileIOFailure) still applies slotsPerThread
// and drainInterval: they do not depend on the map.
[[nodiscard]] Result configureLogBuffers(const LogBufferConfig& cfg) noexcept;

/**
 * @brief Returns the current process-wide log buffer configuration.
 */
[[nodiscard]] LogBufferConfig currentLogBufferConfig() noexcept;

struct LogMapRecovery {
    std::filesystem::path recoveredFile;            // recovered_<start>_<pid>.log
    std::uint32_t pid = 0;
    std::uint64_t undeliveredLines = 0;
    std::uint64_t deliveredLines = 0;               // context
    std::uint32_t skippedBuffers = 0;               // failed validation
    bool crashHandlerRan = false;
};

// Recovers every ended run's .logmap in dir into its own recovered file, then deletes the .logmap.
// Live runs (file locked) are skipped. An unreadable file is renamed to <name>.corrupt and not returned.
[[nodiscard]] Expected<std::vector<LogMapRecovery>> recoverLogMaps(const std::filesystem::path& dir);

} // namespace atugcc::core
