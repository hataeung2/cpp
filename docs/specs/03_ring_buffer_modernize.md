# Spec: 03 — RingBuffer 모듈 (고효율 Fixed-Block 재설계)

## Objective
`std::string` 기반의 동적 할당 구조를 폐기하고, **컴파일 타임 고정 크기 char 배열(fixed-block)** 기반의  
링버퍼로 전면 재설계한다. 각 스레드가 자신의 링버퍼를 단독 소유(thread-local, no-lock)하며,  
`boost::lockfree::spsc_queue` 를 통해 공통 소비 스레드(Logger thread)로 블록을 전달한다.

---

## 메모리 레이아웃 설계

### 블록 구조 (1 Block = 128 bytes)

```
┌──────────────────────────────────────────────────────────────┐
│ Offset │  Size  │  Field                                      │
├──────────────────────────────────────────────────────────────┤
│   0    │ 2 byte │ header (uint16_t, little-endian)            │
│   2    │125 byte│ payload (char[125])  ← 로그 문자열 (null 제외)│
│  127   │ 1 byte │ '\0'  (sentinel)     ← 항상 0, 읽기 안전    │
└──────────────────────────────────────────────────────────────┘
 Total = 128 bytes
```

### 헤더 비트 레이아웃 (uint16_t = 16bit)

```
 Bit  15   14  |  13  |  12       0
      ─────────┼──────┼───────────────
      LEVEL    │ CONT │  payload len
      (2 bits) │(flag)│  (13 bits)

LEVEL 필드:
  00 = DEBUG   01 = INFO  10 = WARN  11 = ERROR

CONT 플래그 (bit 13):
  0 = 단독 또는 첫 번째 블록
  1 = continuation 블록 (이전 블록의 연속)

페이로드 길이 (bit 12~0):
  0 ~ 125  (실제 사용된 바이트)
  빈 블록  : len 필드 = 0
```

```cpp
// 헤더 인코딩 상수
constexpr uint16_t kLevelShift    = 14;
constexpr uint16_t kLevelMask     = 0xC000; // bit[15:14]
constexpr uint16_t kContFlag      = 0x2000; // bit[13]
constexpr uint16_t kLenMask       = 0x1FFF; // bit[12:0]  (max=8191, 실사용 max=125)

// 인코딩
uint16_t encodeHeader(Level lv, bool cont, uint16_t len) {
    return (static_cast<uint16_t>(lv) << kLevelShift)
         | (cont ? kContFlag : 0)
         | (len & kLenMask);
}
// 디코딩
Level    decodeLevel(uint16_t h) { return static_cast<Level>((h & kLevelMask) >> kLevelShift); }
bool     isCont(uint16_t h)      { return h & kContFlag; }
uint16_t decodeLen(uint16_t h)   { return h & kLenMask; }
```

- 미사용 페이로드 바이트는 반드시 `\0` 으로 채움 — 안전한 `string_view` 변환 보장.
- 페이로드가 125B 를 초과하는 메시지는 **continuation block** 으로 분할 (후술).

### 링버퍼 전체 구조

```
┌─────────────────────────────────────────────────────┐
│  RingBuffer<BlockSize=128, BlockCount=256>           │
│                                                      │
│  buf_[BlockCount][BlockSize]  (32 KiB, 연속 배열)   │
│                                                      │
│  write_idx_  : uint32_t  (원자: flush 스레드가 읽음) │
│  read_idx_   : uint32_t  (소비 전용, 원자 불필요)    │
│                                                      │
│  alignas(64) → 캐시 라인 분리                        │
└─────────────────────────────────────────────────────┘
```

- `BlockCount` 는 반드시 **2의 거듭제곱** (기본 256) → 인덱스 마스크: `idx & (BlockCount - 1)`
- `buf_` 는 힙 미사용, **인라인 배열** → 캐시 친화적
- 전체 크기: `128 × 256 = 32 KiB` (L1 캐시 내 수용 가능)

