---
id: 070-15
title: essentials 테스트 레슨(단위·시나리오 테스트 작성과 테스트 리포트 읽기)과 레슨 빌드의 GoogleTest
depends_on: [040-02]
unblocks: []
approved: 2026-11-05
---

# Spec 070-15: essentials 테스트 레슨(단위·시나리오 테스트 작성과 테스트 리포트 읽기)과 레슨 빌드의 GoogleTest

## 0. Assumptions (please review)
| # | Decision | Rejected alternative | Why |
|---|---|---|---|
| 1 | **범위는 넷이다**: (a) 레슨 빌드에 GoogleTest를 공급한다(공용 CMake 파일 + 매니페스트 키 `gtest = true`), (b) 레슨이 040-02의 단계 도우미 `tests/scenario/scenario.hpp`를 쓰게 한다(`uses`의 새 접두사 `test:`), (c) 새 레슨 `testing`, (d) 웹 플레이그라운드가 실행 출력의 GoogleTest 실패 줄을 편집기 표시로 바꾼다. **테스트 리포트(`report.md`)는 웹에 보이지 않는다**(Assumption 10) | (a)·(b)를 따로 작업으로 | BACKLOG 줄이 "GoogleTest 공급 방법과 플레이그라운드의 리포트"를 이 스펙에서 정하라고 했다. 공급 방법을 처음 쓰는 곳이 이 레슨이라 같이 검증해야 한다 |
| 2 | **트랙 안의 자리는 `16_testing`**(essentials 끝), 레슨 id·태그 `testing`. 기존 폴더는 옮기지 않는다 | 문법 묶음 안이나 `11_thread_and_log` 앞에 | 새 레슨은 끝 번호 다음에 붙인다(070-14 Assumption 2). 레슨이 `Expected`(04), `Logger`(11), `std::filesystem`(10)을 쓰므로 앞 레슨들 뒤가 자연스럽다. **순서를 바꾸는 것은 사용자 결정**이라 다른 자리를 원하면 알려 달라 |
| 3 | **GoogleTest 공급**: `tests/CMakeLists.txt`의 `FetchContent_Declare(googletest …v1.14.0…)`·`gtest_force_shared_crt`·`FetchContent_MakeAvailable`을 새 파일 `cmake/atugcc_googletest.cmake`(`include_guard(GLOBAL)`)로 옮기고, `tests/`와 `lessons/`가 그것을 `include()`한다. `lessons/`는 `gtest = true`인 매니페스트가 하나라도 있을 때만 include한다 | (a) 플레이그라운드 preset에서 `ATUGCC_BUILD_TESTS=ON`; (b) 시스템·vcpkg의 `GTest` 패키지(`find_package`); (c) googletest 소스를 저장소에 복사 | (a) 웹의 Run이 레슨 하나만 빌드하더라도 configure가 모든 테스트·probe 타깃과 `PlaygroundServer`를 등록하고, "모든 레슨 빌드"가 테스트 전부를 빌드한다. (b) 새 호스트 준비물(`libgtest-dev`/vcpkg 포트)이 생기고 `tests/`의 v1.14.0과 버전이 갈린다. (c) 수 MB를 커밋한다. 대가: **플레이그라운드 preset의 첫 configure(또는 `--fresh`로 `_deps`가 없을 때)는 네트워크가 필요하다**. 테스트 preset은 지금도 그렇다(§4) |
| 4 | **매니페스트 키 `gtest = true`**(최상위, 한 줄, bool, 없으면 false). CMake는 `(^|\n)gtest[ \t]*=[ \t]*true`로 읽고, 켜진 레슨에 `gtest`를 링크하고 include 경로 `tests/scenario`와 `ATUGCC_SCENARIO_WORK_ROOT="<빌드>/lessons/scenario_work"`를 준다. `lessons.py check`는 다른 키처럼 TOML 값과 CMake 정규식 결과가 다르면 ERROR | (a) 소스의 `#include <gtest/gtest.h>`로 자동 판단; (b) `[run]` 아래에 | (a) CMake가 소스를 읽어야 하고, 무엇이 링크되는지 매니페스트에 보이지 않는다. 대신 `lessons.py`가 include와 키가 어긋나면 알린다(Assumption 11). (b) `[run]`은 실행 방식(프로필, 시간)이고 이것은 빌드 구성이다 |
| 5 | **레슨 실행 파일은 GoogleTest 프로그램이고 `main`을 직접 쓴다**(`testing::InitGoogleTest(&argc, argv); return RUN_ALL_TESTS();`). `gtest_main`은 링크하지 않는다 | `gtest_main` 링크(진입점 `main.cpp`에 테스트만) | `gtest_main`이 무엇을 하는지(명령줄 해석, 종료 코드)가 레슨의 일부다. 종료 코드는 smoke test `lesson.testing`과 웹이 읽는 결과이고, 모든 테스트가 통과해야 0이다 |
| 6 | **레슨 안에서는 단위 테스트와 시나리오가 한 프로세스에서 돈다**(`tests/`는 시나리오마다 프로세스 하나, 040-02 Assumption 3). 레슨의 시나리오는 프로세스 전역 상태(`configureLogBuffers`, `ATUGCC_TRACE_OUT`, crash dump 대상)를 바꾸지 않고 인스턴스 상태만 쓴다(`Logger::Config::filePath`, `enableCrashDump = false`). README가 `tests/`가 왜 나누는지 설명한다 | 레슨에도 `gtest_discover_tests`로 시나리오마다 CTest 테스트 | 웹은 실행 파일 하나를 한 번 실행하고, 레슨 = 실행 파일 하나 = smoke test 하나(070-01)를 지킨다. 나누는 이유는 README의 표와 연습 2의 `--gtest_filter`로 보인다 |
| 7 | **단계 도우미는 `tests/scenario/scenario.hpp`를 그대로 쓴다**. 레슨 소스는 `tests/README.md` §3과 같이 `#include "scenario.hpp"`라고 쓰고, `uses`에 `test:scenario/scenario.hpp`(`tests/` 아래 경로, `lib:`가 `include/`를 가리키는 방식)를 둔다. 웹의 "관련 파일"에 읽기 전용으로 열린다 | (a) 도우미를 유닛으로 복사; (b) `include/atugcc/`로 옮겨 라이브러리 API로 | (a) 사본 둘이 갈라진다. (b) 040-02가 "테스트 코드, 라이브러리 API 아님"으로 정했다. 레슨이 프로젝트의 실제 도우미를 쓰면 레슨에서 익힌 것이 그대로 `tests/scenario/`에 쓰인다 |
| 8 | **레슨 내용**: 시험받는 코드는 레슨 안의 `version.hpp`(`parseVersion(std::string_view) -> atugcc::core::Expected<Version>`, `Version`의 `<=>`). 단위 테스트 `test_version.cpp`(`TEST`, `EXPECT_*`/`ASSERT_*`, 표로 돌리는 `TEST_P`, `PrintTo`), 시나리오 `scenario_version_file.cpp`(버전 파일 → 파싱 → `Logger` → 로그 파일, 4단계). 파일 넷(§2.2) | 라이브러리 클래스(`RingBuffer`, `Logger`)를 시험 | 라이브러리는 이미 `tests/`에 테스트가 있다. 배우는 사람은 **자기가 쓰고 고치는 코드**를 시험해야 테스트가 왜 깨지는지 본다. 파서는 경계값이 많아 표 테스트와 실패 메시지를 보이기 좋다. 시나리오는 공개 헤더(`logger.hpp`, `error.hpp`)만 쓴다(040-02 규칙) |
| 9 | 레슨의 테스트는 **학습 자료이지 프로젝트의 테스트가 아니다**. `tests/`의 종류 label(`unit`/`scenario`/`probe`)을 받지 않고 `lesson`만 받는다. 패턴·엔진 작업의 "시나리오 하나 이상" 규칙(test.md §2)을 채우지 않는다 | 레슨의 시나리오를 `scenario` label로도 | label이 종류를 뜻하는 040-02 규칙이 흐려진다. `-L scenario`는 라이브러리 흐름만 골라야 한다 |
| 10 | **웹은 테스트 리포트를 보여 주지 않는다**. 대신 실행이 끝나면 출력의 GoogleTest 실패 줄(`<file>:<line>: Failure`, Linux 형식)을 진단으로 바꿔 편집기의 그 줄에 표시한다(심각도 error, 메시지는 다음 줄들, 빌드 진단과 같은 표시). 리포트 읽기는 로컬에서 `build.py --report`로 연습한다(연습 3) | (a) 웹에 "Tests" 탭(gtest JSON의 케이스별 표); (b) 웹에서 `test_report.py`를 돌려 `report.md` 표시 | 리포트는 **CTest 실행**(`build.py` → `ctest --output-junit`)의 산출물이고 `test_report.py`는 JUnit 파일이 있어야 한다. 플레이그라운드는 CTest 없이(`ATUGCC_BUILD_TESTS=OFF`) 레슨 실행 파일 하나를 바로 돌린다. 프로그램 하나의 결과는 GoogleTest 콘솔 출력이 이미 다 보여 주고, 빠진 것은 "실패가 소스의 어디인가"뿐이라 그것만 더한다. (a)는 **KI-042**(새)로 남긴다 |
| 11 | **`lessons.py check` 규칙 추가**(§2.4): ERROR — `gtest`가 bool이 아님; `gtest`가 없거나 false인데 레슨 소스나 전이 유닛 파일이 `<gtest/…>`·`<gmock/…>`·`"scenario.hpp"`를 include; `test:<path>`에 `tests/<path>` 파일이 없음; `uses` 접두사 오류 메시지에 `test:`. WARN — `gtest = true`인데 어떤 소스도 `<gtest/gtest.h>`를 include하지 않음; `#include "scenario.hpp"`인데 전이 `uses`에 `test:scenario/scenario.hpp` 없음 | 검사 없이 빌드 오류에 맡기기 | 키 없이 gtest를 include하면 빌드 오류가 "헤더 없음"으로만 나서 원인(매니페스트)이 보이지 않는다. 나머지는 기존 `#include`/`uses` 경고와 같은 성격이다 |
| 12 | **리포트에 레슨 결과가 들어간다**: `build.py --report`는 ctest 단계에 `GTEST_OUTPUT`을 주므로 `lesson.testing`이 `gtest/lesson_testing.json`을 쓰고, `report.md`의 "GoogleTest cases"에 행이, 실패하면 "Failures"에 케이스 이름과 메시지가 나온다. `test_report.py`는 바꾸지 않는 것이 목표이고, DEV 첫 단계에서 확인해 안 맞으면 이 작업에서 고친다 | — | 040-02의 gtest 파일 배정은 CTest 명령의 실행 파일 이름(`lesson_testing`)으로 한다. 연습 3이 이것에 기댄다 |
| 13 | **연습**(§2.2): (1) `EXPECT_EQ`의 기대값을 틀리게 바꿔 메시지 읽기 → `ASSERT_EQ`로 바꿔 그 뒤 줄이 안 도는 것 보기 → `PrintTo`를 지워 `Version`이 바이트로 찍히는 것 보기, (2) 시나리오 3단계를 깨서 `[skip 4]`와 `step 3: …` 추적 줄을 보고, 남은 `workDir` 파일 열기, 그리고 `--gtest_filter`로 시나리오 하나만 돌리기(로컬), (3) 로컬에서 깨진 상태로 `py -3 .agent/scripts/build.py --preset <p> --label lesson --report`를 돌려 `report.md`의 Failures·GoogleTest cases 읽기, 되돌리고 새 표 행을 더하기 | `build.py`에 테스트 이름 정규식 옵션(`-R`)을 더해 레슨 하나만 | `--label lesson`은 레슨 전부(지금 약 20초)를 돌리지만 새 옵션 없이 된다. 테스트 하나만은 `tests/README.md` §4.3의 `ctest -R` 줄로 된다(README가 알려 줌) |
| 14 | **웹 실행 환경**: 실행 전에 환경에서 `GTEST_`로 시작하는 변수(`GTEST_FILTER`, `GTEST_OUTPUT`, …)를 지운다(`ATUGCC_SPAN_METER`를 지우는 것과 같은 이유). 색은 켜지 않는다(gtest 기본: 파이프면 끔) | `GTEST_COLOR=yes` | 서버를 띄운 셸의 설정이 레슨 결과를 바꾸면 안 된다. 색은 실패 줄 표시가 대신한다 |
| 15 | gmock은 링크하지 않는다(`gtest`만). 목 객체는 이 레슨이 다루지 않는다 | `gtest = true`가 `gmock`도 링크 | 이 레슨에 쓸 곳이 없다. 필요한 첫 레슨이 매니페스트 규칙을 넓힌다(§6) |
| 16 | 새 레슨은 070-03의 규칙을 따른다: `profile = "quick"`, 출력 영어, 주석은 한국어 줄 + 영어 줄, `README.md`와 `README.en.md`, 두 preset에서 경고 없이 빌드, 플랫폼 전용 API 없음 | — | 070-03 Assumption 9·10·12, 070-14 Assumption 15 |
| 17 | **진행 순서**: 070-15가 끝나면 A(기반 다지기)가 끝나고 B는 060-01 스펙 재검토부터다(`agent_todo.md` 진행 순서). 이 스펙은 순서를 바꾸지 않는다 | — | 순서는 사용자 결정 |
| 18 | **README는 따라 하는 튜토리얼이다**(사용자 요청 2026-11-05: "레슨을 읽고 gtest, CTest를 십분 활용할 수 있도록"). 부분 A GoogleTest(첫 테스트 → `EXPECT`/`ASSERT` → 실패 메시지와 `PrintTo` → fixture `TEST_F` → 표 테스트 `TEST_P` → 단계 시나리오 → `main`과 실행 옵션), 부분 B CTest(무엇을 하는가 → 이 프로젝트가 등록하는 방식(`add_test`, label, `gtest_discover_tests`) → 고르기 `-N`/`-R`/`-E`/`-L`/`-LE` → 실패 보기 `--output-on-failure`/`--rerun-failed` → 반복·병렬·시간 `--repeat`/`-j`/`--timeout`), 부분 C 테스트 리포트. 각 절은 "무엇 → 코드 → 해 보기 → 보이는 것" 순서이고, 해 보기마다 웹에서 되는지 로컬에서만 되는지 표시한다. 끝에 빠른 참조표(매크로, gtest 옵션, ctest 옵션). 레슨 코드에 fixture 하나를 더한다(§2.2). README의 모든 명령은 DEV에서 실제로 돌려 적힌 대로 나오는지 확인한다(AC-11) | 레슨 README는 짧게 두고 튜토리얼을 `docs/learning/`에 따로 | 레슨을 읽으면서 바로 그 코드로 해 보는 것이 목적이라 레슨 폴더에 있어야 웹의 README 탭에서 소스와 함께 보인다. 길어지는 대신 절마다 독립적으로 읽히게 쓴다 |

