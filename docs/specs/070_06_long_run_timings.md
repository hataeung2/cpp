---
id: 070-06
title: 장시간 실행 프로필과 구간 시간(Timings) 화면
depends_on: [070-02, 020-06]
unblocks: []
approved: null
---

# Spec 070-06: 장시간 실행 프로필과 구간 시간(Timings) 화면

## 0. Assumptions (please review)
| # | Decision | Rejected alternative | Why |
|---|---|---|---|
| 1 | 레슨이 `[run] profile = "long"`을 선언하면(070-01) 실행 제한이 `timeout`(기본 300초, 최대 1800초)이 된다. Stop은 항상 쓸 수 있다 | 모든 레슨에 긴 제한 / 제한 없음 | 짧은 레슨의 실수(무한 루프)는 10초 안에 끝나야 한다. 측정 레슨만 길게 허용한다. 제한 없음은 잊힌 프로세스를 남긴다 |
| 2 | 화면에서 이번 실행만 프로필을 바꿀 수 있다("길게 실행" 토글). 매니페스트는 바뀌지 않는다 | 매니페스트만 따름 | quick 레슨을 고치다가 측정을 해 보고 싶을 때 매니페스트를 고치지 않게 한다 |
| 3 | long 프로필은 **최적화 빌드**를 기본으로 쓴다: preset `linux-x64-playground-release`(RelWithDebInfo, `-O2 -g`). `[run] build = "debug"`로 바꿀 수 있다. 화면의 모든 시간 옆에 빌드 종류를 표시한다 | 항상 Debug | Debug(-O0) 시간은 성능 판단을 왜곡한다. 반대로 최적화 영향 자체를 비교하는 연습을 위해 debug 선택을 남긴다 |
| 4 | long 실행에는 서버가 `ATUGCC_TRACE_FLUSH_MS=100`을 설정한다(020-06 Assumption 6) | 줄마다 flush | 측정 대상보다 기록 비용이 커지지 않게 한다. 화면 갱신 주기(100ms)와 맞춘다 |
| 5 | 집계는 브라우저에서 한다: (file, line, label, meter)별 count, total, mean, min, max, p50, p95. 백분위는 키마다 최근 1024개 표본(reservoir)으로 계산한다 | 서버 집계 / C++ 집계(`spanStats`)만 사용 | 실행 중 실시간 갱신이 필요하다. C++ 집계는 종료 시점에만 알 수 있다. 종료 후에는 화면 값과 `formatTimings()` 콘솔 표가 같은 count·total을 보여야 한다(AC-4) |
| 6 | **이전 실행 대비** 열: 레슨마다 직전 실행의 집계를 브라우저 저장소에 두고 mean 변화율(%)을 표시한다 | 비교 없음 / 서버에 실행 이력 저장 | 성능 연습의 핵심은 "고치고 다시 재서 비교"다. 직전 한 번이면 충분하고, 저장소에 이력을 남기지 않는다(로컬 편의 기능) |
| 7 | long 실행의 Output 패널은 최근 5,000줄만 유지하고, 서버는 stdout·stderr를 합쳐 8 MiB까지 전송한다(초과분은 버리고 표시) | quick과 같은 1 MiB | 장시간 실행은 출력이 많다. 브라우저 메모리를 일정하게 유지한다 |

## 1. Objective
성능 측정처럼 오래 걸리는 레슨을 웹에서 실행하면서, 코드 구간(020-06 span)별 시간을 **실행 중에 실시간으로** 보고 이전 실행과 비교한다. 070-02의 SSE 스트림과 프로필 표 위에 `long` 행과 Timings 화면을 더한다.

## 2. Requirement Details

### 2.1 서버
- 프로필 표에 `long` 행 추가: 실행 제한 = 레슨 `timeout`, 출력 8 MiB, preset `linux-x64-playground-release`(또는 `build = "debug"`면 기존 preset), 환경 `ATUGCC_TRACE_FLUSH_MS=100`.
- `POST /api/runs` body에 선택 필드 `profileOverride: "quick" | "long"`, `spanMeter: "wall" | "cpu"`(→ `ATUGCC_SPAN_METER`).
- `phase` 이벤트에 `buildType` 추가.
- `CMakePresets.json`: configure·build preset `linux-x64-playground-release`.

### 2.2 화면
| 영역 | 내용 |
|---|---|
| 상단 | 프로필 표시와 "길게 실행" 토글, 남은 제한 시간, 빌드 종류 |
| **Timings 탭**(신규) | 행 = (라벨, 파일:줄, 측정기). 열 = 측정기(`wall`/`cpu`/외부 이름), count, total, mean, p50, p95, min, max, 이전 대비 mean 변화율. 열 정렬, 행을 누르면 에디터가 해당 줄로 이동. 실행 중 100ms마다 갱신 |
| 에디터 | span 시작 줄 끝에 인라인 표시 `⏱ 1.23 ms avg ×120` (실행 중 갱신, 다음 실행 시작 시 지움) |
| 행 확장 | 최근 표본의 시간 분포(막대 그림) |

- 시간 단위는 값에 맞게 ns·µs·ms·s로 표시한다(020-06 §2.3과 같은 규칙).
- 숫자 열은 고정폭 숫자(tabular numerals)로 정렬한다.

## 3. C++ Standard Evolution
N/A (도구 작업. C++ 쪽은 020-06)

