#pragma once

#include <cstddef>
#include <cstdint>

namespace alog::detail {

/**
 * @brief Installs process-wide crash handlers (defined in platform-specific crash_handler_*.cpp).
 */
void installCrashHandlers() noexcept;

/**
 * @brief Writes DUMP-V2 crash dump of all registered thread buffers to the prepared target.
 */
void writeDump(const char* eventType, std::uint64_t eventCode, const void* context, std::size_t contextSize) noexcept;

/**
 * @brief Atomically claims the right to produce the crash dump once per process.
 * @return true for the first caller only, false for all subsequent calls.
 */
[[nodiscard]] bool claimDump() noexcept;

/**
 * @brief Signal-safe write helper that loops until all bytes are written to the prepared target.
 */
void writeAll(const void* data, std::size_t size) noexcept;

/**
 * @brief Signal-safe helper that writes a null-terminated string to the prepared target.
 */
void writeText(const char* text) noexcept;

/**
 * @brief Signal-safe helper that formats and writes an unsigned 64-bit integer in decimal.
 */
void writeDecimal(std::uint64_t val) noexcept;

} // namespace alog::detail
