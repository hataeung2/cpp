---
id: 010-09
title: Logger 스레드별 버퍼와 소비자 스레드 — 잠금 없는 기록, 모든 스레드의 crash dump, 실패 유형별 로그 보존
depends_on: [010-08]
unblocks: [070-03, 010-10]
approved: null
---

# Spec 010-09: Logger 스레드별 버퍼와 소비자 스레드

방향(사용자, 2026-10-30): 070-03보다 먼저 한다. **프로그램 안정성**과 **로그가 무조건 남아야 하는 안정성**을 함께 고려한다. 근거: 010-08 측정에서 공유 `Logger`의 8스레드 p99가 스레드별의 37배(Linux), 12.7배(Windows)였고, 실시간 출력을 켜면 공유 스트림 쓰기(줄당 5~9µs, p99 수백 µs)가 호출 스레드의 비용을 지배했다([010-08 testrecord](/docs/tasks/feature_010-08-logger-cleanup/testrecord.md)).

## 0. Assumptions (please review)
| # | Decision | Rejected alternative | Why |
|---|---|---|---|
| 1 | **구조**: 스레드마다 잠금 없는 SPSC 기록 버퍼(`ThreadLogBuffer`, 생산자 = 그 스레드, 소비자 = 로그 스레드) + 프로세스 전역 버퍼 목록(`LogRegistry`) + 소비자 스레드 하나(`LogService`). `Logger::log`는 줄을 만들어 자기 스레드 버퍼에 넣고 돌아온다. 이력(`snapshot()`), 실시간 출력, 파일은 소비자 스레드가 쓴다 | 공유 MPSC 큐 하나 / Logger마다 소비자 스레드 | 공유 큐는 모든 스레드가 한 cache line(꼬리 포인터)을 두고 다툰다. 측정에서 문제가 된 것이 바로 공유 지점이다. Logger마다 스레드를 두면 기능별 Logger 권장(010-08)과 충돌한다 |
| 2 | **보존 보장은 실패 유형별로 정한다**(§2.4 표). 프로세스 안에서 일어나는 모든 종료(정상 종료, 스레드 종료, 예외, `std::terminate`, `abort`, SIGSEGV/SIGBUS/SIGFPE/SIGILL, Windows 예외, 스택 오버플로)에서 마지막 기록이 파일이나 crash dump에 남는다. 프로세스 밖에서 끝내는 경우(SIGKILL, `TerminateProcess`, OOM killer, 전원 차단)는 **이미 파일에 쓴 줄**만 남고, 메모리에 있던 줄은 drain 간격만큼 잃을 수 있다 | "무조건"을 그대로 약속 | 프로세스 밖에서 강제로 끝내면 프로세스 안의 어떤 코드도 돌지 않는다. 못 지키는 약속은 적지 않는다. 그 빈틈을 줄이는 방법(Assumption 12)을 따로 둔다 |
| 3 | **버퍼가 가득 찼을 때(소비자가 밀릴 때)**: `OverflowPolicy::BlockThenDrop`(기본, 최대 100 ms 기다린 뒤 버리고 개수를 센다) / `OverflowPolicy::Block`(절대 버리지 않고 기다린다). 버린 경우 다음에 전달되는 줄 앞에 `[atugcc] dropped N lines` 표시 줄이 들어가고, `Logger::droppedCount()`로도 보인다. 조용히 버리는 일은 없다 | 항상 Block / 항상 덮어쓰기(지금의 eviction) | 두 안정성이 정면으로 부딪히는 곳이다. 파일 sink가 멈추면(디스크 가득, 네트워크 드라이브) Block은 프로그램 전체를 멈춘다. 기본값은 프로그램을 살리고 손실을 드러내는 쪽, 로그가 더 중요한 곳은 `Block`을 고른다. 100 ms는 제안값 |
| 4 | **전달 방식**: `Delivery::Async`(기본: 버퍼에 넣고 바로 돌아옴) / `Delivery::Sync`(소비자가 그 줄을 이력·출력·파일에 쓴 뒤 돌아옴). 언제든 `Logger::flush()`로 그 시점까지의 줄이 전달되기를 기다릴 수 있다. `snapshot()`은 먼저 `flush()`한다 | 항상 Sync(010-08과 같음) / 항상 Async | Async가 성능 목표의 핵심이다. 하지만 레슨처럼 로그와 `std::cout` 직접 출력의 순서가 중요한 곳, 또는 "이 줄이 디스크에 닿은 뒤 다음 일을 하라"가 필요한 곳(결제, 설정 변경)을 위해 Sync를 둔다 |
| 5 | **파일 sink**: `Config::filePath`(비어 있으면 없음). 소비자는 묶음(batch)마다 OS 쓰기(POSIX `write`, Windows `WriteFile`)로 쓴다. C++ 스트림 버퍼에 머무르지 않으므로 쓴 직후 프로세스가 죽어도 남는다. `Durability::Process`(기본) / `Durability::System`(묶음마다 `fsync`/`FlushFileBuffers`: OS 충돌·전원 차단에도 남음, 느림). 회전(rotation)은 하지 않는다 | `std::ofstream` / 회전 포함 | "남아야 하는" 로그의 영구 목적지가 지금은 없다(이력은 메모리, 실시간 출력은 콘솔). `std::ofstream`은 프로세스 crash 때 버퍼를 잃는다. 회전은 범위를 키운다(Out of Scope) |
| 6 | **crash dump = 모든 스레드의 최근 기록**: 버퍼는 소비자가 이미 읽은 칸도 생산자가 새로 덮기 전까지 그대로 둔다. crash 처리기는 목록의 모든 버퍼(종료된 스레드의 버퍼 포함)에서 최근 칸을 미리 연 dump 파일에 그대로 쓴다. 각 칸에 "전달됨/전달 안 됨"이 표시된다. 형식은 `DUMP-V2`. 새 도구 `tools/read_dump.py`가 시간 순으로 합쳐 텍스트로 만든다 | crash한 스레드만(지금) / 전달 안 된 줄만 | crash 원인은 다른 스레드에 있는 경우가 많다. 파일 sink가 없을 때도 dump만으로 마지막 상황을 읽을 수 있어야 한다. 지금은 dump의 로그 블록을 읽는 도구가 없다(`symbolize_dump.py`는 crash 주소만 읽음) |
| 7 | **crash 처리 범위**: Linux SIGSEGV, SIGBUS, SIGFPE, SIGILL, SIGABRT. Windows 처리되지 않은 SEH 예외 + SIGABRT. 양쪽 `std::set_terminate`(처리되지 않은 C++ 예외): 소비자가 살아 있으면 짧게(최대 200 ms) 파일까지 전달한 뒤 dump하고 `abort`. **스택 오버플로**: 버퍼를 등록하는 스레드마다 대체 시그널 스택(`sigaltstack`), Windows는 `SetThreadStackGuarantee`. 처리기는 재진입을 막고(두 번째 crash는 기본 동작), 이전에 있던 처리기(sanitizer, 사용자 처리기)를 dump 뒤에 이어 부른다 | SIGSEGV만(지금) | 지금은 `abort`, `assert`, 처리되지 않은 예외, 스택 오버플로에서 로그가 남지 않는다. 마지막 두 가지가 실제 crash의 큰 몫이다 |
| 8 | **signal-safe(KI-026)**: crash 경로는 원자적 load, 미리 연 fd/HANDLE에 `write`/`WriteFile`, 직접 만든 정수→문자 변환만 쓴다. `snprintf`, `std::string`, 할당, lock을 쓰지 않는다. 실행 파일 경로는 준비 때 고정 `char` 배열에 담는다 | 지금 처리기 유지 | KI-026 |
| 9 | **순서**: 각 줄에 `steady_clock` 시각(ns)과 스레드별 순번을 단다. 소비자와 `read_dump.py`는 시각 순으로 합치고, 같은 시각이면 스레드 번호 순. 전역 순번(atomic 하나)은 쓰지 않는다. 파일과 출력 줄 앞에는 사람이 읽는 시각(`system_clock`, 준비 때 한 번 맞춘 기준점 + steady 차이)을 붙인다 | 전역 `fetch_add` 순번 | 전역 순번은 모든 스레드가 한 cache line을 다투는 공유 지점이라 1번의 목적과 어긋난다. 서로 동기화하지 않은 두 스레드의 줄 사이에 "진짜 순서"는 없으므로 시각 순이면 충분하다. 스레드 안의 순서는 순번으로 정확하다 |
| 10 | **수명**: 버퍼 목록과 버퍼는 **프로세스가 끝날 때까지 해제하지 않는다**(정적 소멸 뒤의 crash에도 dump 가능). 스레드가 끝나면 버퍼는 "은퇴"로 표시되고, 소비자가 다 읽은 뒤 새 스레드가 다시 쓴다(스레드 수만큼만 메모리를 씀). `LogService`는 첫 `Logger`가 만들 때 시작하고, 정상 종료(`std::exit`, `main` 반환, `std::quick_exit`)에서 남은 줄을 모두 전달한 뒤 멈춘다. 멈춘 뒤의 `log()`는 호출 스레드가 직접 전달한다(잃지 않음). `Logger` 소멸자는 자기 줄이 모두 전달될 때까지 기다린다 | 버퍼를 thread_local 객체로 / 정적 소멸에서 정리 | crash 기반 시설은 마지막까지 살아 있어야 한다. 의도적으로 해제하지 않는 것은 흔한 방식이다(메모리는 OS가 회수) |
| 11 | **크기(제안값)**: 칸 256 B(머리 24 B + 내용 232 B, 긴 줄은 이어지는 칸), 스레드당 512칸(128 KiB). 소비자는 5 ms마다 깨어나고, `Warn` 이상의 줄이나 버퍼 절반을 넘는 순간 바로 깨운다(C++20 `std::atomic::wait/notify`) | 더 작게 / 런타임 설정 | 128 KiB × 스레드 수는 데스크톱·서버에서 작다. 5 ms는 SIGKILL 때 잃을 수 있는 최대 시간(Assumption 2)을 정한다. 런타임 설정은 필요해지면 KI |
| 12 | **SIGKILL·강제 종료 대비(메모리 매핑 파일 버퍼)는 010-10으로 나눈다**: 버퍼를 메모리 매핑 파일 위에 두면 프로세스가 강제로 죽어도 OS가 그 내용을 파일에 남기고, 다음 실행 때 복구할 수 있다(모바일 로그 라이브러리들이 쓰는 방식) | 010-09에 포함 | 매핑 수명, 복구 형식, 두 플랫폼 분기가 더해져 위험 단위가 크게 는다. 010-09의 버퍼 형식을 매핑에 그대로 올릴 수 있게 설계해 두고(칸이 고정 크기, 포인터 없음), 하는지는 사용자가 정한다 |
| 13 | **`LogQueue`(전역 SPSC 큐)와 `RingBuffer::flushToQueue()`를 없앤다**. 이것이 Boost의 유일한 사용처이므로 Boost 의존도 없앤다(`vcpkg.json`의 의존 목록은 비우고 manifest는 남겨 엔진 작업의 의존을 받는다). `RingBuffer` 클래스는 일반 컨테이너로 남는다(테스트, 레슨 후보 E12). `DbgBuf`는 같은 API로 `ThreadLogBuffer`를 쓴다 | 큐 유지 / Boost 유지 | 소비자가 생기면 큐는 쓸 곳이 없다. 090-03(사용자 결정)이 Boost를 공급하려고 만든 manifest는 이후 의존을 위해 남긴다 |
| 14 | **KI-027**: `logger.hpp`는 `memory_dump.hpp`(와 `<Windows.h>`)를 include하지 않는다. 필요한 선언은 작은 헤더(`detail/log_service.hpp`)로 | 그대로 | KI-027 |
| 15 | **레슨**: `02_thread_and_log`는 끝에서 `std::cout`으로 결과를 찍기 전에 `logger.flush()`를 부른다(줄 순서 유지). 기능별 Logger 설명은 그대로 | 레슨을 `Delivery::Sync`로 | flush는 Async의 사용법 자체를 보여 준다 |

