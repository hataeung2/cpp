# C++ Evolution: 목차

`atugcc`를 구현하며 익힌 C++ 기능을, 예전 방식(C++11/14/17)에서 C++20/23 방식으로 어떻게 바뀌었는지 중심으로 정리한 페이지들의 목차입니다. 같은 내용을 플레이그라운드 레슨으로 직접 돌려 볼 수 있습니다.

- 페이지는 [`docs/cpp_evolution/`](/docs/cpp_evolution/)에 주제마다 두 벌 있습니다: `<주제>.md`(한국어), `<주제>.en.md`(영어). English: [cpp_evolution.en.md](/docs/cpp_evolution.en.md).
- 페이지마다 보통 **Why → 예전 방식 → C++20 → C++23 → atugcc에서는** 순서입니다.
- 프로젝트 전체 구조와 방향: [project_blueprint.md](/docs/guides/project_blueprint.md). 앞으로 만들 레슨 주제: [lesson_candidates.md](/docs/lesson_candidates.md).

## 1. essentials 트랙 순서로 보기
레슨 순서(`lessons/tracks/01_essentials/`)대로 읽으면 문법 → core 기능(시간, 파일) → 스레드·로그 → 모듈 → 테스트로 이어집니다. 페이지가 없는 레슨은 레슨 README가 설명을 맡습니다.

| # | 레슨 | 예전 방식 → 지금 방식 | 해설 페이지 | atugcc 코드 |
|---|---|---|---|---|
| 01 | [`lambda_capture`](/lessons/tracks/01_essentials/01_lambda_capture/README.md) | 함수 객체 → 람다, 캡처 방식 | — | 유닛 `lambda_capture` |
| 02 | [`format_text`](/lessons/tracks/01_essentials/02_format_text/README.md) | `printf`/`iostream` → `std::format`(C++20), `std::print`(C++23) | [format.md](/docs/cpp_evolution/format.md) | `Logger::log`의 `std::format_string` |
| 03 | [`const_correctness`](/lessons/tracks/01_essentials/03_const_correctness/README.md) | 반환 타입의 `const` vs `const` 멤버 함수, deducing this(C++23) | [const_return_type.md](/docs/cpp_evolution/const_return_type.md) | — |
| 04 | [`error_expected`](/lessons/tracks/01_essentials/04_error_expected/README.md) | 예외·조용한 실패 → `std::optional` → `std::expected`(C++23) | [error_expected.md](/docs/cpp_evolution/error_expected.md) | `core/error.hpp` |
| 05 | [`source_location`](/lessons/tracks/01_essentials/05_source_location/README.md) | `__FILE__`/`__LINE__` 매크로 → `std::source_location`, `std::osyncstream` | [source_location.md](/docs/cpp_evolution/source_location.md) | `FormatWithLocation` (`logger.hpp`) |
| 06 | [`concepts`](/lessons/tracks/01_essentials/06_concepts/README.md) | SFINAE(`enable_if`) → concepts, `requires` | [concepts.md](/docs/cpp_evolution/concepts.md) | `observer.hpp`, `ring_buffer.hpp` |
| 07 | [`ranges_views`](/lessons/tracks/01_essentials/07_ranges_views/README.md) | raw loop·반복자 → `std::ranges`, 뷰 파이프라인 | — | — |
| 08 | [`variant_visit`](/lessons/tracks/01_essentials/08_variant_visit/README.md) | 가상 함수 → `std::variant` + `std::visit` | — | `state.hpp` |
| 09 | [`chrono_time`](/lessons/tracks/01_essentials/09_chrono_time/README.md) | `time_t`/`struct tm` → `std::chrono` 달력·시간대 + `std::format` | [chrono_format.md](/docs/cpp_evolution/chrono_format.md) | `TimeStamp` |
| 10 | [`filesystem_paths`](/lessons/tracks/01_essentials/10_filesystem_paths/README.md) | 문자열·플랫폼 API → `std::filesystem`, `clock_cast`(C++20) | [filesystem.md](/docs/cpp_evolution/filesystem.md) | `MemoryDump::ensurePrepared` |
| 11 | [`thread_and_log`](/lessons/tracks/01_essentials/11_thread_and_log/README.md) | `std::thread` → `std::jthread` + `std::stop_token` | — | 유닛 `jthread_worker` |
| 12 | [`log_recovery`](/lessons/tracks/01_essentials/12_log_recovery/README.md) | 비정상 종료에 사라지는 로그 → 메모리 매핑 버퍼와 복구 | [lock_free_logging.md](/docs/cpp_evolution/lock_free_logging.md) §메모리 매핑 | `configureLogBuffers`, `recoverLogMaps` |
| 13 | [`lock_free_buffer`](/lessons/tracks/01_essentials/13_lock_free_buffer/README.md) | 잠금 하나를 쓰는 Logger → 스레드별 SPSC 버퍼 + 소비자 하나 | [lock_free_logging.md](/docs/cpp_evolution/lock_free_logging.md), 옛 구조 [modern_ring_buffer_architecture.md](/docs/cpp_evolution/modern_ring_buffer_architecture.md) | `detail::ThreadLogBuffer` |
| 14 | [`span_timing`](/lessons/tracks/01_essentials/14_span_timing/README.md) | 손으로 재는 시간 → Tracer span과 집계 | — | `ScopedSpan` (`visualizer.hpp`) |
| 15 | [`modules`](/lessons/tracks/01_essentials/15_modules/README.md) | `#include` → C++20 이름 있는 모듈, `import std`(C++23) | [modules.md](/docs/cpp_evolution/modules.md) | `modules/atugcc/core.cppm` |
| 16 | [`testing`](/lessons/tracks/01_essentials/16_testing/README.md) | GoogleTest 단위 테스트, 단계 시나리오, CTest, 테스트 리포트 | [source_location.md](/docs/cpp_evolution/source_location.md) 끝(테스트 매크로) | `tests/`, `atugcc::test::Scenario` |

## 2. 레슨이 아직 없는 페이지
| 페이지 | 예전 방식 → 지금 방식 | atugcc 코드 |
|---|---|---|
| [designated_initializers.md](/docs/cpp_evolution/designated_initializers.md) | 위치 기반 집합체 초기화·빌더 → 지정 초기화(C++20) | `DiagramBudget` (`visualizer.hpp`). 레슨 후보: 021-02 Builder |

## 3. 옛 구조의 기록
| 페이지 | 내용 |
|---|---|
| [modern_ring_buffer_architecture.md](/docs/cpp_evolution/modern_ring_buffer_architecture.md) | 010-09 전의 Logger: 스레드별 128바이트 고정 블록 `RingBuffer`와 전역 `boost::lockfree::spsc_queue`. 지금 구조는 [lock_free_logging.md](/docs/cpp_evolution/lock_free_logging.md) |

## 4. 페이지를 더하거나 고칠 때
- 예전 패턴을 C++20/23으로 바꾸는 작업은 `docs/cpp_evolution/`에 페이지를 쓰거나 고칩니다([impl.md](/.agent/rules/impl.md) §6 Reference docs). 두 언어를 함께 쓰고, 이 목차와 [`cpp_evolution.en.md`](/docs/cpp_evolution.en.md)에 줄을 더합니다.
- 두 판은 같은 제목 구조와 같은 수의 코드 블록을 가집니다. 문서 게이트(`lint_docs.py`)가 짝이 없거나 모양이 다르면 경고합니다.
- 한국어 판은 한국어 레슨 README와 한국어 페이지로, 영어 판은 `README.en.md`와 `.en.md`로 링크합니다.
