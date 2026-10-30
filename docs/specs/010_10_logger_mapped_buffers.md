---
id: 010-10
title: 메모리 매핑 파일 로그 버퍼와 다음 실행 때 복구 — SIGKILL·강제 종료 대비
depends_on: [010-09]
unblocks: []
approved: null
---

# Spec 010-10: 메모리 매핑 파일 로그 버퍼와 다음 실행 때 복구

방향(사용자, 2026-10-30): 010-09 바로 뒤에 한다. 복구한 줄은 원래 로그 파일에 섞지 않고 **따로 확인할 수 있는 별도 파일**에 남긴다([010-09 Assumption 12](/docs/specs/010_09_logger_thread_buffers.md)).

메우려는 빈틈은 [010-09 §2.4](/docs/specs/010_09_logger_thread_buffers.md)의 이 행이다. SIGKILL, `TerminateProcess`, OOM killer로 끝나면 프로세스 안의 코드가 전혀 돌지 않는다. 그래서 스레드 버퍼에 있었지만 아직 파일에 쓰지 못한 줄(drain 간격 5 ms + holdback 1 ms + 쓰기 시간)을 잃고, crash dump도 없다.

## 0. Assumptions (please review)
| # | Decision | Rejected alternative | Why |
|---|---|---|---|
| 1 | **켜는 방법은 opt-in이다**: `configureLogBuffers({.mappedDir = "log"})` 또는 환경 변수 `ATUGCC_LOG_MAP_DIR`. 비어 있으면 010-09와 똑같이 메모리 버퍼만 쓴다 | 항상 켬 / `Logger::Config::filePath`가 있으면 자동으로 켬 | 매핑 파일은 디스크에 파일을 만들고, 그 파일은 프로세스가 비정상으로 끝나면 남는다. 레슨, 테스트, 짧은 도구가 모르는 사이에 `log/`에 파일을 남기면 안 된다(KI-021과 같은 종류의 문제). 버퍼는 Logger가 아니라 스레드의 것이므로(010-09 Assumption 11) 설정도 프로세스 전역이다 |
| 2 | **파일 하나에 아레나 하나**: 프로세스마다 `<mappedDir>/atugcc-<pid>-<시작 시각>.logmap` 파일 하나를 고정 크기로 매핑한다(`mappedBytes`, 기본 8 MiB = 기본 크기 버퍼 약 60개). 스레드 버퍼는 이 아레나에서 앞에서부터 차례로 잘라 쓴다(bump). 은퇴한 버퍼는 010-09처럼 재사용하므로, 아레나는 **동시에 살아 있는 스레드 수**만큼만 필요하다. 아레나가 차면 그 뒤의 버퍼는 힙에 만든다. 이 버퍼들은 복구 대상이 아니며, 이 사실을 stderr에 한 번 알리고 개수를 센다 | 스레드마다 파일 하나 / 매핑을 늘림(remap) | 스레드마다 파일을 만들면 파일 수가 늘고, 정리와 잠금도 그 수만큼 필요해진다. 매핑을 옮기면 버퍼 주소가 바뀌는데, 010-09의 버퍼는 해제하지 않고 주소가 고정이라는 전제(crash 처리기)에 기대고 있다. 매핑을 여러 조각으로 늘리는 방식은 플랫폼 분기가 커서 필요해질 때 한다(Out of Scope) |
| 3 | **010-09의 버퍼 형식을 그대로 매핑에 올린다**: `ThreadLogBuffer::createIn(storage, slotCount)`가 이미 있고, 버퍼는 포인터가 없는 고정 형식이다(`ATGLBUF1`). 파일 머리(`ATGLMAP1`)에는 PID, 시작 시각, steady↔system 기준점(시각 변환용), 아레나 사용량, Logger 이름표가 들어간다(§2.2) | 매핑용 형식을 따로 만듦 | 010-09가 이 목적으로 미리 설계해 둔 형식이다. 생산자 경로(`tryWrite`)를 바꾸지 않으므로 hot path 비용과 동시성 계약이 그대로다 |
| 4 | **"전달됨"의 기준은 `readPos`다**: 소비자는 sink(이력, 실시간 출력, 파일)에 쓴 뒤에야 `readPos`를 올린다(010-09 `drainLocked`). 따라서 매핑에 남은 `[readPos, writePos)`가 "프로세스가 죽을 때 아직 어떤 sink에도 닿지 않은 줄"이다. 이 동작은 바꾸지 않고, 바꾸지 말아야 할 계약으로 주석과 테스트로 고정한다 | 전달 순번을 따로 기록 | 이미 정확한 경계가 있다. 단, 줄이 파일에 써진 뒤 `readPos`를 올리기 전에 프로세스가 죽으면 그 줄은 파일과 복구 파일 양쪽에 있을 수 있다(중복 가능, 손실은 없음). 이 경우는 복구 파일에 적는다 |
| 5 | **복구 파일**: 끝난 실행 하나마다 `<mappedDir>/recovered_<이전 실행 시작 시각>_<pid>.log` 하나를 만든다. 내용은 ① 머리 주석(PID, 시작 시각, 줄 수, 중복 가능성 안내), ② **전달 안 된 줄 전부**, ③ 각 스레드에 남아 있던 **이미 전달된 최근 줄**(맥락용)이다. 모든 줄은 시각 순으로 정렬하고 `[undelivered]` / `[delivered]` 표시와 Logger 이름표를 단다. 원래 로그 파일에는 아무것도 덧붙이지 않는다 | 전달 안 된 줄만 / Logger마다 복구 파일 / 원래 파일 끝에 덧붙임 | 사용자 결정: 복구한 줄은 별도 파일. SIGKILL에는 crash dump가 없으므로 "마지막 상황"을 보여 줄 것이 이 파일뿐이다. 그래서 `read_dump.py` 출력처럼 맥락도 함께 남긴다. 파일 sink가 없는 Logger(실시간 출력, 이력만 쓰는 Logger)의 줄도 이 파일에 남는다. Logger마다 나누면 파일 수가 늘고 스레드 사이의 순서를 읽기 어려워진다 |
| 6 | **Logger 이름표**: 줄에 붙은 `loggerId`는 그 실행 안에서만 뜻이 있다. 그래서 등록·해제 때 파일 머리의 이름표 표(256칸 × 128 B = 32 KiB)에 `filePath`의 파일 이름을 쓴다. 파일 sink가 없으면 `logger#<id>`, `DbgBuf`는 `dbgbuf`, id가 256 이상이면 `logger#<id>`로 적는다 | 이름표 없음 / 전체 경로 | id는 가장 작은 빈 번호부터 재사용하므로(010-09 `registerLogger`) 대개 작다. 전체 경로를 쓰면 다른 PC에서 읽을 때 의미가 없고, 사용자 이름 같은 개인 경로가 남는다 |
| 7 | **복구 시점**: 매핑을 켜는 순간(`configureLogBuffers`, 또는 환경 변수로 첫 버퍼를 만들 때), 자기 매핑을 만들기 **전에** `mappedDir`에 있는 끝난 실행의 `.logmap`을 모두 복구하고 지운다. 그때마다 stderr에 `[atugcc] recovered N undelivered lines from pid P into <path>`를 한 줄 쓴다. 공개 함수 `recoverLogMaps(dir)`로 아무 때나 직접 부를 수도 있다(도구, 테스트, 매핑을 켜지 않는 감시 프로그램) | 백그라운드 스레드에서 복구 / 수동으로만 | 기본 8 MiB 아레나 하나를 복구하는 비용은 수 ms이다. 시작할 때 동기로 끝내야 "다음 실행 때 복구"가 확실하다. 백그라운드로 돌리면 바로 crash가 났을 때 복구 파일이 반쯤만 남는다 |
| 8 | **살아 있는 프로세스의 파일은 건드리지 않는다**: 매핑 파일은 연 동안 잠근다(Linux `flock(LOCK_EX)`, Windows `CreateFileW`에서 쓰기 공유를 허용하지 않음). 복구는 잠금을 얻은 파일만 처리한다. 잠금은 프로세스가 어떻게 죽든 OS가 풀어 준다 | PID가 살아 있는지 확인 | PID는 재사용되므로 다른 프로그램을 같은 프로세스로 잘못 볼 수 있다. 같은 `mappedDir`을 여러 프로세스가 동시에 써도 서로 해치지 않는다 |
| 9 | **정상 종료하면 파일을 지운다**: `std::exit`, `main` 반환, `std::quick_exit`로 끝나면 010-09의 `shutdown()`이 마지막 drain을 한 뒤 매핑을 닫고 파일을 지운다. crash 처리기로 끝난 경우(dump가 있음)에는 파일이 남고, 다음 실행이 복구한다. 이 경우 복구 파일의 머리에 "crash 처리기가 돌았음"을 적는다(파일 머리의 표시를 signal-safe 원자 store로 남김) | crash 때 파일을 지움 | dump와 복구 파일은 같은 줄을 담을 수 있지만, 복구 파일은 사람이 바로 읽을 수 있는 텍스트이고, dump를 만들지 못했을 때를 대비하는 백업도 된다. crash 처리기 안에서 파일을 지우는 것은 signal-safe가 아니다 |
| 10 | **손상된 파일**: 복구는 파일을 신뢰하지 않는 입력으로 다룬다. magic, 크기, `slotCount`(2의 거듭제곱, 범위), 위치(`readPos ≤ writePos`, 칸 수 범위), 칸 `len ≤ 232`, 이어짐 표시를 모두 검사하고, 맞지 않는 버퍼는 건너뛰고 센다. 파일 머리부터 읽을 수 없으면 `<이름>.corrupt`로 이름을 바꾸고 알린다(다음 실행 때 다시 시도하지 않음, 지우지도 않음). 읽을 때는 `std::memcpy`로 구조체에 복사하고, 매핑된 바이트를 객체로 해석하지 않는다 | 손상 파일을 지움 / `reinterpret_cast`로 읽음 | 디스크가 가득 찬 상태, 전원 차단, 다른 버전이 만든 파일이 있을 수 있다. 복구가 crash하면 그 프로그램은 다시는 시작하지 못한다. 손상 파일을 지우면 조사할 자료가 사라진다 |
| 11 | **전원 차단과 OS 충돌은 다루지 않는다**: 매핑된 내용은 OS의 페이지 캐시에 있다. 프로세스가 강제로 죽어도 OS가 파일에 쓰지만, OS가 죽으면 잃을 수 있다. `msync`/`FlushViewOfFile`을 drain마다 부르지 않는다 | drain마다 `msync` | drain마다 디스크 I/O를 하면 `Durability::System`(010-09)과 같은 비용이 든다. 전원 차단에 대비하려면 그 옵션을 쓰면 된다. §2.4 표에 이 차이를 적는다 |
| 12 | **켜기 전에 만든 버퍼는 힙에 남는다**: 매핑은 켠 뒤에 새로 만드는 스레드 버퍼부터 쓴다(`slotsPerThread`와 같은 규칙). 이미 있는 버퍼는 옮기지 않는다. 그래서 문서는 `main`의 첫 줄에서 설정하거나 환경 변수를 쓰라고 안내한다. 이미 켜진 뒤 다른 `mappedDir`을 주면 `InvalidArgument`를 돌려주고, 빈 값을 주면 바꾸지 않는다(매핑을 끄는 기능은 없음) | 기존 버퍼를 매핑으로 옮김 / 다시 설정하면 새 파일 | 버퍼를 옮기면 SPSC 위치와 crash 처리기가 보는 주소가 깨진다. `slotsPerThread`만 바꾸려는 호출이 `mappedDir`을 비워 두는 것은 흔한 일이므로, 빈 값이 매핑을 끄면 안 된다 |
| 13 | **오류는 프로그램을 멈추지 않는다**: 디렉터리를 만들 수 없거나, 디스크가 가득 찼거나, 매핑이 실패하면 `configureLogBuffers`는 `FileIOFailure`를 돌려준다. 그래도 로그는 메모리 버퍼로 계속 동작한다(010-09와 같음). 환경 변수로 켠 경우에는 stderr에 한 번 알린다 | 실패하면 로그를 멈춤 | 로그를 보존하는 기능 때문에 프로그램이 멈추면 안 된다는 010-09의 원칙(Assumption 3)을 따른다 |
| 14 | **읽는 도구는 `tools/read_dump.py`에 붙인다**: 입력의 magic을 보고 `.logmap`도 읽는다. 복구를 하지 않고, 남은 매핑 파일을 다른 PC에서 그대로 볼 때 쓴다. 출력 형식은 `DUMP-V2`와 같다(`--undelivered`도 같음) | 새 도구 `read_logmap.py` | 칸 형식이 같아서 파서를 재사용할 수 있다. 도구가 하나면 사용자가 찾기 쉽다 |

