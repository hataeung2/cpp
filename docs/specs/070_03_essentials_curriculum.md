---
id: 070-03
title: essentials 트랙 커리큘럼 (1차 레슨 4개, 기존 레슨·유닛 영어판)
depends_on: [010-08, 010-09, 010-10, 070-10]
unblocks: [070-11, 070-12]
approved: 2026-11-03
---

# Spec 070-03: essentials 트랙 커리큘럼 (1차 레슨 4개, 기존 레슨·유닛 영어판)

## 0. Assumptions (please review)
| # | Decision | Rejected alternative | Why |
|---|---|---|---|
| 1 | **범위**: 이 작업은 (a) essentials 트랙의 전체 순서(후보 E1–E14 모두)를 정하고, (b) 그중 **새 레슨 4개**(E2 포맷팅, E4 오류 처리, E7 호출 위치, E13 로그 복구)를 만들고, (c) 기존 레슨 4개와 유닛 2개를 한/영 전환되게 고친다(README 영어판, 영어 출력). 나머지 후보 7개는 새 작업 두 개로 나눈다: **070-11**(문법: E1, E5, E6, E14), **070-12**(시간·파일·동시성: E8, E9, E12) | 후보 14개를 이 작업에서 모두, 또는 기존 레슨 번역만 | 14개를 한 브랜치에 넣으면 리뷰 단위가 너무 크다. 1차 묶음은 트랙 제목의 "core, 스레드·로그 관리"에 가장 가깝고, 이미 있는 라이브러리 기능(`core/error.hpp`, `Logger`의 `FormatWithLocation`, 010-10 복구)을 바로 가르친다. 번역은 070-10 Assumption 13에 따라 레슨 작업이 맡는다 |
| 2 | **트랙 순서**(§2.1): 문법(람다 → 포맷 → `const` → 오류 → 호출 위치 → concepts → ranges → variant) → core 기능(시간, 파일) → 스레드·로그(작업 스레드 → 로그 복구 → lock-free 버퍼 → 구간 시간). 뒤 레슨이 앞 레슨의 문법을 쓴다(Logger 레슨은 `std::format`과 `source_location`을 안다고 본다) | core 기능(Logger)을 맨 앞에 | 메모리의 방향 "core, 문법, 기능" 중 Logger·스레드는 문법을 전제로 한다. 먼저 쓰는 것을 먼저 배운다 |
| 3 | **폴더 번호는 최종 순서 번호**다(`01_`–`14_`). 아직 없는 레슨의 번호는 비워 두고, 070-11·070-12가 그 번호로 폴더를 만든다. 그래서 기존 폴더 둘만 한 번 옮긴다: `02_thread_and_log` → `11_thread_and_log`, `03_span_timing` → `14_span_timing`. 레슨 id는 그대로다 | 옮기지 않고 새 레슨을 `04_`부터 뒤에 붙이기, `track.toml`에 순서 목록 키 추가 | 트리 순서는 폴더 접두사로 정해진다(070-01). 뒤에 붙이면 포맷 레슨이 Logger 레슨보다 뒤에 온다. 번호를 미리 정해 두면 이후 레슨은 아무것도 옮기지 않는다. 순서 키는 070-01 형식을 바꾸는 일이라 이 작업에 비해 크다 |
| 4 | 폴더를 옮기면 **완료된 스펙 두 개**(010-08, 010-09)의 §8 표 링크가 깨진다(`lint_docs.py` ERROR). 링크 경로만 고치고 각 스펙의 History에 한 줄 남긴다. 내용은 고치지 않는다. 봉인된 작업 산출물 폴더(`feature_*`)의 경로 문구는 링크가 아니라 고치지 않는다 | 서브 스펙(`NNN_SS_PP`)을 만들기 | spec.md §4의 서브 스펙은 요구사항을 다시 열 때다. 경로 이동은 요구사항 변경이 아니다 |
| 5 | **E2 `format_text`**: `std::format`(위치 인자, 폭·채움·정렬, 진법·정밀도), 사용자 타입의 `std::formatter` 특수화, `std::format_to`, 컴파일 시간 형식 검사(`std::format_string`)와 실행 시간 형식(`std::vformat`)을 출력으로 비교한다. `std::print`(C++23)는 **README에만** 쓴다: 플레이그라운드의 GCC 13.3에 `<print>`가 없다(2026-11-03 확인) | `std::print`를 레슨 코드에 쓰기 | 레슨은 두 preset 모두에서 빌드돼야 한다(lessons/README.md). GCC 14로 올라가면 연습 과제로 바꾼다 |
| 6 | **E4 `error_expected`**: 설정 줄(`port=8080`)을 읽는 같은 함수를 예외 방식과 `core::Expected` 방식으로 둘 다 쓰고, 좋은 입력과 나쁜 입력을 출력으로 비교한다. C++23 `and_then`, `transform`, `or_else`로 단계를 잇는다. 라이브러리 `atugcc/core/error.hpp`를 `uses`로 보여 준다 | 새 오류 타입 만들기 | 라이브러리 전체가 `core::Expected`/`Result`를 쓴다. 레슨이 같은 타입을 써야 다른 레슨과 라이브러리 코드를 바로 읽는다 |
| 7 | **E7 `source_location`**: `__FILE__`·`__LINE__` 매크로, `std::source_location` 기본 인자, 가변 인자에서 기본 인자가 안 되는 문제와 `FormatWithLocation` 해법을 단계별로 보여 주고, 마지막에 `Logger::log`가 같은 방법으로 호출 줄을 기록하는 것을 보인다. 레슨이 직접 찍는 줄의 파일 이름은 경로 없이 이름만 쓴다(5단계의 Logger 줄은 Logger가 전체 경로를 찍는다) | 매크로만 비교 | 이 라이브러리가 실제로 쓰는 해법(`logger.hpp`)까지 가야 Logger 레슨으로 이어진다. 전체 경로는 기계마다 달라 출력이 길고 비교하기 어렵다 |
| 8 | **E13 `log_recovery`**: **두 번 실행하는 레슨**이다. 실행할 때마다 (1) `configureLogBuffers({.drainInterval = 1000ms, .mappedDir = "log/map"})`로 **이전 실행**의 `.logmap`을 복구하고 복구 파일의 줄을 보여 준 뒤 그 파일을 지우고, (2) 줄 몇 개를 쓰고 (3) `std::_Exit(0)`으로 종료 처리기, 소멸자, flush 없이 끝난다. 그래서 화면에 못 나온 줄이 다음 실행의 처음에 나온다. 첫 실행은 "복구할 것 없음"이다. crash dump(`std::abort`, `tools/read_dump.py`)는 연습 과제로만 둔다 | 자기 자신을 자식 프로세스로 띄워 죽이기(`std::system`), 실제 `abort` | 한 프로세스, 이식 가능한 표준 함수만 쓴다. 종료 코드가 0이라 smoke test와 웹 실행이 그대로 통과한다. `abort`는 종료 코드가 0이 아니라 smoke test가 실패한다. 매핑 파일의 내용은 프로세스가 어떻게 끝나든 OS가 남기므로(010-10) 처리기를 하나도 돌리지 않는 `_Exit`과 SIGKILL은 복구 쪽에서 같다. `std::quick_exit`은 쓰지 않는다: Logger에게는 정상 종료라 마지막 drain 뒤 매핑 파일을 지운다(010-10 Assumption 9, `logger.hpp` 계약). `_Exit`은 Logger 계약의 "not covered"(보장 없음)이지만 레슨이 보여 주려는 것이 바로 보장 없이 끝난 실행이다(2026-11-03 두 OS에서 확인: 다음 실행이 flush하지 않은 줄을 `[undelivered]`로 복구) |
| 9 | 새 레슨은 **유닛을 만들지 않는다**. 각 레슨의 코드는 `main.cpp` 하나이고, 라이브러리 헤더를 `uses`로 보인다 | 레슨마다 유닛 | 유닛은 여러 레슨이 같이 쓸 때 만든다(070-01). 이 네 레슨의 코드는 다른 레슨이 가져다 쓸 것이 아니다 |
| 10 | **README 영어판**: 기존 레슨 4개, 유닛 2개, 새 레슨 4개 모두 `README.en.md`를 둔다. 한국어판과 절, 연습 과제, 코드 블록이 같다. 영어판 안의 링크는 영어판이 있는 README면 `README.en.md`를, 없으면(`lessons/README.md`, 스펙) 그대로 둔다. `intro.en.md`의 레슨 링크도 영어판으로 바꾼다 | 기계 번역 그대로, 링크는 한국어판 그대로 | 영어 화면에서 링크를 따라가도 영어로 이어져야 한다. `lessons/README.md`(레슨 작성 안내)와 스펙은 기여자 문서라 이 작업 밖이다 |
| 11 | 번역하다가 한국어판의 틀린 내용을 찾으면 **두 판을 같이 고친다**. 이미 찾은 것: 유닛 `jthread_worker` README의 사용 예시 주석 "Logger는 이 워커 스레드 전용이어야 하며 …"가 010-08의 계약(여러 스레드가 함께 써도 안전)과 어긋난다 | 영어판만 맞게 쓰기 | 두 판이 다르면 언어를 바꿀 때 다른 것을 배운다 |
| 12 | **프로그램 출력은 영어**(070-10 Assumption 14): `thread_and_log`, `device_state_machine`의 한국어 로그 문구를 영어로 바꾼다. 다른 레슨과 유닛은 이미 영어다. **레슨·유닛 코드 주석은 한국어와 영어를 둘 다 둔다**(사용자 결정 2026-11-03): 주석마다 한국어 줄 바로 아래에 같은 뜻의 영어 줄을 둔다(`// 한국어` 다음 줄 `// English`). 여러 줄 주석은 한국어 문단 바로 다음에 영어 문단을 둬도 된다. `[학습]` 표시는 영어 쪽에서 `[Learn]`. 기존 레슨 4개(`lessons/tracks/*/*/main.cpp`)와 유닛 2개(`lessons/units/*/*.hpp`)의 주석도 이 작업에서 영어 줄을 더한다. 라이브러리(`include/`, `src/`, 이미 영어)와 `lessons/support/`(레슨 코드가 아니라 빌드 지원 코드, 090-06)의 주석은 바꾸지 않는다 | 주석은 한국어만(070-10의 원래 규칙), 주석을 영어로만 | 영어 화면을 쓰는 사람도 에디터에서 같은 소스를 본다. 코드는 언어 전환이 안 되므로 두 언어를 함께 둔다. 같은 줄에 섞지 않고 줄을 나눠야 각 언어로 읽기 쉽다. 070-10 Assumption 14의 "코드 주석은 번역하지 않는다"를 레슨·유닛 코드에 한해 대체한다 |
| 13 | `lessons.py check`에 **경고 두 개**를 더한다: (a) 레슨·유닛 폴더에 `README.en.md`가 없음, (b) 레슨 `sources`와 유닛 `files`에서 **문자열 리터럴 안에 한글**이 있음(주석은 보지 않는다. `"…"`, 이스케이프, 문자 리터럴 `'…'`, raw string `R"d(…)d"`를 구분). 둘 다 WARN이다 | 검사 없음, 실행 출력 검사(CTest `FAIL_REGULAR_EXPRESSION`) | 이 작업이 끝나면 모든 레슨에 영어판이 있으므로 070-10 Assumption 13의 "경고하지 않음"을 바꿀 때다. 출력 문구는 거의 모두 문자열 리터럴이라 빌드 없이 잡힌다. CMake 정규식은 바이트 단위라 한글 범위를 안정적으로 쓰기 어렵다 |
| 14 | 태그 어휘에 새 태그 4개를 더한다: `format`, `error`, `source_location`, `recovery`(별칭은 §2.4). 모든 새 레슨에 기존 태그도 붙인다(`log_recovery`에 `log`) | 태그 없이 | 070-10의 기능 검색이 "expected", "`__LINE__`", "복구"로 새 레슨을 찾게 한다 |
| 15 | 오래 남길 해설: E2의 비교는 새 `docs/cpp_evolution/format.md`(영어, 기존 페이지와 같은 형식)에 쓴다. E4, E7은 이미 있는 [`error_expected.md`](/docs/cpp_evolution/error_expected.md), [`source_location.md`](/docs/cpp_evolution/source_location.md)에 레슨 링크만 더한다. E13은 [`lock_free_logging.md`](/docs/cpp_evolution/lock_free_logging.md)에 레슨 링크를 더한다. KI-001의 `filesystem_format.md`는 format 부분을 이 작업이, filesystem 부분을 070-12가 맡는다고 고친다 | 레슨 README에만 | lesson_candidates.md 머리말의 규칙이다 |
| 16 | 070-11, 070-12의 **진행 순서 자리**는 이 스펙이 정하지 않는다. `agent_todo.md`에 BACKLOG로만 더하고, "진행 순서"에는 넣지 않는다 | B의 레슨 줄 앞에 넣기 | 순서를 바꾸는 것은 사용자 결정이다(agent_todo.md 진행 순서 머리말) |

