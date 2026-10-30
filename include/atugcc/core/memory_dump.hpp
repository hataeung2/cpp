#pragma once

#include "atugcc/core/atime.hpp"
#include "atugcc/core/error.hpp"
#include "atugcc/core/ring_buffer.hpp"

#include <filesystem>
#include <fstream>
#include <format>
#include <iostream>
#include <memory>
#include <string>
#include <cstring>
#include <cstdlib>
#include <mutex>
#include <utility>
#ifdef __linux__
#include <unistd.h>
#include <ucontext.h>
#include <dlfcn.h>
#include <limits.h>
#include <sys/stat.h>
#endif
#include <fcntl.h>

#ifdef _WIN32
#define WIN32_LEAN_AND_MEAN
#include <Windows.h>
#elif defined(__linux__)
#include <csignal>
#endif

template <typename T>
static inline void ignoreResult(T&&) noexcept {}

namespace alog {

class ExceptionHandlerImpl {
public:
  ExceptionHandlerImpl() = default;
  virtual ~ExceptionHandlerImpl() = default;

  virtual void registerHandler() = 0;

  [[nodiscard]] static atugcc::core::Result dumpToFile(const std::filesystem::path& dir) {
    namespace fs = std::filesystem;
    using atugcc::core::CoreError;

    std::error_code ec;
    if (!fs::exists(dir, ec)) {
      fs::create_directories(dir, ec);
      if (ec) {
        return std::unexpected(CoreError::FileIOFailure);
      }
    }

    const std::string file_name = std::format("dump{}.log", TimeStamp::str(TimeStamp::OPTION::eNothing));
    const fs::path file_path = dir / file_name;

    std::ofstream out_file(file_path, std::ios::out | std::ios::trunc);
    if (!out_file.is_open()) {
      return std::unexpected(CoreError::FileIOFailure);
    }

    out_file << atugcc::core::DbgBuf::dump() << '\n';
    if (!out_file.good()) {
      return std::unexpected(CoreError::FileIOFailure);
    }

    return {};
  }
};

#ifdef _WIN32
class ExceptionHandlerImpl_Windows final : public ExceptionHandlerImpl {
public:
  void registerHandler() override;
};
#elif defined(__linux__)
class ExceptionHandlerImpl_Linux final : public ExceptionHandlerImpl {
public:
  void registerHandler() override;
};
#endif

class MemoryDump {
private:
  static inline std::unique_ptr<ExceptionHandlerImpl> impl_{};
  static inline int dump_fd_{-1};
  static inline void* dump_handle_{nullptr};
  static inline std::string exe_path_{};
  static inline uint64_t module_base_{0};
  static inline std::filesystem::path prepared_path_{};
  static inline std::mutex prepared_path_mutex_{};

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
        bool is_empty = (GetFileSizeEx(h, &size) != 0 && size.QuadPart == 0);
        CloseHandle(h);
        if (dump_handle_ == static_cast<void*>(h)) {
          dump_handle_ = nullptr;
        }
        if (is_empty && !path_.empty()) {
          DeleteFileW(path_.c_str());
        }
        path_.clear();
      }
#elif defined(__linux__)
      if (auto_fd_ >= 0) {
        int fd = auto_fd_;
        auto_fd_ = -1;
        struct stat st{};
        bool is_empty = (::fstat(fd, &st) == 0 && st.st_size == 0);
        ::close(fd);
        if (dump_fd_ == fd) {
          dump_fd_ = -1;
        }
        if (is_empty && !path_.empty()) {
          ::unlink(path_.c_str());
        }
        path_.clear();
      }
#endif
      {
        std::lock_guard lock(prepared_path_mutex_);
        prepared_path_.clear();
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

public:
  MemoryDump() {
    ignoreResult(ensurePrepared("log"));
  }

  ~MemoryDump() = default;

  [[nodiscard]] static atugcc::core::Result ensurePrepared(const std::filesystem::path& dir) noexcept {
    static std::once_flag once_flag;
    static atugcc::core::Result outcome = std::unexpected(atugcc::core::CoreError::PlatformUnsupported);

    try {
      std::call_once(once_flag, [&dir]() noexcept {
#if !defined(_WIN32) && !defined(__linux__)
        outcome = std::unexpected(atugcc::core::CoreError::PlatformUnsupported);
        return;
#else
        try {
#ifdef _WIN32
          impl_ = std::make_unique<ExceptionHandlerImpl_Windows>();
#elif defined(__linux__)
          impl_ = std::make_unique<ExceptionHandlerImpl_Linux>();
#endif
          if (impl_) {
            impl_->registerHandler();
          }

          namespace fs = std::filesystem;
          std::error_code ec;
          fs::create_directories(dir, ec);
          if (ec) {
            outcome = std::unexpected(atugcc::core::CoreError::FileIOFailure);
            return;
          }

          const fs::path file_path = dir / std::format("crash_dump_{}.log", TimeStamp::str(TimeStamp::OPTION::eNothing));

#ifdef _WIN32
          std::wstring wp = file_path.wstring();
          SECURITY_ATTRIBUTES sa{};
          sa.nLength = sizeof(sa);
          sa.lpSecurityDescriptor = nullptr;
          sa.bInheritHandle = FALSE;
          HANDLE h = CreateFileW(wp.c_str(), GENERIC_WRITE, FILE_SHARE_READ | FILE_SHARE_WRITE, &sa, CREATE_ALWAYS,
                                 FILE_ATTRIBUTE_NORMAL | FILE_FLAG_WRITE_THROUGH, NULL);
          if (h == INVALID_HANDLE_VALUE) {
            outcome = std::unexpected(atugcc::core::CoreError::FileIOFailure);
            return;
          }
          dump_handle_ = static_cast<void*>(h);
          {
            std::lock_guard lock(prepared_path_mutex_);
            prepared_path_ = file_path;
          }
          [[maybe_unused]] static AutoDumpGuard guard(h, file_path);
          (void)guard;
#elif defined(__linux__)
          int fd = ::open(file_path.c_str(), O_WRONLY | O_CREAT | O_TRUNC, 0644);
          if (fd < 0) {
            outcome = std::unexpected(atugcc::core::CoreError::FileIOFailure);
            return;
          }
          dump_fd_ = fd;
          {
            std::lock_guard lock(prepared_path_mutex_);
            prepared_path_ = file_path;
          }
          [[maybe_unused]] static AutoDumpGuard guard(fd, file_path);
          (void)guard;

          char buf[PATH_MAX] = {0};
          ssize_t n = ::readlink("/proc/self/exe", buf, sizeof(buf) - 1);
          if (n > 0) {
            buf[n] = '\0';
            exe_path_ = std::string(buf);
          }
          if (!exe_path_.empty()) {
            std::ifstream maps("/proc/self/maps");
            std::string line;
            while (std::getline(maps, line)) {
              if (line.find(exe_path_) != std::string::npos) {
                size_t dash = line.find('-');
                if (dash != std::string::npos) {
                  std::string addrstr = line.substr(0, dash);
                  char* end = nullptr;
                  module_base_ = static_cast<uint64_t>(std::strtoull(addrstr.c_str(), &end, 16));
                  break;
                }
              }
            }
          }
#endif
          outcome = atugcc::core::Result{};
        } catch (...) {
          AutoDumpGuard* guard = AutoDumpGuard::activeGuard();
          if (guard == nullptr) {
#ifdef _WIN32
            if (dump_handle_ != nullptr && dump_handle_ != INVALID_HANDLE_VALUE) {
              CloseHandle(static_cast<HANDLE>(dump_handle_));
              dump_handle_ = nullptr;
            }
#elif defined(__linux__)
            if (dump_fd_ >= 0) {
              ::close(dump_fd_);
              dump_fd_ = -1;
            }
#endif
            {
              std::lock_guard lock(prepared_path_mutex_);
              prepared_path_.clear();
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

  [[nodiscard]] static std::filesystem::path preparedPath() noexcept {
    try {
      std::lock_guard lock(prepared_path_mutex_);
      return prepared_path_;
    } catch (...) {
      return {};
    }
  }

  [[nodiscard]] static int getDumpFd() noexcept { return dump_fd_; }
  [[nodiscard]] static void* getDumpHandle() noexcept { return dump_handle_; }
  [[nodiscard]] static const std::string& getExePath() noexcept { return exe_path_; }
  [[nodiscard]] static uint64_t getModuleBase() noexcept { return module_base_; }

  // prepareDumpFile and prepareDumpFileWin are not required to be thread-safe with each other.
  [[nodiscard]] static atugcc::core::Result prepareDumpFile(std::filesystem::path const& p) noexcept {
#ifdef _WIN32
    (void)p;
    return std::unexpected(atugcc::core::CoreError::PlatformUnsupported);
#else
    int new_fd = ::open(p.c_str(), O_WRONLY | O_CREAT | O_TRUNC, 0600);
    if (new_fd < 0) return std::unexpected(atugcc::core::CoreError::FileIOFailure);

    AutoDumpGuard* guard = AutoDumpGuard::activeGuard();
    if (guard != nullptr && dump_fd_ >= 0 && dump_fd_ == guard->fd()) {
      guard->cleanup();
    } else if (dump_fd_ >= 0) {
      ::close(dump_fd_);
      dump_fd_ = -1;
    }

    dump_fd_ = new_fd;
    return {};
#endif
  }

  // prepareDumpFile and prepareDumpFileWin are not required to be thread-safe with each other.
  [[nodiscard]] static atugcc::core::Result prepareDumpFileWin(std::wstring const& p) noexcept {
#ifdef _WIN32
    SECURITY_ATTRIBUTES sa{};
    sa.nLength = sizeof(sa);
    sa.lpSecurityDescriptor = nullptr;
    sa.bInheritHandle = FALSE;
    HANDLE new_h = CreateFileW(p.c_str(), GENERIC_WRITE, FILE_SHARE_READ | FILE_SHARE_WRITE, &sa, CREATE_ALWAYS,
                               FILE_ATTRIBUTE_NORMAL | FILE_FLAG_WRITE_THROUGH, NULL);
    if (new_h == INVALID_HANDLE_VALUE) return std::unexpected(atugcc::core::CoreError::FileIOFailure);

    AutoDumpGuard* guard = AutoDumpGuard::activeGuard();
    if (guard != nullptr && dump_handle_ != nullptr && dump_handle_ == guard->handle()) {
      guard->cleanup();
    } else if (dump_handle_ != nullptr && dump_handle_ != INVALID_HANDLE_VALUE) {
      CloseHandle(static_cast<HANDLE>(dump_handle_));
      dump_handle_ = nullptr;
    }

    dump_handle_ = static_cast<void*>(new_h);
    return {};
#else
    (void)p;
    return std::unexpected(atugcc::core::CoreError::PlatformUnsupported);
#endif
  }

  [[nodiscard]] static atugcc::core::Result dump(const std::filesystem::path& dir = "log") noexcept {
    if (!impl_) {
      return std::unexpected(atugcc::core::CoreError::PlatformUnsupported);
    }
    return ExceptionHandlerImpl::dumpToFile(dir);
  }
};

} // namespace alog

#ifdef _WIN32
inline LONG WINAPI crashHdler(EXCEPTION_POINTERS* exceptionInfo) {
  // Async-signal / exception safe minimal logging. Avoid calling non-async-signal-safe
  // functions (like MemoryDump::dump) from inside this handler.
  auto safeWrite = [](const char* msg) {
#ifdef _WIN32
    DWORD written = 0;
    HANDLE h = GetStdHandle(STD_ERROR_HANDLE);
    if (h != INVALID_HANDLE_VALUE && h != NULL) {
      WriteFile(h, msg, static_cast<DWORD>(std::strlen(msg)), &written, nullptr);
    }
#else
    ignoreResult(::write(STDERR_FILENO, msg, std::strlen(msg)));
#endif
  };
  safeWrite("program crashed!\n");
  // If we have a prepared dump fd/handle, write the in-memory log immediately.
#ifdef _WIN32
  if (alog::MemoryDump::getDumpHandle()) {
    // Windows: write a minimal structured header and best-effort CONTEXT binary.
    HANDLE h = static_cast<HANDLE>(alog::MemoryDump::getDumpHandle());
    char hdr[256];
    int hn = std::snprintf(hdr, sizeof(hdr), "DUMP-V1\nPID: %lu\nTID: %lu\nEvent-Type: exception\nEvent-Code: 0x%08X\n\n--BINARY-BLOCKS--\n",
                          static_cast<unsigned long>(GetCurrentProcessId()),
                          static_cast<unsigned long>(GetCurrentThreadId()),
                          exceptionInfo ? exceptionInfo->ExceptionRecord->ExceptionCode : 0u);
    DWORD written = 0;
    if (hn > 0) WriteFile(h, hdr, static_cast<DWORD>(std::strlen(hdr)), &written, nullptr);

    // Write a small marker and raw CONTEXT block (best-effort).
    const char ctxMarker[] = "--CONTEXT-BINARY--\n";
    WriteFile(h, ctxMarker, static_cast<DWORD>(std::strlen(ctxMarker)), &written, nullptr);
    if (exceptionInfo && exceptionInfo->ContextRecord) {
      WriteFile(h, exceptionInfo->ContextRecord, static_cast<DWORD>(sizeof(CONTEXT)), &written, nullptr);
    }

    // Best-effort: record main module base and filename to aid symbolization offline.
    const char modulesMarker[] = "--MODULES--\n";
    WriteFile(h, modulesMarker, static_cast<DWORD>(std::strlen(modulesMarker)), &written, nullptr);
    HMODULE hm = GetModuleHandleW(NULL);
    if (hm) {
      // Write module base as a 64-bit value for portability
      UINT64 baseAddr = reinterpret_cast<UINT64>(hm);
      WriteFile(h, &baseAddr, static_cast<DWORD>(sizeof(baseAddr)), &written, nullptr);
      // Write module filename as UTF-8 (best-effort)
      WCHAR wname[MAX_PATH] = {0};
      DWORD wn = GetModuleFileNameW(hm, wname, MAX_PATH);
      if (wn > 0) {
        char mname[1024] = {0};
        int mlen = WideCharToMultiByte(CP_UTF8, 0, wname, static_cast<int>(wn), mname, sizeof(mname)-1, NULL, NULL);
        if (mlen > 0) {
          WriteFile(h, mname, static_cast<DWORD>(mlen), &written, nullptr);
          const char nl = '\n';
          WriteFile(h, &nl, 1, &written, nullptr);
        }
      }
    }

    // Best-effort: dump thread-local ring buffers to the prepared HANDLE.
    atugcc::core::DbgBuf::dumpToHandle(alog::MemoryDump::getDumpHandle());
  } else {
    safeWrite("MemoryDump deferred: please run MemoryDump::dump() after restart.\n");
  }
#else
  if (alog::MemoryDump::getDumpFd() >= 0) {
    const char* hdr = "=== CRASH DUMP START ===\n";
    ignoreResult(::write(alog::MemoryDump::getDumpFd(), hdr, std::strlen(hdr)));
    // Dump ring buffer raw blocks to fd
    atugcc::core::DbgBuf::dumpToFd(alog::MemoryDump::getDumpFd());
    const char* ftr = "\n=== CRASH DUMP END ===\n";
    ignoreResult(::write(alog::MemoryDump::getDumpFd(), ftr, std::strlen(ftr)));
  } else {
    safeWrite("MemoryDump deferred: please run MemoryDump::dump() after restart.\n");
  }
#endif
  return EXCEPTION_CONTINUE_SEARCH;
}

inline void alog::ExceptionHandlerImpl_Windows::registerHandler() {
  SetUnhandledExceptionFilter(crashHdler);
}
#elif defined(__linux__)
static void signalHandler(int signum, siginfo_t* /*info*/, void* uctx) {
  auto safeWrite = [&](const char* prefix) {
#ifdef _WIN32
    DWORD written = 0;
    HANDLE h = GetStdHandle(STD_ERROR_HANDLE);
    if (h != INVALID_HANDLE_VALUE && h != NULL) {
      WriteFile(h, prefix, static_cast<DWORD>(std::strlen(prefix)), &written, nullptr);
    }
#else
    ignoreResult(::write(STDERR_FILENO, prefix, std::strlen(prefix)));
#endif
  };

  char buf[64];
  int n = std::snprintf(buf, sizeof(buf), "program crashed! %d\n", signum);
  if (n > 0) safeWrite(buf);

  // If we prepared a dump fd, write immediately (async-signal-safe).
#ifdef _WIN32
  if (alog::MemoryDump::getDumpHandle()) {
    char hdr[64];
    int hn = std::snprintf(hdr, sizeof(hdr), "=== CRASH DUMP START (signal %d) ===\n", signum);
    DWORD written = 0;
    WriteFile(static_cast<HANDLE>(alog::MemoryDump::getDumpHandle()), hdr, static_cast<DWORD>(hn), &written, nullptr);
    atugcc::core::DbgBuf::dumpToHandle(alog::MemoryDump::getDumpHandle());
  } else {
    safeWrite("MemoryDump deferred: please run MemoryDump::dump() after restart.\n");
  }
#else
  if (alog::MemoryDump::getDumpFd() >= 0) {
    int fd = alog::MemoryDump::getDumpFd();
    char hdr[128];
    int hn = std::snprintf(hdr, sizeof(hdr), "=== CRASH DUMP START (signal %d) ===\n", signum);
    if (hn > 0) ignoreResult(::write(fd, hdr, static_cast<size_t>(hn)));

    // Write a small marker and the raw instruction pointer (uint64_t) so an
    // external symbolizer can map the IP back to source. This mirrors the
    // Windows handler which writes CONTEXT and module info.
    const char ctxMarker[] = "--CONTEXT-BINARY--\n";
    ignoreResult(::write(fd, ctxMarker, static_cast<size_t>(std::strlen(ctxMarker))));

    uint64_t ip = 0;
#if defined(__x86_64__)
    if (uctx) {
      ucontext_t* uc = static_cast<ucontext_t*>(uctx);
      ip = static_cast<uint64_t>(uc->uc_mcontext.gregs[REG_RIP]);
    }
#elif defined(__aarch64__)
    if (uctx) {
      ucontext_t* uc = static_cast<ucontext_t*>(uctx);
      ip = static_cast<uint64_t>(uc->uc_mcontext.pc);
    }
#endif
    ignoreResult(::write(fd, &ip, sizeof(ip)));

    // Record module information (module base + filename) to allow computing
    // file-relative offsets for PIE binaries.
    const char modulesMarker[] = "--MODULES--\n";
    ignoreResult(::write(fd, modulesMarker, static_cast<size_t>(std::strlen(modulesMarker))));
    uint64_t base = alog::MemoryDump::getModuleBase();
    ignoreResult(::write(fd, &base, sizeof(base)));
    const std::string& exe = alog::MemoryDump::getExePath();
    if (!exe.empty()) {
      ignoreResult(::write(fd, exe.c_str(), exe.size()));
      const char nl = '\n';
      ignoreResult(::write(fd, &nl, 1));
    }

    // Best-effort: dump thread-local ring buffers to the prepared FD.
    atugcc::core::DbgBuf::dumpToFd(fd);

    const char* ftr = "\n=== CRASH DUMP END ===\n";
    ignoreResult(::write(fd, ftr, std::strlen(ftr)));
  } else {
    safeWrite("MemoryDump deferred: please run MemoryDump::dump() after restart.\n");
  }
#endif

  std::signal(signum, SIG_DFL);
  std::raise(signum);
}

inline void alog::ExceptionHandlerImpl_Linux::registerHandler() {
  struct sigaction sa{};
  sa.sa_sigaction = signalHandler;
  sigemptyset(&sa.sa_mask);
  sa.sa_flags = SA_SIGINFO | SA_RESETHAND;
  sigaction(SIGSEGV, &sa, nullptr);
}
#endif
