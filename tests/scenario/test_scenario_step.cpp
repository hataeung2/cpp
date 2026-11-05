/**
 * @file test_scenario_step.cpp
 * @brief atugcc::test::Scenario -- step helper tests (spec 040-02 AC-3)
 *
 * Test groups:
 *   ScenarioStepTest    -- in process: the step name in failure messages, output and return value, workDir
 *   ScenarioStepSelfRun -- disabled, failing on purpose: what a fatal / non-fatal failure does to later
 *                          steps, checked out of process by CTest (tests/CMakeLists.txt)
 */
#include <gtest/gtest.h>
#include <gtest/gtest-spi.h>

#include <filesystem>
#include <fstream>
#include <iostream>
#include <string>

#include "scenario.hpp"

namespace {

void runFailureMessageScenario() {
    atugcc::test::Scenario s;
    s.step("first", [] {});
    s.step("second", [] { ADD_FAILURE() << "planned"; });
}

void failFatally() {
    FAIL() << "planned before steps";
}

} // namespace

TEST(ScenarioStepTest, FailureMessageNamesTheStep) {
    EXPECT_NONFATAL_FAILURE(runFailureMessageScenario(), "step 2: second");
}

TEST(ScenarioStepTest, SuccessfulStepsReturnTrueAndPrint) {
    testing::internal::CaptureStdout();
    atugcc::test::Scenario s;
    const bool r1 = s.step("first", [] {});
    const bool r2 = s.step("second", [] {});
    const std::string output = testing::internal::GetCapturedStdout();

    EXPECT_TRUE(r1);
    EXPECT_TRUE(r2);
    EXPECT_NE(output.find("[step 1] first"), std::string::npos);
    EXPECT_NE(output.find("[step 2] second"), std::string::npos);
    EXPECT_EQ(output.find("[skip"), std::string::npos);
}

TEST(ScenarioStepTest, WorkDirIsEmptiedWhenScenarioStarts) {
    {
        atugcc::test::Scenario s1;
        const std::filesystem::path workDir1 = s1.workDir();
        EXPECT_TRUE(std::filesystem::exists(workDir1));
        EXPECT_TRUE(std::filesystem::is_directory(workDir1));
        EXPECT_EQ(workDir1.filename().string(), "ScenarioStepTest.WorkDirIsEmptiedWhenScenarioStarts");
        EXPECT_EQ(workDir1.parent_path(), std::filesystem::path(ATUGCC_SCENARIO_WORK_ROOT));

        std::ofstream leftFile(workDir1 / "left.txt");
        ASSERT_TRUE(leftFile.is_open());
        leftFile << "residual data";
        leftFile.close();
        EXPECT_TRUE(std::filesystem::exists(workDir1 / "left.txt"));
    }

    {
        atugcc::test::Scenario s2;
        const std::filesystem::path workDir2 = s2.workDir();
        EXPECT_TRUE(std::filesystem::exists(workDir2));
        EXPECT_TRUE(std::filesystem::is_directory(workDir2));
        EXPECT_TRUE((std::filesystem::is_empty)(workDir2));
    }
}

// Deliberately failing tests: what a failure does to the later steps. Inside gtest-spi's
// EXPECT_FATAL_FAILURE / EXPECT_NONFATAL_FAILURE the failure goes to a fake reporter, so
// Test::HasFatalFailure() (and HasFailure()) cannot see it and these cases cannot be checked in
// process. The CTest tests ScenarioStepFatalStops, ScenarioStepFatalBefore and
// ScenarioStepNonFatalContinues (tests/CMakeLists.txt) run each one in its own process with
// --gtest_also_run_disabled_tests and check its output with regular expressions.
TEST(ScenarioStepSelfRun, DISABLED_FatalStopsLaterSteps) {
    atugcc::test::Scenario s;
    const bool r1 = s.step("first", [] { FAIL() << "planned"; });
    const bool r2 = s.step("second", [] { std::cout << "BODY2_RAN" << std::endl; });
    std::cout << "returns=" << (r1 ? "true" : "false") << "," << (r2 ? "true" : "false") << std::endl;
}

TEST(ScenarioStepSelfRun, DISABLED_NonFatalDoesNotStopLaterSteps) {
    atugcc::test::Scenario s;
    const bool r1 = s.step("first", [] { ADD_FAILURE() << "planned"; });
    const bool r2 = s.step("second", [] { std::cout << "BODY2_RAN" << std::endl; });
    std::cout << "returns=" << (r1 ? "true" : "false") << "," << (r2 ? "true" : "false") << std::endl;
}

TEST(ScenarioStepSelfRun, DISABLED_FatalBeforeFirstStep) {
    failFatally();
    atugcc::test::Scenario s;
    s.step("first", [] { std::cout << "BODY1_RAN" << std::endl; });
}
