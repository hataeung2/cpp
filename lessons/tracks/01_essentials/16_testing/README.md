# 레슨: 테스트 — GoogleTest 단위 테스트, 단계 시나리오, 테스트 리포트 읽기 (`testing`)

이 레슨은 따라 하는 튜토리얼입니다. 작은 버전 파서([`version.hpp`](version.hpp))에 테스트를 쓰고, 일부러 깨뜨리고, 그 실패를 콘솔·편집기·테스트 리포트에서 읽습니다. 다 읽고 나면 다음을 할 수 있습니다.

- GoogleTest로 단위 테스트를 씁니다: `TEST`, `EXPECT`/`ASSERT`, fixture(`TEST_F`), 표 테스트(`TEST_P`), 실패 메시지에 값 보이기(`PrintTo`).
- 이 프로젝트의 단계 도우미로 시나리오를 씁니다: `[step n]`, `[skip n]`, `workDir()`.
- 테스트 프로그램을 옵션으로 골라 돌립니다: `--gtest_filter`, `--gtest_repeat`, `--gtest_shuffle`, `--gtest_output`.
- CTest로 프로젝트의 테스트를 고르고, 실패를 다시 보고, 반복하고, 나란히 돌립니다: `-N`, `-R`, `-L`, `--output-on-failure`, `--rerun-failed`, `--repeat`, `-j`.
- `build.py --report`가 만든 `report.md`에서 무엇이 왜 깨졌는지 찾습니다.

## 파일과 실행
| 파일 | 하는 일 |
|---|---|
| [`version.hpp`](version.hpp) | 시험받는 코드: `Version`, `parseVersion`, `newestVersion`, `PrintTo` |
| [`test_version.cpp`](test_version.cpp) | 단위 테스트 (A1–A5) |
| [`scenario_version_file.cpp`](scenario_version_file.cpp) | 시나리오: 버전 파일 → 파싱 → `Logger` → 로그 파일 (A6) |
| [`main.cpp`](main.cpp) | 진입점: `InitGoogleTest`와 `RUN_ALL_TESTS` (A1, A7) |

`lesson.toml`의 `gtest = true` 한 줄이 이 레슨에 GoogleTest를 링크하고, `tests/scenario/`의 단계 도우미 [`scenario.hpp`](/tests/scenario/scenario.hpp)를 쓸 수 있게 합니다([`lessons/README.md`](/lessons/README.md)).

- 🌐 **웹 플레이그라운드**: 레슨 트리에서 `testing`을 고르고 Run. 고친 파일은 Run이 저장하고 다시 빌드합니다. 실행 인자는 줄 수 없습니다(A7에서 대신하는 법).
- 💻 **로컬**: `py -3 .agent/scripts/build.py --preset <preset> --target lesson_testing`(Linux: `python3`) 뒤 `out/build/<preset>/bin/lessons/lesson_testing`(Windows: `.exe`)을 실행합니다. `<preset>`은 `windows-x64-debug`나 `linux-x64-debug`입니다. Windows 호스트에서 `linux-x64-*` preset은 WSL 안에서 빌드됩니다.

이 문서의 출력은 실제 실행에서 가져왔고, 저장소 위치는 `<repo>`로 줄였습니다. 시간(`(0 ms)`)은 실행마다 다릅니다.

### `assert`와 테스트 프레임워크
| | `assert(x)` / 손으로 쓴 `if` | GoogleTest |
|---|---|---|
| 실패하면 | 첫 실패에서 프로그램이 끝남(`abort`) | 그 검사만 실패로 적고 다음 검사·다음 테스트로 감 |
| 무엇이 깨졌나 | 파일과 줄, 식 | 테스트 이름, 파일과 줄, 식, **두 값** |
| Release 빌드 | `NDEBUG`면 사라짐 | 빌드 종류와 상관없이 돎 |
| 골라 돌리기 | 안 됨 | `--gtest_filter`, CTest `-R`/`-L` |
| 결과를 기계가 읽기 | 종료 코드뿐 | 종료 코드 + JSON/XML 결과 파일 |

## A. GoogleTest

### A1. 첫 테스트와 `main`
테스트 하나는 `TEST(묶음, 이름)` 블록 하나입니다. 이름은 결과와 필터에 그대로 쓰이므로 무엇을 확인하는지 읽히게 짓습니다(`ParseVersion.ReadsThreeNumbers`). GoogleTest는 이름에 밑줄 `_`을 쓰지 말라고 합니다(내부에서 만드는 이름과 겹칠 수 있음).

```cpp
TEST(ParseVersion, ReadsThreeNumbers) {
    const auto result = parseVersion("1.2.3");
    ASSERT_TRUE(result) << "error: " << core::to_string(result.error());
    EXPECT_EQ(result->major, 1u);
    EXPECT_EQ(result->minor, 2u);
    EXPECT_EQ(result->patch, 3u);
}
```

`main`에는 테스트 목록이 없습니다. `TEST`가 만든 전역 객체가 `main` 전에 테스트를 등록하고, `RUN_ALL_TESTS()`가 등록된 것을 모두 돌립니다. 모두 통과하면 0, 하나라도 실패하면 1을 돌려주고, 그 값이 프로그램의 종료 코드입니다. CTest와 웹은 이 종료 코드로 성공·실패를 정합니다. `gtest_main` 라이브러리를 링크하면 이 `main`을 대신 써 줍니다(그때는 `Running main() from …` 한 줄이 더 나옵니다).

