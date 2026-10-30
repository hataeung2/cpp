/**
 * @file log_registry.cpp
 * @brief Implementation of log buffer configuration and thread registry.
 */

#include "atugcc/core/detail/log_registry.hpp"
#include "atugcc/core/log_buffer_config.hpp"

#include <atomic>
#include <chrono>
#include <cstddef>
#include <cstdint>
#include <new>

namespace atugcc::core {

namespace {

constexpr std::size_t kDefaultSlotsPerThread = 512;
constexpr std::int64_t kDefaultDrainIntervalMs = 5;

std::atomic<std::size_t> gSlotsPerThread{kDefaultSlotsPerThread};
std::atomic<std::int64_t> gDrainIntervalMs{kDefaultDrainIntervalMs};
std::atomic<bool> gConfigInitialized{false};

void ensureConfigInitialized() noexcept {
    if (!gConfigInitialized.load(std::memory_order_acquire)) {
        static std::atomic_flag lock = ATOMIC_FLAG_INIT;
        while ((lock.test_and_set)(std::memory_order_acquire)) {
        }
        if (!gConfigInitialized.load(std::memory_order_relaxed)) {
            const std::uint32_t envSlots = detail::readEnvSlots();
            if (envSlots >= detail::kMinSlots && envSlots <= detail::kMaxSlots &&
                (envSlots & (envSlots - 1)) == 0) {
                gSlotsPerThread.store(envSlots, std::memory_order_relaxed);
            }
            gConfigInitialized.store(true, std::memory_order_release);
        }
        lock.clear(std::memory_order_release);
    }
}

} // namespace

Result configureLogBuffers(const LogBufferConfig& cfg) noexcept {
    const std::size_t slots = cfg.slotsPerThread;
    if (slots < detail::kMinSlots || slots > detail::kMaxSlots || (slots & (slots - 1)) != 0) {
        return std::unexpected(CoreError::InvalidArgument);
    }

    const auto drainMs = cfg.drainInterval.count();
    if (drainMs < 1 || drainMs > 1000) {
        return std::unexpected(CoreError::InvalidArgument);
    }

    ensureConfigInitialized();

    gSlotsPerThread.store(slots, std::memory_order_release);
    gDrainIntervalMs.store(drainMs, std::memory_order_release);

    return {};
}

LogBufferConfig currentLogBufferConfig() noexcept {
    ensureConfigInitialized();
    return LogBufferConfig{
        .slotsPerThread = gSlotsPerThread.load(std::memory_order_acquire),
        .drainInterval = std::chrono::milliseconds(gDrainIntervalMs.load(std::memory_order_acquire))
    };
}

} // namespace atugcc::core

namespace atugcc::core::detail {

namespace {

std::atomic<RegistryNode*> gRegistryHead{nullptr};
std::atomic<std::uint32_t> gThreadNoCounter{0};

// Process-wide emergency fallback buffer
std::atomic_flag gEmergencyLock = ATOMIC_FLAG_INIT;
std::atomic<ThreadLogBuffer*> gEmergencyBuffer{nullptr};
RegistryNode gEmergencyNode{};

ThreadLogBuffer& getEmergencyBuffer() noexcept {
    alignas(64) static std::byte storage[64 + kMinSlots * kSlotBytes];
    static ThreadLogBuffer* const emergencyBuffer = []() noexcept -> ThreadLogBuffer* {
        ThreadLogBuffer* buf = ThreadLogBuffer::createIn(storage, kMinSlots);
        gEmergencyBuffer.store(buf, std::memory_order_release);
        gEmergencyNode.buffer = buf;
        gEmergencyNode.inUse.store(true, std::memory_order_relaxed);
        gEmergencyNode.altStack = nullptr;

        RegistryNode* oldHead = gRegistryHead.load(std::memory_order_relaxed);
        do {
            gEmergencyNode.next = oldHead;
        } while (!(gRegistryHead.compare_exchange_weak)(oldHead, &gEmergencyNode,
                                                      std::memory_order_release,
                                                      std::memory_order_relaxed));
        return buf;
    }();
    return *emergencyBuffer;
}

RegistryNode* acquireNode(std::uint32_t targetSlots) noexcept {
    // 1. Try to reuse an existing retired node
    RegistryNode* curr = gRegistryHead.load(std::memory_order_acquire);
    while (curr != nullptr) {
        if (!curr->inUse.load(std::memory_order_relaxed)) {
            ThreadLogBuffer* buf = curr->buffer;
            if (buf != nullptr &&
                buf->readPos() == buf->writePos() &&
                buf->slotCount() == targetSlots) {
                bool expected = false;
                if ((curr->inUse.compare_exchange_strong)(expected, true,
                                                         std::memory_order_acq_rel,
                                                         std::memory_order_acquire)) {
                    if (buf->readPos() == buf->writePos() && buf->slotCount() == targetSlots) {
                        return curr;
                    }
                    curr->inUse.store(false, std::memory_order_release);
                }
            }
        }
        curr = curr->next;
    }

    // 2. Allocate a new buffer and registry node
    ThreadLogBuffer* newBuf = ThreadLogBuffer::create(targetSlots);
    if (newBuf == nullptr) {
        return nullptr;
    }

    auto* newNode = new (std::nothrow) RegistryNode();
    if (newNode == nullptr) {
        return nullptr;
    }

    newNode->buffer = newBuf;
    newNode->inUse.store(true, std::memory_order_relaxed);
    newNode->altStack = nullptr;

    // 3. Push to registry list via CAS
    RegistryNode* oldHead = gRegistryHead.load(std::memory_order_relaxed);
    do {
        newNode->next = oldHead;
    } while (!(gRegistryHead.compare_exchange_weak)(oldHead, newNode,
                                                  std::memory_order_release,
                                                  std::memory_order_relaxed));

    return newNode;
}

struct ThreadHandle {
    RegistryNode* node{nullptr};
    std::uint32_t seq{0};

