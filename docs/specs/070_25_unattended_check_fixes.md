---
id: 070-25
title: 무인 확인을 흐리는 KI 정리 (KI-050, KI-052, KI-053)
depends_on: []
unblocks: [070-26]
approved: 2026-11-16
---

# Spec 070-25: 무인 확인을 흐리는 KI 정리 (KI-050, KI-052, KI-053)

## 0. Assumptions (please review)
| # | Decision | Rejected alternative | Why |
|---|---|---|---|
| 1 | **범위**: 사람이 지켜보지 않는 확인(`build.py --test`, `tools/exercises.py check`, 문서의 프런트엔드 테스트 명령)이 멈추거나 거짓 결과를 내는 세 KI만 고친다. 레슨 내용은 KI-053이 요구하는 만큼만 바꾼다 | 열린 KI 전부 | 나머지(KI-001, 009, 015, 023, 024)는 주인 작업이 있다 |
| 2 | **KI-050: Windows Debug 레슨은 CRT 보고를 대화상자 대신 stderr로 보낸다.** 새 파일 `lessons/support/crt_report.cpp`를 `atugcc_lesson_console`(모든 `lesson_<id>`, `practice_<id>`에 링크)에 더한다. `_CRT_ERROR`와 `_CRT_ASSERT`를 `_CRTDBG_MODE_FILE` + `_CRTDBG_FILE_STDERR`로, `_set_abort_behavior(0, _WRITE_ABORT_MSG \| _CALL_REPORTFAULT)`. 결과: 잡히지 않은 예외나 `abort()`는 한 줄을 stderr에 쓰고 종료 코드 3으로 바로 끝난다(Release와 같음) | (a) `console_utf8.cpp`에 같이 쓰기; (b) 테스트 러너(`ATUGCC_TEST_LAUNCHER`, `exercises.py`)에서만 환경으로 끄기 | (a) 그 파일은 콘솔 코드 페이지만 다룬다. 일이 다르면 파일도 나눈다. (b) CRT 대화상자는 환경 변수로 끌 수 없고, 연습 사본을 손으로 실행할 때도 같은 동작이어야 과제 설명과 맞는다 |
| 3 | **디버거가 붙어 있으면 바꾸지 않는다**(`IsDebuggerPresent()`): Visual Studio / VS Code에서 디버깅할 때는 지금처럼 대화상자(Retry로 중단점)가 뜬다 | 항상 stderr | 디버거로 레슨을 따라가는 사람에게 대화상자는 쓸모 있는 진입점이다 |
| 4 | **Release와 Linux는 변화 없음**: 새 파일은 `_WIN32`이고 `_DEBUG`일 때만 내용이 있다. `#ifdef`는 `console_utf8.cpp`처럼 이 지원 파일 안에만 둔다 | 라이브러리(`atugcc_core`)에 넣기 | 라이브러리 사용자의 크래시 동작을 바꾸면 안 된다. 레슨 지원 코드의 일이다 |
| 5 | **대화상자 때문에만 관찰 과제였던 것은 자동 과제로 바꾼다**: `thread_and_log`의 마지막 과제(1단계에서 `std::terminate`)에 `exit = "nonzero"`와 `source` 규칙을 준다. `error_expected`의 `remove_catch`는 이미 자동이고 이제 `windows-x64-debug`에서도 통과해야 한다. `log_recovery`의 `crash_dump_abort`는 로컬 도구(`read_dump.py`)가 필요해 관찰 과제로 남는다. 세 과제의 힌트·해설과 `lessons/README.md`에서 대화상자 문장을 고친다 | 과제 정의는 그대로 | 관찰 과제의 기준(`lessons/README.md`)에서 "abort()로 끝나야 하는 과제"가 빠지므로, 기준과 정의를 같이 맞춘다 |
| 6 | **KI-052는 재현부터 한다.** 2026-11-16에 PowerShell에서 저장소 루트의 `npm --prefix web/frontend test`는 통과했다(13 파일, 164 테스트). 실패는 070-16-01 때 한 번 기록됐고 조건이 적혀 있지 않다. 후보: 작업 디렉터리의 드라이브 글자가 소문자인 셸(Git Bash, VS Code 태스크)에서 vitest가 두 번 로드됨. 재현되면 원인을 고치고(설정 또는 문서의 명령), 세 셸(PowerShell, Git Bash, WSL)에서 재현되지 않으면 `dropped: not reproducible`로 닫고 KI에 시도한 조건을 남긴다 | 문서의 명령을 `cd web/frontend && npm test`로 그냥 바꾸기 | 원인을 모른 채 명령만 바꾸면 같은 실패가 다른 곳(playground 테스트, CI)에서 다시 나온다 |
| 7 | **KI-053: `device_state_machine`은 정해진 시간 대신 틱 수를 기다린다.** `main`이 `sleep_for(120ms)` 대신 워커가 마지막 틱을 끝냈다는 신호(`std::atomic<std::size_t>` + `wait`/`notify_one`, 또는 `std::latch`)를 기다린 뒤 멈춘다. README 연습 1과 `exercises.toml`의 "대기 시간을 늘리세요" 문장을 지운다 | 대기를 250 ms로 늘리기 | 느린 호스트(sanitizer preset, 바쁜 CI)에서 같은 문제가 다시 난다. 시간을 기다리는 대신 사건을 기다리는 것이 이 레슨이 보여 줄 바른 방식이기도 하다 |
| 8 | KI-053의 고친 레슨은 021–024의 패턴 재작성 때 다시 쓰일 수 있다. 여기서는 대기 방식만 바꾸고 구조는 두지 않는다 | 레슨 전체 재작성 | 패턴 작업의 몫이다 |