---

## Write / Read 충돌 처리 (Overwrite Policy)

링버퍼가 가득 찼을 때(write가 read를 추월하려 할 때) **최신 로그를 우선 보존** 한다.

```
충돌 감지 조건:
  next_write_idx == read_idx   (write가 read를 추월하는 순간)

처리 절차:
  1. write 범위 확정  : 현재 메시지가 차지할 블록 수(N) 계산
  2. read_idx 강제 전진: read_idx = (write_idx + N) & mask
     → 쓰기 범위 바로 다음 블록이 새 읽기 시작점
  3. 오래된 로그가 덮어쓰여지며, 가장 최신 N개 블록은 항상 보존됨
```

```
시각화 (BlockCount=8, 메시지=3블록):

Before write (write=5, read=3, 충돌):
  [0][1][2][R=3][4][W=5][6][7]

After eviction + write:
  [0][1][2][3*][4*][W=5][6][7]  ← 3,4 덮어쓰기
  read_idx → 6  (= (5+3) & 7 → 0? 아니면 8 & 7 = 0)
  (정확한 인덱스는 구현에서 마스킹으로 처리)
```

---

## Public API Surface (`include/atugcc/core/ring_buffer.hpp`)

```cpp
#pragma once
#include <cstdint>
#include <cstring>
#include <string_view>
#include <span>
#include <atomic>
#include <concepts>

namespace atugcc::core {

// ── 로그 레벨 ────────────────────────────────────────────────
enum class Level : uint8_t {
    Debug = 0b00,
    Info  = 0b01,
    Warn  = 0b10,
    Error = 0b11,
};

// ── 블록 레이아웃 상수 ─────────────────────────────────────────
inline constexpr std::size_t kDefaultBlockSize  = 128;
inline constexpr std::size_t kDefaultBlockCount = 256; // 반드시 2의 거듭제곱
inline constexpr uint16_t    kLevelShift        = 14;
inline constexpr uint16_t    kLevelMask         = 0xC000; // bit[15:14]
inline constexpr uint16_t    kContFlag          = 0x2000; // bit[13]
inline constexpr uint16_t    kLenMask           = 0x1FFF; // bit[12:0]

// ── Flush 정책 ────────────────────────────────────────────────
// 링버퍼 사용률이 FlushThreshold 를 초과하면 write() 종료 시 자동 flush 트리거
// 0.0 = 항상 수동, 1.0 = 자동 flush 없음
// 기본: 0.5 (50% 초과 시 자동 flush)
inline constexpr float kDefaultFlushThreshold = 0.5f;

// ── RingBuffer ─────────────────────────────────────────────────
// BlockSize      : 블록 당 바이트 수 (헤더 포함)
// BlockCount     : 블록 총 개수 (2의 거듭제곱 강제)
template <std::size_t BlockSize  = kDefaultBlockSize,
          std::size_t BlockCount = kDefaultBlockCount>
    requires (BlockCount > 1 && (BlockCount & (BlockCount - 1)) == 0) // 2의 거듭제곱
          && (BlockSize  >= 4)   // 최소: 2B header + 1B payload + 1B null
class RingBuffer {
public:
    static constexpr std::size_t kHeaderSize  = 2;
    static constexpr std::size_t kSentinel    = 1;
    static constexpr std::size_t kPayloadSize = BlockSize - kHeaderSize - kSentinel;
    static constexpr std::size_t kMask        = BlockCount - 1;

    // flush_threshold : 0.5 = 사용률 50% 초과 시 write() 후 자동 flush 트리거
    explicit RingBuffer(float flush_threshold = kDefaultFlushThreshold) noexcept;
    ~RingBuffer() = default;

    // ── 단일 스레드 전용 / no-lock ────────────────────────────
    // Level 지정 기록 (125B 초과 시 자동 continuation 분할)
    // write() 종료 후 사용률 > flush_threshold 이면 flushToQueue() 자동 호출
    void write(std::string_view msg, Level lv = Level::Debug) noexcept;

    // ── 소비 스레드에서 호출 ───────────────────────────────────
    // 다음 블록 헤더 + string_view 반환 (Zero-copy, buf_ 메모리 직접 참조)
    // 비어있으면 nullopt 반환
    struct ReadResult {
        std::string_view payload;
        Level            level;
        bool             isContinuation;
    };
    [[nodiscard]] std::optional<ReadResult> read() noexcept;

    // 명시적 flush — 소비 스레드 없이도 직접 큐에 드레인
    void flushToQueue() noexcept;

    // 현재 사용 중인 블록 수 (write 스레드 내에서 정확, 외부에서는 근사값)
    [[nodiscard]] std::size_t usedBlocks() const noexcept;
    [[nodiscard]] float       usageRatio() const noexcept; // usedBlocks / BlockCount
    [[nodiscard]] bool        empty() const noexcept;

    // flush 스레드가 write_idx를 원자적으로 읽기 위해 사용
    [[nodiscard]] uint32_t writeIdx() const noexcept {
        return write_idx_.load(std::memory_order_acquire);
    }

private:
    // N블록 쓸 공간 확보: 충돌 시 read_idx 강제 전진
    void evictIfNeeded(std::size_t blocksNeeded) noexcept;

    // 단일 블록 기록 (헤더 + 페이로드 + zero-padding)
    void writeBlock(uint32_t idx, std::string_view chunk,
                    Level lv, bool isContinuation) noexcept;

    // ── 메모리 레이아웃 (캐시 라인 분리) ─────────────────────
    alignas(64) std::atomic<uint32_t> write_idx_{0}; // flush 스레드가 acquire로 읽음
    alignas(64) uint32_t              read_idx_{0};  // write 스레드 단독 소유

    float flush_threshold_;

    // 인라인 2D 배열 — 힙 할당 없음, 캐시 연속
    char buf_[BlockCount][BlockSize]{};
};

// ── DbgBuf: thread_local 싱글턴 래퍼 ─────────────────────────
// 각 스레드가 독립된 RingBuffer 를 소유 (no-lock)
class DbgBuf {
public:
    DbgBuf() = delete;

    // 현재 스레드의 RingBuffer 에 Level 지정 기록
    static void log(std::string_view msg, Level lv = Level::Debug) noexcept;

    // 현재 스레드의 RingBuffer 인스턴스 반환
    static RingBuffer<>& instance() noexcept;
};

} // namespace atugcc::core
```

