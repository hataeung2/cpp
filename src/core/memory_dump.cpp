#include "atugcc/core/memory_dump.hpp"
#include "crash_internal.hpp"

#include <atomic>
#include <chrono>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <filesystem>
#include <format>
#include <fstream>
#include <mutex>
#include <string>
#include <utility>

#include "atugcc/core/atime.hpp"
#include "atugcc/core/detail/log_registry.hpp"
#include "atugcc/core/detail/thread_log_buffer.hpp"
#include "atugcc/core/ring_buffer.hpp"

#ifdef _WIN32
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <Windows.h>
#elif defined(__linux__)
#include <cerrno>
#include <fcntl.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>
#endif

namespace {

std::atomic<int> gDumpFd{-1};
std::atomic<void*> gDumpHandle{nullptr};
char gExePath[4096]{0};
std::uint64_t gModuleBase{0};
std::uint64_t gSystemBaseNs{0};
std::uint64_t gSteadyBaseNs{0};
std::filesystem::path gPreparedPath{};
std::mutex gPreparedPathMutex{};
std::atomic_flag gDumpClaimed = ATOMIC_FLAG_INIT;

class AutoDumpGuard {
public:
#ifdef _WIN32
    AutoDumpGuard(HANDLE h, std::filesystem::path path)
        : auto_handle_(h), path_(std::move(path)) {
        active_guard_ = this;
    }
#else
    AutoDumpGuard(int fd, std::filesystem::path path)
        : auto_fd_(fd), path_(std::move(path)) {
        active_guard_ = this;
    }
#endif

    ~AutoDumpGuard() noexcept {
        cleanup();
    }

    AutoDumpGuard(const AutoDumpGuard&) = delete;
    AutoDumpGuard& operator=(const AutoDumpGuard&) = delete;
    AutoDumpGuard(AutoDumpGuard&&) = delete;
    AutoDumpGuard& operator=(AutoDumpGuard&&) = delete;

    void cleanup() noexcept {
#ifdef _WIN32
        if (auto_handle_ != nullptr && auto_handle_ != INVALID_HANDLE_VALUE) {
            HANDLE h = auto_handle_;
            auto_handle_ = nullptr;
            LARGE_INTEGER size{};
            bool isEmpty = (GetFileSizeEx(h, &size) != 0 && size.QuadPart == 0);
            CloseHandle(h);
            if (gDumpHandle.load(std::memory_order_relaxed) == static_cast<void*>(h)) {
                gDumpHandle.store(nullptr, std::memory_order_relaxed);
            }
            if (isEmpty && !path_.empty()) {
                DeleteFileW(path_.c_str());
            }
            path_.clear();
        }
#elif defined(__linux__)
        if (auto_fd_ >= 0) {
            int fd = auto_fd_;
            auto_fd_ = -1;
            struct stat st{};
            bool isEmpty = (::fstat(fd, &st) == 0 && st.st_size == 0);
            ::close(fd);
            if (gDumpFd.load(std::memory_order_relaxed) == fd) {
                gDumpFd.store(-1, std::memory_order_relaxed);
            }
            if (isEmpty && !path_.empty()) {
                ::unlink(path_.c_str());
            }
            path_.clear();
        }
#endif
        {
            std::lock_guard lock(gPreparedPathMutex);
            gPreparedPath.clear();
        }
        if (active_guard_ == this) {
            active_guard_ = nullptr;
        }
    }

#ifdef _WIN32
    [[nodiscard]] HANDLE handle() const noexcept { return auto_handle_; }
#else
    [[nodiscard]] int fd() const noexcept { return auto_fd_; }
#endif
    [[nodiscard]] static AutoDumpGuard* activeGuard() noexcept { return active_guard_; }

private:
#ifdef _WIN32
    HANDLE auto_handle_{nullptr};
#else
    int auto_fd_{-1};
#endif
    std::filesystem::path path_{};
    static inline AutoDumpGuard* active_guard_{nullptr};
};

void recordClockAndProcessInfo() noexcept {
    if (gSystemBaseNs == 0 && gSteadyBaseNs == 0) {
        const auto sysNow = std::chrono::system_clock::now();
        const auto steadyNow = std::chrono::steady_clock::now();
        gSystemBaseNs = static_cast<std::uint64_t>(
            std::chrono::duration_cast<std::chrono::nanoseconds>(sysNow.time_since_epoch()).count());
        gSteadyBaseNs = static_cast<std::uint64_t>(
            std::chrono::duration_cast<std::chrono::nanoseconds>(steadyNow.time_since_epoch()).count());
    }

    if (gExePath[0] == '\0') {
#ifdef _WIN32
        DWORD len = GetModuleFileNameA(nullptr, gExePath, static_cast<DWORD>(sizeof(gExePath) - 1));
        if (len > 0 && len < sizeof(gExePath)) {
            gExePath[len] = '\0';
        } else {
            gExePath[0] = '\0';
        }
#elif defined(__linux__)
        char buf[sizeof(gExePath)] = {0};
        ssize_t n = ::readlink("/proc/self/exe", buf, sizeof(buf) - 1);
        if (n > 0) {
            buf[n] = '\0';
            std::memcpy(gExePath, buf, static_cast<std::size_t>(n) + 1);
        }
#endif
    }

    if (gModuleBase == 0) {
#ifdef _WIN32
        HMODULE hm = GetModuleHandleW(nullptr);
        if (hm != nullptr) {
            gModuleBase = reinterpret_cast<std::uint64_t>(hm);
        }
#elif defined(__linux__)
        if (gExePath[0] != '\0') {
            try {
                std::ifstream maps("/proc/self/maps");
                std::string line;
                while (std::getline(maps, line)) {
                    if (line.find(gExePath) != std::string::npos) {
                        std::size_t dash = line.find('-');
                        if (dash != std::string::npos) {
                            std::string addrstr = line.substr(0, dash);
                            char* end = nullptr;
                            gModuleBase = static_cast<std::uint64_t>(std::strtoull(addrstr.c_str(), &end, 16));
                            break;
                        }
                    }
                }
            } catch (const std::exception&) {
                // Handled silently
            } catch (...) {
                // Handled silently
            }
        }
#endif
    }
}

} // namespace

