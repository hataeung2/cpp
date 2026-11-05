---
id: 040-02
title: CTest 시나리오 테스트 (GoogleTest 시나리오를 따로 등록·선택·실행)
depends_on: []
unblocks: [070-15]
approved: 2026-11-04
---

# Spec 040-02: CTest 시나리오 테스트 (GoogleTest 시나리오를 따로 등록·선택·실행)

배경: [090-05](/docs/specs/090_05_backlog_sync.md) D6("단위 테스트 외에 시나리오 테스트를 추가하고 실행하는 기능"), 진행 순서 A-5("이후 레슨·패턴·엔진 작업이 시나리오 테스트를 바로 쓰게 한다"). 지금 `tests/`의 GoogleTest 135개는 모두 실행 파일 하나(`atugcc_tests`)에 들어 있고 CTest에는 테스트 하나(`AllTests`)로 등록된다. 그 밖의 CTest 테스트는 probe 실행 파일과 Python 스크립트가 짝을 이룬 것들(`TraceStream`, `CrashDump`, `LogMap` 등)이고, label은 레슨(`lesson`, `long`)과 `PlaygroundServer`(`playground`)에만 있다. 그래서 "여러 구성 요소를 엮은 흐름"을 테스트할 자리가 없고, 그런 테스트만 골라 돌릴 수도 없다.