```cpp
int main(int argc, char** argv) {
    ::testing::InitGoogleTest(&argc, argv);
    return RUN_ALL_TESTS();
}
```

**해 보기** 🌐💻: 그대로 실행합니다.

**보이는 것**: 테스트마다 `[ RUN ]`/`[ OK ]`, 묶음마다 `[----------]`, 끝에 요약. 시나리오의 `[step n]` 줄은 단계 도우미가 찍습니다(A6).
```text
[==========] Running 13 tests from 6 test suites.
[----------] Global test environment set-up.
[----------] 1 test from ParseVersion
[ RUN      ] ParseVersion.ReadsThreeNumbers
[       OK ] ParseVersion.ReadsThreeNumbers (0 ms)
[----------] 1 test from ParseVersion (0 ms total)
...
[----------] 7 tests from Table/ParseVersionRejects
[ RUN      ] Table/ParseVersionRejects.BadText/0
[       OK ] Table/ParseVersionRejects.BadText/0 (0 ms)
...
[==========] 13 tests from 6 test suites ran. (16 ms total)
[  PASSED  ] 13 tests.
```

### A2. `EXPECT`와 `ASSERT`
같은 비교가 두 가지로 있습니다.
- `EXPECT_*`: 실패를 적고 **계속** 갑니다. 한 번에 여러 값을 확인할 때.
- `ASSERT_*`: 실패를 적고 **그 테스트 함수에서 바로 return**합니다. 뒤 줄이 앞 결과에 기댈 때. 위의 `ASSERT_TRUE(result)`가 그 예입니다: 파싱이 실패했는데 `result->major`를 읽으면 미정의 동작입니다.

자주 쓰는 것:

| 매크로 (`EXPECT_`/`ASSERT_` 둘 다 있음) | 참인 조건 |
|---|---|
| `TRUE(c)`, `FALSE(c)` | `c`가 참 / 거짓 (`std::expected`, `std::optional`도 됨) |
| `EQ(a, b)`, `NE(a, b)` | `a == b` / `a != b` |
| `LT`, `LE`, `GT`, `GE` | `<`, `<=`, `>`, `>=` |
| `STREQ(a, b)` | C 문자열 내용이 같음 (`const char*`를 `EQ`로 비교하면 주소를 비교) |
| `DOUBLE_EQ(a, b)`, `NEAR(a, b, eps)` | 부동소수점이 4 ULP 안 / 차이가 `eps` 이하 |
| `THROW(stmt, E)`, `NO_THROW(stmt)` | `stmt`가 `E`를 던짐 / 아무것도 안 던짐 |

어느 매크로든 `<<`로 설명을 붙일 수 있고, 실패할 때만 계산됩니다(`ASSERT_TRUE(result) << "error: " << …`).

`1u`인 이유: `Version`의 필드는 `unsigned`입니다. `EXPECT_EQ(result->major, 1)`은 GoogleTest 템플릿 안에서 `unsigned`와 `int`를 비교해 `-Wsign-compare` 경고가 나고, 이 프로젝트는 경고를 오류로 다룹니다. 기대값의 타입을 맞추세요.

**해 보기** 🌐💻: [`test_version.cpp`](test_version.cpp)의 `ReadsThreeNumbers`에서 기대값 둘을 틀리게 바꿉니다: `EXPECT_EQ(result->minor, 5u);`, `EXPECT_EQ(result->patch, 7u);`. 실행한 뒤, 첫 줄만 `ASSERT_EQ(result->minor, 5u);`로 바꿔 다시 실행합니다.

**보이는 것**: `EXPECT` 둘이면 실패가 **둘**(36행, 37행), 첫 줄이 `ASSERT`면 **하나**(36행)입니다. `ASSERT`가 return했기 때문에 37행은 검사되지 않았습니다. 테스트 이름은 둘 다 `[  FAILED  ] ParseVersion.ReadsThreeNumbers` 하나이고, 종료 코드는 1입니다.
```text
<repo>\lessons\tracks\01_essentials\16_testing\test_version.cpp(36): error: Expected equality of these values:
  result->minor
    Which is: 2
  5u
    Which is: 5

<repo>\lessons\tracks\01_essentials\16_testing\test_version.cpp(37): error: Expected equality of these values:
  result->patch
    Which is: 3
  7u
    Which is: 7

[  FAILED  ] ParseVersion.ReadsThreeNumbers (0 ms)
```
웹과 Linux(Clang)에서는 같은 실패가 이렇게 시작합니다: `<repo>/lessons/tracks/01_essentials/16_testing/test_version.cpp:36: Failure` 다음 줄에 `Expected equality of these values:`.
웹에서는 실패한 줄(36, 37)에 빨간 표시가 붙고, 마우스를 올리면 메시지가 보입니다. 다음 절로 가기 전에 되돌립니다.