## 1. Objective
- 하나의 `Logger`를 여러 스레드가 써도 **잠금 없이** 기록하고, 출력·파일 쓰기 비용을 호출 스레드에서 뗀다.
- 프로세스 안에서 일어나는 모든 종료에서 **모든 스레드의 마지막 기록**이 파일이나 crash dump에 남게 한다.
- 남지 못하는 경우(프로세스 밖의 강제 종료)를 정확히 적고, 그 손실을 drain 간격으로 묶는다.
- 버퍼가 넘칠 때 프로그램을 멈출지 로그를 버릴지를 사용자가 고르게 하고, 버린 사실은 반드시 드러낸다.

## 2. Requirement Details

### 2.1 Public API Surface
[`include/atugcc/core/logger.hpp`](/include/atugcc/core/logger.hpp)
```cpp
enum class Delivery : std::uint8_t { Async, Sync };
enum class OverflowPolicy : std::uint8_t { BlockThenDrop, Block };
enum class Durability : std::uint8_t { Process, System };

struct Config {                       // 010-08 필드는 그대로
    std::size_t bufferCapacity = kDefaultBlockCount;   // snapshot() 이력 줄 수
    std::ostream* liveOutput = nullptr;
    std::filesystem::path dumpDir = "log";
    bool enableCrashDump = true;
    // 010-09
    std::filesystem::path filePath{};                   // 비면 파일 sink 없음
    Delivery delivery = Delivery::Async;
    OverflowPolicy overflow = OverflowPolicy::BlockThenDrop;
    std::chrono::milliseconds overflowWait{100};
    Durability durability = Durability::Process;
};

class Logger {
public:
    // log(...) 오버로드 3개, snapshot(), dump(), global(), levelName(): 010-08 시그니처 그대로
    void flush();                                   // 이 호출 전에 이 Logger로 쓴 줄이 모두 전달될 때까지
    [[nodiscard]] std::uint64_t droppedCount() const noexcept;
    ~Logger();                                      // 자기 줄을 모두 전달한 뒤 등록 해제
};
```
[`include/atugcc/core/ring_buffer.hpp`](/include/atugcc/core/ring_buffer.hpp): `flushToQueue()`, `kNoAutoFlush`, 임계값 생성자 인자 삭제. `DbgBuf::log/dump/dumpToFd/dumpToHandle`은 그대로, `DbgBuf::instance()`는 `ThreadLogBuffer&`를 돌려준다.
[`include/atugcc/core/log_queue.hpp`](/include/atugcc/core/log_queue.hpp), `src/core/log_queue.cpp`: 삭제.
[`include/atugcc/core/memory_dump.hpp`](/include/atugcc/core/memory_dump.hpp): `ensurePrepared`, `preparedPath`, `prepareDumpFile*`, `dump()` 시그니처 그대로. 처리하는 신호와 terminate 처리기가 늘어난다(Assumption 7).

