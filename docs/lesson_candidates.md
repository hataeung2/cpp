# 레슨 후보 목록

웹 플레이그라운드 레슨으로 만들 주제 목록이다. 옛 Phase 5(C++ Evolution 문서, 050-01 ~ 050-06), KI-001의 빠진 evolution 페이지, 기존 학습 문서를 한곳에 모았다(090-05, 2026-10-29).

- 레슨을 만드는 작업이 후보를 고르고, 다 만들면 **상태**를 바꾼다. essentials는 070-03, patterns는 각 패턴 작업(021–024)과 070-04, OOP 입문은 070-21이 맡는다.
- 레슨 하나는 "예전 방식 → C++20/23 방식"의 비교를 담을 수 있다. 비교 설명은 레슨 README에 쓰고, 오래 남길 해설은 `docs/cpp_evolution/<topic>.md`(한국어)와 `<topic>.en.md`(영어)에 두고 목차 [`docs/cpp_evolution.md`](/docs/cpp_evolution.md)에 줄을 더한다(090-07). KI-001의 빠진 페이지는 이렇게 채운다.
- 유닛(`lessons/units/`)은 여러 레슨이 같이 쓴다. 새 유닛을 만들기 전에 아래 "기존 자료"부터 확인한다.
- 상태: `후보`, `일부`(관련 유닛이나 문서가 있음), `레슨 있음`.
- 새 레슨은 영어 필드(`title_en`, `summary_en`)와 [`lessons/tags.toml`](/lessons/tags.toml)의 태그를 쓰고, 프로그램 출력은 영어로 쓴다([070-10](/docs/specs/070_10_lesson_search_i18n.md) Assumption 14). 레슨과 유닛마다 `README.en.md`를 두고(없으면 `lessons.py check`가 경고, 070-03), 코드 주석은 한국어 줄 다음에 같은 뜻의 영어 줄을 둔다(070-03 Assumption 12).
- 새 레슨은 README "연습" 항목마다 `exercises.toml`에 과제를 정의한다([lessons/README.md](/lessons/README.md) "연습 과제 정의", 070-17).

## Essentials 트랙 (070-03)
폴더 번호는 트랙 안의 최종 순서다(070-03 Assumption 2·3): 문법 → core 기능(시간, 파일) → 스레드·로그 → 모듈 → 테스트. 지금은 `01_`–`16_`이 모두 있어 비어 있는 번호가 없다. 새 레슨은 기존 폴더를 옮기지 않고 끝 번호 다음에 붙인다(`15_modules`, 070-14 Assumption 2; `16_testing`, 070-15 Assumption 2). 순서를 바꾸면 폴더를 옮겨야 하므로 사용자 결정이다.

| 폴더 | # | 주제 | 비교 | 출처 | 기존 자료 | 선행 | 상태 |
|---|---|---|---|---|---|---|---|
| `01_lambda_capture` | E10 | 람다 캡처 | 함수 객체 → 람다, 캡처 방식 | — | 유닛 `lambda_capture`, 레슨 `lambda_capture` | — | 레슨 있음 |
| `02_format_text` | E2 | 문자열 포맷팅 | `iostream`·`printf`·fmt → `std::format`, `std::print` | 050-02, KI-001 `filesystem_format.md` | 레슨 `format_text`, `TimeStamp`, `MemoryDump` | — | 레슨 있음 |
| `03_const_correctness` | E14 | `const`의 위치 | 반환 타입 `const` vs `const` 멤버 함수 | [`const_return_type.md`](/docs/cpp_evolution/const_return_type.md) | 레슨 `const_correctness` | — | 레슨 있음 |
| `04_error_expected` | E4 | 오류 처리 | 예외 → `std::expected` | 050-04 | 레슨 `error_expected`, [`error_expected.md`](/docs/cpp_evolution/error_expected.md), `core/error.hpp` | — | 레슨 있음 |
| `05_source_location` | E7 | 호출 위치 기록 | `__FILE__`·`__LINE__` 매크로 → `std::source_location` | 010-04, KI-001 `source_location.md` | 레슨 `source_location`, `Logger::log`, `ScopedSpan`(`span_timing.hpp`), [`source_location.md`](/docs/cpp_evolution/source_location.md) | — | 레슨 있음 |
| `06_concepts` | E1 | 템플릿 제약 | SFINAE(`enable_if`) → concepts | 050-01, [`concepts.md`](/docs/cpp_evolution/concepts.md) | 레슨 `concepts`, `observer.hpp`의 concept 주석 | — | 레슨 있음 |
| `07_ranges_views` | E5 | 순회와 뷰 | raw loop → `std::ranges`, 뷰 파이프라인 | 050-05 | 레슨 `ranges_views` (023-05 Iterator가 이 레슨을 링크할 예정) | — | 레슨 있음 |
| `08_variant_visit` | E6 | 다형성 | 가상 함수 → `std::variant` + `std::visit` | 050-06 | 레슨 `variant_visit`, `state.hpp`, 레슨 `02_patterns/01_device_state_machine`(태그 `variant`) | — | 레슨 있음 |
| `09_chrono_time` | E8 | 시간 다루기 | C 시간 함수 → `std::chrono` + format | [`chrono_format.md`](/docs/cpp_evolution/chrono_format.md) | 레슨 `chrono_time`, `TimeStamp` | — | 레슨 있음 |
| `10_filesystem_paths` | E9 | 파일 시스템 | 플랫폼 API → `std::filesystem` | [`filesystem.md`](/docs/cpp_evolution/filesystem.md) | 레슨 `filesystem_paths`, `MemoryDump`(dump 디렉터리) | — | 레슨 있음 |
| `11_thread_and_log` | E3 | 스레드 수명과 중단 | `std::thread` + 플래그 → `std::jthread` + `stop_token`, `stop_callback` | 050-03, [`jthread_stop_token.md`](/docs/cpp_evolution/jthread_stop_token.md) | 유닛 `jthread_worker`, 레슨 `thread_and_log`(예전 워커 `legacy_worker.hpp`) | — | 레슨 있음 |
| `12_log_recovery` | E13 | 로그와 crash dump | printf 디버깅 → 모든 스레드의 crash dump, 실패 유형별 보존, SIGKILL 뒤 다음 실행 때 복구(메모리 매핑 파일) | 010-06, 010-07, 010-09, 010-10 | 레슨 `log_recovery`, `Logger`, `MemoryDump`, `configureLogBuffers({.mappedDir})`, `recoverLogMaps`, `tools/read_dump.py`, `tools/symbolize_dump.py`, `tests/core/crash_probe.cpp`, `tests/core/log_map_probe.cpp` | — | 레슨 있음 |
| `13_lock_free_buffer` | E12 | lock-free 링 버퍼 | mutex 큐 → 스레드별 SPSC 버퍼 + 소비자 스레드 | [`modern_ring_buffer_architecture.md`](/docs/cpp_evolution/modern_ring_buffer_architecture.md)(옛 구조), [`lock_free_logging.md`](/docs/cpp_evolution/lock_free_logging.md) | 레슨 `lock_free_buffer`, `RingBuffer`, `detail::ThreadLogBuffer` (010-09) | — | 레슨 있음 |
| `14_span_timing` | E11 | 구간 시간 측정 | 수동 시계 → RAII span, `SpanMeter` | 020-06 | 레슨 `span_timing` | — | 레슨 있음 |
| `15_modules` | E15 | C++20 모듈 | `#include`·include guard·PCH → named module(인터페이스·파티션·구현 유닛) | 070-13 | 레슨 `modules`, `modules/atugcc/core.cppm`, `tests/modules/`, [`modules.md`](/docs/cpp_evolution/modules.md) | — | 레슨 있음 |
| `16_testing` | E16 | 테스트 작성과 리포트 | `assert`·손으로 쓴 `main` 검사 → GoogleTest 단위 테스트(fixture, 표 테스트), 단계 시나리오, CTest, 테스트 리포트 | 040-02 | 레슨 `testing`, [`tests/README.md`](/tests/README.md), [`scenario.hpp`](/tests/scenario/scenario.hpp), `.agent/scripts/test_report.py` | — | 레슨 있음 |