## 0. Assumptions (please review)
| # | Decision | Rejected alternative | Why |
|---|---|---|---|
| 1 | **시나리오 테스트의 정의**: 공개 헤더만 써서, 라이브러리 사용자가 하는 흐름 하나를 여러 단계(step)로 끝까지 따라가는 GoogleTest 테스트. 구성 요소 둘 이상을 엮거나, 한 구성 요소의 수명 전체(설정 → 사용 → 정리)를 다룬다. **단위 테스트**는 한 구성 요소의 한 동작이다. 프로세스를 죽이거나 다시 띄워야 하는 확인(crash, kill, 다음 실행의 복구)은 지금처럼 **probe 테스트**(probe 실행 파일 + 스크립트)로 남긴다 | 시나리오를 데이터 파일(YAML/JSON)로 적고 해석기가 실행 | 해석기와 그 문법을 따로 유지해야 한다. C++ 라이브러리의 흐름은 C++ 코드가 가장 정확하게 적고, 컴파일러가 검사한다 |
| 2 | 시나리오는 **별도 실행 파일 `atugcc_scenarios`**(`tests/scenario/`)에 둔다. 단위 테스트 `atugcc_tests`와 CTest `AllTests`는 그대로 둔다 | (a) `atugcc_tests` 전체를 `gtest_discover_tests`로 쪼갬. (b) 같은 실행 파일 안에서 이름 규칙(`*Scenario*`)과 `TEST_FILTER`로 나눔 | (a) `build.py --gtest-filter`(`-R ^AllTests$` + `GTEST_FILTER`, 090-06)와 그 문서·시험이 모두 바뀌고, 단위 테스트 135개가 각자 프로세스를 띄워 Windows에서 느려진다. 얻는 것은 시나리오 선택뿐인데 그것은 이 안으로 충분하다. (b) 시나리오가 단위 테스트와 링크 단위·전역 상태를 공유하고, 새 단위 테스트 이름이 우연히 규칙에 걸릴 수 있다 |
| 3 | **시나리오 하나 = CTest 테스트 하나 = 프로세스 하나.** `gtest_discover_tests(atugcc_scenarios TEST_PREFIX "scenario." ...)`로 등록해 이름은 `scenario.<Suite>.<Name>` | 시나리오 실행 파일 전체를 CTest 테스트 하나로 | 라이브러리에는 프로세스에 한 번만 정해지는 상태가 있다: `configureLogBuffers`(첫 `mappedDir`), `environmentEventSink()`(`ATUGCC_TRACE_OUT`을 한 번 읽음), crash dump 대상. 시나리오마다 새 프로세스여야 각자 처음부터 설정할 수 있고, `ctest -j`로 나란히 돌릴 수 있다. 이름 모양은 레슨의 `lesson.<id>`와 맞춘다 |
| 4 | **`tests/`의 모든 CTest 테스트에 종류 label을 정확히 하나** 붙인다: `unit`(`AllTests`), `scenario`(시나리오 전부), `probe`(`TraceStream`, `SpanCost`, `DumpPrepare_*`, `LogSlotsFromEnvironment`, `LoggerContention`, `CrashDump`, `LogMap`, `LessonConsoleCodePage`, `PlaygroundServer`). `PlaygroundServer`는 지금의 `playground`도 유지(`probe;playground`). 레슨의 `lesson`/`long`은 그대로 | 시나리오에만 label | `ctest -LE scenario`에는 레슨과 probe가 섞인다. 종류마다 label이 있어야 `ctest -L unit`(가장 빠른 확인), `-L scenario`, `-L probe`를 각각 고를 수 있다. 붙이는 비용은 `set_tests_properties` 몇 줄이다 |
| 5 | **단계 도우미** `tests/scenario/scenario.hpp`(테스트 전용, `namespace atugcc::test`): `Scenario` 객체의 `step(name, fn)`. 단계마다 `[step n] <name>`을 stdout에 쓰고 `SCOPED_TRACE`로 실패 메시지에 단계 번호와 이름을 붙인다. 한 단계에서 fatal 실패(`ASSERT_*`, `FAIL()`)가 나면 뒤 단계는 실행하지 않고 `[skip n] <name>`만 쓴다. non-fatal 실패(`EXPECT_*`)는 멈추지 않는다. 라이브러리 API(`include/atugcc/`)가 아니다 | (a) 도우미 없이 `TEST` 본문에 주석으로 단계 표시. (b) Given/When/Then 세 종류의 함수 | (a) 실패가 어느 단계인지 메시지에 없고, 단계를 람다로 나누면 람다 안의 `ASSERT`는 람다만 빠져나와 뒤 단계가 깨진 상태로 계속 돈다. 도우미는 이 두 가지를 막는다. (b) 이름만 늘고 동작은 같다. 단계 이름 문장이 그 구분을 대신한다 |
| 6 | 시나리오마다 **자기 작업 디렉터리**: `Scenario::workDir()` = `<빌드 디렉터리>/tests/scenario_work/<Suite>.<Name>`, `Scenario`를 만들 때 비우고 새로 만든다. 끝나도 지우지 않는다(실패를 조사할 수 있게) | `std::filesystem::temp_directory_path()` 아래 | 빌드 디렉터리 밖에 파일이 쌓이지 않고, 실패한 시나리오의 파일이 다음 실행 전까지 그 자리에 남는다. 이름이 시나리오마다 달라 `ctest -j`에서도 겹치지 않는다 |
| 7 | 등록 설정: 발견 시점 `POST_BUILD`(CMake 기본), `DISCOVERY_TIMEOUT 30`, 테스트마다 `TIMEOUT 120`. `atugcc_scenarios`의 `TEST_LAUNCHER` 속성 = `ATUGCC_TEST_LAUNCHER`(TSan에서 `setarch -R`; `gtest_discover_tests`가 발견과 실행 모두에 쓴다, CMake 3.29+). TSan에서는 `PROPERTIES ENVIRONMENT TSAN_OPTIONS=suppressions=tests/tsan.supp`, `AllTests`와 같게 | `PRE_TEST`(ctest를 돌릴 때마다 목록 작성); 시나리오별 timeout | 목록 작성이 깨지면(예: 정적 초기화에서 abort) 그 변경을 빌드한 자리에서 바로 보인다. 기본 5초는 Windows에서 새 실행 파일을 처음 띄울 때(백신 검사) 모자랄 수 있다. 지금 시나리오에 따로 긴 timeout이 필요한 것은 없다 |
| 8 | **`build.py --label <L>`**: 빌드 뒤 `ctest --preset <p> -L <L> --no-tests=error`를 돌린다. `--test`와 함께 주면 전체 대신 이 하나만 돈다. `%`, `"`, 줄바꿈은 `--gtest-filter`와 같은 이유로 거부(exit 2) | build.py는 그대로 두고 `ctest -L`을 직접 실행 | Windows 호스트에서 Linux preset은 WSL 안에서 돌아야 하고, 그 일을 하는 것이 "한 명령" build.py다([config.md](/.agent/rules/config.md) §1). `--no-tests=error`: 오타 난 label이 "테스트 0개, 통과"로 끝나지 않게 |
| 9 | **첫 시나리오 둘**(구조가 실제로 쓰이는지 증명): **S1 `TracedStateMachine`** — 패턴 State + Tracer + span + `JsonLinesEventSink`. **S2 `LoggedErrorFlow`** — `Expected` 오류 + `Logger` + 프로세스 전역 `configureLogBuffers`(두 스레드). 내용은 §2.2 | 기존 테스트 중 흐름에 가까운 것을 옮김 | 기존 테스트는 지금 자리에서 통과하고 있고, 옮기면 이 작업의 증거와 기존 증거가 섞인다. S2는 프로세스 전역 설정을 쓰므로 Assumption 3의 이유를 직접 보여 준다 |
| 10 | **이후 작업이 시나리오를 쓰는 규칙**: 패턴 작업(021–024)과 엔진 작업(Phase 6)은 단위 테스트에 더해 시나리오를 하나 이상 더한다(패턴을 실제 흐름에 적용한 모습). 이 규칙은 [test.md](/.agent/rules/test.md)와 `agent_todo.md`의 "작업 공통 원칙"에 적는다 | 규칙 없이 각 작업이 정함 | 진행 순서 A-5가 이 작업을 앞에 둔 이유다. 규칙이 없으면 다음 패턴 작업이 다시 "시나리오가 필요한가"를 정해야 한다 |
| 11 | 기존 테스트는 옮기지 않는다. 지금 `atugcc_tests`에 있는 흐름 성격의 테스트는 그 모듈을 다음에 고치는 작업이 옮길 수 있다 | 이 작업에서 전부 분류해 옮김 | 옮기는 일 자체가 이 작업의 목적(구조와 규칙)과 무관하고, 테스트 135개를 다시 검증해야 한다 |
| 12 | **테스트 리포트 `build.py --report [DIR]`** (사용자 요청 2026-11-04): 그 실행의 ctest 단계마다 JUnit XML(`ctest --output-junit`), gtest 케이스별 JSON(`GTEST_OUTPUT=json:<DIR>/gtest/`), 테스트 목록과 label(`ctest --show-only=json-v1`), 그리고 셋을 읽어 만든 사람용 요약 `report.md`를 남긴다. `--test`, `--label`, `--gtest-filter`와 함께 쓴다 | (a) 작업별 `testrecord.md`만. (b) gtest 출력만(`--gtest_output`) | (a) testrecord는 AC 증거를 골라 적는 문서라, 작업 밖에서 직접 돌린 결과가 남을 곳이 없다. (b) `AllTests`는 CTest 항목 하나라 ctest 결과만으로는 135개 중 무엇이 깨졌는지 모르고, 반대로 gtest 출력만으로는 probe·레슨·시나리오 항목(각자 프로세스)의 결과와 시간이 빠진다. 둘을 합쳐야 한 번의 실행 전체가 보인다 |
| 13 | **리포트 위치**: 기본 `out/test-reports/<preset>/<YYYYMMDD-HHMMSS>/`. `DIR`을 주면 저장소 루트 기준 **상대 경로**만 받는다(절대 경로는 exit 2). 커밋하지 않는다(`out/`은 이미 gitignore) | `tests/report/` 또는 최상위 `testreport/`에 두고 커밋 | 생성물이 소스 트리에 섞이면 실행할 때마다 diff가 생기고, JUnit·gtest 출력에는 실행 파일의 절대 경로가 들어가 non-negotiable rule 1에 걸린다. 상대 경로만 받으면 Windows에서 WSL로 넘길 때도 같은 폴더를 가리킨다 |
| 14 | **testrecord와의 관계**: 작업의 AC 증거는 여전히 `testrecord.md`. 증거로 쓰는 실행은 `--report`로 돌리고, testrecord에는 명령과 `report.md`의 요약(숫자, 실패 목록)을 옮겨 적는다. 리포트 폴더 자체는 링크하지 않는다(커밋되지 않으므로) | 리포트를 testrecord 대신 쓴다 | testrecord는 저장소에 남는 기록이고, 리포트는 로컬 산출물이다. 역할을 나눈다 |
| 15 | **리포트는 실패해도 남긴다**: ctest 단계가 하나라도 실행됐으면, 단계가 실패해 뒤 단계가 멈췄어도 그때까지의 결과로 `report.md`를 쓴다. 종료 코드는 지금처럼 처음 실패한 단계의 코드. 빌드가 실패해 ctest가 하나도 돌지 않았으면 리포트를 쓰지 않고 그렇다고 출력한다 | 성공했을 때만 | 리포트가 가장 필요한 때가 실패했을 때다. Windows에서는 단계가 배치 파일 안에서 돌고 첫 실패에서 배치가 끝나므로, 요약은 배치가 끝난 뒤 Python에서 만든다 |