## 1. Objective
- 프로세스가 밖에서 강제로 끝나도(SIGKILL, `TerminateProcess`, OOM killer) **스레드 버퍼에 있던 줄이 다음 실행 때 별도 파일로 복구**되게 한다.
- 복구한 줄이 어디서 왔는지, 무엇이 원래 로그 파일에 없는지(전달 안 됨)를 사용자가 바로 알 수 있게 한다.
- hot path(`Logger::log`)의 비용과 010-09의 동시성 계약을 바꾸지 않는다.

## 2. Requirement Details

### 2.1 Public API Surface
[`include/atugcc/core/log_buffer_config.hpp`](/include/atugcc/core/log_buffer_config.hpp)
```cpp
struct LogBufferConfig {
    std::size_t slotsPerThread = 512;               // 010-09
    std::chrono::milliseconds drainInterval{5};     // 010-09
    // 010-10
    std::filesystem::path mappedDir{};              // empty = leave as is (off by default)
    std::size_t mappedBytes = 8 * 1024 * 1024;      // 1 MiB .. 1 GiB, read when mapping starts
};

// 010-09 + 010-10: the first non-empty mappedDir recovers ended runs in that directory, then maps this
// run's arena there. Same directory again: no change. Another directory while mapped: InvalidArgument.
// Cannot create or map: FileIOFailure (logging continues in memory). Env: ATUGCC_LOG_MAP_DIR.
[[nodiscard]] Result configureLogBuffers(const LogBufferConfig& cfg) noexcept;

struct LogMapRecovery {
    std::filesystem::path recoveredFile;            // recovered_<start>_<pid>.log
    std::uint32_t pid = 0;
    std::uint64_t undeliveredLines = 0;
    std::uint64_t deliveredLines = 0;               // context
    std::uint32_t skippedBuffers = 0;               // failed validation
    bool crashHandlerRan = false;
};
// Recovers every ended run's .logmap in dir into its own recovered file, then deletes the .logmap.
// Live runs (file locked) are skipped. An unreadable file is renamed to <name>.corrupt and not returned.
[[nodiscard]] Expected<std::vector<LogMapRecovery>> recoverLogMaps(const std::filesystem::path& dir);
```
[`include/atugcc/core/logger.hpp`](/include/atugcc/core/logger.hpp): API 변화 없음. 클래스 주석의 보존 보장 표만 고친다(§2.4).