**결정** (2026-11-03): 코드 주석은 한국어와 영어 둘 다(Assumption 12), 프로그램 출력은 영어.

## 1. Objective
essentials 트랙을 "레슨 3개 시드"에서 **순서가 정해진 커리큘럼**으로 만든다. 레슨이 어떤 순서로 무엇을 가르치는지 정하고, 그 순서의 첫 묶음(포맷팅, 오류 처리, 호출 위치, 로그 복구)을 만든다. 동시에 지금 있는 레슨과 유닛을 070-10의 한/영 전환에 맞춘다: 영어 화면에서 README가 영어로 나오고, 프로그램 출력은 언제나 영어다.

## 2. Requirement Details

### 2.1 트랙 순서
| 폴더 | 레슨 id | 후보 | 상태 |
|---|---|---|---|
| `01_lambda_capture` | `lambda_capture` | E10 | 있음 (번역) |
| `02_format_text` | `format_text` | E2 | **새로** |
| `03_` | (070-11) | E14 `const`의 위치 | 비움 |
| `04_error_expected` | `error_expected` | E4 | **새로** |
| `05_source_location` | `source_location` | E7 | **새로** |
| `06_` – `08_` | (070-11) | E1 concepts, E5 ranges, E6 variant | 비움 |
| `09_`, `10_` | (070-12) | E8 chrono, E9 filesystem | 비움 |
| `11_thread_and_log` | `thread_and_log` | E3 | 있음 (`02_`에서 옮김, 번역, 영어 출력) |
| `12_log_recovery` | `log_recovery` | E13 | **새로** |
| `13_` | (070-12) | E12 lock-free 링 버퍼 | 비움 |
| `14_span_timing` | `span_timing` | E11 | 있음 (`03_`에서 옮김, 번역) |

