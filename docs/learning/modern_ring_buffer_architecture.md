# Modern C++23 RingBuffer Architecture & implementation Study

이 문서는 코멧 `f8c62cf949757af763a328427e0213b170b7799c`에서 구현된 고성능 로깅 시스템의 핵심 구조와 현대적 C++ 문법을 분석합니다.

---

## 1. 핵심 아키텍처 설계 (Architecture)

### 1-1. Fixed-Block 기반 메모리 레이아웃
기존의 `std::string` 기반 유동적 메모리 할당 대신, **128바이트 고정 블록** 방식을 채택했습니다.
- **장점**: 힙 할당(malloc/new)이 발생하지 않아 런타임 성능이 매우 일정(Deterministic)하며, 캐시 효율이 극대화됩니다.
- **블록 구조**: `[2B Header][125B Payload][1B Sentinel]`
  - **Header (16-bit)**:
    - `bit[15:14]`: 로그 레벨 (Debug, Info, Warn, Error)
    - `bit[13]`: Continuation 플래그 (메시지가 다음 블록으로 이어지는지 여부)
    - `bit[12:0]`: 실제 데이터 길이 (Max 125)

### 1-2. Thread-Local 격리 (No-Lock Write)
가장 큰 성능 향상 요인은 **`thread_local`** 키워드를 통한 쓰기 작업의 완전한 격리입니다.
- 각 스레드는 본인만의 `RingBuffer` 인스턴스를 가집니다 (`DbgBuf::instance()`).
- 쓰기 작업 시 다른 스레드와 경합(Contention)하지 않으므로 **Mutex(잠금)가 전혀 필요 없습니다.**

### 1-3. SPSC(Single-Producer Single-Consumer) 전역 큐
스레드별 로컬 버퍼는 일정량(50%) 이상 차면 전역 공유 큐로 데이터를 토스합니다.
- **`boost::lockfree::spsc_queue`**: Producer는 로그를 쓰는 스레드, Consumer는 로그를 파일로 저장하거나 출력하는 전용 로거 스레드입니다.
- 이 구조를 통해 로깅 작업이 실제 I/O(파일 쓰기) 대기 시간으로부터 완전히 분리됩니다.

---

## 2. 현대적 C++ 문법 활용 (Key Features)

### 2-1. `concepts` & `requires` (C++20)
템플릿 인수가 유효한지 컴파일 타임에 엄격하게 검사합니다.
```cpp
template <std::size_t BlockSize, std::size_t BlockCount>
    requires (BlockCount > 1 && (BlockCount & (BlockCount - 1)) == 0) // Power of Two 검사
          && (BlockSize >= 4)
class RingBuffer { ... };
```
- 비트 연산(`BC & (BC-1)`)을 통해 링버퍼 크기가 반드시 2의 거듭제곱임을 보장하여, 나머지 연산을 `& mask`로 대체(고속화)할 수 있게 합니다.

### 2-2. `std::atomic` & Memory Order (Memory Model)
스레드 간 인덱스 공유 시 성능 최적화를 위해 세밀한 메모리 배리어를 제어합니다.
- **`memory_order_release`**: 데이터를 쓴 후 인덱스를 업데이트할 때, "내가 쓴 데이터가 다른 스레드에 확실히 보이게" 보장합니다.
- **`memory_order_acquire`**: 인덱스를 읽을 때, "그 인덱스에 해당하는 최신 데이터"를 관찰할 수 있게 합니다.
- **`std::memory_order_relaxed`**: 스레드 로컬 내에서만 쓰이는 인덱스 읽기/쓰기에는 오버헤드 없는 relaxed를 사용합니다.

### 2-3. `alignas(64)` (False Sharing 방지)
현대 CPU의 캐시 라인 크기(CPU 캐시 한 단위)는 보통 64바이트입니다.
```cpp
alignas(64) std::atomic<uint32_t> write_idx_{0};
alignas(64) uint32_t read_idx_{0};
```
- 두 인덱스가 같은 캐시 라인에 있으면, 한 스레드가 업데이트할 때마다 다른 스레드의 캐시가 무효화되어 성능이 저하되는 **False Sharing** 현상이 발생합니다. `alignas(64)`로 이를 물리적으로 분리했습니다.

### 2-4. `thread_local` Singleton
```cpp
RingBuffer<>& DbgBuf::instance() noexcept {
    thread_local RingBuffer<> buf;
    return buf;
}
```
- 전역 Singleton의 단점인 '모든 스레드 공유' 문제를 해결하면서도, 각 스레드마다 고유한 저장소를 자동으로 관리하게 해주는 우아한 현대적 패턴입니다.

---

## 3. 알고리즘: Newest-Wins Eviction

링버퍼가 꽉 찼을 때, 전통적으로는 에러를 내거나 대기하지만, 로깅 시스템에서는 **최신 로그 보존**이 중요합니다.
- `evictIfNeeded`: `(write_idx + 1) == read_idx`가 되면, 아직 읽지 않은 가장 오래된 로그(`read_idx`)를 과감히 버리고 한 칸 전진시킵니다.
- 이를 통해 버퍼는 항상 순환하며 최신 N개의 로그를 완벽하게 유지합니다.

## 4. 템플릿 구현의 물리적 분리 팁
- **문제**: 템플릿 구현을 `.cpp`에 넣으면 다른 파일에서 사용할 때 링크 에러(`LNK2019`)가 발생합니다.
- **해결**: 구현부 대부분을 `.hpp` 하단으로 이동시키되, 복잡한 의존성(`boost` 등)이 있는 `flushToQueue` 같은 메서드는 `template<>` 특수화를 통해 `.cpp`에 정의함으로써 빌드 시간과 의존성을 분리했습니다.
