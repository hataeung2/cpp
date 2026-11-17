---
id: 070-18
title: essentials `thread_and_log` 보강 (예전 방식 비교, stop_callback, evolution 페이지, 과제 정의)
depends_on: [070-17]
unblocks: []
approved: 2026-11-10
---

# Spec 070-18: essentials `thread_and_log` 보강 (예전 방식 비교, stop_callback, evolution 페이지, 과제 정의)

## 0. Assumptions (please review)
| # | Decision | Rejected alternative | Why |
|---|---|---|---|
| 1 | **범위**: 레슨 `thread_and_log`(`11_thread_and_log`)를 다른 essentials 레슨의 형식으로 맞춘다. (a) 코드에 "예전 방식" 단계와 `std::stop_callback` 단계를 더함, (b) README 두 판을 "예전 방식과 C++20 / 실행 / 볼 것 / 연습" 형식으로 다시 씀, (c) `docs/cpp_evolution/jthread_stop_token.md`와 `.en.md`, (d) 070-17 형식의 `exercises.toml`, (e) [`lesson_candidates.md`](/docs/lesson_candidates.md) E3 상태 `일부` → `레슨 있음` | 새 레슨을 따로 | 후보 목록에서 이 레슨만 `일부`다. 비교(`std::thread` + 플래그 → `std::jthread` + `stop_token`)가 없고 evolution 페이지(옛 050-03)가 없으며, README의 실행 경로(`bin\lessons\…`)가 지금의 `out/build/<preset>/bin/lessons/`와 다르다. 레슨 id·폴더·태그는 그대로 둔다 |
| 2 | **"예전 방식" 단계는 실제로 돈다**: 레슨 폴더의 `legacy_worker.hpp`에 `LegacyWorker`(`std::thread` + `std::atomic<bool> stop_` + `std::this_thread::sleep_for(period)` 루프, 소멸자에서 `stop_ = true; join()`). 주기 100ms로 돌리고 `requestStop()`부터 스레드가 끝날 때까지 걸린 시간을 잰다. 이어서 같은 주기의 `PeriodicWorker`(기존 유닛)도 잰다. 출력은 `legacy stop took <n> ms (period 100 ms)`와 `jthread stop took <n> ms` | 예전 방식을 README 코드 블록으로만 | 차이(예전 방식은 정지를 다음 깨어남까지 모름, 최대 한 주기)를 직접 보아야 기억에 남는다. `chrono_time`, `error_expected`처럼 비교를 실행으로 보인다. 측정값은 실행마다 다르므로 출력은 값만 찍고 판정하지 않는다 |
| 3 | **`std::thread`를 join하지 않으면 `std::terminate`**는 실행하지 않고 주석과 README로만 보인다. 연습 과제 하나가 그것을 해 보게 한다(관찰 과제, 웹에서는 종료 코드가 0이 아님) | 단계로 실행 | 프로그램이 끝나 버려 뒤 단계가 돌지 않는다. 과제로 두면 사용자가 연습 사본(070-16)에서 해 보고 되돌린다 |
| 4 | **`std::stop_callback` 단계**: `std::stop_source`와 `std::stop_callback`으로 "정지 요청 때 한 번 불리는 함수"를 보인다(콜백이 요청한 스레드에서 바로 돈다는 것, 이미 요청된 뒤 등록하면 등록하는 자리에서 바로 돈다는 것, 두 경우를 찍음). `PeriodicWorker`는 바꾸지 않는다 | `PeriodicWorker`에 `stopToken()` 접근자를 더함 | 유닛은 `device_state_machine`도 쓴다. 유닛 API를 넓히지 않고 표준 기능만으로 보일 수 있다 |
| 5 | **기존 내용(기능별 Logger, `flush()`, 틱 수)은 마지막 단계로 그대로** 둔다. 출력의 단계 머리줄은 `== Step N: … ==` | 다시 씀 | 기존 연습 4개가 이 내용을 쓴다. 바꾸지 않아야 과제 정의(070-17)를 그대로 붙인다 |
| 6 | **실행 시간**: 전체 1초 안(예전 방식 최대 100ms + jthread + 기존 200ms). `quick` 프로필 그대로. sanitizer preset에서도 10초 안 | 주기 1초로 차이를 더 크게 | quick 제한(10초)과 smoke test 시간을 지킨다. 100ms면 차이가 충분히 보인다 |
| 7 | **evolution 페이지 이름은 `jthread_stop_token.md`**(+ `.en.md`), 목차 [`docs/cpp_evolution.md`](/docs/cpp_evolution.md)와 영어 목차에 한 줄 | `thread.md` | 다루는 것이 스레드 전부가 아니라 수명과 협력적 정지다(E3 주제) |
| 8 | **과제**: 기존 4개를 남기고 새 과제 2개를 더한다. (5) `LegacyWorker`의 주기를 500ms로 바꿔 정지 시간이 어떻게 되는지(자동: `expect = legacy stop took \d+ ms \(period 500 ms\)`, `source.has = 500`), (6) `LegacyWorker` 소멸자의 `join()`을 지워 보기(관찰, Assumption 3). 기존 과제 1(주기 10/50ms)은 자동(`source.has`, `exit = 0`), 2·3·4는 관찰 또는 `source` 규칙(DEV에서 정함) | 기존 과제를 바꿈 | 기존 과제는 기능별 Logger를 연습한다. 새 과제가 비교 단계를 연습한다 |
| 9 | 태그: `thread`의 별칭에 `jthread`, `stop_token`, `stop_callback`, `std::thread`가 없으면 더한다(`lessons/tags.toml`) | 새 태그 | 검색(070-10)으로 찾혀야 한다. 같은 낱말이 다른 태그에 없는지 확인 |
| 10 | 070-03 규칙: 출력 영어, 주석은 한국어 줄 + 영어 줄, 두 preset에서 경고 없이 빌드, 플랫폼 전용 API 없음 | — | 070-03 Assumption 9·10·12 |