## 1. Objective
GoogleTest로 쓴 **시나리오 테스트**를 단위 테스트와 따로 등록하고, CTest label로 골라 실행할 수 있게 한다. 시나리오는 각자 새 프로세스에서 돌아 프로세스 전역 설정을 처음부터 할 수 있고, 실패하면 어느 단계에서 깨졌는지 보인다. 이후 패턴·엔진·레슨 작업은 `tests/scenario/`에 파일 하나와 CMake 목록 한 줄을 더해 시나리오를 추가한다. 단위·시나리오·probe 어느 것을 돌리든 `--report`를 주면 그 실행의 결과가 파일(케이스별 결과, 실패 메시지, 시간, 요약)로 남는다.

## 2. Requirement Details

### 2.1 Public API Surface
라이브러리 공개 API(`include/atugcc/`) 변경 없음. 테스트·도구 쪽 표면:

**`tests/scenario/scenario.hpp`** (테스트 전용, header-only)
```cpp
namespace atugcc::test {
class Scenario {
public:
    Scenario();                                   // workDir()를 비우고 새로 만든다 (현재 gtest 테스트 이름으로)
    const std::filesystem::path& workDir() const noexcept;

    // [step n] name 을 쓰고 fn()을 실행한다. 앞 단계에 fatal 실패가 있었으면 [skip n] name만 쓰고 돌아온다.
    // 돌려주는 값: 이 단계가 fatal 실패 없이 끝났는가.
    template <std::invocable F>
    bool step(std::string_view name, F&& fn);
};
}
```
사용 모양:
```cpp
TEST(LoggedErrorFlow, ErrorFromTwoThreadsReachesFile) {
    atugcc::test::Scenario s;
    s.step("configure per-thread log buffers", [&] { ASSERT_TRUE(core::configureLogBuffers({...})); });
    s.step("two threads log the same error",   [&] { /* 스레드 시작, join */ });
    s.step("the log file has both lines",      [&] { /* 파일 읽고 EXPECT */ });
}
```

**CTest**
- `scenario.<Suite>.<Name>`: label `scenario`, 시나리오마다 프로세스 하나.
- `AllTests`: label `unit`. probe 테스트(Assumption 4 목록): label `probe`.

**`.agent/scripts/build.py`**
- `--label <L>`: 빌드 뒤 `ctest --preset <p> -L <L> --no-tests=error`. `--test`와 함께면 이 단계가 전체 ctest를 대신한다. `--gtest-filter`와는 독립(둘 다 주면 둘 다 돈다). WSL로 넘길 때 그대로 전달.
- `--report [DIR]`: ctest 단계가 있는 실행(`--test`, `--label`, `--gtest-filter` 중 하나 이상)의 결과를 `DIR`(기본 `out/test-reports/<preset>/<YYYYMMDD-HHMMSS>/`)에 남긴다. ctest 단계가 없거나 `DIR`이 절대 경로면 exit 2. 마지막 줄에 `report: <DIR>/report.md`를 출력한다.

**리포트 폴더**
```text
out/test-reports/<preset>/<YYYYMMDD-HHMMSS>/
  report.md              사람용 요약 (아래)
  tests.json             ctest --show-only=json-v1 (테스트 이름, label, 명령)
  ctest-<n>.junit.xml    ctest 단계마다 하나 (n = 1, 2: --test/--label 단계, --gtest-filter 단계)
  gtest/*.json           gtest 실행 파일마다 (AllTests 하나, 시나리오 프로세스마다 하나)
```

**`report.md` 내용**
1. 머리: preset, 날짜, git commit(짧은 해시, 변경 있음 표시), 컴파일러(`CMakeCache.txt`의 `CMAKE_CXX_COMPILER_ID`·`_VERSION`), 실행한 `build.py` 명령, 단계별 종료 코드.
2. label별 표: `unit` / `scenario` / `probe` / `lesson` / 그 밖 — 전체, 통과, 실패, 건너뜀, 시간 합계.
3. 실패 목록: CTest 항목 이름, gtest 케이스(`Suite.Name`)가 있으면 그 이름과 실패 메시지(gtest JSON의 failure), 없으면 ctest가 JUnit에 담은 출력의 마지막 30줄. 시나리오는 실패한 `step n: <name>`이 메시지에 들어 있다.
4. 느린 항목 상위 5개(CTest 항목), gtest 케이스 수(전체·실패·비활성).
5. 경로는 모두 저장소 루트 기준 상대 경로로 쓴다(절대 경로 없음).

