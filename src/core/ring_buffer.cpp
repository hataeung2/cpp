/**
 * @file ring_buffer.cpp
 * @brief RingBuffer<> and DbgBuf implementation.
 */

#include "atugcc/core/ring_buffer.hpp"
#include "atugcc/core/log_queue.hpp"

#include <cstring>
#include <string>

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

} // namespace atugcc::core