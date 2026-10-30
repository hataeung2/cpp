#include "mapped_file.hpp"

#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN // MACRO: Lean Windows headers
#endif
#ifndef NOMINMAX
#define NOMINMAX // MACRO: Suppress min/max macros
#endif
#include <Windows.h>

#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <optional>
#include <string>
#include <utility>

namespace atugcc::core::detail {

MappedFile::MappedFile(std::filesystem::path path,
                       std::intptr_t handle,
                       std::intptr_t mapping_handle,
                       std::byte* data,
                       std::size_t size) noexcept
    : path_(std::move(path)),
      handle_(handle),
      mapping_handle_(mapping_handle),
      data_(data),
      size_(size) {
}

MappedFile::~MappedFile() noexcept {
    unmapAndClose();
}

MappedFile::MappedFile(MappedFile&& other) noexcept
    : path_(std::move(other.path_)),
      handle_(std::exchange(other.handle_, -1)),
      mapping_handle_(std::exchange(other.mapping_handle_, -1)),
      data_(std::exchange(other.data_, nullptr)),
      size_(std::exchange(other.size_, 0)) {
    other.path_.clear();
}

MappedFile& MappedFile::operator=(MappedFile&& other) noexcept {
    if (this != &other) {
        unmapAndClose();
        path_ = std::move(other.path_);
        other.path_.clear();
        handle_ = std::exchange(other.handle_, -1);
        mapping_handle_ = std::exchange(other.mapping_handle_, -1);
        data_ = std::exchange(other.data_, nullptr);
        size_ = std::exchange(other.size_, 0);
    }
    return *this;
}

Expected<MappedFile> MappedFile::createLocked(const std::filesystem::path& path, std::size_t bytes) noexcept {
    HANDLE fileHandle = INVALID_HANDLE_VALUE;
    HANDLE mappingHandle = nullptr;
    void* viewPtr = nullptr;
    std::wstring wpath;
    try {
        if (bytes == 0 || bytes > kMaxMappedFileBytes) {
            return std::unexpected(CoreError::FileIOFailure);
        }

        std::filesystem::path storedPath = path;
        wpath = storedPath.wstring();

        fileHandle = CreateFileW(
            wpath.c_str(),
            GENERIC_READ | GENERIC_WRITE | DELETE,
            FILE_SHARE_READ | FILE_SHARE_DELETE,
            nullptr,
            CREATE_NEW,
            FILE_ATTRIBUTE_NORMAL,
            nullptr
        );
        if (fileHandle == INVALID_HANDLE_VALUE) {
            return std::unexpected(CoreError::FileIOFailure);
        }

        auto cleanupAndFail = [&]() noexcept -> Expected<MappedFile> {
            if (viewPtr != nullptr) {
                UnmapViewOfFile(viewPtr);
                viewPtr = nullptr;
            }
            if (mappingHandle != nullptr) {
                CloseHandle(mappingHandle);
                mappingHandle = nullptr;
            }
            if (fileHandle != INVALID_HANDLE_VALUE) {
                CloseHandle(fileHandle);
                fileHandle = INVALID_HANDLE_VALUE;
            }
            DeleteFileW(wpath.c_str());
            return std::unexpected(CoreError::FileIOFailure);
        };

        LARGE_INTEGER li{};
        li.QuadPart = static_cast<LONGLONG>(bytes);
        if (!SetFilePointerEx(fileHandle, li, nullptr, FILE_BEGIN)) {
            return cleanupAndFail();
        }
        if (!SetEndOfFile(fileHandle)) {
            return cleanupAndFail();
        }

        const DWORD sizeHigh = static_cast<DWORD>(static_cast<std::uint64_t>(bytes) >> 32);
        const DWORD sizeLow = static_cast<DWORD>(static_cast<std::uint64_t>(bytes) & 0xFFFFFFFFULL);

        mappingHandle = CreateFileMappingW(
            fileHandle,
            nullptr,
            PAGE_READWRITE,
            sizeHigh,
            sizeLow,
            nullptr
        );
        if (mappingHandle == nullptr) {
            return cleanupAndFail();
        }

        viewPtr = MapViewOfFile(
            mappingHandle,
            FILE_MAP_WRITE,
            0,
            0,
            static_cast<SIZE_T>(bytes)
        );
        if (viewPtr == nullptr) {
            return cleanupAndFail();
        }

        return MappedFile(
            std::move(storedPath),
            reinterpret_cast<std::intptr_t>(fileHandle),
            reinterpret_cast<std::intptr_t>(mappingHandle),
            static_cast<std::byte*>(viewPtr),
            bytes
        );
    } catch (...) {
        if (viewPtr != nullptr) {
            UnmapViewOfFile(viewPtr);
        }
        if (mappingHandle != nullptr) {
            CloseHandle(mappingHandle);
        }
        if (fileHandle != INVALID_HANDLE_VALUE) {
            CloseHandle(fileHandle);
            if (!wpath.empty()) {
                DeleteFileW(wpath.c_str());
            }
        }
        return std::unexpected(CoreError::FileIOFailure);
    }
}

Expected<std::optional<MappedFile>> MappedFile::openIfEnded(const std::filesystem::path& path) noexcept {
    HANDLE fileHandle = INVALID_HANDLE_VALUE;
    HANDLE mappingHandle = nullptr;
    void* viewPtr = nullptr;
    try {
        std::filesystem::path storedPath = path;
        const std::wstring wpath = storedPath.wstring();

        fileHandle = CreateFileW(
            wpath.c_str(),
            GENERIC_READ | GENERIC_WRITE | DELETE,
            0,
            nullptr,
            OPEN_EXISTING,
            FILE_ATTRIBUTE_NORMAL,
            nullptr
        );
        if (fileHandle == INVALID_HANDLE_VALUE) {
            const DWORD err = GetLastError();
            if (err == ERROR_SHARING_VIOLATION) {
                return std::optional<MappedFile>{std::nullopt};
            }
            return std::unexpected(CoreError::FileIOFailure);
        }

        LARGE_INTEGER fileSize{};
        if (!GetFileSizeEx(fileHandle, &fileSize)) {
            CloseHandle(fileHandle);
            fileHandle = INVALID_HANDLE_VALUE;
            return std::unexpected(CoreError::FileIOFailure);
        }

        if (fileSize.QuadPart <= 0 || static_cast<std::uint64_t>(fileSize.QuadPart) > kMaxMappedFileBytes) {
            CloseHandle(fileHandle);
            fileHandle = INVALID_HANDLE_VALUE;
            return std::unexpected(CoreError::FileIOFailure);
        }

        const std::size_t size = static_cast<std::size_t>(fileSize.QuadPart);

        mappingHandle = CreateFileMappingW(
            fileHandle,
            nullptr,
            PAGE_READONLY,
            0,
            0,
            nullptr
        );
        if (mappingHandle == nullptr) {
            CloseHandle(fileHandle);
            fileHandle = INVALID_HANDLE_VALUE;
            return std::unexpected(CoreError::FileIOFailure);
        }

        viewPtr = MapViewOfFile(
            mappingHandle,
            FILE_MAP_READ,
            0,
            0,
            static_cast<SIZE_T>(size)
        );
        if (viewPtr == nullptr) {
            CloseHandle(mappingHandle);
            mappingHandle = nullptr;
            CloseHandle(fileHandle);
            fileHandle = INVALID_HANDLE_VALUE;
            return std::unexpected(CoreError::FileIOFailure);
        }

        return std::optional<MappedFile>{MappedFile(
            std::move(storedPath),
            reinterpret_cast<std::intptr_t>(fileHandle),
            reinterpret_cast<std::intptr_t>(mappingHandle),
            static_cast<std::byte*>(viewPtr),
            size
        )};
    } catch (...) {
        if (viewPtr != nullptr) {
            UnmapViewOfFile(viewPtr);
        }
        if (mappingHandle != nullptr) {
            CloseHandle(mappingHandle);
        }
        if (fileHandle != INVALID_HANDLE_VALUE) {
            CloseHandle(fileHandle);
        }
        return std::unexpected(CoreError::FileIOFailure);
    }
}

const std::byte* MappedFile::data() const noexcept {
    return data_;
}

std::byte* MappedFile::data() noexcept {
    return data_;
}

std::size_t MappedFile::size() const noexcept {
    return size_;
}

Result MappedFile::removeFile() noexcept {
    try {
        if (handle_ == -1 || handle_ == 0) {
            return std::unexpected(CoreError::FileIOFailure);
        }
        HANDLE h = reinterpret_cast<HANDLE>(handle_);
        if (h == INVALID_HANDLE_VALUE) {
            return std::unexpected(CoreError::FileIOFailure);
        }

        FILE_DISPOSITION_INFO_EX info{};
        info.Flags = FILE_DISPOSITION_FLAG_DELETE | FILE_DISPOSITION_FLAG_POSIX_SEMANTICS;

        if (!SetFileInformationByHandle(h, FileDispositionInfoEx, &info, sizeof(info))) {
            return std::unexpected(CoreError::FileIOFailure);
        }

        return {};
    } catch (...) {
        return std::unexpected(CoreError::FileIOFailure);
    }
}

bool MappedFile::processAlive(std::uint32_t pid) noexcept {
    if (pid == 0) {
        return false;
    }
    HANDLE process = OpenProcess(SYNCHRONIZE | PROCESS_QUERY_LIMITED_INFORMATION, FALSE, static_cast<DWORD>(pid));
    if (process == nullptr) {
        return GetLastError() == ERROR_ACCESS_DENIED;  // exists, owned by someone else
    }
    const bool alive = WaitForSingleObject(process, 0) == WAIT_TIMEOUT;
    CloseHandle(process);
    return alive;
}

std::uint32_t MappedFile::currentProcessId() noexcept {
    return static_cast<std::uint32_t>(GetCurrentProcessId());
}

void MappedFile::unmapAndClose() noexcept {
    if (data_ != nullptr) {
        UnmapViewOfFile(data_);
        data_ = nullptr;
    }
    size_ = 0;
    if (mapping_handle_ != -1 && mapping_handle_ != 0) {
        CloseHandle(reinterpret_cast<HANDLE>(mapping_handle_));
        mapping_handle_ = -1;
    } else {
        mapping_handle_ = -1;
    }
    if (handle_ != -1 && handle_ != 0 && reinterpret_cast<HANDLE>(handle_) != INVALID_HANDLE_VALUE) {
        CloseHandle(reinterpret_cast<HANDLE>(handle_));
        handle_ = -1;
    } else {
        handle_ = -1;
    }
    path_.clear();
}

} // namespace atugcc::core::detail
