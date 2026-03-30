#include <gtest/gtest.h>
#include "atugcc/core/timestamp.hpp"
#include <chrono>
#include <regex>
#include <type_traits>

namespace atugcc::core::test {

using Option = TimeStamp::Option;

TEST(TimeStampTest, FormatWithFmt) {
    // Expected: YYYY-MM-DD HH:MM:SS.mmm 
    // Example: 2026-03-30 16:30:00.123 
    std::string ts = TimeStamp::str(static_cast<TimeStamp::OptFlags>(Option::WithFmt) | static_cast<TimeStamp::OptFlags>(Option::AddSpace));
    
    std::regex pattern(R"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3} )");
    EXPECT_TRUE(std::regex_match(ts, pattern)) << "Value: " << ts;
}

TEST(TimeStampTest, FormatNone) {
    // Expected: YYYYMMDDHHMMSSmmm
    std::string ts = TimeStamp::str(static_cast<TimeStamp::OptFlags>(Option::None));
    
    std::regex pattern(R"(\d{14}\d{3})");
    EXPECT_TRUE(std::regex_match(ts, pattern)) << "Value: " << ts;
}

TEST(TimeStampTest, TimePointOverload) {
    // Use a fixed time point: 2024-01-01 00:00:00 UTC
    // We expect the result based on local time zone.
    // To make it deterministic regardless of timezone, we'll check the format mostly.
    auto tp = std::chrono::sys_days{std::chrono::January/1/2024};
    std::string ts = TimeStamp::str(tp, static_cast<TimeStamp::OptFlags>(Option::WithFmt));
    
    // Format should be: YYYY-MM-DD HH:MM:SS.mmm
    std::regex pattern(R"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})");
    EXPECT_TRUE(std::regex_match(ts, pattern)) << "Value: " << ts;
    
    // In some timezones (like West of UTC), 2024-01-01 00:00:00 UTC is still 2023.
    // So we don't strictly check for "2024" to stay cross-timezone compatible in tests.
}

TEST(TimeStampTest, NoInstantiation) {
    // Verify that TimeStamp cannot be instantiated
    static_assert(!std::is_default_constructible_v<TimeStamp>);
    // TimeStamp has deleted copy/move ops by deleting the constructor or adding explicit delete
}

TEST(TimeStampTest, BitwiseOperators) {
    auto flags = Option::WithFmt | Option::AddSpace;
    EXPECT_EQ(flags, static_cast<TimeStamp::OptFlags>(Option::WithFmt) | static_cast<TimeStamp::OptFlags>(Option::AddSpace));
    
    auto flags2 = flags | Option::None;
    EXPECT_EQ(flags2, flags);
}

} // namespace atugcc::core::test