### 2.2 Internal Implementation
**CMake** ([tests/CMakeLists.txt](/tests/CMakeLists.txt))
- `include(GoogleTest)`, `add_executable(atugcc_scenarios ...)`(시나리오 파일을 명시 목록으로; 기존 `TEST_SOURCES`와 같은 방식), 링크 `atugcc_headers atugcc_core gtest gtest_main`.
- `set_target_properties(atugcc_scenarios PROPERTIES TEST_LAUNCHER "${ATUGCC_TEST_LAUNCHER}")` (빈 값이면 생략). `ATUGCC_SANITIZERS`면 `ATUGCC_SANITIZED_BUILD` 정의(`atugcc_tests`와 같게).
- `gtest_discover_tests(atugcc_scenarios TEST_PREFIX "scenario." WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR} DISCOVERY_TIMEOUT 30 PROPERTIES LABELS scenario TIMEOUT 120 [ENVIRONMENT TSAN_OPTIONS=...])`.
- `workDir()`의 기준 디렉터리는 컴파일 정의 `ATUGCC_SCENARIO_WORK_ROOT="${CMAKE_CURRENT_BINARY_DIR}/scenario_work"`로 넘긴다(작업 디렉터리에 기대지 않음). 이 경로는 빌드 산출물에만 들어가고 저장소 파일에는 들어가지 않는다.
- 기존 테스트에 label: `AllTests` → `unit`, Assumption 4의 probe 목록 → `probe`(`PlaygroundServer`는 `probe;playground`).

**단계 도우미**
- 단계 번호는 1부터. `SCOPED_TRACE`의 메시지는 `step n: <name>`.
- fatal 실패 판정은 `::testing::Test::HasFatalFailure()`. 이 값은 **호출한 스레드**의 실패만 본다: 단계 안에서 띄운 스레드는 단계 안에서 join하고, 판정에 쓰는 `ASSERT`는 시나리오 스레드에서 한다(test.md에 적음).
- `workDir()` 이름은 `<test_suite_name>.<test_name>`. 매개변수화 테스트의 `/`는 `_`로 바꾼다.

**S1 `TracedStateMachine.EventsReachStreamInOrder`** ([state.hpp](/include/atugcc/pattern/state.hpp), [visualizer.hpp](/include/atugcc/pattern/visualizer.hpp))
1. `workDir()/trace.jsonl`로 `JsonLinesEventSink`를 만들고 Tracer에 붙인다.
2. 장치 상태 머신을 정해진 이벤트 순서로 돌린다(IDLE → STANDBY → RUN → ABORT → IDLE를 거치는 순서). 전이 하나하나를 span으로 감싼다.
3. Tracer를 끝내고(소멸) 파일을 닫는다.
4. 파일을 줄 단위로 읽는다: 전이 이벤트가 돌린 순서와 같은 (from, to)로 나오고, `seq`가 줄마다 증가하고, span 이벤트가 전이 수만큼 있고, 마지막에 diagram parts 줄이 있다.

**S2 `LoggedErrorFlow.ErrorFromTwoThreadsReachesFile`** ([error.hpp](/include/atugcc/core/error.hpp), [logger.hpp](/include/atugcc/core/logger.hpp), [log_buffer_config.hpp](/include/atugcc/core/log_buffer_config.hpp))
1. `configureLogBuffers`로 스레드별 버퍼를 설정한다(`mappedDir = workDir()/map`). 프로세스에 한 번인 설정이며 이 시나리오의 프로세스에서는 처음이다.
2. `Logger`(파일 출력 `workDir()/app.log`)를 만든다.
3. 두 스레드가 `std::latch`로 맞춰 같은 함수를 부른다. 그 함수는 `Expected`로 `CoreError::FileIOFailure`를 돌려주고, 호출한 쪽이 오류 이름을 로그로 남긴다. 두 스레드를 join한다.
4. `flush()` 뒤 파일에 두 줄이 있고, 각 줄에 `FileIOFailure`와 로그를 남긴 호출 위치(시나리오 파일 이름과 줄)가 있다.

정확한 API 호출(타입 이름, 상태 머신 이벤트 이름)은 구현 계획(plan.md)이 헤더를 보고 정한다. 위의 단계와 확인 내용은 바꾸지 않는다.

**build.py**
- `bad_filter`와 같은 검사를 `--label`에도 적용(메시지의 옵션 이름만 다름).
- `build_steps(..., label)`: label이 있으면 전체 ctest 단계(`--test`) 대신 `["ctest", "--preset", p, "-L", label, "--no-tests=error"]`. Windows 배치에서는 `^`, `|` 같은 문자를 090-06의 인용 규칙대로 감싼다(label은 정규식이다).
- `--report`가 있으면 ctest 단계마다 `--output-junit <절대 경로>/ctest-<n>.junit.xml`을 붙이고(ctest는 상대 경로를 빌드 디렉터리 기준으로 읽는다) 환경에 `GTEST_OUTPUT=json:<절대 경로>/gtest/`를 더한다. 목록 단계 `ctest --preset p --show-only=json-v1`의 출력은 `tests.json`으로 저장한다(라벨 집계용, 첫 ctest 단계 앞).
- 기본 `DIR`의 시각은 바깥 프로세스가 정하고, WSL로 넘길 때 상대 경로로 넘긴다(`--report out/test-reports/<preset>/<시각>`). 안쪽 build.py가 같은 폴더에 쓴다.
- 요약 작성은 새 모듈 `.agent/scripts/test_report.py`(새 파일)(`write_report(report_dir, ...)`, 표준 라이브러리 `xml.etree`·`json`만)가 한다. build.py는 단계 실행이 끝난 뒤(성공이든 실패든, Assumption 15) 호출한다. 혼자 실행도 된다: `py -3 .agent/scripts/test_report.py <DIR>`(이미 있는 결과로 `report.md` 다시 쓰기).
- `--dry-run`: 단계에 붙는 `--output-junit`, `GTEST_OUTPUT`과 리포트 폴더를 보여 주고, 폴더는 만들지 않는다.

