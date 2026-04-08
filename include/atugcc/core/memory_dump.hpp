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
#ifdef __linux__
#include <unistd.h>
#endif
#include <fcntl.h>

#ifdef _WIN32
#define WIN32_LEAN_AND_MEAN
#include <Windows.h>
#elif defined(__linux__)
#include <csignal>
#endif

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
public:
  MemoryDump() {
#ifdef _WIN32
    impl_ = std::make_unique<ExceptionHandlerImpl_Windows>();
#elif defined(__linux__)
    impl_ = std::make_unique<ExceptionHandlerImpl_Linux>();
#endif
    if (impl_) {
      impl_->registerHandler();
    }
    // Prepare a pre-opened dump file descriptor / handle for use in crash handlers.
    try {
      namespace fs = std::filesystem;
      const fs::path dir = "log";
      std::error_code ec;
      if (!fs::exists(dir, ec)) fs::create_directories(dir, ec);
      const fs::path file_path = dir / std::format("crash_dump_{}.log", TimeStamp::str(TimeStamp::OPTION::eNothing));
#ifdef _WIN32
      // Open pre-created dump handle with conservative options: non-inheritable,
      // write-through to reduce caching, and allow read/write sharing for collectors.
      std::wstring wp = file_path.wstring();
      SECURITY_ATTRIBUTES sa{};
      sa.nLength = sizeof(sa);
      sa.lpSecurityDescriptor = nullptr;
      sa.bInheritHandle = FALSE;
      HANDLE h = CreateFileW(wp.c_str(), GENERIC_WRITE, FILE_SHARE_READ | FILE_SHARE_WRITE, &sa, CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL | FILE_FLAG_WRITE_THROUGH, NULL);
      if (h != INVALID_HANDLE_VALUE) {
        dump_handle_ = h;
      }
#else
      int fd = ::open(file_path.c_str(), O_WRONLY | O_CREAT | O_TRUNC, 0644);
      if (fd >= 0) dump_fd_ = fd;
#endif
    } catch (...) {
      /* ignore */
    }
  }

  ~MemoryDump() = default;

  [[nodiscard]] static int getDumpFd() noexcept { return dump_fd_; }
  [[nodiscard]] static void* getDumpHandle() noexcept { return dump_handle_; }

  // Explicit prepare functions to allow tests and runtime configuration to
  // set the prepared dump target. On POSIX this opens and stores an fd;
  // on Windows this opens and stores a HANDLE.
  [[nodiscard]] static atugcc::core::Result prepareDumpFile(std::filesystem::path const& p) noexcept {
#ifdef _WIN32
    (void)p;
    return std::unexpected(atugcc::core::CoreError::PlatformUnsupported);
#else
    int fd = ::open(p.c_str(), O_WRONLY | O_CREAT | O_TRUNC, 0600);
    if (fd < 0) return std::unexpected(atugcc::core::CoreError::FileIOFailure);
    dump_fd_ = fd;
    return {};
#endif
  }

  [[nodiscard]] static atugcc::core::Result prepareDumpFileWin(std::wstring const& p) noexcept {
#ifdef _WIN32
    SECURITY_ATTRIBUTES sa{};
    sa.nLength = sizeof(sa);
    sa.lpSecurityDescriptor = nullptr;
    sa.bInheritHandle = FALSE;
    HANDLE h = CreateFileW(p.c_str(), GENERIC_WRITE, FILE_SHARE_READ | FILE_SHARE_WRITE, &sa, CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL | FILE_FLAG_WRITE_THROUGH, NULL);
    if (h == INVALID_HANDLE_VALUE) return std::unexpected(atugcc::core::CoreError::FileIOFailure);
    dump_handle_ = static_cast<void*>(h);
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

private:
  static inline std::unique_ptr<ExceptionHandlerImpl> impl_{};
  static inline int dump_fd_{-1};
  static inline void* dump_handle_{nullptr};
};

} // namespace alog