## OOP 입문 트랙 (070-21)
트랙 `03_oop_basics`(patterns 뒤, 맨 아래; 사용자 결정 2026-11-12). 독자는 변수, 함수, 반복문, `struct`는 아는데 클래스는 처음 쓰는 사람이고, 기초 문법(변수·제어문·포인터)은 가르치지 않는다. 이 트랙은 "예전 방식 → C++20/23"이 아니라 **"흔한 실수 → 바른 방식"**으로 쓰고, evolution 페이지는 만들지 않는다(070-21 Assumption 4·11). 폴더 번호는 최종 순서이고 후속 세 개의 번호는 비워 둔다.

| 폴더 | # | 주제 | 흔한 실수 → 바른 방식 | 선행 | 상태 |
|---|---|---|---|---|---|
| `01_class_basics` | O1 | 클래스와 캡슐화 | 모든 멤버 `public`, 초기화 안 한 멤버, 한 인자 생성자의 암시적 변환 → 불변식을 지키는 멤버 함수, 초기화 목록과 멤버 기본값, `explicit` | — | 레슨 있음 |
| `02_object_lifetime` | O2 | 객체의 수명: 생성·소멸·RAII | `new`/`delete` 짝 맞추기, 멤버 초기화·소멸 순서 착각 → 스코프가 수명을 정함, 소멸자에서 자원 해제(RAII) | — | 레슨 있음 |
| `03_copy_and_move` | O3 | 복사와 이동, Rule of 0/5 | 자원을 가진 클래스를 얕게 복사 → 복사·이동을 직접 쓰거나(`Rule of 5`) 쓰지 않고 멤버에게 맡김(`Rule of 0`), `= default`/`= delete` | — | 레슨 있음 |
| `04_inheritance_virtual` | O4 | 상속, 가상 함수, 추상 클래스 | 가상 소멸자 없음, 오버라이드 철자 틀림, 값으로 받아 슬라이싱 → `virtual ~Base`, `override`/`final`, 참조·포인터로 받기, 순수 가상 함수 | — | 레슨 있음 |
| `05_` | O5 | has-a 대 is-a (`composition`) | 코드 재사용을 위한 상속 → 합성과 위임, LSP를 어기는 `Square : Rectangle` | O4 | 후보 |
| `06_` | O6 | 소유권 (`smart_pointers`) | 날 포인터가 소유권을 숨김 → `unique_ptr`, `shared_ptr`/`weak_ptr`, `vector<unique_ptr<Base>>` | O2, O3 | 후보 |
| `07_` | O7 | 값 의미론, 연산자, 비교 (`value_semantics`) | 비교 연산자 6개 직접 쓰기 → `operator<=>` 기본 비교, 연산자 오버로딩의 기준 | O3 | 후보 |

## Patterns 트랙 (021–024, 070-04)
패턴별 레슨은 각 패턴 작업이 만든다([agent_todo.md](/docs/agent_todo.md)의 "작업 공통 원칙"). 여기에는 패턴 작업에 묶이지 않은 주제만 적는다.

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