### A3. 실패 메시지 읽기, `PrintTo`
메시지는 늘 같은 모양입니다: `파일(줄)`(MSVC) 또는 `파일:줄: Failure`(Clang, GCC) 다음에 **식의 글자**와 **그 값**.
```text
Expected equality of these values:
  *newer                 ← 첫 인자의 글자
    Which is: 1.10.0     ← 그 값
  (Version{1, 9, 0})     ← 둘째 인자의 글자
    Which is: 1.9.0
```
값을 글자로 바꾸는 방법은 GoogleTest가 찾습니다: 같은 namespace에 `PrintTo(const T&, std::ostream*)`가 있으면 그것(ADL), 없으면 `operator<<`. 둘 다 있으면 `PrintTo`가 이깁니다. 둘 다 없으면 객체의 바이트를 찍습니다. `version.hpp`의 `PrintTo`가 `Version`을 `1.10.0`으로 보이게 합니다. `Expected<Version>`처럼 GoogleTest가 모르는 타입은 바이트로 찍히므로, 비교는 `*newer`처럼 값을 꺼낸 뒤에 합니다.

`(Version{1, 9, 0})`의 괄호: 전처리기는 매크로 인자를 `{}` 안의 쉼표에서도 나눕니다. 괄호로 감싸야 인자 하나가 됩니다.

왜 함수가 아니라 매크로인가: 실패 위치(파일과 줄)는 C++20 `std::source_location`으로도 얻을 수 있지만([05_source_location](../05_source_location/README.md)), 식의 글자(`*newer`)는 전처리기의 `#`만 만들 수 있고, `ASSERT`의 "테스트 함수에서 return"도 함수 호출로는 할 수 없습니다.

**해 보기** 🌐💻: `VersionOrder.ComparesNumbersNotText`의 `EXPECT_EQ(*newer, (Version{1, 10, 0}));`을 `(Version{1, 9, 0})`으로 바꿔 실행합니다. 그다음 `version.hpp`에서 `PrintTo` 함수를 통째로 지우고 다시 실행합니다.

**보이는 것**: `PrintTo`가 있으면 `Which is: 1.10.0`, 없으면 바이트 덤프입니다(`0A`가 10, `09`가 9).
```text
  *newer
    Which is: 12-byte object <01-00 00-00 0A-00 00-00 00-00 00-00>
  (Version{1, 9, 0})
    Which is: 12-byte object <01-00 00-00 09-00 00-00 00-00 00-00>
```
되돌립니다.

### A4. fixture: `TEST_F`
여러 테스트가 같은 준비를 하면 fixture 클래스에 둡니다. `::testing::Test`를 상속하고, 준비는 `SetUp()`, 정리는 `TearDown()`(이 레슨은 필요 없음), 테스트는 `TEST(…)` 대신 `TEST_F(클래스, 이름)`으로 씁니다. 테스트 본문은 fixture의 `protected` 멤버를 그대로 씁니다.

```cpp
class ReleaseListTest : public ::testing::Test {
protected:
    void SetUp() override;           // "1.2.0", "1.10.0", "1.9.3" 을 releases_ 에 넣음
    std::vector<Version> releases_;
};

TEST_F(ReleaseListTest, SortsAscending) {
    std::ranges::sort(releases_);
    ASSERT_EQ(releases_.size(), 3u);
    EXPECT_EQ(releases_.front(), (Version{1, 2, 0}));
    EXPECT_EQ(releases_.back(), (Version{1, 10, 0}));
}
```

- **테스트마다 새 fixture 객체**입니다. `SortsAscending`이 `releases_`를 정렬해도 `NewestIsHighest`는 정렬되지 않은 새 목록을 받습니다. 테스트끼리 순서에 기대지 않게 하는 장치입니다(A7의 `--gtest_shuffle`로 확인).
- `SetUp`의 `FAIL()`이나 `ASSERT_*`가 실패하면 그 테스트 본문은 돌지 않습니다.
- fixture를 쓸 때: 같은 준비가 두 테스트 이상에 있을 때, 정리(`TearDown`)가 꼭 돌아야 할 때. 한 테스트에만 쓰이는 준비는 테스트 안에 둡니다.

**해 보기** 🌐💻: `SetUp`의 목록에 `"2.0"`을 하나 더해 실행합니다(배열 크기도 4로).

**보이는 것**: `ReleaseListTest`의 두 테스트가 모두 `cannot parse 2.0`으로 실패하고, 본문의 검사(`SortsAscending`의 `size() == 3`)는 나오지 않습니다. 되돌립니다.

### A5. 표 테스트: `TEST_P`
같은 검사를 입력만 바꿔 여러 번 할 때 씁니다. 행 하나가 이름 있는 테스트 하나가 되어, 어느 입력이 깨졌는지 결과에 바로 보입니다.

```cpp
class ParseVersionRejects : public ::testing::TestWithParam<std::string_view> {};

TEST_P(ParseVersionRejects, BadText) {
    const auto result = parseVersion(GetParam());
    ASSERT_FALSE(result) << "accepted: " << GetParam();
    EXPECT_EQ(result.error(), core::CoreError::InvalidArgument);
}

INSTANTIATE_TEST_SUITE_P(Table, ParseVersionRejects,
    ::testing::Values("", "1.2", "1.2.3.4", "1.x.3", "-1.2.3", "1..3", "99999999999.0.0"));
```

