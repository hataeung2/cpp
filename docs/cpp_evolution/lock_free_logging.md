# C++ Evolution: 잠금을 쓰는 Logger에서 스레드별 버퍼로

## Why
010-08에서 `atugcc::core::Logger`는 히스토리를 뮤텍스 하나로 감싸서 공유해도 안전해졌습니다. Release 빌드, 스레드 8개, 실시간 출력 없음으로 재 보니, 공유 Logger의 호출 지연 p99는 스레드마다 Logger를 하나씩 둔 경우의 37배(Linux), 12.7배(Windows)였고, 처리량은 그 경우의 26 %와 47 %였습니다([010-08 testrecord](/docs/tasks/feature_010-08-logger-cleanup/testrecord.md)). 실시간 출력을 켜면 스트림 쓰기 자체(한 줄에 5–9 µs, p99는 수백 µs)가 로그를 남기는 모든 스레드에서 돌았습니다. 그리고 crash dump에는 죽은 스레드의 줄만 남았습니다. 태스크 010-09는 공유 상태를 hot path 밖으로 옮깁니다.

## C++11/17 (Legacy): 잠금 하나, 스트림 하나
```cpp
class Logger {
  std::mutex m_;
  std::ofstream out_;
public:
  void log(const std::string& line) {
    std::lock_guard lock(m_);   // every thread waits here
    out_ << line << '\n';       // and pays for the write
  }                             // a crash loses what is still in out_'s buffer
};
```
`std::queue` + `std::condition_variable`을 쓰는 백그라운드 스레드를 두면 쓰기는 호출자에게서 떼어 낼 수 있지만, 큐의 뮤텍스가 여전히 공유 지점 하나이고, 프로세스가 죽으면 큐도 사라집니다.

## C++20: 스레드별 SPSC 버퍼와 소비자 하나
```cpp
// producer: the calling thread, its own buffer, no lock
auto& buf = detail::threadBuffer();                     // thread_local handle, buffer from a registry
buf.tryWrite(now, seq, loggerId, level, line);          // fill slots, then
                                                        // writePos.store(w + n, std::memory_order_release)
// consumer: one log thread for all buffers
const auto w = buf.writePos();                          // acquire: sees the filled slots
/* read slots [readPos, w), sort by time, write to sinks */
buf.advanceRead(w);                                     // release: slots may be reused
```
- **버퍼마다 생산자 하나, 소비자 하나**: 원자 변수 두 개(`writePos`는 그 스레드만 쓰고, `readPos`는 로그 스레드만 씀)가 뮤텍스를 대신합니다. 각 스레드는 자기 캐시 라인만 건드립니다.
- **공유 카운터 없음**: 줄은 `steady_clock` 시간과 스레드별 번호로 정렬합니다. 전역 `fetch_add` 순번은 이 변경이 없애려는 바로 그 공유 캐시 라인이 됩니다.
- **카운터 없이 순서 지키기(010-09-01)**: 소비자는 느린 스레드가 따라올 수 있도록 1 ms보다 어린 기록을 잡아 두지만, 바쁜 스레드가 느려지지 않도록 반쯤 찬 버퍼는 바로 가져갑니다. 이것을 버퍼마다 따로 하면, `join()` 뒤에 시작한 스레드가 자신이 기다린 스레드의 마지막 줄들보다 먼저 전달될 수 있었습니다. 그래서 drain은 두 번에 나눠 돕니다. 첫 번째는 그런 버퍼마다 `writePos`(acquire)와 마지막 기록의 시간을 읽고, 그중 가장 새로운 시간이 기준(cutoff)이 됩니다. 두 번째는 모든 버퍼에서 기준까지의(또는 1 ms 한도 중 더 늦은 쪽까지의) 기록을 가져갑니다. 호출 a가 호출 b보다 먼저 일어났다면(happens before), a는 b의 타임스탬프를 찍기 전에 게시되었습니다. b가 기준 때문에 선택되었다면 b의 타임스탬프는 기준 기록의 것보다 늦지 않고, 기준 기록은 첫 번째가 그것을 읽기 전에 게시되었습니다. b가 1 ms 한도보다 오래되어 선택되었다면 a도 그 시점 전에 게시되었습니다. 어느 쪽이든 그 둘 다 뒤에 a의 버퍼를 읽는 두 번째는 a를 보고, a의 버퍼에서 a 앞에 있는 기록은 어느 것도 그 경계(기준과 1 ms 한도 중 더 늦은 쪽)보다 새로울 수 없습니다(모두 a보다 먼저 게시되었으니까). 그래서 a는 b와 함께 선택됩니다. 약속하는 것은 Logger 하나의 줄들 사이의 happens-before 순서(같은 스레드, `join`, 뮤텍스, release/acquire)입니다. 다만 서로 다른 스레드에서 같은 시계 눈금을 읽은 두 호출은 예외입니다: 같은 시간은 스레드 번호로 정렬하고, 이것은 happens-before 순서를 따르지 않습니다. 그런 순서가 없는 스레드들은 시간으로만 정렬합니다.
- **깨우기를 놓치는 버그 없이 깨우기**: 소비자는 시간 제한(drain 간격, 기본 5 ms)을 둔 condition variable에서 기다리고, 생산자는 `Warn` 이상이거나 버퍼가 반쯤 차면 일찍 알립니다. 알림을 하나 놓쳐도 잃는 것은 최대 한 간격입니다. 버퍼가 꽉 찬 생산자는 잠금에서 막히는 대신 기한까지 물러서며 기다립니다(`yield`, 그다음 `sleep_for(50us)`).
- **`std::jthread` + `std::stop_token`**은 소비자를 깔끔하게 멈추게 하고, `std::atexit` / `std::at_quick_exit`는 프로세스가 끝나기 전에 drain합니다.

