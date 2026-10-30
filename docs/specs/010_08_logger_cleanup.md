---
id: 010-08
title: Logger 정비 — 호출 위치, 공유 계약, crash dump 준비, 로그 큐, 공유/스레드별 성능 측정
depends_on: [090-05]
unblocks: [070-03, 010-09]
approved: 2026-10-30
---

# Spec 010-08: Logger 정비

승인: 사용자가 2026-10-30 세션에서 Assumption 1–10을 모두 확인하고 승인함(9번 판단 기준은 "일단 이대로 해 보자").

KI-013, KI-014, KI-021, KI-025를 닫는다. 방향(사용자, 2026-10-30): 정확성 결함을 먼저 고치고, 공유 `Logger`와 스레드별 `Logger`의 성능 trade-off를 **측정으로** 판단한다. 스레드별 버퍼와 소비자 스레드는 측정 결과에 따라 010-09에서 한다.

## 0. Assumptions (please review)
| # | Decision | Rejected alternative | Why |
|---|---|---|---|
| 1 | **계약: 하나의 `Logger`를 여러 스레드가 동시에 써도 안전하다.** 기능별로 `Logger`를 나누는 것은 권장 사용법으로 남긴다(설정·레벨·출력 대상 분리) | "스레드당 하나" 계약 유지 | 지키기 어려운 계약이다. 우리 레슨도 우회했고(KI-014), `Logger::global()`은 그 자체가 공유 싱글턴이다. 2026-10-30 논의: 안정성 이득은 Logger 객체가 아니라 버퍼를 나누는 데서 온다 |
| 2 | 이번 구현은 **lock 하나**로 안전하게 만든다: `log()`는 줄을 lock 밖에서 포맷하고, lock 안에서는 이력에 넣기만 한다. 실시간 출력은 `std::osyncstream`으로 줄 단위로 쓴다 | 바로 스레드별 버퍼 + 소비자 스레드 | 작게 고치고 측정의 기준선으로 쓴다. 측정에서 lock 경쟁이 의미 있게 나오면 010-09가 스레드별 버퍼로 바꾼다(Assumption 9) |
| 3 | 한 줄은 **목적별로 한 번씩만** 저장한다: `snapshot()`용 이력(고정 크기 원형 배열, 앞에서 지우지 않음)과 crash dump용 스레드별 `DbgBuf`. `Logger`의 자체 `RingBuffer m_buffer`는 없앤다 | 세 곳 유지 / 이력 하나로 통합 | `m_buffer`는 아무도 읽지 않는 중복이다. crash 처리기는 signal-safe한 원시 블록(`DbgBuf`)이 필요하고, `snapshot()`은 문자열이 필요해서 둘은 목적이 다르다. 원형 배열이면 가득 찬 뒤에도 줄마다 vector를 당기지 않는다 |
| 4 | **호출 위치(KI-013)**: 포맷 문자열과 `std::source_location`을 함께 잡는 래퍼 `FormatWithLocation<Args...>`를 첫 인자로 받는다. 생성자는 `consteval`이고 `loc = std::source_location::current()`를 기본 인자로 가져, 호출한 줄이 기록된다. `std::type_identity_t`로 인자 추론에서 뺀다 | 매크로(`LOG(...)`) / `loc`를 맨 뒤 기본 인자로(가변 인자 뒤에는 불가) | 매크로 없이 호출 코드가 그대로다(`logger.log(Level::Info, "x {}", v)`). C++20의 알려진 기법이다. 명시적 `log(loc, lv, fmt, args...)` 오버로드는 남긴다 |
| 5 | **crash dump 준비(KI-021)**: `MemoryDump::ensurePrepared(dir)`(새 static 함수)가 프로세스당 **한 번** 처리기를 등록하고 dump 파일을 연다. `Logger`는 `enableCrashDump`일 때만 `cfg.dumpDir`로 이를 부른다. `Logger`는 `MemoryDump` 멤버를 갖지 않는다. 먼저 준비한 디렉터리가 이긴다 | Logger마다 준비 / 마지막 Logger가 이김 | 처리기와 dump 대상은 프로세스 전역 자원이다. 두 번째 준비가 첫 번째를 덮으면 fd가 새고(KI-021) 어느 파일에 쓰일지 알 수 없다 |
| 6 | 정상 종료 때 `ensurePrepared`가 만든 dump 파일이 **비어 있으면 닫고 지운다**. 명시적 `prepareDumpFile`/`prepareDumpFileWin`으로 연 파일은 호출한 쪽 것이므로 지우지 않고, 다시 부르면 이전 것을 닫는다 | 지우지 않음 / 처음부터 열지 않고 crash 때 생성 | crash 때 파일을 여는 것은 signal-safe하지 않아 미리 열어 두는 설계는 유지한다. 대신 정상 실행마다 빈 파일이 쌓이지 않게 한다(레슨 폴더 `log/`의 0바이트 파일들) |
| 7 | **로그 큐(KI-025)**: `RingBuffer`의 자동 flush 기본값을 **끈다**(`kDefaultFlushThreshold`를 "끔" 값으로). `flushToQueue()`와 `globalLogQueue()`는 남기되 "한 번에 한 스레드만, 소비자는 010-09"라고 헤더에 적는다 | 큐를 MPSC로 교체 / 큐 삭제 | 소비자가 없는 지금은 자동 flush가 data race(SPSC에 생산자 여럿)를 만들고, crash 버퍼를 아무도 읽지 않는 큐로 비워 crash 직전 기록을 잃게 한다. 끄면 링 버퍼는 항상 최신 256블록을 갖는다(기존 eviction 정책). 큐 구조는 010-09의 설계 재료라 지우지 않는다 |
| 8 | **측정**: `tests/core/logger_contention_probe.cpp`(`span_cost_probe`와 같은 방식)가 세 방식을 비교한다. (A) 공유 `Logger` 하나, (B) 스레드마다 `Logger`, (C) `DbgBuf::log`만(스레드별 버퍼의 하한, 소비자 비용 제외). 스레드 1/2/4/8, 실시간 출력 끔/켬(켬: 모든 방식이 같은 임시 파일 하나에 씀, C는 해당 없음). 줄당 평균 ns, 호출 지연 p50/p99/max, 세 번 중 가장 빠른 값. Release preset 숫자를 testrecord에 적는다 | 외부 벤치 프레임워크 / 숫자 없이 판단 | 2026-10-30 합의: 숫자를 보고 결정한다. 외부 의존을 늘리지 않는다(020-03이 정한 방침과 같음) |
| 9 | **010-09 판단 기준(제안)**: 실시간 출력을 끈 상태에서 4·8 스레드일 때 (A)의 p99가 (B)의 3배 이상이거나 (A)의 처리량이 (B)의 50% 이하면, 010-09는 공유 `Logger` 안을 스레드별 버퍼 + 소비자 스레드로 바꾼다. 아니면 010-09는 "모든 스레드의 버퍼를 crash dump에 담기"만 한다. 결과와 판단은 testrecord와 010-09 노트에 적고, 최종 결정은 사용자가 한다 | 측정 뒤에 기준을 정함 | 기준을 먼저 적어 두면 숫자를 보고 기준을 맞추는 일을 막는다. 3배·50%는 사용자가 조정할 수 있는 제안값이다 |
| 10 | 레슨 `02_thread_and_log`는 기능별 `Logger` 세 개를 그대로 쓴다(이제 권장 사용법). KI-014를 피하려던 설명과 연습 4번을 "공유도 안전하다, 그럼 언제 나누는가"로 바꾼다 | 레슨 코드를 공유 Logger 하나로 변경 | 코드는 이미 권장 방식이다. 바뀌는 것은 이유다 |