## 1. Objective
A3(저작 인프라)의 첫 작업이다. 레슨을 더하거나 고친 뒤 "확인 명령을 돌리고 결과를 믿는다"가 되려면 확인이 사람 손 없이 끝나고, 통과와 실패가 실제와 같아야 한다. 지금은 세 곳이 어긋난다.
- KI-050: Windows Debug에서 `abort()` 대화상자가 떠서 `exercises.py check`와 smoke test가 시간 제한까지 멈춘다.
- KI-052: 문서에 적힌 프런트엔드 테스트 명령이 전부 실패로 나온 적이 있다.
- KI-053: `device_state_machine`의 연습 1이 타이머 정밀도에 따라 아무 변화도 보여 주지 않는다.

## 2. Requirement Details

### 2.1 Public API Surface
없음. `include/atugcc/`는 바꾸지 않는다.

### 2.2 Internal Implementation
| 파일 | 바꾸는 것 |
|---|---|
| `lessons/support/crt_report.cpp` [NEW] | Assumption 2–4. `console_utf8.cpp`와 같은 모양(이름 없는 namespace의 정적 객체, `init_seg(lib)`)으로 프로그램 시작 때 한 번 설정한다. 되돌릴 것은 없다(프로세스 상태) |
| [`lessons/CMakeLists.txt`](/lessons/CMakeLists.txt) | `atugcc_lesson_console`의 소스에 새 파일을 더한다 |
| [`lessons/tracks/01_essentials/11_thread_and_log/exercises.toml`](/lessons/tracks/01_essentials/11_thread_and_log/exercises.toml) | 마지막 과제를 자동으로(Assumption 5), 해설의 대화상자 문장 수정 |
| `04_error_expected/exercises.toml`, `12_log_recovery/exercises.toml` | 대화상자 문장 수정(두 언어) |
| [`lessons/tracks/02_patterns/01_device_state_machine/main.cpp`](/lessons/tracks/02_patterns/01_device_state_machine/main.cpp), README 두 개, `exercises.toml` | Assumption 7 |
| `web/frontend/` 또는 [`web/README.md`](/web/README.md) | Assumption 6의 결과에 따라 |

### 2.3 Platform Specifics
- KI-050의 코드는 MSVC Debug 전용이다. Clang(Linux)에서는 빈 번역 단위다.
- KI-053의 대기는 두 컴파일러에서 같은 표준 라이브러리 기능만 쓴다(`std::atomic::wait` 또는 `std::latch`, 둘 다 libstdc++ 14와 MSVC에 있음).

## 3. C++ Standard Evolution
N/A. KI-053의 "시간 대신 사건을 기다린다"는 README에 한 문장으로 적는다. evolution 페이지는 만들지 않는다.

## 4. Edge Cases
- [x] Thread safety: KI-053의 신호는 `std::atomic` 또는 `std::latch`로 워커와 `main` 사이에만 쓴다. 워커가 마지막 틱 전에 끝나는 경우(연습에서 `request_stop`을 일찍 부름)에도 `main`이 영원히 기다리지 않게, 워커 종료 때도 신호를 준다(또는 `jthread` join으로 끝남을 안다).
- [x] Resource lifetime: CRT 설정은 프로세스 전역이고 되돌리지 않는다. 정적 객체의 생성 순서는 `init_seg(lib)`로 사용자 정적 객체보다 앞선다.
- [x] Platform differences: Assumption 4.
- [x] Template / concept: N/A.
- [x] ODR: 새 파일은 이름 없는 namespace만 쓴다.
- [x] UB: `abort()` 뒤의 동작은 CRT의 것 그대로다. 신호 처리기는 건드리지 않는다(`log_recovery`의 crash dump 처리기와 겹치지 않는지 AC-3이 확인).
- [x] 출력이 파이프일 때(ctest, 웹은 Linux라 해당 없음): stderr로 가는 한 줄이 smoke test의 통과 조건(종료 코드)을 바꾸지 않는다.

