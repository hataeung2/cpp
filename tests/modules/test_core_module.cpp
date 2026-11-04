// Verifies public core API usage via import atugcc.core (spec 070-13 AC-3).
#include <gtest/gtest.h>

#include <expected>
#include <string>
#include <string_view>
#include <vector>

import atugcc.core;

namespace {

atugcc::core::Expected<int> makeExpectedValue(int input) {
    if (input > 0) {
        return input;
    }
    return std::unexpected(atugcc::core::CoreError::InvalidArgument);
}

TEST(CoreModule, LoggerSnapshot) {
    atugcc::core::Logger logger({
        .bufferCapacity = 8,
        .liveOutput = nullptr,
        .enableCrashDump = false,
        .delivery = atugcc::core::Delivery::Sync,
    });

    logger.log(atugcc::core::Level::Info, "module {}", 70013);
    const auto lines = logger.snapshot();

    ASSERT_FALSE(lines.empty());
    EXPECT_NE(lines.back().find("module 70013"), std::string::npos);
    EXPECT_NE(lines.back().find("INFO"), std::string::npos);
}

TEST(CoreModule, RingBufferRoundTrip) {
    atugcc::core::RingBuffer<> ringBuffer;
    ringBuffer.write("abc", atugcc::core::Level::Warn);

    const auto result = ringBuffer.read();
    ASSERT_TRUE(result.has_value());
    EXPECT_EQ(result->payload, "abc");
    EXPECT_EQ(result->level, atugcc::core::Level::Warn);
}

TEST(CoreModule, ExpectedError) {
    const auto positiveResult = makeExpectedValue(42);
    ASSERT_TRUE(positiveResult.has_value());
    EXPECT_EQ(*positiveResult, 42);

    const auto errorResult = makeExpectedValue(-1);
    ASSERT_FALSE(errorResult.has_value());
    EXPECT_EQ(errorResult.error(), atugcc::core::CoreError::InvalidArgument);

    const auto errorName = atugcc::core::to_string(atugcc::core::CoreError::InvalidArgument);
    EXPECT_FALSE(errorName.empty());
}

TEST(CoreModule, TimeStampOptions) {
    const auto optionMask = atugcc::core::TimeStamp::Option::WithFmt | atugcc::core::TimeStamp::Option::AddSpace;
    // WithFmt = 0x1, AddSpace = 0x2 (timestamp.hpp)
    EXPECT_EQ(optionMask, 0x3u);

    const std::string formatted = atugcc::core::TimeStamp::str(optionMask);
    EXPECT_FALSE(formatted.empty());
}

} // namespace

namespace atugcc_test {

decltype(&atugcc::core::configureLogBuffers) coreModuleConfigureAddress() {
    return &atugcc::core::configureLogBuffers;
}

// Defined here with module names; test_core_module_mixed.cpp declares it with header names.
// Parameter types are part of the symbol, so the call links only if both name the same entities.
bool moduleSideAccepts(atugcc::core::Logger& logger,
                       const atugcc::core::Expected<int>& value,
                       atugcc::core::CoreError error) {
    logger.log(atugcc::core::Level::Info, "module side {}", static_cast<int>(error));
    return !value.has_value() && value.error() == error;
}

} // namespace atugcc_test