## 1. Objective
`atugcc::core::Logger`를 essentials 레슨(070-03)이 우회 설명 없이 가르칠 수 있는 상태로 만든다.
- 로그 줄에 **호출한 곳**이 찍힌다(지금은 `logger.hpp:41`).
- **여러 스레드가 하나의 `Logger`를 공유해도 안전하다.**
- `Logger`가 설정을 따른다: `enableCrashDump = false`면 crash 처리기와 파일을 건드리지 않고, `dumpDir`을 쓴다. fd가 새지 않는다.
- 소비자 없는 단일 생산자 큐에 여러 스레드가 넣는 data race가 없다.
- 공유 방식과 스레드별 방식의 성능 차이를 숫자로 남겨, 010-09의 범위를 정한다.

## 2. Requirement Details

### 2.1 Public API Surface
[`include/atugcc/core/logger.hpp`](/include/atugcc/core/logger.hpp)
```cpp
template <typename... Args>
struct FormatWithLocation {
    std::format_string<Args...> fmt;
    std::source_location loc;
    template <typename S>
        requires std::convertible_to<const S&, std::string_view>
    consteval FormatWithLocation(const S& s,
                                 std::source_location l = std::source_location::current());
    FormatWithLocation(std::format_string<Args...> f,
                       std::source_location l = std::source_location::current());
};

class Logger {
public:
    // 계약: 모든 public 멤버 함수는 여러 스레드에서 동시에 불러도 안전하다.
    template <typename... Args>
    void log(FormatWithLocation<std::type_identity_t<Args>...> fmt, Args&&... args);            // Level::Debug
    template <typename... Args>
    void log(Level lv, FormatWithLocation<std::type_identity_t<Args>...> fmt, Args&&... args);
    template <typename... Args>
    void log(std::source_location loc, Level lv, std::format_string<Args...> fmt, Args&&... args); // 그대로
    // snapshot(), dump(), global(), levelName(), Config: 시그니처 그대로
};
```
- `Config::bufferCapacity`는 `snapshot()` 이력의 줄 수만 정한다(기본 256, 0이면 1). `m_buffer`가 없어지므로 다른 의미는 없다.

