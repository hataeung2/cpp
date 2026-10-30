#include <gtest/gtest.h>

#include <charconv>
#include <cstddef>
#include <filesystem>
#include <latch>
#include <sstream>
#include <string>
#include <string_view>
#include <system_error>
#include <thread>
#include <vector>

#include "atugcc/core/logger.hpp"
#include "atugcc/core/ring_buffer.hpp"

namespace {

TEST(LoggerTest, GlobalInstance) {
    auto& a = atugcc::core::Logger::global();
    auto& b = atugcc::core::Logger::global();

    EXPECT_EQ(&a, &b);
}

TEST(LoggerTest, FormatLog) {
    atugcc::core::Logger logger({
        .bufferCapacity = 8,
        .liveOutput = nullptr,
        .dumpDir = "log",
        .enableCrashDump = true,
    });

    logger.log(atugcc::core::Level::Info, "hello {} {}", "logger", 10);
    const auto lines = logger.snapshot();

    ASSERT_FALSE(lines.empty());
    EXPECT_NE(lines.back().find("hello logger 10"), std::string::npos);
    EXPECT_NE(lines.back().find("INFO"), std::string::npos);
}

TEST(LoggerTest, DumpOnRequest) {
    const std::filesystem::path dump_dir = std::filesystem::temp_directory_path() / "atugcc_logger_facade_test";

    atugcc::core::Logger logger({
        .bufferCapacity = 8,
        .liveOutput = nullptr,
        .dumpDir = dump_dir,
        .enableCrashDump = true,
    });

    logger.log(atugcc::core::Level::Warn, "dump test {}", 1);
    const auto result = logger.dump();

    EXPECT_TRUE(result.has_value());
}

// ─── Spec 010-08 ─────────────────────────────────────────────────────────────

atugcc::core::Logger::Config quietConfig(std::size_t capacity, std::ostream* live = nullptr) {
    return {
        .bufferCapacity = capacity,
        .liveOutput = live,
        .dumpDir = "log",
        .enableCrashDump = false,
        // These tests count lines: never drop (the default BlockThenDrop drops after 100 ms when
        // the log thread falls behind, e.g. under ThreadSanitizer; spec 010-09 Assumption 3).
        .overflow = atugcc::core::OverflowPolicy::Block,
    };
}

// "] writer <w> line <i>" -> w, i
bool parseWriterLine(std::string_view s, int& w, int& i) {
    constexpr std::string_view kWriter = "] writer ";
    constexpr std::string_view kLine = " line ";
    if (!s.starts_with(kWriter)) return false;
    s.remove_prefix(kWriter.size());
    auto [p1, e1] = std::from_chars(s.data(), s.data() + s.size(), w);
    if (e1 != std::errc{}) return false;
    s.remove_prefix(static_cast<std::size_t>(p1 - s.data()));
    if (!s.starts_with(kLine)) return false;
    s.remove_prefix(kLine.size());
    auto [p2, e2] = std::from_chars(s.data(), s.data() + s.size(), i);
    return e2 == std::errc{} && p2 == s.data() + s.size();
}

bool hasLocation(const std::string& line, int lineNo) {
    return line.find("test_logger.cpp:" + std::to_string(lineNo) + " ") != std::string::npos;
}

// AC-1: the convenience overloads record the caller's file and line, not logger.hpp.
TEST(LoggerTest, RecordsCallerLocation) {
    atugcc::core::Logger logger(quietConfig(4));

    logger.log("plain {}", 1); const int plainLine = __LINE__;
    logger.log(atugcc::core::Level::Info, "with level {}", 2); const int levelLine = __LINE__;
    logger.log("no arguments"); const int bareLine = __LINE__;

    const auto lines = logger.snapshot();
    ASSERT_EQ(lines.size(), 3u);
    EXPECT_TRUE(hasLocation(lines[0], plainLine)) << lines[0];
    EXPECT_TRUE(hasLocation(lines[1], levelLine)) << lines[1];
    EXPECT_TRUE(hasLocation(lines[2], bareLine)) << lines[2];
    EXPECT_NE(lines[0].find("[DEBUG]"), std::string::npos);
    EXPECT_NE(lines[1].find("[INFO]"), std::string::npos);
    for (const auto& line : lines) {
        EXPECT_EQ(line.find("logger.hpp:"), std::string::npos) << line;
    }
}

// Ring history: oldest first, only the newest bufferCapacity lines.
TEST(LoggerTest, SnapshotKeepsNewestInOrder) {
    atugcc::core::Logger logger(quietConfig(3));
    for (int i = 0; i < 5; ++i) {
        logger.log(atugcc::core::Level::Info, "n{}", i);
    }
    const auto lines = logger.snapshot();
    ASSERT_EQ(lines.size(), 3u);
    EXPECT_TRUE(lines[0].ends_with("] n2"));
    EXPECT_TRUE(lines[1].ends_with("] n3"));
    EXPECT_TRUE(lines[2].ends_with("] n4"));
}

// AC-3: one Logger shared by 8 writers while another thread reads snapshots (run under TSan).
TEST(LoggerTest, SharedAcrossThreads) {
    constexpr int kWriters = 8;
    constexpr int kLines = 10000;
    constexpr std::size_t kCapacity = 64;
    atugcc::core::Logger logger(quietConfig(kCapacity));

    std::latch start(kWriters + 1);
    std::latch writersDone(kWriters);
    std::vector<std::jthread> writers;
    for (int w = 0; w < kWriters; ++w) {
        writers.emplace_back([&, w] {
            start.arrive_and_wait();
            for (int i = 0; i < kLines; ++i) {
                logger.log(atugcc::core::Level::Info, "writer {} line {}", w, i);
            }
            writersDone.count_down();
        });
    }
    std::size_t snapshots = 0;
    std::jthread reader([&] {
        start.arrive_and_wait();
        while (!writersDone.try_wait()) {
            const auto lines = logger.snapshot();
            EXPECT_LE(lines.size(), kCapacity);
            ++snapshots;
        }
    });
    writers.clear();
    reader.join();

    const auto lines = logger.snapshot();
    ASSERT_EQ(lines.size(), kCapacity);
    for (const auto& line : lines) {
        EXPECT_TRUE(line.starts_with("[INFO] [")) << line;
        const auto at = line.find("] writer ");
        ASSERT_NE(at, std::string::npos) << line;
        int w = -1;
        int i = -1;
        ASSERT_TRUE(parseWriterLine(std::string_view(line).substr(at), w, i)) << line;
        EXPECT_GE(w, 0);
        EXPECT_LT(w, kWriters);
        EXPECT_GE(i, 0);
        EXPECT_LT(i, kLines);
    }
    EXPECT_GT(snapshots, 0u);
}

// AC-4: two Loggers share one live output stream; every output line stays whole.
TEST(LoggerTest, LiveOutputLinesDoNotInterleave) {
    constexpr int kThreads = 4;
    constexpr int kLines = 2000;
    const std::string padding(200, 'x');
    std::ostringstream out;
    atugcc::core::Logger first(quietConfig(8, &out));
    atugcc::core::Logger second(quietConfig(8, &out));

    std::latch start(kThreads);
    {
        std::vector<std::jthread> threads;
        for (int t = 0; t < kThreads; ++t) {
            threads.emplace_back([&, t] {
                auto& logger = (t % 2 == 0) ? first : second;
                start.arrive_and_wait();
                for (int i = 0; i < kLines; ++i) {
                    logger.log(atugcc::core::Level::Info, "t{} i{} {}", t, i, padding);
                }
            });
        }
    }

    first.flush();  // delivery is asynchronous (spec 010-09)
    std::istringstream in(out.str());
    std::string line;
    int count = 0;
    while (std::getline(in, line)) {
        ++count;
        EXPECT_EQ(line.find("[INFO] ["), 16u) << line;  // after the "HH:MM:SS.uuuuuu " prefix
        EXPECT_TRUE(line.ends_with(padding)) << line;
        EXPECT_EQ(line.find("[INFO] [", 17), std::string::npos) << line;
    }
    EXPECT_EQ(count, kThreads * kLines);
}

// 010-08 AC-9 / 010-09 D7: a line is stored once in the calling thread's buffer (that record is
// also the crash copy) and once in the history.
TEST(LoggerTest, OneBufferCopyPerLine) {
    std::string retained;
    std::size_t history = 0;
    std::jthread fresh([&] {
        atugcc::core::Logger logger(quietConfig(4));
        logger.log(atugcc::core::Level::Info, "one copy");
        history = logger.snapshot().size();
        retained = atugcc::core::DbgBuf::dump();
    });
    fresh.join();
    EXPECT_EQ(history, 1u);
    const auto first = retained.find("one copy");
    ASSERT_NE(first, std::string::npos);
    EXPECT_EQ(retained.find("one copy", first + 1), std::string::npos);
}

} // namespace