### 2.2 Internal Implementation
- **파일 형식** (`ATGLMAP1`, little-endian, 포인터 없음):
  ```
  MapHeader (4096 B, 페이지 하나)
    char     magic[8]          "ATGLMAP1"
    uint32   version           1
    uint32   headerBytes       4096 + 이름표 표 크기 (버퍼 시작 위치, 페이지 정렬)
    uint64   fileBytes         mappedBytes
    uint32   pid
    uint32   flags             atomic: bit0 = crash handler ran
    uint64   startSystemNs     system_clock, 실행 시작
    uint64   steadyBaseNs      010-09 LogService의 기준점 쌍(steady ↔ system)
    int64    systemBaseNs
    uint64   arenaUsed         atomic: 다음 버퍼가 들어갈 위치(bump, 64 B 정렬)
    uint32   labelCount        256
    ...      reserved
  LabelTable (256 × 128 B)
    uint16   id, uint16 len, char text[124]   // id 0 = 빈 칸
  Arena (headerBytes ..)
    [BufferHeader + Slot × slotCount] × n     // 010-09 ATGLBUF1 그대로
  ```
- **`detail/log_map.hpp` / `src/core/log_map.cpp`** (새로): `LogMap` 싱글턴. `start(dir, bytes)`(복구 → 파일 생성·잠금·크기 설정·매핑 → 머리 쓰기), `allocateBuffer(slotCount)`(아레나 bump, CAS. 넘치면 `nullptr`), `setLabel(id, text)` / `clearLabel(id)`(서비스 mutex 아래에서만), `markCrash()`(signal-safe 원자 store), `closeAndRemove()`(정상 종료). 매핑은 해제하지 않는다(010-09 D2와 같은 이유. 정상 종료 때만 닫음).
- **`src/core/log_map_posix.cpp` / `src/core/log_map_win.cpp`** (새로): `MappedFile`(`open(path, bytes)` → 잠금 + 크기 설정 + 매핑, `tryOpenExisting(path)` → 잠금을 얻으면 읽기 매핑, `unmap`, `remove`). POSIX는 `open`, `flock`, `posix_fallocate`(실패하면 `ftruncate`), `mmap(MAP_SHARED)`. Windows는 `CreateFileW`(`FILE_SHARE_READ`), `SetFilePointerEx` + `SetEndOfFile`, `CreateFileMappingW`, `MapViewOfFile`. 플랫폼 분기는 이 두 파일에만 둔다(010-09 §2.3과 같은 원칙).
- **`log_registry.cpp`**: `acquireNode`의 "새 버퍼 만들기" 단계가 매핑이 켜져 있으면 `LogMap::allocateBuffer`를 먼저 시도하고, 실패하면 `ThreadLogBuffer::create`(힙)를 쓴다. 재사용 규칙은 그대로다. 비상 버퍼(정적 저장소)는 매핑하지 않는다.
- **`log_service.cpp`**: `registerLogger`/`unregisterLogger`가 이름표를 쓰고 지운다. `shutdown()`이 마지막 drain 뒤에 `LogMap::closeAndRemove()`를 부른다. drain 순서(sink에 쓴 뒤 `advanceRead`)는 Assumption 4의 계약이다. 이 순서를 지키라는 주석을 단다.
- **crash 처리기**(`memory_dump.cpp`): dump를 쓰기 전에 `LogMap::markCrash()`를 부른다. 매핑된 버퍼도 registry에 있으므로 DUMP-V2는 그대로 모든 버퍼를 담는다.
- **복구**(`src/core/log_map_recover.cpp`, 새로): 디렉터리의 `*.logmap`마다 자기 파일을 건너뛰고 `tryOpenExisting`을 부른다. 잠금을 얻지 못하면(살아 있는 실행) 건너뛴다. 머리를 검증하고(Assumption 10), `arenaUsed`까지 버퍼를 하나씩 `memcpy`로 읽어 검증한 뒤, 완전한 기록(처음 칸~마지막 칸)만 모은다. 범위는 `[max(0, writePos − slotCount), writePos)`이고, `< readPos`이면 delivered, 아니면 undelivered다. `(timeNs, threadNo, threadSeq)` 순으로 정렬하고, 기준점으로 시각을 바꿔 복구 파일을 쓴다. 그다음 매핑 파일을 지운다. 복구 파일을 다 쓰지 못하면 매핑 파일을 지우지 않는다(다음에 다시 시도).
- **복구 파일 형식**:
  ```
  # atugcc recovered log (spec 010-10)
  # pid 4242, started 2026-10-30 12:00:00.123, ended without a clean exit (crash handler: no)
  # 37 undelivered lines (never reached any sink: not in the log file), 412 delivered lines (context)
  # a line delivered just before the end can appear both here as undelivered and in the log file
  2026-10-30 12:00:01.234567 T3 [undelivered] app.log [INFO] [main.cpp:42 run] text
  ```