namespace alog {

atugcc::core::Result MemoryDump::ensurePrepared(const std::filesystem::path& dir) noexcept {
    static std::once_flag onceFlag;
    static atugcc::core::Result outcome = std::unexpected(atugcc::core::CoreError::PlatformUnsupported);

    try {
        std::call_once(onceFlag, [&dir]() noexcept {
#if !defined(_WIN32) && !defined(__linux__)
            (void)dir;
            outcome = std::unexpected(atugcc::core::CoreError::PlatformUnsupported);
            return;
#else
            try {
                namespace fs = std::filesystem;
                std::error_code ec;
                fs::create_directories(dir, ec);
                if (ec) {
                    outcome = std::unexpected(atugcc::core::CoreError::FileIOFailure);
                    return;
                }

                const fs::path filePath = dir / std::format("crash_dump_{}.log", TimeStamp::str(TimeStamp::OPTION::eNothing));

#ifdef _WIN32
                std::wstring wp = filePath.wstring();
                SECURITY_ATTRIBUTES sa{};
                sa.nLength = sizeof(sa);
                sa.lpSecurityDescriptor = nullptr;
                sa.bInheritHandle = FALSE;
                HANDLE h = CreateFileW(wp.c_str(), GENERIC_WRITE, FILE_SHARE_READ | FILE_SHARE_WRITE, &sa, CREATE_ALWAYS,
                                       FILE_ATTRIBUTE_NORMAL | FILE_FLAG_WRITE_THROUGH, nullptr);
                if (h == INVALID_HANDLE_VALUE) {
                    outcome = std::unexpected(atugcc::core::CoreError::FileIOFailure);
                    return;
                }
                gDumpHandle.store(static_cast<void*>(h), std::memory_order_relaxed);
                {
                    std::lock_guard lock(gPreparedPathMutex);
                    gPreparedPath = filePath;
                }
                [[maybe_unused]] static AutoDumpGuard guard(h, filePath);
                (void)guard;
#elif defined(__linux__)
                int fd = ::open(filePath.c_str(), O_WRONLY | O_CREAT | O_TRUNC, 0644);
                if (fd < 0) {
                    outcome = std::unexpected(atugcc::core::CoreError::FileIOFailure);
                    return;
                }
                gDumpFd.store(fd, std::memory_order_relaxed);
                {
                    std::lock_guard lock(gPreparedPathMutex);
                    gPreparedPath = filePath;
                }
                [[maybe_unused]] static AutoDumpGuard guard(fd, filePath);
                (void)guard;
#endif
                recordClockAndProcessInfo();
                detail::installCrashHandlers();
                outcome = atugcc::core::Result{};
            } catch (const std::exception&) {
                AutoDumpGuard* guard = AutoDumpGuard::activeGuard();
                if (guard == nullptr) {
#ifdef _WIN32
                    void* h = gDumpHandle.load(std::memory_order_relaxed);
                    if (h != nullptr && h != INVALID_HANDLE_VALUE) {
                        CloseHandle(static_cast<HANDLE>(h));
                        gDumpHandle.store(nullptr, std::memory_order_relaxed);
                    }
#elif defined(__linux__)
                    int fd = gDumpFd.load(std::memory_order_relaxed);
                    if (fd >= 0) {
                        ::close(fd);
                        gDumpFd.store(-1, std::memory_order_relaxed);
                    }
#endif
                    {
                        std::lock_guard lock(gPreparedPathMutex);
                        gPreparedPath.clear();
                    }
                }
                outcome = std::unexpected(atugcc::core::CoreError::FileIOFailure);
            } catch (...) {
                AutoDumpGuard* guard = AutoDumpGuard::activeGuard();
                if (guard == nullptr) {
#ifdef _WIN32
                    void* h = gDumpHandle.load(std::memory_order_relaxed);
                    if (h != nullptr && h != INVALID_HANDLE_VALUE) {
                        CloseHandle(static_cast<HANDLE>(h));
                        gDumpHandle.store(nullptr, std::memory_order_relaxed);
                    }
#elif defined(__linux__)
                    int fd = gDumpFd.load(std::memory_order_relaxed);
                    if (fd >= 0) {
                        ::close(fd);
                        gDumpFd.store(-1, std::memory_order_relaxed);
                    }
#endif
                    {
                        std::lock_guard lock(gPreparedPathMutex);
                        gPreparedPath.clear();
                    }
                }
                outcome = std::unexpected(atugcc::core::CoreError::FileIOFailure);
            }
#endif
        });
    } catch (const std::exception&) {
        return std::unexpected(atugcc::core::CoreError::FileIOFailure);
    } catch (...) {
        return std::unexpected(atugcc::core::CoreError::FileIOFailure);
    }

    return outcome;
}

std::filesystem::path MemoryDump::preparedPath() noexcept {
    try {
        std::lock_guard lock(gPreparedPathMutex);
        return gPreparedPath;
    } catch (const std::exception&) {
        return {};
    } catch (...) {
        return {};
    }
}

int MemoryDump::getDumpFd() noexcept {
    return gDumpFd.load(std::memory_order_relaxed);
}

void* MemoryDump::getDumpHandle() noexcept {
    return gDumpHandle.load(std::memory_order_relaxed);
}

const char* MemoryDump::getExePath() noexcept {
    return gExePath;
}

std::uint64_t MemoryDump::getModuleBase() noexcept {
    return gModuleBase;
}

atugcc::core::Result MemoryDump::prepareDumpFile(const std::filesystem::path& path) noexcept {
#ifdef _WIN32
    (void)path;
    return std::unexpected(atugcc::core::CoreError::PlatformUnsupported);
#elif defined(__linux__)
    int newFd = ::open(path.c_str(), O_WRONLY | O_CREAT | O_TRUNC, 0600);
    if (newFd < 0) {
        return std::unexpected(atugcc::core::CoreError::FileIOFailure);
    }

    AutoDumpGuard* guard = AutoDumpGuard::activeGuard();
    int currentFd = gDumpFd.load(std::memory_order_relaxed);
    if (guard != nullptr && currentFd >= 0 && currentFd == guard->fd()) {
        guard->cleanup();
    } else if (currentFd >= 0) {
        ::close(currentFd);
        gDumpFd.store(-1, std::memory_order_relaxed);
    }

    {
        std::lock_guard lock(gPreparedPathMutex);
        gPreparedPath.clear();
    }

    gDumpFd.store(newFd, std::memory_order_relaxed);
    recordClockAndProcessInfo();
    return {};
#else
    (void)path;
    return std::unexpected(atugcc::core::CoreError::PlatformUnsupported);
#endif
}

atugcc::core::Result MemoryDump::prepareDumpFileWin(const std::wstring& path) noexcept {
#ifdef _WIN32
    SECURITY_ATTRIBUTES sa{};
    sa.nLength = sizeof(sa);
    sa.lpSecurityDescriptor = nullptr;
    sa.bInheritHandle = FALSE;
    HANDLE newH = CreateFileW(path.c_str(), GENERIC_WRITE, FILE_SHARE_READ | FILE_SHARE_WRITE, &sa, CREATE_ALWAYS,
                              FILE_ATTRIBUTE_NORMAL | FILE_FLAG_WRITE_THROUGH, nullptr);
    if (newH == INVALID_HANDLE_VALUE) {
        return std::unexpected(atugcc::core::CoreError::FileIOFailure);
    }

    AutoDumpGuard* guard = AutoDumpGuard::activeGuard();
    void* currentH = gDumpHandle.load(std::memory_order_relaxed);
    if (guard != nullptr && currentH != nullptr && currentH == guard->handle()) {
        guard->cleanup();
    } else if (currentH != nullptr && currentH != INVALID_HANDLE_VALUE) {
        CloseHandle(static_cast<HANDLE>(currentH));
        gDumpHandle.store(nullptr, std::memory_order_relaxed);
    }

    {
        std::lock_guard lock(gPreparedPathMutex);
        gPreparedPath.clear();
    }

    gDumpHandle.store(static_cast<void*>(newH), std::memory_order_relaxed);
    recordClockAndProcessInfo();
    return {};
#else
    (void)path;
    return std::unexpected(atugcc::core::CoreError::PlatformUnsupported);
#endif
}

atugcc::core::Result MemoryDump::dump(const std::filesystem::path& dir) noexcept {
#ifdef _WIN32
    if (gDumpHandle.load(std::memory_order_relaxed) == nullptr) {
        return std::unexpected(atugcc::core::CoreError::PlatformUnsupported);
    }
#elif defined(__linux__)
    if (gDumpFd.load(std::memory_order_relaxed) < 0) {
        return std::unexpected(atugcc::core::CoreError::PlatformUnsupported);
    }
#else
    return std::unexpected(atugcc::core::CoreError::PlatformUnsupported);
#endif

    try {
        namespace fs = std::filesystem;
        using atugcc::core::CoreError;

        std::error_code ec;
        if (!fs::exists(dir, ec)) {
            fs::create_directories(dir, ec);
            if (ec) {
                return std::unexpected(CoreError::FileIOFailure);
            }
        }

        const std::string fileName = std::format("dump{}.log", TimeStamp::str(TimeStamp::OPTION::eNothing));
        const fs::path filePath = dir / fileName;

        std::ofstream outFile(filePath, std::ios::out | std::ios::trunc);
        if (!outFile.is_open()) {
            return std::unexpected(CoreError::FileIOFailure);
        }

        outFile << atugcc::core::DbgBuf::dump() << '\n';
        if (!outFile.good()) {
            return std::unexpected(CoreError::FileIOFailure);
        }

        return {};
    } catch (const std::exception&) {
        return std::unexpected(atugcc::core::CoreError::FileIOFailure);
    } catch (...) {
        return std::unexpected(atugcc::core::CoreError::FileIOFailure);
    }
}

void MemoryDump::writeDumpNow(const char* eventType, std::uint64_t eventCode) noexcept {
#ifdef _WIN32
    void* handle = gDumpHandle.load(std::memory_order_relaxed);
    if (handle == nullptr || handle == INVALID_HANDLE_VALUE) {
        return;
    }
#elif defined(__linux__)
    int fd = gDumpFd.load(std::memory_order_relaxed);
    if (fd < 0) {
        return;
    }
#else
    return;
#endif

    const bool isManual = (eventType != nullptr && std::strcmp(eventType, "manual") == 0);
    if (!isManual) {
        if (!detail::claimDump()) {
            return;
        }
    }
    detail::writeDump(eventType, eventCode, nullptr, 0);
}

} // namespace alog

