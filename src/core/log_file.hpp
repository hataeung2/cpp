#pragma once

#include <cstdint>
#include <filesystem>
#include <string_view>

#include "atugcc/core/error.hpp"

namespace atugcc::core::detail {

/**
 * @brief Move-only OS file wrapper for appending log lines (Design D4).
 *
 * Uses low-level OS file descriptors (POSIX open/write/fsync/close) or
 * Windows file handles (CreateFileW/WriteFile/FlushFileBuffers/CloseHandle)
 * without intermediate C++ stream buffers, guaranteeing durability across
 * crashes once written.
 */
class LogFile {
public:
    LogFile() noexcept = default;
    ~LogFile() noexcept;

    LogFile(const LogFile&) = delete;
    LogFile& operator=(const LogFile&) = delete;

    LogFile(LogFile&& other) noexcept;
    LogFile& operator=(LogFile&& other) noexcept;

    [[nodiscard]] static Expected<LogFile> open(const std::filesystem::path& path) noexcept;
    [[nodiscard]] Result write(std::string_view text) noexcept;
    [[nodiscard]] Result sync() noexcept;
    [[nodiscard]] bool isOpen() const noexcept;

private:
    explicit LogFile(std::intptr_t handle) noexcept;
    void close() noexcept;

    std::intptr_t handle_{-1};
};

} // namespace atugcc::core::detail