### 2.2 Internal Implementation
- `include/atugcc/core/detail/thread_log_buffer.hpp`: 고정 크기 칸의 SPSC ring. 칸 머리 = 시각(ns), 스레드 순번, Logger id(0 = `DbgBuf` 직접 기록), 레벨, 이어짐 표시, 길이. 쓰기 위치는 생산자만, 읽기 위치는 소비자만 바꾼다(`std::atomic<std::uint64_t>`, release/acquire). 전달 안 된 칸은 덮지 않는다(Assumption 3). crash 처리기는 두 위치를 load해 `[쓰기 - 칸 수 + 1, 쓰기)`를 그대로 쓴다.
- `detail/log_registry.hpp`: 버퍼 목록은 CAS로만 늘어나는 단방향 연결 목록(해제 없음). 스레드가 처음 기록할 때 은퇴한 버퍼를 다시 쓰거나 새로 만든다. `thread_local` 핸들의 소멸자가 버퍼를 은퇴시킨다. 등록 때 그 스레드의 대체 시그널 스택을 설치한다.
- `src/core/log_service.cpp`: 소비자 `std::jthread`. 깨어나면 모든 버퍼에서 전달 안 된 칸을 읽어 시각 순으로 합치고(k-way merge), Logger id로 찾은 sink(이력, 실시간 출력, 파일)에 묶어서 쓴다. 각 Logger의 "전달된 마지막 순번"을 올리고 `flush()`를 기다리는 쪽을 깨운다. `std::atexit` / `std::at_quick_exit`에서 남은 줄을 모두 전달하고 멈춘다.
- 실시간 출력은 소비자 하나만 쓰므로 `std::osyncstream`이 더는 필요 없다. 다만 사용자가 같은 스트림에 직접 쓰는 것과 섞이지 않게 묶음마다 한 번 `write` 후 flush한다.
- crash 처리기(`memory_dump.hpp`): dump 머리(`DUMP-V2`, PID, 신호/예외 코드, crash 스레드 번호) → 기존 `--CONTEXT-BINARY--` 블록(symbolize 호환) → 버퍼마다 `--THREAD <n> <retired>--` + 칸 원본. 그다음 이전 처리기 호출 또는 기본 동작.
- `tools/read_dump.py`: `DUMP-V2`를 읽어 `시각 스레드 레벨 [전달됨/안 됨] 내용` 줄로 시각 순 출력. `--undelivered`로 파일에 없을 수 있는 줄만.
- 테스트용 `tests/core/crash_probe.cpp` + `tests/core/check_crash_dump.py`: 모드별로 crash를 일으키고 dump와 파일을 검사(§5).