이름은 `<INSTANTIATE 이름>/<클래스>.<테스트>/<행 번호>`입니다: `Table/ParseVersionRejects.BadText/3`은 `"1.x.3"` 행입니다. `--gtest_list_tests`가 행마다 값을 보여 줍니다(A7). 값 목록은 `::testing::Values` 말고도 `ValuesIn(컨테이너)`, `Range`, `Combine`으로 만들 수 있습니다.

**해 보기** 🌐💻: `Values(…)`의 끝에 `"1.2.3"`을 더합니다. 올바른 버전이므로 "거부해야 한다"는 검사가 실패해야 합니다.

**보이는 것**: 새 행 `/7`만 실패하고, 실패 줄에 그 값이 붙습니다. 되돌립니다.
```text
<repo>\lessons\tracks\01_essentials\16_testing\test_version.cpp(50): error: Value of: result
  Actual: true
Expected: false
accepted: 1.2.3

[  FAILED  ] Table/ParseVersionRejects.BadText/7, where GetParam() = "1.2.3" (0 ms)
```

### A6. 단계 시나리오
단위 테스트는 부품 하나를, 시나리오는 사용자가 지나가는 **흐름 하나**를 봅니다. 이 프로젝트는 시나리오를 이름 있는 단계로 씁니다([`tests/README.md`](/tests/README.md) §3, 도우미 [`scenario.hpp`](/tests/scenario/scenario.hpp)). 이 레슨의 [`scenario_version_file.cpp`](scenario_version_file.cpp):

```cpp
TEST(VersionFileFlow, BadVersionIsLogged) {
    atugcc::test::Scenario s;
    std::unique_ptr<core::Logger> logger;   // 다음 단계가 쓰는 상태는 단계 밖에

    s.step("write a version file with a bad line", [&] { /* workDir()/version.txt 에 "1.2" */ });
    s.step("open a logger that writes a file",     [&] { /* filePath = workDir()/app.log */ });
    s.step("parse the file: the error is logged",  [&] { /* ASSERT_FALSE(result), logger->log(...) */ });
    s.step("the log file has the error line",      [&] { /* flush() 뒤 app.log 에서 찾기 */ });
}
```

- 단계마다 `[step n] <이름>`이 찍히고, 단계 안의 실패 메시지에 `step n: <이름>`이 붙습니다.
- 단계 안에서 `ASSERT_*`가 실패하면 남은 단계는 `[skip n]`으로 찍히고 돌지 않습니다. `EXPECT_*` 실패는 다음 단계를 막지 않습니다.
- 단계는 람다입니다. 다음 단계가 쓸 값(`logger`)은 단계 밖 변수에 둡니다.
- `s.workDir()`은 시나리오마다 따로인 폴더입니다: `out/build/<preset>/lessons/scenario_work/VersionFileFlow.BadVersionIsLogged/`. 시작할 때 비우고 끝나도 **남겨 두므로** 실패한 뒤 파일을 열어 볼 수 있습니다.
- 다른 스레드의 `ASSERT_*`는 단계를 멈추지 못합니다. 스레드는 한 단계 안에서 시작하고 join한 뒤 그 단계에서 검사합니다([`tests/README.md`](/tests/README.md) §3).

**레슨과 `tests/`의 차이**: 이 레슨은 단위 테스트와 시나리오가 한 프로세스에서 돕니다. 그래서 이 시나리오는 프로세스에 한 번 정하는 설정(`configureLogBuffers`, `ATUGCC_TRACE_OUT`, crash dump 대상)을 건드리지 않습니다. `tests/`의 시나리오는 그런 설정을 처음부터 해 보는 것이 목적이라 **시나리오마다 프로세스 하나**로 돕니다(B2의 `gtest_discover_tests`).

| | 이 레슨 | `tests/scenario/` |
|---|---|---|
| 프로그램 | `lesson_testing` 하나 | `atugcc_scenarios` |
| 프로세스 | 13개 테스트가 한 프로세스 | 시나리오마다 하나 |
| CTest 테스트 | `lesson.testing` 하나 | `scenario.<묶음>.<이름>` 시나리오마다 |
| 프로세스 전역 설정 | 쓰지 않음 | 시나리오마다 처음부터 |

**해 보기** 🌐💻: 1단계에서 쓰는 내용을 `"1.2.3\n"`으로 바꿉니다. 올바른 버전이라 3단계의 `ASSERT_FALSE(result)`가 실패합니다. 💻 로컬이면 그 뒤 `workDir()` 폴더의 `version.txt`를 열어 봅니다.

**보이는 것**: 실패 메시지 끝의 `Google Test trace:`가 단계를 알려 주고, 4단계는 `[skip 4]`입니다. 웹에서는 `scenario_version_file.cpp`의 `ASSERT_FALSE` 줄에 표시가 붙습니다. 되돌립니다.
```text
[step 1] write a version file with a bad line
[step 2] open a logger that writes a file
[step 3] parse the file: the error is logged
<repo>\lessons\tracks\01_essentials\16_testing\scenario_version_file.cpp(71): error: Value of: result
  Actual: true
Expected: false
accepted: 1.2.3
Google Test trace:
<repo>\tests\scenario\scenario.hpp(73): step 3: parse the file: the error is logged

[skip 4] the log file has the error line
[  FAILED  ] VersionFileFlow.BadVersionIsLogged (12 ms)
```

