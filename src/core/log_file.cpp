#include "log_file.hpp"

#include <algorithm>
#include <utility>

#if defined(_WIN32)
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#else
#include <fcntl.h>
#include <unistd.h>
#include <cerrno>
#endif

namespace atugcc::core::detail {

LogFile::LogFile(std::intptr_t handle) noexcept
    : handle_(handle) {
}

LogFile::~LogFile() noexcept {
    close();
}

LogFile::LogFile(LogFile&& other) noexcept
    : handle_(std::exchange(other.handle_, -1)) {
}

LogFile& LogFile::operator=(LogFile&& other) noexcept {
    if (this != &other) {
        close();
        handle_ = std::exchange(other.handle_, -1);
    }
    return *this;
}

Expected<LogFile> LogFile::open(const std::filesystem::path& path) noexcept {
    try {
        if (path.has_parent_path()) {
            std::error_code ec;
            std::filesystem::create_directories(path.parent_path(), ec);
            if (ec) {
                return std::unexpected(CoreError::FileIOFailure);
            }
        }
#if defined(_WIN32)
        std::wstring wpath = path.wstring();
        HANDLE h = CreateFileW(
            wpath.c_str(),
            FILE_APPEND_DATA,
            FILE_SHARE_READ | FILE_SHARE_WRITE,
            nullptr,
            OPEN_ALWAYS,
            FILE_ATTRIBUTE_NORMAL,
            nullptr
        );
        if (h == INVALID_HANDLE_VALUE) {
            return std::unexpected(CoreError::FileIOFailure);
        }
        return LogFile(reinterpret_cast<std::intptr_t>(h));
#else
        int fd = ::open(path.c_str(), O_WRONLY | O_CREAT | O_APPEND | O_CLOEXEC, 0644);
        if (fd < 0) {
            return std::unexpected(CoreError::FileIOFailure);
        }
        return LogFile(static_cast<std::intptr_t>(fd));
#endif
    } catch (const std::exception&) {
        return std::unexpected(CoreError::FileIOFailure);
    } catch (...) {
        return std::unexpected(CoreError::FileIOFailure);
    }
}

Result LogFile::write(std::string_view text) noexcept {
    if (!isOpen()) {
        return std::unexpected(CoreError::FileIOFailure);
    }
#if defined(_WIN32)
    HANDLE h = reinterpret_cast<HANDLE>(handle_);
    const char* ptr = text.data();
    std::size_t remaining = text.size();
    while (remaining > 0) {
        constexpr std::size_t kMaxChunk = 64 * 1024 * 1024;
        DWORD toWrite = static_cast<DWORD>(std::min(remaining, kMaxChunk));
        DWORD written = 0;
        if (!WriteFile(h, ptr, toWrite, &written, nullptr) || written == 0) {
            return std::unexpected(CoreError::FileIOFailure);
        }
        ptr += written;
        remaining -= written;
    }
    return {};
#else
    int fd = static_cast<int>(handle_);
    const char* ptr = text.data();
    std::size_t remaining = text.size();
    while (remaining > 0) {
        ssize_t n = ::write(fd, ptr, remaining);
        if (n < 0) {
            if (errno == EINTR) {
                continue;
            }
            return std::unexpected(CoreError::FileIOFailure);
        }
        if (n == 0) {
            return std::unexpected(CoreError::FileIOFailure);
        }
        ptr += n;
        remaining -= static_cast<std::size_t>(n);
    }
    return {};
#endif
}

Result LogFile::sync() noexcept {
    if (!isOpen()) {
        return std::unexpected(CoreError::FileIOFailure);
    }
#if defined(_WIN32)
    HANDLE h = reinterpret_cast<HANDLE>(handle_);
    if (!FlushFileBuffers(h)) {
        return std::unexpected(CoreError::FileIOFailure);
    }
    return {};
#else
    int fd = static_cast<int>(handle_);
    int res = ::fsync(fd);
    while (res < 0 && errno == EINTR) {
        res = ::fsync(fd);
    }
    if (res < 0) {
        return std::unexpected(CoreError::FileIOFailure);
    }
    return {};
#endif
}

void LogFile::close() noexcept {
    if (isOpen()) {
#if defined(_WIN32)
        CloseHandle(reinterpret_cast<HANDLE>(handle_));
#else
        ::close(static_cast<int>(handle_));
#endif
        handle_ = -1;
    }
}

bool LogFile::isOpen() const noexcept {
#if defined(_WIN32)
    return handle_ != -1 && handle_ != 0;
#else
    return handle_ >= 0;
#endif
}

} // namespace atugcc::core::detail