#ifdef _WIN32
inline LONG WINAPI crashHdler(EXCEPTION_POINTERS* exceptionInfo) {
  // Async-signal / exception safe minimal logging. Avoid calling non-async-signal-safe
  // functions (like MemoryDump::dump) from inside this handler.
  auto safe_write = [](const char* msg) {
#ifdef _WIN32
    DWORD written = 0;
    HANDLE h = GetStdHandle(STD_ERROR_HANDLE);
    if (h != INVALID_HANDLE_VALUE && h != NULL) {
      WriteFile(h, msg, static_cast<DWORD>(std::strlen(msg)), &written, nullptr);
    }
#else
    (void)write(STDERR_FILENO, msg, std::strlen(msg));
#endif
  };
  safe_write("program crashed!\n");
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

    // Best-effort: dump thread-local ring buffers to the prepared HANDLE.
    atugcc::core::DbgBuf::dumpToHandle(alog::MemoryDump::getDumpHandle());
  } else {
    safe_write("MemoryDump deferred: please run MemoryDump::dump() after restart.\n");
  }
#else
  if (alog::MemoryDump::getDumpFd() >= 0) {
    const char* hdr = "=== CRASH DUMP START ===\n";
    (void)write(alog::MemoryDump::getDumpFd(), hdr, std::strlen(hdr));
    // Dump ring buffer raw blocks to fd
    atugcc::core::DbgBuf::dumpToFd(alog::MemoryDump::getDumpFd());
    const char* ftr = "\n=== CRASH DUMP END ===\n";
    (void)write(alog::MemoryDump::getDumpFd(), ftr, std::strlen(ftr));
  } else {
    safe_write("MemoryDump deferred: please run MemoryDump::dump() after restart.\n");
  }
#endif
  return EXCEPTION_CONTINUE_SEARCH;
}

inline void alog::ExceptionHandlerImpl_Windows::registerHandler() {
  SetUnhandledExceptionFilter(crashHdler);
}
#elif defined(__linux__)
inline void signalHandler(int signum) {
  auto safe_write = [&](const char* prefix) {
#ifdef _WIN32
    DWORD written = 0;
    HANDLE h = GetStdHandle(STD_ERROR_HANDLE);
    if (h != INVALID_HANDLE_VALUE && h != NULL) {
      WriteFile(h, prefix, static_cast<DWORD>(std::strlen(prefix)), &written, nullptr);
    }
#else
    (void)write(STDERR_FILENO, prefix, std::strlen(prefix));
#endif
  };
  char buf[64];
  int n = std::snprintf(buf, sizeof(buf), "program crashed! %d\n", signum);
  if (n > 0) safe_write(buf);
  // If we prepared a dump fd, write immediately (async-signal-safe).
#ifdef _WIN32
  if (alog::MemoryDump::getDumpHandle()) {
    char hdr[64];
    int hn = std::snprintf(hdr, sizeof(hdr), "=== CRASH DUMP START (signal %d) ===\n", signum);
    DWORD written = 0;
    WriteFile(static_cast<HANDLE>(alog::MemoryDump::getDumpHandle()), hdr, static_cast<DWORD>(hn), &written, nullptr);
    atugcc::core::DbgBuf::dumpToHandle(alog::MemoryDump::getDumpHandle());
  } else {
    safe_write("MemoryDump deferred: please run MemoryDump::dump() after restart.\n");
  }
#else
  if (alog::MemoryDump::getDumpFd() >= 0) {
    char hdr[64];
    int hn = std::snprintf(hdr, sizeof(hdr), "=== CRASH DUMP START (signal %d) ===\n", signum);
    if (hn > 0) (void)write(alog::MemoryDump::getDumpFd(), hdr, static_cast<size_t>(hn));
    atugcc::core::DbgBuf::dumpToFd(alog::MemoryDump::getDumpFd());
    const char* ftr = "\n=== CRASH DUMP END ===\n";
    (void)write(alog::MemoryDump::getDumpFd(), ftr, std::strlen(ftr));
  } else {
    safe_write("MemoryDump deferred: please run MemoryDump::dump() after restart.\n");
  }
#endif
  std::signal(signum, SIG_DFL);
  std::raise(signum);
}

inline void alog::ExceptionHandlerImpl_Linux::registerHandler() {
  std::signal(SIGSEGV, signalHandler);
}
#endif