- **`tools/read_dump.py`**: magic이 `ATGLMAP1`이면 매핑 파일로 읽는다. 출력과 `--undelivered`는 DUMP-V2와 같다.
- **테스트용**: `crash_probe`에 `killmap` 모드를 더한다(매핑 켬, `drainInterval` 1000 ms, Debug 표시 줄을 쓴 뒤 자기 자신에게 SIGKILL / `TerminateProcess`). `check_crash_dump.py`가 다음 실행(`recoverLogMaps`를 부르는 probe 모드 `recover`)의 복구 파일을 검사한다.

### 2.3 Platform Specifics
- Linux: `mmap(MAP_SHARED)`, `flock`, `posix_fallocate`. SIGKILL 뒤에도 페이지 캐시의 내용은 파일에 남는다.
- Windows: `CreateFileMappingW` / `MapViewOfFile`. `TerminateProcess` 뒤에도 수정된 페이지는 메모리 관리자가 파일에 쓴다. 파일 크기는 매핑 전에 정한다. 매핑이 열린 동안에는 파일을 지울 수 없으므로, 닫은 뒤 지운다.
- 파일 이름의 시각은 UTC `YYYYMMDDTHHMMSSmmm`이다(`:`는 Windows 파일 이름에 쓸 수 없음).
- sanitizer preset: 매핑 메모리는 ASan/TSan이 일반 메모리처럼 다룬다. 정상 종료 경로는 4 preset에서 모두, `killmap`은 Debug와 Release에서만 실행한다(010-09 crash 검사와 같은 이유).

