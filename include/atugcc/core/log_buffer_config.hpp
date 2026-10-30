#pragma once

#include <chrono>
#include <cstddef>
#include <cstdint>

#include "atugcc/core/error.hpp"

namespace atugcc::core {

enum class Delivery : std::uint8_t { Async, Sync };
enum class OverflowPolicy : std::uint8_t { BlockThenDrop, Block };
enum class Durability : std::uint8_t { Process, System };

/**
 * @brief Configuration for per-thread log buffers and consumer drain frequency.
 */
struct LogBufferConfig {
    std::size_t slotsPerThread = 512;               // power of two, 64 .. 65536
    std::chrono::milliseconds drainInterval{5};     // 1 .. 1000 ms
};

/**
 * @brief Configures global log buffer defaults for newly created thread buffers.
 *
 * Rejects invalid slot counts (non-power-of-two or outside [64, 65536]) and
 * invalid drain intervals (outside [1, 1000] ms) with CoreError::InvalidArgument.
 * On rejection, existing configuration remains unchanged.
 */
[[nodiscard]] Result configureLogBuffers(const LogBufferConfig& cfg) noexcept;

/**
 * @brief Returns the current process-wide log buffer configuration.
 */
[[nodiscard]] LogBufferConfig currentLogBufferConfig() noexcept;

} // namespace atugcc::core
