/**
 * @file thread_log_buffer.cpp
 * @brief Implementation of ThreadLogBuffer and retainedText helper.
 */

#include "atugcc/core/detail/thread_log_buffer.hpp"

#include <cassert>
#include <cstring>
#include <new>

namespace atugcc::core::detail {

namespace {

char* appendDigits(char* dst, std::size_t val) noexcept {
    char temp[32];
    std::size_t count = 0;
    do {
        temp[count++] = static_cast<char>('0' + (val % 10));
        val /= 10;
    } while (val > 0);
    while (count > 0) {
        *dst++ = temp[--count];
    }
    return dst;
}

} // namespace

ThreadLogBuffer::ThreadLogBuffer(std::uint32_t slotCount) noexcept {
    std::memcpy(header_.magic, kMagic.data(), kMagicBytes);
    header_.slotCount = slotCount;
    header_.slotBytes = kSlotBytes;
    header_.threadNo = 0;
    header_.flags.store(0, std::memory_order_relaxed);
    header_.writePos.store(0, std::memory_order_relaxed);
    header_.readPos.store(0, std::memory_order_relaxed);
    header_.reservePos.store(0, std::memory_order_relaxed);
    header_.reserved[0] = 0;
    header_.reserved[1] = 0;
}

Slot* ThreadLogBuffer::slots() noexcept {
    return reinterpret_cast<Slot*>(reinterpret_cast<std::byte*>(this) + sizeof(BufferHeader));
}

const Slot* ThreadLogBuffer::slots() const noexcept {
    return reinterpret_cast<const Slot*>(reinterpret_cast<const std::byte*>(this) + sizeof(BufferHeader));
}

ThreadLogBuffer* ThreadLogBuffer::createIn(void* storage, std::uint32_t slotCount) noexcept {
    if (storage == nullptr || (reinterpret_cast<std::uintptr_t>(storage) % alignof(ThreadLogBuffer)) != 0 ||
        slotCount < kMinSlots || slotCount > kMaxSlots || (slotCount & (slotCount - 1)) != 0) {
        return nullptr;
    }

    auto* buf = ::new (storage) ThreadLogBuffer(slotCount);
    std::memset(reinterpret_cast<std::byte*>(storage) + sizeof(BufferHeader), 0, static_cast<std::size_t>(slotCount) * kSlotBytes);
    return buf;
}

ThreadLogBuffer* ThreadLogBuffer::create(std::uint32_t slotCount) noexcept {
    if (slotCount < kMinSlots || slotCount > kMaxSlots || (slotCount & (slotCount - 1)) != 0) {
        return nullptr;
    }

    const std::size_t totalBytes = sizeof(BufferHeader) + static_cast<std::size_t>(slotCount) * kSlotBytes;
    void* ptr = ::operator new(totalBytes, std::align_val_t{64}, std::nothrow);
    if (!ptr) {
        return nullptr;
    }

    return createIn(ptr, slotCount);
}

bool ThreadLogBuffer::tryWrite(std::uint64_t timeNs,
                               std::uint32_t threadSeq,
                               std::uint16_t loggerId,
                               Level level,
                               std::string_view text) noexcept {
    const std::uint32_t sc = header_.slotCount;
    const std::size_t textLen = text.size();
    const std::size_t maxSlots = static_cast<std::size_t>(sc / 2);

    std::size_t neededSlots = 1;
    if (textLen > 0) {
        neededSlots = (textLen + kSlotPayloadBytes - 1) / kSlotPayloadBytes;
    }

    bool isTruncated = false;
    std::uint32_t n = 0;
    std::size_t keepLen = textLen;
    std::size_t droppedBytes = 0;

    // Buffer for suffix: "…(truncated " + N + " bytes)"
    // UTF-8 ellipsis "\xe2\x80\xa6" is 3 bytes, "(truncated " is 11 bytes, " bytes)" is 7 bytes (base 21 bytes)
    char suffixBuf[64];
    std::size_t suffixLen = 0;

    if (neededSlots > maxSlots) {
        n = static_cast<std::uint32_t>(maxSlots);
        isTruncated = true;
        const std::size_t maxPayload = maxSlots * kSlotPayloadBytes;

        auto countDigits = [](std::size_t val) -> std::size_t {
            std::size_t d = 1;
            while (val >= 10) {
                val /= 10;
                ++d;
            }
            return d;
        };

        const std::size_t base = textLen - maxPayload + 21;
        std::size_t d = countDigits(base);
        droppedBytes = base + d;
        const std::size_t newD = countDigits(droppedBytes);
        if (newD != d) {
            droppedBytes = base + newD;
            d = newD;
        }
        suffixLen = 21 + d;
        keepLen = maxPayload - suffixLen;

        std::memcpy(suffixBuf, "\xe2\x80\xa6(truncated ", 14);
        char* p = appendDigits(suffixBuf + 14, droppedBytes);
        std::memcpy(p, " bytes)", 7);
        suffixLen = static_cast<std::size_t>((p + 7) - suffixBuf);
    } else {
        n = static_cast<std::uint32_t>(neededSlots);
    }

    const std::uint64_t w = header_.writePos.load(std::memory_order_relaxed);
    const std::uint64_t r = header_.readPos.load(std::memory_order_acquire);

    // Space check: undelivered slots are never overwritten
    if (w + n - r > sc) {
        return false;
    }

    // Reserve the range before touching any slot
    header_.reservePos.store(w + n, std::memory_order_relaxed);
    // Orders reservePos before the plain slot stores below, for a crash-time reader on another
    // thread (plan D1). ThreadSanitizer does not model fences, and GCC warns about that with
    // -Wtsan; producer/consumer synchronisation does not rely on this fence (writePos release/acquire).
#if defined(__GNUC__) && !defined(__clang__)
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wtsan"
#endif
    std::atomic_thread_fence(std::memory_order_seq_cst);
#if defined(__GNUC__) && !defined(__clang__)
#pragma GCC diagnostic pop
#endif

    std::size_t offset = 0;
    const std::size_t totalBytesToWrite = isTruncated
        ? (keepLen + suffixLen)
        : textLen;

    const std::uint32_t mask = sc - 1;

    for (std::uint32_t i = 0; i < n; ++i) {
        const std::uint64_t pos = w + i;
        const std::uint32_t idx = static_cast<std::uint32_t>(pos & mask);
        Slot& slot = slots()[idx];

        slot.header.timeNs = timeNs;
        slot.header.threadSeq = threadSeq;
        slot.header.loggerId = loggerId;
        slot.header.level = level;
        slot.header.flags = static_cast<std::uint8_t>(
            (i == 0 ? kSlotFlagFirst : 0) | (i == n - 1 ? kSlotFlagLast : 0)
        );

        const std::size_t remaining = totalBytesToWrite > offset ? (totalBytesToWrite - offset) : 0;
        const std::size_t chunkLen = (remaining < kSlotPayloadBytes) ? remaining : kSlotPayloadBytes;
        slot.header.len = static_cast<std::uint16_t>(chunkLen);
        slot.header.reserved0 = 0;
        slot.header.reserved1 = 0;

        if (chunkLen > 0) {
            if (!isTruncated) {
                std::memcpy(slot.payload, text.data() + offset, chunkLen);
            } else {
                if (offset + chunkLen <= keepLen) {
                    std::memcpy(slot.payload, text.data() + offset, chunkLen);
                } else if (offset >= keepLen) {
                    const std::size_t suffixOff = offset - keepLen;
                    std::memcpy(slot.payload, suffixBuf + suffixOff, chunkLen);
                } else {
                    const std::size_t part1 = keepLen - offset;
                    const std::size_t part2 = chunkLen - part1;
                    std::memcpy(slot.payload, text.data() + offset, part1);
                    std::memcpy(slot.payload + part1, suffixBuf, part2);
                }
            }
        }
        if (chunkLen < kSlotPayloadBytes) {
            std::memset(slot.payload + chunkLen, 0, kSlotPayloadBytes - chunkLen);
        }

        offset += chunkLen;
    }

    header_.writePos.store(w + n, std::memory_order_release);
    return true;
}

std::uint64_t ThreadLogBuffer::writePos() const noexcept {
    return header_.writePos.load(std::memory_order_acquire);
}

std::uint64_t ThreadLogBuffer::readPos() const noexcept {
    return header_.readPos.load(std::memory_order_acquire);
}

std::uint64_t ThreadLogBuffer::reservePos() const noexcept {
    return header_.reservePos.load(std::memory_order_acquire);
}

void ThreadLogBuffer::advanceRead(std::uint64_t newReadPos) noexcept {
    assert(newReadPos >= header_.readPos.load(std::memory_order_relaxed));
    assert(newReadPos <= header_.writePos.load(std::memory_order_relaxed));
    header_.readPos.store(newReadPos, std::memory_order_release);
}

const SlotHeader& ThreadLogBuffer::slotHeader(std::uint64_t pos) const noexcept {
    const std::uint32_t mask = header_.slotCount - 1;
    return slots()[pos & mask].header;
}

std::string_view ThreadLogBuffer::slotPayload(std::uint64_t pos) const noexcept {
    const std::uint32_t mask = header_.slotCount - 1;
    const Slot& slot = slots()[pos & mask];
    return std::string_view{reinterpret_cast<const char*>(slot.payload), slot.header.len};
}

std::uint32_t ThreadLogBuffer::slotCount() const noexcept {
    return header_.slotCount;
}

std::size_t ThreadLogBuffer::usedSlots() const noexcept {
    const std::uint64_t w = writePos();
    const std::uint64_t r = readPos();
    return static_cast<std::size_t>(w >= r ? (w - r) : 0);
}

std::uint32_t ThreadLogBuffer::threadNo() const noexcept {
    return header_.threadNo;
}

void ThreadLogBuffer::setThreadNo(std::uint32_t no) noexcept {
    header_.threadNo = no;
}

void ThreadLogBuffer::setRetired(bool retired) noexcept {
    if (retired) {
        header_.flags |= kBufferFlagRetired;
    } else {
        header_.flags &= ~kBufferFlagRetired;
    }
}

bool ThreadLogBuffer::retired() const noexcept {
    return (header_.flags.load(std::memory_order_acquire) & kBufferFlagRetired) != 0;
}

const void* ThreadLogBuffer::rawBytes() const noexcept {
    return this;
}

std::size_t ThreadLogBuffer::rawSize() const noexcept {
    return sizeof(BufferHeader) + static_cast<std::size_t>(header_.slotCount) * kSlotBytes;
}

const BufferHeader& ThreadLogBuffer::header() const noexcept {
    return header_;
}

std::string retainedText(const ThreadLogBuffer& b) {
    const std::uint64_t w = b.writePos();
    const std::uint64_t res = b.reservePos();
    const std::uint64_t sc = b.slotCount();
    if (sc == 0 || w == 0) {
        return {};
    }

    const std::uint64_t maxActivePos = (res > w) ? res : w;
    const std::uint64_t startPos = (maxActivePos > sc) ? (maxActivePos - sc) : 0;
    const std::uint64_t endPos = w;
    if (startPos >= endPos) {
        return {};
    }

    std::string result;
    std::uint64_t pos = startPos;

    while (pos < endPos) {
        const SlotHeader& hFirst = b.slotHeader(pos);
        if ((hFirst.flags & kSlotFlagFirst) == 0) {
            ++pos;
            continue;
        }

        bool complete = false;
        std::uint64_t recordEnd = pos;

        for (std::uint64_t cur = pos; cur < endPos; ++cur) {
            const SlotHeader& hCur = b.slotHeader(cur);
            if (cur > pos) {
                if ((hCur.flags & kSlotFlagFirst) != 0 ||
                    hCur.timeNs != hFirst.timeNs ||
                    hCur.threadSeq != hFirst.threadSeq ||
                    hCur.loggerId != hFirst.loggerId) {
                    break;
                }
            }
            if ((hCur.flags & kSlotFlagLast) != 0) {
                complete = true;
                recordEnd = cur;
                break;
            }
        }

        if (complete) {
            std::size_t recordBytes = 0;
            for (std::uint64_t cur = pos; cur <= recordEnd; ++cur) {
                recordBytes += b.slotHeader(cur).len;
            }
            std::string record;
            record.reserve(recordBytes);
            for (std::uint64_t cur = pos; cur <= recordEnd; ++cur) {
                record.append(b.slotPayload(cur));
            }

            result.append(record);
            if (record.empty() || record.back() != '\n') {
                result.push_back('\n');
            }
            pos = recordEnd + 1;
        } else {
            ++pos;
        }
    }

    return result;
}

} // namespace atugcc::core::detail