### 2.4 보존 보장 (010-09 표에서 바뀌는 행)
| 상황 | 파일 sink | crash dump | 매핑 켰을 때 (010-10) |
|---|---|---|---|
| `main` 반환, `std::exit`, `std::quick_exit` | 모든 줄 | — | 매핑 파일 지움, 복구 없음 |
| `abort`, 신호, Windows 예외, 스택 오버플로, `std::terminate` | 010-09와 같음 | 010-09와 같음 | 다음 실행 때 복구 파일(dump와 겹칠 수 있음) |
| SIGKILL, `TerminateProcess`, OOM killer | 이미 쓴 줄 | 없음 | **다음 실행 때 복구 파일에 전달 안 된 줄 전부 + 맥락** |
| OS 충돌, 전원 차단 | `Durability::System`이면 이미 쓴 줄 | 없음 | 보장하지 않음(OS가 아직 쓰지 않은 페이지는 잃음) |
| 매핑 켜기 전에 만든 스레드 버퍼, 아레나가 찬 뒤의 버퍼 | — | — | 복구 대상 아님(stderr 안내, 개수) |

## 3. C++ Standard Evolution
| Approach | Standard | Description |
|----------|----------|-------------|
| Legacy | C++11/14/17 | `mmap` 결과를 `reinterpret_cast<Header*>`로 읽음. 그 주소에 객체가 "살아 있지" 않아 엄밀히는 UB이고, 손상된 파일을 그대로 믿음 |
| Modern | C++20 | 암시적 객체 생성(P0593): 쓰는 쪽은 placement new(`createIn`)로 객체의 수명을 연다. 읽는 쪽은 `std::memcpy` / `std::bit_cast`로 trivially copyable 구조체에 복사해 검증한다. `std::atomic<uint64_t>`는 lock-free이므로 매핑 메모리에서도 동작한다(`is_always_lock_free`, 010-09에서 static_assert) |
| Latest | C++23 | `std::start_lifetime_as`(P2590)가 "이 바이트를 객체로 본다"를 표준으로 적는다. MSVC와 GCC가 아직 구현하지 않았으므로 쓰지 않는다. 문서에서만 소개한다 |

