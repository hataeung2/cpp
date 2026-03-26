# Spec: 05 — MemoryDump 플랫폼 추상화

## Objective
`alog::MemoryDump`와 플랫폼별 구현체(`ExceptionHandlerImpl_Windows`, `ExceptionHandlerImpl_Linux`)를  
`atugcc::core` 네임스페이스로 이전하고, 다음 문제를 해결한다:

1. **헤더에 구현이 혼재** — `memory_dump.hpp` 가 플랫폼별 `#ifdef` 블록 안에 전역 함수(`crashHdler`, `signalHandler`)와 클래스 멤버 정의(`registerHandler`, `dump`)를 모두 포함 → ODR 위반 가능성 및 다중 TU 포함 불가.
2. **`PURE` 매크로** 제거 → `= 0` 직접 사용.
3. **의존성 역전**: `ExceptionHandlerImpl` 인터페이스를 Concept 또는 추상 기반 클래스로 명확히 분리.
4. **`static inline impl_` 초기화 위치** 정리.

## Requirement Details

### Public API Surface (`include/atugcc/core/memory_dump.hpp`)

```cpp
namespace atugcc::core {

// 추상 인터페이스 (순수 가상)
class ICrashHandler {
public:
    virtual ~ICrashHandler() = default;
    virtual void registerHandler() = 0; // = 0; 직접 사용 (PURE 매크로 제거)
    virtual void dump(std::ostream& out) = 0;
};

// 팩토리 함수 선언 (플랫폼별 .cpp에서 정의)
[[nodiscard]] std::unique_ptr<ICrashHandler> makeCrashHandler();

// 퍼사드 — 사용자가 직접 인스턴스화
class MemoryDump {
public:
    // 생성 시 플랫폼 핸들러 자동 등록
    explicit MemoryDump(std::ostream& dumpOut = std::cerr);
    ~MemoryDump() = default;

    // 명시적 덤프 트리거 (RingBuffer → 파일)
    void dump() const;

private:
    std::unique_ptr<ICrashHandler> m_handler;
    std::ostream&                  m_out;
};

} // namespace atugcc::core
```

> **주요 변경**: `MemoryDump::impl_` 정적 멤버 제거 → 각 인스턴스가 `unique_ptr<ICrashHandler>` 소유.  
> `REGISTER_MEMORY_DUMP_HANDLER` 매크로는 유지하되 `atugcc::core::MemoryDump` 타입으로 업데이트.

### Internal Implementation

#### `src/core/crash_handler_windows.cpp` (MSVC 전용)
```cpp
// WIN32_LEAN_AND_MEAN, Windows.h 포함은 이 TU에만 격리
LONG WINAPI crashHandlerCallback(EXCEPTION_POINTERS* ei) { ... }

void WindowsCrashHandler::registerHandler() {
    SetUnhandledExceptionFilter(crashHandlerCallback);
}
void WindowsCrashHandler::dump(std::ostream& out) { /* RingBuffer → out */ }
```

#### `src/core/crash_handler_linux.cpp` (Linux 전용)
```cpp
void signalHandler(int sig) { ... }

void LinuxCrashHandler::registerHandler() {
    std::signal(SIGSEGV, signalHandler);
    std::signal(SIGABRT, signalHandler); // 추가 권장
}
void LinuxCrashHandler::dump(std::ostream& out) { ... }
```

#### `src/core/memory_dump.cpp`
- `makeCrashHandler()` 구현 (`#ifdef _WIN32` 분기)
- `MemoryDump` 생성자 / `dump()` 구현
- 덤프 파일 경로: `std::filesystem::path` 기반으로 교체 (하드코딩 `"log"` 제거)

### Platform Specifics
| 플랫폼 | 파일 | 특이사항 |
|--------|------|---------|
| Windows | `crash_handler_windows.cpp` | `SetUnhandledExceptionFilter`, DbgHelp.lib 선택적 연동 |
| Linux   | `crash_handler_linux.cpp`   | `SIGSEGV`, `SIGABRT`, `SIGBUS` 핸들러 등록 |
| 공통    | `memory_dump.cpp`           | `std::filesystem`, `std::format` |

CMakeLists.txt 조건부 소스 추가:
```cmake
if(WIN32)
    target_sources(atugcc_core PRIVATE src/core/crash_handler_windows.cpp)
elseif(UNIX)
    target_sources(atugcc_core PRIVATE src/core/crash_handler_linux.cpp)
endif()
```