`docs/tasks/lesson_candidates.md`의 essentials 표에 **폴더** 열을 더하고, 표를 이 순서로 다시 정렬한다. patterns 트랙(`02_patterns/01_device_state_machine`)은 옮기지 않고 번역과 영어 출력만 한다.

### 2.2 새 레슨
모두 `profile = "quick"`(10초 안), Windows(MSVC)와 Linux(GCC 13) preset에서 경고 없이 빌드, 출력은 영어, 플랫폼 전용 API 없음. README 두 판에 무엇을 보여 주는지, 예전 방식과 C++20/23 방식의 비교, 실행 방법, 볼 것, 연습 2–3개.

**`format_text`** (E2): `uses = ["lib:atugcc/core/logger.hpp"]`(Logger가 `std::format_string`을 받는 곳), `tags = ["format"]`
- 출력 단계: 위치 인자와 같은 인자 다시 쓰기(`{0} {1} {0}`) / 폭·채움·정렬로 표 한 개 / 정수 진법(`{:#x}`, `{:012b}`)과 부동소수 정밀도(`{:.3f}`, `{:e}`) / 사용자 타입 `Vec2`의 `std::formatter` 특수화(`{}`와 정밀도 `{:.1}` 둘 다) / `std::format_to(std::back_inserter(buf), …)`로 버퍼에 이어 쓰기 / 실행 시간에 받은 형식 문자열은 `std::vformat`, 잘못된 형식이면 `std::format_error`를 잡아 메시지 출력.
- 연습: 형식 문자열의 인자 수를 틀리게 바꿔 **컴파일 오류**를 읽기(`std::format_string`이 consteval로 검사), `Vec2` formatter에 다른 표시(`{:p}` 극좌표 등) 더하기.

