#include "mapped_file.hpp"

#include <cerrno>
#include <cstddef>
#include <cstdint>
#include <fcntl.h>
#include <signal.h>
#include <filesystem>
#include <optional>
#include <sys/file.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>
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
    try {
        if (bytes == 0 || bytes > kMaxMappedFileBytes) {
            return std::unexpected(CoreError::FileIOFailure);
        }

        std::filesystem::path storedPath = path;
        const char* cPath = storedPath.c_str();

        int fd = -1;
        do {
            fd = ::open(cPath, O_RDWR | O_CREAT | O_EXCL | O_CLOEXEC, 0644);
        } while (fd < 0 && errno == EINTR);

        if (fd < 0) {
            return std::unexpected(CoreError::FileIOFailure);
        }

        auto cleanupAndFail = [&]() noexcept -> Expected<MappedFile> {
            ::close(fd);
            int unres = -1;
            do {
                unres = ::unlink(cPath);
            } while (unres != 0 && errno == EINTR);
            return std::unexpected(CoreError::FileIOFailure);
        };

        int flockRes = -1;
        do {
            flockRes = ::flock(fd, LOCK_EX | LOCK_NB);
        } while (flockRes < 0 && errno == EINTR);

        if (flockRes < 0) {
            return cleanupAndFail();
        }

        int ret = ::posix_fallocate(fd, 0, static_cast<off_t>(bytes));
        if (ret != 0) {
            if (ret == EOPNOTSUPP || ret == EINVAL) {
                int ftr = -1;
                do {
                    ftr = ::ftruncate(fd, static_cast<off_t>(bytes));
                } while (ftr < 0 && errno == EINTR);
                if (ftr < 0) {
                    return cleanupAndFail();
                }
            } else {
                return cleanupAndFail();
            }
        }

        void* addr = ::mmap(nullptr, bytes, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
        if (addr == MAP_FAILED) {
            return cleanupAndFail();
        }

        return MappedFile(
            std::move(storedPath),
            static_cast<std::intptr_t>(fd),
            -1,
            static_cast<std::byte*>(addr),
            bytes
        );
    } catch (...) {
        return std::unexpected(CoreError::FileIOFailure);
    }
}

Expected<std::optional<MappedFile>> MappedFile::openIfEnded(const std::filesystem::path& path) noexcept {
    try {
        std::filesystem::path storedPath = path;
        const char* cPath = storedPath.c_str();

        int fd = -1;
        do {
            fd = ::open(cPath, O_RDWR | O_CLOEXEC);
        } while (fd < 0 && errno == EINTR);

        if (fd < 0) {
            return std::unexpected(CoreError::FileIOFailure);
        }

        int flockRes = -1;
        do {
            flockRes = ::flock(fd, LOCK_EX | LOCK_NB);
        } while (flockRes < 0 && errno == EINTR);

        if (flockRes < 0) {
            const int err = errno;
            ::close(fd);
            if (err == EWOULDBLOCK || err == EAGAIN) {
                return std::optional<MappedFile>{std::nullopt};
            }
            return std::unexpected(CoreError::FileIOFailure);
        }

        struct stat st{};
        if (::fstat(fd, &st) < 0) {
            ::close(fd);
            return std::unexpected(CoreError::FileIOFailure);
        }

        if (!S_ISREG(st.st_mode) || st.st_size <= 0 || static_cast<std::uintmax_t>(st.st_size) > kMaxMappedFileBytes) {
            ::close(fd);
            return std::unexpected(CoreError::FileIOFailure);
        }

        std::size_t size = static_cast<std::size_t>(st.st_size);

        void* addr = ::mmap(nullptr, size, PROT_READ, MAP_PRIVATE, fd, 0);
        if (addr == MAP_FAILED) {
            ::close(fd);
            return std::unexpected(CoreError::FileIOFailure);
        }

        return std::optional<MappedFile>{MappedFile(
            std::move(storedPath),
            static_cast<std::intptr_t>(fd),
            -1,
            static_cast<std::byte*>(addr),
            size
        )};
    } catch (...) {
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
        if (path_.empty()) {
            return std::unexpected(CoreError::FileIOFailure);
        }

        int res = -1;
        do {
            res = ::unlink(path_.c_str());
        } while (res != 0 && errno == EINTR);

        if (res != 0) {
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
    return ::kill(static_cast<pid_t>(pid), 0) == 0 || errno == EPERM;
}

std::uint32_t MappedFile::currentProcessId() noexcept {
    return static_cast<std::uint32_t>(::getpid());
}

void MappedFile::unmapAndClose() noexcept {
    if (data_ != nullptr && size_ > 0) {
        ::munmap(data_, size_);
        data_ = nullptr;
        size_ = 0;
    }
    if (handle_ >= 0) {
        ::close(static_cast<int>(handle_));
        handle_ = -1;
    }
    mapping_handle_ = -1;
    path_.clear();
}

} // namespace atugcc::core::detail