### A7. 실행 옵션
GoogleTest 프로그램은 모두 같은 옵션을 받습니다. 💻 로컬에서 실행 파일 뒤에 붙입니다(`<exe>` = `out/build/<preset>/bin/lessons/lesson_testing`).

| 옵션 | 하는 일 |
|---|---|
| `--gtest_list_tests` | 돌리지 않고 이름만 (표 행은 값과 함께) |
| `--gtest_filter=<패턴>` | 이름이 맞는 것만. `*` `?` 와일드카드, `:`로 여럿, `-` 뒤는 뺄 것 |
| `--gtest_repeat=<n>` | n번 반복 (`-1`은 끝없이). 가끔만 깨지는 테스트 찾기 |
| `--gtest_shuffle`, `--gtest_random_seed=<n>` | 순서를 섞음. 같은 seed는 같은 순서 |
| `--gtest_break_on_failure` | 첫 실패에서 디버거가 멈추게 함 |
| `--gtest_brief=1` | 실패한 테스트와 요약만 |
| `--gtest_output=json:<파일 또는 폴더/>` | 결과를 JSON으로 (`xml:`이면 JUnit 모양 XML) |
| `--gtest_also_run_disabled_tests` | 이름이 `DISABLED_`로 시작해 꺼 둔 테스트도 |

`--gtest_list_tests`를 뺀 옵션은 환경 변수로도 줍니다: `--gtest_filter`는 `GTEST_FILTER`, `--gtest_output`은 `GTEST_OUTPUT`처럼 앞에 `GTEST_`, 대문자. 환경 변수는 `main` 전에 기본값이 되고, 명령줄 옵션이 그것을 이깁니다. `build.py --report`는 `GTEST_OUTPUT`으로 결과 파일을 받습니다(C).

**해 보기** 💻:
```text
<exe> --gtest_list_tests
<exe> --gtest_filter=ParseVersion*
<exe> --gtest_filter=*-Table/*:VersionFileFlow.*
<exe> --gtest_filter=ReleaseListTest.* --gtest_repeat=2
<exe> --gtest_shuffle --gtest_random_seed=7
<exe> --gtest_brief=1
<exe> --gtest_filter=NewestVersion.* --gtest_output=json:out/one.json
```

**보이는 것**:
- 목록: 표 행마다 `# GetParam() = …`.
  ```text
  ReleaseListTest.
    NewestIsHighest
    SortsAscending
  ...
  Table/ParseVersionRejects.
    BadText/0  # GetParam() = ""
    BadText/1  # GetParam() = "1.2"
  ```
- 필터는 첫 줄에 `Note: Google Test filter = …`를 찍습니다. `ParseVersion*`은 1개(`ParseVersionRejects`의 행은 묶음 이름이 `Table/…`로 시작하므로 안 맞음), `*-Table/*:VersionFileFlow.*`는 표와 시나리오를 뺀 5개입니다.
- `--gtest_repeat=2`: `Repeating all tests (iteration 1) . . .`, `(iteration 2)`가 차례로.
- `--gtest_shuffle`: `Note: Randomizing tests' orders with a seed of 7 .` 다음에 섞인 순서. fixture가 테스트마다 새것이라 순서가 바뀌어도 통과합니다.
- `--gtest_brief=1`: 통과한 테스트 줄이 없어지고 요약만 남습니다(시나리오의 `[step n]`은 레슨이 직접 찍는 줄이라 남음).
- JSON: 테스트마다 `file`, `line`, `status`, `result`, 실패하면 `failures` 배열. 묶음마다 개수(`tests`, `failures`, `disabled`)와 시간.

🌐 웹에서는 실행 인자를 줄 수 없으므로 [`main.cpp`](main.cpp)에서 `InitGoogleTest` 다음 줄에 써서 해 봅니다(해 본 뒤 지웁니다):
```cpp
    ::testing::InitGoogleTest(&argc, argv);
    GTEST_FLAG_SET(filter, "ReleaseListTest.*");
```
옵션 이름에서 `--gtest_`를 뺀 것이 `GTEST_FLAG_SET`의 첫 인자입니다. 이 자리(`InitGoogleTest` 뒤)에서는 `RUN_ALL_TESTS`가 읽는 옵션만 듣습니다: `filter`, `repeat`, `shuffle`, `random_seed`, `also_run_disabled_tests`, `list_tests`. `brief`와 `output`은 `InitGoogleTest` 안에서 읽히므로 그 앞 줄에 써야 합니다.

## B. CTest
GoogleTest는 **한 프로그램 안의** 테스트 케이스를 돌립니다. CTest(CMake에 딸린 `ctest`)는 **프로그램(명령)** 을 테스트로 등록해 두고 돌립니다. 명령이 0으로 끝나면 통과, 아니면 실패입니다. 그래서 GoogleTest 프로그램, Python 검사 스크립트, 레슨 실행 파일을 한 목록에서 같이 다룹니다.

