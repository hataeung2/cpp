// Thread log buffers, buffer configuration and delivery (spec 010-09 AC-6, AC-6b, AC-7, AC-8)
#include <gtest/gtest.h>

#include <algorithm>
#include <atomic>
#include <chrono>
#include <cstddef>
#include <filesystem>
#include <fstream>
#include <latch>
#include <ostream>
#include <sstream>
#include <streambuf>
#include <string>
#include <thread>
#include <vector>

#include "atugcc/core/detail/log_registry.hpp"
#include "atugcc/core/detail/thread_log_buffer.hpp"
#include "atugcc/core/log_buffer_config.hpp"
#include "atugcc/core/logger.hpp"

namespace {

using namespace std::chrono_literals;
using atugcc::core::Level;
using atugcc::core::Logger;
namespace detail = atugcc::core::detail;
namespace fs = std::filesystem;

std::size_t countLines(const std::string& text, const std::string& needle) {
    std::size_t n = 0;
    std::istringstream in(text);
    std::string line;
    while (std::getline(in, line)) {
        if (line.find(needle) != std::string::npos) ++n;
    }
    return n;
}

std::string readFile(const fs::path& p) {
    std::ifstream in(p, std::ios::binary);
    return {std::istreambuf_iterator<char>(in), std::istreambuf_iterator<char>()};
}

fs::path freshDir(const char* name) {
    const fs::path dir = fs::temp_directory_path() / "atugcc_log_buffers" / name;
    std::error_code ec;
    fs::remove_all(dir, ec);
    fs::create_directories(dir);
    return dir;
}

Logger::Config quiet(std::ostream* live = nullptr) {
    Logger::Config cfg;
    cfg.bufferCapacity = 16;
    cfg.liveOutput = live;
    cfg.enableCrashDump = false;
    cfg.overflow = atugcc::core::OverflowPolicy::Block;  // counted lines must not be dropped (overflow tests set their own)
    return cfg;
}

// ─── ThreadLogBuffer (plan D1) ───────────────────────────────────────────────

// Buffers are never freed by design (plan D1); keep the test's own ones reachable so
// LeakSanitizer does not report them.
detail::ThreadLogBuffer* makeBuffer(std::uint32_t slots) {
    static auto* kept = new std::vector<detail::ThreadLogBuffer*>;  // never destroyed: stays reachable at exit
    auto* b = detail::ThreadLogBuffer::create(slots);
    if (b != nullptr) kept->push_back(b);
    return b;
}

TEST(ThreadLogBufferTest, CreateRejectsBadSizes) {
    EXPECT_EQ(makeBuffer(32), nullptr);
    EXPECT_EQ(makeBuffer(100), nullptr);
    EXPECT_EQ(makeBuffer(1u << 17), nullptr);
    auto* b = makeBuffer(64);
    ASSERT_NE(b, nullptr);
    EXPECT_EQ(b->slotCount(), 64u);
    EXPECT_EQ(b->rawSize(), 64u + 64u * 256u);
}

TEST(ThreadLogBufferTest, NeverOverwritesUndeliveredSlots) {
    auto* b = makeBuffer(64);
    ASSERT_NE(b, nullptr);
    int written = 0;
    while (b->tryWrite(1, static_cast<std::uint32_t>(written), 1, Level::Info, "x")) ++written;
    EXPECT_EQ(written, 64);
    EXPECT_EQ(b->usedSlots(), 64u);
    EXPECT_FALSE(b->tryWrite(2, 99, 1, Level::Info, "y"));
    // a multi-slot record needs all its slots free: nothing is written partially
    b->advanceRead(b->readPos() + 2);
    EXPECT_FALSE(b->tryWrite(2, 99, 1, Level::Info, std::string(3 * 232, 'z')));
    EXPECT_TRUE(b->tryWrite(2, 99, 1, Level::Info, std::string(2 * 232, 'z')));
    EXPECT_EQ(b->usedSlots(), 64u);
}

TEST(ThreadLogBufferTest, SlotsCarryRecordFields) {
    auto* b = makeBuffer(64);
    ASSERT_NE(b, nullptr);
    const std::string text(300, 'a');
    ASSERT_TRUE(b->tryWrite(1234, 7, 42, Level::Warn, text));
    ASSERT_EQ(b->writePos(), 2u);
    const auto& h0 = b->slotHeader(0);
    const auto& h1 = b->slotHeader(1);
    EXPECT_EQ(h0.timeNs, 1234u);
    EXPECT_EQ(h0.threadSeq, 7u);
    EXPECT_EQ(h0.loggerId, 42u);
    EXPECT_EQ(h0.level, Level::Warn);
    EXPECT_EQ(h0.flags, detail::kSlotFlagFirst);
    EXPECT_EQ(h1.flags, detail::kSlotFlagLast);
    EXPECT_EQ(std::string(b->slotPayload(0)) + std::string(b->slotPayload(1)), text);
}

TEST(ThreadLogBufferTest, HugeRecordIsTruncatedVisibly) {
    auto* b = makeBuffer(64);
    ASSERT_NE(b, nullptr);
    ASSERT_TRUE(b->tryWrite(1, 0, 1, Level::Info, std::string(100 * 232, 'q')));
    EXPECT_EQ(b->usedSlots(), 32u);  // slotCount / 2
    const std::string text = detail::retainedText(*b);
    EXPECT_NE(text.find("(truncated "), std::string::npos);
    EXPECT_NE(text.find(" bytes)"), std::string::npos);
}

// ─── configureLogBuffers (AC-6b) ─────────────────────────────────────────────

TEST(LogBufferConfigTest, NewThreadsGetTheConfiguredSize) {
    const auto before = atugcc::core::currentLogBufferConfig();
    const std::uint32_t mine = detail::threadBuffer().slotCount();

    const auto invalid = [](const atugcc::core::LogBufferConfig& c) {
        const auto r = atugcc::core::configureLogBuffers(c);
        return !r.has_value() && r.error() == atugcc::core::CoreError::InvalidArgument;
    };
    EXPECT_TRUE(invalid({.slotsPerThread = 100}));
    EXPECT_TRUE(invalid({.slotsPerThread = 32}));
    EXPECT_TRUE(invalid({.slotsPerThread = 1u << 17}));
    EXPECT_TRUE(invalid({.slotsPerThread = 64, .drainInterval = 0ms}));
    EXPECT_EQ(atugcc::core::currentLogBufferConfig().slotsPerThread, before.slotsPerThread);

    ASSERT_TRUE(atugcc::core::configureLogBuffers({.slotsPerThread = 64}).has_value());
    std::uint32_t other = 0;
    std::jthread([&] { other = detail::threadBuffer().slotCount(); }).join();
    EXPECT_EQ(other, 64u);
    EXPECT_EQ(detail::threadBuffer().slotCount(), mine);  // existing buffers keep their size

    ASSERT_TRUE(atugcc::core::configureLogBuffers(before).has_value());
}

// ─── Delivery (AC-7, AC-8) ───────────────────────────────────────────────────

TEST(LoggerDeliveryTest, SyncLineIsDeliveredWhenLogReturns) {
    const fs::path dir = freshDir("sync");
    std::ostringstream live;
    Logger::Config cfg = quiet(&live);
    cfg.delivery = atugcc::core::Delivery::Sync;
    cfg.filePath = dir / "sync.log";
    Logger logger(cfg);
    logger.log(Level::Info, "sync line {}", 1);
    EXPECT_NE(live.str().find("sync line 1"), std::string::npos);  // no flush() before these checks
    EXPECT_NE(readFile(dir / "sync.log").find("sync line 1"), std::string::npos);
}

TEST(LoggerDeliveryTest, FlushDeliversEveryEarlierLine) {
    const fs::path dir = freshDir("flush");
    Logger::Config cfg = quiet();
    cfg.filePath = dir / "flush.log";
    Logger logger(cfg);
    {
        std::vector<std::jthread> threads;
        for (int t = 0; t < 4; ++t) {
            threads.emplace_back([&, t] {
                for (int i = 0; i < 1000; ++i) logger.log(Level::Info, "t{} i{}", t, i);
            });
        }
    }
    logger.flush();
    EXPECT_EQ(countLines(readFile(dir / "flush.log"), "] t"), 4000u);
    const auto lines = logger.snapshot();
    EXPECT_EQ(lines.size(), 16u);
}

TEST(LoggerDeliveryTest, DestructorDeliversItsLines) {
    // The stream dies right after the Logger: a consumer touching it later is a use-after-free
    // that ASan reports (AC-8, second half).
    auto* live = new std::ostringstream;
    {
        Logger logger(quiet(live));
        for (int i = 0; i < 5000; ++i) logger.log(Level::Info, "d{}", i);
    }
    const std::string text = live->str();
    delete live;
    for (int i = 0; i < 50; ++i) {  // more lines from other Loggers keep the consumer busy
        Logger other(quiet());
        other.log(Level::Info, "after {}", i);
    }
    EXPECT_EQ(countLines(text, "] d"), 5000u);
    EXPECT_NE(text.find("] d4999"), std::string::npos);
}

// A stream whose writes block until released: it stalls the consumer thread.
class GateBuf : public std::stringbuf {
public:
    std::atomic<bool> entered{false};
    std::atomic<bool> open{false};

protected:
    std::streamsize xsputn(const char* s, std::streamsize n) override {
        wait();
        return std::stringbuf::xsputn(s, n);
    }
    int_type overflow(int_type c) override {
        wait();
        return std::stringbuf::overflow(c);
    }

private:
    void wait() {
        entered.store(true);
        while (!open.load()) std::this_thread::sleep_for(1ms);
    }
};

TEST(LoggerOverflowTest, BlockThenDropReturnsAndReportsDrops) {
    const auto before = atugcc::core::currentLogBufferConfig();
    ASSERT_TRUE(atugcc::core::configureLogBuffers({.slotsPerThread = 64}).has_value());
    GateBuf gate;
    std::ostream gated(&gate);
    Logger::Config cfg = quiet(&gated);
    cfg.overflow = atugcc::core::OverflowPolicy::BlockThenDrop;
    cfg.overflowWait = 50ms;
    Logger logger(cfg);

    std::chrono::steady_clock::duration slowest{};
    std::jthread producer([&] {  // a new thread: gets a 64-slot buffer
        logger.log(Level::Warn, "first");
        while (!gate.entered.load()) std::this_thread::sleep_for(1ms);  // the consumer is stuck now
        for (int i = 0; i < 80; ++i) {
            const auto t0 = std::chrono::steady_clock::now();
            logger.log(Level::Info, "fill {}", i);
            slowest = std::max(slowest, std::chrono::steady_clock::now() - t0);
        }
    });
    producer.join();
    EXPECT_LT(slowest, 50ms + 50ms);
    const std::uint64_t dropped = logger.droppedCount();
    EXPECT_GT(dropped, 0u);
    gate.open = true;
    logger.flush();
    EXPECT_NE(gate.str().find("[atugcc] dropped " + std::to_string(dropped) + " lines"), std::string::npos);
    ASSERT_TRUE(atugcc::core::configureLogBuffers(before).has_value());
}

TEST(LoggerOverflowTest, BlockLosesNothing) {
    const auto before = atugcc::core::currentLogBufferConfig();
    ASSERT_TRUE(atugcc::core::configureLogBuffers({.slotsPerThread = 64}).has_value());
    GateBuf gate;
    std::ostream gated(&gate);
    Logger::Config cfg = quiet(&gated);
    cfg.overflow = atugcc::core::OverflowPolicy::Block;
    Logger logger(cfg);

    std::jthread producer([&] {
        logger.log(Level::Warn, "first");
        while (!gate.entered.load()) std::this_thread::sleep_for(1ms);
        for (int i = 0; i < 200; ++i) logger.log(Level::Info, "keep {}", i);
    });
    std::this_thread::sleep_for(200ms);  // the producer is blocked on the full buffer now
    gate.open = true;
    producer.join();
    logger.flush();
    EXPECT_EQ(logger.droppedCount(), 0u);
    EXPECT_EQ(countLines(gate.str(), "] keep "), 200u);
    ASSERT_TRUE(atugcc::core::configureLogBuffers(before).has_value());
}

}  // namespace