---

## 스레드 아키텍처 및 boost::lockfree 연동

### 전체 흐름

```
Thread A ──[thread_local RingBuffer A]──┐
Thread B ──[thread_local RingBuffer B]──┼──► boost::lockfree::spsc_queue<Block*>
Thread C ──[thread_local RingBuffer C]──┘         │
                                              Logger Thread
                                           (drain → 파일/콘솔)
```

### 공통 큐 설계

```cpp
// include/atugcc/core/log_queue.hpp

#include <boost/lockfree/spsc_queue.hpp>

namespace atugcc::core {

// 블록 포인터(또는 복사본)를 전달하는 SPSC 큐
// 프로듀서: flush 스레드 / 각 RingBuffer 소유 스레드가 명시적 flush 호출
// 컨슈머: 단일 Logger Thread

struct LogBlock {
    char data[kDefaultBlockSize];
};

// spsc_queue: 고정 capacity, lock-free, 단일 생산자/소비자
using LogQueue = boost::lockfree::spsc_queue<
    LogBlock,
    boost::lockfree::capacity<4096>  // 컴파일 타임 고정
>;

// 전역 큐 (Logger thread와 각 flush 코드가 공유)
LogQueue& globalLogQueue() noexcept;

} // namespace atugcc::core
```

#### flush 절차 — 자동(50% 임계값) + 수동 혼합 정책

