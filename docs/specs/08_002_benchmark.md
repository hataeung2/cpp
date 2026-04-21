# Spec: Benchmark Option for Pattern Tracer

## Objective
`atugcc::pattern::viz` tracer의 런타임 오버헤드를 측정할 수 있도록 벤치마크 옵션을 추가한다. 측정 결과는 환경 의존성을 고려해 pass/fail 임계값 없이 리포트 전용으로 제공하며, 개발자가 기능 변경 전후 성능 추이를 비교할 수 있게 한다.

## Requirement Details

### Public API Surface
- 기존 tracer 공개 API는 변경하지 않는다.
- 벤치마크는 별도 실행 타깃에서 tracer 공개 API를 호출해 측정한다.

### Internal Implementation
- 벤치마크 전용 실행 파일 타깃을 추가한다.
- 측정 시나리오를 최소 4가지로 구성한다.
  - `record_message` 반복 성능
  - `record_transition` 반복 성능
  - `push_node` 반복 성능
  - 전용 콘솔 output on/off 상태 비교
- 결과는 `ops/sec`, `avg ns/op` 중심으로 표준 출력에 리포트한다.

### Platform Specifics
- Linux(GCC) 및 Windows(MSVC)에서 동일 시나리오 실행이 가능해야 한다.
- 타이머 분해능 차이를 고려해 warm-up과 반복 횟수를 명시한다.

## C++ Standard Evolution (if applicable)
| Approach | Standard | Description |
|----------|----------|-------------|
| Legacy | C++11/14/17 | ad-hoc 로그/디버거 기반 수동 측정 |
| Modern | C++20 | `std::chrono` 기반 반복 측정과 시나리오 자동화 |
| Latest | C++23 | 표준 라이브러리 중심 리포트 파이프라인 정교화 |

Reference: `/docs/cpp_evolution/tracer_benchmarking.md`

## Edge Cases
- [ ] Thread safety: 단일/다중 스레드 측정 구분 및 공유 자원 경쟁 영향 분리
- [ ] Resource lifetime / RAII: 측정 중 객체 재사용/초기화 시점 일관성
- [ ] Platform differences (MSVC vs GCC): 타이머 정밀도/최적화 차이
- [ ] Template instantiation: 측정 헬퍼 제네릭화 시 인스턴스 폭증 관리
- [ ] ODR violations: 벤치 유틸 헤더 inline 정의 충돌 방지

## Dependencies & Adapters
- 외부 벤치 프레임워크를 필수 의존으로 추가하지 않는다.
- 프로젝트 표준 CMake + 표준 라이브러리로 벤치 타깃을 구성한다.

## Technical Constraints
- Compiler: MSVC (VS 2026) / GCC (latest stable)
- CMake: 3.26+
- C++ Standard: C++23 (C++20 minimum)

## Context & References
- [Pattern Visualizer Spec](/docs/specs/08_pattern_visualizer.md)
- [Tracer Header](/include/atugcc/pattern/visualizer.hpp)
- [Pattern Example](/src/pattern/example_visualizer.cpp)
- [Visualizer Tests](/tests/pattern/test_visualizer.cpp)
- [Root CMake](/CMakeLists.txt)

## Implementation Plan
- [ ] Step 1: CMake에 벤치 타깃 옵션(예: `ATUGCC_BUILD_BENCHMARKS`) 정의
- [ ] Step 2: tracer 벤치 실행 파일 추가 및 시나리오 구현
- [ ] Step 3: 결과 리포트 형식(`ops/sec`, `ns/op`) 정규화
- [ ] Step 4: output on/off 비교 시나리오 포함
- [ ] Step 5: 문서화(실행 명령, 해석 가이드, 환경 유의사항)

## Verification Plan
- [ ] CMake configure/build with benchmark option ON
- [ ] Benchmark executable run and report generation
- [ ] 기존 테스트 스위트 회귀 없음 확인
- [ ] Zero warnings at `/W3` (MSVC) or `-Wall` (GCC)