## 1. Objective
essentials 트랙에서 `thread_and_log`만 "예전 방식 → C++20" 비교가 없고 해설 페이지가 없다. 이 작업은 `std::thread` + 플래그 + `sleep_for`로 만든 예전 워커와 `std::jthread` + `stop_token` + `condition_variable_any`로 만든 워커의 정지 시간을 실제로 재어 보이고, `std::stop_callback`을 더하고, README와 evolution 페이지를 다른 레슨과 같은 형식으로 쓰고, 070-17 형식의 과제 정의를 붙인다.

## 2. Requirement Details

### 2.1 Public API Surface
라이브러리 API 변경 없음. 유닛 `jthread_worker` 변경 없음.

### 2.2 Internal Implementation
| 파일 | 바꾸는 것 |
|---|---|
| `lessons/tracks/01_essentials/11_thread_and_log/legacy_worker.hpp` (새) | `namespace thread_and_log_lesson { class LegacyWorker }`(Assumption 2). 생성자에서 `std::thread`, `requestStop()`은 `stop_.store(true)`, 소멸자는 `requestStop(); if (joinable) join();`. 주석: 왜 최대 한 주기, join을 잊으면 `std::terminate`, 이동 대입이 `joinable`인 스레드를 덮으면 역시 terminate |
| `main.cpp` | Step 1 예전 방식 정지 시간, Step 2 jthread 정지 시간, Step 3 `stop_callback` 두 경우, Step 4 지금의 내용. 시간은 `steady_clock`, ms로 반올림 |
| `lesson.toml` | `sources = ["main.cpp", "legacy_worker.hpp"]`(헤더도 sources에 두어 웹에서 탭으로 열림, 070-15의 `version.hpp`와 같음), `summary` 두 언어에 비교 |
| `README.md`, `README.en.md` | 형식(Assumption 1), 비교 표(수명: 소멸자에서 terminate vs 자동 join, 정지: 플래그를 손으로 vs `stop_token`, 대기 중 깨우기: 불가 vs `wait_for(lock, token, …)`, 정지 때 할 일: 직접 호출 vs `stop_callback`), 실행(웹, 로컬 `build.py --target lesson_thread_and_log`, 경로 `out/build/<preset>/bin/lessons/`), 볼 것(단계별), 연습 6개 |
| `exercises.toml` (새) | Assumption 8 |
| `docs/cpp_evolution/jthread_stop_token.md` (새), `.en.md` | 예전 코드와 새 코드, 정지 시간의 이유, `stop_token` 세 도구(`stop_source`, `stop_token`, `stop_callback`), 멤버 선언 순서(`thread_` 마지막), 레슨 링크 |

