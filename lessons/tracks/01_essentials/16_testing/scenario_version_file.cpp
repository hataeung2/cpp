/**
 * @file scenario_version_file.cpp
 * @brief 레슨 testing — 버전 파일 파싱 및 에러 로깅에 대한 단계별 시나리오 테스트
 * @brief Lesson testing — step-by-step scenario test for version file parsing and error logging
 *
 * Scenario 도우미를 사용하여 파일 작성, 로거 열기, 에러 로깅, 로그 파일 검증의 4단계를 수행한다
 * Uses the Scenario helper to execute four steps: write file, open logger, log error, and verify log file
 */
#include "scenario.hpp"

#include <gtest/gtest.h>

#include <filesystem>
#include <fstream>
#include <memory>
#include <string>

#include "atugcc/core/error.hpp"
#include "atugcc/core/logger.hpp"
#include "version.hpp"

namespace {

namespace core = atugcc::core;

} // namespace

// 버전 파일 파싱 오류 발생 시 Logger를 통해 파일에 기록되는지 검증하는 시나리오 테스트
// Scenario test verifying that a version file parse error is recorded to a log file via Logger
TEST(VersionFileFlow, BadVersionIsLogged) {
    using testing_lesson::parseVersion;

    atugcc::test::Scenario s;

    // [학습] 각 단계는 람다이므로 후속 단계에서 접근해야 하는 상태는 람다 외부 변수로 선언해야 한다
    // [Learn] A step is a lambda, so anything a later step needs must live outside it
    std::unique_ptr<core::Logger> logger;

    s.step("write a version file with a bad line", [&] {
        const auto versionPath = s.workDir() / "version.txt";
        std::ofstream out(versionPath);
        ASSERT_TRUE(out.is_open()) << "failed to open " << versionPath.string();
        out << "1.2\n";
        out.close();
        ASSERT_TRUE(out) << "failed to write to " << versionPath.string();
    });

    s.step("open a logger that writes a file", [&] {
        core::Logger::Config cfg;
        cfg.filePath = s.workDir() / "app.log";
        cfg.enableCrashDump = false;
        cfg.dumpDir = s.workDir() / "dump";
        logger = std::make_unique<core::Logger>(cfg);
        ASSERT_NE(logger, nullptr);
        // 프로세스 전역 설정(configureLogBuffers, ATUGCC_TRACE_OUT, crash dump 대상)은 건드리지 않는다. 이 레슨의 테스트는 모두 한 프로세스를 같이 쓰기 때문이다(tests/는 시나리오마다 프로세스를 따로 준다, 스펙 Assumption 6)
        // The process-wide settings (configureLogBuffers, ATUGCC_TRACE_OUT, crash dump target) are left alone, because all tests of this lesson share one process (tests/ gives every scenario its own process, spec Assumption 6)
        // 첫 Logger는 프로세스에 하나인 로그 소비자 스레드를 시작하지만, 그것은 설정이 아니라 모든 Logger가 같이 쓰는 것이다
        // The first Logger starts the process's one log consumer thread, but that is shared by every Logger, not a setting
    });

    s.step("parse the file: the error is logged", [&] {
        ASSERT_NE(logger, nullptr);
        const auto versionPath = s.workDir() / "version.txt";
        std::ifstream in(versionPath);
        ASSERT_TRUE(in.is_open()) << "failed to open " << versionPath.string();
        std::string line;
        ASSERT_TRUE(std::getline(in, line)) << "failed to read line from " << versionPath.string();
        const auto result = parseVersion(line);
        // [학습] 여기서 ASSERT 실패가 발생하면 단계 도우미가 [skip 4]를 출력하고 4단계를 실행하지 않는다
        // [Learn] An ASSERT failure here makes the helper print [skip 4] and not run step 4
        ASSERT_FALSE(result) << "accepted: " << line;
        EXPECT_EQ(result.error(), core::CoreError::InvalidArgument);
        logger->log(core::Level::Error, "version.txt: {}", core::to_string(result.error()));
    });

    s.step("the log file has the error line", [&] {
        ASSERT_NE(logger, nullptr);
        // [학습] flush()는 호출 전에 남긴 모든 줄이 로그 파일에 쓰일 때까지(OS에 넘어갈 때까지) 기다린다. 디스크 동기화(fsync)는 하지 않는다
        // [Learn] flush() waits until every earlier line is written to the log file (handed to the OS); it does not sync to disk (no fsync)
        logger->flush();

        const auto logFile = s.workDir() / "app.log";
        std::ifstream in(logFile);
        ASSERT_TRUE(in.is_open()) << "failed to open " << logFile.string();

        bool found = false;
        std::string line;
        while (std::getline(in, line)) {
            if (line.find("version.txt: InvalidArgument") != std::string::npos) {
                found = true;
                break;
            }
        }
        EXPECT_TRUE(found) << "app.log has no error line";

        // 테스트 종료 후에도 파일들은 workDir()에 보존되므로(경로는 콘솔에 출력되지 않음, <build>/lessons/scenario_work/VersionFileFlow.BadVersionIsLogged/), 실패 후 파일을 직접 열어볼 수 있다
        // The files stay in workDir() after the run (the path is printed nowhere, it is <build>/lessons/scenario_work/VersionFileFlow.BadVersionIsLogged/), so after a failure they can be opened
    });
}