## C++ Standard Evolution

| Approach | Standard | Description |
|----------|----------|-------------|
| Legacy   | C++17    | `#ifdef` 블록 안에 전역 함수 정의, `fmt::format`, 헤더 내 구현 혼재 |
| Modern   | C++20    | 헤더/소스 완전 분리, `std::format`, `std::filesystem::path`, `[[nodiscard]]` |
| Latest   | C++23    | `std::stacktrace` (MSVC 지원) 연동으로 크래시 시 스택 트레이스 자동 덤프 |

Reference: `/docs/cpp_evolution/filesystem_format.md` (예정)

## Edge Cases
- [ ] **다중 TU 포함 ODR**: 헤더에서 `crashHdler`, `signalHandler` 정의 제거 → 소스 파일로 이동
- [ ] **전역 핸들러 콜백에서 `MemoryDump` 인스턴스 접근**: 정적 전역 포인터 또는 싱글턴 `DbgBuf` 경유
- [ ] **`dump()` 파일 경로 `fs::exists` 버그**: 현재 코드는 파일이 존재하면 삭제, 존재하지 않으면 디렉터리 생성 — 로직 반전 버그 수정 필요
- [ ] `std::filesystem::create_directories` 사용 (중첩 경로 지원)
- [ ] 신호 핸들러 안전: `async-signal-safe` 함수만 사용 (`write` 선호, `std::cerr` 지양)
- [ ] `MemoryDump` 복수 생성 방지 또는 허용 정책 결정

## Dependencies & Adapters
- `atugcc::core::TimeStamp` (덤프 파일명 생성)
- `atugcc::core::RingBuffer` / `DbgBuf` (덤프 내용 소스)
- Windows: `DbgHelp.lib` — `option(ATUGCC_ENABLE_DBGHELP OFF)` 로 선택적 활성화
- Linux: 추가 신호(`SIGBUS`, `SIGFPE`) 핸들러 — 선택적

## Technical Constraints
- Compiler: MSVC (VS 2026) / GCC (latest stable)
- CMake: 3.26+
- C++ Standard: C++20 minimum

## Context & References
- 현재 헤더/구현 혼재: [`memory_dump.hpp`](/include/atugcc/core/memory_dump.hpp)
- 매크로 정의: [`adefine.hpp`](/include/atugcc/core/adefine.hpp)
- 의존: [`ring_buffer.h`](/include/atugcc/core/ring_buffer.h), [`atime.hpp`](/include/atugcc/core/atime.hpp)

## Implementation Plan
- [ ] Step 1: `include/atugcc/core/memory_dump.hpp` — `ICrashHandler` 인터페이스, `MemoryDump` 퍼사드, `makeCrashHandler()` 선언
- [ ] Step 2: `src/core/crash_handler_windows.cpp` 생성 (Windows 전용 구현 격리)
- [ ] Step 3: `src/core/crash_handler_linux.cpp` 생성 (Linux 전용)
- [ ] Step 4: `src/core/memory_dump.cpp` — 팩토리, `dump()`, 파일 경로 `std::filesystem` 전환
- [ ] Step 5: `fs::exists` 버그 수정
- [ ] Step 6: `CMakeLists.txt` 플랫폼별 소스 조건부 추가
- [ ] Step 7: `adefine.hpp` 내 `REGISTER_MEMORY_DUMP_HANDLER` 매크로 네임스페이스 업데이트

## Verification Plan
- [ ] CMake build: `cmake --build build --config Debug`
- [ ] Tests: `ctest --output-on-failure -C Debug`
- [ ] 빌드 테스트: Windows + Linux CI (또는 WSL) 양쪽 확인
- [ ] GTest 케이스:
  - `MemoryDumpTest.DumpCreatesFile` — `dump()` 후 `log/` 디렉터리에 파일 생성 확인
  - `MemoryDumpTest.DumpFileContainsLog` — `RingBuffer` 에 기록된 항목이 덤프 파일에 포함
  - `MemoryDumpTest.NoBugOnExistingDir` — `log/` 디렉터리 이미 존재 시 정상 동작
- [ ] Zero warnings at `/W4` (MSVC) or `-Wall -Wextra` (GCC)
