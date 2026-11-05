/**
 * @file scenario_logged_error_flow.cpp
 * @brief Scenario S2: Expected error + Logger + process-wide per-thread buffers across two threads.
 *
 * Demonstrates two concurrent threads encountering an Expected error (CoreError::FileIOFailure)
 * and logging it through a shared Logger backed by memory-mapped per-thread log buffers.
 * This scenario requires its own process because configureLogBuffers() sets process-wide state
 * (specifically mappedDir) that cannot be reconfigured to another directory within the same process.
 */

#include "scenario.hpp"

#include <gtest/gtest.h>

#include <algorithm>
#include <array>
#include <atomic>
#include <cstddef>
#include <cstdint>
#include <expected>
#include <filesystem>
#include <format>
#include <fstream>
#include <latch>
#include <memory>
#include <optional>
#include <source_location>
#include <string>
#include <thread>
#include <vector>

#include "atugcc/core/error.hpp"
#include "atugcc/core/log_buffer_config.hpp"
#include "atugcc/core/logger.hpp"

namespace {

namespace core = atugcc::core;

[[nodiscard]] core::Expected<int> openConfig() {
    return std::unexpected(core::CoreError::FileIOFailure);
}

} // namespace

TEST(LoggedErrorFlow, ErrorFromTwoThreadsReachesFile) {
    atugcc::test::Scenario s;
    std::unique_ptr<core::Logger> logger;
    std::atomic<std::uint_least32_t> recordedLogLine{0};

    s.step("configure per-thread log buffers", [&] {
        core::LogBufferConfig cfg;
        cfg.mappedDir = s.workDir() / "map";
        ASSERT_TRUE(core::configureLogBuffers(cfg));
    });

    s.step("open a logger that writes a file", [&] {
        core::Logger::Config cfg;
        cfg.filePath = s.workDir() / "app.log";
        cfg.enableCrashDump = false;
        cfg.dumpDir = s.workDir() / "dump";
        logger = std::make_unique<core::Logger>(cfg);
        ASSERT_NE(logger, nullptr);
    });

    s.step("two threads log the same error", [&] {
        ASSERT_NE(logger, nullptr);
        std::latch ready{2};
        std::array<std::optional<core::CoreError>, 2> threadErrors{};

        auto worker = [&](int index) {
            ready.arrive_and_wait();
            const auto result = openConfig();
            if (!result) {
                threadErrors[static_cast<std::size_t>(index)] = result.error();
                const auto logLine = std::source_location::current().line() + 1;
                logger->log(core::Level::Error, "thread {} failed: {}", index, core::to_string(result.error()));
                recordedLogLine.store(logLine, std::memory_order_relaxed);
            }
        };

        {
            std::jthread t0(worker, 0);
            std::jthread t1(worker, 1);
        }

        ASSERT_TRUE(threadErrors[0].has_value());
        EXPECT_EQ(threadErrors[0].value(), core::CoreError::FileIOFailure);
        ASSERT_TRUE(threadErrors[1].has_value());
        EXPECT_EQ(threadErrors[1].value(), core::CoreError::FileIOFailure);
        EXPECT_GT(recordedLogLine.load(), 0u);
    });

    s.step("the log file has both lines", [&] {
        ASSERT_NE(logger, nullptr);
        logger->flush();

        const auto logFile = s.workDir() / "app.log";
        std::ifstream in(logFile);
        ASSERT_TRUE(in.is_open()) << "failed to open " << logFile.string();

        std::vector<std::string> errorLines;
        std::string line;
        while (std::getline(in, line)) {
            if (line.find("FileIOFailure") != std::string::npos) {
                errorLines.push_back(line);
            }
        }

        ASSERT_EQ(errorLines.size(), 2u);

        const std::string expectedLocation = std::format("scenario_logged_error_flow.cpp:{}", recordedLogLine.load());
        for (const auto& errLine : errorLines) {
            EXPECT_NE(errLine.find(expectedLocation), std::string::npos) << errLine;
        }
        // each thread's message exactly once, in either order (the threads race to log)
        for (const std::string payload : { "thread 0 failed: FileIOFailure", "thread 1 failed: FileIOFailure" }) {
            const auto count = std::ranges::count_if(errorLines, [&](const std::string& errLine) {
                return errLine.find(payload) != std::string::npos;
            });
            EXPECT_EQ(count, 1) << payload;
        }
    });
}