Reference: [`/docs/cpp_evolution/lock_free_logging.md`](/docs/cpp_evolution/lock_free_logging.md)에 "매핑 파일 위의 버퍼" 절을 더한다.

## 4. Edge Cases
- [x] Thread safety / memory ordering — 생산자·소비자 경로는 바뀌지 않는다. 아레나 bump는 `arenaUsed` CAS로만 한다(버퍼 머리를 다 쓴 뒤 다른 스레드가 읽는 것은 registry 연결의 release가 맡음). 이름표는 서비스 mutex 아래에서만 쓴다. 복구 쪽은 주인이 죽은 뒤 읽으므로 원자 연산이 필요 없다(잠금으로 보장). TSan: 매핑 켬 + 010-09의 스레드 생성·종료 반복 테스트
- [x] Resource lifetime — 매핑은 정상 종료 때만 닫는다. `shutdown()` 뒤의 `log()`(010-09: 호출 스레드가 직접 전달)는 매핑을 닫은 뒤이므로 힙 버퍼만 쓴다: 닫기 전에 registry가 매핑 버퍼를 더는 내주지 않게 막는다. 정적 소멸 뒤의 crash는 매핑이 살아 있으므로 그대로 dump된다
- [x] Platform differences — §2.3. Windows는 매핑이 열린 파일을 지울 수 없음, 잠금 방식이 다름
- [x] Template instantiation — N/A: 새 템플릿 없음
- [x] ODR — `LogMap` 상태는 `log_map.cpp` 하나에만 둔다. 헤더에 `inline` static을 두지 않는다
- [x] Undefined behaviour / signal-handler safety — 복구는 `memcpy`로 읽고 모든 크기와 위치를 검사한다(Assumption 10). crash 경로에서 늘어나는 것은 `markCrash()`의 원자 store 하나뿐이다
- [x] 같은 `mappedDir`을 쓰는 두 프로세스 — 잠금으로 서로의 파일을 복구하지 않는다(AC-3)
- [x] 매핑 직후 crash — 머리를 다 쓰기 전에 죽으면 magic이 없으므로 `.corrupt` 처리된다
- [x] 복구 중 crash 또는 강제 종료 — 복구 파일을 다 쓰기 전에는 매핑 파일을 지우지 않는다. 다음 실행이 다시 복구하며, 이전의 반쯤 쓴 복구 파일은 덮어쓴다(같은 이름)
- [x] 디스크 가득 — 생성은 `posix_fallocate`로 미리 공간을 잡아 실패를 시작할 때 알린다. Windows는 `SetEndOfFile`이 실패를 알린다
- [x] `fork()` — 010-09와 같이 다루지 않는다(자식이 같은 매핑을 공유함). 헤더에 적는다
- [x] 이전 버전이나 다른 크기 설정으로 만든 파일 — 파일 머리의 `version`과 버퍼마다 있는 `slotCount`로 읽으므로, 지금 실행의 설정과 상관없이 복구한다

