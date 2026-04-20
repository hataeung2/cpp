# Walkthrough — Pattern Visualizer (Phase 2.0)

## What Was Implemented

### Core: `visualizer.hpp`
- `atugcc::pattern::viz::Tracer` — 스레드 안전 이벤트 기록기
  - `record_message(from, to, action)` → `core::Result`
  - `record_transition(old_state, new_state, trigger)` → `core::Result`
  - `push_node(parent, child, relation_type)` → `core::Result`
  - `format_terminal()` → ANSI 컬러 ASCII 출력 문자열 반환
  - `format_diagram(backend=PlantUML)` → 기본 PlantUML 스니펫 반환
  - `format_plantuml()` / `format_mermaid()` / `format_d2()` → thin wrapper
  - `snapshot_messages() / snapshot_transitions() / snapshot_nodes()` — 테스트용 읽기
  - `clear()` — 버퍼 초기화
  - `static Tracer& global()` — Meyers Singleton
- `EventSink<T, Event>` concept — `sink.on_event(e)` 요구
- `get_global_tracer()` — 전역 싱글톤 편의 접근자
- `EventMeta` — `std::source_location` + `chrono::system_clock::time_point`

### Terminal Output: `detail/terminal_formatter.hpp`
- `namespace ansi` — `constexpr string_view` ANSI 색상 코드 12종
- `enable_windows_ansi()` — Win32 `ENABLE_VIRTUAL_TERMINAL_PROCESSING` 활성화
- `TerminalFormatter::format_messages()` — `[N] FROM ──▶ TO :: action()` 형식
- `TerminalFormatter::format_transitions()` — `[OLD] ──( trigger )──▶ [NEW]` 형식
- `TerminalFormatter::format_tree()` — `├─(rel)─▶ child` ASCII 계층 트리 (DFS 재귀)
- `Tracer::format_terminal()` — shared_lock 보호 후 세 포맷터 조합

### Diagram Backends
- PlantUML: `detail/plantuml_formatter.hpp`
  - `PlantUMLFormatter::sequence_diagram()` / `state_diagram()` / `class_tree()`
  - `Tracer::format_diagram()` 기본 디스패치 대상
- Mermaid: `detail/mermaid_formatter.hpp`
  - `MermaidFormatter::sequence_diagram()` / `state_diagram()` / `class_tree()`
  - `Tracer::format_diagram(DiagramBackend::Mermaid)` 또는 `format_mermaid()`
- D2: `detail/d2_formatter.hpp`
  - `D2Formatter::message_flow()` / `state_flow()` / `structure_tree()`
  - `Tracer::format_diagram(DiagramBackend::D2)` 또는 `format_d2()`

### State Machine: `state.hpp` (전면 재작성)
- Namespace: `atugcc::pattern::state`
- `overloaded<Ts...>` 헬퍼 (CTAD 가이드 포함)
- 5개 상태 타입: `IdleState`, `StandbyState`, `RunState`, `AbortState`, `EmergencyState`
- `MachineStateVariant = std::variant<...>` 통합 상태
- `Machine::schedule()` — `std::visit`으로 현재 상태별 `Tracer::record_message()` 호출
- `Machine::transition(target)` — 이중 `std::visit` 전이 허용 매트릭스 검증 + Tracer 기록
- `Machine(viz::Tracer& = viz::get_global_tracer())` 생성자

### Observer Pattern: `observer.hpp` (전면 재작성)
- Namespace: `atugcc::pattern::observer`
- `ObserverOf<T>` concept — `on_notify(const Subject&)` + `display() → string` 요구
- `Subject` — `std::weak_ptr<void>` handle + `std::function` 콜백 (Entry struct)
  - `std::erase_if`으로 만료 구독자 자동 정리
- `subscribe<ObserverOf T>(Subject&, shared_ptr<T>, name)` 헬퍼 함수
- `DataObserver1`, `DataObserver2` 구체 구현 (`static_assert(ObserverOf<...>)` 검증)
- `Subject(viz::Tracer& = viz::get_global_tracer())` 생성자

### Example: `src/pattern/example_visualizer.cpp`
- Demo 1: State Machine (IDLE → STANDBY → RUN → ABORT, schedule 실행)
- Demo 2: Observer (Subject + 두 구독자 notify)
- Demo 3: Decorator tree (Deco2 → Deco1_outer → Deco1_inner → Product)
- 각 Demo는 독립 Tracer 사용, `format_terminal()` + `format_diagram()` 중심으로 출력

## API 사용 예시

```cpp
// 전역 Tracer 사용
auto& tracer = atugcc::pattern::viz::get_global_tracer();

// State Machine
atugcc::pattern::state::Machine machine{ tracer };
auto result = machine.transition(state::StandbyState{});
if (!result) { /* CoreError::InvalidArgument */ }

// Observer
atugcc::pattern::observer::Subject subject{ tracer };
auto obs = std::make_shared<observer::DataObserver1>();
observer::subscribe(subject, obs, "Observer1");
subject.set_data("key", "value"); // notify 자동 기록

// 출력
std::print("{}", tracer.format_terminal()); // ANSI 컬러 콘솔 출력
std::print("{}", tracer.format_diagram());  // 기본 PlantUML
std::print("{}", tracer.format_diagram(viz::DiagramBackend::Mermaid));
std::print("{}", tracer.format_diagram(viz::DiagramBackend::D2));
```

## Build Issues Resolved

| 문제 | 원인 | 해결 |
|---|---|---|
| `std::function` 미인식 | `observer.hpp`에 `#include <functional>` 누락 | 헤더 추가 |
| 한국어 주석 파싱 오류 (`U+2014` 등) | MSVC 기본 인코딩이 CP949 | `CMakeLists.txt`에 `/utf-8` 플래그 추가 |
| 블록 주석 조기 종료 | `test_visualizer.cpp` 상단 주석에 `record_*/snapshot_*/` 패턴 → `*/` 인식 | 주석 텍스트를 ASCII로 교체 |
| `format_tree()`에 relation_type 미출력 | `render_node()`에서 `rel` 변수 캡처 후 포맷에 미포함 | `─(rel)─▶` 형식으로 수정 |
| `[[nodiscard]]` 경고 다수 | `/W4` 플래그 + 반환값 미캡처 | 의도적 무시 위치에 `(void)` 캐스트 추가 |

## Verification
- Build: 성공 (MSVC 19.50.35726.0, `-std:c++latest`)
- Tests: **55/55 passed** (1 SKIPPED: POSIX-only `PosixDumpTest`)
- 자세한 테스트 로그: `/docs/tasks/feature_pattern-visualizer/testrecord.md`
