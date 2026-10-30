#pragma once
/**
 * @file log_queue.hpp
 * @brief Global SPSC log queue that a RingBuffer can flush LogBlocks into.
 *        Nothing drains it yet; a consumer thread that owns output is task 010-09.
 *
 * Thread model:
 *   Producer: a single thread for the life of the queue (calls RingBuffer::flushToQueue()).
 *             The queue is SPSC: pushes from a second thread are a data race (KI-025).
 *             RingBuffer no longer flushes on its own by default (kNoAutoFlush, spec 010-08).
 *   Consumer: none yet; a consumer thread that owns output is task 010-09.
 *
 * NOTE: Third-party Boost headers are *not* exposed in ring_buffer.hpp.
 *       Include this header only in files that need queue access.
 */

#include <boost/lockfree/spsc_queue.hpp>
#include "atugcc/core/ring_buffer.hpp"

namespace atugcc::core {

// ─── LogBlock ────────────────────────────────────────────────────────────────
/**
 * One fixed-size block transferred from a thread-local RingBuffer to the
 * global shared queue.  The full kDefaultBlockSize bytes are copied so that
 * the Logger thread can decode the header without touching the originating
 * RingBuffer's memory.
 */
struct LogBlock {
    char data[kDefaultBlockSize];
};

// ─── LogQueue ────────────────────────────────────────────────────────────────
/**
 * SPSC lock-free queue with a compile-time fixed capacity.
 * 4096 slots × 128 bytes = 512 KiB static memory.
 * Adjust capacity via the template argument if needed at compile time.
 */
using LogQueue = boost::lockfree::spsc_queue<
    LogBlock,
    boost::lockfree::capacity<4096>
>;

// ─── Global accessor ─────────────────────────────────────────────────────────
/**
 * Returns the single global LogQueue instance (Meyers Singleton).
 * Safe to call from any thread after static initialisation.
 */
[[nodiscard]] LogQueue& globalLogQueue() noexcept;

} // namespace atugcc::core
