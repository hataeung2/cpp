# Spec: 06 — dlog 매크로 → std::source_location 기반 함수 전환

## Objective
`#define dlog(...)` 매크로를 `std::source_location` 기반 인라인 함수 `atugcc::core::dlog()`로 교체한다.  
목표:
1. `__func__` 문자열 수동 전달 방식 제거 → `std::source_location::current()` 자동 캡처
2. `#ifdef NDEBUG` 조건부 컴파일을 함수 레벨 `if constexpr` / `[[maybe_unused]]` 로 대체
3. `aformat` 매크로 (`std::format` / `fmt::format` 분기) 제거 → C++20 `std::format` 통일
4. `adefine.hpp` 에서 `PURE` 매크로 제거 (Spec 05 연계)

## Requirement Details

### Public API Surface (`include/atugcc/core/dlog.hpp`)

```cpp
#pragma once
#include <source_location>
#include <string_view>
#include <format>
#include "atugcc/core/ring_buffer.hpp" // atugcc::core::DbgBuf

namespace atugcc::core {

// 컴파일 타임 상수: 릴리즈 빌드에서 dlog는 no-op
inline constexpr bool kDlogEnabled =
#ifdef NDEBUG
    false;
#else
    true;
#endif

// 핵심 로깅 함수
// default argument로 std::source_location::current() 자동 캡처
template <typename... Args>
inline void dlog(
    std::format_string<Args...> fmt,
    Args&&...                    args,
    std::source_location         loc = std::source_location::current()
) {
    if constexpr (kDlogEnabled) {
        auto msg = std::format("[{}:{}:{}] ",
            loc.file_name(), loc.line(), loc.function_name());
        msg += std::format(fmt, std::forward<Args>(args)...);
        DbgBuf::instance().add(std::move(msg));
    }
}

// 포맷 없이 단순 메시지 기록 오버로드
inline void dlog(
    std::string_view             msg,
    std::source_location         loc = std::source_location::current()
) {
    if constexpr (kDlogEnabled) {
        auto entry = std::format("[{}:{}:{}] {}",
            loc.file_name(), loc.line(), loc.function_name(), msg);
        DbgBuf::instance().add(std::move(entry));
    }
}

} // namespace atugcc::core
```

> **기존 `dlog(...)` 매크로 사용처 마이그레이션**:  
> `dlog("value: ", x, y)` → `atugcc::core::dlog("{} {}", x, y)` 또는  
> `using atugcc::core::dlog;` 선언 후 `dlog("{} {}", x, y)`.

### `adefine.hpp` 업데이트 (`include/atugcc/core/adefine.hpp`)
- `#define dlog(...)` 제거
- `#define PURE =0` 제거
- `#define aformat std::format` 제거 (Linux도 C++20 `std::format` 사용)
- `REGISTER_MEMORY_DUMP_HANDLER` → `atugcc::core::MemoryDump` 타입 업데이트

최종 `adefine.hpp` 는 아래만 남기거나 파일 자체를 폐기:
```cpp
// adefine.hpp (하위 호환 포워딩용, deprecated)
#pragma once
#include "atugcc/core/dlog.hpp"
#define REGISTER_MEMORY_DUMP_HANDLER atugcc::core::MemoryDump _atugcc_md_
```

### Internal Implementation
- 별도 `.cpp` 불필요 (함수 템플릿 헤더 인라인). `inline` 필수.
- `kDlogEnabled`: `constexpr bool` → `if constexpr` 분기로 릴리즈 빌드에서 zero-overhead 보장.

### Platform Specifics
- `std::format` — MSVC / GCC 14+ 완전 지원.
- GCC 13 이하: `std::format` 부분 지원 이슈 → CMake에서 GCC 버전 체크 후 경고 출력.
- `std::source_location` — C++20 표준. MSVC 2019 16.6+ / GCC 11+ 지원.

## C++ Standard Evolution