## 5. Acceptance Criteria
| ID | Criterion | Verified by |
|---|---|---|
| AC-1 | 매핑을 켜고 4스레드 × 1,000줄(Debug, `drainInterval` 1000 ms, `OverflowPolicy::Block`, 파일 sink 있음)을 쓴 직후 SIGKILL(Windows `TerminateProcess`)로 끝낸 뒤, 다음 실행이 만든 복구 파일에서 `[undelivered]` 줄과 로그 파일의 줄을 합치면 모든 줄이 빠짐없이 있다. 로그 파일에 없는 줄은 모두 `[undelivered]`이다. Linux와 Windows 모두 | `crash_probe killmap` → `crash_probe recover` + `check_crash_dump.py` |
| AC-2 | AC-1의 복구 파일 줄이 시각 순이고, 각 줄에 Logger 이름표(로그 파일 이름 / `logger#<id>`)와 스레드 번호가 있으며, 머리 주석의 줄 수가 실제 줄 수와 같다. 복구 뒤 `.logmap` 파일이 없다 | 같은 검사 |
| AC-3 | 프로세스 A가 매핑을 켜고 살아 있는 동안 프로세스 B가 같은 디렉터리에서 `recoverLogMaps`를 부르면, A의 파일은 건드리지 않고 결과에도 없다 | probe 두 개 + 검사 스크립트 |
| AC-4 | 정상 종료(`main` 반환, `std::exit`, `std::quick_exit`) 뒤에는 `.logmap` 파일이 남지 않고, 다음 실행이 복구 파일을 만들지 않는다 | `crash_probe normal`(매핑 켬) + 검사 |
| AC-5 | `abort` / SIGSEGV로 끝난 실행은 dump가 남고, 다음 실행의 복구 파일 머리에 `crash handler: yes`가 있다 | `crash_probe abort`(매핑 켬) + 검사 |
| AC-6 | 손상된 입력에서 `recoverLogMaps`가 crash하지 않는다: magic 틀림, 잘린 파일, `slotCount` 범위 밖, `writePos < readPos`, `len > 232`, 끊긴 이어짐, 무작위 바이트(seed 고정 1,000개). 머리가 틀리면 `.corrupt`로 바뀌고, 버퍼 하나만 틀리면 나머지 버퍼는 복구되며 `skippedBuffers`가 센다 | GoogleTest + ASan |
| AC-7 | `configureLogBuffers`: `mappedBytes` 범위 밖이면 `InvalidArgument`, 매핑된 뒤 다른 디렉터리면 `InvalidArgument`, 같은 디렉터리나 빈 값이면 성공하고 바뀌지 않는다. 만들 수 없는 디렉터리이면 `FileIOFailure`이고 그 뒤에도 `log()`가 전달된다. `ATUGCC_LOG_MAP_DIR`로 시작한 프로세스는 매핑을 쓴다 | GoogleTest + 환경 변수 probe |
| AC-8 | `mappedBytes` = 1 MiB에서 동시에 살아 있는 스레드 12개가 기록하면 아레나에 들어가는 만큼만 매핑 버퍼를 쓰고, 나머지는 힙 버퍼를 쓰며, 줄을 하나도 잃지 않는다. stderr 안내는 한 번이다 | GoogleTest |
| AC-9 | 매핑을 켜도 `logger_contention_probe`(Release, 실시간 출력 끔) 공유 Logger의 4·8스레드 p99가 매핑을 끈 경우의 1.5배 이하이다 | Release 측정(Linux, Windows), testrecord |
| AC-10 | `tools/read_dump.py`가 `.logmap`을 DUMP-V2와 같은 형식으로 출력하고, `--undelivered`가 전달 안 된 줄만 보여 준다 | Python unittest + AC-1의 매핑 파일(복구 전 사본)로 실행 |
| AC-11 | 010-09의 모든 테스트와 레슨, `PlaygroundServer`가 통과하고, Windows `/W4 /WX`, Linux, ASan, TSan에서 경고 없이 전체 suite가 통과한다. 매핑을 켠 TSan 테스트(스레드 생성·종료 반복)가 있다 | `build.py --test` 4 preset |
| AC-12 | §2.4 표가 `logger.hpp` 주석과 루트 README에 반영돼 있다 | 문서 리뷰 |

## 6. Out of Scope
- 아레나를 실행 중에 늘리기(매핑 조각 추가) — 필요해지면 새 작업(KI로 기록)
- 전원 차단·OS 충돌 대비(`msync` 주기) — `Durability::System`(010-09)을 쓴다
- 복구 파일의 회전, 개수 제한, 오래된 복구 파일 정리 — 로그 회전과 함께 새 작업
- `fork()` 뒤 자식, `_exit` — 010-09와 같음
- 비상 버퍼(메모리 부족 때의 정적 버퍼) 매핑 — 메모리가 없는 상황에서 파일 매핑은 기대할 수 없다