[`include/atugcc/core/memory_dump.hpp`](/include/atugcc/core/memory_dump.hpp)
```cpp
// 프로세스당 한 번: 처리기 등록 + dir/crash_dump_<time>.log 열기. 이미 준비됐으면 아무것도 하지 않고 성공.
[[nodiscard]] static atugcc::core::Result ensurePrepared(const std::filesystem::path& dir) noexcept;
[[nodiscard]] static std::filesystem::path preparedPath() noexcept; // 준비 안 됐으면 빈 경로
```
- `MemoryDump` 생성자(`REGISTER_MEMORY_DUMP_HANDLER`)는 `ensurePrepared("log")`를 부른다. 생성자를 여러 번 불러도 처리기와 파일은 하나다.
- `prepareDumpFile` / `prepareDumpFileWin`은 그대로 두되, 이전에 열린 fd/HANDLE을 닫고 바꾼다.

[`include/atugcc/core/ring_buffer.hpp`](/include/atugcc/core/ring_buffer.hpp)
- `inline constexpr float kNoAutoFlush = 2.0f;`(사용률은 1.0을 넘지 않으므로 끔), `kDefaultFlushThreshold = kNoAutoFlush`. 생성자 인자로 켤 수 있는 것은 그대로다.

### 2.2 Internal Implementation
- `Logger::log`: (1) lock 밖에서 `std::format`으로 줄 생성, (2) lock 안에서 이력 원형 배열의 `head` 자리에 넣기, (3) lock 밖에서 `DbgBuf::log(line, lv)`(호출 스레드의 `thread_local` 버퍼), (4) `liveOutput`이 있으면 `std::osyncstream(*cfg_.liveOutput) << line << '\n';` 후 flush. 같은 스트림을 여러 `Logger`가 써도 줄이 섞이지 않는다.
- `snapshot()`: lock 안에서 오래된 줄부터 순서대로 복사한다.
- 생성자: `enableCrashDump`면 `alog::MemoryDump::ensurePrepared(cfg_.dumpDir)`. 실패해도 `Logger`는 만들어진다(로그는 계속 쓸 수 있어야 한다). 실패는 `dump()`가 다시 시도할 때와 같은 `Result`로 드러난다.
- `ensurePrepared`: 함수 안 static 상태 + `std::call_once`. 성공한 경로를 기억한다. 정상 종료 때 소멸하는 static 가드가 파일을 닫고 크기가 0이면 지운다(Assumption 6).
- `tests/core/logger_contention_probe.cpp` + `tests/CMakeLists.txt`: 실행 파일 `logger_contention_probe`, CTest `LoggerContention`(작은 횟수로 실행해 줄 수만 검사, 통과 기준에 성능 숫자 없음).

### 2.3 Platform Specifics
- 빈 dump 파일 지우기: Linux `fstat` → `close` → `unlink`, Windows `GetFileSizeEx` → `CloseHandle` → `DeleteFileW`.
- `consteval` 생성자의 `source_location::current()` 기본 인자: GCC 13과 MSVC(VS 2026) 모두에서 호출 위치가 나오는지 AC-1로 확인한다. 어느 쪽에서든 안 되면 STOP하고 사용자에게 묻는다(대안: 명시적 `loc` 오버로드만 남김).

