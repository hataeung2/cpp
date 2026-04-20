# Test Record — Pattern Visualizer (Phase 2.0)

## Environment
- OS: Windows (x64)
- Compiler: MSVC 19.50.35726.0 (Visual Studio 2026 BuildTools)
- Standard: `-std:c++latest` (C++23)
- Build system: CMake 3.26+, Ninja generator, preset `windows-x64-debug`
- Build directory: `/out/windows/x64/debug`
- Test framework: GoogleTest v1.14.0 (FetchContent)

## Build

### Configure
```
cmd /c "VsDevCmd.bat -arch=x64 -host_arch=x64 && cmake --preset windows-x64-debug"
```
결과: **성공** (12.6s)
- MSVC 감지, Boost 발견, vcpkg toolchain 적용

### Build
```
cmd /c "VsDevCmd.bat -arch=x64 -host_arch=x64 && cmake --build --preset windows-x64-debug -- -j 8"
```
결과: **성공** (12/12 targets)

## Test Execution

```
cmd /c "VsDevCmd.bat && ctest --test-dir E:/cpp/out/windows/x64/debug -C Debug --output-on-failure"
```

### Summary
```
Test project E:/cpp/out/windows/x64/debug
    Start 1: AllTests
1/1 Test #1: AllTests .........................   Passed    0.08 sec

100% tests passed, 0 tests failed out of 1
Total Test time (real) =   0.21 sec
```

### Detailed Results (55 test cases)

| Test Suite | Tests | Result |
|---|---|---|
| `testSample` | 1 | PASSED |
| `RingBufferTest` | 11 | PASSED |
| `LoggerTest` | 2 | PASSED |
| `ErrorExpectedTest` | 5 | PASSED |
| `DumpHandleTest` | 1 | PASSED |
| `PosixDumpTest` | 1 | **SKIPPED** (POSIX-only) |
| `TimeStampTest` | 5 | PASSED |
| **`TracerTest`** | **5** | **PASSED** |
| **`TerminalFmtTest`** | **4** | **PASSED** |
| **`PlantUMLFmtTest`** | **3** | **PASSED** |
| **`MermaidFmtTest`** | **2** | **PASSED** |
| **`D2FmtTest`** | **5** | **PASSED** |
| **`StateMachineTest`** | **4** | **PASSED** |
| **`ObserverTest`** | **4** | **PASSED** |

신규/개편된 시각화 관련 테스트 케이스 (굵게 표시) 총 **27개 전원 통과**.

### New Test Case Details

**TracerTest (5)**
- `RecordMessageAddsToSnapshot` — 메시지 기록 후 snapshot 확인
- `RecordTransitionAddsToSnapshot` — 전이 기록 후 snapshot 확인
- `PushNodeAddsToSnapshot` — 노드 관계 기록 후 snapshot 확인
- `CapacityLimitReturnsError` — 8개 초과 시 `CoreError::Unexpected` 반환
- `ClearResetsAllBuffers` — `clear()` 후 모든 버퍼 비어있음 확인

**TerminalFmtTest (4)**
- `FormatTerminalContainsFromAndTo` — from/to/action 문자열 포함 확인
- `FormatTerminalContainsTransitionArrow` — 전이 출력에 상태명 포함 확인
- `FormatTerminalContainsTreeRelation` — 트리 출력에 relation_type 포함 확인
- `EmptyTracerReturnsEmptyString` — 빈 Tracer → 빈 문자열 반환 확인

**PlantUMLFmtTest (3)**
- `DefaultBackendIsPlantUML` — `format_diagram()` 기본 호출 시 PlantUML(`@startuml`) 출력 확인
- `ExplicitPlantUMLBackend` — `DiagramBackend::PlantUML` 선택 시 상태 전이 문법(`A --> B : trigger`) 확인
- `FormatPlantUMLWrapperWorks` — thin wrapper `format_plantuml()` 동작 확인

**MermaidFmtTest (2)**
- `BackendSelectorToMermaidWorks` — `DiagramBackend::Mermaid` 선택 시 `sequenceDiagram` 출력 확인
- `FormatMermaidWrapperWorks` — thin wrapper `format_mermaid()` 동작 확인

**D2FmtTest (5)**
- `MessageFlowHeader` — `# sequence/message flow` 헤더 + `A -> B: call()` 형식 확인
- `StateFlowHeader` — `# state transitions` 헤더 + `IDLE -> STANDBY: go` 형식 확인
- `StructureTreeHeader` — `# class/structure tree` 헤더 + `P -> C: wraps` 형식 확인
- `DuplicateMessagesDeduped` — 중복 메시지 dedup: `A -> B: ping()` 정확히 1회만 등장
- `BackendSelectorToD2Works` — `DiagramBackend::D2` 선택 시 D2 출력 확인

**StateMachineTest (4)**
- `ValidTransitionRecorded` — 유효 전이 성공 + Tracer snapshot에 old/new_state 기록 확인
- `InvalidTransitionReturnsError` — 무효 전이 `CoreError::InvalidArgument` + 상태 변화 없음 확인
- `ScheduleRecordsMessage` — `schedule()` 후 `from == "Machine"` 메시지 기록 확인
- `FullFlowProducesDefaultPlantUMLOutput` — 전체 흐름 후 기본 PlantUML 스니펫 생성 확인

**ObserverTest (4)**
- `NotifyRecordsMessages` — notify 후 Observer1/Observer2 메시지 기록 확인
- `ExpiredObserverNotNotified` — 만료된 shared_ptr 구독자 메시지 미기록 확인
- `DisplayReflectsLatestData` — `collect_displays()` 최신 데이터 반영 확인
- `D2MessageFlowGenerated` — Observer notify 후 D2 message flow 생성 확인

## Issues Encountered and Resolved

1. **`observer.hpp` — `std::function` 미인식**
   - 원인: `#include <functional>` 누락
   - 해결: 헤더 추가

2. **`test_visualizer.cpp` — 주석 내 `*/` 파싱 오류**
   - 원인: `record_*/snapshot_*/` 패턴이 블록 주석 종료로 오인됨
   - 해결: `--` 구분자 사용으로 주석 텍스트 교체

3. **MSVC 한국어 주석 인코딩 오류 (`U+2014` 등)**
   - 원인: MSVC 기본 인코딩 CP949에서 UTF-8 소스 파싱 실패
   - 해결: `CMakeLists.txt` `atugcc_headers` INTERFACE에 `/utf-8` 플래그 추가

4. **`TerminalFmtTest.FormatTerminalContainsTreeRelation` 실패**
   - 원인: `render_node()`에서 `rel` 캡처 후 포맷 문자열에 미포함
   - 해결: `─(rel)─▶` 형식으로 출력에 relation_type 포함

5. **`[[nodiscard]]` C4834 경고 다수 (`/W4`)**
   - 원인: `record_*`, `transition()` 등 반환값 미캡처
   - 해결: 의도적 무시 위치마다 `(void)` 캐스트 적용