## 7. Dependencies & Backends
새 외부 의존 없음. OS 매핑 API는 `src/core/log_map_posix.cpp`, `src/core/log_map_win.cpp` 뒤에 둔다.

## 8. Documentation Updates
| Document | Section | Change |
|---|---|---|
| [`include/atugcc/core/logger.hpp`](/include/atugcc/core/logger.hpp) | 클래스 주석, 보존 보장 | SIGKILL 행, 매핑 켜는 법 |
| [`include/atugcc/core/log_buffer_config.hpp`](/include/atugcc/core/log_buffer_config.hpp) | `LogBufferConfig`, `recoverLogMaps` | §2.1 계약 |
| [`include/atugcc/core/detail/log_service.hpp`](/include/atugcc/core/detail/log_service.hpp) | 보존 보장 표 | §2.4 |
| [`README.md`](/README.md) | 로그 보존 보장 표, 도구 | §2.4 (AC-12), `read_dump.py`가 `.logmap`도 읽음 |
| [`docs/cpp_evolution/lock_free_logging.md`](/docs/cpp_evolution/lock_free_logging.md) | 새 절 | §3 |
| [`docs/known_issues.md`](/docs/known_issues.md) | 새 KI | 아레나 크기 고정(Out of Scope 1), 측정에서 나온 것이 있으면 그것도 |
| [`docs/tasks/lesson_candidates.md`](/docs/tasks/lesson_candidates.md) | E12, E13 근처 | 매핑 버퍼와 복구를 레슨 후보로 |

## 9. Technical Constraints
- Compiler: MSVC (VS 2026) / GCC 13+, C++23 (C++20 minimum)
- CMake 3.26+, preset으로만 빌드

## 10. Context & References
- [010-09 spec](/docs/specs/010_09_logger_thread_buffers.md), [010-09 testrecord](/docs/tasks/feature_010-09-logger-thread-buffers/testrecord.md)
- [thread_log_buffer.hpp](/include/atugcc/core/detail/thread_log_buffer.hpp) (ATGLBUF1 형식, `createIn`), [log_registry.hpp](/include/atugcc/core/detail/log_registry.hpp), [log_service.hpp](/include/atugcc/core/detail/log_service.hpp), [log_service.cpp](/src/core/log_service.cpp) (`drainLocked`: sink 뒤 `advanceRead`)
- [crash_probe.cpp](/tests/core/crash_probe.cpp), [check_crash_dump.py](/tests/core/check_crash_dump.py), [read_dump.py](/tools/read_dump.py)

## 11. Implementation Plan
- [ ] Step 1: `MappedFile` POSIX / Windows (생성, 잠금, 크기, 매핑, 기존 파일 열기, 지우기) — Risky(플랫폼)
- [ ] Step 2: `LogMap`(파일 형식, 아레나 bump, 이름표, `markCrash`, 닫고 지우기) — Risky(레이아웃, 원자 연산)
- [ ] Step 3: registry·service·crash 처리기 연결, `configureLogBuffers`·환경 변수 — Risky(수명, 여러 파일)
- [ ] Step 4: 복구(`recoverLogMaps`, 검증, 복구 파일) — Risky(신뢰하지 않는 입력, 레이아웃)
- [ ] Step 5: GoogleTest(AC-6 ~ AC-8, 매핑 TSan) — 일반 단위(agy)
- [ ] Step 6: `crash_probe` `killmap`/`recover`/두 프로세스 모드 + `check_crash_dump.py`(AC-1 ~ AC-5) — 일반 단위(agy)
- [ ] Step 7: `read_dump.py` `.logmap` + unittest(AC-10) — 일반 단위(agy)
- [ ] Step 8: Release 측정(AC-9), §8 문서 — lead

## 12. Verification Plan
- [ ] `build.py --test`: `windows-x64-debug`, `linux-x64-debug`, `linux-x64-asan`, `linux-x64-tsan`
- [ ] `killmap` 검사는 Debug·Release preset에서만, 정상 종료 경로는 4 preset 모두(testrecord에 기록)
- [ ] mutant: 복구가 `readPos` 대신 `writePos`로 delivered를 판정(AC-1이 잡아야 함), 잠금 생략(AC-3이 잡아야 함), 머리 검증 생략(AC-6이 ASan으로 잡아야 함)
- [ ] Release 측정(AC-9) 두 플랫폼, 다른 부하 없이
- [ ] `lint_docs.py`, `naming_check.py`, `test_agent_scripts.py`

## History / Amendments
- 2026-10-30: 초안