### 2.3 Platform Specifics
- Windows(MSVC, Ninja): `POST_BUILD` 발견은 빌드 중 VS 개발자 환경에서 실행 파일을 띄운다. gtest는 정적 링크라 DLL 경로 문제가 없다.
- Linux TSan: 발견과 실행 모두 `setarch -R`(Assumption 7). ASan: 목록 작성 프로세스는 할당 없이 끝나므로 LSan 보고 없음.
- 그 밖에는 없음.

## 3. C++ Standard Evolution
N/A (테스트 구조와 도구). 도우미가 `std::invocable` concept과 `std::filesystem`을 쓰지만 새로 소개할 기능은 아니다.

## 4. Edge Cases
- [x] Thread safety: 도우미는 시나리오 스레드에서만 부른다. `HasFatalFailure()`가 스레드별이라 다른 스레드의 `ASSERT`는 뒤 단계를 멈추지 못한다 → 스레드는 단계 안에서 join, 판정은 시나리오 스레드에서(§2.2, test.md). S2는 `std::latch`로 두 스레드를 맞춘다.
- [x] Resource lifetime: 단계 람다는 `TEST` 본문의 지역 변수를 참조로 잡고 `step` 안에서 동기로 실행된다(보관하지 않음). S1은 sink 파일을 Tracer가 끝난 뒤 읽는다. S2는 `flush()` 뒤 읽는다.
- [x] Platform differences: §2.3. 경로는 `std::filesystem::path`로만 조립한다.
- [x] Template / concept: `step`은 `std::invocable<F>`로 제한한다. 인자를 받는 람다는 컴파일 오류.
- [x] ODR: `scenario.hpp`는 header-only, 멤버 함수는 클래스 안에 정의(암묵적 `inline`), 정적 지역 변수 없음. 단위 테스트 실행 파일(도우미 자체 시험)과 시나리오 실행 파일은 서로 다른 프로그램이다.
- N/A Undefined behaviour: 캐스트·정렬·시그널 처리 없음.
- [x] 프로세스 전역 상태: 시나리오마다 새 프로세스(Assumption 3). 같은 실행 파일을 `--gtest_filter` 없이 직접 돌리면 시나리오들이 한 프로세스를 공유한다 → 직접 실행은 지원하는 방법이 아니라고 test.md에 적는다.
- [x] 병렬 실행(`ctest -j`): 작업 디렉터리가 시나리오 이름별(Assumption 6).
- [x] 오타 난 label: `--no-tests=error`로 실패(Assumption 8).
- [x] 시나리오 실행 파일에 테스트가 없음: `gtest_discover_tests`는 아무것도 등록하지 않고 `--label scenario`는 실패한다. 이 작업이 끝나면 S1, S2가 있으므로 생기지 않는다.
- [x] 목록 작성 실패(실행 파일이 시작하자마자 죽음): `POST_BUILD`라 빌드가 실패한다(Assumption 7).
- [x] 리포트: 테스트가 crash·timeout으로 끝나 gtest JSON이 없음 → 그 항목은 JUnit의 상태와 출력으로 실패 목록에 나온다(§2.1 3번). JSON이 깨졌거나 반쯤 쓰였으면 그 파일을 건너뛰고 `report.md`에 "읽지 못함: <파일>"을 적는다. 리포트 작성이 실패해도 종료 코드는 ctest 단계의 것을 바꾸지 않고, 오류는 stderr에 쓴다.
- [x] 리포트: 같은 실행 파일을 여러 프로세스가 씀(시나리오) → gtest가 `atugcc_scenarios.json`, `atugcc_scenarios_1.json` …으로 이름을 겹치지 않게 고른다. build.py는 ctest를 순서대로(`-j` 없이) 돌리므로 이름 고르기가 경쟁하지 않는다. 사용자가 다른 방법으로 `-j`를 주어 파일이 겹쳐도, 시나리오의 통과·실패는 JUnit(항목마다 하나)에서 온다.
- [x] 리포트: `GTEST_OUTPUT`은 gtest가 아닌 테스트(probe, 레슨)에는 아무 영향이 없다. 시나리오 목록 작성(빌드 중)에는 설정되지 않는다.
- [x] 리포트: 같은 `DIR`을 다시 주면 → 그 폴더의 이전 결과를 지우고 쓴다(섞인 결과가 요약에 들어가지 않게). 기본 `DIR`은 초 단위 시각이라 겹치지 않는다.
- [x] 리포트: 기계 경로 → `report.md`는 상대 경로만. 원본 XML·JSON에는 절대 경로가 있지만 `out/` 안에만 있고 커밋되지 않는다(Assumption 13).