### B1. 실행하는 곳
- 이 프로젝트는 `CMakePresets.json`에 테스트 preset이 있습니다: `ctest --preset <preset>`은 그 빌드 폴더의 테스트를 돌리고, 실패한 테스트의 출력을 보여 줍니다(`outputOnFailure`).
- 💻 Linux, WSL: 셸에서 바로 `ctest --preset linux-x64-debug …`.
- 💻 Windows: `ctest`는 VS 개발자 명령 프롬프트(Developer PowerShell for VS)에서만 PATH에 있습니다. 그 밖의 셸에서는 `build.py`를 씁니다: `build.py`는 개발자 환경을 스스로 찾아 `ctest`를 부릅니다.
- 먼저 빌드합니다: `ctest`는 빌드하지 않습니다. `build.py --test`/`--label`은 빌드한 뒤 `ctest`를 부릅니다.
- 🌐 웹 플레이그라운드에는 CTest가 없습니다(레슨 실행 파일을 바로 돌림).

### B2. 이 프로젝트가 테스트를 등록하는 방식
CTest의 목록은 CMake가 만듭니다. 네 가지가 있습니다.

1. **레슨마다 하나** ([`lessons/CMakeLists.txt`](/lessons/CMakeLists.txt)): 레슨 실행 파일을 그대로 테스트 `lesson.<id>`로. 시간 제한과 label을 붙입니다.
   ```cmake
   add_test(NAME lesson.${_id} COMMAND ${ATUGCC_TEST_LAUNCHER} $<TARGET_FILE:lesson_${_id}>)
   set_tests_properties(lesson.${_id} PROPERTIES TIMEOUT 10 LABELS "lesson")
   ```
   그래서 이 레슨의 13개 케이스는 CTest에서는 `lesson.testing` **하나**입니다. 하나라도 깨지면 `lesson.testing`이 실패합니다.
2. **단위 테스트 전부를 하나로** ([`tests/CMakeLists.txt`](/tests/CMakeLists.txt)): `atugcc_tests`(140여 케이스)가 테스트 `AllTests` 하나, label `unit`. 단계 도우미가 일부러 실패하는 자기 검사 셋(`ScenarioStep*`)은 따로 프로세스를 갖는 `unit` 테스트입니다.
3. **케이스마다 하나** (`tests/CMakeLists.txt`): `gtest_discover_tests`가 빌드 뒤 프로그램을 `--gtest_list_tests`로 돌려 케이스마다 CTest 테스트를 만듭니다. 시나리오가 이렇게 `scenario.<묶음>.<이름>`이 되고, 각자 프로세스 하나로 돕니다.
   ```cmake
   gtest_discover_tests(atugcc_scenarios
     TEST_PREFIX "scenario."
     WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}
     DISCOVERY_TIMEOUT 30
     PROPERTIES ${ATUGCC_SCENARIO_PROPERTIES})
   ```
4. **probe** (`tests/CMakeLists.txt`): 크래시, 강제 종료, 다시 시작, 특별한 환경이 필요한 검사. probe 프로그램을 `add_test`로 등록하고, 대개 Python 스크립트가 그 프로그램을 돌려 결과 파일을 확인합니다(`CrashDump`, `LogMap`, `TraceStream` …).

**label**은 테스트의 종류입니다: `unit`, `scenario`, `probe`(크래시·종료·환경이 필요한 검사), `lesson`, `long`(오래 걸리는 레슨). 하나의 테스트가 label을 여럿 가질 수 있습니다(`lesson;long`). 종류별 설명은 [`tests/README.md`](/tests/README.md) §1.

### B3. 고르기
| 옵션 | 하는 일 |
|---|---|
| `-N` | 돌리지 않고 목록만 |
| `-R <정규식>` / `-E <정규식>` | 이름이 맞는 것만 / 맞는 것을 빼고 |
| `-L <정규식>` / `-LE <정규식>` | label이 맞는 것만 / 맞는 것을 빼고 |

`-R`, `-L`은 **정규식**입니다. `lesson.testing`의 `.`은 아무 글자이므로 정확히 하나만 고르려면 `^lesson\.testing$`처럼 씁니다. `build.py --label <L>`은 빌드한 뒤 `ctest -L <L>`을 부르는 것과 같고, 맞는 테스트가 없으면 실패합니다(오타가 통과처럼 보이지 않게).

**해 보기** 💻:
```text
ctest --preset linux-x64-debug -N -L lesson
ctest --preset linux-x64-debug -N -L unit
ctest --preset linux-x64-debug -N -L scenario
ctest --preset linux-x64-debug -R "^lesson\.testing$"
```

**보이는 것**: `-N -L scenario`는 시나리오가 케이스마다 하나씩 있는 것을, `-N -L unit`은 단위 테스트 전부가 든 `AllTests`와 자기 검사 셋, 모두 4개를 보여 줍니다.
```text
Test project <repo>/out/build/linux-x64-debug
  Test #1: scenario.TracedStateMachine.EventsReachStreamInOrder
  Test #2: scenario.LoggedErrorFlow.ErrorFromTwoThreadsReachesFile

Total Tests: 2
```
```text
    Start 34: lesson.testing
1/1 Test #34: lesson.testing ...................   Passed    0.04 sec

100% tests passed out of 1

Label Time Summary:
lesson    =   0.04 sec*proc (1 test)
```

