# Plan — Pattern Visualizer (Phase 2.0)

## Target Task
- Phase 2.0: 패턴 시각화 도구 구현 (atugcc::pattern::visualizer)
- Spec: /docs/specs/08_pattern_visualizer.md

## Design Decisions (Confirmed Before Implementation)
- Namespace: `atugcc::pattern` (기존 `astate::`, `observer::` 등 즉시 전환)
- Tracer 역할 분리: Tracer는 문자열만 생성, 출력 책임은 호출자/Logger가 담당

## File Change Plan

### New Files
- [NEW] `/include/atugcc/pattern/visualizer.hpp`
  — Tracer 코어, EventSink concept, Message/Transition/Node 이벤트 타입, 전역 싱글톤 접근자
- [NEW] `/include/atugcc/pattern/detail/terminal_formatter.hpp`
  — ANSI 컬러 출력, ASCII 트리(`├─`, `└─`), 상태 흐름(`──▶`) 포맷터
  — `Tracer::format_terminal()` inline 구현 포함
- [NEW] `/include/atugcc/pattern/detail/d2_formatter.hpp`
  — message/state/structure 흐름용 D2 스니펫 생성기
  — `Tracer::format_d2()` inline 구현 포함
- [NEW] `/tests/pattern/test_visualizer.cpp`
  — 5개 테스트 그룹, 21개 케이스 (TracerTest, TerminalFmtTest, D2FmtTest, StateMachineTest, ObserverTest)
- [NEW] `/src/pattern/example_visualizer.cpp`
  — Demo 3개: State machine / Observer / Decorator tree

### Rewritten Files
- [MODIFY] `/include/atugcc/pattern/state.hpp`
  — 기존 `astate::` + 가상함수 → `atugcc::pattern::state` + `std::variant`+`std::visit`으로 완전 재작성
  — Tracer hook 연동: `schedule()`, `transition()` 호출 시 자동 기록
- [MODIFY] `/include/atugcc/pattern/observer.hpp`
  — 기존 `observer::` + 가상함수 → `atugcc::pattern::observer` + Concept 기반으로 완전 재작성
  — Tracer hook 연동: `notify_observers()` 호출 시 자동 기록

### Build Integration
- [MODIFY] `/CMakeLists.txt`
  — `atugcc_pattern_example` 실행 타깃 추가
  — MSVC `/utf-8` 컴파일 플래그 추가 (`atugcc_headers` INTERFACE)
- [MODIFY] `/tests/CMakeLists.txt`
  — `TEST_SOURCES`에 `../tests/pattern/test_visualizer.cpp` 추가

## C++23 Features Applied
| Feature | 사용 위치 |
|---|---|
| `std::variant` + `std::visit` | `state.hpp` 상태 머신 |
| `std::expected<T, E>` / `core::Result` | `visualizer.hpp` record_* 반환 타입 |
| Concepts (`EventSink<T, Event>`, `ObserverOf<T>`) | `visualizer.hpp`, `observer.hpp` |
| `std::shared_mutex` (shared/unique lock) | `Tracer` 스레드 안전 읽기/쓰기 분리 |
| `std::source_location` | `EventMeta` 호출 위치 캡처 |
| `std::format` | 전 파일 문자열 포맷팅 |
| `std::println` | `example_visualizer.cpp` 출력 |
| `std::ranges::sort`, `unique`, `any_of`, `binary_search` | formatter 중복 제거 로직 |
| `std::erase_if` | 만료 구독자 제거 (`observer.hpp`) |
| Designated Initializers | `EventMeta` 초기화 |
| CTAD (Class Template Argument Deduction) | `overloaded<Ts...>` 헬퍼 |

## Legacy Pattern Evolution
- `astate::` 가상함수 계층 → `atugcc::pattern::state` variant 기반 상태 머신
- `observer::` 가상함수 계층 → `atugcc::pattern::observer` Concept 기반 옵저버
- 관련 C++ Evolution 문서: `/docs/cpp_evolution/` (State/Observer 항목은 향후 추가 예정)