## 1. Objective
040-02가 단위·시나리오·probe 테스트의 종류와 단계 도우미, 테스트 리포트(`build.py --report`)를 만들었지만, 그것을 직접 써 보는 레슨이 없고 레슨 빌드에는 GoogleTest가 없다(플레이그라운드 preset은 tests를 끈다). 이 작업은 레슨이 매니페스트 한 줄로 GoogleTest와 프로젝트의 단계 도우미를 쓰게 하고, 그 첫 사용자로 essentials 마지막 레슨 `testing`을 만든다: 자기 코드에 단위 테스트를 쓰고(`EXPECT`와 `ASSERT`의 차이, 표 테스트, 값 출력), 단계로 나눈 시나리오를 쓰고, 깨뜨린 테스트를 실패 메시지·편집기 표시·테스트 리포트로 읽는다.

## 2. Requirement Details

### 2.1 트랙 안의 자리
| 폴더 | 레슨 id | 후보 | 상태 |
|---|---|---|---|
| `01_lambda_capture` – `15_modules` | (기존 15개) | | 그대로 |
| `16_testing` | `testing` | E16 테스트 작성과 리포트 | **새로** |

[`lesson_candidates.md`](/docs/lesson_candidates.md) essentials 표에 E16 행을 더한다(비교: `assert`·손으로 쓴 `main` 검사 → GoogleTest 단위 테스트와 단계 시나리오, 출처 040-02, 기존 자료 `tests/scenario/`, `tests/README.md`, `.agent/scripts/test_report.py`).

