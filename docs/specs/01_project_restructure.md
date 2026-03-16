# Spec: 01_project_restructure

## Objective
기존 C++ 프로젝트(`cpp20samplecode`)의 구조를 `atugcc` 프레임워크 라이브러리 개발에 적합한 표준 구조로 재배치하고, CMake빌드 시스템을 최신 C++23 및 모던 CMake 문법에 맞게 개편합니다.

## Requirement Details

### Public API Surface
- 이 단계에서는 새로운 클래스나 함수를 추가하지 않습니다. 기존 헤더 파일들을 `include/atugcc/` 하위 디렉터리로 이동시켜 논리적인 트리 구조를 마련합니다.
  - `atugcc/core/`: 핵심 유틸리티 (로그, 시간 등)
  - `atugcc/pattern/`: 디자인 패턴 템플릿
  - `atugcc/adapter/`: 어댑터 인터페이스

### Internal Implementation  
- 소스 파일(`.cpp`, `.cppm`)들은 보이지 않는 내부 구현 디렉터리인 `src/`로 이동합니다.
  - `src/core/`, `src/pattern/`, `src/adapters/`

### Platform Specifics
- `CMakeLists.txt`에서 하드코딩된 `#ifdef _WIN32` 경로 및 플래그 지정을 제거하고, `target_compile_options`, `target_compile_features`로 플랫폼 차이를 추상화합니다.

## C++ Standard Evolution (if applicable)
| Approach | Standard | Description |
|----------|----------|-------------|
| Legacy | CMake < 3.0 | `CMAKE_CXX_FLAGS` 전역 변수 조작, 헤더와 소스 혼재 |
| Modern | CMake 3.12+ | `target_*` 명령어 기반, 디렉터리 구조화 (`include`/`src`) |
| Latest | CMake 3.26+ | C++23 타겟팅 (`cxx_std_23`), C++20 모듈(`FILE_SET`) 지원 |

Reference: `/docs/cpp_evolution/cmake_modernization.md` (예정)

## Edge Cases
- [x] ODR violations: 헤더 전용(`.hpp`) 구현을 분리할 때 ODR 위반 방지 확인
- [x] 기존 샘플(`double_dispatch`, `hardware_interfacing_system` 등)이 올바른 경로로 `#include`하는지 확인

## Dependencies & Adapters
- `pqxx`, `fmt` 등 FetchContent로 가져오는 외부 의존성은 즉시 컴파일되지 않아도 되도록 `option()`으로 전환합니다 (예: `ATUGCC_ENABLE_PQXX`).

## Technical Constraints
- Compiler: MSVC (VS 2026) / GCC (latest stable)
- CMake: 3.26+
- C++ Standard: C++23 (기본 타겟)

## Implementation Plan
- [x] Step 1: `include/atugcc/`, `src/` 디렉터리 구조 생성
- [x] Step 2: 루트 `CMakeLists.txt` 현대화 (`PROJECT_NAME` 변경, `target_compile_features`, `option` 추가)
- [x] Step 3: 기존 소스 파일 이동
  - `modules/log/` -> `include/atugcc/core/`, `src/core/`
  - `sample/design_pattern/` -> `include/atugcc/pattern/`
  - `sample/` 나머지 구현 예제 -> `sample/`
  - `libs/libsample/` 헤더/소스 -> `include/atugcc/libs/`, `src/libs/`
- [x] Step 4: 이동한 소스 파일 내부의 `#include` 경로 일괄 수정 (`#include "atugcc/core/..."`)
- [x] Step 5: `tests/CMakeLists.txt` 현대화 (GTest 최신화, target 연동)

## Verification Plan
- [x] CMake build: `cmake --build build --config Debug`
- [x] Tests: `ctest --output-on-failure -C Debug`
- [x] Zero warnings at `/W3` (MSVC) or `-Wall` (GCC)