    ~ThreadHandle() noexcept;
};

thread_local ThreadHandle tHandle;
thread_local bool tHandleDestroyed{false};
thread_local ThreadLogBuffer* tActiveBuffer{nullptr};
thread_local RegistryNode* tPostDestructionNode{nullptr};
thread_local std::uint32_t tPostDestructionSeq{0};

ThreadHandle::~ThreadHandle() noexcept {
    if (node != nullptr) {
        if (node->buffer != nullptr) {
            node->buffer->setRetired(true);
        }
        node->inUse.store(false, std::memory_order_release);
        node = nullptr;
    }
    tActiveBuffer = nullptr;
    tHandleDestroyed = true;
}

} // namespace

RegistryNode* registryHead() noexcept {
    return gRegistryHead.load(std::memory_order_acquire);
}

std::uint32_t currentSlotCount() noexcept {
    ensureConfigInitialized();
    return static_cast<std::uint32_t>(gSlotsPerThread.load(std::memory_order_acquire));
}

bool isEmergencyBuffer(const ThreadLogBuffer* buf) noexcept {
    return buf != nullptr && buf == gEmergencyBuffer.load(std::memory_order_acquire);
}

bool tryLockEmergencyBuffer() noexcept {
    return !(gEmergencyLock.test_and_set)(std::memory_order_acquire);
}

void unlockEmergencyBuffer() noexcept {
    gEmergencyLock.clear(std::memory_order_release);
}

ThreadLogBuffer& threadBuffer() noexcept {
    if (tHandleDestroyed) {
        // Late call after handle was destroyed (e.g. from other thread_local destructors).
        // Acquire a fresh node and intentionally leave inUse true (document D2: acceptable leak of 1 node).
        if (tPostDestructionNode == nullptr) {
            const std::uint32_t slots = currentSlotCount();
            tPostDestructionNode = acquireNode(slots);
            if (tPostDestructionNode != nullptr && tPostDestructionNode->buffer != nullptr) {
                tPostDestructionNode->buffer->setThreadNo(++gThreadNoCounter);
                tPostDestructionNode->buffer->setRetired(false);
                tPostDestructionSeq = 0;
                prepareThreadForCrash(tPostDestructionNode->altStack);
                installTerminateHandlerForThisThread();
                tActiveBuffer = tPostDestructionNode->buffer;
            }
        }
        if (tPostDestructionNode != nullptr && tPostDestructionNode->buffer != nullptr) {
            return *tPostDestructionNode->buffer;
        }
        ThreadLogBuffer& fallback = getEmergencyBuffer();
        tActiveBuffer = &fallback;
        return fallback;
    }

    if (tHandle.node == nullptr) {
        const std::uint32_t slots = currentSlotCount();
        tHandle.node = acquireNode(slots);
        if (tHandle.node != nullptr && tHandle.node->buffer != nullptr) {
            tHandle.node->buffer->setThreadNo(++gThreadNoCounter);
            tHandle.node->buffer->setRetired(false);
            tHandle.seq = 0;
            prepareThreadForCrash(tHandle.node->altStack);
            installTerminateHandlerForThisThread();
            tActiveBuffer = tHandle.node->buffer;
        }
    }

    if (tHandle.node != nullptr && tHandle.node->buffer != nullptr) {
        return *tHandle.node->buffer;
    }

    ThreadLogBuffer& fallback = getEmergencyBuffer();
    tActiveBuffer = &fallback;
    return fallback;
}

ThreadLogBuffer* peekThreadBuffer() noexcept {
    return tActiveBuffer;
}

std::uint32_t nextThreadSeq() noexcept {
    if (tHandleDestroyed) {
        return tPostDestructionSeq++;
    }
    if (tHandle.node == nullptr) {
        (void)threadBuffer();
    }
    return tHandle.seq++;
}

} // namespace atugcc::core::detail