## 3. C++ Standard Evolution
| Approach | Standard | Description |
|----------|----------|-------------|
| Legacy | C++11/14/17 | `LOG(...)` 매크로가 `__FILE__`, `__LINE__`, `__func__`를 넘김. 여러 스레드의 `std::cout` 출력은 글자 단위로 섞이고, 막으려면 직접 mutex |
| Modern | C++20 | `std::source_location::current()`를 기본 인자로 받아 매크로 없이 호출 위치 기록. 가변 인자와 함께 쓰려고 `consteval` 래퍼 + `std::type_identity_t`. `std::osyncstream`이 줄 단위로 원자적으로 출력 |
| Latest | C++23 | `std::expected`(`Result`)로 준비 실패 보고. 비교: `std::print` |

Reference: `/docs/cpp_evolution/source_location.md` (KI-001의 빠진 페이지, 이 작업이 쓴다).

## 4. Edge Cases
- [x] Thread safety / memory ordering — 이력은 mutex, 포맷은 lock 밖. `DbgBuf`는 스레드마다 따로라 lock 없음. 자동 flush를 끄면 큐에 생산자가 없다(명시적 `flushToQueue`는 한 스레드만, 헤더에 명시). `ensurePrepared`는 `std::call_once`. 실시간 출력은 `osyncstream`. TSan: 8스레드가 공유 `Logger` 하나에 쓰고, 동시에 `snapshot()`을 부르는 테스트(AC-3)
- [x] Resource lifetime / RAII — dump fd/HANDLE은 static 가드가 소유하고 정상 종료 때 닫는다. 명시적 prepare는 이전 것을 닫는다. `snapshot()`은 복사본을 돌려준다. `ReadResult::payload`(string_view) 규칙은 그대로
- [x] Platform differences — §2.3. 경로 문자열은 `std::filesystem::path`
- [x] Template instantiation / concept constraints — `FormatWithLocation`의 문자열 생성자는 `convertible_to<string_view>`로 제한해 `log(Level::Info, ...)`가 첫 오버로드로 잘못 가지 않는다. 런타임 `std::format_string` 객체도 받는다. 포맷 오류는 지금처럼 컴파일 오류(AC-2)
- [x] ODR — `ensurePrepared`의 상태는 `.cpp`(또는 함수 안 static) 하나에 둔다. 헤더의 `static inline` 멤버 사용은 지금과 같다
- [x] Undefined behaviour / signal-handler safety — crash 처리기는 바꾸지 않는다(미리 연 fd에 `write`만). 처리기가 도는 동안 static 가드는 소멸하지 않는다(signal로 끝나면 소멸자가 돌지 않음). 정상 종료 중에 다른 스레드가 crash하는 경우는 다루지 않는다(Out of Scope)
- [x] 다른 `dumpDir`을 가진 두 번째 Logger — crash 대상은 첫 준비 그대로, 두 번째 Logger의 `dump()`(수동)는 자기 `dumpDir`에 쓴다. 헤더에 적는다
- [x] `bufferCapacity`보다 많은 줄 — 원형 배열이 가장 오래된 줄을 덮는다. `snapshot()`은 최신 `bufferCapacity`줄을 오래된 것부터

