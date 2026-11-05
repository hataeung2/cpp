/**
 * @file scenario.hpp
 * @brief Step helper for scenario tests (spec 040-02). Test code only, not library API.
 *
 *   TEST(LoggedErrorFlow, ErrorFromTwoThreadsReachesFile) {
 *       atugcc::test::Scenario s;
 *       s.step("configure per-thread log buffers", [&] { ASSERT_TRUE(...); });
 *       s.step("the log file has both lines",      [&] { EXPECT_EQ(...); });
 *   }
 *
 * - Each step prints "[step n] <name>" and tags its failures with "step n: <name>".
 * - After a fatal failure (ASSERT_*, FAIL()) the remaining steps print "[skip n] <name>" and do
 *   not run; a non-fatal failure (EXPECT_*) does not stop them.
 * - HasFatalFailure() sees the calling thread only: join threads inside the step that starts them
 *   and assert on the scenario thread.
 * - workDir() = <ATUGCC_SCENARIO_WORK_ROOT>/<Suite>.<Name>, emptied when the Scenario is made and
 *   kept afterwards, so a failed scenario's files stay until the next run.
 */
#pragma once

#include <gtest/gtest.h>

#include <concepts>
#include <cstddef>
#include <filesystem>
#include <format>
#include <iostream>
#include <string>
#include <string_view>
#include <system_error>
#include <utility>

#ifndef ATUGCC_SCENARIO_WORK_ROOT
#error "ATUGCC_SCENARIO_WORK_ROOT must be defined by tests/CMakeLists.txt"
#endif

namespace atugcc::test {

class Scenario {
public:
    Scenario() {
        const auto* info = ::testing::UnitTest::GetInstance()->current_test_info();
        std::string name = info ? std::format("{}.{}", info->test_suite_name(), info->name()) : "unnamed";
        for (char& c : name) {
            if (c == '/') c = '_';  // parameterized tests: Suite/0, Name/1
        }
        workDir_ = std::filesystem::path(ATUGCC_SCENARIO_WORK_ROOT) / name;
        std::error_code ec;
        std::filesystem::remove_all(workDir_, ec);
        if (!ec) std::filesystem::create_directories(workDir_, ec);
        if (ec) ADD_FAILURE() << "cannot prepare " << workDir_.string() << ": " << ec.message();
    }

    Scenario(const Scenario&) = delete;
    Scenario& operator=(const Scenario&) = delete;
    Scenario(Scenario&&) = delete;
    Scenario& operator=(Scenario&&) = delete;

    [[nodiscard]] const std::filesystem::path& workDir() const noexcept { return workDir_; }

    // Runs fn() as step n; returns whether the step ended without a fatal failure.
    template <std::invocable F>
    bool step(std::string_view name, F&& fn) {
        const std::size_t n = ++index_;
        // a fatal failure before the first step (e.g. in a fixture) stops every step too
        if (stopped_ || ::testing::Test::HasFatalFailure()) {
            stopped_ = true;
            std::cout << "[skip " << n << "] " << name << std::endl;
            return false;
        }
        std::cout << "[step " << n << "] " << name << std::endl;
        {
            SCOPED_TRACE(std::format("step {}: {}", n, name));
            std::forward<F>(fn)();
        }
        if (::testing::Test::HasFatalFailure()) {
            stopped_ = true;
            return false;
        }
        return true;
    }

private:
    std::filesystem::path workDir_;
    std::size_t           index_{ 0 };
    bool                  stopped_{ false };
};

} // namespace atugcc::test
