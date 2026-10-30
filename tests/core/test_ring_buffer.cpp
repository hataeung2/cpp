/**
 * @file test_ring_buffer.cpp
 * @brief GoogleTest suite for atugcc::core::RingBuffer<> and DbgBuf.
 */

#include <gtest/gtest.h>
#include <cstring>
#include <string>
#include <string_view>
#include <vector>
#include <thread>
#include <latch>

#include "atugcc/core/ring_buffer.hpp"

using namespace atugcc::core;

// ─── Helpers ─────────────────────────────────────────────────────────────────

// Small RingBuffer for tests: 8 blocks of 8 bytes each.
// Layout per block: [2B header][5B payload][1B sentinel]
using SmallRB = RingBuffer<8, 8>;



// ─── Header Encoding / Decoding ──────────────────────────────────────────────
TEST(RingBufferTest, HeaderEncoding) {
    // DEBUG, non-continuation, len=10
    const uint16_t h1 = encodeHeader(Level::Debug, false, 10);
    EXPECT_EQ(decodeLevel(h1), Level::Debug);
    EXPECT_FALSE(decodeCont(h1));
    EXPECT_EQ(decodeLen(h1), 10);

    // ERROR, continuation, len=125
    const uint16_t h2 = encodeHeader(Level::Error, true, 125);
    EXPECT_EQ(decodeLevel(h2), Level::Error);
    EXPECT_TRUE(decodeCont(h2));
    EXPECT_EQ(decodeLen(h2), 125);

    // WARN, non-continuation, len=0
    const uint16_t h3 = encodeHeader(Level::Warn, false, 0);
    EXPECT_EQ(decodeLevel(h3), Level::Warn);
    EXPECT_FALSE(decodeCont(h3));
    EXPECT_EQ(decodeLen(h3), 0);
}

// ─── Basic Write + Read ───────────────────────────────────────────────────────
TEST(RingBufferTest, WriteAndRead) {
    // Disable auto-flush for this test (threshold = 1.0 = never).
    RingBuffer<8, 8> rb;

    rb.write("hi", Level::Info);

    auto r = rb.read();
    ASSERT_TRUE(r.has_value());
    EXPECT_EQ(r->payload, "hi");
    EXPECT_EQ(r->level, Level::Info);
    EXPECT_FALSE(r->isContinuation);

    // Buffer should be empty now.
    EXPECT_TRUE(rb.empty());
    EXPECT_FALSE(rb.read().has_value());
}

// ─── Zero-padding of unused payload bytes ────────────────────────────────────
TEST(RingBufferTest, ZeroPaddingInBlock) {
    RingBuffer<8, 8> rb;

    rb.write("ab", Level::Debug); // 2 bytes payload, 3 bytes padding

    // Peek into the raw buffer via read() returning a string_view into buf_.
    auto r = rb.read();
    ASSERT_TRUE(r.has_value());
    EXPECT_EQ(r->payload.size(), 2u);

    // The sentinel byte right after payload must be '\0'.
    // string_view data() points into buf_; sentinel is at data()[2].
    const char* raw = r->payload.data();
    EXPECT_EQ(raw[2], '\0'); // 3rd byte after payload start = first padding byte
    EXPECT_EQ(raw[SmallRB::kPayloadBytes], '\0'); // sentinel
}

// ─── Wrap-Around: newest blocks preserved ────────────────────────────────────
TEST(RingBufferTest, WrapAround) {
    std::cout << "Starting WrapAround test\n";
    // 8 blocks, threshold=1.0 to prevent auto-flush.
    RingBuffer<8, 8> rb;

    std::cout << "Writing 9 items...\n";
    // Fill +1 block beyond capacity to force eviction.
    for (int i = 0; i < 9; ++i) {
        rb.write(std::string(1, static_cast<char>('a' + i)), Level::Debug);
        std::cout << "Wrote item " << i << " w=" << rb.writeIdx() << " used=" << rb.usedBlocks() << "\n";
    }

    std::cout << "Reading items...\n";
    // The first entry ('a') must have been evicted; we should read from 'b' onwards.
    std::string got;
    while (!rb.empty()) {
        auto r = rb.read();
        ASSERT_TRUE(r.has_value());
        got += r->payload;
        std::cout << "Read char, got sz=" << got.size() << "\n";
    }
    std::cout << "Finished reading. got=" << got << "\n";
    // The last 7 entries ('c'–'i') survive (buffer holds 8 slots, 1 empty to avoid ambiguity).
    EXPECT_EQ(got, "cdefghi");
    std::cout << "WrapAround test complete\n";
}