```
자동 flush 조건 (write() 종료 시 체크):
  usageRatio() > flush_threshold_  →  flushToQueue() 자동 호출

수동 flush:
  DbgBuf::instance().flushToQueue()  // 임계값 이하에서 호출자가 직접 제어
                                      // (e.g. 프레임 종료, 트랜잭션 완료 시점)
```

```cpp
// RingBuffer::write() 내부 (의사 코드)
void write(string_view msg, Level lv) noexcept {
    // ... 블록 기록 ...

    // 자동 flush 체크
    if (usageRatio() > flush_threshold_) {
        flushToQueue();
    }
}

// flushToQueue() — write 스레드에서만 호출
void flushToQueue() noexcept {
    auto& q = globalLogQueue();
    while (!empty()) {
        LogBlock blk;
        std::memcpy(blk.data, buf_[read_idx_], kDefaultBlockSize); // 전체 블록 복사
        read_idx_ = (read_idx_ + 1) & kMask;
        if (!q.push(blk)) {
            // 큐 가득 참 → 드롭, drop_count_ 증가 (진단용)
            ++drop_count_;
            break;
        }
    }
}
```

> **왜 `spsc_queue`인가?**  
> 각 thread_local RingBuffer의 flush 호출자(=write 스레드)와  
> 컨슈머(Logger thread)가 1:1 이므로 CAS 없는 `spsc_queue`가 최적.  
> 여러 스레드가 동일 큐에 동시 push하는 경우 `boost::lockfree::queue`(MPSC)로 교체.

---

## 설계 확정 항목 요약

| 항목 | 결정 |
|------|------|
| **Continuation block** | ✅ 사용 — 125B 초과 메시지 분할, CONT 플래그(bit 13)로 표시 |
| **로그 레벨** | ✅ 헤더 bit[15:14] — DEBUG/INFO/WARN/ERROR (2bit, 4단계) |
| **Boost 도입** | ✅ 시스템 설치 `find_package(Boost REQUIRED)` |
| **Flush 정책** | ✅ 50% 초과 시 자동 + 수동 `flushToQueue()` 병행 (임계값 생성자 파라미터) |
| **Thread model** | ✅ thread_local RingBuffer (no-lock write), SPSC 큐로 Logger thread 전달 |
| **Eviction** | ✅ write 범위 확정 후 read를 그 범위 바로 다음 블록으로 강제 전진 |

---

## Internal Implementation (`src/core/ring_buffer.cpp`)

### `write()` 의사 코드

```
write(string_view msg):
  remaining = msg
  first = true
  while remaining.size() > 0:
    chunk = remaining.substr(0, kPayloadSize)
    remaining = remaining.substr(chunk.size())
    evictIfNeeded(1)          // 1블록 쓸 공간 확보
    writeBlock(write_idx_, chunk, !first)
    write_idx_.store((write_idx_ + 1) & kMask, memory_order_release)
    first = false
```

### `evictIfNeeded()` 의사 코드

```
evictIfNeeded(N):
  for i in 0..N:
    next = (write_idx_ + i) & kMask
    if next == read_idx_:
      // 충돌 → read를 write 완료 다음으로 강제 이동
      read_idx_ = (write_idx_ + N) & kMask
      return
```

### `writeBlock()` 의사 코드

```
writeBlock(idx, chunk, lv, isContinuation):
  block = buf_[idx]
  header = (uint16_t(lv) << kLevelShift)
          | (isContinuation ? kContFlag : 0)
          | (chunk.size() & kLenMask)
  memcpy(block + 0, &header, 2)             // 헤더 (2바이트)
  memcpy(block + 2, chunk.data(), chunk.size())
  memset(block + 2 + chunk.size(), '\0',    // 미사용 페이로드 + sentinel
         kPayloadSize - chunk.size() + kSentinel)
```

