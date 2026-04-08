# Spec 09_001 — Crash Dump Format & Immediate Dumping (draft, expanded)

목적
- `MemoryDump`의 즉시 덤프 동작(시그널/예외 핸들러에서 안전하게 기록)을 정형화하고, POSIX/Windows 구현 세부사항과 통합 테스트 요건을 명시한다.

요구사항 요약
- 핸들러 내부에서 호출되는 코드와 API는 async-signal-safe 함수만 사용해야 한다.
- 즉시 덤프는 프로세스 시작 시 덤프 대상(fd/HANDLE)을 미리 열어두고, 핸들러는 그 식별자에 대해 블록 단위 쓰기만 수행해야 한다.
- 덤프 파일 포맷은 텍스트 헤더 + 바이너리 블록 섹션(고정 크기 LogBlock)으로 단순하게 설계하여 파싱과 post-processing이 쉽도록 한다.
- Windows와 POSIX 모두에서 동작하도록 플랫폼별 구현 상세를 포함한다.

포맷 세부명세 (권장)
- 파일은 UTF-8 텍스트 헤더(개행으로 종료) 이후 고정 마커로 바이너리 블록을 이어붙인다.
- 헤더 필드 (한 줄씩, `Key: Value` 형식; 헤더 끝은 빈 줄)
  - `DUMP-V1`  # 식별자(파일 첫 줄)
  - `Timestamp: <ISO-8601>`
  - `PID: <pid>`
  - `TID: <tid or thread-name>`
  - `Event-Type: signal|exception`
  - `Event-Code: <SIGSEGV|EXCEPTION_ACCESS_VIOLATION|…>`
  - `Build-Id: <build-id-or-git-short>`  # 권장(심볼 매칭용)
  - `Commit: <git-sha1-short>`  # 가능하면 포함
  - 빈 줄
- 바이너리 섹션 시작 마커: `--BINARY-BLOCKS--\\n`
- 블록 스펙
  - 블록 고정 길이: `LogBlockSize` (프로젝트 기본값: 128 바이트; 구현에서 상수로 정의)
  - 블록은 링버퍼에 저장된 원시 바이트 그대로 기록 — 블록 내부 포맷(메타/길이/페이로드)은 링버퍼 설계에 따름.
  - 블록 개수는 파일 길이로 유추 가능(헤더 끝에서 EOF까지의 바이트 ÷ LogBlockSize).
- 바이너리 섹션 종료 마커(선택): `--END-BINARY--\\n` (파일 끝에 없어도 무방)

간단한 헤더 예시
```
DUMP-V1
Timestamp: 2026-04-07T12:34:56Z
PID: 12345
TID: 12345
Event-Type: signal
Event-Code: SIGSEGV
Build-Id: 1a2b3c4d

--BINARY-BLOCKS--
```

플랫폼별 구현 지침
- POSIX (Linux, macOS 등)
  - API: `MemoryDump::prepareDumpFile(std::filesystem::path const& p)` — 내부에서 `open(p, O_CREAT|O_WRONLY|O_TRUNC, 0600)`를 수행하고 반환/저장.
  - 즉시 덤프: `DbgBuf::dumpToFd(int fd) noexcept` — async-signal-safe인 `::write(fd, ptr, len)`만 호출하여 고정 크기 블록을 순차 쓰기.
  - 핸들러는 `prepareDumpFile()`으로 미리 얻은 `int fd`를 읽어서 사용한다. 핸들러 내부에서 `open()`/`fopen()`과 같은 비안전 호출을 하지 않는다.
- Windows
  - API: `MemoryDump::prepareDumpFileWin(HANDLE h)` 또는 `MemoryDump::prepareDumpFile(std::wstring path)`(내부에서 CreateFile로 HANDLE을 얻음).
  - 즉시 덤프: `DbgBuf::dumpToHandle(HANDLE h) noexcept` — `WriteFile` 호출을 블록 단위로 반복해서 수행. `WriteFile`은 async-signal-safe가 아니지만 Windows structured-exception handler나 vectored-exception에서 제한적으로 사용 가능하므로,
    구현 시 `WriteFile` 실패에 대비해 헤더만 먼저 쓰고, 블록 쓰기는 best-effort로 처리한다. (완전 안전을 보장하려면 미리 CreateFile을 통해 동기/비동기 핸들을 열어두고 사용)

