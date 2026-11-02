---
id: 090-06
title: 개발 도구 정비 — guard hook 명령 위치 판정(KI-008), 레슨 콘솔 UTF-8(KI-011), build.py --gtest-filter를 ctest로(KI-012)
depends_on: []
unblocks: []
approved: 2026-11-02
---

# Spec 090-06: 개발 도구 정비

세 문제는 서로 독립이다. 한 작업, 세 단위(U1 guard, U2 build.py, U3 레슨 콘솔)로 진행한다.

2026-11-02 재현 결과(초안 작성 중 확인):
- **KI-008**: 지금 guard는 아래 13개 명령 중 7개를 잘못 막고 1개를 놓친다(§5 AC-1, AC-2의 "현재" 표시). 이 스펙 초안을 쓰는 동안에도, 확인용 heredoc에 `git commit` 글자가 있다는 이유로 Bash 호출이 거부됐다. 즉석 cmake 판정만이 아니라 main 커밋 판정도 같은 문제다.
- **KI-012**: `build.py --preset linux-x64-tsan --target atugcc_tests --gtest-filter LoggerTest.RecordsCallerLocation` → 출력 없이 exit 66. 같은 필터를 `GTEST_FILTER` 환경 변수로 주고 `ctest --preset linux-x64-tsan -R "^AllTests$" --verbose`로 돌리면 `setarch "x86_64" "-R"` launcher가 붙고 1개 테스트가 통과한다.
- **KI-011**: KI 본문의 전제("`atugcc_pattern_example`이 콘솔을 UTF-8로 바꾸지 않는다")는 틀렸다. 예제는 2026-04부터 `enableWindowsAnsi()`에서 `SetConsoleOutputCP(CP_UTF8)`를 부른다(`f37bd35`). 실제로 빠진 곳은 **레슨 실행 파일**이다: 레슨 4개 중 2개가 한글 로그를 찍고, `span_timing`은 `µs`·`⏱`, 패턴 레슨은 `formatTerminal()`(`×`)을 찍는데, 어느 레슨도 콘솔 코드 페이지를 바꾸지 않는다. 이 PC의 OEM 코드 페이지는 949라서 새 cmd 창에서 레슨을 바로 실행하면 깨진다.