## crash 뒤에도 로그를 남기는 부분
- 버퍼는 각각 포인터 없는 연속된 블록 하나이고 **해제되지 않으므로**, signal handler가 레지스트리를 훑으며(`forEachBuffer`, acquire load만) 미리 열어 둔 파일에 모든 블록을 `write(2)`할 수 있습니다. 소비된 슬롯은 생산자가 필요로 할 때까지 그 자리에 남으므로, 덤프에는 전달되었든 아니든 모든 스레드의 가장 새로운 기록이 들어갑니다.
- 덮어쓰는 중인 기록은 세 번째 위치 `reservePos`로 걸러 냅니다. 이 값은 슬롯을 건드리기 전에 게시됩니다(`std::atomic_thread_fence(std::memory_order_seq_cst)`가 일반 store들보다 앞서게 합니다).
- handler 경로는 `write`, `sigaction`, `raise`, 원자 변수, 손으로 쓴 정수 포맷터만 씁니다: `snprintf` 없음, `std::string` 없음, 할당 없음, 잠금 없음(async-signal-safety). 스레드마다 둔 대체 시그널 스택(`sigaltstack`; Windows는 `SetThreadStackGuarantee`) 덕분에 스택 오버플로 뒤에도 돌 수 있습니다.
- `tools/read_dump.py`는 날것의 블록을 시간순 텍스트로 되돌리고, 로그 스레드가 아직 전달하지 않은 기록에 표시를 합니다.

## 메모리 매핑 파일에 둔 버퍼 (010-10)
프로세스가 밖에서 죽으면(SIGKILL, `TerminateProcess`) crash handler가 돌 수 없습니다. 버퍼 자체가 파일 매핑 안에 있으면 OS가 그 바이트를 파일에 남기고, 다음 실행이 그것을 읽을 수 있습니다.

