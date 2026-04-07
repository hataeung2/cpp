#include <gtest/gtest.h>

#include <filesystem>
#include <string>

#include "atugcc/core/error.hpp"
#include "atugcc/core/memory_dump.hpp"
#include "atugcc/core/ring_buffer.hpp"

namespace {

using atugcc::core::CoreError;
using atugcc::core::Expected;

TEST(ErrorExpectedTest, ToStringMapping) {
    EXPECT_EQ(atugcc::core::to_string(CoreError::InvalidArgument), "InvalidArgument");
    EXPECT_EQ(atugcc::core::to_string(CoreError::FileIOFailure), "FileIOFailure");
}

TEST(ErrorExpectedTest, ExpectedMonadicChain) {
    const auto transformed = Expected<int>{21}
        .and_then([](int value) -> Expected<int> {
            return value + 1;
        })
        .transform([](int value) {
            return value * 2;
        });

    ASSERT_TRUE(transformed.has_value());
    EXPECT_EQ(transformed.value(), 44);
}

TEST(ErrorExpectedTest, ExpectedOrElseRecovery) {
    const auto recovered = Expected<int>{std::unexpected(CoreError::InvalidArgument)}
        .or_else([](CoreError error) -> Expected<int> {
            if (error == CoreError::InvalidArgument) {
                return 7;
            }
            return std::unexpected(error);
        });

    ASSERT_TRUE(recovered.has_value());
    EXPECT_EQ(recovered.value(), 7);
}

TEST(ErrorExpectedTest, MakeRingBufferCapacityValidation) {
    const auto invalid = atugcc::core::makeRingBuffer(0);
    ASSERT_FALSE(invalid.has_value());
    EXPECT_EQ(invalid.error(), CoreError::InvalidArgument);

    const auto valid = atugcc::core::makeRingBuffer(atugcc::core::kDefaultBlockCount);
    ASSERT_TRUE(valid.has_value());
    EXPECT_TRUE(valid->empty());
}

TEST(ErrorExpectedTest, MemoryDumpReturnsResult) {
    alog::MemoryDump dump_handler;
    atugcc::core::DbgBuf::log("error-expected-test", atugcc::core::Level::Info);

    const std::filesystem::path out_dir = std::filesystem::path("build") / "test_logs";
    const auto result = alog::MemoryDump::dump(out_dir);

    EXPECT_TRUE(result.has_value());
}

}  // namespace