**`error_expected`** (E4): `uses = ["lib:atugcc/core/error.hpp"]`, `tags = ["error"]`
- `parsePortThrowing(std::string_view)`(예외: `std::invalid_argument`, `std::out_of_range`)와 `parsePort(std::string_view) -> core::Expected<std::uint16_t>`(`std::from_chars`, 실패는 `CoreError::InvalidArgument`)를 같은 입력 4개(`8080`, `abc`, `70000`, 빈 문자열)로 돌려 결과를 나란히 출력한다.
- `valueOf("port=8080", "port")`로 키·값 나누기 → `parsePort` → 포트 범위 검사를 `and_then`/`transform`으로 잇고, 실패 시 `or_else`로 기본값을 고르는 경로를 보인다. 실패 이유는 `core::to_string(CoreError)`로 출력.
- 연습: 새 오류 종류가 필요하면 무엇을 바꿔야 하는지(`CoreError`는 라이브러리 공통) 생각해 보기, 예외 버전의 `try`를 지웠을 때 어떻게 되는지 보기.

**`source_location`** (E7): `uses = ["lib:atugcc/core/logger.hpp"]`, `tags = ["source_location", "log"]`
- 단계 1: 매크로 `LOG_HERE(msg)`가 `__FILE__`, `__LINE__`, `__func__`를 찍는다. 단계 2: `logHere(msg, std::source_location = current())` 함수가 같은 줄을 찍는다(기본 인자는 호출한 곳에서 계산). 단계 3: 가변 인자 버전에서 위치를 마지막 인자로 둘 수 없음을 주석과 README로 설명하고, 형식 문자열에 위치를 붙이는 작은 `FormatWithLocation`으로 해결한다. 단계 4: `Logger::log`(liveOutput = `std::cout`)가 같은 방식으로 이 파일의 줄 번호를 기록한다. 끝에 `logger.flush()`.
- 파일 이름은 `std::filesystem::path(loc.file_name()).filename()`으로 이름만 출력한다.
- 연습: 단계 2의 함수를 감싸는 도우미 함수를 하나 더 만들면 기록되는 줄이 어디가 되는지 보기(기본 인자를 도우미가 다시 받아야 하는 이유).

**`log_recovery`** (E13): `uses = ["lib:atugcc/core/logger.hpp", "lib:atugcc/core/log_buffer_config.hpp"]`, `tags = ["recovery", "log"]`
- 실행 순서(Assumption 8):
  1. `configureLogBuffers({.drainInterval = 1000ms, .mappedDir = "log/map"})`. 실패하면 이유를 출력하고 복구 부분을 건너뛴 채 계속한다(종료 코드 0).
  2. `log/map`의 `recovered_*.log`를 찾아 각 파일의 머리와 줄(최대 20줄)을 출력하고 파일을 지운다. 없으면 `nothing to recover (first run?)`.
  3. `Logger`(liveOutput = `std::cout`, `enableCrashDump = false`)로 줄 5개(`step 1` – `step 5`)를 쓴다. 앞의 몇 줄은 `logger.flush()`로 화면에 내보내고, 뒤의 줄은 flush하지 않는다.
  4. `std::cout`을 flush하고 `std::_Exit(0)`. drain 간격이 1초라 뒤의 줄은 화면에 나오지 않고 매핑 파일에만 남는다.
- 다음 실행의 2단계가 그 줄을 보여 준다. README가 "Run을 두 번 누르세요"로 시작한다.
- 연습: `_Exit` 대신 `std::quick_exit(0)`으로 바꿔 다음 실행에서 복구할 것이 없는 이유 보기(정상 종료), `std::abort()`와 `enableCrashDump = true`로 바꿔 crash dump를 만들고 `py -3 tools/read_dump.py`로 읽기(종료 코드가 0이 아니라 웹에서는 실패로 표시됨을 README에 적는다), `mappedDir`을 지우고 실행해 줄이 사라지는 것 보기.

