#pragma once

/**
 * @file log_registry.hpp
 * @brief Thread buffer registry and lifecycle management (Design D2).
 *
 * Thread Model & Lifetimes:
 *   - Per-Thread Buffers:
 *       Each producing thread logs into an independent SPSC ThreadLogBuffer.
 *       On first use, threadBuffer() attempts to reuse an existing retired node
 *       from the registry whose buffer has been fully drained (readPos == writePos)
 *       and whose slot count matches currentSlotCount(). If no suitable node is
 *       available, a new RegistryNode and ThreadLogBuffer are allocated and pushed
 *       to the global singly-linked list via atomic CAS on head.
 *   - Indefinite Lifetimes (D2):
 *       Registry nodes, ThreadLogBuffer blocks, and alternate signal stacks are
 *       NEVER freed during the lifetime of the process. This guarantees signal-safe
 *       inspection during crash dumps, even if crashes occur after static destructors
 *       have begun or completed.
 *   - Thread Termination:
 *       When a thread exits, its thread_local handle destructor marks the buffer
 *       retired (bit0 in flags) and resets inUse to false via a release store.
 *       The buffer remains readable by the consumer thread until all pending
 *       records are delivered.
 *   - Post-Destruction Logging:
 *       If threadBuffer() is invoked on a thread after its thread_local handle has
 *       already been destroyed (e.g. from the destructor of another thread_local
 *       object declared in a different translation unit), a thread_local destroyed
 *       flag prevents access to the dead handle. Instead, a fresh RegistryNode is
 *       acquired and left in use (inUse remains true). Leaking at most one node per
 *       such thread is documented and acceptable per design D2.
 *   - Emergency Fallback Buffer:
 *       If heap allocation fails during buffer creation (out of memory),
 *       threadBuffer() falls back to a single process-wide emergency buffer created
 *       with kMinSlots slots. Because multiple threads may share this fallback, it
 *       is not SPSC-safe. Callers must guard writes to it using an std::atomic_flag
 *       try-lock (tryLockEmergencyBuffer / unlockEmergencyBuffer) and skip writes if
 *       the lock cannot be acquired, never blocking.
 *   - Signal Safety:
 *       forEachBuffer() traverses the registry list starting from head with acquire
 *       loads. It performs zero dynamic allocations and takes no mutex locks, making
 *       it signal-safe provided the visitor callable f is signal-safe.
 */

#include <atomic>
#include <cstdint>
#include <utility>

#include "atugcc/core/detail/thread_log_buffer.hpp"

namespace atugcc::core::detail {

/**
 * @brief Singly-linked list node holding a thread's log buffer.
 */
struct RegistryNode {
    ThreadLogBuffer* buffer{nullptr};
    std::atomic<bool> inUse{false};
    RegistryNode* next{nullptr};
    void* altStack{nullptr};
};

/**
 * @brief Returns the head of the global registry list with acquire memory order.
 */
[[nodiscard]] RegistryNode* registryHead() noexcept;

/**
 * @brief Traverses all registered log buffers, invoking f(buffer) for each.
 *
 * Walks from head using acquire loads. Performs no dynamic memory allocation.
 * Signal-safe when f is signal-safe.
 */
template <class F>
void forEachBuffer(F&& f) noexcept(noexcept(f(std::declval<ThreadLogBuffer&>()))) {
    for (RegistryNode* curr = registryHead(); curr != nullptr; curr = curr->next) {
        if (curr->buffer != nullptr) {
            f(*curr->buffer);
        }
    }
}

/**
 * @brief Obtains the calling thread's log buffer, acquiring on first use.
 *
 * On first use:
 *   - Reuses an existing node with !inUse, readPos == writePos, and matching slot count.
 *   - Otherwise creates a new node + buffer with ThreadLogBuffer::create and pushes via CAS.
 *   - Increments global threadNo counter, clears retired flag, resets threadSeq to 0,
 *     and calls prepareThreadForCrash(node->altStack).
 *   - Falls back to process-wide emergency buffer if creation fails.
 */
[[nodiscard]] ThreadLogBuffer& threadBuffer() noexcept;

/**
 * @brief Peeks at the calling thread's buffer without acquiring or allocating.
 *
 * Returns nullptr if the calling thread has not yet acquired a buffer or if its
 * handle has been retired. Used by crash handlers to identify the crashing thread.
 */
[[nodiscard]] ThreadLogBuffer* peekThreadBuffer() noexcept;

/**
 * @brief Obtains and post-increments the calling thread's record sequence number.
 */
[[nodiscard]] std::uint32_t nextThreadSeq() noexcept;

/**
 * @brief Returns the current slot count configured for new thread buffers.
 */
[[nodiscard]] std::uint32_t currentSlotCount() noexcept;

/**
 * @brief Sets up an alternate signal stack (Linux) or stack guarantee (Windows).
 *
 * Implemented in thread_crash_prep.cpp.
 */
void prepareThreadForCrash(void*& altStack) noexcept;

/**
 * @brief Reads ATUGCC_LOG_SLOTS environment variable once during initialization.
 *
 * Implemented in thread_crash_prep.cpp. Returns 0 if unset, unparseable, or invalid.
 */
[[nodiscard]] std::uint32_t readEnvSlots() noexcept;

/**
 * @brief Checks if a buffer pointer is the process-wide emergency fallback buffer.
 */
[[nodiscard]] bool isEmergencyBuffer(const ThreadLogBuffer* buf) noexcept;

/**
 * @brief Tries to acquire the non-blocking lock for emergency buffer writes.
 */
[[nodiscard]] bool tryLockEmergencyBuffer() noexcept;

/**
 * @brief Releases the non-blocking lock for emergency buffer writes.
 */
void unlockEmergencyBuffer() noexcept;

} // namespace atugcc::core::detail