## 5. Acceptance Criteria
| ID | Criterion | Verified by |
|---|---|---|
| AC-1 | `windows-x64-debug`에서 잡히지 않은 예외로 끝나는 연습 사본이 대화상자 없이 5초 안에 0이 아닌 코드로 끝난다 | `py -3 tools/exercises.py check error_expected --preset windows-x64-debug`(해설대로 고친 사본): `remove_catch` 통과, 시간 초과 없음 |
| AC-2 | `thread_and_log`의 마지막 과제가 자동 과제이고, 해설대로 고친 사본이 `windows-x64-debug`와 `linux-x64-debug`에서 통과하며 원본은 통과하지 않는다 | `exercises.py check thread_and_log` 두 preset, `lesson.thread_and_log.exercises_verify` |
| AC-3 | `log_recovery`의 crash dump 동작이 그대로다 | `build.py --preset windows-x64-debug --test`의 `CrashDump`, `lesson.log_recovery` 통과 |
| AC-4 | Release와 Linux의 레슨 바이너리에 새 설정 코드가 없다 | 새 파일의 전처리 조건 검토 + `windows-x64-release`, `linux-x64-debug` 전체 테스트 통과 |
| AC-5 | `device_state_machine`의 원본을 20번 연속 실행해도 마지막 틱까지의 전이가 모두 출력되고, 연습 1을 해설대로 풀면 대기 시간을 바꾸지 않고 새 전이가 보인다 | 두 preset에서 반복 실행 스크립트(testrecord에 횟수와 결과), `exercises.py check device_state_machine` |
| AC-6 | KI-052: 재현 조건과 원인이 KI에 적혀 있고, 문서의 명령이 PowerShell, Git Bash, WSL에서 통과한다. 재현되지 않으면 세 셸의 실행 기록과 함께 `dropped`로 닫는다 | testrecord의 세 셸 실행 결과, `web/README.md` |
| AC-7 | 문서에 "대화상자를 누를 때까지 기다린다"는 문장이 디버거 경우 말고는 남아 있지 않고, KI-050·052·053이 CLOSED다 | `git grep` 결과, `lint_docs.py` exit 0 |

## 6. Out of Scope
- 평범한 콘솔 호스트의 색 출력(KI-032), `lesson.testing` 시간 초과(KI-046): DEFERRED 그대로.
- `device_state_machine`의 패턴 구조 재작성: 021–024.
- 테스트(`tests/`) 바이너리의 CRT 대화상자: 지금 문제가 보고되지 않았다. 생기면 새 KI.

## 7. Dependencies & Backends
none.

## 8. Documentation Updates
| Document | Section | Change |
|---|---|---|
| [`lessons/README.md`](/lessons/README.md) | 연습 과제 정의(관찰 과제의 기준, 마지막 문단), 실행 | `abort()` 과제를 관찰 과제 기준에서 빼고, Windows Debug의 동작(stderr 한 줄, 종료 코드 3, 디버거에서는 대화상자)을 적는다 |
| `lessons/tracks/…/exercises.toml` 3개 | 힌트·해설 | Assumption 5 |
| `device_state_machine` README 두 개 | 연습 1, 실행 설명 | Assumption 7 |
| [`web/README.md`](/web/README.md) | Verification | AC-6의 결과 |
| [`docs/known_issues.md`](/docs/known_issues.md) | KI-050, 052, 053 | CLOSED |

## 9. Technical Constraints
- Compiler: MSVC (VS 2026) / Clang 20 with libstdc++ 14 (Linux)
- CMake: 4.0+
- C++ Standard: C++23

## 10. Context & References
- [console_utf8.cpp](/lessons/support/console_utf8.cpp), [lessons/CMakeLists.txt](/lessons/CMakeLists.txt)
- [070-17](/docs/specs/070_17_exercise_check.md), [070-20](/docs/specs/070_20_remaining_exercises.md): 관찰 과제의 기준
- [known_issues.md](/docs/known_issues.md): KI-050, KI-052, KI-053

## 11. Implementation Plan
- [ ] U1: `crt_report.cpp` + CMake (Risky: 모든 레슨의 크래시 동작)
- [ ] U2: `exercises.toml` 세 개와 `lessons/README.md`
- [ ] U3: `device_state_machine` 대기 방식, README, 과제
- [ ] U4: KI-052 재현(research) → 수정 또는 dropped
- [ ] U5: KI 닫기, 문서 gate

## 12. Verification Plan
- [ ] `py -3 .agent/scripts/build.py --preset windows-x64-debug --test --report`, `linux-x64-debug` 같은 명령(WSL), 경고 0
- [ ] `windows-x64-release --test --label lesson`
- [ ] AC-1, AC-2, AC-5의 `exercises.py check` 실행
- [ ] `npm --prefix web/frontend test` 세 셸
- [ ] `py -3 .agent/scripts/lint_docs.py`

## History / Amendments
