/**
 * @file log_queue.cpp
 * @brief Global SPSC log queue — Meyers Singleton implementation.
 */

#include "atugcc/core/log_queue.hpp"

namespace atugcc::core {

LogQueue& globalLogQueue() noexcept {
    // Meyers Singleton: thread-safe initialisation guaranteed by C++11 §6.7.
    // spsc_queue<> with compile-time capacity uses no dynamic memory.
    static LogQueue queue;
    return queue;
}

} // namespace atugcc::core
