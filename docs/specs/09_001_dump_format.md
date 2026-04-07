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
- 릴리스(최적화) 빌드에서도 별도 심볼 파일로 함수/라인/로컬 변수 정보를 보관할 수 있어, 덤프에 기록된 로그/주소와 매칭하면 호출 순서와 변수 값을 역추적하는 데 유용합니다.
- 스펙 구현 목표는 "링버퍼 원시 블록" + 분리된 디버그 심볼을 결합하여, 크래시 시점의 호출 흐름과 상호참조 가능한 변수 상태를 분석할 수 있도록 하는 것입니다.

마지막 주의사항
- 이 스펙은 "링버퍼 원시 블록" 기반의 즉시 덤프에 초점을 둡니다. 레지스터/스택/완전한 미니덤프(심볼+레지스터 포함)은 외부 솔루션(Breakpad/Crashpad 또는 OS core dump) 통합을 권장합니다.

---
작성: feature/error-expected 구현안 기준 — 리뷰 후 세부 구현 항목을 분할하여 PR로 진행합니다.