### 2.3 Platform Specifics
- `sleep_for`와 조건 변수 깨우기의 정밀도는 OS마다 다르다(Windows 약 1–16ms). 출력은 값만 찍는다(판정 없음). 과제 5의 `expect`는 주기 숫자만 본다.
- TSan preset에서 `LegacyWorker`의 `stop_`은 `std::atomic<bool>`이라 경합이 없다(AC-3).

## 3. C++ Standard Evolution
| Approach | Standard | Description |
|----------|----------|-------------|
| Legacy | C++11/14/17 | `std::thread` + `std::atomic<bool>` 정지 플래그 + `sleep_for`. 소멸 때 `joinable`이면 `std::terminate`, 대기 중에는 정지를 모름(최대 한 주기 늦음), 정지 때 할 일은 직접 부름 |
| Modern | C++20 | `std::jthread`(소멸자가 `request_stop()` + `join()`), `std::stop_token`, `condition_variable_any::wait_for(lock, token, …)`(대기 중 정지 요청에 바로 깨어남), `std::stop_callback` |
| Latest | C++23 | N/A |

Reference: `/docs/cpp_evolution/jthread_stop_token.md` + `.en.md` (새, §8).

## 4. Edge Cases
- [x] Thread safety / memory ordering — `LegacyWorker::stop_`은 `std::atomic<bool>`(기본 `seq_cst`). 측정 시각은 메인 스레드가 `requestStop()` 전과 `join()` 뒤에 읽는다. `stop_callback`의 출력은 `std::cout` 한 줄씩이고, 그 시점에 다른 스레드가 `std::cout`을 쓰지 않게 단계를 나눈다(Logger 출력과 섞이지 않게 Step 4 전에 끝냄).
- [x] Resource lifetime / RAII — `LegacyWorker`의 스레드 함수는 `this`를 잡는다. 멤버 순서(`std::thread`가 마지막)와 소멸자의 join으로 다른 멤버보다 먼저 끝난다. `stop_callback`은 `stop_source`보다 짧게 산다.
- [x] Platform differences — §2.3.
- [x] Template instantiation / concept constraints — `stop_callback`의 콜백 타입 추론(CTAD). N/A otherwise.
- [x] ODR — `legacy_worker.hpp`의 함수는 클래스 안 정의(암묵적 inline).
- [x] Undefined behaviour — join 없이 끝내는 것은 실행하지 않는다(Assumption 3). 데이터 경합 없음(TSan, AC-3).

## 5. Acceptance Criteria
| ID | Criterion | Verified by |
|---|---|---|
| AC-1 | `lesson_thread_and_log`가 `windows-x64-debug`, `linux-x64-debug`에서 경고 없이 빌드되고 `lesson.thread_and_log`가 통과한다. 출력에 Step 1–4 머리줄, `legacy stop took … (period 100 ms)`, `jthread stop took …`, `stop_callback`의 두 경우, 기존 틱 수 줄이 있다 | 빌드 로그, `ctest -R lesson.thread_and_log`, 출력 발췌 |
| AC-2 | 10번 실행해 예전 방식의 정지 시간이 jthread보다 크고 주기(100ms)를 넘지 않는 것을 기록한다(판정은 사람, 레슨은 판정하지 않음) | 실행 기록(두 OS 중 하나 이상), testrecord |
| AC-3 | `linux-x64-asan`, `linux-x64-tsan`에서 `ctest -R lesson.thread_and_log`가 통과한다 | 명령 출력 |
| AC-4 | README 두 판이 다른 레슨의 형식(비교 표, 실행, 볼 것, 연습)을 갖고, 영어판은 한국어판과 절 제목 수·연습 수·코드 블록 수가 같다. 실행 경로가 지금의 빌드 경로다 | 070-03의 비교 스크립트, 읽기 확인 |
| AC-5 | `exercises.toml`이 `lessons.py check`를 통과하고(ERROR·WARN 0), 자동 과제는 해설대로 풀면 연습 공간에서 통과하며 원본은 통과하지 않는다(`exercises_verify`) | 070-17의 도구와 테스트, 풀이 기록 |
| AC-6 | `jthread_stop_token.md`와 `.en.md`가 있고 두 목차에 줄이 있으며, `lesson_candidates.md`의 E3가 `레슨 있음`이다. 검색 `jthread`, `stop_token`이 이 레슨을 찾는다 | `lint_docs.py`(evolution 쌍 검사), 헤드리스 브라우저 검색 |
| AC-7 | 전체 suite가 두 preset에서 통과하고 `lint_docs.py`가 exit 0이다 | 명령 출력 |