### 2.2 새 레슨 `testing`
`lessons/tracks/01_essentials/16_testing/lesson.toml`:
```toml
id         = "testing"
title      = "테스트: GoogleTest 단위 테스트, 단계 시나리오, 테스트 리포트 읽기"
title_en   = "Testing: GoogleTest unit tests, step scenarios, and reading a test report"
summary    = "버전 파서에 단위 테스트와 시나리오를 쓰고, 일부러 깨뜨린 테스트를 실패 메시지와 테스트 리포트로 읽는다"
summary_en = "Write unit tests and a scenario for a version parser, then read deliberately broken tests through failure messages and a test report"
sources    = ["main.cpp", "version.hpp", "test_version.cpp", "scenario_version_file.cpp"]
uses       = ["lib:atugcc/core/error.hpp", "lib:atugcc/core/logger.hpp", "test:scenario/scenario.hpp"]
tags       = ["testing", "error"]
gtest      = true
```

파일(주석 규칙은 Assumption 16):
- `version.hpp`: 시험받는 코드. `namespace testing_lesson { struct Version { unsigned major, minor, patch; auto operator<=>(const Version&) const = default; }; }`, `inline atugcc::core::Expected<Version> parseVersion(std::string_view text)`(`"<n>.<n>.<n>"`만, 각 부분은 `std::from_chars`로 `unsigned`, 빈 부분·숫자 아닌 글자·부분이 셋이 아님·범위 넘침 → `std::unexpected(CoreError::InvalidArgument)`), `inline std::string to_string(const Version&)`, `inline void PrintTo(const Version&, std::ostream*)`(gtest가 실패 메시지에 `1.2.3`으로 찍게). 함수는 두 TU가 include하므로 `inline`.
- `test_version.cpp`: 단위 테스트.
  - `TEST(ParseVersion, ReadsThreeNumbers)`: `ASSERT_TRUE(result)`(실패하면 그 뒤의 `*result`가 UB가 되므로 `ASSERT`) 후 `EXPECT_EQ(result->major, 1u)` 등. 주석: `1u`인 이유(`unsigned`와 `int` 비교는 `-Wsign-compare` 경고, 프로젝트는 경고를 오류로).
  - `TEST_P(ParseVersionRejects, BadText)` + `INSTANTIATE_TEST_SUITE_P(Table, ParseVersionRejects, ::testing::Values("", "1.2", "1.2.3.4", "1.x.3", "-1.2.3", "1..3", "99999999999.0.0"))`: 모두 `CoreError::InvalidArgument`. 매개변수는 `std::string_view`(문자열 리터럴이라 수명 문제 없음).
  - `TEST(VersionOrder, ComparesNumbersNotText)`: `1.9.0 < 1.10.0`(문자열 비교라면 반대), `EXPECT_EQ(*newer, (Version{1, 10, 0}))`(`PrintTo`가 메시지에 쓰임. `Expected<Version>`을 바로 비교하면 바이트로 찍히므로 `*`로 값을 꺼냄, DEV 리뷰).
  - fixture(Assumption 18): `class ReleaseListTest : public ::testing::Test`의 `SetUp()`이 문자열 목록(`"1.2.0"`, `"1.10.0"`, `"1.9.3"`)을 파싱해 `std::vector<Version>` 멤버에 넣는다(실패하면 `FAIL()`). `TEST_F(ReleaseListTest, NewestIsHighest)`, `TEST_F(ReleaseListTest, SortsAscending)`. 테스트마다 새 fixture 객체라는 것을 주석에. 시험받는 함수 `inline std::optional<Version> newestVersion(std::span<const Version>)`(빈 목록 `std::nullopt`)을 `version.hpp`에 더하고, 빈 목록 경우는 `TEST(NewestVersion, EmptyListHasNone)`.
