#pragma once
/**
 * @file log_queue.hpp
 * @brief Shared SPSC log queue: each thread's RingBuffer flushes LogBlocks here.
 *        The Logger thread drains this queue and writes to output (file/console).
 *
 * Thread model:
 *   Producer: the write-thread (calls RingBuffer::flushToQueue())
 *   Consumer: the Logger thread (calls globalLogQueue().pop() / consume_all())
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
