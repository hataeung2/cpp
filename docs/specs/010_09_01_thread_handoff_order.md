---
id: 010-09-01
title: Logger 전달 순서 — 먼저 일어난 기록을 먼저 전달 (스레드 교대, KI-030)
depends_on: [010-09]
unblocks: []
approved: 2026-10-30
---

# Spec 010-09-01: Logger 전달 순서 — 먼저 일어난 기록을 먼저 전달

- 원래 스펙: [010-09](/docs/specs/010_09_logger_thread_buffers.md) (Assumption 9, plan D3 "Sustained load")
- 다시 여는 이유: [KI-030](/docs/known_issues.md). `CrashDump` `normal` 검사가 부하 아래에서 가끔 실패한다(`P6: ... in order False`). `main`에서도 8번 중 2번 재현됐다(010-10 게이트, 2026-10-30). 한 생산자의 줄을 스레드 A가 쓰다 끝나고, `join()` 뒤에 시작한 스레드 B가 이어서 쓰는데, A의 마지막 줄이 B의 줄보다 늦게 전달된다.
- 방향(사용자, 2026-10-30): 고친다.

## 0. Assumptions (please review)
| # | Decision | Rejected alternative | Why |
|---|---|---|---|
| 1 | **원인 가설과 확인 순서**: 소비자는 각 버퍼에서 1 ms보다 새로운 기록을 다음 drain으로 미룬다(holdback). 다만 절반 넘게 찬 버퍼는 holdback 없이 모두 가져간다(010-09 plan D3 "Sustained load"). 그래서 바쁜 B의 버퍼는 바로 전달되고, 막 끝난 A의 버퍼(절반 미만)에 있는 마지막 기록은 미뤄져 다음 묶음에 들어간다. 고치기 **전에** 이 경우를 매번 재현하는 probe 모드를 만들고, 그 모드가 지금 코드에서 실패하는 것을 먼저 확인한다(AC-1) | 바로 고침 | 원인은 코드를 읽고 세운 가설이다. 재현이 실패하면 가설이 틀린 것이므로, 그때는 멈추고 다시 조사한다 |
| 2 | **고치는 방법: drain을 두 단계로**. 1단계에서 holdback 없이 가져갈 버퍼(절반 이상 참, 또는 flush/종료 중)마다 지금 완성된 마지막 기록의 시각을 읽고, 그 최댓값을 이번 묶음의 상한(cutoff)으로 삼는다. 2단계에서는 **모든 버퍼**에서 `timeNs ≤ max(holdback 한계, cutoff)`인 기록을 가져간다. holdback 없는 버퍼도 cutoff를 넘는 기록(1단계 뒤에 공개된 것)은 다음 묶음으로 넘긴다 | holdback 예외를 없앰 / 전역 순번 | 예외를 없애면 010-09가 측정한 지속 부하 문제(Linux Release 85,000 lines/s)가 돌아온다. 전역 순번은 010-09 Assumption 9가 공유 지점이라 거부했다. 두 단계로 나누면 B의 기록이 A의 기록보다 앞서 전달될 수 없다: A의 공개는 `join`을 거쳐 B의 시각 읽기보다 먼저 일어나고, 1단계가 B의 위치를 acquire로 읽은 뒤에 2단계가 A의 버퍼를 읽으므로 A의 기록이 보인다. 그리고 A의 시각은 cutoff 이하다 |
| 3 | **계약을 한 줄 강화한다**: "한 `log()` 호출이 다른 호출보다 먼저 일어나면(같은 스레드, 또는 `join`, mutex, release/acquire 원자 연산으로 순서가 정해짐) 먼저 일어난 줄이 먼저 전달된다." 순서가 정해지지 않은 두 스레드 사이의 시각 역전은 지금처럼 세어 보고만 한다(010-09 AC-2 문구) | 계약은 그대로 두고 테스트만 고침 | 사용자는 `join` 뒤의 로그가 `join` 앞의 로그보다 먼저 나오리라고 생각하지 않는다. 지킬 수 있는 약속이므로 적는다 |
| 4 | **010-10 복구 파일은 바뀌지 않는다**: 복구는 이미 모든 기록을 `(timeNs, threadNo, threadSeq)`로 정렬한다. `readPos` 계약(010-10 Assumption 4)도 그대로다 | — | 이 작업은 소비자의 묶음 선택만 바꾼다 |

