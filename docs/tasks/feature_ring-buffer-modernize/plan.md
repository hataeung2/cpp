# Plan: RingBuffer 모듈 C++20 전환 (Fixed-Block 재설계)

Branch: `feature/ring-buffer-modernize`
Spec: `/docs/specs/03_ring_buffer_modernize.md`

## Files

### [NEW] `include/atugcc/core/ring_buffer.hpp`
- `atugcc::core` 네임스페이스
- `Level` enum class (DEBUG/INFO/WARN/ERROR — 헤더 bit[15:14])
- 헤더 인코딩/디코딩 상수 및 헬퍼 함수
- `RingBuffer<BlockSize=128, BlockCount=256>` 템플릿 클래스
  - `requires` concept: 2의 거듭제곱 강제
  - `write(string_view, Level)` — no-lock, 자동 continuation 분할
  - Auto-flush: `usageRatio() > flush_threshold_` 시 `flushToQueue()`
  - `read() → optional<ReadResult>` — Zero-copy
  - `flushToQueue()` — `buf_` → `globalLogQueue()` copy
  - `alignas(64)` 캐시 라인 분리
- `DbgBuf` — thread_local 싱글턴 래퍼

### [NEW] `include/atugcc/core/log_queue.hpp`
- `LogBlock` (128B char 배열)
- `LogQueue = boost::lockfree::spsc_queue<LogBlock, capacity<4096>>`
- `globalLogQueue()` 선언

### [NEW] `src/core/log_queue.cpp`
- `globalLogQueue()` Meyers Singleton

### [MODIFY] `src/core/ring_buffer.cpp` → `src/core/ring_buffer.cpp` (전면 교체)
- `DbgBuf::instance()`, `DbgBuf::log()` 구현

### [MODIFY] `CMakeLists.txt`
- `find_package(Boost REQUIRED)` + vcpkg toolchain 지원
- `target_link_libraries(atugcc_core PUBLIC Boost::headers)`

### [MODIFY] `include/atugcc/core/adefine.hpp`
- `PURE` 매크로 제거 (spec 범위 내)
- `ring_buffer.h` → `ring_buffer.hpp` 포워딩 전환

### [MODIFY] `include/atugcc/core/ring_buffer.h`
- deprecated 포워딩 헤더로 전환

### [NEW] `tests/core/test_ring_buffer.cpp`
- GTest 케이스 전체 구현

### [MODIFY] `tests/CMakeLists.txt`
- `tests/core/test_ring_buffer.cpp` 추가

## C++20/23 Features Applied
| Feature | 사용처 |
|---------|--------|
| `requires` + concept | `BlockCount` 2의-거듭제곱, `BlockSize >= 4` 컴파일 타임 검증 |
| `std::optional<T>` | `read()` 반환 타입 |
| `std::atomic<uint32_t>` acquire/release | `write_idx_` — flush 스레드 안전 읽기 |
| `alignas(64)` | false sharing 방지 |
| `[[nodiscard]]` | `read()`, `usedBlocks()`, `usageRatio()`, `empty()` |
| `std::string_view` | 인자 및 반환 (zero-copy) |
| `static_cast` / `std::bit_cast` | 헤더 uint16_t 인코딩 |
| `inline constexpr` | 레이아웃 상수 |
| `thread_local` | `DbgBuf::instance()` per-thread 버퍼 |

## C++ Evolution Doc
`/docs/cpp_evolution/ring_buffer_evolution.md` — string 기반 → fixed-block 비교