### 2.3 Platform Specifics
- Linux: `sigaction`(SA_SIGINFO | SA_ONSTACK), `sigaltstack`(스레드마다), `write`, `fsync`. Windows: `SetUnhandledExceptionFilter`, `signal(SIGABRT)`, `SetThreadStackGuarantee`, `WriteFile`, `FlushFileBuffers`. 공통: `std::set_terminate`.
- 플랫폼 분기는 `src/core/` 안의 파일 하나씩(`crash_handler_posix.cpp`, `crash_handler_win.cpp`)으로 모으고, 공개 헤더에서는 뺀다(KI-027과 같은 이유).
- Windows `steady_clock` 간격(100 ns)은 순서 결정에 충분하다(같은 시각은 스레드 번호로).

### 2.4 보존 보장 (실패 유형별)
| 상황 | 파일 sink(있을 때) | crash dump | 비고 |
|---|---|---|---|
| `main` 반환, `std::exit`, `std::quick_exit` | 모든 줄 | — (빈 파일 정리, 010-08) | atexit / at_quick_exit에서 drain |
| 스레드 종료 | 모든 줄 | 은퇴 버퍼도 포함 | 버퍼는 다 읽힌 뒤 재사용 |
| `Logger` 소멸 | 그 Logger의 모든 줄 | — | 소멸자가 기다림 |
| 처리되지 않은 C++ 예외, `std::terminate` | 소비자가 200 ms 안에 전달한 줄까지 | 모든 스레드의 최근 512칸 | 그다음 `abort` |
| `abort`, `assert` 실패, SIGSEGV/SIGBUS/SIGFPE/SIGILL, Windows 예외 | crash 전에 이미 쓴 줄 | 모든 스레드의 최근 512칸 | signal-safe 경로만 |
| 스택 오버플로 | 위와 같음 | 위와 같음 | 대체 스택 / 스택 보장 |
| 버퍼 넘침(`BlockThenDrop`) | 버린 개수 표시 줄 | — | `droppedCount()` |
| SIGKILL, `TerminateProcess`, OOM killer | crash 전에 이미 쓴 줄(drain 간격 5 ms + 쓰기 시간 이전 줄) | 없음 | 010-10이 메울 빈틈 |
| OS 충돌, 전원 차단 | `Durability::System`이면 이미 쓴 줄, 아니면 OS가 아직 디스크에 안 쓴 줄은 잃음 | 없음 | |
| `_exit`, `fork` 뒤 자식 | 다루지 않음 | 다루지 않음 | Out of Scope |