// ─── Eviction preserves latest N entries ─────────────────────────────────────
TEST(RingBufferTest, EvictionKeepsLatest) {
    RingBuffer<8, 8> rb;

    // Write 10 single-char messages into an 8-block buffer.
    for (int i = 0; i < 10; ++i) {
        rb.write(std::string(1, static_cast<char>('0' + i)), Level::Debug);
    }

    // We expect the 7 most recent ('3' through '9') to be readable.
    std::string got;
    while (!rb.empty()) {
        auto r = rb.read();
        ASSERT_TRUE(r.has_value());
        got += r->payload;
    }
    EXPECT_EQ(got, "3456789");
}

// ─── Continuation Blocks ─────────────────────────────────────────────────────
TEST(RingBufferTest, ContinuationBlock) {
    // Default RingBuffer (125B payload per block).
    // Use threshold=1.0 to suppress auto-flush.
    RingBuffer<128, 256> rb;

    // Construct a message longer than one block (200 chars).
    const std::string longMsg(200, 'X');
    rb.write(longMsg, Level::Warn);

    // Should read 2 blocks: first normal, second continuation.
    auto r1 = rb.read();
    ASSERT_TRUE(r1.has_value());
    EXPECT_EQ(r1->level, Level::Warn);
    EXPECT_FALSE(r1->isContinuation);
    EXPECT_EQ(r1->payload.size(), 125u);

    auto r2 = rb.read();
    ASSERT_TRUE(r2.has_value());
    EXPECT_EQ(r2->level, Level::Warn);
    EXPECT_TRUE(r2->isContinuation);
    EXPECT_EQ(r2->payload.size(), 75u); // 200 - 125

    // Reassemble and compare.
    const std::string assembled = std::string(r1->payload) + std::string(r2->payload);
    EXPECT_EQ(assembled, longMsg);

    EXPECT_TRUE(rb.empty());
}

// ─── Level is preserved across blocks ────────────────────────────────────────
TEST(RingBufferTest, LevelFilter) {
    RingBuffer<128, 256> rb;

    rb.write("debug msg", Level::Debug);
    rb.write("error msg", Level::Error);

    auto r1 = rb.read();
    ASSERT_TRUE(r1.has_value());
    EXPECT_EQ(r1->level, Level::Debug);

    auto r2 = rb.read();
    ASSERT_TRUE(r2.has_value());
    EXPECT_EQ(r2->level, Level::Error);
}

// ─── Eviction with the default layout ────────────────────────────────────────
TEST(RingBufferTest, EvictionKeepsNewestDefaultLayout) {
    // 300 single-block messages into the default layout: the oldest are evicted.
    RingBuffer<> rb;
    for (int i = 0; i < 300; ++i) {
        rb.write("m" + std::to_string(i), Level::Info);
    }

    // dropCount() counts evicted blocks: 300 written, BlockCount - 1 kept.
    EXPECT_EQ(rb.dropCount(), 300u - (kDefaultBlockCount - 1));
    EXPECT_EQ(rb.usedBlocks(), kDefaultBlockCount - 1);
    std::string last;
    std::string first;
    while (!rb.empty()) {
        auto r = rb.read();
        ASSERT_TRUE(r.has_value());
        if (first.empty()) first = std::string(r->payload);
        last = std::string(r->payload);
    }
    EXPECT_EQ(first, "m" + std::to_string(300 - (kDefaultBlockCount - 1)));
    EXPECT_EQ(last, "m299");
}

// ─── Dump output includes diagnostic warnings if eviction occurred ───────────
TEST(RingBufferTest, EvictionWarningLogged) {
    RingBuffer<8, 8> rb;

    // Write 10 items into 8-slot buffer to force at least 1 eviction.
    for (int i = 0; i < 10; ++i) {
        rb.write("x", Level::Debug);
    }

    // Read all contents via dump(), which should implicitly append the eviction warning.
    std::string content = rb.dump();
    
    // We expect the tracking warning string to be appended.
    EXPECT_NE(content.find("EVICTED due to buffer overflow"), std::string::npos);
    EXPECT_GT(rb.dropCount(), 0u);
}

// ─── DbgBuf thread_local isolation ───────────────────────────────────────────
TEST(RingBufferTest, DbgBufThreadLocalIsolation) {
    // Each thread writes to its own buffer; neither sees the other's messages.
    std::latch ready(2);
    std::vector<std::string> results(2);

    auto threadFn = [&](int idx, const char* msg) {
        ready.arrive_and_wait();
        DbgBuf::log(msg, Level::Debug);
        auto r = DbgBuf::instance().read();
        if (r) results[idx] = std::string(r->payload);
    };

    std::thread t0(threadFn, 0, "thread0");
    std::thread t1(threadFn, 1, "thread1");
    t0.join();
    t1.join();

    EXPECT_EQ(results[0], "thread0");
    EXPECT_EQ(results[1], "thread1");
}