## 5. Acceptance Criteria
| ID | Criterion | Verified by |
|---|---|---|
| AC-1 | `log("...")`와 `log(Level::Info, "...")`로 쓴 줄에 **호출한 파일과 줄 번호**가 찍힌다(`logger.hpp`가 아님). GCC와 MSVC 모두 | GoogleTest `LoggerTest.RecordsCallerLocation` (`__LINE__`과 비교), 두 preset |
| AC-2 | 기존 호출 코드(테스트, 레슨 `02_thread_and_log`·`01_device_state_machine`, 유닛 `jthread_worker`)가 고치지 않고 빌드된다. 포맷 문자열과 인자 개수가 안 맞으면 지금처럼 컴파일 오류다 | 전체 빌드 + 컴파일 실패 확인(임시 파일, testrecord에 기록) |
| AC-3 | 8스레드 × 10,000줄을 공유 `Logger` 하나에 쓰는 동안 다른 스레드가 `snapshot()`을 반복해도 TSan 경고가 없고, 끝난 뒤 `snapshot()`은 정확히 `bufferCapacity`줄이며 각 줄이 온전하다 | GoogleTest `LoggerTest.SharedAcrossThreads` on `linux-x64-tsan` |
| AC-4 | 공유 `std::ostringstream`을 `liveOutput`으로 둔 `Logger` 두 개를 4스레드가 쓰면, 출력의 모든 줄이 온전한 한 줄이다(섞이지 않음) | GoogleTest `LoggerTest.LiveOutputLinesDoNotInterleave` (+ TSan) |
| AC-5 | `enableCrashDump = false`인 `Logger`만 만들면 `log/`도 `dumpDir`도 생기지 않고, 처리기도 등록되지 않는다(`preparedPath()`가 빈 경로) | GoogleTest(빈 임시 작업 디렉터리에서 실행) |
| AC-6 | `enableCrashDump = true`인 `Logger`를 세 개 만들면 dump 파일은 첫 `dumpDir`에 **하나**이고, 열린 fd 수가 Logger 수만큼 늘지 않는다 | GoogleTest(Linux `/proc/self/fd` 개수, Windows는 `preparedPath()` 하나 확인) |
| AC-7 | 정상 종료한 프로그램은 빈 dump 파일을 남기지 않는다. crash한 프로그램은 dump 파일에 crash 직전 줄을 남긴다(지금 동작 유지) | 레슨 `02_patterns/01_device_state_machine`·`02_thread_and_log` 실행 후 `log/` 확인 + 기존 crash 테스트(`test_posix_dump`, `test_dump_handle`) |
| AC-8 | 자동 flush 기본값이 꺼져 있다: 기본 `RingBuffer`에 256블록보다 많이 써도 `globalLogQueue()`는 비어 있고 버퍼는 최신 블록을 갖는다. 명시적 임계값을 준 기존 테스트(`AutoFlushThreshold` 등)는 그대로 통과한다 | GoogleTest `RingBufferTest.NoAutoFlushByDefault` + 기존 `RingBufferTest.*` |
| AC-9 | `Logger`에 `m_buffer`(자체 `RingBuffer`)가 없고, 한 줄은 이력과 호출 스레드의 `DbgBuf`에 한 번씩만 들어간다 | 코드 리뷰 + `DbgBuf` 블록 수 테스트 |
| AC-10 | `logger_contention_probe`가 (A)(B)(C) × 스레드 1/2/4/8 × 출력 끔/켬의 평균 ns, p50/p99/max, 처리량을 표로 출력하고, 모든 줄이 기록됐는지 검사한다(누락 시 exit 1). CTest `LoggerContention`이 Debug에서 작은 횟수로 통과한다 | CTest + `linux-x64-release`, `windows-x64-release` 실행 결과를 testrecord에 기록 |
| AC-11 | testrecord에 AC-10 숫자와 Assumption 9 기준에 따른 010-09 범위 제안이 있고, `agent_todo.md`의 010-09 노트에 반영된다 | 문서 리뷰(최종 결정은 사용자) |
| AC-12 | Windows `/W4 /WX`, Linux 경고 없이 빌드되고 전체 suite가 `windows-x64-debug`, `linux-x64-debug`, `linux-x64-asan`, `linux-x64-tsan`에서 통과한다 | `build.py --test` |

## 6. Out of Scope
- 공유 `Logger` 내부를 스레드별 버퍼 + 소비자 스레드로 바꾸기, `LogQueue` 소비자 — 010-09(AC-10 결과로 범위 결정)
- crash dump에 crash한 스레드 말고 **다른 스레드들의 버퍼**까지 담기(스레드별 버퍼 목록 필요) — 010-09
- 정상 종료 중에 다른 스레드가 crash하는 경우 — 010-09에서 버퍼 목록과 함께 다룬다
- 로그 레벨 필터, 파일 sink, 로그 회전 — 필요해지면 새 작업
- `alog::Logger` 별칭(이미 deprecated) 삭제 — 이 작업은 건드리지 않는다

## 7. Dependencies & Backends
none (Boost.Lockfree는 기존 그대로, 새 외부 의존 없음).