### 2.3 기존 레슨과 유닛
| 대상 | 바꾸는 것 |
|---|---|
| 레슨 `lambda_capture` | `README.en.md` |
| 레슨 `thread_and_log` | 폴더 이동(`11_`), `README.en.md`, 로그 문구 영어로(`=== thread_and_log lesson start ===`, `[WorkerFast] tick {}` 등). README의 실행 경로 예시가 옛 폴더를 쓰지 않는지 확인 |
| 레슨 `span_timing` | 폴더 이동(`14_`), `README.en.md` (출력은 이미 영어) |
| 레슨 `device_state_machine` | `README.en.md`, 로그·출력 문구 영어로(`STANDBY transition failed`, `=== Terminal trace (formatTerminal) ===` 등) |
| `tests/console/check_console_cp.py` | Windows CTest `LessonConsoleCodePage`(090-06 AC-9)는 이 레슨의 한국어 제목 줄이 콘솔 화면에 깨지지 않고 보이는지로 UTF-8 전환을 확인했다. 출력이 영어가 되므로 기대 줄을 이 레슨의 다른 비ASCII 줄 `══ State Transitions ══`(Tracer 제목, U+2550, 실행 시간과 무관)로 바꾼다. UTF-8이 아닌 콘솔이면 이 줄도 깨지므로 검사의 목적은 그대로다 |
| 유닛 `lambda_capture` | `README.en.md` |
| 유닛 `jthread_worker` | `README.en.md`, 두 판의 사용 예시 주석을 010-08 계약에 맞게 고침(Assumption 11) |
| `lessons/intro.md`, `intro.en.md` | 옮긴 폴더의 링크, `intro.en.md`의 README 링크를 `README.en.md`로 |
| `lessons/README.md` | `span_timing` 링크 경로 두 곳, "기존 레슨의 한국어 출력은 070-03이 고칩니다" 문장 삭제, `README.en.md`가 이제 경고 대상임 |

### 2.4 태그 어휘 (`lessons/tags.toml`에 더함)
| 키 | ko | en | aliases |
|---|---|---|---|
| `format` | 포맷 | Formatting | `std::format`, `std::print`, `std::formatter`, `std::vformat`, `printf`, `fmt`, `포맷팅`, `문자열 포맷` |
| `error` | 오류 처리 | Error handling | `std::expected`, `std::unexpected`, `Expected`, `Result`, `CoreError`, `exception`, `예외`, `오류` |
| `source_location` | 호출 위치 | Source location | `std::source_location`, `__FILE__`, `__LINE__`, `__func__`, `FormatWithLocation`, `호출 위치 기록` |
| `recovery` | 로그 복구 | Log recovery | `crash dump`, `크래시 덤프`, `logmap`, `mappedDir`, `memory-mapped`, `메모리 매핑`, `SIGKILL`, `복구` |

070-10의 중복 별칭 경고(한 이름은 한 태그에만)를 지킨다.

### 2.5 `tools/lessons.py check`
| 조건 | 수준 | 메시지 위치 |
|---|---|---|
| 레슨 폴더 또는 유닛 폴더에 `README.md`는 있는데 `README.en.md`가 없음 | WARN | 매니페스트 |
| `sources`/`files`의 파일에서 한글 음절(U+AC00–U+D7A3)이나 한글 자모가 든 문자열 리터럴 | WARN | 파일, 줄 번호 |

리터럴 찾기(새 함수 `hangul_literals(text) -> list[int]`, 줄 번호 목록. 이름은 `lessons.py`의 Python 규칙을 따른다): `//` 주석과 `/* */` 주석을 건너뛰고, `"…"`(백슬래시 이스케이프), `'…'`, 접두사가 붙은 리터럴(`u8"…"`, `L"…"`), raw string `R"delim(…)delim"`을 읽는다. 전처리기 줄(`#include "…"`)의 경로도 리터럴로 본다(한글 경로는 어차피 쓰지 않는다). 문자열을 다 읽지 못하고 파일이 끝나면 그 줄부터 끝까지를 리터럴로 본다(경고가 빠지는 쪽보다 낫다).

### 2.6 Platform Specifics
- `log_recovery`: 매핑 파일은 010-10이 두 플랫폼에서 지원한다. `std::_Exit`은 MSVC와 glibc 모두에 있고, 두 플랫폼 모두 프로세스가 끝나도 매핑된 페이지를 파일에 남긴다(2026-11-03 시제품으로 확인). 웹(WSL/Linux)과 로컬 Windows에서 각각 세 번 실행해 확인한다(AC-3).
- 다른 새 레슨은 표준 라이브러리만 쓴다. `<print>`는 쓰지 않는다(Assumption 5).

## 3. C++ Standard Evolution
| Approach | Standard | Description |
|----------|----------|-------------|
| Legacy | C++11/17 | `printf`·`iostream` 조작자, 예외 또는 오류 코드 + 출력 인자, `__FILE__`/`__LINE__` 매크로, 로그는 `printf` 디버깅 |
| Modern | C++20 | `std::format`(컴파일 시간 형식 검사), `std::source_location`, 메모리 매핑 로그 버퍼(라이브러리 기능) |
| Latest | C++23 | `std::expected`와 `and_then`/`transform`/`or_else`, `std::print`(README에서만) |

Reference: 새 `docs/cpp_evolution/format.md`(§8), 기존 `error_expected.md`, `source_location.md`, `lock_free_logging.md`.