namespace alog::detail {

bool claimDump() noexcept {
    return !gDumpClaimed.test_and_set(std::memory_order_relaxed);
}

void writeAll(const void* data, std::size_t size) noexcept {
    if (data == nullptr || size == 0) {
        return;
    }
#ifdef _WIN32
    void* handle = gDumpHandle.load(std::memory_order_relaxed);
    if (handle == nullptr || handle == INVALID_HANDLE_VALUE) {
        return;
    }
    const char* ptr = static_cast<const char*>(data);
    std::size_t remaining = size;
    while (remaining > 0) {
        DWORD chunk = (remaining > static_cast<std::size_t>(MAXDWORD))
                          ? MAXDWORD
                          : static_cast<DWORD>(remaining);
        DWORD written = 0;
        if (!WriteFile(static_cast<HANDLE>(handle), ptr, chunk, &written, nullptr) || written == 0) {
            break;
        }
        ptr += written;
        remaining -= written;
    }
#elif defined(__linux__)
    int fd = gDumpFd.load(std::memory_order_relaxed);
    if (fd < 0) {
        return;
    }
    const char* ptr = static_cast<const char*>(data);
    std::size_t remaining = size;
    while (remaining > 0) {
        ssize_t n = ::write(fd, ptr, remaining);
        if (n <= 0) {
            if (n < 0 && errno == EINTR) {
                continue;
            }
            break;
        }
        ptr += n;
        remaining -= static_cast<std::size_t>(n);
    }
#else
    (void)data;
    (void)size;
#endif
}

void writeText(const char* text) noexcept {
    if (text == nullptr) {
        return;
    }
    std::size_t len = 0;
    while (text[len] != '\0') {
        ++len;
    }
    writeAll(text, len);
}

void writeDecimal(std::uint64_t val) noexcept {
    char buf[32];
    std::size_t pos = 0;
    if (val == 0) {
        buf[pos++] = '0';
    } else {
        char temp[32];
        std::size_t tpos = 0;
        while (val > 0) {
            temp[tpos++] = static_cast<char>('0' + (val % 10));
            val /= 10;
        }
        while (tpos > 0) {
            buf[pos++] = temp[--tpos];
        }
    }
    writeAll(buf, pos);
}

void writeDump(const char* eventType, std::uint64_t eventCode, const void* context, std::size_t contextSize) noexcept {
#ifdef _WIN32
    void* handle = gDumpHandle.load(std::memory_order_relaxed);
    if (handle == nullptr || handle == INVALID_HANDLE_VALUE) {
        return;
    }
#elif defined(__linux__)
    int fd = gDumpFd.load(std::memory_order_relaxed);
    if (fd < 0) {
        return;
    }
#else
    return;
#endif

    writeText("DUMP-V2\n");

    writeText("PID: ");
#ifdef _WIN32
    const std::uint64_t pid = static_cast<std::uint64_t>(::GetCurrentProcessId());
#elif defined(__linux__)
    const std::uint64_t pid = static_cast<std::uint64_t>(::getpid());
#else
    const std::uint64_t pid = 0;
#endif
    writeDecimal(pid);
    writeText("\n");

    writeText("Event-Type: ");
    writeText(eventType != nullptr ? eventType : "");
    writeText("\n");

    writeText("Event-Code: ");
    writeDecimal(eventCode);
    writeText("\n");

    writeText("Crash-Thread: ");
    const auto* threadBuf = atugcc::core::detail::peekThreadBuffer();
    const std::uint32_t crashThreadNo = (threadBuf != nullptr) ? threadBuf->threadNo() : 0;
    writeDecimal(crashThreadNo);
    writeText("\n");

    writeText("Clock-Base: ");
    writeDecimal(gSystemBaseNs);
    writeText(" ");
    writeDecimal(gSteadyBaseNs);
    writeText("\n");

    writeText("--CONTEXT-BINARY--\n");
    if (context != nullptr && contextSize > 0) {
        writeAll(context, contextSize);
    }

    writeText("--MODULES--\n");
    writeAll(&gModuleBase, sizeof(gModuleBase));
    if (gExePath[0] != '\0') {
        writeText(gExePath);
    }
    writeText("\n");

    writeText("--THREADS--\n");
    atugcc::core::detail::forEachBuffer([](const atugcc::core::detail::ThreadLogBuffer& buf) noexcept {
        writeText("--THREAD--\n");
        writeAll(buf.rawBytes(), buf.rawSize());
    });

    writeText("--END--\n");
}

} // namespace alog::detail
