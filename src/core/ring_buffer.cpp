/**
 * @file ring_buffer.cpp
 * @brief RingBuffer<> and DbgBuf implementation.
 */

#include "atugcc/core/ring_buffer.hpp"
#include "atugcc/core/log_queue.hpp"

#include <cstring>
#include <string>
#ifdef _WIN32
#include <windows.h>
#endif

namespace atugcc::core {

// ─── flushToQueue (Specialization for Default Layout) ───────────────────────
// Only the default 128-byte block size can be flushed to the global LogQueue.
template <>
void RingBuffer<kDefaultBlockSize, kDefaultBlockCount>::flushToQueue() noexcept {
    LogQueue& q = globalLogQueue();

    while (!empty()) {
        LogBlock blk;
        // Copy the entire block (header + payload + sentinel) before advancing
        // read_idx_, so the string_view lifetime issue cannot arise.
        std::memcpy(blk.data, buf_[read_idx_], kDefaultBlockSize);
        read_idx_ = (read_idx_ + 1u) & kMask;

        if (!q.push(blk)) {
            // Queue is full: drop and count.
            ++drop_count_;
            break;
        }
    }
}

// ─── DbgBuf Implementation ───────────────────────────────────────────────────
void DbgBuf::log(std::string_view msg, Level lv) noexcept {
    instance().write(msg, lv);
}

RingBuffer<>& DbgBuf::instance() noexcept {
    // thread_local: each thread gets its own RingBuffer with default settings.
    thread_local RingBuffer<> buf;
    return buf;
}

std::string DbgBuf::dump() noexcept {
    return instance().dump();
}

void DbgBuf::dumpToFd(int fd) noexcept {
    // Delegate to the RingBuffer instance's member which has access to internals.
    instance().rawDumpToFd(fd);
}

#ifdef _WIN32
void DbgBuf::dumpToHandle(void* h) noexcept {
    if (!h) return;
    HANDLE hh = static_cast<HANDLE>(h);
    const uint32_t w = instance().writeIdx();
    // Access internals via the instance's raw member function by copying blocks
    // We cannot call instance().rawDumpToFd here on Windows; instead iterate similarly
    // Since rawDumpToFd is a template member, call the RingBuffer specialization directly
    auto &rb = instance();
    uint32_t r = rb.writeIdx();
    // The RingBuffer implementation keeps read_idx_ private; use dump() to consume
    // But dump() returns a textual concat; for Windows immediate dump we best-effort write
    // blocks by calling dump() and WriteFile the resulting string.
    std::string s = rb.dump();
    if (s.empty()) return;
    DWORD written = 0;
    const char* ptr = s.data();
    size_t remaining = s.size();
    while (remaining > 0) {
        DWORD chunk = static_cast<DWORD>(remaining > 65536 ? 65536 : remaining);
        if (!WriteFile(hh, ptr, chunk, &written, nullptr)) break;
        remaining -= written;
        ptr += written;
        if (written == 0) break;
    }
}
#endif

Expected<RingBuffer<>> makeRingBuffer(std::size_t capacity) {
    if (capacity != kDefaultBlockCount) {
        return std::unexpected(CoreError::InvalidArgument);
    }
    return Expected<RingBuffer<>>(std::in_place, kDefaultFlushThreshold);
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

} // namespace atugcc::core