| Approach | Standard | Description |
|----------|----------|-------------|
| Legacy   | C++11/14 | `#define dlog(...) DbgBuf::log(__func__, ...)` — 매크로, 파일/라인 정보 없음 |
| Modern   | C++20    | `std::source_location` 자동 캡처 — 파일명/줄번호/함수명 포함, 타입 안전 |
| Latest   | C++23    | `std::stacktrace` 연동 옵션: `dlog` 호출 시 스택 트레이스 자동 첨부 (opt-in) |

Reference: `/docs/cpp_evolution/source_location.md` (예정)

## Edge Cases
- [ ] **`std::format_string` + `source_location` default arg 콤보**: C++ 표준에서 마지막 비-default 매개변수 뒤에 default 매개변수 배치 규칙 → variadic `Args...` + `source_location` 순서 주의 (MSVC/GCC 컴파일러 확장 필요 가능성)
  - 대안: `source_location` 를 첫 번째 인자로 받는 태그 dispatch 오버로드
- [ ] **릴리즈 빌드 zero-overhead**: `if constexpr (false)` 분기는 컴파일러가 완전 제거 → 검증 필요 (`/O2`, `-O2` 어셈블리 확인)
- [ ] **ODR**: `inline` 함수 템플릿 헤더 중복 포함 → `#pragma once` 필수
- [ ] **기존 `dlog` 매크로 사용처 호환**: 매크로 → 함수 전환 시 `dlog("text", x)` 형태가 함수 호출로 자연스럽게 전환되는지 확인
- [ ] `constexpr` 컨텍스트에서 `dlog` 허용 불가 (`std::format` 미지원) — 문서화

## Dependencies & Adapters
- `atugcc::core::DbgBuf` / `RingBuffer` (Spec 03)
- 외부 의존성 없음 (표준 `<source_location>`, `<format>`)

## Technical Constraints
- Compiler: MSVC (VS 2026) / GCC 11+ (`source_location`), GCC 14+ (`format` 완전)
- CMake: 3.26+
- C++ Standard: C++20 minimum

## Context & References
- 현재 매크로 정의: [`adefine.hpp`](/include/atugcc/core/adefine.hpp)
- 현재 모듈: [`alog.cppm`](/src/core/alog.cppm)
- 의존: Spec 03 (RingBuffer/DbgBuf), Spec 04 (TimeStamp)

## Implementation Plan
- [ ] Step 1: `include/atugcc/core/dlog.hpp` 생성 (`kDlogEnabled`, `dlog` 함수 템플릿)
- [ ] Step 2: `adefine.hpp` 정리 — `dlog`, `PURE`, `aformat` 매크로 제거, 포워딩 헤더로 전환
- [ ] Step 3: 기존 `dlog(...)` 사용처 전체 검색 및 `atugcc::core::dlog(fmt, args...)` 로 마이그레이션
- [ ] Step 4: `alog.cppm` — export 목록에 `dlog` 추가
- [ ] Step 5: Linux 빌드에서 `fmt::format` 의존성 제거 확인

## Verification Plan
- [ ] CMake build: `cmake --build build --config Debug`
- [ ] CMake build Release: `cmake --build build --config Release`
- [ ] Tests: `ctest --output-on-failure -C Debug`
- [ ] GTest 케이스:
  - `DlogTest.CapturesSourceLocation` — `dlog("msg")` 후 `DbgBuf::instance().snapshot()` 에서 파일명/라인 포함 확인
  - `DlogTest.FormatArgs` — `dlog("{} + {} = {}", 1, 2, 3)` — 포맷 결과 검증
  - `DlogTest.ReleaseBuildNoOp` — `NDEBUG` 정의 시 `DbgBuf` 에 항목 추가 없음
  - `DlogTest.NoMacroContamination` — `dlog` 가 함수임을 확인 (포인터 취득 가능)
- [ ] 어셈블리 확인: Release 빌드에서 `dlog` 호출 코드가 완전 제거됨 (`/O2` / `-O2`)
- [ ] Zero warnings at `/W4` (MSVC) or `-Wall -Wextra` (GCC)
