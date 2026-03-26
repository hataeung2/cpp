# Spec: 09 — ErrorCode / Expected 모듈 (제안)

## Objective
`atugcc::core` 에 C++23 `std::expected` 기반 **통일 오류 처리 레이어**를 추가한다.  
기존 예외 throw (`std::invalid_argument` 등) 와 `nullptr` 반환을 혼재하지 않고, 라이브러리 전체에서 일관된 오류 흐름을 제공한다.

## Background / Motivation
- `RingBuffer` 생성자: 현재 `std::invalid_argument` throw → `std::expected<RingBuffer, Error>` 팩토리로 대안 제공 가능
- `MemoryDump::dump()`: 파일 I/O 실패 시 오류 무시 → `std::expected` 반환으로 호출자가 처리
- C++23 `std::expected` + monadic operations (`.and_then`, `.or_else`, `.transform`) 연습 목적

## Requirement Details

### Public API Surface (`include/atugcc/core/error.hpp`)

```cpp
namespace atugcc::core {

enum class CoreError {
    InvalidArgument,      // 잘못된 인자
    FileIOFailure,        // 파일 입출력 오류
    PlatformUnsupported,  // 현재 플랫폼 미지원 기능
    Unexpected,           // 예상치 못한 오류
};

[[nodiscard]] std::string_view to_string(CoreError e) noexcept;

// 편의 타입 별칭
template <typename T>
using Expected = std::expected<T, CoreError>;

// void 성공 결과
using Result = std::expected<void, CoreError>;

} // namespace atugcc::core
```

### 연동 적용 예시
```cpp
// RingBuffer 팩토리 함수
Expected<RingBuffer> makeRingBuffer(std::size_t capacity);

// MemoryDump::dump() 반환형 변경
Result dump(const std::filesystem::path& dir = "log") const;
```

## C++ Standard Evolution
| Approach | Standard | Description |
|----------|----------|-------------|
| Legacy   | C++17    | 예외 throw / null 반환 혼재, 오류 처리 일관성 없음 |
| Modern   | C++23    | `std::expected<T, E>` — 오류를 값으로 전파, monadic chain |

## Implementation Plan
- [ ] Step 1: `include/atugcc/core/error.hpp` — `CoreError` enum, `Expected<T>`, `Result` 정의
- [ ] Step 2: `RingBuffer` 에 `makeRingBuffer()` 팩토리 추가 (생성자는 유지)
- [ ] Step 3: `MemoryDump::dump()` → `Result` 반환으로 변경

## Verification Plan
- [ ] GTest: `Expected<T>` chain 및 오류 처리 경로 테스트
- [ ] CMake build: `cmake --build build --config Debug`