Implementation notes / current deviations
- POSIX immediate-dump (`DbgBuf::dumpToFd`) is implemented as a non-destructive snapshot: the POSIX `rawDumpToFd` implementation iterates from the buffer's current `read_idx_` to `write_idx_` using a local `r` index and writes blocks with `::write()` without advancing the shared `read_idx_`. This preserves the ring buffer contents after an immediate dump — the spec's handler path should explicitly allow and recommend this non-destructive behavior.
- Windows immediate-dump (`DbgBuf::dumpToHandle`) in the current implementation is a best-effort path that calls the ring-buffer `dump()` method to produce a textual concatenation and then uses `WriteFile` to write that string to the prepared `HANDLE`. Important consequences:
  - `dump()` is consuming (it advances the buffer `read_idx_`) and therefore destroys the in-memory ring-buffer contents when called.
  - `WriteFile` is not async-signal-safe; using `dump()` inside a structured-exception handler is therefore not strictly signal/exception-safe and should be considered best-effort only.
  - Recommendation: change the Windows immediate-dump implementation to perform non-consuming raw-block writes (same semantics as POSIX `rawDumpToFd`) using the ring buffer's internal layout and calling `WriteFile` per block. This keeps immediate-dump non-destructive and makes behavior consistent across platforms while still treating `WriteFile` failures as best-effort.
- File permission inconsistency: the spec recommends creating dump files with `0600` permissions. Current code paths create prepared dump files in two places: `MemoryDump::prepareDumpFile()` (POSIX) uses `open(..., 0600)`, but the `MemoryDump` constructor's pre-open logic uses `::open(..., 0644)` when it creates a default `crash_dump_*.log` in `log/`. Recommendation: unify to `0600` for all created dump files to avoid inadvertently exposing sensitive data.

API 제안 (C++ 시그니처)
```
namespace atugcc::core {
  using Result = std::expected<void, CoreError>;

  // 준비: 프로세스 시작 시 호출. 성공 시 fd/HANDLE을 내부에 저장.
  Result MemoryDump::prepareDumpFile(std::filesystem::path const& p) noexcept;
  Result MemoryDump::prepareDumpFileWin(std::wstring const& p) noexcept;

  // 즉시 덤프: 핸들러에서 호출되도록 noexcept, async-signal-safe 경로 사용.
  void DbgBuf::dumpToFd(int fd) noexcept;         // POSIX, 완전 안전 경로
  void DbgBuf::dumpToHandle(HANDLE h) noexcept;   // Windows, best-effort 블록 쓰기
}
```

테스트 및 검증
- 단위/통합 테스트 요구사항
  - `posix/sig_dump_integration` (통합): 테스트 바이너리가 `prepareDumpFile()`로 `/tmp/testdump.bin`을 준비하고, 의도적 SIGSEGV를 트리거한 뒤 덤프 파일이 생성되고 블록이 파싱 가능한지 검증.
  - `parser` 유닛 테스트: 샘플 덤프(고정 블록 수)를 만들어 `scripts/parse_dump.py`(또는 C++ 파서)로 헤더와 블록을 정상 파싱하는지 확인.
  - `windows/dump_handle_test`: Windows에서 `dumpToHandle`이 헤더를 쓰고 블록 쓰기를 시도하는지 확인.

파서/검증 도구
- 간단한 Python 파서(`scripts/parse_dump.py`)를 제공하여 헤더를 읽고 `LogBlockSize` 단위로 블록을 분리, 각 블록의 페이로드 샘플을 출력하도록 한다.

운영/보안 고려사항
- 파일 권한: 생성 시 `0600` 권장(민감 데이터 포함 가능).
- 롤링/압축: 덤프가 클 수 있으므로 외부 프로세스로 주기적 압축/전송(예: systemd service hook 또는 로그 수집 에이전트) 권장.
- 심볼 매칭: Release 빌드에서도 유의미한 분석을 위해 `Build-Id` 또는 분리된 디버그 심볼(`objcopy --only-keep-debug`)을 운영 파이프라인에 포함.