- `scenario_version_file.cpp`: `TEST(VersionFileFlow, BadVersionIsLogged)`, `atugcc::test::Scenario s;`, 단계 사이 상태(`std::unique_ptr<Logger>`, 결과)는 단계 밖 변수.
  1. `"write a version file with a bad line"`: `s.workDir() / "version.txt"`에 `1.2`.
  2. `"open a logger that writes a file"`: `cfg.filePath = s.workDir() / "app.log"`, `enableCrashDump = false`, `dumpDir = s.workDir() / "dump"`.
  3. `"parse the file: the error is logged"`: 읽어서 `parseVersion`, `ASSERT_FALSE(result)`, `EXPECT_EQ(result.error(), CoreError::InvalidArgument)`, `logger->log(Level::Error, "version.txt: {}", to_string(result.error()))`.
  4. `"the log file has the error line"`: `logger->flush()`, 파일에서 `version.txt: InvalidArgument`를 찾음.
- `main.cpp`: `#include <gtest/gtest.h>`, `int main(int argc, char** argv)`. 주석: `gtest_main`이 하는 일이 이 두 줄이라는 것, `--gtest_filter`·`--gtest_list_tests`를 받는다는 것, 종료 코드(모두 통과 0, 하나라도 실패 1)를 smoke test와 웹이 읽는다는 것, 테스트는 다른 파일의 전역 객체가 `main` 전에 등록한다는 것.

출력(영어, GoogleTest 기본 형식, 두 OS에서 테스트 목록과 통과 수가 같음): `[==========] Running N tests from M test suites.` … 시나리오의 `[step 1]` – `[step 4]` … `[  PASSED  ] N tests.` 시간(`(0 ms)`)은 실행마다 다르다.

README(두 판, 튜토리얼, Assumption 18). 절마다 "무엇 → 이 레슨의 코드 → 해 보기(🌐 웹 / 💻 로컬) → 보이는 것(실제 출력 발췌)":
- 머리: 이 레슨으로 할 수 있게 되는 것, 파일 넷의 역할, 웹과 로컬에서 실행하는 법, 비교 표(`assert`/손으로 쓴 검사 vs GoogleTest: 이름 있는 테스트, 실패해도 나머지가 돔, 값이 찍힘, 골라 돌리기, 기계가 읽는 출력).
- **A. GoogleTest**
  1. 첫 테스트: `TEST(Suite, Name)`, 이름 규칙(밑줄 없이), 등록은 `main` 전에 전역 객체가, `main.cpp`의 두 줄과 `gtest_main`.
  2. `EXPECT`와 `ASSERT`: 언제 무엇(뒤 줄이 앞 결과에 기대면 `ASSERT`), 자주 쓰는 비교 매크로 표(`EQ/NE/LT/LE/GT/GE`, `TRUE/FALSE`, `STREQ`, `DOUBLE_EQ`/`NEAR`, `THROW`/`NO_THROW`), `<< "추가 메시지"`, `1u`와 경고.
  3. 실패 메시지 읽기: `Expected equality of these values:` 형식, `PrintTo`/`operator<<`로 값 보이기, 왜 매크로인가(위치는 `std::source_location`으로 되지만 `#expr`과 return은 안 됨, 05 레슨).
  4. fixture `TEST_F`: `SetUp`/`TearDown`, 테스트마다 새 객체, 언제 fixture를 쓰는가.
  5. 표 테스트 `TEST_P`: `GetParam()`, `INSTANTIATE_TEST_SUITE_P`, 생기는 이름(`Table/ParseVersionRejects.BadText/3`), 한 경우 더하기.
  6. 단계 시나리오: [`tests/README.md`](/tests/README.md) §3의 도우미, `[step n]`/`[skip n]`, 상태는 단계 밖, `workDir()` 위치(`out/build/<p>/lessons/scenario_work/VersionFileFlow.BadVersionIsLogged/`), 스레드 규칙(링크), 이 레슨은 한 프로세스이지만 `tests/`는 시나리오마다 프로세스(이유 표).
  7. 실행 옵션: `--gtest_list_tests`, `--gtest_filter`(패턴, `-` 빼기), `--gtest_repeat`, `--gtest_shuffle`/`--gtest_random_seed`, `--gtest_break_on_failure`, `--gtest_brief`, `--gtest_output=json:`, 같은 것을 환경 변수(`GTEST_FILTER`)로. 웹은 실행 인자를 받지 않으므로 `main.cpp`에서 `GTEST_FLAG_SET(filter, "…")`를 `InitGoogleTest` 뒤에 써서 해 본다.
- **B. CTest**
  1. CTest가 하는 일: GoogleTest는 한 프로그램 안의 케이스, CTest는 프로그램(명령)을 테스트로 등록하고 돌림. 종료 코드가 결과. `ctest --preset <p>`(테스트 preset, `outputOnFailure`).
  2. 이 프로젝트의 등록: `add_test` + `LABELS`(레슨 `lesson.<id>`, `lessons/CMakeLists.txt`), `AllTests`(단위 전체가 한 테스트), `gtest_discover_tests`(시나리오마다 한 테스트, `tests/CMakeLists.txt`), probe. 발췌는 저장소 파일 그대로.
  3. 고르기: `-N`(목록만), `-R`/`-E`(이름 정규식), `-L`/`-LE`(label), `build.py --label`과의 관계.
  4. 실패 보기: `--output-on-failure`, `-V`, `--rerun-failed`, `Testing/Temporary/LastTestsFailed.log`.
  5. 반복·병렬·시간: `--repeat until-fail:N`(가끔 깨지는 테스트), `--repeat until-pass:N`, `-j N`, `--timeout`, 레슨의 `TIMEOUT`(quick 10초).
- **C. 테스트 리포트**: `build.py --report`가 만드는 것, `report.md`의 Failures와 GoogleTest cases에서 이 레슨 찾기, 리포트 읽는 법은 [`tests/README.md`](/tests/README.md) §4로 링크. 웹에서는 리포트가 없다는 것과 이유(한 줄, Assumption 10). 실패를 읽는 세 곳: 콘솔 출력(MSVC `file(line): error:`, Clang/GCC `file:line: Failure`), 웹의 편집기 표시, 로컬 리포트.
- **연습** 3개(Assumption 13). 연습 2의 `--gtest_filter`와 연습 3은 로컬 명령이라고 적는다.
- **빠른 참조**: 매크로 표, gtest 옵션 표, ctest 옵션 표(이 프로젝트 명령으로).