## 3. C++ Standard Evolution
| Approach | Standard | Description |
|----------|----------|-------------|
| Legacy | C++11/14/17 | 전역 mutex + `std::ofstream` 로거, 또는 조건 변수로 깨우는 큐. crash 때 스트림 버퍼의 내용을 잃음 |
| Modern | C++20 | `std::atomic::wait/notify_one`(조건 변수 없이 소비자 깨우기·넘침 대기), `std::jthread` + `std::stop_token`(소비자 수명), `std::span`(칸 접근) |
| Latest | C++23 | `std::expected`로 sink 실패 보고, `std::to_underlying`, `std::unreachable` 대신 명시적 처리 |

Reference: `/docs/cpp_evolution/lock_free_logging.md` (새로 씀: 공유 mutex 로거 → 스레드별 SPSC 버퍼 + 소비자, 010-08 측정 숫자 포함).

## 4. Edge Cases
- [ ] Thread safety / memory ordering — SPSC 위치는 release/acquire. crash 처리기는 다른 스레드가 쓰는 중인 칸을 볼 수 있다: 쓰기 위치보다 앞(공개 전)인 칸은 쓰지 않는다. 버퍼 목록은 CAS로만 추가. 소비자와 `flush()` 대기자는 Logger별 전달 순번(atomic) + `wait/notify`. TSan: 생산 8스레드 + flush + snapshot + 스레드 생성·종료 반복
- [ ] Resource lifetime — 버퍼·목록은 해제하지 않음. `liveOutput` 스트림과 파일은 Logger보다 오래 살아야 함(지금과 같음); Logger 소멸자가 drain을 기다리므로 소멸 뒤 소비자가 그 스트림을 만지지 않는다. `thread_local` 핸들 소멸 순서: 같은 스레드의 다른 thread_local 소멸자가 로그를 쓰면 은퇴한 버퍼가 아니라 호출 스레드 직접 전달로
- [ ] Platform differences — §2.3. Windows에서 `abort()`의 SIGABRT 처리기, terminate 처리기가 둘 다 불릴 수 있다: 재진입 막기로 dump는 한 번
- [ ] Template instantiation — 기록 경로의 템플릿은 `log()`의 포맷까지만. 버퍼는 비템플릿
- [ ] ODR — 전역 상태는 `.cpp` 하나씩에. 헤더의 `inline` 함수 안 static 금지(010-08의 `ensurePrepared` 상태도 `.cpp`로 옮김)
- [ ] Undefined behaviour / signal-handler safety — Assumption 8. 처리기 재진입, crash 중 crash. 같은 스레드에서 기록 도중 신호(칸을 쓰다 만 상태): 쓰기 위치 공개 전이라 dump에서 빠짐
- [ ] 소비자 스레드가 crash한 경우 — 처리기는 프로세스 전역이라 그대로 dump한다
- [ ] 정적 초기화 순서 — 다른 정적 객체의 생성자에서 `Logger::global()`을 써도 `LogService`가 먼저 완성된다(함수 안 static)
- [ ] 아주 긴 줄 — 칸 512개를 넘는 줄은 잘라서 `…(truncated N bytes)`를 붙인다
- [ ] `Delivery::Sync`를 소비자 스레드 자신(sink 콜백 안)에서 부름 — 교착을 막으려고 그 경우엔 Async로 처리