마일스톤 및 수용 기준
1) 포맷 확정(본 문서) — 수용: 스펙 리뷰 승인
2) RelWithDebInfo 빌드 및 디버그 심볼 분리 자동화 — 수용: CI 또는 로컬 워크플로우에서 `RelWithDebInfo` 빌드가 가능하고, 빌드 결과물에 대해 분리된 디버그 심볼(`*.debug`)이 자동으로 생성/연결되는지 확인
3) POSIX 통합 테스트 추가 — 수용: 통합 테스트가 CI에서 성공적으로 SIGSEGV 트리거 후 파서가 블록을 검증
4) `scripts/parse_dump.py` 및 유닛 테스트 — 수용: 파서가 샘플 덤프를 정확히 파싱
5) Windows `dumpToHandle` 구현 — 수용: Windows 단위테스트에서 핸들에 헤더 및 (best-effort) 블록이 쓰이는지 확인
6) 운영 가이드 문서화 (파일 권한, symbol handling, rotation)

우선순위(이번 스프린트)
- 필수
  - RelWithDebInfo 빌드 + 디버그 심볼 분리 자동화 (CMake 변경)
  - POSIX 통합 테스트 및 파서 구현
  - `Build-Id`/commit 헤더 필드 추가
  - Windows `dumpToHandle` 완전 구현 및 테스트

수용 테스트 예시(간단)
1) 빌드: `cmake -S . -B build -DCMAKE_BUILD_TYPE=RelWithDebInfo && cmake --build build -j`
2) 실행: `./build/bin/atugcc_sample --prepare-dump /tmp/testdump.bin --trigger-segfault`
3) 파싱: `python3 scripts/parse_dump.py /tmp/testdump.bin` → 헤더 및 블록이 정상 출력

빌드 및 디버그 심볼 분리 (권장/필수 워크플로우)
프로덕션/릴리스 빌드에서도 의미있는 분석을 위해 디버그 심볼을 별도 파일로 분리하는 자동화가 필요합니다. 예시 명령:

```
# RelWithDebInfo (CMake)
cmake -S . -B build -DCMAKE_BUILD_TYPE=RelWithDebInfo

# 분리된 디버그 심볼 생성 예 (after build)
objcopy --only-keep-debug build/bin/atugcc_sample build/bin/atugcc_sample.debug
objcopy --strip-debug build/bin/atugcc_sample
objcopy --add-gnu-debuglink=atugcc_sample.debug build/bin/atugcc_sample
```

이 워크플로우는 다음을 보장합니다:
- 릴리스(최적화) 빌드에서도 별도 심볼 파일을 보관하면 덤프에 기록된 주소를 함수/라인으로 매핑할 수 있어 호출 흐름(reconstructed call flow)과 코드 위치 분석에 매우 유용합니다. 다만, **로컬 변수 값의 자동 복원은 보장되지 않습니다** — 로컬 변수 재구성에는 추가적인 레지스터/스택/메모리 스냅샷 또는 미니덤프 수준의 데이터를 함께 수집해야 실효적으로 지원됩니다.
- 스펙 구현 목표는 `"링버퍼 원시 블록" + 분리된 디버그 심볼`을 결합하여 크래시 시점의 호출 흐름을 재구성하고, 별도로 캡처된 레지스터/스택/메모리 정보와 결합할 때 로컬 변수/상태 분석을 지원 하는 것입니다.

마지막 주의사항
- 이 스펙은 "링버퍼 원시 블록" 기반의 즉시 덤프에 초점을 둡니다. 레지스터/스택/완전한 미니덤프(심볼+레지스터 포함)은 외부 솔루션(Breakpad/Crashpad 또는 OS core dump) 통합을 권장합니다.


Windows 즉시 덤프 개선 제안 (요약)

문제
- 현재 `DbgBuf::dumpToHandle()`는 내부적으로 `rb.dump()`(문자열 생성 및 버퍼 소비)를 호출한 뒤 `WriteFile`로 기록합니다. 이로 인해:
  - 링버퍼가 소비(consuming)되어 이후 분석/재시도가 불가능합니다.
  - `rb.dump()`는 힙/문자열 할당 등 비안전 함수들을 사용하므로 SEH/핸들러 내부에서 안전하지 않습니다.
  - `WriteFile`은 Windows에서 async-signal-safe가 아니므로 실패/블로킹 리스크가 존재합니다.
  - 덤프 헤더(예: `DUMP-V1`)가 항상 쓰이지 않아 포맷 호환성 문제가 발생합니다.
  - 레지스터/컨텍스트(CONTEXT) 또는 최소한의 스택 슬라이스가 덤프에 포함되지 않습니다.