## 5. Acceptance Criteria
| ID | Criterion | Verified by |
|---|---|---|
| AC-1 | `ctest --preset <p> -N -L scenario`가 `scenario.TracedStateMachine.EventsReachStreamInOrder`와 `scenario.LoggedErrorFlow.ErrorFromTwoThreadsReachesFile` 둘만 보여 주고, `-L scenario` 실행이 둘 다 통과한다. `windows-x64-debug`, `linux-x64-debug` | `build.py --preset <p> --label scenario`, `ctest -N` 출력을 `testrecord.md`에 |
| AC-2 | `tests/`가 등록한 CTest 테스트는 모두 `unit`, `scenario`, `probe` 중 정확히 하나를 label로 갖는다. `-L unit`은 `AllTests`와 단계 도우미 자기 시험 셋(`ScenarioStep*`, History 2026-11-04 DEV). 레슨 테스트의 label은 바뀌지 않는다 | `ctest --show-only=json-v1` 출력을 읽는 짧은 확인(명령과 결과를 `testrecord.md`에), 두 preset |
| AC-3 | 도우미: (a) 단계 안의 실패 메시지에 `step n: <name>`이 있다. (b) 단계 k의 fatal 실패 뒤 k+1부터는 실행되지 않고 `[skip n] <name>`이 출력된다. (c) non-fatal 실패 뒤에는 다음 단계가 실행된다. (d) `step`이 성공 여부를 돌려준다. (e) `workDir()`는 시작할 때 비어 있다 | (a), (d), (e): `atugcc_tests`의 `ScenarioStepTest`(gtest-spi). (b), (c)와 첫 단계 전의 fatal 실패: 일부러 실패하는 `ScenarioStepSelfRun.DISABLED_*`를 CTest `ScenarioStepFatalStops`, `ScenarioStepNonFatalContinues`, `ScenarioStepFatalBefore`가 따로 실행하고 출력을 정규식으로 확인 (History 2026-11-04 DEV) |
| AC-4 | 시나리오는 서로 독립이다: 각자 따로(`-R`), 함께 차례로, 함께 나란히(`-j 4`), 순서를 바꿔(`--schedule-random`) 돌려도 통과한다. 두 번 연이어 돌려도 통과한다(앞 실행의 `workDir()` 잔여물에 영향 없음) | `linux-x64-debug`에서 네 가지 명령, `testrecord.md` |
| AC-5 | S1이 §2.2의 네 단계를 실행하고, 4단계의 확인(전이 순서, `seq` 증가, span 수, diagram parts)이 모두 이뤄진다. 상태 머신의 전이 순서를 일부러 바꾸면 4단계에서 `step 4`가 붙은 메시지로 실패한다 | 시나리오 통과 + 일부러 깨뜨린 사본으로 한 번 실행(되돌림), 출력을 `testrecord.md`에 |
| AC-6 | S2가 §2.2의 네 단계를 실행하고, 파일의 두 줄에 `FileIOFailure`와 시나리오 파일의 호출 위치가 있다. 1단계의 `configureLogBuffers`가 성공한다(이 프로세스에서 처음) | 시나리오 통과, `--verbose` 출력의 단계 줄 |
| AC-7 | `linux-x64-tsan`과 `linux-x64-asan`에서 `--label scenario`가 통과하고, TSan의 테스트 명령에 `setarch` launcher와 `TSAN_OPTIONS`가 붙는다 | `build.py --preset linux-x64-tsan --label scenario`(`ctest --verbose`로 명령 확인), asan 동일 |
| AC-8 | `build.py --label`: `--dry-run`에 `ctest --preset <p> -L <L> --no-tests=error`가 보인다. `--test`와 함께면 전체 ctest 단계가 없다. 없는 label은 0이 아닌 코드로 끝난다. `%`, `"`, 줄바꿈은 exit 2. Linux preset을 Windows에서 부르면 WSL 쪽에 `--label`이 전달된다. Windows 배치에서 `^scenario$`가 그대로 ctest에 닿는다 | `py -3 .agent/scripts/test_agent_scripts.py`의 새 시험 + `--label nosuchlabel` 수동 실행 |
| AC-9 | 기존 동작 유지: `build.py --test`가 두 preset에서 통과하고 시나리오도 포함한다. `--gtest-filter`는 이전처럼 `AllTests`만 돈다 | `build.py --preset <p> --test`, `--gtest-filter "Tracer*"` |
| AC-10 | 문서 게이트와 이름 게이트 통과 | `py -3 .agent/scripts/lint_docs.py`, `py -3 .agent/scripts/naming_check.py` exit 0 |
| AC-11 | `build.py --preset <p> --test --report`가 두 preset에서 §2.1의 폴더 구조를 만들고, `report.md`의 숫자가 ctest의 요약 줄(전체·실패 수)과 같으며, `AllTests`의 gtest 케이스 수가 `atugcc_tests --gtest_list_tests`의 수와 같다. label별 표에 `unit`, `scenario`, `probe`, `lesson`이 나온다. `report.md`에 절대 경로가 없다 | 실제 실행 두 번, 숫자 대조와 `report.md` 발췌를 `testrecord.md`에 |
| AC-12 | 실패한 실행에도 리포트가 남는다: AC-5의 일부러 깨뜨린 S1으로 `--label scenario --report`를 돌리면 종료 코드가 0이 아니고, `report.md`의 실패 목록에 `scenario.TracedStateMachine.EventsReachStreamInOrder`와 `step 4`가 든 메시지가 있다. 빌드가 실패하면 리포트를 쓰지 않는다는 줄이 나온다 | 실제 실행(되돌림) + `test_agent_scripts.py`의 시험(빌드 실패 단계를 흉내) |
| AC-14 | `tests/README.md`만 보고 따라 할 수 있다: 문서의 명령을 그대로 실행하면(두 preset 중 하나) 문서가 말한 결과가 나오고, 문서의 `report.md` 표본이 실제로 만든 것과 같은 구조다. 시나리오 추가 순서대로 빈 시나리오 하나를 더하면 `-L scenario`에 나타난다(확인 후 되돌림) | 리드가 문서를 처음부터 따라 한 기록을 `testrecord.md`에 |
| AC-13 | `test_report.py`: 준비된 JUnit·gtest JSON·`tests.json` 표본(통과, gtest 케이스 실패, crash로 JSON 없음, 깨진 JSON)에서 `report.md`가 §2.1의 다섯 부분을 정확히 쓴다. `--report`에 ctest 단계가 없거나 절대 경로면 exit 2. `--dry-run`에 `--output-junit`과 `GTEST_OUTPUT`이 보이고 폴더가 생기지 않는다. Windows→WSL에서 같은 상대 `DIR`이 전달된다 | `py -3 .agent/scripts/test_agent_scripts.py`의 새 시험 |