### B4. 실패 보기
| 옵션 | 하는 일 |
|---|---|
| `--output-on-failure` | 실패한 테스트의 출력을 보여 줌 (이 프로젝트의 preset은 이미 켬) |
| `-V` | 모든 테스트의 명령과 출력 |
| `--rerun-failed` | 지난번에 실패한 테스트만 다시 |

실패한 테스트의 목록은 빌드 폴더의 `Testing/Temporary/LastTestsFailed.log`에 남습니다(`--rerun-failed`가 이것을 읽음). 모든 출력은 `Testing/Temporary/LastTest.log`.

**해 보기** 💻: A2처럼 기대값 하나를 틀리게 바꾸고 다시 빌드합니다(WSL·Linux 셸에서 `python3 .agent/scripts/build.py --preset linux-x64-debug --target lesson_testing`). 그다음 `--preset` 대신 빌드 폴더를 직접 주어(`--test-dir`, preset의 `outputOnFailure` 없이) 차이를 봅니다:
```text
ctest --test-dir out/build/linux-x64-debug -R "^lesson\.testing$"
ctest --test-dir out/build/linux-x64-debug -R "^lesson\.testing$" --output-on-failure
ctest --test-dir out/build/linux-x64-debug --rerun-failed
```

**보이는 것**: 첫 명령은 `***Failed` 한 줄과 끝의 목록만, 둘째는 GoogleTest 출력 전체(A2의 실패 메시지 포함), 셋째는 `lesson.testing`만 다시 돕니다.
```text
The following tests FAILED:
	 34 - lesson.testing (Failed)                           lesson
```
되돌리고 다시 빌드합니다.

### B5. 반복, 병렬, 시간 제한
| 옵션 | 하는 일 |
|---|---|
| `--repeat until-fail:<n>` | 실패할 때까지 n번까지 (가끔만 깨지는 테스트 찾기) |
| `--repeat until-pass:<n>` | 통과할 때까지 n번까지 (가끔 깨지는 것을 일단 넘기기, 원인은 따로 찾음) |
| `-j <n>` | 테스트 n개를 나란히 |
| `--timeout <초>` | 테스트마다 시간 제한 (테스트에 `TIMEOUT`이 있으면 그것이 우선) |

레슨 테스트의 `TIMEOUT`은 quick 레슨 10초, long 레슨은 매니페스트의 `timeout`(없으면 300초)입니다. 제한을 넘으면 `***Timeout`으로 실패합니다.

`-j`가 안전한 것은 테스트가 서로 파일·포트·전역 상태를 나누지 않을 때뿐입니다. 시나리오가 프로세스와 `workDir()`을 따로 갖는 이유 중 하나입니다.

**해 보기** 💻:
```text
ctest --preset linux-x64-debug -R "^lesson\.testing$" --repeat until-fail:3
ctest --preset linux-x64-debug -L scenario -j 2
```

**보이는 것**: 첫 명령은 같은 테스트가 세 번 `Start`되고, 둘째는 두 시나리오가 함께 시작합니다(`Start 2`, `Start 1`이 먼저 나오고 결과는 끝나는 순서).

## C. 테스트 리포트
`build.py`에 `--report`를 더하면 그 실행의 결과를 파일로 남깁니다: 테스트 목록, CTest 단계마다 JUnit XML, GoogleTest 프로그램마다 JSON(`GTEST_OUTPUT`), 그리고 사람이 읽는 요약 `report.md`. 실패해도 리포트는 남고, 종료 코드는 `--report` 없을 때와 같습니다.

```text
py -3 .agent/scripts/build.py --preset windows-x64-debug --label lesson --report
```

마지막 줄 `report: out/test-reports/<preset>/<날짜-시각>/report.md`가 리포트 위치입니다. 이 레슨이 리포트에 나오는 곳:
- **Results by label**: `lesson` 행의 숫자에 `lesson.testing`이 하나로 들어 있습니다.
- **Failures**: `lesson.testing`이 실패하면 그 아래에 깨진 **케이스 이름**과 메시지. CTest 테스트 하나 안의 13개 중 무엇이 깨졌는지는 GoogleTest JSON에서 옵니다.
- **GoogleTest cases**: `lesson_testing.json` 행(케이스 13, 실패 수).

A2의 기대값을 틀리게 바꾼 상태의 `report.md`(일부):
````markdown
## Results by label
| Label | Tests | Passed | Failed | Not run | Time (s) |
|---|---|---|---|---|---|
| lesson | 17 | 16 | 1 | 0 | 17.82 |

## Failures
### lesson.testing
- `ParseVersion.ReadsThreeNumbers`:
```
lessons/tracks/01_essentials/16_testing/test_version.cpp:36
Expected equality of these values:
  result->minor
    Which is: 2
  5u
    Which is: 5
```

## GoogleTest cases
| Program | Cases | Failed | Disabled |
|---|---|---|---|
| lesson_testing.json | 13 | 1 | 0 |
````

