/**
 * @file main.cpp
 * @brief 레슨 testing — GoogleTest 진입점 및 테스트 실행기
 * @brief Lesson testing — GoogleTest entry point and test runner
 *
 * GoogleTest 프레임워크를 초기화하고 모든 등록된 단위 테스트 및 시나리오를 실행한다
 * Initializes the GoogleTest framework and runs all registered unit tests and scenarios
 */
#include <gtest/gtest.h>

int main(int argc, char** argv) {
    // gtest_main 라이브러리가 하는 일은 이 두 줄과 "Running main() from ..." 한 줄 출력이다
    // gtest_main does these two lines plus one printed line "Running main() from ..."
    // GTEST_* 환경 변수(GTEST_FILTER 등)는 main 전에 옵션의 기본값이 되고, InitGoogleTest는 명령줄의 --gtest_* 옵션을 읽어 그 값을 덮어쓰고 argv에서 지운다
    // The GTEST_* environment variables (GTEST_FILTER ...) become the option defaults before main; InitGoogleTest reads the --gtest_* command-line options, which win, and removes them from argv
    // TEST와 TEST_F는 매크로가 만든 전역 객체가 main 전에 등록하고, TEST_P의 표 행들은 InitGoogleTest 안에서 만들어진다. 그래서 main은 테스트를 나열하지 않는다
    // TEST and TEST_F are registered before main by global objects the macros create, and the TEST_P table rows are made inside InitGoogleTest, so main does not list any test
    ::testing::InitGoogleTest(&argc, argv);

    // RUN_ALL_TESTS()는 모든 테스트가 통과했을 때만 0을 반환하며 하나라도 실패하면 0이 아닌 값을 반환한다
    // RUN_ALL_TESTS() returns 0 only when every test passed
    // 이 반환값은 CTest 스모크 테스트(lesson.testing)와 웹 플레이그라운드가 읽는 프로세스 종료 코드가 된다
    // That return value is the exit code the smoke test lesson.testing (CTest) and the web playground read
    // RUN_ALL_TESTS()는 프로그램 내에서 반드시 한 번만 호출되어야 하며 그 결과가 곧바로 반환되어야 한다
    // It must be called once and its result returned
    return RUN_ALL_TESTS();
}