### 2.3 레슨 빌드의 GoogleTest
| 곳 | 바꾸는 것 |
|---|---|
| `cmake/atugcc_googletest.cmake` (새) | `include_guard(GLOBAL)`, `include(FetchContent)`, `tests/CMakeLists.txt`에 있던 `FetchContent_Declare(googletest URL …/v1.14.0.zip)`, `gtest_force_shared_crt`, `FetchContent_MakeAvailable(googletest)`를 그대로. 머리 주석(spec 070-15, 누가 include하는가) |
| [`tests/CMakeLists.txt`](/tests/CMakeLists.txt) | 위 세 줄 대신 `include(${atugcc_SOURCE_DIR}/cmake/atugcc_googletest.cmake)` (`tests/`는 `project(atugcc_tests)`라 `PROJECT_SOURCE_DIR`은 쓰지 않음) |
| [`lessons/CMakeLists.txt`](/lessons/CMakeLists.txt) | 매니페스트에서 `gtest`를 읽고, 켜진 레슨이 있으면 같은 파일을 include, 그 레슨에 `target_link_libraries(… PRIVATE gtest)`, `target_include_directories(… PRIVATE "${atugcc_SOURCE_DIR}/tests/scenario")`, `target_compile_definitions(… PRIVATE ATUGCC_SCENARIO_WORK_ROOT="${CMAKE_CURRENT_BINARY_DIR}/scenario_work")`, sanitizer 빌드면 `ATUGCC_SANITIZED_BUILD`(tests와 같음). 머리 주석에 `gtest` 키 |

`tests/`와 `lessons/` 둘 다 켜진 preset에서는 `tests/`가 먼저 include하고(루트 `CMakeLists.txt` 순서) `lessons/`의 include는 guard로 건너뛴다. googletest 타깃은 전역이라 둘 다 같은 `gtest`를 쓴다.

### 2.4 `tools/lessons.py`와 `uses`의 `test:`
| 곳 | 바꾸는 것 |
|---|---|
| 매니페스트 스키마 | 레슨에 선택 키 `gtest`(bool). 유닛 `unit.toml`은 받지 않음(알 수 없는 키 처리는 기존 규칙대로) |
| CMake 정규식 대조 | `gtest`를 `(^|\n)gtest[ \t]*=[ \t]*true`로 읽은 결과와 TOML 값이 다르면 ERROR(들여 쓴 `  gtest = true`, `[run]` 같은 표 아래의 `gtest = true`. `gtest = "true"`는 두 쪽 모두 false라 차이가 아니고 bool 검사가 잡는다, DEV 리뷰) |
| `uses` | 새 접두사 `test:<path>` → `tests/<path>`. 없는 파일 ERROR, 접두사 오류 메시지에 `test:` |
| `check` | Assumption 11의 ERROR 2개·WARN 2개. include 찾기는 기존 `#include` 검사와 같은 줄 정규식(`<gtest/`, `<gmock/`, `"scenario.hpp"`) |
| `ref_files` / `index` | `test:<path>` → `tests/<path>`. 인덱스의 레슨 항목에 `gtest`는 넣지 않는다(웹이 쓰지 않음) |
| [`tools/test_lessons.py`](/tools/test_lessons.py) | 위 규칙마다 한 경우, 인덱스의 `test:` 경로 |

### 2.5 웹
| 곳 | 바꾸는 것 |
|---|---|
| [`web/server/runner.py`](/web/server/runner.py) | (a) 실행 환경에서 `GTEST_`로 시작하는 변수를 지움. (b) `TEST_FAILURE_RE = ^(?P<file>[^:\n]+):(?P<line>\d+): Failure$`(re.M)와 `parse_test_failures(text, root, cwd)`: 그 줄 다음의 줄들 중 빈 줄, `[`로 시작하는 줄, `Google Test trace:` 전까지(최대 6줄, 500자)를 메시지로, `col` 1, `severity` `"error"`, 경로는 `repo_relative`(실행 cwd 기준). 실행 중 받은 stdout을 출력 상한(`output_bytes`) 안에서 모아 두었다가 `done`의 `run.diagnostics`로 보냄(최대 `MAX_DIAGNOSTICS`). 빌드 진단 형식과 같다 |
| [`web/frontend/src/main.ts`](/web/frontend/src/main.ts) | `done`에서 `editor.setDiagnostics([...build.diagnostics, ...(run?.diagnostics ?? [])])`. `api.ts`의 run 타입에 `diagnostics?` |
| [`web/server/test_server.py`](/web/server/test_server.py) | `parse_test_failures`: 실패 둘(시나리오 추적 줄이 있는 것 포함), 저장소 밖 경로, 상한. 실행 환경에서 `GTEST_FILTER`가 지워짐(fixture가 환경을 출력하는 기존 방식이 있으면 그것으로, 없으면 `_execute`가 만드는 env를 함수로 빼서 시험) |
| 프런트엔드 단위 테스트 | 진단 합치기가 함수로 빠지면 한 경우 |

GoogleTest가 MSVC에서 쓰는 `file(line): error:` 형식은 웹(Linux, Clang)에 나오지 않으므로 받지 않는다.

### 2.6 태그 어휘 (`lessons/tags.toml`에 더함)
| 키 | ko | en | aliases |
|---|---|---|---|
| `testing` | 테스트 | Testing | `GoogleTest`, `gtest`, `TEST`, `TEST_F`, `TEST_P`, `fixture`, `픽스처`, `EXPECT_EQ`, `ASSERT_EQ`, `unit test`, `단위 테스트`, `scenario test`, `시나리오 테스트`, `test report`, `테스트 리포트`, `ctest` |

별칭 중복 경고(070-10)를 지킨다(`ctest`, `TEST`가 다른 태그에 없는지 구현 때 확인).

### 2.7 Platform Specifics
- 실패 줄 형식: GoogleTest는 MSVC에서 `file(line): error: …`, 그 밖에서 `file:line: Failure`를 쓴다. README가 둘 다 보인다. 웹은 Linux 형식만 읽는다(§2.5).
- `__FILE__`은 CMake가 넘긴 절대 경로다. 웹은 저장소 상대 경로로 바꾸고, 로컬 리포트는 `test_report.py`가 저장소 상대로 바꾼다(040-02).
- Windows: `gtest_force_shared_crt`로 레슨과 같은 `/MD(d)`. 레슨의 콘솔 UTF-8 설정(090-06)은 그대로 링크되고 gtest 출력은 ASCII다.
- 웹 플레이그라운드는 `linux-x64-playground`(Clang 20)로 빌드한다. 첫 Run은 `gtest` 라이브러리도 빌드한다(빌드 상한 120초 안이어야 함, AC-7에서 잼).