## 4. Edge Cases
- [x] Thread safety / memory ordering — `thread_and_log`, `device_state_machine`은 문구만 바뀐다. `log_recovery`는 스레드를 만들지 않는다(로그 소비자 스레드는 라이브러리 것). `_Exit`은 소비자 스레드를 그 자리에서 끝낸다. 소비자가 매핑 파일에 쓰는 도중이어도 복구는 버퍼를 검사하고 깨진 버퍼는 건너뛴다(`skippedBuffers`, 010-10)
- [x] Resource lifetime — `log_recovery`의 `Logger`는 소멸자가 불리지 않는다(의도). `_Exit`은 C++ 스트림을 flush하지 않으므로 그 전에 `std::cout.flush()`를 해야 앞의 출력이 남는다. `source_location`의 `file_name()`은 정적 문자열이라 수명 문제가 없다
- [x] Platform differences — §2.6. `std::from_chars`(정수)는 GCC 13과 MSVC 모두에 있다. `std::formatter` 특수화의 `parse`는 두 컴파일러 모두 `constexpr`로 쓴다
- [x] Template / concept — `std::formatter<Vec2>` 특수화는 `main.cpp` 안에서만 쓰므로 ODR 문제 없음. `FormatWithLocation`의 consteval 생성자는 레슨 안 사본이다(라이브러리 것을 바꾸지 않음)
- [x] ODR — 새 유닛 없음. 레슨마다 실행 파일 하나
- [x] Undefined behaviour — `parsePort`는 `from_chars`의 `ec`와 남은 글자를 모두 검사한다. 범위 밖 값은 `std::uint16_t`로 자르지 않고 오류로 낸다
- [x] `log_recovery`의 flush 직후 drain — `flush()`가 로그 스레드를 깨우므로, 그 drain이 뒤에 쓴 `step 3`–`step 5`를 가져가면 화면에 나가고 복구되지 않는다. 레슨은 flush 뒤 100 ms를 기다려 로그 스레드가 1초 대기로 돌아간 다음 쓰고 곧바로 끝낸다. 기다림은 동기화가 아니므로 몹시 바쁜 기계에서는 드물게 일부가 화면에 나갈 수 있고, README가 그렇게 적는다(U10 codex 리뷰)
- [x] `log_recovery`를 같은 폴더에서 동시에 두 번 실행 — 살아 있는 실행의 `.logmap`은 잠겨 있어 건너뛴다(010-10). 화면에는 "nothing to recover"가 나올 수 있다
- [x] `log_recovery`를 ctest가 여러 번 실행 — 복구 파일은 읽은 뒤 지우므로 쌓이지 않는다. 남는 것은 마지막 실행의 `.logmap` 하나다(`log/`는 `.gitignore`)
- [x] 복구 파일이 깨짐 — `recoverLogMaps`가 `.corrupt`로 이름을 바꾸고 결과에서 뺀다(010-10). 레슨은 그 사실을 출력하지 않아도 된다. `configureLogBuffers`가 `FileIOFailure`면 이유를 출력하고 계속한다
- [x] 웹 실행의 작업 폴더 — 웹은 레슨 폴더에서 실행한다(`runner.py`). `log/map`은 레슨 폴더 아래에 생기고 `.gitignore`의 `log/`에 걸린다
- [x] 레슨 폴더 이동 뒤의 브라우저 상태 — URL 해시와 저장 상태는 레슨 id를 쓰므로 그대로다. 에디터에 열린 옛 경로 탭은 다음 인덱스 새로 고침에서 사라진다(070-02 동작)
- [x] 한글 리터럴 검사의 오탐 — 주석 안의 한글, `[학습]` 주석은 대상이 아니다. 문자 리터럴 안의 `'`, 문자열 안의 `\"`, raw string 안의 `"`를 테스트 케이스로 둔다
- [x] 영어판 README의 링크 — `lint_docs.py`가 `lessons/` 아래 Markdown 링크를 검사한다(090-04). 영어판이 가리키는 영어판이 없으면 깨진 링크로 나온다

## 5. Acceptance Criteria
| ID | Criterion | Verified by |
|---|---|---|
| AC-1 | 트랙 트리가 §2.1 순서다: 인덱스의 essentials 레슨 순서가 `lambda_capture, format_text, error_expected, source_location, thread_and_log, log_recovery, span_timing`이다. 레슨 id는 바뀌지 않았다 | `py -3 tools/lessons.py index -` 출력, testrecord |
| AC-2 | 새 레슨 4개가 `windows-x64-debug`와 `linux-x64-debug`에서 경고 없이 빌드되고 smoke test가 통과한다. 각 레슨의 출력에 §2.2의 단계가 모두 나온다 | 빌드 로그, `ctest -L lesson`, 레슨별 출력 전문을 testrecord에 |
| AC-3 | `log_recovery`: 빈 `log/map`에서 첫 실행은 "nothing to recover"를 내고, 두 번째 실행은 첫 실행에서 화면에 나오지 않은 줄(`step` 뒤쪽)을 복구해 보여 준다. 세 번째 실행 뒤에도 `log/map`의 `recovered_*.log`는 0개다. 두 플랫폼 모두 | 두 OS에서 세 번 실행한 출력과 `ls log/map`, testrecord |
| AC-4 | 레슨 8개(기존 4, 새 4)와 유닛 2개 모두 `README.en.md`가 있다. 각 영어판은 한국어판과 절 제목 수, 연습 과제 수, 코드 블록 수가 같다. 영어판의 링크는 영어판이 있는 README면 영어판을 가리킨다 | 비교 스크립트 출력(testrecord), `cpp-reviewer` 번역 검토 한 번(내용 누락, 의미 차이) |
| AC-5 | 모든 레슨(트랙 2개 전부)의 stdout·stderr에 한글이 없다. 레슨 8개와 유닛 2개의 소스에서 한글이 든 주석 줄이 이어진 묶음마다 바로 다음 줄이 영어 주석이다(줄마다 짝 또는 문단마다 짝) | 두 preset에서 모든 레슨을 실행하고 출력에서 U+AC00–U+D7A3, U+1100–U+11FF, U+3130–U+318F를 찾는 스크립트, 주석 짝 검사 스크립트(한글 주석 줄 다음 줄이 한글 없는 주석인지), testrecord |
| AC-6 | `lessons.py check`의 §2.5 경고 둘: `README.en.md` 없음 WARN, 한글 리터럴 WARN(줄 번호). 주석 안 한글, 문자 리터럴 `'"'`, 이스케이프 `\"`, raw string, `u8` 접두사, 끝나지 않은 문자열 각각의 경우 | `tools/test_lessons.py` 새 케이스 |
| AC-7 | 저장소에서 `py -3 tools/lessons.py check`가 ERROR 0, WARN 0이다 | 명령 출력 |
| AC-8 | 웹 검색: `expected`, `__LINE__`, `포맷`, `복구`, `std::format`이 각각 새 레슨을 찾는다. 영어 화면에서 모든 레슨과 유닛의 README가 안내 줄 없이 영어판으로 나온다 | 브라우저 확인(헤드리스, 070-10과 같은 방식): 검색어 5개의 결과 스크린샷, 영어 화면에서 레슨 8개·유닛 2개의 README 패널에 안내 줄이 없는지 확인한 기록, 스크린샷 2장(새 레슨 하나, 기존 유닛 하나) |
| AC-9 | 전체 suite가 두 preset에서 통과한다(`PlaygroundServer`, 레슨 smoke, 기존 테스트). `npm run build`, `npm test`, `tools/test_lessons.py` 통과 | 명령 출력, testrecord |
| AC-10 | §8 문서가 갱신되고 `lint_docs.py`가 exit 0이다(옮긴 폴더의 링크, 영어판 링크 포함) | 명령 출력 |