## 8. Documentation Updates
| Document | Section | Change |
|---|---|---|
| [`include/atugcc/core/logger.hpp`](/include/atugcc/core/logger.hpp) | 클래스 주석 | 스레드 계약(공유 안전), 기능별 Logger 권장, 첫 준비 디렉터리가 crash 대상 |
| [`include/atugcc/core/ring_buffer.hpp`](/include/atugcc/core/ring_buffer.hpp), [`log_queue.hpp`](/include/atugcc/core/log_queue.hpp) | 파일 주석 | 자동 flush 기본 끔, `flushToQueue`는 한 스레드만, 소비자는 010-09 |
| [`include/atugcc/core/memory_dump.hpp`](/include/atugcc/core/memory_dump.hpp) | `ensurePrepared` | 프로세스당 한 번, 빈 파일 정리 |
| `docs/cpp_evolution/source_location.md` | 새 문서 | 매크로 → `source_location`, 가변 인자와 `consteval` 래퍼, `osyncstream` |
| [`lessons/tracks/01_essentials/02_thread_and_log/README.md`](/lessons/tracks/01_essentials/02_thread_and_log/README.md), `main.cpp` 주석 | 스레드 안전성 계약, 연습 4 | "공유도 안전하다. 그래도 기능별로 나누는 이유"로 변경 |
| [`lessons/units/jthread_worker/README.md`](/lessons/units/jthread_worker/README.md), `jthread_worker.hpp` 주석 | Logger 계약 | KI-014 제약 삭제 |
| [`docs/known_issues.md`](/docs/known_issues.md) | KI-013, KI-014, KI-021, KI-025, KI-001 | CLOSED by 010-08; KI-001에 `source_location.md` 작성 기록 |
| [`docs/tasks/lesson_candidates.md`](/docs/tasks/lesson_candidates.md) | E3, E7, E13 | 선행(010-08) 해제 |
| [`docs/tasks/agent_todo.md`](/docs/tasks/agent_todo.md) | 010-09 | 측정 결과와 범위 제안(AC-11) |

## 9. Technical Constraints
- Compiler: MSVC (VS 2026) / GCC 13+
- CMake: 3.26+, `CMakePresets.json` preset으로만 빌드
- C++ Standard: C++23 (C++20 minimum). `<syncstream>` 필요

## 10. Context & References
- [logger.hpp](/include/atugcc/core/logger.hpp), [logger.cpp](/src/core/logger.cpp), [memory_dump.hpp](/include/atugcc/core/memory_dump.hpp), [ring_buffer.hpp](/include/atugcc/core/ring_buffer.hpp), [ring_buffer.cpp](/src/core/ring_buffer.cpp), [log_queue.hpp](/include/atugcc/core/log_queue.hpp)
- [test_logger.cpp](/tests/core/test_logger.cpp), [test_ring_buffer.cpp](/tests/core/test_ring_buffer.cpp), [span_cost_probe.cpp](/tests/pattern/span_cost_probe.cpp) (측정 방식 참고)
- [Logger 퍼사드 스펙(010-06)](/docs/specs/10_logger_facade.md), [090-05](/docs/specs/090_05_backlog_sync.md)

## 11. Implementation Plan
- [ ] Step 1: `ring_buffer.hpp` 자동 flush 기본 끔 + `RingBufferTest.NoAutoFlushByDefault` (AC-8)
- [ ] Step 2: `MemoryDump::ensurePrepared`, `preparedPath`, prepare 시 이전 fd/HANDLE 닫기, 종료 시 빈 파일 정리 + 테스트 (AC-5, AC-6, AC-7) — Risky(전역 상태, 플랫폼별)
- [ ] Step 3: `FormatWithLocation` + `log` 오버로드 (AC-1, AC-2) — Risky(템플릿, 두 컴파일러)
- [ ] Step 4: `Logger` 내부: `m_buffer` 제거, 이력 원형 배열, `osyncstream`, 생성자에서 `ensurePrepared` + 테스트 (AC-3, AC-4, AC-9) — Risky(동시성)
- [ ] Step 5: `logger_contention_probe` + CTest `LoggerContention` (AC-10)
- [ ] Step 6: Release 측정, 010-09 범위 제안 (AC-10, AC-11)
- [ ] Step 7: §8 문서

## 12. Verification Plan
- [ ] `py -3 .agent/scripts/build.py --preset windows-x64-debug --test`, 같은 명령을 `linux-x64-debug`, `linux-x64-asan`, `linux-x64-tsan`에서
- [ ] AC-2 컴파일 실패 확인: 인자 개수가 틀린 호출을 담은 임시 파일(빌드 후 삭제)
- [ ] AC-7: 두 레슨을 `tools/lessons.py` 또는 플레이그라운드로 실행하고 `log/` 확인
- [ ] AC-10: `linux-x64-release`, `windows-x64-release`로 `logger_contention_probe` 실행(호스트 코어 수 기록)
- [ ] `py -3 .agent/scripts/lint_docs.py` exit 0
- [ ] Every AC row has its evidence in `testrecord.md`

## History / Amendments
- 2026-10-30: 초안. 사용자와 공유/스레드별 trade-off 논의 반영(정확성 먼저, 측정으로 010-09 범위 결정)
- 2026-10-30: 승인