## 5. Acceptance Criteria
| ID | Criterion | Verified by |
|---|---|---|
| AC-1 | `logger_contention_probe`(010-08) Release, 실시간 출력 끔, 4·8스레드: 공유 Logger(A)의 p99가 스레드별(B)의 2배 이하, 처리량이 B의 80% 이상. 실시간 출력을 켜도 A의 호출 p99가 출력 끔의 3배 이하 | Release 측정(Linux, Windows), testrecord |
| AC-2 | 8스레드 × 100,000줄(그중 4스레드는 중간에 끝나고 새 스레드로 바뀜) 뒤 정상 종료: 파일에 모든 줄이 정확히 한 번, 스레드 안 순서대로, 전체는 시각 비내림차순 | `crash_probe normal` + `check_crash_dump.py` |
| AC-3 | 4스레드가 기록하는 중 다른 스레드에서 SIGSEGV / `abort()` / 처리되지 않은 예외 / 스택 오버플로를 일으키면, dump에 **모든 스레드**(이미 끝난 스레드 포함)의 crash 직전 표시 줄이 있다. Linux, Windows 모두 | `crash_probe segv|abort|terminate|stackoverflow` + `check_crash_dump.py` |
| AC-4 | AC-3의 각 경우, crash 전에 `Delivery::Sync`로 쓴 줄은 파일에 있다. terminate 경우엔 Async 줄도 200 ms 안에 전달된 만큼 파일에 있다 | 같은 검사 |
| AC-5 | Linux에서 표시 줄을 쓰고 50 ms 뒤 SIGKILL(Windows `TerminateProcess`): 그 줄이 파일에 있다 | `crash_probe killme` + 검사 스크립트 |
| AC-6 | sink가 멈춘 동안: `BlockThenDrop`은 `log()`가 `overflowWait` + 50 ms 안에 돌아오고, sink가 풀리면 `dropped N lines` 표시 줄이 나오며 `droppedCount()` = N. `Block`은 줄을 잃지 않는다 | GoogleTest(테스트용 막히는 sink) |
| AC-7 | `Delivery::Sync`의 `log()`가 돌아오면 그 줄이 이력·실시간 출력·파일에 있다. `flush()` 뒤에는 그 전 모든 줄이 있다. `snapshot()`은 호출 전의 줄을 모두 담는다 | GoogleTest |
| AC-8 | `Logger` 소멸자가 돌아오면 그 Logger의 줄이 모두 전달돼 있고, 소멸 뒤 소비자가 그 Logger의 스트림을 만지지 않는다 | GoogleTest + ASan |
| AC-9 | crash 경로에 `snprintf`, `std::string`, `new`/`malloc`, lock이 없다(KI-026) | 코드 리뷰 + `grep` + codex 리뷰 |
| AC-10 | Windows에서 `logger.hpp`만 include한 파일이 `std::min(a, b)`를 쓸 수 있다(KI-027) | 컴파일 테스트(`(std::min)` 없이) |
| AC-11 | Boost 없이 모든 preset이 configure·build된다. `log_queue.hpp`와 `flushToQueue`가 없다 | 빌드 + `grep -c` |
| AC-12 | `tools/read_dump.py`가 `DUMP-V2`를 시각 순 텍스트로 바꾸고, 전달 안 된 줄을 표시한다. `symbolize_dump.py`가 새 dump에서도 crash 주소를 찾는다 | Python unittest + AC-3 dump로 실행 |
| AC-13 | 010-08의 모든 테스트(바뀐 API에 맞게 고친 것 포함), 레슨 4개, `PlaygroundServer`가 통과하고, Windows `/W4 /WX`, Linux, ASan, TSan에서 경고 없이 전체 suite가 통과한다 | `build.py --test` 4 preset |

