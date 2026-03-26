# Spec: 10 — Logger 통합 퍼사드 (제안)

## Objective
`RingBuffer` + `TimeStamp` + `dlog` + `MemoryDump` 를 하나의 **`atugcc::core::Logger`** 퍼사드로 통합한다.  
사용자는 `Logger` 하나만 헤더에 포함하면 코어 로깅 기능 전체를 사용 가능하게 한다.

## Background / Motivation
- 현재: `alog.h` → `ring_buffer.h`, `memory_dump.hpp`, `atime.hpp` 를 수동으로 묶음
- 현재 `alog.cppm` 은 C++ 모듈 방식을 시도하지만 구현 다소 미완성
- 목표: 단일 진입점 API → 빌더/설정 패턴으로 구성 가능한 `Logger`

## Requirement Details

### Public API Surface (`include/atugcc/core/logger.hpp`)

```cpp
namespace atugcc::core {

class Logger {
public:
    struct Config {
        std::size_t              bufferCapacity = 256;
        std::ostream*            liveOutput     = nullptr; // 실시간 cout/cerr 출력
        std::filesystem::path    dumpDir        = "log";
        bool                     enableCrashDump = true;
    };

    explicit Logger(Config cfg = {});
    ~Logger() = default;

    // 포맷 로깅
    template <typename... Args>
    void log(std::format_string<Args...> fmt, Args&&... args,
             std::source_location loc = std::source_location::current());

    // 버퍼 스냅샷
    [[nodiscard]] std::vector<std::string> snapshot() const;

    // 즉시 덤프
    Result dump() const;

    // 전역 기본 Logger 인스턴스 (Meyers Singleton)
    static Logger& global() noexcept;

private:
    RingBuffer  m_buffer;
    MemoryDump  m_dump;
};

} // namespace atugcc::core

// 전역 dlog → global Logger로 라우팅하는 래퍼
#define ATUGCC_LOG(...) ::atugcc::core::Logger::global().log(__VA_ARGS__)
```

## C++ Standard Evolution
| Approach | Standard | Description |
|----------|----------|-------------|
| Legacy   | C++11/17 | `alog.h` 수동 조합, 전역 `DbgBuf` singleton, 매크로 API |
| Modern   | C++20/23 | `Logger` 단일 퍼사드, `Config` Designated Initializer, `std::source_location` |

## Implementation Plan
- [ ] Step 1: Phase 1 (Spec 03~06) 완료 후 구현
- [ ] Step 2: `include/atugcc/core/logger.hpp` 생성
- [ ] Step 3: `src/core/logger.cpp` — 통합 구현
- [ ] Step 4: `alog.h` / `alog.cppm` → `logger.hpp` 래퍼로 deprecated 처리

## Verification Plan
- [ ] GTest: `LoggerTest.GlobalInstance`, `LoggerTest.FormatLog`, `LoggerTest.DumpOnRequest`
- [ ] CMake build: `cmake --build build --config Debug`
