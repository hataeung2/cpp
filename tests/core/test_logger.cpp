#include <gtest/gtest.h>

#include <filesystem>
#include <string>

#include "atugcc/core/logger.hpp"

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

} // namespace