## 3. C++ Standard Evolution
| Approach | Standard | Description |
|----------|----------|-------------|
| Legacy | C++98–17 | `assert()`(NDEBUG에서 사라짐, 첫 실패에서 abort, 이름 없음) 또는 손으로 쓴 `if (…) { printf(…); return 1; }`. 테스트 프레임워크는 `__FILE__`/`__LINE__`, `#expr`, 테스트 함수에서의 `return`이 필요해 매크로로 만든다 |
| Modern | C++20 | `std::source_location`이 위치를 매크로 없이 준다(그래도 식의 글자와 `ASSERT`의 return은 매크로가 필요). 단계 도우미의 `template <std::invocable F>`(concepts), `SCOPED_TRACE(std::format(…))`, 기본 `operator<=>`로 순서 비교를 시험 |
| Latest | C++23 | `std::expected`(`atugcc::core::Expected`) 결과를 `ASSERT_TRUE(result)` 후 `*result`로. 그 밖 N/A |

Reference: 새 `docs/cpp_evolution/` 페이지는 만들지 않는다. 비교는 레슨 README에 둔다. 위치 부분은 [`/docs/cpp_evolution/source_location.md`](/docs/cpp_evolution/source_location.md)(있음)에 레슨 링크 한 줄.

## 4. Edge Cases
- [x] Thread safety / memory ordering — 레슨의 테스트는 한 스레드에서 돈다. `Logger`의 소비자 스레드는 라이브러리 내부이고 `flush()`가 기다린다(시나리오 4단계). 단계 도우미의 "다른 스레드의 `ASSERT`" 규칙은 README가 `tests/README.md`로 링크만.
- [x] Resource lifetime / RAII / dangling views — `TEST_P` 매개변수 `std::string_view`는 문자열 리터럴(정적 수명)만 가리킨다. `parseVersion`은 `string_view`를 붙잡지 않고 값 `Version`을 돌려준다. 시나리오의 `Logger`는 `unique_ptr`로 단계 밖에 두고, 단계마다 `ASSERT_NE(logger, nullptr)`.
- [x] Platform differences (MSVC vs Clang) — 실패 줄 형식(§2.7). `unsigned` 비교 경고(`1u`, §2.2). 테스트 목록과 통과 수는 두 OS가 같고, 시간·경로는 다르다(AC-2는 목록과 요약 줄만 비교).
- [x] Template instantiation / concept constraints — `EXPECT_EQ(Version, Version)`는 `operator==`(기본 `<=>`가 만듦)와 `PrintTo`를 찾는다(ADL, 같은 namespace). `PrintTo`가 없으면 바이트 덤프가 찍힌다(연습 1의 일부). `Scenario::step`은 `std::invocable` 람다만 받는다.
- [x] ODR — `version.hpp`의 함수는 `inline`(두 TU가 include). 테스트 등록 객체는 TU마다 따로이고 이름(`Suite.Name`)이 겹치면 gtest가 실행 때 알린다.
- [x] Undefined behaviour — `ASSERT_TRUE(result)` 뒤에만 `*result`. `from_chars`의 `result_out_of_range`를 오류로. `unsigned`라 `-1`은 `from_chars`가 거부한다(부호 넘침 없음).
- [x] 정적 초기화 순서 — 테스트는 각 TU의 전역 등록 객체가 `main` 전에 등록하고, `RUN_ALL_TESTS()`는 `main` 안에서 부른다. 등록 객체끼리는 서로 기대지 않는다.
- [x] 출력 순서 — gtest는 C stdio(`printf`+`fflush`), 도우미는 `std::cout << std::endl`. `sync_with_stdio(true)`(기본)라 파이프에서도 순서가 맞는다(070-14 Assumption 12와 같음).
- [x] 레슨 실패와 smoke test — 연습으로 테스트를 깨면 `lesson.testing`도 실패한다(그것이 연습 3). README가 연습 뒤 되돌리라고 적는다.
- [x] `workDir` — `ATUGCC_SCENARIO_WORK_ROOT`는 preset의 빌드 디렉터리 아래(`lessons/scenario_work`)라 `tests/`의 것과 겹치지 않고 preset끼리도 겹치지 않는다. 시나리오 시작 때 비우고 끝나도 남긴다(040-02). 웹 실행도 같은 곳(`out/build/linux-x64-playground/lessons/scenario_work/…`).
- [x] 매크로 없이 도우미를 include — `scenario.hpp`의 `#error`가 막는다. `lessons.py`가 키 없는 include를 ERROR로 먼저 잡는다(Assumption 11).
- [x] 네트워크 없는 첫 configure — `gtest = true` 레슨이 있으므로 레슨을 켠 모든 preset의 첫 configure가 googletest zip을 받는다. 이미 받은 빌드 디렉터리(`_deps`)는 다시 받지 않는다. 오프라인에서 새 플레이그라운드 빌드 디렉터리를 만들면 configure가 실패한다: `web/README.md`와 `config.md`에 적는다. 해결책(오프라인 미러, 공유 다운로드)은 지금 만들지 않는다
- [x] 웹의 빌드 시간 — 첫 Run은 `gtest-all.cc`도 컴파일한다. 120초 상한 안에 드는지 AC-7에서 잰다. 넘으면 멈추고 사용자에게 묻는다
- [x] Sanitizer — `gtest`는 계측되지 않은 채로 링크된다(`tests/`와 같음). `linux-x64-asan`/`tsan`에서 `ctest -L lesson`이 통과해야 한다(AC-9).
- [x] 서버를 띄운 셸의 `GTEST_FILTER` — 웹은 지운다(Assumption 14). 로컬 ctest는 사용자의 환경을 그대로 따른다(의도된 사용법).

