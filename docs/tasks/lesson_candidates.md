# 레슨 후보 목록

웹 플레이그라운드 레슨으로 만들 주제 목록이다. 옛 Phase 5(C++ Evolution 문서, 050-01 ~ 050-06), KI-001의 빠진 evolution 페이지, 기존 학습 문서를 한곳에 모았다(090-05, 2026-10-29).

- 레슨을 만드는 작업이 후보를 고르고, 다 만들면 **상태**를 바꾼다. essentials는 070-03, patterns는 각 패턴 작업(021–024)과 070-04가 맡는다.
- 레슨 하나는 "예전 방식 → C++20/23 방식"의 비교를 담을 수 있다. 비교 설명은 레슨 README에 쓰고, 오래 남길 해설은 `docs/cpp_evolution/<topic>.md`에 둔다. KI-001의 빠진 페이지는 이렇게 채운다.
- 유닛(`lessons/units/`)은 여러 레슨이 같이 쓴다. 새 유닛을 만들기 전에 아래 "기존 자료"부터 확인한다.
- 상태: `후보`, `일부`(관련 유닛이나 문서가 있음), `레슨 있음`.

## Essentials 트랙 (070-03)
| # | 주제 | 비교 | 출처 | 기존 자료 | 선행 | 상태 |
|---|---|---|---|---|---|---|
| E1 | 템플릿 제약 | SFINAE(`enable_if`) → concepts | 050-01, KI-001 `concepts.md` | `observer.hpp`의 concept 주석 | — | 후보 |
| E2 | 문자열 포맷팅 | `iostream`·`printf`·fmt → `std::format`, `std::print` | 050-02, KI-001 `filesystem_format.md` | `TimeStamp`, `MemoryDump` | — | 후보 |
| E3 | 스레드 수명과 중단 | `std::thread` + 플래그 → `std::jthread` + `stop_token` | 050-03 | 유닛 `jthread_worker`, 레슨 `02_thread_and_log` | — | 일부 |
| E4 | 오류 처리 | 예외 → `std::expected` | 050-04 | [`error_expected.md`](/docs/cpp_evolution/error_expected.md), `core/error.hpp` | — | 일부 |
| E5 | 순회와 뷰 | raw loop → `std::ranges`, 뷰 파이프라인 | 050-05 | 023-05 Iterator와 같이 다룰 수 있음 | — | 후보 |
| E6 | 다형성 | 가상 함수 → `std::variant` + `std::visit` | 050-06 | `state.hpp`, 레슨 `02_patterns/01_device_state_machine` | — | 일부 |
| E7 | 호출 위치 기록 | `__FILE__`·`__LINE__` 매크로 → `std::source_location` | 010-04, KI-001 `source_location.md` | `Logger::log`, `ScopedSpan`(`span_timing.hpp`), [`source_location.md`](/docs/cpp_evolution/source_location.md) | — | 일부 |
| E8 | 시간 다루기 | C 시간 함수 → `std::chrono` + format | [`chrono_format.md`](/docs/cpp_evolution/chrono_format.md) | `TimeStamp` | — | 일부 |
| E9 | 파일 시스템 | 플랫폼 API → `std::filesystem` | KI-001 `filesystem_format.md` | `MemoryDump`(dump 디렉터리) | — | 후보 |
| E10 | 람다 캡처 | 함수 객체 → 람다, 캡처 방식 | — | 유닛 `lambda_capture`, 레슨 `01_lambda_capture` | — | 레슨 있음 |
| E11 | 구간 시간 측정 | 수동 시계 → RAII span, `SpanMeter` | 020-06 | 레슨 `03_span_timing` | — | 레슨 있음 |
| E12 | lock-free 링 버퍼 | mutex 큐 → lock-free 링 버퍼 | [`modern_ring_buffer_architecture.md`](/docs/learning/modern_ring_buffer_architecture.md) | `RingBuffer` | — | 일부 |
| E13 | 로그와 crash dump | printf 디버깅 → 링 버퍼 로그, 즉시 dump와 심볼화 | 010-06, 010-07 | `Logger`, `MemoryDump`, `tools/symbolize_dump.py` | — (다른 스레드 버퍼까지 담기는 010-09) | 후보 |
| E14 | `const`의 위치 | 반환 타입 `const` vs `const` 멤버 함수 | [`const_return_type_guide.md`](/docs/learning/const_return_type_guide.md) | — | — | 후보 |

## Patterns 트랙 (021–024, 070-04)
패턴별 레슨은 각 패턴 작업이 만든다([agent_todo.md](/docs/tasks/agent_todo.md)의 "작업 공통 원칙"). 여기에는 패턴 작업에 묶이지 않은 주제만 적는다.

| # | 주제 | 비교 | 출처 | 기존 자료 | 선행 | 상태 |
|---|---|---|---|---|---|---|
| P1 | 옵션 구조체 | 긴 인자 목록·setter → designated initializers | [`designated_initializers.md`](/docs/cpp_evolution/designated_initializers.md) | `DiagramBudget` | 021-02 Builder와 같이 | 일부 |
| P2 | double dispatch | 가상 함수 두 번 → `std::visit` 두 인자 | — | `sample/double_dispatch.hpp`, `tests/test_double_dispatch.cpp` | 070-04 (샘플 이전) | 일부 |
| P3 | 조건 변수 동기화 | busy wait → `std::condition_variable` | — | `sample/cond_var.hpp` | 070-04 (샘플 이전) | 일부 |

## 레슨보다 문서가 맞는 것
| 주제 | 출처 | 이유 |
|---|---|---|
| CMake 현대화 (target 기반, presets) | KI-001 `cmake_modernization.md` | 플레이그라운드는 빌드 설정을 숨긴다. 필요하면 `docs/cpp_evolution/`에 문서로 쓴다 |
| 전용 콘솔 on/off | KI-001 `trace_console_toggle.md` | 웹에서는 콘솔 대신 페이지가 출력을 보여 준다. 로컬 CLI 문서로 충분하다 |