리포트의 모든 부분(Steps, Slowest tests, Inputs, 실패를 따라가는 순서)은 [`tests/README.md`](/tests/README.md) §4가 설명합니다.

**실패를 읽는 세 곳**
| 어디서 | 무엇이 보이나 |
|---|---|
| 콘솔 출력 | 전부. MSVC는 `파일(줄): error:`, Clang·GCC는 `파일:줄: Failure` |
| 🌐 웹 편집기 | 실패한 `ASSERT`/`EXPECT` 줄의 빨간 표시와 메시지 |
| 💻 `report.md` | 실행 전체에서 실패한 CTest 테스트와 그 안의 케이스, 메시지, 시간 |

웹에는 리포트가 없습니다. 리포트는 CTest 실행(`build.py` → `ctest`)에서 나오는데, 웹은 CTest 없이 레슨 실행 파일 하나를 바로 돌리기 때문입니다([KI-042](/docs/known_issues.md)).

## 연습
1. **`EXPECT`와 `ASSERT`, 값 보이기** 🌐💻: A2와 A3의 "해 보기"를 차례로 합니다. 그다음 `Version`에 `operator<<`를 더하고 `PrintTo`를 지워도 메시지가 `1.10.0`으로 나오는지 확인합니다(GoogleTest는 둘 중 하나를 씀). 되돌립니다.
2. **시나리오 단계 깨기** 🌐💻: A6의 "해 보기"를 하고, 💻 로컬에서 `workDir()`의 `version.txt`와 `app.log`를 엽니다(3단계가 멈췄으므로 `app.log`에는 오류 줄이 없음). 그다음 💻 시나리오만 돌립니다: `<exe> --gtest_filter=VersionFileFlow.*`. 되돌립니다.
3. **리포트 읽기와 새 테스트** 💻: A2처럼 테스트 하나를 깬 상태로 `py -3 .agent/scripts/build.py --preset <preset> --label lesson --report`를 돌려, `report.md`의 Failures에서 케이스 이름과 줄을, GoogleTest cases에서 `lesson_testing.json`의 실패 1을 찾습니다. 되돌린 뒤 `ParseVersionRejects`의 표에 거부해야 할 입력 하나(예: `" 1.2.3"`, 앞에 빈칸)를 더하고, 통과하는지 예측한 다음 실행해 확인합니다.

## 빠른 참조
**매크로**
| 쓰임 | 쓰는 것 |
|---|---|
| 테스트 하나 | `TEST(Suite, Name) { … }` |
| 준비를 같이 쓰는 테스트 | `class F : public ::testing::Test { protected: void SetUp() override; };` + `TEST_F(F, Name)` |
| 표 테스트 | `class P : public ::testing::TestWithParam<T> {};` + `TEST_P(P, Name)` + `INSTANTIATE_TEST_SUITE_P(Inst, P, ::testing::Values(…))`, 본문에서 `GetParam()` |
| 계속 / 멈춤 | `EXPECT_*` / `ASSERT_*` |
| 바로 실패 | `ADD_FAILURE()`(계속), `FAIL()`(멈춤), `GTEST_SKIP()`(건너뜀으로 표시) |
| 메시지 붙이기 | `EXPECT_EQ(a, b) << "…";` |
| 흐름에 이름 | `SCOPED_TRACE("…")` (이 프로젝트의 단계 도우미가 씀) |
| 값 보이기 | `operator<<` 또는 같은 namespace의 `PrintTo(const T&, std::ostream*)` |

**GoogleTest 옵션** (`--gtest_list_tests` 말고는 `GTEST_<대문자>` 환경 변수로도)
| 옵션 | 하는 일 |
|---|---|
| `--gtest_list_tests` | 목록 |
| `--gtest_filter=A*:B.*-C.*` | 고르기와 빼기 |
| `--gtest_repeat=N`, `--gtest_shuffle`, `--gtest_random_seed=N` | 반복, 섞기 |
| `--gtest_brief=1`, `--gtest_output=json:<경로>` | 짧은 출력, 결과 파일 |
| `--gtest_break_on_failure` | 디버거에서 멈춤 |

**CTest와 `build.py`** (`<p>` = preset)
| 하고 싶은 것 | 명령 |
|---|---|
| 빌드하고 전부 | `py -3 .agent/scripts/build.py --preset <p> --test` |
| 빌드하고 한 종류 | `py -3 .agent/scripts/build.py --preset <p> --label lesson` |
| 빌드하고 리포트까지 | 위 명령에 `--report` |
| 목록 | `ctest --preset <p> -N` (`-L <label>`, `-R <이름>`) |
| 하나만 | `ctest --preset <p> -R "^lesson\.testing$"` |
| 실패한 것만 다시 | `ctest --preset <p> --rerun-failed` |
| 가끔 깨지는 것 찾기 | `ctest --preset <p> -R <이름> --repeat until-fail:20` |
| 나란히 | `ctest --preset <p> -j 4` |

해설: 테스트의 종류와 리포트 [`tests/README.md`](/tests/README.md), 위치 정보 [05_source_location](../05_source_location/README.md), 오류 값 [04_error_expected](../04_error_expected/README.md).