### `read()` 의사 코드 (Logger thread 전용)

```
read():
  if read_idx_ == write_idx_.load(acquire): return nullopt  // empty
  block  = buf_[read_idx_]
  h      = *reinterpret_cast<uint16_t*>(block)
  lv     = decodeLevel(h)
  isCont = isCont(h)
  plen   = decodeLen(h)          // bit[12:0]
  read_idx_ = (read_idx_ + 1) & kMask
  return ReadResult { string_view(block + 2, plen), lv, isCont }
  // 주의: string_view 는 buf_ 직접 참조 (Zero-copy)
  //       flushToQueue() 내에서 memcpy 후 큐에 복사 → 수명 문제 없음
```

### continuation 블록 조합 (Logger thread)

```
// Logger thread 소비 루프
std::string assembled;
while (auto r = rb.read()) {
    if (!r->isContinuation) assembled.clear();
    assembled += r->payload;
    if (next block is NOT continuation OR empty) {
        process(assembled, r->level);  // 완전한 메시지 처리
    }
}
```

---

## Platform Specifics
- 플랫폼 무관 (표준 라이브러리 + Boost).
- `alignas(64)` — x86/ARM 모두 지원.
- `boost::lockfree::spsc_queue` — 헤더 전용, 플랫폼 무관.

---

## C++ Standard Evolution

| Approach | Standard | Description |
|----------|----------|-------------|
| Legacy   | C++17    | `std::string` 동적 할당, `std::mutex` 전역 잠금, 힙 메모리 파편화 |
| Modern   | C++20    | `requires` concept으로 컴파일 타임 파라미터 검증, `std::atomic<>` acquire/release, `std::span` |
| Latest   | C++23    | `std::mdspan` 으로 2D `buf_` 뷰 추상화 가능 (선택적), `std::stacktrace` 연동 |

Reference: `/docs/cpp_evolution/concepts.md` (예정)

---

## Edge Cases

- [ ] **멀티블록 continuation read**: 소비자는 한 번의 `read()` 에서 단일 블록만 반환 → Logger thread가 continuation flag 확인 후 조합
- [ ] **Zero-copy 수명**: `read()` 가 반환한 `string_view`는 다음 `write()` 호출 전까지만 유효 → 소비 즉시 복사 또는 Logger thread가 전담 소비
- [ ] **write_idx_ 랩어라운드**: `uint32_t` 4G 오버플로 → `& kMask` 마스킹이 자동 처리 (kMask = 255 for default)
- [ ] **spsc_queue 가득 참**: `push()` 실패 시 드롭 — 최신 우선 정책 일관, 드롭 통계 카운터 권장
- [ ] **flush 주기**: 명시적 `flushToQueue()` 호출 없이 블록이 쌓이면 eviction 발생 → flush 주기를 `write()` N회마다 자동 트리거하는 정책 고려
- [ ] **Logger thread 종료 시 drain**: 프로그램 종료 전 잔여 블록 소비 (`std::atexit` or RAII guard)
- [ ] **`thread_local` 소멸 순서**: Logger thread 가 먼저 종료되면 큐 push 실패 → Logger thread를 가장 마지막에 join
- [ ] **ODR**: 템플릿 클래스 헤더 전용 → `#pragma once` 충분

---

## Dependencies & Adapters
- `atugcc::core::TimeStamp` — `write()` 호출 전 `dlog()` 레벨에서 타임스탬프 prepend (Spec 06 연계)
- **Boost** — 시스템 설치본 사용 (`find_package`)
  ```cmake
  # CMakeLists.txt
  find_package(Boost REQUIRED)
  target_link_libraries(atugcc_core PUBLIC Boost::headers)
  ```
  > Boost는 헤더 전용 lockfree 사용이므로 `Boost::headers` 링크만으로 충분.  
  > 미설치 시 빌드 오류로 명시 (`REQUIRED`). 설치 안내: `vcpkg install boost-lockfree` / Linux `apt install libboost-dev`