```cpp
// C++11/17: map the file and treat the bytes as a struct
auto* hdr = reinterpret_cast<Header*>(mmap(...));   // no object lives there: strictly UB
if (hdr->count > 0) { ... }                         // and a corrupt file is trusted as is
```
```cpp
// C++20 (atugcc): the writer starts each object's lifetime, the reader copies and checks
ThreadLogBuffer::createIn(base + offset, slots);   // placement new: std::atomic members are real objects
std::atomic_ref<std::uint64_t>(header.arenaUsed)    // plain header fields, updated atomically in place
    .compare_exchange_weak(used, used + need);
MapHeader h;  std::memcpy(&h, bytes, sizeof h);     // recovery: copy into a trivially copyable struct,
if (h.fileBytes != size || ...) { /* .corrupt */ }  // validate every size and position before use
```
- 이미 있는 trivially copyable 구조체에 `memcpy`로 바이트를 복사하는 것은 예전부터 잘 정의되어 있었습니다. P0593(C++20)은 `memcpy`, `malloc` 같은 연산이 객체를 암묵적으로 만든다는 규칙을 더했고, 쓰는 쪽의 placement new는 수명을 명시적으로 시작합니다. `std::atomic_ref`(C++20)는 구조체를 복사 불가로 만들지 않고 일반 필드에 원자적으로 접근하게 해 줍니다.
- C++23의 `std::start_lifetime_as<T>(p)`(P2590)는 "이 바이트는 `T`다"라고 바로 말합니다. MSVC와 GCC가 아직 제공하지 않으므로 atugcc는 `memcpy`를 유지합니다.
- 어떤 기록을 잃은 것으로 칠지는 crash dump와 같은 위치들로 정합니다. 소비자는 모든 sink가 기록을 받은 뒤에만 `readPos`를 옮기므로, `[readPos, writePos)`에는 어느 sink도 받지 못한 기록이 모두 있습니다. 죽기 직전에(`readPos`가 옮겨지기 전에) 파일에 쓰인 기록은 양쪽에 다 나올 수 있습니다.
- [`detail/log_map.hpp`](/include/atugcc/core/detail/log_map.hpp)(형식), `src/core/log_map_recover.cpp`(복구), 스펙 [010-10](/docs/specs/010_10_logger_mapped_buffers.md).

## C++23 (Current, atugcc)
- [`logger.hpp`](/include/atugcc/core/logger.hpp): `Delivery::Async` / `Sync`, `OverflowPolicy::BlockThenDrop` / `Block`, `Durability::Process` / `System`, `flush()`, `droppedCount()`.
- [`detail/thread_log_buffer.hpp`](/include/atugcc/core/detail/thread_log_buffer.hpp), [`detail/log_registry.hpp`](/include/atugcc/core/detail/log_registry.hpp), [`detail/log_service.hpp`](/include/atugcc/core/detail/log_service.hpp).
- 실패는 값입니다(`atugcc::core::Result`를 통한 `std::expected`): 잘못된 `configureLogBuffers` 값, 열 수 없는 로그 파일.
- 측정 결과: [010-09 testrecord](/docs/tasks/feature_010-09-logger-thread-buffers/testrecord.md) (AC-1).
- 레슨: [`log_recovery`](/lessons/tracks/01_essentials/12_log_recovery/README.md)(essentials 트랙)는 정리 없이 실행을 끝내고(`std::_Exit`), 다음 실행이 화면에 닿지 못한 줄들을 복구하는 것을 보여 줍니다.
- 레슨: [`lock_free_buffer`](/lessons/tracks/01_essentials/13_lock_free_buffer/README.md)(essentials 트랙)는 release/acquire로 작은 SPSC 링을 만들고, 정해진 시간 동안 뮤텍스 큐와 비교해 재고, false sharing을 보여 주고, 생산자마다 링 하나와 소비자 하나를 돌립니다. 위에서 설명한 스레드별 SPSC 버퍼와 소비자 하나의 구조입니다(스레드마다 `ThreadLogBuffer` 하나).