## 6. Out of Scope
- 후보 E1, E5, E6, E14(문법) — 070-11. E8, E9, E12(시간·파일·lock-free) — 070-12
- `lessons/README.md`(레슨 작성 안내)와 `web/README.md`의 영어판 — 기여자 문서. 필요해지면 KI로 등록한다
- `std::print` 레슨 코드 — GCC 14 이상이 플레이그라운드에 들어오면. KI로 등록한다(이 작업의 walkthrough에서)
- patterns 트랙 순서와 샘플 이전 — 070-04

## 7. Dependencies & Backends
none. 새 의존성 없음. 레슨은 `atugcc_core`만 링크한다(기존).

## 8. Documentation Updates
| Document | Section | Change |
|---|---|---|
| `lessons/tracks/01_essentials/*/README.md`, `README.en.md` | 새 레슨 4개 | 새로 씀 |
| 기존 레슨 4개와 유닛 2개의 `README.en.md` | 전체 | 새로 씀 (§2.3) |
| [`lessons/units/jthread_worker/README.md`](/lessons/units/jthread_worker/README.md) | 3. 사용 예시 | 주석을 010-08 계약에 맞게(Assumption 11) |
| [`lessons/intro.md`](/lessons/intro.md), [`lessons/intro.en.md`](/lessons/intro.en.md) | 트랙 목록 | 옮긴 폴더 링크, 영어판 링크 |
| [`lessons/README.md`](/lessons/README.md) | 구조, 새 레슨 추가, 레슨 작성 안내, 성능 측정 레슨 작성 | 폴더 번호 규칙(최종 순서 번호, 빈 번호), `span_timing` 링크, `README.en.md`와 한글 리터럴 경고, 코드 주석은 한국어 줄 + 영어 줄(Assumption 12), 070-03 문장 삭제 |
| [`lessons/tags.toml`](/lessons/tags.toml) | — | 태그 4개 (§2.4) |
| [`docs/tasks/lesson_candidates.md`](/docs/tasks/lesson_candidates.md) | Essentials 표 | 폴더 열, 순서대로 정렬, E2·E4·E7·E13 `레슨 있음`, 남은 후보에 070-11/070-12 |
| `docs/cpp_evolution/format.md` | 새 페이지 | E2 비교(Legacy `printf`/iostream → `std::format` → `std::print`), 레슨 링크 |
| [`docs/cpp_evolution/error_expected.md`](/docs/cpp_evolution/error_expected.md), [`source_location.md`](/docs/cpp_evolution/source_location.md), [`lock_free_logging.md`](/docs/cpp_evolution/lock_free_logging.md) | 끝 | 레슨 링크 한 줄 |
| [`docs/known_issues.md`](/docs/known_issues.md) | KI-001 | `filesystem_format.md`: format은 070-03이 `format.md`로, filesystem은 070-12 |
| [`docs/specs/010_08_logger_cleanup.md`](/docs/specs/010_08_logger_cleanup.md), [`010_09_logger_thread_buffers.md`](/docs/specs/010_09_logger_thread_buffers.md) | §8 링크, History | 옮긴 폴더 경로(Assumption 4) |
| [`docs/specs/090_06_dev_tools_cleanup.md`](/docs/specs/090_06_dev_tools_cleanup.md) | History / Amendments | "070-03이 AC-9의 기대 줄을 `══ State Transitions ══`로 바꿈(레슨 출력이 영어가 됨)" |
| [`docs/specs/070_10_lesson_search_i18n.md`](/docs/specs/070_10_lesson_search_i18n.md) | History / Amendments | "070-03이 `README.en.md` 없음을 WARN으로 바꿈(Assumption 13의 '경고하지 않음' 대체), 레슨·유닛 코드 주석은 한/영 둘 다(Assumption 14의 '코드 주석은 번역하지 않는다'를 레슨·유닛 코드에 한해 대체)" |
| [`docs/tasks/agent_todo.md`](/docs/tasks/agent_todo.md) | Phase 7, 진행 순서 | 070-03 줄, 새 070-11·070-12 BACKLOG 줄, 진행 순서 4번 |