## 0. Assumptions (please review)
| # | Decision | Rejected alternative | Why |
|---|---|---|---|
| 1 | **KI-008: 문자열을 지우지 않고 "명령 위치"를 본다.** 명령 줄을 셸 규칙대로 단순 명령(argv 목록)으로 나누고, 프로그램 자리(첫 단어)가 `cmake`/`cmake.exe`일 때만 즉석 configure를 검사한다. main 커밋도 프로그램이 `git`이고 전역 옵션(`-c k=v`, `-C dir`, `--git-dir=…` 등) 다음 첫 단어가 `commit`일 때만 본다 | KI-008이 적어 둔 방법: 따옴표 안 문자열과 heredoc 본문을 지운 뒤 지금 정규식을 적용 | 지우기만 하면 `bash -c "cmake -S . -B b"`가 통과하는 새 구멍이 생기고, 따옴표가 없는 오탐(`grep -n cmake -B 3 CMakeLists.txt`의 `-B`는 grep 옵션이다, `git log --grep commit`)은 그대로 남는다. 명령 위치 판정은 둘 다 해결한다 |
| 2 | **문자열을 실행하는 명령은 안으로 들어가 다시 판정한다**: `bash`/`sh`/`zsh -c <s>`, `pwsh`/`powershell -Command`/`-c <s>`, `cmd /c`·`/k <s>`, `eval <args>`, 셸에 먹이는 heredoc(`bash <<EOF`), `$(…)`와 bash 역따옴표 명령 치환(큰따옴표 안 포함). 앞에 붙는 감싸개는 건너뛴다: `VAR=x` 대입, `sudo`, `env`, `time`, `nice`, `nohup`, `exec`, `command`, PowerShell 호출 연산자 `&`, `wsl`/`wsl.exe`와 그 옵션(`-d X`, `--cd X`, `--exec`, `--`) | 첫 단어만 봄 | 에이전트가 실제로 쓰는 형태다(이 저장소의 `build.py`도 `wsl.exe --exec`를 쓴다). 여기서 놓치면 규칙 2가 쉽게 뚫린다 |
| 3 | **나누기에 실패하면(닫히지 않은 따옴표, 끝나지 않은 heredoc 등) 지금 정규식으로 전체 문자열을 판정한다** — 막는 쪽으로 기운다. 내부 예외가 나면 지금처럼 통과(fail open)한다 | 실패 시 통과 | 판정 불가인 명령은 드물고, 그때 오탐은 우회법(파일에 쓰고 실행)이 있다. 놓치는 쪽이 더 나쁘다. fail open은 guard가 고장 났을 때 작업을 막지 않기 위한 090-01의 결정으로, 그대로 둔다 |
| 4 | **방언은 도구 이름으로 정한다**: `Bash` → POSIX 규칙(`\` 이스케이프, `'…'`, `"…"`, `$'…'`, heredoc `<<`·`<<-`·따옴표 붙은 구분자, 역따옴표 치환). `PowerShell` → 역따옴표 이스케이프, `'…'`(`''`는 따옴표 하나), `"…"`, here-string `@'…'@`·`@"…"@`, `$(…)`; `\`는 보통 글자 | 두 셸을 한 규칙으로 | PowerShell 경로 `"<dir>\sub\"`를 POSIX 규칙으로 읽으면 `\"`가 따옴표를 먹어 나누기가 깨진다 |
| 5 | **무엇이 즉석 configure인지는 바꾸지 않는다**: cmake 인자에 `-S`·`-B`(붙여 쓰기 `-Bout` 포함)가 있거나 `..` 위치 인자가 있으면 막는다. 다만 인자의 따옴표를 벗기고 보므로 `& cmake "-S" "." "-B" "out"`(지금은 통과, 놓침)도 막힌다. `cmake --preset`, `cmake --build --preset`, `ctest`는 계속 허용 | `cmake .`, `cmake ../src`처럼 위치 인자 전체로 넓힘 | KI-008은 오탐 문제다. 판정 범위를 넓히는 것은 쓰임이 관찰된 적 없고, 규칙 문서와 리뷰가 이미 막는다 |
| 6 | **판정 코드는 `agent_common.py`에 둔다**: `simple_commands(command, shell)`(나누기), `is_adhoc_cmake(command, shell="bash")`, `is_git_commit(command, shell="bash")`. `guard.py`의 `GIT_COMMIT_RE`는 없앤다. 표준 라이브러리만 쓴다(`shlex`는 PowerShell과 heredoc을 모르므로 직접 쓴다) | guard.py 안에 둠 | 090-01 B-11: hook과 lint가 같은 판정 모듈을 쓴다 |
| 7 | **KI-012: `--gtest-filter <f>`는 실행 파일을 직접 돌리지 않고 `GTEST_FILTER=<f>`를 준 `ctest --preset <p> -R "^AllTests$" --verbose`로 돌린다.** launcher(`setarch -R`)와 `TSAN_OPTIONS` suppressions는 CMake 테스트 속성 한 곳에서 온다. 모든 preset에 같게 적용한다 | KI-012가 적어 둔 방법: 캐시의 `ATUGCC_SANITIZERS`에 `thread`가 있으면 build.py가 `setarch` 접두어를 붙임 | 같은 launcher 로직이 CMake와 build.py 두 곳에 생긴다. 또 직접 실행은 `TSAN_OPTIONS=suppressions=tests/tsan.supp`(일부러 경쟁하는 crash-dump 스냅샷 읽기)도 빠뜨리므로, launcher만 붙이면 해당 테스트가 TSan 경고로 실패한다. 2026-11-02 시험 실행으로 동작 확인 |
| 8 | **`--verbose`로 gtest 출력을 그대로 보인다**(줄 앞에 `1: `가 붙는다) | `--output-on-failure`만 | GoogleTest 1.14에는 `fail_if_no_test_selected`가 없어서, 아무 테스트에도 맞지 않는 필터가 조용히 통과한다. `Running 0 tests`가 화면에 보여야 한다. 지금 직접 실행과 같은 정보량이다 |
| 9 | **Windows 배치에서는 `set "GTEST_FILTER=<f>"` 줄을 ctest 앞에 둔다. 필터에 `%`·`"`·줄바꿈이 있으면 모든 호스트에서 exit 2로 거부한다** | 이스케이프 처리 | gtest 필터 문법(`*`, `?`, `:`, `-`, `.`)에 필요 없는 글자이고, 배치에서 `%`는 확장되고 `"`는 `set "…"`를 깬다. 호스트마다 다르게 동작하지 않게 한 곳에서 막는다 |
| 10 | **KI-011: 레슨 실행 파일마다 콘솔 준비 객체를 링크한다.** `lessons/support/console_utf8.cpp`를 OBJECT 라이브러리 `atugcc_lesson_console`로 만들고 `lessons/CMakeLists.txt`가 모든 `lesson_<id>`에 링크한다. 그 파일의 정적 RAII 객체가 Windows에서 (표준 출력이 콘솔일 때만) 출력 코드 페이지를 저장하고 `CP_UTF8`로 바꾸며, 정상 종료 때 되돌린다. Windows가 아니면 빈 파일이다. 레슨 코드는 바꾸지 않는다 | (a) 레슨 `main`마다 도우미 호출 (b) 공개 라이브러리 API (c) Logger/Tracer가 쓸 때 몰래 바꿈 (d) 앱 매니페스트 `activeCodePage=UTF-8` | (a) 교재 코드에 상관없는 줄이 생기고 새 레슨이 빠뜨린다 (b) 레슨 밖에 아직 쓰는 사람이 없다 (c) 라이브러리 헤더가 프로세스 전역 상태를 숨겨서 바꾼다 (d) ANSI 코드 페이지를 바꿀 뿐 콘솔 출력 코드 페이지는 바꾸지 않는다 |
| 11 | **되돌리기와 순서: `#pragma init_seg(lib)`로 그 객체를 사용자 수준 정적 객체보다 먼저 만들고 나중에 없앤다.** 그래서 레슨이나 atugcc 헤더의 정적 객체가 소멸자에서 찍는 줄도 UTF-8로 나간다. 비정상 종료(crash, `TerminateProcess`, 강제 종료)에서는 되돌리지 못한다 — 받아들이고 README에 적는다 | 되돌리지 않음(`enableWindowsAnsi()`처럼) / `std::atexit` | 콘솔 코드 페이지는 프로세스가 아니라 **콘솔**의 상태라서, 되돌리지 않으면 레슨이 끝난 뒤에도 사용자의 cmd가 65001로 남는다. 다른 번역 단위의 정적 객체와의 소멸 순서는 표준이 정하지 않으므로, `atexit`나 보통 전역 객체로는 마지막 줄들이 되돌린 뒤에 찍힐 수 있다 |
| 12 | **표준 출력이 콘솔일 때만 바꾼다**(`GetFileType == FILE_TYPE_CHAR`이고 `GetConsoleMode` 성공). 출력 코드 페이지만 바꾸고 입력(`SetConsoleCP`)은 건드리지 않는다 | 항상 바꿈 / 입력도 바꿈 | 파이프로 도는 경우(ctest, 플레이그라운드)는 바이트를 그대로 받으므로 바꿀 필요가 없고, 부모와 공유하는 콘솔을 건드리지 않는다. 레슨은 콘솔 입력을 읽지 않는다 |
| 13 | **020-06 §2.5의 `⏱` 대체 표기 `[t]`는 두지 않는다** | `[t]` 옵션 추가 | 코드 페이지가 맞으면 표시된다. 남는 경우는 글꼴에 글리프가 없는 콘솔뿐이고, 그것은 이 KI의 문제가 아니다 |
| 14 | **`atugcc_pattern_example`과 `enableWindowsAnsi()`는 바꾸지 않는다.** 그 함수가 출력·입력 코드 페이지를 바꾸고 되돌리지 않는 점은 새 KI-031로 남긴다 | 이 작업에서 함께 고침 | 예제는 이미 제대로 보인다. 그 함수는 legacy 패턴 헤더(`detail/terminal_formatter.hpp`)의 일부라서 KI-023 정리 때 함께 다루는 편이 맞다 |

## 1. Objective
- **KI-008**: guard hook이 명령을 "언급만 하는" 호출(heredoc 데이터, grep 패턴, 커밋 메시지, echo)을 막지 않고, 실제로 실행되는 즉석 configure와 main 커밋은 계속(그리고 지금보다 조금 더) 막는다.
- **KI-012**: `build.py --gtest-filter`가 모든 preset에서 `ctest`와 같은 launcher·환경으로 돌아서, TSan preset에서 조용히 66으로 끝나지 않는다.
- **KI-011**: 레슨 실행 파일을 cp949 같은 비UTF-8 Windows 콘솔에서 바로 실행해도 한글·`×`·`µs`·`⏱`가 깨지지 않고, 끝나면 콘솔이 원래 코드 페이지로 돌아간다.

## 2. Requirement Details

### 2.1 Public API Surface
none. `include/atugcc/`는 바뀌지 않는다.

도구 쪽 인터페이스:
- [`agent_common.py`](/.agent/scripts/agent_common.py) (나누기 코드는 [`shell_commands.py`](/.agent/scripts/shell_commands.py)에 있고 `agent_common`이 다시 내보낸다): `simple_commands(command: str, shell: str = "bash") -> list[list[str]] | None`(나누기 실패 시 `None`), `is_adhoc_cmake(command, shell="bash")`, `is_git_commit(command, shell="bash")`. `shell`은 `"bash"` 또는 `"powershell"`.
- [`build.py`](/.agent/scripts/build.py): 옵션 이름과 뜻(`--gtest-filter <f>`: 빌드 뒤 이 필터로 `atugcc_tests`를 돌림)은 그대로. 돌리는 방법만 바뀐다.

### 2.2 Internal Implementation

**U1 guard (KI-008)**
- `simple_commands`: 한 글자씩 읽는 작은 상태 기계. 따옴표 밖의 `;`, `&&`, `||`, `|`, `&`(bash 백그라운드), 줄바꿈, `(`, `)`, `{`, `}`에서 단순 명령을 끊는다. 단어는 따옴표를 벗긴 값으로 모은다. heredoc은 명령 줄이 끝난 다음 줄부터 구분자 줄까지를 그 명령의 입력으로 떼어 둔다(단어가 아니다). 명령 치환과 셸 문자열은 재귀로 나눈 결과를 같은 목록에 더한다. 재귀 깊이는 8로 제한하고, 넘으면 나누기 실패.
- `guard.check_command(command, shell)`: `decide()`가 도구 이름에서 `shell`을 정해 넘긴다. 메시지는 지금과 같다.

**U2 build.py (KI-012)**
- `build_steps(...)`: `gtest_filter`가 있으면 마지막 단계는 `["ctest", "--preset", p, "-R", "^AllTests$", "--verbose"]`, 그리고 그 단계의 환경 `GTEST_FILTER=<f>`. 단계에 환경을 싣는 방법(예: 단계를 `(argv, env)`로)은 구현이 정한다. `--dry-run` 출력에 필터가 보여야 한다.
- Linux 경로 `run()`은 `subprocess.run(step, env=os.environ | step_env)`. Windows `batch_script()`는 ctest 줄 앞에 `set "GTEST_FILTER=<f>"`.
- 필터 검사(Assumption 9)는 `main()`에서 preset 고르기 전에 한다. Windows 호스트에서 Linux preset을 WSL로 넘길 때도 같은 검사를 먼저 거친다.
- `TEST_EXE`와 `exe_suffix`는 쓰이지 않게 되면 지운다.

**U3 레슨 콘솔 (KI-011)**
- `lessons/support/console_utf8.cpp`:
  ```cpp
  #ifdef _WIN32
  #pragma warning(disable : 4073)   // init_seg(lib) 경고: 의도한 것
  #pragma init_seg(lib)
  namespace {
  class ConsoleUtf8 {               // 생성: 저장 후 CP_UTF8, 소멸: 되돌림
      UINT previous_ = 0;           // 0 = 바꾸지 않았음
  public:
      ConsoleUtf8() noexcept;       // stdout이 콘솔일 때만 (Assumption 12)
      ~ConsoleUtf8();
  } const g_consoleUtf8;
  }
  #endif
  ```
  Windows 헤더는 이 파일에만 들어간다(`WIN32_LEAN_AND_MEAN`, `NOMINMAX`).
- `lessons/CMakeLists.txt`: `add_library(atugcc_lesson_console OBJECT support/console_utf8.cpp)` 한 번, 각 `lesson_<id>`에 `target_link_libraries(... PRIVATE atugcc_lesson_console)`. OBJECT 라이브러리라서 링커가 참조 없는 객체를 버리지 않는다.
- `tools/lessons.py`는 `lessons/support/`를 레슨이나 유닛으로 보지 않는다(지금 `tracks/*`, `units/*`만 읽음). 플레이그라운드 빌드도 같은 `lessons/CMakeLists.txt`를 쓰고, Linux에서는 빈 객체다.
- 시험(AC-8, AC-9): `tests/console/console_cp_probe.cpp`(같은 OBJECT 라이브러리 링크, 실행 중 `GetConsoleOutputCP()`와 정적 객체 소멸자 안의 값을 파일로 씀)와 `tests/console/check_console_cp.py`. 드라이버는 `CREATE_NO_WINDOW`로 숨은 새 콘솔을 만들고 그 안에서 `chcp 949 >nul & <exe> & <끝난 뒤 출력 코드 페이지를 읽는 자식>`을 돌린다. 표준 핸들을 넘기지 않으므로 프로그램은 그 콘솔의 핸들을 물려받는다(구현 중 확인: `>CON`은 콘솔을 쓰기 전용으로 열어 `GetConsoleMode`가 실패하고, 인자 없는 `chcp`는 레슨이 바꾸는 출력 코드 페이지를 보여 주지 않는다). Windows에서만 CTest에 등록한다.

### 2.3 Platform Specifics
- U1: 셸 방언 두 개(Assumption 4). hook 자체는 지금처럼 Windows와 Linux 모두에서 돈다.
- U2: Windows는 배치의 `set`, Linux는 프로세스 환경. Windows 호스트 → WSL 전달은 지금 그대로(인자만 넘김).
- U3: Windows 전용 코드. `#pragma init_seg`는 MSVC 확장이다. 이 저장소의 Windows 빌드는 MSVC뿐이다.

## 3. C++ Standard Evolution
N/A. U3의 C++ 요점(번역 단위 사이 정적 초기화·소멸 순서는 표준이 정하지 않음 — "static initialization order fiasco", MSVC `init_seg`)은 파일 주석에만 적는다. 레슨 후보로 쓸 만하지만 레슨을 만드는 것은 이 작업의 범위가 아니다.

## 4. Edge Cases
- [x] Thread safety / memory ordering — U3: 생성은 `main` 전, 소멸은 `main` 뒤 사용자 정적 객체 소멸 다음이다. 그때 아직 도는 스레드(분리된 스레드)가 찍는 줄은 되돌린 뒤의 코드 페이지로 나갈 수 있다. 레슨은 `std::jthread`/`join`을 쓰므로 해당 없음. U1·U2는 단일 스레드 스크립트
- [x] Resource lifetime / RAII — U3 객체가 저장한 코드 페이지를 소멸자에서 되돌린다. 바꾸지 않았으면(`previous_ == 0`) 아무것도 하지 않는다
- [x] Platform differences — §2.3. U3는 Windows에서만 코드가 있다. U1은 방언별 규칙
- [x] Template instantiation / concept constraints — N/A
- [x] ODR — U3는 익명 이름공간의 객체 하나, OBJECT 라이브러리로 실행 파일마다 한 번 들어간다. 헤더가 아니다
- [x] Undefined behaviour — U3 소멸자는 Win32 호출 하나이고 예외를 던지지 않는다
- [x] (U1) 명령이 언급만 하는 경우 — heredoc 데이터, 따옴표 안의 인자, 옵션 값(`grep -B 3`), 커밋 메시지, echo → 허용 (AC-1)
- [x] (U1) 실행되는 문자열 — 셸 `-c`, `cmd /c`, `eval`, 셸에 먹이는 heredoc, `$(…)`, 역따옴표, `wsl --exec` → 안을 판정 (AC-2)
- [x] (U1) 나눌 수 없는 명령 — 정규식으로 판정, 막는 쪽 (AC-3)
- [x] (U1) PowerShell 경로의 `\`, here-string — 방언 규칙 (AC-1, AC-2)
- [x] (U1) 판정하지 않는 실행 경로 — `find -exec`, `xargs`, `ssh host "…"`, 스크립트 파일 안의 명령, Python `subprocess` 안의 문자열. guard는 실수를 막는 장치이지 보안 경계가 아니다(090-01). §6
- [x] (U2) 아무 테스트에도 맞지 않는 필터 — `Running 0 tests`가 보이고 exit 0 (지금과 같음, AC-6)
- [x] (U2) 테스트 실패 — gtest exit ≠ 0 → ctest 실패 → build.py가 0이 아닌 코드로 끝남 (AC-5)
- [x] (U2) `--test`와 `--gtest-filter`를 함께 — 전체 ctest 다음 필터 ctest, 지금 순서와 같음
- [x] (U2) `--target`으로 `atugcc_tests`가 아닌 것을 빌드하고 필터를 줌 — 지금처럼 이전에 빌드된 `atugcc_tests`를 돌린다. 없으면 ctest가 실행 파일을 찾지 못해 실패
- [x] (U3) 파이프로 실행(ctest, 플레이그라운드, `> file`) — 바꾸지 않음 (AC-8)
- [x] (U3) 이미 65001인 콘솔 — 저장 값이 65001이라 되돌려도 같다
- [x] (U3) 비정상 종료 — 되돌리지 못함, README에 적음 (Assumption 11)
- [x] (U3) 레슨 둘이 같은 콘솔에서 동시에 — 사용자가 `&`로 동시에 돌리는 경우만 해당. 나중에 끝난 쪽이 자기가 본 값으로 되돌린다. 받아들인다

## 5. Acceptance Criteria
| ID | Criterion | Verified by |
|---|---|---|
| AC-1 | **오탐 없음**: 아래 명령은 feature 브랜치에서 허용되고, 커밋이 아닌 것은 main에서도 허용된다. heredoc 데이터에 즉석 configure 문자열 (현재 DENY) · heredoc 데이터에 `git commit` 문자열 (현재 DENY) · `grep -n "cmake -B" x.md` (현재 DENY) · `grep -n cmake -B 3 CMakeLists.txt` (현재 DENY) · `echo "git commit"` (현재 DENY) · `git log --grep commit` (현재 DENY) · feature 브랜치에서 메시지에 `cmake -S`가 든 `git commit -m "…"` (현재 DENY) · PowerShell here-string 데이터에 즉석 configure 문자열 | `test_agent_scripts.py` 새 표 테스트(Bash·PowerShell). "현재"는 2026-11-02 probe 결과 |
| AC-2 | **실제 실행은 막힘**: `cmake -S . -B build`, `cd x && cmake ..`, `a; cmake -Bout`, `bash -c "cmake -S . -B b"`, `sh -c '…'`, `pwsh -Command "cmake -B o"`, `cmd /c "cmake -B o"`, `wsl.exe --cd . --exec cmake -B o`, `sudo env X=1 cmake ..`, `echo "$(cmake -B o)"`, `` `cmake -B o` ``, `bash <<EOF` 본문의 `cmake -B o`, PowerShell `& "<path>\cmake.exe" "-S" "." "-B" "out"` (현재 allow, 놓침); main에서 `git commit -m x`, `git -C . commit`, `git -c user.name=x commit`. 그리고 `cmake --preset p`, `cmake --build --preset p`, `ctest --preset p`는 허용 | 같은 표 테스트. 변이 두 개: (M1) 명령 위치 판정 대신 옛 정규식 → AC-1 행 실패, (M2) 셸 문자열 재귀 제거 → AC-2의 `-c`/`cmd /c` 행 실패 |
| AC-3 | 나눌 수 없는 명령(닫히지 않은 따옴표 안의 즉석 configure 문자열)은 막히고, guard 내부 예외는 지금처럼 통과(fail open)한다 | 표 테스트 한 행 + 기존 fail-open 테스트 |
| AC-4 | **실제 hook**: 작업 브랜치의 이 세션에서 (a) heredoc 데이터에 `git commit`과 즉석 configure 문자열이 든 Bash 호출이 실행되고 (b) 실제 즉석 configure Bash 호출은 거부된다 | 이 세션의 도구 호출 결과를 testrecord에 기록 |
| AC-5 | **TSan 필터 실행**: `build.py --preset linux-x64-tsan --target atugcc_tests --gtest-filter LoggerTest.RecordsCallerLocation`이 exit 0으로 끝나고 출력에 `setarch`가 붙은 test command와 `Running 1 test`가 보인다(고치기 전: 출력 없이 exit 66). 실패하는 테스트를 거르면 exit ≠ 0 | 명령 출력. 실패 쪽은 임시 변이(한 테스트의 기대값 변경, 확인 뒤 되돌림) |
| AC-6 | **Windows 필터 실행**: `build.py --preset windows-x64-debug --target atugcc_tests --gtest-filter "LoggerTest.*"`가 exit 0, `Running N tests`(N ≥ 1) 출력. 맞는 테스트가 없는 필터는 `Running 0 tests`가 보인다. `--dry-run`이 `set "GTEST_FILTER=…"`와 ctest 줄을 보인다 | 명령 출력 + `build_steps`/`batch_script` 단위 테스트 |
| AC-7 | 필터에 `%`, `"`, 줄바꿈이 있으면 빌드 전에 exit 2와 이유를 출력한다 (Windows·Linux preset 모두) | `test_agent_scripts.py` 단위 테스트 |
| AC-8 | **콘솔 코드 페이지**: 숨은 새 콘솔(cp949)에서 probe를 콘솔 출력으로 돌리면 실행 중 `65001`, 정적 객체 소멸자 안에서도 `65001`, 끝난 뒤 콘솔의 출력 코드 페이지는 `949`. 표준 출력을 파이프로 돌리면 실행 중에도 바뀌지 않는다 | CTest `LessonConsoleCodePage`(Windows). 변이: (M3) 되돌림 제거 → 끝난 뒤 65001로 실패, (M5) 설정 제거 → 실행 중 949로 실패, (M4) `init_seg(lib)` 제거 → 소멸자 검사가 실패하거나 링크 순서상 우연히 통과할 수 있으므로 결과를 그대로 기록 |
| AC-9 | **실제 레슨**: 숨은 cp949 콘솔에서 `lesson_device_state_machine`을 돌린 뒤 같은 콘솔의 화면 버퍼를 읽으면 `=== 터미널 추적 결과 (formatTerminal) ===` 줄이 그대로 있다(UTF-8이 아닌 코드 페이지라면 깨진 글자가 된다). 모든 `lesson_<id>`가 `atugcc_lesson_console`을 링크한다 | 같은 드라이버의 두 번째 검사(화면 버퍼는 `ReadConsoleOutputCharacterW`로, 같은 콘솔에 붙은 Python 자식이 읽음) + CMake 링크 확인. 숨은 콘솔에서 화면 버퍼 읽기가 동작하지 않으면 U3 첫 단계에서 멈추고 보고한다 |
| AC-10 | 회귀 없음: `windows-x64-debug`, `linux-x64-debug`, `linux-x64-tsan` 전체 ctest 통과(레슨 smoke 포함), 경고 0, `test_agent_scripts.py` 통과, `lint_docs.py` exit 0 | 명령 출력 |

## 6. Out of Scope
- guard가 판정하지 않는 실행 경로(`find -exec`, `xargs`, `ssh`, 스크립트 파일 안, Python `subprocess` 문자열) — guard는 실수 방지 장치다(090-01 B-11). 규칙 문서·리뷰·문서 게이트가 남는다. 쓰임이 관찰되면 새 KI
- 실행 중에 만들어지는 프로그램 이름(`x=cmake; $x -B o`, `$(echo cmake) -B o`) — 정적으로 나눠서는 알 수 없다. `echo { cmake -B o }`처럼 뒤쪽 단어로 온 `{`는 구분자로 본다(드문 형태, 막는 쪽). 줄바꿈으로 이어지는 파이프(`… |⏎bash`), 치환 안의 `case` 패턴 `)`, `Start-Process pwsh -ArgumentList '-c …'`, base64로 넘기는 `pwsh -EncodedCommand`도 판정하지 않는다 — U1b 리뷰, 쓰임이 관찰되면 새 KI
- 즉석 configure 판정 범위 확대(`cmake .`, `cmake ../src`) — Assumption 5. 관찰된 쓰임이 없다
- `enableWindowsAnsi()`가 출력·입력 코드 페이지를 되돌리지 않음 — 새 **KI-031** (KI-023 정리 때)
- 레슨 밖 사용자 프로그램을 위한 공개 콘솔 도우미 — 필요해지면 새 작업
- `⏱` 대체 표기 `[t]` — 두지 않기로 함 (Assumption 13)

## 7. Dependencies & Backends
none. Python 표준 라이브러리(`ctypes`는 U3 시험 드라이버에서만), Win32 `SetConsoleOutputCP`/`GetConsoleOutputCP`/`GetFileType`/`GetConsoleMode`/`ReadConsoleOutputCharacterW`.

## 8. Documentation Updates
| Document | Section | Change |
|---|---|---|
| [`docs/known_issues.md`](/docs/known_issues.md) | KI-008, KI-011, KI-012, 표 | CLOSED by 090-06과 고친 방법. KI-011에는 전제 정정(예제는 이미 UTF-8, 빠진 곳은 레슨)과 `[t]`를 두지 않은 결정. 새 KI-031, KI-032(U3c에서 발견: 레슨의 ANSI 색 코드가 VT 처리 없는 콘솔에서 그대로 보임) |
| [`.claude/hooks/guard.py`](/.claude/hooks/guard.py) | 머리 docstring | 명령 위치 판정, 재귀 대상, 나누기 실패 시 동작 |
| [`.agent/scripts/build.py`](/.agent/scripts/build.py) | 머리 docstring, `--gtest-filter` help | ctest + `GTEST_FILTER`로 돈다, 거부하는 글자 |
| [`.agent/rules/config.md`](/.agent/rules/config.md) | hook 문장, build.py 사용법 | hook은 실제로 실행되는 configure만 막는다(언급은 허용). `--gtest-filter`는 ctest의 launcher·환경을 쓴다 |
| [`.agent/rules/test.md`](/.agent/rules/test.md) | 단위 검사 명령 | 같은 명령이 TSan preset에서도 동작함 |
| [`docs/agent_start_prompt.md`](/docs/agent_start_prompt.md) | Hooks 문장 | 실행되는 명령만 판정한다는 한 구절 |
| [`lessons/README.md`](/lessons/README.md) | 레슨 실행 / 새 레슨 추가 | Windows 콘솔에서 레슨은 출력 코드 페이지를 UTF-8로 바꾸고 끝나면 되돌린다(비정상 종료 제외). 레슨 코드에 따로 쓸 것 없음 |
| [`docs/specs/020_06_tracer_span_timing.md`](/docs/specs/020_06_tracer_span_timing.md) | History / Amendments | `[t]` 대체 표기는 090-06에서 두지 않기로 함 (본문은 바꾸지 않음) |
| [`docs/tasks/agent_todo.md`](/docs/tasks/agent_todo.md) | 090-06 줄, Phase 9 제목, 진행 순서 A.2 | 상태, 링크, 완료 표시 |

## 9. Technical Constraints
- Python 3.11+ 표준 라이브러리 (hook, build.py, 시험 드라이버)
- Compiler: MSVC (VS 2026) / GCC (latest stable), CMake 3.26+, C++23
- GoogleTest 1.14 (`GTEST_FILTER` 환경 변수 지원)

## 10. Context & References
- [guard.py](/.claude/hooks/guard.py), [agent_common.py](/.agent/scripts/agent_common.py), [build.py](/.agent/scripts/build.py), [test_agent_scripts.py](/.agent/scripts/test_agent_scripts.py)
- [CMakeLists.txt](/CMakeLists.txt) (`ATUGCC_TEST_LAUNCHER`), [tests/CMakeLists.txt](/tests/CMakeLists.txt) (`AllTests`, `TSAN_OPTIONS`), [lessons/CMakeLists.txt](/lessons/CMakeLists.txt)
- [terminal_formatter.hpp](/include/atugcc/pattern/detail/terminal_formatter.hpp) (`enableWindowsAnsi`), [example_visualizer.cpp](/src/pattern/example_visualizer.cpp)
- [090-01](/docs/specs/090_01_agent_process.md) B-11 (hook과 lint가 판정 모듈 공유), [020-06](/docs/specs/020_06_tracer_span_timing.md) §2.5
- 재현 기록: 090-01 testrecord "Live hook" 행, 020-05 testrecord R5, 010-08 testrecord R11

## 11. Implementation Plan
- [ ] Step 0: 브랜치 `feature/090-06-dev-tools-cleanup`, `plan.md`
- [ ] U1: AC-1~3 표 테스트를 먼저 쓰고 지금 코드에서 실패하는 행 확인 → `simple_commands`, `is_adhoc_cmake`, `is_git_commit` → `guard.py` 연결 → 변이 M1, M2 → AC-4 실제 hook
- [ ] U2: `build_steps`/`batch_script`/필터 검사 단위 테스트 → 구현 → AC-5(WSL), AC-6(Windows)
- [ ] U3: 드라이버의 화면 버퍼 읽기를 먼저 시험(AC-9 전제) → `console_utf8.cpp`, OBJECT 라이브러리, probe, CTest 등록 → 변이 M3~M5
- [ ] 문서(§8), 리뷰(`cpp-reviewer`: U3 C++/CMake, U1 판정 규칙), testrecord, walkthrough

## 12. Verification Plan
- [ ] `py -3 .agent/scripts/test_agent_scripts.py`
- [ ] `py -3 .agent/scripts/build.py --preset windows-x64-debug --test`, `--preset linux-x64-debug --test`, `--preset linux-x64-tsan --test` (경고 0)
- [ ] AC-5, AC-6 명령
- [ ] `py -3 .agent/scripts/lint_docs.py` exit 0
- [ ] 모든 AC 행의 근거를 `testrecord.md`에

## History / Amendments
- 2026-11-02: 초안 (KI-008·011·012 재현 결과 포함), 같은 날 승인(사용자)
- 2026-11-02 (DEV): U1b 리뷰가 찾은 형태를 판정 대상에 더함(plan D1'): bash 예약어(`for`/`if`/`while`/`!`) 안의 명령, `&>`·`>&`, 리다이렉션 대상과 `<<<` 안의 치환, 따옴표 없는 heredoc 본문과 `@"…"@` 안의 치환, 파이프나 heredoc으로 셸에 먹이는 텍스트, 옵션이 붙은 감싸개(`sudo -E`, `timeout`, `stdbuf`), PowerShell `iex`·`.`·`Start-Process`. Assumption 1의 원칙(실행되는 것만 판정)은 그대로이고, §6에 판정하지 않는 형태 한 줄을 더함. 나누기 코드가 900줄이 되어 `shell_commands.py`로 옮김(`agent_common`이 다시 내보내므로 Assumption 6의 "한 판정 모듈"은 유지)
- 2026-11-02 (DEV): Assumption 3 보충: 나누기 코드 안에서 난 예외는 "나눌 수 없음"과 같이 다룬다(정규식 판정, 막는 쪽). guard 자체의 예외는 지금처럼 통과(fail open). U1b 재리뷰 뒤 lead가 고침: 셸 옵션 값(`bash -o pipefail -c`, `pwsh -ExecutionPolicy Bypass -Command`) 뒤의 스크립트 인자, Windows PowerShell 5.1의 위치 인자(-Command), `env -S`, `timeout --signal=…`, 감싸개 처리의 선형 시간
- 2026-11-02 (DEV): U2 리뷰: Windows 배치에서 따옴표 없는 `^`가 사라져 ctest가 `-R AllTests$`를 받던 것을 고침(cmd 특수 문자가 든 인자는 따옴표로 감쌈, 실제 배치를 돌리는 시험 추가). 새 KI-032(§8)
- 2026-11-02 (DEV): U3c 시험 방식 정정(§2.2, AC-8 문구): `>CON`과 인자 없는 `chcp` 대신 물려받은 콘솔 핸들과 `GetConsoleOutputCP()`를 읽는 자식
