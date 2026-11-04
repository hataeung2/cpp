// Verifies entity identity and ODR when mixing headers and import atugcc.core (spec 070-13 AC-4).
#include <gtest/gtest.h>

#include <expected>
#include <string>

#include "atugcc/core/logger.hpp"
#include "atugcc/core/log_buffer_config.hpp"
#include "atugcc/core/error.hpp"

import atugcc.core;

namespace atugcc_test {
decltype(&atugcc::core::configureLogBuffers) coreModuleConfigureAddress();
bool moduleSideAccepts(atugcc::core::Logger& logger,
                       const atugcc::core::Expected<int>& value,
                       atugcc::core::CoreError error);
} // namespace atugcc_test

namespace {

TEST(CoreModuleMixed, SameEntities) {
    atugcc::core::Logger logger({
        .bufferCapacity = 8,
        .liveOutput = nullptr,
        .enableCrashDump = false,
        .delivery = atugcc::core::Delivery::Sync,
    });
    // A Logger, Expected and CoreError made here go to a function compiled with module names in
    // the import-only TU: it links and runs only if both TUs name the same entities.
    const atugcc::core::Expected<int> failed = std::unexpected(atugcc::core::CoreError::InvalidArgument);
    EXPECT_TRUE(atugcc_test::moduleSideAccepts(logger, failed, atugcc::core::CoreError::InvalidArgument));

    logger.log(atugcc::core::Level::Info, "module mixed {}", 70013);
    const auto lines = logger.snapshot();
    ASSERT_GE(lines.size(), 2u);
    EXPECT_NE(lines[lines.size() - 2].find("module side"), std::string::npos);
    EXPECT_NE(lines.back().find("module mixed 70013"), std::string::npos);
    EXPECT_NE(lines.back().find("INFO"), std::string::npos);
}

TEST(CoreModuleMixed, SameFunctionAcrossTranslationUnits) {
    EXPECT_EQ(&atugcc::core::configureLogBuffers, atugcc_test::coreModuleConfigureAddress());
}

} // namespace