---

## Technical Constraints
- Compiler: MSVC (VS 2026) / GCC (latest stable)
- CMake: 3.26+
- C++ Standard: C++20 minimum, C++23 target
- Boost: 1.76+ (lockfree::spsc_queue 헤더 전용)

---

## Context & References
- 현재 헤더: [`ring_buffer.h`](/include/atugcc/core/ring_buffer.h)
- 현재 구현: [`ring_buffer.cpp`](/src/core/ring_buffer.cpp)
- 관련: [`adefine.hpp`](/include/atugcc/core/adefine.hpp) — `dlog` 매크로 (→ Spec 06)
- 연동: [Spec 05 — MemoryDump](/docs/specs/05_memory_dump_refactor.md) — `dump()` 시 RingBuffer 내용 플러시
- 연동: [Spec 06 — dlog](/docs/specs/06_dlog_modernize.md) — `write()` 호출 진입점

---

## Implementation Plan
- [ ] Step 1: `include/atugcc/core/ring_buffer.hpp` 신규 생성
  - `Level` enum, 헤더 비트 상수, `RingBuffer<>` 템플릿, `DbgBuf`
  - flush threshold 생성자 파라미터, `usageRatio()`, `flushToQueue()`
- [ ] Step 2: `include/atugcc/core/log_queue.hpp` 신규 생성
  - `LogBlock` (128B), `LogQueue` (spsc_queue), `globalLogQueue()` 선언
- [ ] Step 3: `src/core/ring_buffer.cpp` — `write()` (auto-flush 체크 포함), `evictIfNeeded()`, `writeBlock()` (Level 인코딩), `read()` (ReadResult 반환), `flushToQueue()`, `DbgBuf::log()`
- [ ] Step 4: `src/core/log_queue.cpp` — `globalLogQueue()` Meyers Singleton
- [ ] Step 5: `CMakeLists.txt` — `find_package(Boost REQUIRED)` + `target_link_libraries(atugcc_core PUBLIC Boost::headers)` 추가
- [ ] Step 6: `ring_buffer.h` deprecated 포워딩 헤더로 전환
- [ ] Step 7: 기존 참조처 (`memory_dump.hpp`, `alog.h`, `alog.cppm`) 업데이트

---

## Verification Plan
- [ ] CMake build: `cmake --build build --config Debug`
- [ ] Tests: `ctest --output-on-failure -C Debug`
- [ ] GTest 케이스:
  - `RingBufferTest.HeaderEncoding` — Level + continuation flag + len 비트 인코딩/디코딩 검증
  - `RingBufferTest.WriteAndRead` — 단일 블록 기록 후 `ReadResult` 필드 검증
  - `RingBufferTest.WrapAround` — BlockCount 초과 쓰기 → 최신 블록 보존 확인
  - `RingBufferTest.EvictionKeepsLatest` — 충돌 시 read_idx 올바른 전진, 최신 N개 유지
  - `RingBufferTest.ContinuationBlock` — 126B 초과 메시지 → CONT 플래그 + 다중 블록 분할 + Level 일관성
  - `RingBufferTest.ZeroPaddingInBlock` — 미사용 페이로드 바이트가 `\0` 임을 확인
  - `RingBufferTest.AutoFlushThreshold` — 사용률 50% 초과 시 `flushToQueue()` 자동 호출 확인
  - `RingBufferTest.ManualFlush` — 임계값 이하에서 수동 `flushToQueue()` 후 큐에 블록 이동 확인
  - `RingBufferTest.QueueFullDrop` — spsc_queue 가득 참 시 드롭하고 크래시 없음, `drop_count_` 증가
  - `RingBufferTest.LevelFilter` — `ReadResult.level` 필드가 기록 시 Level 과 일치
- [ ] Zero warnings at `/W4` (MSVC) or `-Wall -Wextra` (GCC)