## 6. Out of Scope
- 메모리 매핑 파일 버퍼와 다음 실행 때 복구(SIGKILL·강제 종료의 빈틈) — 010-10(사용자 결정)
- 로그 파일 회전, 압축, 원격 전송 — 필요해지면 새 작업
- 레벨 필터 — 필요해지면 새 작업
- `fork()` 뒤 자식 프로세스, `_exit` — 다루지 않음(헤더에 적음)
- 신호 처리기 안에서 `Logger::log` 호출 — 지원하지 않음(헤더에 적음)

## 7. Dependencies & Backends
Boost 제거(Assumption 13). 새 외부 의존 없음. 파일 쓰기는 `src/core/` 안의 플랫폼 파일 두 개 뒤에 둔다.

## 8. Documentation Updates
| Document | Section | Change |
|---|---|---|
| [`include/atugcc/core/logger.hpp`](/include/atugcc/core/logger.hpp) | 클래스 주석 | 전달 방식, 넘침 정책, 보존 보장 표 요약, 신호 처리기 안 사용 금지 |
| [`include/atugcc/core/ring_buffer.hpp`](/include/atugcc/core/ring_buffer.hpp) | 파일 주석 | 일반 컨테이너로, `DbgBuf`는 스레드 기록 버퍼 사용 |
| `docs/cpp_evolution/lock_free_logging.md` | 새 문서 | §3 |
| [`lessons/tracks/01_essentials/02_thread_and_log/README.md`](/lessons/tracks/01_essentials/02_thread_and_log/README.md), `main.cpp` | 계약, `flush()` | Async와 flush, 보존 보장 |
| [`docs/tasks/feature_error-expected/usage/symb-dump-relwithdebinfo.md`](/docs/tasks/feature_error-expected/usage/symb-dump-relwithdebinfo.md) | — | 봉인된 기록이라 바꾸지 않음. 새 사용법은 `tools/read_dump.py --help`와 루트 README |
| [`README.md`](/README.md) | 구조, 의존성 | Boost 제거, `tools/read_dump.py` |
| [`docs/known_issues.md`](/docs/known_issues.md) | KI-026, KI-027 | CLOSED by 010-09 |
| [`docs/tasks/lesson_candidates.md`](/docs/tasks/lesson_candidates.md) | E12, E13 | 새 버퍼와 crash dump로 갱신 |
| [`.agent/rules/config.md`](/.agent/rules/config.md) | vcpkg / Boost, 문제 해결 표 | Boost 줄 삭제, manifest는 이후 의존용 |
| [`README.md`](/README.md) | 빌드 준비 1번 | "Boost.Lockfree is required"와 `libboost-dev` 삭제 |