## 1. Objective
`Logger`가 먼저 일어난 기록을 먼저 전달하게 하여, 스레드가 교대할 때의 순서 역전(KI-030)을 없앤다. 010-09의 지속 부하 처리량은 유지한다.

## 2. Requirement Details
### 2.1 Public API Surface
API 변화 없음. [`logger.hpp`](/include/atugcc/core/logger.hpp) 클래스 주석에 Assumption 3의 순서 계약을 더한다.

### 2.2 Internal Implementation
- [`src/core/log_service.cpp`](/src/core/log_service.cpp) `drainLocked`: Assumption 2의 두 단계. 1단계는 할당하지 않는다(버퍼마다 위치와 마지막 완성 기록의 시각만 읽음). 2단계는 지금의 수집 루프에 cutoff 조건을 더한다.
- `gEarliestHeldBackNs`(다음 drain까지 기다리는 시간)는 2단계에서 미룬 기록 기준으로 지금처럼 계산한다.
- 재현 probe: [`tests/core/crash_probe.cpp`](/tests/core/crash_probe.cpp)에 모드 `handoff`를 더한다. `configureLogBuffers({.slotsPerThread = 64})`, 500회 반복: 스레드 A가 40줄을 쓰고 끝나면 `join` 뒤에 스레드 B가 같은 생산자 번호로 40줄을 이어 쓴다(64칸의 절반 초과라 B의 버퍼는 holdback 없이 전달됨). [`check_crash_dump.py`](/tests/core/check_crash_dump.py)가 `app.log`에서 회차마다 A의 줄이 B의 줄보다 모두 앞서는지 검사한다.

### 2.3 Platform Specifics
none (소비자 논리만 바뀜).

## 3. C++ Standard Evolution
N/A (기존 C++20 원자 연산의 acquire/release 순서를 이용할 뿐 새 기능은 없음).

## 4. Edge Cases
- [x] Thread safety / memory ordering — 1단계의 `writePos` acquire 읽기가 2단계보다 먼저 일어나야 한다(Assumption 2의 근거). TSan: `handoff` 모드를 `linux-x64-tsan`에서도 실행
- [x] Resource lifetime — N/A: 버퍼 수명은 010-09 그대로
- [x] Platform differences — N/A
- [x] Template instantiation — N/A
- [x] ODR — N/A
- [x] Undefined behaviour — N/A: 새 캐스트나 신호 경로 없음
- [x] 1단계와 2단계 사이에 새 기록이 공개됨 — cutoff보다 새로우면 다음 묶음으로 간다. 순서는 cutoff로 정해지므로 깨지지 않는다
- [x] 모든 버퍼가 holdback 대상(절반 미만) — cutoff가 없으므로 지금과 똑같이 동작한다
- [x] flush·종료 중 — 모든 버퍼가 holdback 없음이므로 cutoff = 가장 새로운 완성 기록의 시각, 즉 지금처럼 모두 전달한다

## 5. Acceptance Criteria
| ID | Criterion | Verified by |
|---|---|---|
| AC-1 | 고치기 전 코드에서 `crash_probe handoff` 검사가 실패한다(가설 확인). 실패하지 않으면 멈추고 사용자에게 보고한다 | `check_crash_dump.py --modes handoff`, 수정 전 커밋에서 실행, testrecord |
| AC-2 | 고친 뒤 `handoff`가 Windows와 Linux에서 10회 연속 통과하고, `normal`이 부하 아래(다른 빌드를 돌리는 동안) 10회 연속 통과한다 | 같은 검사 반복, testrecord |
| AC-3 | 010-09 AC-1 측정의 공유 Logger 4·8스레드 처리량이 지금(010-10 testrecord 측정)의 90% 이상이고 p99가 1.5배 이하이다 | Release `logger_contention_probe`, 두 플랫폼 |
| AC-4 | 전체 suite가 4 preset에서 경고 없이 통과하고, `handoff`는 TSan preset에서도 실행된다 | `build.py --test` 4 preset |
| AC-5 | `logger.hpp` 주석에 Assumption 3의 순서 계약이 있고, KI-030이 CLOSED다 | 문서 리뷰, `lint_docs.py` |