## 4. Edge Cases
- [x] span이 매우 많음(초당 수십만) → C++ 쪽 flush 간격(Assumption 4), 서버의 100ms 묶음 전송, 브라우저는 키별 집계만 유지한다(개별 span 목록을 보관하지 않음)
- [x] 제한 시간 초과 → 그때까지의 집계를 유지하고 `timedOut` 표시
- [x] 크래시 → 마지막으로 flush된 span까지 표시(최대 100ms 손실을 화면에 안내)
- [x] 같은 줄에 라벨이 다른 span 여러 개 → 별도 행. 인라인 표시는 합쳐서 한 줄
- [x] 이전 실행과 빌드 종류가 다름 → 비교 열에 "빌드 다름" 표시, 변화율 숨김. 측정기가 다르면 같은 키가 아니므로 비교하지 않는다
- [x] 측정 방식을 모르는 레코드(새 `meter` 이름) → 이름 그대로 행을 만든다. 화면은 측정 방식에 의존하지 않는다(020-06 Assumption 1a)
- [x] 상단에 측정기 선택(`wall`/`cpu`)을 두고 서버가 `ATUGCC_SPAN_METER`로 전달한다
- [x] 브라우저 저장소를 쓸 수 없음 → 비교 열만 사라지고 나머지는 동작
- N/A C++ 위험 목록: 이 작업은 C++ 코드를 바꾸지 않는다

## 5. Acceptance Criteria
| ID | Criterion | Verified by |
|---|---|---|
| AC-1 | `profile = "long"`, `timeout = 30` fixture 레슨이 25초 동안 실행되어 정상 종료하고, 같은 레슨이 quick 토글로는 10초에 `timedOut`이 된다 | unittest |
| AC-2 | long 실행은 `linux-x64-playground-release`로 빌드되고 `phase.buildType`이 `RelWithDebInfo`다. `build = "debug"`면 Debug다 | unittest |
| AC-3 | 1초마다 span을 기록하는 레슨에서 실행 중 Timings 행의 count가 최소 3번 서로 다른 시각에 증가한다 | 수동 + 스크린샷, SSE unittest(`trace` 이벤트 도착 시각) |
| AC-4 | 종료 후 Timings의 키별 count·total이 같은 실행의 `formatTimings()` 콘솔 표와 같다 | fixture 레슨이 표를 stdout에 출력, vitest로 비교 |
| AC-5 | 코드를 바꿔 다시 실행하면 이전 대비 열에 mean 변화율이 나오고, 빌드 종류가 다르면 "빌드 다름"이 나온다 | vitest(집계·비교 함수) + 수동 |
| AC-6 | span 시작 줄에 인라인 시간이 표시되고, 행을 누르면 에디터가 그 줄로 이동한다 | 수동, 스크린샷 |
| AC-7 | 초당 10만 span 레슨을 60초 실행하는 동안 브라우저 탭 메모리가 일정 범위를 유지하고(시작 대비 증가가 50 MB 미만) 화면이 멈추지 않는다 | 수동 측정 기록 |
| AC-8 | `npm test`, `test_server.py`, `lint_docs.py` exit 0 | 실행 기록 |

## 6. Out of Scope
- span 이외의 측정(하드웨어 카운터, 메모리 사용량) — 필요 시 새 작업
- 실행 이력 저장과 여러 실행 비교 — 직전 1회만(Assumption 6)
- 단계별 다이어그램 재생 — 070-07

## 7. Dependencies & Adapters
070-02와 같음. 그림(분포 막대)은 SVG로 직접 그린다(새 패키지 없음).

## 8. Documentation Updates
| Document | Section | Change |
|---|---|---|
| `web/README.md` | 프로필, Timings | long 프로필, 토글, Timings 화면 설명 |
| `lessons/README.md` | 성능 측정 레슨 | `[run] profile/timeout/build` 사용법 |
| `.agent/rules/config.md` | presets | `linux-x64-playground-release` 용도 |

## 9. Technical Constraints
- 서버: Python 3.11+ stdlib. 프론트엔드: 070-02와 같은 패키지

## 10. Context & References
- [로컬 웹 플레이그라운드 스펙](/docs/specs/070_02_web_playground.md) — SSE, 프로필 표
- [Tracer 구간 시간 측정 스펙](/docs/specs/020_06_tracer_span_timing.md)
- [레슨 구조 스펙](/docs/specs/070_01_lesson_structure.md) — `[run]`

## 11. Implementation Plan
- [ ] Step 1: preset `linux-x64-playground-release`, 서버 프로필 표 `long` 행, `profileOverride` + 테스트(AC-1, AC-2)
- [ ] Step 2: Timings 집계·비교 모듈 + vitest(AC-4, AC-5)
- [ ] Step 3: Timings 탭, 에디터 인라인 표시, 분포 막대
- [ ] Step 4: 부하 레슨으로 수동 측정(AC-3, AC-6, AC-7), 문서

## 12. Verification Plan
- [ ] `py -3 web/server/test_server.py`, `npm --prefix web/frontend test`
- [ ] `py -3 .agent/scripts/lint_docs.py`
- [ ] 수동 시나리오 스크린샷과 측정값을 `testrecord.md`에
- [ ] Every AC row has its evidence in `testrecord.md`

## History / Amendments
- 2026-10-28: 초안. 070-02 검토 중 사용자 요구(성능 측정 레슨은 10초로 부족, 구간별 시간 스트리밍)에서 분리.