## 9. Technical Constraints
- Compiler: MSVC (VS 2026) / GCC 13+, C++23 (C++20 minimum), `std::atomic::wait`
- CMake 3.26+, preset으로만 빌드

## 10. Context & References
- [010-08 spec](/docs/specs/010_08_logger_cleanup.md), [010-08 testrecord](/docs/tasks/feature_010-08-logger-cleanup/testrecord.md)
- [logger.hpp](/include/atugcc/core/logger.hpp), [memory_dump.hpp](/include/atugcc/core/memory_dump.hpp), [ring_buffer.hpp](/include/atugcc/core/ring_buffer.hpp), [log_queue.hpp](/include/atugcc/core/log_queue.hpp), [symbolize_dump.py](/tools/symbolize_dump.py)

## 11. Implementation Plan
- [ ] Step 1: `ThreadLogBuffer` + 단위 테스트(SPSC, 덮지 않음, crash 읽기 범위) — Risky
- [ ] Step 2: `LogRegistry`(CAS 목록, 은퇴·재사용, 대체 스택) + TSan 테스트 — Risky
- [ ] Step 3: `LogService`(소비자, merge, sink, flush, atexit) + `Logger` 연결, `DbgBuf` 이전, `LogQueue`·Boost 제거 — Risky
- [ ] Step 4: crash 처리기 재작성(신호 확대, terminate, 모든 버퍼 dump, signal-safe, 이전 처리기 연결), 플랫폼 파일 분리(KI-026, KI-027) — Risky
- [ ] Step 5: 파일 sink(OS 쓰기, `Durability`) — Risky(플랫폼)
- [ ] Step 6: `tools/read_dump.py` + unittest, `symbolize_dump.py` 호환
- [ ] Step 7: `crash_probe` + `check_crash_dump.py` + CTest(AC-2 ~ AC-5)
- [ ] Step 8: GoogleTest(AC-6 ~ AC-8), Release 측정(AC-1)
- [ ] Step 9: §8 문서

## 12. Verification Plan
- [ ] `build.py --test`: `windows-x64-debug`, `linux-x64-debug`, `linux-x64-asan`, `linux-x64-tsan`
- [ ] crash 검사는 sanitizer preset에서 sanitizer의 신호 처리와 겹치므로, Debug·Release preset에서 실행하고 sanitizer preset에서는 정상 종료 경우만(testrecord에 기록)
- [ ] mutant: 칸 공개를 release 없이(TSan), 은퇴 버퍼를 dump에서 빼기(AC-3이 잡아야 함)
- [ ] Release 측정(AC-1) 두 플랫폼, 다른 부하 없이
- [ ] `lint_docs.py`, `naming_check.py`, `test_agent_scripts.py`

## History / Amendments
- 2026-10-30: 초안. 사용자 요청: 프로그램 안정성과 로그 보존 안정성을 모두 고려