## 6. Out of Scope
- 기존 단위 테스트를 시나리오로 옮기기 — 그 모듈을 다음에 고치는 작업 (Assumption 11)
- `atugcc_tests`를 테스트별 CTest 항목으로 쪼개기 — 필요해지면 새 작업 (Assumption 2)
- 프로세스를 죽이거나 다시 띄우는 시나리오 — probe 테스트가 맡는다 (Assumption 1)
- 레슨의 smoke test를 시나리오로 바꾸기 — 레슨은 `lesson.<id>`로 남는다. 레슨이 시나리오를 쓰고 싶어지면 그 레슨 작업이 정한다
- 테스트 작성(단위·시나리오)과 리포트 읽기를 실습하는 레슨 — 070-15 (사용자 요청 2026-11-04). 레슨에서 GoogleTest를 쓰려면 레슨 빌드(플레이그라운드 preset은 tests를 끔)에 gtest를 공급하는 결정이 따로 필요하다
- 패턴별 시나리오 — 각 패턴 작업(021–024)이 더한다 (Assumption 10)
- CI에서 label별로 나눠 돌리기, 리포트를 CI 산출물로 올리기 — KI-024 (CI 도입, 사용자 결정)
- HTML 리포트, 여러 실행에 걸친 추이(시간 변화) 비교, 오래된 리포트 폴더 자동 정리 — 필요해지면 새 작업
- build.py를 거치지 않고 `ctest`나 실행 파일을 직접 돌릴 때의 리포트 — 직접 `--output-junit`/`--gtest_output`을 줄 수 있고, `test_report.py <DIR>`로 요약할 수 있다(test.md에 방법만 적음)

## 7. Dependencies & Backends
GoogleTest 1.14(이미 FetchContent), CMake `GoogleTest` 모듈(`gtest_discover_tests`, `TEST_LAUNCHER`는 3.29+; 프로젝트 최소 4.0). 새 외부 의존 없음.

## 8. Documentation Updates
| Document | Section | Change |
|---|---|---|
| [test.md](/.agent/rules/test.md) | §2 | 테스트 종류 셋(unit / scenario / probe)과 고르는 기준(Assumption 1), `tests/scenario/` 위치와 파일 이름(`scenario_<flow>.cpp`), 단계 도우미 사용법과 스레드 주의, 직접 실행은 지원하지 않음, 실행(`--label scenario`, `ctest -L`), 패턴·엔진 작업은 시나리오를 하나 이상 더함(Assumption 10) |
| `tests/README.md` | 새 문서 (사용자 요청 2026-11-04) | 사람이 직접 테스트를 돌리고 결과를 읽는 안내: 테스트 종류 셋과 각자 어디에 있는지, 종류별로 골라 돌리기(`--test`, `--label unit/scenario/probe`, `--gtest-filter`, 같은 일을 `ctest`로), 시나리오 하나 더하는 순서(파일, CMake 목록 한 줄, 단계 도우미 예), `--report` 사용법(기본 폴더와 `DIR`, 폴더 안 파일마다 무엇이 들었는지, `report.md`의 다섯 부분을 실제 표본으로 읽는 법, 실패했을 때 어디부터 보는지: 실패 목록 → gtest JSON의 메시지 → JUnit 출력 → 시나리오의 `workDir()`), build.py 없이 돌린 결과를 `test_report.py <DIR>`로 요약하기, 자주 생기는 일(오타 난 label, TSan launcher, 시나리오 실행 파일을 직접 돌리면 생기는 일). README.md의 `tests/` 줄과 test.md가 이 문서를 가리킨다 |
| [test.md](/.agent/rules/test.md) | §6 | 리포트: 증거로 쓰는 실행은 `--report`, testrecord에는 명령과 `report.md` 요약을 옮겨 적음(Assumption 14). build.py 없이 돌린 결과를 `test_report.py <DIR>`로 요약하는 방법 |
| [config.md](/.agent/rules/config.md) | §1 | 명령 줄에 `--label <L>`, `--report [DIR]`, 설명 두 항목(리포트 폴더 구조 한 줄) |
| [build.py](/.agent/scripts/build.py) | 모듈 docstring, `--help` | `--label`, `--report` |
| `.agent/scripts/test_report.py` | 새 파일 docstring | 입력 파일, `report.md`의 다섯 부분, 혼자 실행 방법 |
| [agent_start_prompt.md](/docs/agent_start_prompt.md) | Quick reference | Build / test 줄에 `--label scenario`, `--report` 예 |
| [00_template.md](/docs/specs/00_template.md) | §12 | "시나리오를 더하는 작업: `build.py --preset <p> --label scenario`" 한 줄 |
| [agent_todo.md](/docs/agent_todo.md) | 040-02 줄, 작업 공통 원칙 | 스펙 링크와 상태. 공통 원칙에 "패턴·엔진 작업은 단위 테스트에 더해 시나리오를 하나 이상" |
| [README.md](/README.md) | 구조 트리(`tests/`), 빌드·테스트 예 | `tests/`의 설명(단위·시나리오·probe), `--label scenario`와 `--report` 예 한 줄씩, `ctest -L unit` / `-L scenario` / `-L probe`, 리포트 위치 `out/test-reports/` |
| [tests/CMakeLists.txt](/tests/CMakeLists.txt) | 시나리오 블록 주석 | 왜 별도 실행 파일·프로세스별인지 (spec 040-02) |