## 5. Acceptance Criteria
| ID | Criterion | Verified by |
|---|---|---|
| AC-1 | 인덱스의 essentials 순서 끝에 `testing`이 온다(`…, span_timing, modules, testing`). 기존 레슨의 id와 순서는 그대로다. `testing` 항목의 `uses`에서 `test:scenario/scenario.hpp`가 `tests/scenario/scenario.hpp`로 나온다 | `py -3 tools/lessons.py index --out -` 출력, testrecord |
| AC-2 | `testing`이 `windows-x64-debug`와 `linux-x64-debug`에서 경고 없이 빌드되고 `lesson.testing`이 통과한다. 출력에 `[step 1]`–`[step 4]`와 `[  PASSED  ]` 요약이 있다. 두 OS의 `--gtest_list_tests` 출력과 `[  PASSED  ] N tests.` 줄이 같다 | 빌드 로그, `ctest -R lesson.testing`, 두 출력의 비교, testrecord |
| AC-3 | googletest는 `cmake/atugcc_googletest.cmake` 한 곳에서 선언되고(v1.14.0 그대로), `tests/`와 `lessons/`가 둘 다 켜진 preset에서 configure 오류·경고 없이 같은 `gtest` 타깃을 쓴다. `linux-x64-playground`, `linux-x64-playground-release`(tests 끔)가 configure되고 모든 레슨을 빌드한다. `gtest = true`가 아닌 레슨은 `gtest`를 링크하지 않는다 | `grep -rn "FetchContent_Declare(" tests lessons cmake`(한 곳), configure 로그, `build.ninja`에서 `lesson_modules`의 링크 줄에 `gtest` 없음, `lesson_testing`에 있음 |
| AC-4 | 연습 1·2가 README가 말하는 대로 된다: 틀린 `EXPECT_EQ` → 기대값·실제값이 찍힌 실패, 그 뒤 검사도 돎; `ASSERT_EQ`로 바꾸면 그 뒤 줄이 돌지 않음; `PrintTo`를 지우면 실패 메시지의 `Version`이 바이트 덤프; 시나리오 3단계를 깨면 `[skip 4]`와 `step 3: parse the file: the error is logged` 추적 줄, `workDir`에 `version.txt`·`app.log`가 남음; `--gtest_filter=VersionFileFlow.*`로 시나리오만 돎 | 임시로 고친 사본의 출력 발췌(두 OS 중 하나 이상, 실패 줄 형식은 두 OS), testrecord. 커밋하지 않음 |
| AC-5 | 연습 3: 테스트 하나를 깬 상태의 `build.py --preset <p> --label lesson --report`가 0이 아닌 코드로 끝나고, `report.md`의 Failures에 `lesson.testing`과 깨진 케이스 이름·메시지가, GoogleTest cases에 `lesson_testing.json` 행(실패 1)이 있다. 되돌린 상태에서는 같은 행의 실패가 0이다(Windows 1회, Linux 1회) | 두 `report.md` 발췌, testrecord |
| AC-6 | `lessons.py check`의 새 규칙(§2.4)이 각 경우에 맞는 수준을 낸다: `gtest`가 bool 아님 ERROR, 키 없이 `<gtest/gtest.h>` ERROR, 키 없이 `"scenario.hpp"` ERROR, 없는 `test:` 경로 ERROR, TOML과 CMake 정규식 차이 ERROR, 키는 있는데 gtest include 없음 WARN, `"scenario.hpp"` + `test:` 없음 WARN. 저장소 전체는 ERROR 0, WARN 0 | `py -3 tools/test_lessons.py`, `py -3 tools/lessons.py check` |
| AC-7 | 웹: 레슨 트리의 `testing`을 Run하면 GoogleTest 출력이 나오고 성공으로 끝난다(첫 Run의 빌드 시간 기록, 120초 안). `test_version.cpp`의 `EXPECT_EQ`를 깨고 Run하면 그 줄에 오류 표시와 메시지가 붙고, 시나리오 단계를 깨면 `scenario_version_file.cpp`의 그 줄에 붙는다. "관련 파일"의 `tests/scenario/scenario.hpp`가 읽기 전용으로 열린다. 검색 `gtest`, `테스트`, `EXPECT_EQ`가 `testing`을 찾는다 | 헤드리스 브라우저: 실행 출력, 스크린샷 2장(두 표시), 검색어 3개 결과; `web/server/test_server.py`의 새 경우 |
| AC-8 | 새 README의 영어판이 한국어판과 절 제목 수, 연습 수, 코드 블록 수가 같다. 새 소스의 stdout·stderr에 한글이 없고, 한글 주석 줄(문단)마다 바로 다음이 같은 뜻의 영어 주석이다 | 070-03의 비교 스크립트와 주석 검사 스크립트, `cpp-reviewer` 번역 검토 한 번 |
| AC-9 | 전체 suite가 `windows-x64-debug`, `linux-x64-debug`에서 통과한다. `linux-x64-asan`, `linux-x64-tsan`에서 `ctest -L lesson`이 통과한다. `npm --prefix web/frontend test`, `tools/test_lessons.py`, `PlaygroundServer` 통과. `-L unit`/`-L scenario`/`-L probe`의 테스트 목록은 이 작업 전과 같다(레슨 테스트가 그 label을 받지 않음) | `build.py --preset <p> --test`, `ctest -N -L …` 전후 비교, 명령 출력, testrecord |
| AC-10 | §8 문서가 결과와 맞고 `lint_docs.py`가 exit 0이다 | 명령 출력 |
| AC-11 | README(두 판)는 §2.2의 A·B·C 절과 빠른 참조를 모두 갖고, 절마다 해 보기와 웹/로컬 표시가 있다. README의 모든 명령(gtest 옵션, ctest 옵션, `build.py`)과 `GTEST_FLAG_SET` 예를 한 번씩 실제로 돌려 README가 말하는 결과가 나온다. README의 출력 발췌는 실제 출력에서 가져온다 | 명령마다 실행 기록(명령, 결과 요약)을 testrecord에, 절 목록 대조 |

## 6. Out of Scope
- 웹의 테스트 결과 탭(케이스별 표, 리포트 보기) — **KI-042**(새)
- 레슨에서 gmock(목 객체) — 계획 없음. 필요한 첫 레슨 작업이 `gtest` 키의 링크 대상을 넓힌다
- 레슨 시나리오를 프로세스마다 나눠 CTest에 등록(`gtest_discover_tests`) — 하지 않는다(Assumption 6)
- 레슨의 테스트를 `unit`/`scenario` label로 — 하지 않는다(Assumption 9)
- 유닛(`lessons/units/`)이 gtest·도우미를 쓰는 것 — 규칙은 전이 검사로 막지 않고 허용하지만(쓰는 레슨이 `gtest = true`여야 함), 지금 그런 유닛은 만들지 않는다
- death test(`EXPECT_DEATH`), 커버리지, `build.py`의 테스트 이름 정규식 옵션 — 계획 없음(Assumption 13)
- 오프라인 configure(googletest 미러·공유 다운로드) — 계획 없음(§4). 필요해지면 KI로
- 다른 레슨의 smoke test를 GoogleTest로 바꾸기 — 하지 않는다

## 7. Dependencies & Backends
GoogleTest v1.14.0(이미 `tests/`가 FetchContent로 씀). 새 패키지 없음. 테스트 코드 전용이라 backend 경계([impl.md](/.agent/rules/impl.md) §5) 대상이 아니다.

