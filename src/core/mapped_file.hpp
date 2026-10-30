#pragma once

#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <optional>

#include "atugcc/core/error.hpp"

namespace atugcc::core::detail {

inline constexpr std::size_t kMaxMappedFileBytes = (std::size_t{1} << 30) + 64 * 1024;

/**
 * @brief Move-only platform-neutral memory-mapped file wrapper (Design D1).
 *
 * Provides locked creation for new files and conditional opening for completed runs.
 * On POSIX, locks use flock(LOCK_EX | LOCK_NB) and unlinking occurs immediately on removeFile().
 * On Windows, handles use FILE_SHARE_READ | FILE_SHARE_DELETE and POSIX delete disposition.
 */
class MappedFile {
public:
    MappedFile() noexcept = default;
    ~MappedFile() noexcept;

    MappedFile(const MappedFile&) = delete;
    MappedFile& operator=(const MappedFile&) = delete;

    MappedFile(MappedFile&& other) noexcept;
    MappedFile& operator=(MappedFile&& other) noexcept;

    // New file (fails if it exists), locked for the life of the handle, space reserved, mapped read-write.
    [[nodiscard]] static Expected<MappedFile> createLocked(const std::filesystem::path& path, std::size_t bytes) noexcept;

    // Existing file: std::nullopt when another process holds it (a live run). Mapped read-only.
    // Size 0 or above kMaxMappedFileBytes (1 GiB + 64 KiB): FileIOFailure.
    [[nodiscard]] static Expected<std::optional<MappedFile>> openIfEnded(const std::filesystem::path& path) noexcept;

    [[nodiscard]] const std::byte* data() const noexcept;
    [[nodiscard]] std::byte* data() noexcept;
    [[nodiscard]] std::size_t size() const noexcept;

    // POSIX: unlink now. Windows: delete disposition with POSIX semantics (gone when the last handle
    // closes). The mapping stays valid in both cases.
    [[nodiscard]] Result removeFile() noexcept;

    // The calling process's id (getpid / GetCurrentProcessId): the map file name and header (plan D2).
    [[nodiscard]] static std::uint32_t currentProcessId() noexcept;

    // Whether a process with this id exists (POSIX kill(pid, 0), Windows OpenProcess). Recovery uses it
    // only to decide whether to wait for a lock that a just-killed owner has not released yet.
    [[nodiscard]] static bool processAlive(std::uint32_t pid) noexcept;

private:
    MappedFile(std::filesystem::path path,
               std::intptr_t handle,
               std::intptr_t mapping_handle,
               std::byte* data,
               std::size_t size) noexcept;
    void unmapAndClose() noexcept;

    std::filesystem::path path_{};
    std::intptr_t handle_{-1};
    std::intptr_t mapping_handle_{-1};
    std::byte* data_{nullptr};
    std::size_t size_{0};
};

} // namespace atugcc::core::detail