## 9. Technical Constraints
- Compiler: MSVC (VS 2026) / Clang 20 with libstdc++ 14 (Linux)
- CMake: 4.0+ (C++20 modules always on)
- C++ Standard: C++23 (C++20 minimum)

## 10. Context & References
- [tests/CMakeLists.txt](/tests/CMakeLists.txt) (`AllTests`, probe 테스트들, `TSAN_OPTIONS`), [CMakeLists.txt](/CMakeLists.txt) (`ATUGCC_TEST_LAUNCHER`), [lessons/CMakeLists.txt](/lessons/CMakeLists.txt) (`lesson.<id>`, label `lesson`/`long`)
- [build.py](/.agent/scripts/build.py), [test_agent_scripts.py](/.agent/scripts/test_agent_scripts.py), spec [090-06](/docs/specs/090_06_dev_tools_cleanup.md) (`--gtest-filter`를 ctest로, Windows 배치 인용)
- [test_event_stream.cpp](/tests/pattern/test_event_stream.cpp) (`environmentEventSink()`는 프로세스에 한 번), [log_buffer_config.hpp](/include/atugcc/core/log_buffer_config.hpp)
- spec [090-05](/docs/specs/090_05_backlog_sync.md) D6

## 11. Implementation Plan
- [ ] Step 1: `tests/scenario/scenario.hpp` 도우미와 `atugcc_tests`의 `ScenarioStepTest` (AC-3)
- [ ] Step 2: `tests/CMakeLists.txt`: `atugcc_scenarios`, `gtest_discover_tests`, launcher·환경, 기존 테스트 label (AC-2)
- [ ] Step 3: 시나리오 S1 `tests/scenario/scenario_traced_state_machine.cpp` (AC-5)
- [ ] Step 4: 시나리오 S2 `tests/scenario/scenario_logged_error_flow.cpp` (AC-6)
- [ ] Step 5: `build.py --label`과 시험 (AC-8)
- [ ] Step 6: `.agent/scripts/test_report.py`와 표본 기반 시험 (AC-13)
- [ ] Step 7: `build.py --report`(단계 인자·환경, WSL 전달, 실패 뒤 요약)와 시험 (AC-12, AC-13)
- [ ] Step 8: §8 문서

## 12. Verification Plan
- [ ] Build, zero warnings: `build.py --preset windows-x64-debug`, `build.py --preset linux-x64-debug`
- [ ] Full suite: `build.py --preset <p> --test` on both presets (AC-9)
- [ ] 시나리오: `build.py --preset <p> --label scenario` on both presets, tsan, asan (AC-1, AC-7)
- [ ] 독립성 명령 네 가지 (AC-4), label 확인 (AC-2)
- [ ] `py -3 .agent/scripts/test_agent_scripts.py` (AC-8, AC-13), 문서·이름 게이트 (AC-10)
- [ ] 리포트: `--test --report` 두 preset (AC-11), 깨뜨린 S1으로 `--label scenario --report` (AC-12)
- [ ] Every AC row has its evidence in `testrecord.md` (증거 실행은 `--report`로, Assumption 14)

## History / Amendments
- 2026-11-04: 초안 (SPEC_DRAFT)
- 2026-11-04: 테스트 리포트 `build.py --report` 추가(사용자 요청): Assumption 12–15, §2.1·§2.2 리포트, §4 리포트 항목, AC-11–AC-13, §6·§8·§11·§12. 사용 안내 `tests/README.md`(§8), 레슨은 070-15로 분리
- 2026-11-04: 사용자 승인 (APPROVED), DEV
- 2026-11-04 (DEV): AC-3 (b), (c)의 검증 방법 변경. gtest-spi의 `EXPECT_*_FAILURE` 안에서는 실패가 가짜 reporter로 가서 `HasFatalFailure()`/`HasFailure()`가 보지 못하므로, 같은 프로세스에서는 (b)를 시험할 수 없고 (c)는 항상 통과한다(계획 중 발견, cpp-reviewer 지적). 일부러 실패하는 `DISABLED_` 테스트 셋을 CTest가 따로 실행하고 출력을 정규식으로 확인한다. 이 셋은 label `unit`이므로 AC-2의 `-L unit`은 `AllTests`와 이 셋이다. 리포트의 gtest 집계에 계획된 실패가 섞이지 않게 이 셋은 `GTEST_OUTPUT`을 지운다
- 2026-11-04 (DEV): 리포트 세부. (1) 컴파일러는 `CMakeCache.txt`가 아니라 configure가 쓰는 `CMakeFiles/<CMake 버전>/CMakeCXXCompiler.cmake`에서 읽는다(캐시 항목이 아님). (2) `--report DIR` 안전: DIR은 실행 전에 비우므로, 저장소 안(저장소 자체, `..`로 밖, `.git` 안 제외)의 폴더이고, 있으면 비어 있거나 이전 리포트(`run.json`)여야 하며, 링크가 아니어야 한다. `%`, `"`, 줄바꿈은 거부(배치 줄에 들어감). (3) `report.md`의 GoogleTest 표는 gtest 파일(프로그램)마다 한 줄과 **All** 줄(AC-11의 `AllTests` 케이스 수를 바로 읽도록). (4) 저장소 밖 절대 경로는 `<abs>/<파일 이름>`으로 줄인다(§2.1 5번). 리뷰(cpp-reviewer) 지적 반영
