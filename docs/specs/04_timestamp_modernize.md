# Spec: 04 — TimeStamp 모듈 C++20 전환

## Objective
`alog::TimeStamp`를 `atugcc::core::TimeStamp`로 이전하면서, `#ifdef _WIN32 / localtime_r` 분기를 제거하고 C++20 `std::chrono` calendar API로 완전히 대체한다.  
`using namespace std;`를 제거하고, `enum OPTION`을 `enum class`로 승격시킨다.

## Requirement Details

### Public API Surface (`include/atugcc/core/timestamp.hpp`)

```cpp
namespace atugcc::core {

class TimeStamp {
public:
    enum class Option : unsigned int {
        None      = 0x0000,
        WithFmt   = 0x0001, // "YYYY-MM-DD HH:MM:SS.mmm"
        AddSpace  = 0x0002, // 끝에 공백 1개 추가
    };
    using OptFlags = unsigned int;

    // 현재 시각 문자열 반환 (consteval 불가, noexcept 가능)
    [[nodiscard]] static std::string str(
        OptFlags opt = static_cast<OptFlags>(Option::WithFmt)
                     | static_cast<OptFlags>(Option::AddSpace)
    ) noexcept;

    // C++20 std::chrono::time_point 직접 받는 오버로드 (테스트 용이성)
    [[nodiscard]] static std::string str(
        std::chrono::system_clock::time_point tp,
        OptFlags opt = static_cast<OptFlags>(Option::WithFmt)
                     | static_cast<OptFlags>(Option::AddSpace)
    ) noexcept;

    TimeStamp() = delete; // 정적 유틸리티 클래스 — 인스턴스 금지
};

// 비트 OR 연산자 지원 (enum class 용)
constexpr TimeStamp::OptFlags operator|(TimeStamp::Option a, TimeStamp::Option b) noexcept;

} // namespace atugcc::core
```

### Internal Implementation (`src/core/timestamp.cpp` 또는 헤더 인라인)
- C++20 `std::chrono::system_clock::now()` + `std::chrono::zoned_time` (`<chrono>`) 사용:
  ```cpp
  auto now  = std::chrono::system_clock::now();
  auto zt   = std::chrono::zoned_time{std::chrono::current_zone(), now};
  auto local = zt.get_local_time();
  ```
- `std::format`(`<format>`) 으로 날짜 문자열 생성:
  ```cpp
  // WithFmt + AddSpace
  return std::format("{:%Y-%m-%d %H:%M:%S} ", local);
  // None
  return std::format("{:%Y%m%d%H%M%S}", local);
  ```
- **플랫폼 분기 완전 제거** — `_localtime64_s` / `localtime_r` 불필요.

> ⚠️ **`std::chrono::current_zone()`** 은 MSVC 2019 16.10+ / GCC 14+ 에서 지원.  
> GCC 13 이하 폴백: `<tzdata>` 또는 `date` 라이브러리(Howard Hinnant).

### Platform Specifics
| 플랫폼 | 구현 |
|--------|------|
| MSVC (VS 2026) | `std::chrono::zoned_time` 완전 지원. `std::format` 사용. |
| GCC (≥ 14)    | `std::chrono::zoned_time` 지원. `std::format` 사용. |
| GCC (< 14)    | `CMakeLists.txt` `option(ATUGCC_USE_DATE_LIB)` 으로 Howard Hinnant `date` 라이브러리 폴백 활성화. |

## C++ Standard Evolution

| Approach | Standard | Description |
|----------|----------|-------------|
| Legacy   | C++17    | `std::chrono::system_clock::to_time_t` + `_localtime64_s`/`localtime_r` 분기, `std::put_time` |
| Modern   | C++20    | `std::chrono::zoned_time`, `std::format("{:%Y-%m-%d ...}", ...)` — 플랫폼 분기 제거 |
| Latest   | C++23    | `std::print` 연동, `std::chrono::hh_mm_ss` 등 추가 분해 타입 활용 가능 |

Reference: `/docs/cpp_evolution/chrono_format.md` (예정)

## Edge Cases
- [ ] `current_zone()` 미지원 GCC 버전 — CMake 조건부 폴백
- [ ] `noexcept` 보장 — `std::format`이 throw할 수 있음 → 실패 시 `""` 반환 + `std::terminate` 방지
- [ ] 밀리초 정밀도: `std::chrono::duration_cast<milliseconds>` 명시적 사용
- [ ] DST(일광절약시간) 처리 — `zoned_time`이 자동 처리
- [ ] ODR: 인라인 정의 시 `inline` 키워드 필수

## Dependencies & Adapters
- 외부 의존성 없음 (표준 `<chrono>`, `<format>`)
- GCC < 14 옵션: `FetchContent` 로 [Howard Hinnant date](https://github.com/HowardHinnant/date) 추가 (`option(ATUGCC_USE_DATE_LIB OFF)`)

## Technical Constraints
- Compiler: MSVC (VS 2026) / GCC 14+ 권장
- CMake: 3.26+
- C++ Standard: C++20 minimum

## Context & References
- 현재 헤더: [`atime.hpp`](/include/atugcc/core/atime.hpp)
- 의존: [`ring_buffer.h`](/include/atugcc/core/ring_buffer.h) — `addStringEntry`에서 `TimeStamp::str()` 사용
- 관련: [`memory_dump.hpp`](/include/atugcc/core/memory_dump.hpp) — 덤프 파일명에 `TimeStamp` 사용

## Implementation Plan
- [ ] Step 1: `include/atugcc/core/timestamp.hpp` 생성 (`atugcc::core`, enum class, `operator|`)
- [ ] Step 2: `src/core/timestamp.cpp` 생성 (zoned_time + std::format 구현)
- [ ] Step 3: CMake `option(ATUGCC_USE_DATE_LIB OFF)` 추가 및 GCC 버전 검사
- [ ] Step 4: `atime.hpp` — deprecated alias 헤더로 전환
- [ ] Step 5: `ring_buffer.cpp`, `memory_dump.hpp` 참조처 `atugcc::core::TimeStamp`로 업데이트

## Verification Plan
- [ ] CMake build: `cmake --build build --config Debug`
- [ ] Tests: `ctest --output-on-failure -C Debug`
- [ ] GTest 케이스:
  - `TimeStampTest.FormatWithFmt` — `YYYY-MM-DD HH:MM:SS.mmm ` 형식 검증 (정규식 매칭)
  - `TimeStampTest.FormatNone` — `YYYYMMDDHHMMSSmmm` 14자리 숫자 검증
  - `TimeStampTest.TimePointOverload` — 고정 `time_point` 입력 → 결정론적 출력 비교
  - `TimeStampTest.NoInstantiation` — `TimeStamp ts;` 컴파일 오류 확인 (static_assert)
- [ ] Zero warnings at `/W4` (MSVC) or `-Wall -Wextra` (GCC)