## 6. Out of Scope
- 유닛 `jthread_worker` API 변경 — 하지 않는다(Assumption 4)
- `std::latch`, `std::barrier`, `std::counting_semaphore` — 레슨 후보로 남기지 않았다. 필요하면 후보 목록에 새 행
- 스레드 풀, `std::async` — 다루지 않는다

## 7. Dependencies & Backends
없음.

## 8. Documentation Updates
| Document | Section | Change |
|---|---|---|
| `lessons/tracks/01_essentials/11_thread_and_log/README.md`, `README.en.md` | 전체 | 다시 씀(§2.2) |
| `docs/cpp_evolution/jthread_stop_token.md`, `.en.md` | 전체 | 새로 씀 |
| [`docs/cpp_evolution.md`](/docs/cpp_evolution.md), [`docs/cpp_evolution.en.md`](/docs/cpp_evolution.en.md) | 목차 | 한 줄 |
| [`docs/lesson_candidates.md`](/docs/lesson_candidates.md) | E3 행 | 출처에 evolution 페이지, 상태 `레슨 있음` |
| [`lessons/tags.toml`](/lessons/tags.toml) | `thread` | 별칭(Assumption 9) |
| [`lessons/units/jthread_worker/README.md`](/lessons/units/jthread_worker/README.md), `.en.md` | 쓰는 레슨 | 비교 단계가 생겼다는 한 줄(필요하면) |

## 9. Technical Constraints
- Compiler: MSVC (VS 2026) / Clang 20 with libstdc++ 14 (Linux)
- CMake: 4.0+
- C++ Standard: C++23 (C++20 minimum)

## 10. Context & References
- [`lessons/tracks/01_essentials/11_thread_and_log/main.cpp`](/lessons/tracks/essentials/thread_and_log/main.cpp), [`README.md`](/lessons/tracks/essentials/thread_and_log/README.md)
- [`lessons/units/jthread_worker/jthread_worker.hpp`](/lessons/units/jthread_worker/jthread_worker.hpp)
- 형식의 예: [`09_chrono_time/README.md`](/lessons/tracks/essentials/chrono_time/README.md), [070-03 스펙](/docs/specs/070_03_essentials_curriculum.md)
- [070-17 스펙](/docs/specs/070_17_exercise_check.md)(과제 정의 형식)

## 11. Implementation Plan
- [ ] Step 1: `legacy_worker.hpp`, `main.cpp`, `lesson.toml`
- [ ] Step 2: 두 OS, sanitizer 실행과 정지 시간 기록
- [ ] Step 3: README 두 판, evolution 페이지 쌍, 목차, 후보 목록, 태그
- [ ] Step 4: `exercises.toml`과 풀이 확인

## 12. Verification Plan
- [ ] `py -3 .agent/scripts/build.py --preset windows-x64-debug --test`, `--preset linux-x64-debug --test`
- [ ] `--preset linux-x64-asan`, `--preset linux-x64-tsan`의 `ctest -R lesson.thread_and_log`
- [ ] `py -3 tools/lessons.py check`, `lint_docs.py` exit 0
- [ ] 모든 AC 행의 증거가 `testrecord.md`에

## History / Amendments
- 2026-11-10: 초안
- 2026-11-10: 승인(사용자, 070-07·070-16·070-17·070-19와 함께)