권장 개선 (우선순위)
1) 비파괴적(raw block) 덤프 도입 — 필수
  - `RingBuffer`에 POSIX의 `rawDumpToFd`와 대칭되는 `rawDumpToHandle(HANDLE h) const noexcept` 추가.
  - 구현은 내부 `read_idx_`를 변경하지 않고 로컬 인덱스(r)를 사용하여 고정 크기 블록을 하나씩 `WriteFile`로 씀.
  - `DbgBuf::dumpToHandle(void* h)`는 `instance().rawDumpToHandle(static_cast<HANDLE>(h))`를 호출하도록 교체.

2) 헤더 및 포맷 일관성 보장 — 중요
  - `prepareDumpFileWin()`으로 얻은 `HANDLE`로 덤프 시, 먼저 텍스트 헤더(`DUMP-V1`, `Timestamp`, `PID`, `TID`, `Event-Type`, `Event-Code`, `Build-Id`, 빈 줄, `--BINARY-BLOCKS--\n`)를 `WriteFile`로 기록.
  - 이후 블록을 순차적으로 쓰고, 블록 개수는 파서에서 파일 길이로 유추할 수 있게 함.

3) 핸들 생성/속성 개선 — 중요
  - `CreateFileW`로 미리 열 때 권장 플래그: `FILE_ATTRIBUTE_NORMAL` 및 필요시 `FILE_FLAG_WRITE_THROUGH` 고려(쓰기 신뢰성), `FILE_SHARE_READ | FILE_SHARE_WRITE` 허용.
  - 가능한 경우 보안 속성(SECURITY_ATTRIBUTES/DACL)으로 접근을 제한하고, 핸들은 프로세스 시작 시 미리 열어 둠.

4) 핸들러 안전성 / 실패 대응 — 필수
  - SEH/핸들러 경로에서는 반드시 "헤더 먼저"를 쓰고, 블록 쓰기는 best-effort로 루프 처리하되 실패 시 즉시 중단.
  - 핸들러 코드에서 힙/동적 할당/가변 포맷팅을 사용하지 않도록 하고, 필요하면 미리 정적 버퍼를 준비.

5) 레지스터/스택/컨텍스트 캡처 — 강력 권장
  - `EXCEPTION_POINTERS*`의 `CONTEXT`를 직렬화하여 헤더 인접 영역 또는 별도 블록으로 기록(가능한 범위에서 best-effort).
  - 스택 슬라이스 기록은 유효성 검사를 포함하여 제한된 바이트만 복사하도록 구현.

6) 소비(consume) 동작 제거 및 문서화 — 필수
  - `rb.dump()`(소비형)는 핸들러용으로 사용 금지로 문서화하고, 즉시 덤프는 `rawDumpToHandle`(비소비) 사용을 강제.

7) 테스트 추가 — 필수
  - 유닛: `tests/core/test_dump_handle.cpp` 확장하여 `prepareDumpFileWin(path)`로 파일 준비 후 `rawDumpToHandle`이 헤더 + 블록을 쓴다는 것을 검증.
  - 통합: 실제 `CreateFile` 핸들을 열고(파일), 인위적 예외 또는 직접 `DbgBuf::dumpToHandle` 호출로 파일 내용을 검증.
  - CI: Windows 빌드/테스트 파이프라인에 해당 테스트를 추가.

대안 / 장기 권장
- 고급 분석이 필요하면 `MiniDumpWriteDump`(DbgHelp) 또는 Crashpad/Breakpad 같은 검증된 미니덤프 솔루션 도입 검토. 현재는 경량 링버퍼 기반 덤프를 유지하되, 필요 시 병행 제공 권장.

간단한 코드 제안 스니펫
```
// RingBuffer
void RingBuffer::rawDumpToHandle(HANDLE h) const noexcept;

// DbgBuf
void DbgBuf::dumpToHandle(void* h) noexcept { if (!h) return; instance().rawDumpToHandle(static_cast<HANDLE>(h)); }

// MemoryDump: prepareDumpFileWin()는 CreateFileW에 WRITE_THROUGH/SECURITY_ATTRIBUTES 옵션을 적용
```

운영/안전 노트
- SEH 내부에서 절대 힙/CRT 동적 호출 금지.
- 운영 가이드에 `prepareDumpFileWin`을 프로세스 시작 시 호출하도록 명시하고, "best-effort / non-guaranteed" 문구를 추가.