## 8. Documentation Updates
| Document | Section | Change |
|---|---|---|
| `lessons/tracks/01_essentials/16_testing/README.md`, `README.en.md` | 전체 | 새로 씀(§2.2) |
| [`lessons/README.md`](/lessons/README.md) | 구조, 매니페스트, 새 레슨 추가 3단계 | `gtest = true`(무엇이 링크·정의되는가, 한 줄), `uses`의 `test:`, 새 check 항목, CMake가 한 줄로 읽는 키에 `gtest` |
| [`lessons/tags.toml`](/lessons/tags.toml) | — | `testing` 태그(§2.6) |
| [`docs/lesson_candidates.md`](/docs/lesson_candidates.md) | Essentials 머리말, 표 | "`01_`–`15_`" → `16_`, `16_testing` E16 행 `레슨 있음` |
| [`tests/README.md`](/tests/README.md) | §1 레슨 줄, §4.1 `gtest/*.json` | 레슨이 GoogleTest를 쓸 수 있다는 것과 `testing` 레슨 링크; `lesson_<id>.json`도 생김 |
| [`.agent/rules/test.md`](/.agent/rules/test.md) | §2 | 레슨의 GoogleTest는 학습 자료이고 프로젝트 테스트 규칙(종류 label, 시나리오 하나 이상)에 들지 않는다(한 줄) |
| [`.agent/rules/config.md`](/.agent/rules/config.md) | configure 항목 | googletest는 `cmake/atugcc_googletest.cmake`, tests 또는 `gtest` 레슨이 있으면 configure가 받는다(플레이그라운드 preset 포함, 첫 configure는 네트워크) |
| [`web/README.md`](/web/README.md) | 실행·진단 설명 | 테스트 실패 줄 표시, `GTEST_*` 환경 변수 지움, 첫 configure의 googletest 다운로드 |
| [`docs/cpp_evolution/source_location.md`](/docs/cpp_evolution/source_location.md) | 레슨·관련 항목 | 테스트 매크로가 아직 매크로인 이유와 `testing` 레슨 링크(한 줄) |
| [`docs/known_issues.md`](/docs/known_issues.md) | 표, 새 KI-042 | KI-042 웹 플레이그라운드에 테스트 결과 보기(케이스별 표·리포트)가 없음 |
| [`docs/agent_todo.md`](/docs/agent_todo.md) | Phase 7, 진행 순서 A.5a | 070-15 줄(링크, 상태), 끝나면 A.5a 취소선 |

## 9. Technical Constraints
- Compiler: MSVC (VS 2026) / Clang 20 with libstdc++ 14 (Linux)
- CMake: 4.0+ (C++20 modules always on), Ninja
- C++ Standard: C++23 (C++20 minimum)
- GoogleTest v1.14.0 (FetchContent)

## 10. Context & References
- [040-02 스펙](/docs/specs/040_02_ctest_scenario_tests.md) Assumption 3·4·12, §6(070-15로 넘긴 항목), [`tests/README.md`](/tests/README.md), [`tests/scenario/scenario.hpp`](/tests/scenario/scenario.hpp), [`tests/scenario/scenario_logged_error_flow.cpp`](/tests/scenario/scenario_logged_error_flow.cpp), [`.agent/scripts/test_report.py`](/.agent/scripts/test_report.py)(`assign_gtest_files`)
- [`tests/CMakeLists.txt`](/tests/CMakeLists.txt)(googletest FetchContent, `ATUGCC_SCENARIO_WORK_ROOT`), [`lessons/CMakeLists.txt`](/lessons/CMakeLists.txt), [CMakePresets.json](/CMakePresets.json)(`linux-x64-playground*`: `ATUGCC_BUILD_TESTS=OFF`)
- [070-14 스펙](/docs/specs/070_14_essentials_modules_lesson.md)(매니페스트 키와 `uses` 접두사 추가의 선례), [070-03 스펙](/docs/specs/070_03_essentials_curriculum.md), [070-01 스펙](/docs/specs/070_01_lesson_structure.md)
- [`tools/lessons.py`](/tools/lessons.py), [`web/server/runner.py`](/web/server/runner.py)(`DIAGNOSTIC_RE`, `parse_diagnostics`, `_execute`의 env), [`web/frontend/src/diagnostics.ts`](/web/frontend/src/diagnostics.ts), [`web/frontend/src/main.ts`](/web/frontend/src/main.ts)
- [`include/atugcc/core/error.hpp`](/include/atugcc/core/error.hpp), [`include/atugcc/core/logger.hpp`](/include/atugcc/core/logger.hpp)
- 이 스펙은 새 시험을 하지 않았다. 레슨에 gtest를 링크한 빌드(두 호스트, 플레이그라운드 preset)와 리포트의 `lesson_testing.json` 배정은 DEV 첫 단계에서 확인하고, 안 되는 것이 있으면 멈추고 스펙을 고친다

## 11. Implementation Plan
- [ ] Step 1: `cmake/atugcc_googletest.cmake`, `tests/CMakeLists.txt`, `lessons/CMakeLists.txt`의 `gtest` 키. 최소 레슨 파일(Step 3의 `main.cpp` + 테스트 하나)로 `windows-x64-debug`, `linux-x64-debug`, `linux-x64-playground` 빌드와 `--report`의 `lesson_testing.json` 배정 확인
- [ ] Step 2: `tools/lessons.py`(`gtest` 스키마·정규식 대조, `test:`, check 규칙, 인덱스)와 `tools/test_lessons.py`
- [ ] Step 3: `16_testing` 레슨(`lesson.toml`, 소스 4개, README 두 판), `tags.toml`
- [ ] Step 4: 웹 `runner.py`(env, 실패 줄), `main.ts`/`api.ts`, `test_server.py`
- [ ] Step 5: §8 문서, KI-042

## 12. Verification Plan
- [ ] `py -3 .agent/scripts/build.py --preset windows-x64-debug --test`, `--preset linux-x64-debug --test`
- [ ] `--preset linux-x64-asan`, `--preset linux-x64-tsan` 빌드와 `ctest -L lesson`
- [ ] `--preset linux-x64-playground`, `linux-x64-playground-release` configure·빌드
- [ ] `lesson_testing`의 `--gtest_list_tests`와 요약 줄 두 OS 비교
- [ ] 연습 1–3을 임시 사본으로(AC-4, AC-5), `--report` 두 번
- [ ] `ctest -N -L unit|scenario|probe` 전후 비교(AC-9)
- [ ] `py -3 tools/test_lessons.py`, `npm --prefix web/frontend test`, `ctest -R PlaygroundServer`
- [ ] 헤드리스 브라우저(AC-7)
- [ ] `lint_docs.py`, `lessons.py check` exit 0
- [ ] 모든 AC 행의 증거가 `testrecord.md`에

## History / Amendments
- 2026-11-04: 초안
- 2026-11-05: 승인. 같은 때 사용자 요청으로 README를 GoogleTest·CTest 튜토리얼로(Assumption 18, §2.2의 README와 fixture, AC-11)
- 2026-11-05 (DEV 리뷰, 동작 변화 없음): §2.2 VersionOrder 줄을 코드에 맞춤(`EXPECT_EQ(*newer, (Version{1, 10, 0}))`), §2.4 CMake 대조의 예(`gtest = "true"`는 차이가 아니라 bool 검사가 잡음), AC-1 명령 `index --out -`(`index -`는 없는 인자), §2.6 별칭에 `TEST_F`, `fixture`, `픽스처`