## 6. Out of Scope
- 순서가 정해지지 않은 스레드 사이의 시각 순서 보장 — 010-09와 같이 보장하지 않음(세어서 보고)
- 소비자 처리량 한계 — KI-028

## 7. Dependencies & Backends
none

## 8. Documentation Updates
| Document | Section | Change |
|---|---|---|
| [`include/atugcc/core/logger.hpp`](/include/atugcc/core/logger.hpp) | 클래스 주석 Contract | Assumption 3 |
| [`docs/known_issues.md`](/docs/known_issues.md) | KI-030 | CLOSED by 010-09-01 |
| [`docs/specs/010_09_logger_thread_buffers.md`](/docs/specs/010_09_logger_thread_buffers.md) | History | 010-09-01 보완 항목 |
| [`docs/cpp_evolution/lock_free_logging.md`](/docs/cpp_evolution/lock_free_logging.md) | 소비자 설명 | 두 단계 drain과 순서 계약 한 문단 |

## 9. Technical Constraints
- Compiler: MSVC (VS 2026) / GCC 13+, C++23 (C++20 minimum)
- CMake 3.26+, preset으로만 빌드

## 10. Context & References
- [010-09 spec](/docs/specs/010_09_logger_thread_buffers.md), [010-09 plan](/docs/tasks/feature_010-09-logger-thread-buffers/plan.md) D3, [010-10 testrecord](/docs/tasks/feature_010-10-logger-mapped-buffers/testrecord.md) R6
- [log_service.cpp](/src/core/log_service.cpp) `drainLocked`

## 11. Implementation Plan
- [ ] Step 1: `crash_probe handoff` + 검사(일반 단위, agy) → 지금 코드에서 실패 확인(AC-1)
- [ ] Step 2: `drainLocked` 두 단계(위험 단위: 동시성, agy + codex)
- [ ] Step 3: 반복 검사(AC-2), Release 측정(AC-3), 4 preset(AC-4), 문서(AC-5, lead)

## 12. Verification Plan
- [ ] `check_crash_dump.py --modes handoff`: 수정 전 실패, 수정 후 10회 연속 통과(두 플랫폼)
- [ ] mutant: 2단계에서 cutoff 조건을 빼면 `handoff`가 실패해야 한다
- [ ] `build.py --test` 4 preset, Release 측정 두 플랫폼
- [ ] `lint_docs.py`, `naming_check.py`

## History / Amendments
- 2026-10-30: 초안 (KI-030, 사용자 결정: 고친다)
- 2026-10-30: 승인(사용자, Assumption 1–4 그대로)
- 2026-10-30: 구현 중 보완(plan D1, D2). probe의 A는 20줄 뒤 `flush()`를 한 번 불러 소비자가 A를 매 회차 중간에 읽게 한다(없으면 B가 A의 버퍼를 다시 써서 실패가 가끔만 남). Assumption 3의 계약에 예외 한 줄: 서로 다른 스레드의 두 호출이 같은 `steady_clock` 눈금(Windows 100 ns)을 읽으면 순서를 보장하지 않는다(같은 시각은 스레드 번호로 정렬하고, 스레드 번호는 먼저 일어난 순서를 따르지 않음). 엄밀히 지키려면 공유 순번이 필요해 010-09 Assumption 9에 어긋난다. Assumption 1의 "절반 넘게"는 코드와 같이 "절반 이상"
