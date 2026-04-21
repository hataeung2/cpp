# Spec: Dedicated Console Output Control for Tracer

## Objective
atugcc::pattern::viz Tracer의 기록 기능은 유지하면서, 애플리케이션이 tracer 출력 경로를 별도 채널로 라우팅하고 런타임에 on/off 제어할 수 있는 전용 콘솔 출력 기능을 추가한다. 이 기능은 디버깅/학습 환경에서는 즉시 가시성을 제공하고, 일반 실행 환경에서는 출력 비용을 제어하는 것을 목표로 한다.

## Requirement Details

### Public API Surface
- `include/atugcc/pattern/` 영역에 tracer 출력용 sink 인터페이스를 정의한다.
- `Tracer`에 선택적 출력 경로를 설정할 수 있는 API를 추가한다.
- 출력 on/off 상태를 런타임에 제어할 수 있어야 한다.
- 기존 API(`record_message`, `record_transition`, `push_node`, `format_terminal`, `format_diagram`)는 시그니처 호환을 유지한다.

### Internal Implementation
- Tracer의 기록(record)과 출력(emit)을 분리한다.
- 출력 emit은 tracer 내부 write lock 구간 밖에서 수행한다.
- 출력 비활성화 시 경량 no-op 경로로 동작한다.
- sink 미설정 시 기존과 동일하게 기록만 수행한다.

### Platform Specifics
- Linux(GCC)에서는 표준 출력 스트림 기반 전용 콘솔 채널을 제공한다.
- Windows(MSVC)에서는 기존 ANSI 활성화 유틸리티(`enable_windows_ansi`)와 호환되어야 한다.
- OS별 새 콘솔 창 생성은 이번 범위에서 제외한다.

## C++ Standard Evolution (if applicable)
| Approach | Standard | Description |
|----------|----------|-------------|
| Legacy | C++11/14/17 | 호출자 분기 또는 직접 출력 호출 중심 제어 |
| Modern | C++20 | 출력 sink 추상화 + 런타임 토글 + 명시적 스레드 안전 경계 |
| Latest | C++23 | `std::expected` 기반 오류 모델과 결합한 출력 경로 명시화 |

Reference: `/docs/cpp_evolution/trace_console_toggle.md`

## Edge Cases
- [ ] Thread safety: 다중 스레드 동시 기록 시 출력 경쟁/교착 방지
- [ ] Resource lifetime / RAII: sink 생명주기와 tracer 참조 무효화 방지
- [ ] Platform differences (MSVC vs GCC): ANSI/버퍼링/개행 동작 차이
- [ ] Template instantiation: sink 제네릭 확장 시 제약 기반 설계 검증
- [ ] ODR violations: 헤더 온리 inline 확장 시 중복 정의 방지

## Dependencies & Adapters
- 외부 라이브러리 의존성 추가 없이 표준 C++로 구현한다.
- 콘솔 출력은 sink 인터페이스 뒤로 숨겨 adapter 형태를 유지한다.

## Technical Constraints
- Compiler: MSVC (VS 2026) / GCC (latest stable)
- CMake: 3.26+
- C++ Standard: C++23 (C++20 minimum)

## Context & References
- [Pattern Visualizer Spec](/docs/specs/08_pattern_visualizer.md)
- [Tracer Header](/include/atugcc/pattern/visualizer.hpp)
- [Terminal Formatter](/include/atugcc/pattern/detail/terminal_formatter.hpp)
- [Pattern Example](/src/pattern/example_visualizer.cpp)
- [Visualizer Tests](/tests/pattern/test_visualizer.cpp)

## Implementation Plan
- [ ] Step 1: 출력 sink 인터페이스/콘솔 sink 설계
- [ ] Step 2: Tracer에 sink 연결점과 on/off 토글 API 추가
- [ ] Step 3: 기록 경로와 출력 경로 락 경계 분리
- [ ] Step 4: 예제에서 on/off 시나리오 반영
- [ ] Step 5: sink 미설정/비활성/동시성 테스트 추가

## Verification Plan
- [ ] CMake build: `cmake --build --preset <buildPreset> --config <CMAKE_BUILD_TYPE>`
- [ ] Tests: `ctest --test-dir "<binaryDir>" -C <CMAKE_BUILD_TYPE> --output-on-failure`
- [ ] 전용 콘솔 on/off 수동 확인: pattern example 실행 로그 비교
- [ ] Zero warnings at `/W3` (MSVC) or `-Wall` (GCC)