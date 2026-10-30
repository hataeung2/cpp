/**
 * @file ring_buffer.cpp
 * @brief RingBuffer<> and DbgBuf implementation.
 */

#include "atugcc/core/ring_buffer.hpp"

#include <chrono>
#include <cstring>
#include <string_view>
#ifdef _WIN32
#else
#include <unistd.h>
#endif

#include "atugcc/core/detail/log_registry.hpp"
#include "atugcc/core/detail/log_service.hpp"
#include "atugcc/core/detail/thread_log_buffer.hpp"
#include "atugcc/core/log_buffer_config.hpp"
#include <string>
#ifdef _WIN32
#include <windows.h>
#endif

namespace atugcc::core {

// ─── DbgBuf Implementation ───────────────────────────────────────────────────
void DbgBuf::log(std::string_view msg, Level lv) noexcept {
    detail::LogService::instance().submit(0,
                                          nullptr,
                                          lv,
                                          msg,
                                          Delivery::Async,
                                          OverflowPolicy::BlockThenDrop,
                                          std::chrono::milliseconds{100});
}

detail::ThreadLogBuffer& DbgBuf::instance() noexcept {
    return detail::threadBuffer();


}

std::string DbgBuf::dump() noexcept {
    return detail::retainedText(detail::threadBuffer());
}

void DbgBuf::dumpToFd(int fd) noexcept {
#ifndef _WIN32
    if (fd < 0) return;
    const detail::ThreadLogBuffer* buf = detail::peekThreadBuffer();  // never allocates (signal-safe)
    if (buf == nullptr) return;
    const char* ptr = static_cast<const char*>(buf->rawBytes());
    std::size_t remaining = buf->rawSize();
    while (remaining > 0) {
        ssize_t n = ::write(fd, ptr, remaining);
        if (n <= 0) break;
        remaining -= static_cast<std::size_t>(n);
        ptr += n;
    }
#else
    (void)fd;
#endif

}

#ifdef _WIN32
void DbgBuf::dumpToHandle(void* h) noexcept {
    if (!h) return;
    HANDLE hh = static_cast<HANDLE>(h);
    const detail::ThreadLogBuffer* buf = detail::peekThreadBuffer();  // never allocates (signal-safe)
    if (buf == nullptr) return;
    const char* ptr = static_cast<const char*>(buf->rawBytes());
    std::size_t remaining = buf->rawSize();
    while (remaining > 0) {
        DWORD toWrite = (remaining > 32768u) ? 32768u : static_cast<DWORD>(remaining);
        DWORD written = 0;
        if (!WriteFile(hh, ptr, toWrite, &written, nullptr)) return;
        if (written == 0) return;
        remaining -= written;
        ptr += written;
    }

}
#endif

Expected<RingBuffer<>> makeRingBuffer(std::size_t capacity) {
    if (capacity != kDefaultBlockCount) {
        return std::unexpected(CoreError::InvalidArgument);
    }
    return Expected<RingBuffer<>>(std::in_place);
}
template <std::size_t BS, std::size_t BC>
    requires (BC > 1 && (BC & (BC - 1)) == 0) && (BS >= 4)
void RingBuffer<BS, BC>::rawDumpToFd(int fd) const noexcept {
#ifndef _WIN32
    const uint32_t w = write_idx_.load(std::memory_order_acquire);
    uint32_t r = read_idx_;
    while (r != w) {
        const char* block = buf_[r & kMask];
        ssize_t towrite = static_cast<ssize_t>(BS);
        const char* ptr = block;
        while (towrite > 0) {
            ssize_t n = ::write(fd, ptr, static_cast<size_t>(towrite));
            if (n <= 0) break; // best-effort
            towrite -= n;
            ptr += n;
        }
        r = (r + 1u) & kMask;
    }
#else
    (void)fd; // Windows: caller should use WriteFile on the prepared HANDLE
#endif
}

#ifdef _WIN32
template <std::size_t BS, std::size_t BC>
    requires (BC > 1 && (BC & (BC - 1)) == 0) && (BS >= 4)
void RingBuffer<BS, BC>::rawDumpToHandle(void* h) const noexcept {
    if (!h) return;
    HANDLE hh = static_cast<HANDLE>(h);
    const uint32_t w = write_idx_.load(std::memory_order_acquire);
    uint32_t r = read_idx_;
    while (r != w) {
        const char* block = buf_[r & kMask];
        DWORD remaining = static_cast<DWORD>(BS);
        const char* ptr = block;
        while (remaining > 0) {
            DWORD toWrite = (remaining > 32768u) ? 32768u : remaining;
            DWORD written = 0;
            if (!WriteFile(hh, ptr, toWrite, &written, nullptr)) return; // abort on failure
            if (written == 0) return;
            remaining -= written;
            ptr += written;
        }
        r = (r + 1u) & kMask;
    }
}
#endif

} // namespace atugcc::core