## 9. Technical Constraints
- Compiler: MSVC (VS 2026) / GCC 13.3 (플레이그라운드와 `linux-x64-*` preset)
- C++ Standard: C++23 (레슨이 쓰는 C++23: `std::expected` 모나드 연산, `std::move_only_function`)
- Python 3.11+ (`tools/lessons.py`)

## 10. Context & References
- [레슨 후보 목록](/docs/tasks/lesson_candidates.md), [lessons/README.md](/lessons/README.md), [tags.toml](/lessons/tags.toml)
- [070-01 스펙](/docs/specs/070_01_lesson_structure.md)(구조), [070-10 스펙](/docs/specs/070_10_lesson_search_i18n.md)(영어 필드, Assumption 13·14)
- [logger.hpp](/include/atugcc/core/logger.hpp)(`FormatWithLocation`), [log_buffer_config.hpp](/include/atugcc/core/log_buffer_config.hpp)(`configureLogBuffers`, `recoverLogMaps`), [error.hpp](/include/atugcc/core/error.hpp)
- [010-10 스펙](/docs/specs/010_10_logger_mapped_buffers.md), [log_map_probe.cpp](/tests/core/log_map_probe.cpp)(`quickexit` 경우)
- [lessons.py](/tools/lessons.py), [test_lessons.py](/tools/test_lessons.py)

## 11. Implementation Plan
- [ ] Step 1: `lessons.py` 경고 두 개와 `test_lessons.py` 케이스(AC-6)
- [ ] Step 2: 폴더 이동(`git mv`), 링크 고치기(intro 두 개, `lessons/README.md`, 스펙 두 개), `lint_docs.py` 통과
- [ ] Step 3: 기존 레슨 출력 영어로(`thread_and_log`, `device_state_machine`), 기존 레슨 4개·유닛 2개 주석에 영어 줄 더하기
- [ ] Step 4: `tags.toml` 태그 4개
- [ ] Step 5: 새 레슨 4개(코드, 매니페스트), 레슨마다 두 preset 빌드와 실행
- [ ] Step 6: README 두 판(새 레슨 4) + 영어판(기존 4, 유닛 2), `jthread_worker` 예시 고침
- [ ] Step 7: `docs/cpp_evolution/format.md`, 기존 evolution 페이지 링크, 그 밖의 §8 문서

## 12. Verification Plan
- [ ] `py -3 tools/test_lessons.py`, `py -3 tools/lessons.py check`(ERROR 0, WARN 0)
- [ ] `py -3 .agent/scripts/build.py --preset windows-x64-debug --test`, `--preset linux-x64-debug --test` (0 warnings, 전체 suite)
- [ ] 모든 레슨 출력의 한글 검사 스크립트(AC-5), `log_recovery` 세 번 실행(AC-3) 두 OS
- [ ] `npm --prefix web/frontend run build`, `npm --prefix web/frontend test`
- [ ] 브라우저(AC-8): 검색 결과와 영어 화면 스크린샷을 `docs/tasks/feature_070-03-essentials-curriculum/screenshots/`에
- [ ] `py -3 .agent/scripts/lint_docs.py` exit 0
- [ ] Every AC row has its evidence in `testrecord.md`

## History / Amendments
- 2026-11-03: 초안. 같은 날 사용자 결정 반영(Assumption 12: 레슨·유닛 코드 주석은 한/영 둘 다, 출력은 영어) 후 승인
- 2026-11-03 (DEV, 구현 전): Assumption 8, §2.2, §2.6, §4의 `std::quick_exit`을 `std::_Exit`으로. `quick_exit`은 Logger가 정상 종료로 처리해 매핑 파일을 지우므로 복구할 것이 남지 않는다(`logger.hpp` 계약, 010-10 Assumption 9). 두 OS의 시제품 실행으로 `_Exit` 뒤 복구를 확인. 레슨의 의도와 AC는 그대로
- 2026-11-03 (DEV, 리뷰 반영): Assumption 12와 AC-5에 여러 줄 주석의 문단 짝 허용, `lessons/support/`를 바꾸지 않는 이유 정정. §2.3·§8에 `LessonConsoleCodePage`의 기대 줄 변경 추가(U4 리뷰가 찾음: 한국어 제목 줄에 기대고 있었음)
- 2026-11-03 (DEV, U7–U9 리뷰 반영): §2.2의 `{:.1f}` → `{:.1}`(Vec2 formatter의 형식), `readLine` → `valueOf`(plan의 이름), Assumption 7의 파일 이름 규칙은 레슨이 찍는 줄에만
- 2026-11-03 (DEV, U10 리뷰 반영): §4에 flush 직후 drain 항목(100 ms 대기, 남는 작은 창은 README에 적음)
