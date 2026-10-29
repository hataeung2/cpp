---
id: 070-06
title: 장시간 실행 프로필과 구간 시간(Timings) 화면
depends_on: [070-02, 020-06]
unblocks: []
approved: 2026-10-29
---

# Spec 070-06: 장시간 실행 프로필과 구간 시간(Timings) 화면

## 0. Assumptions (please review)
| # | Decision | Rejected alternative | Why |
|---|---|---|---|
| 1 | 레슨이 `[run] profile = "long"`을 선언하면(070-01) 실행 제한이 `timeout`(기본 300초, 최대 1800초)이 된다. Stop은 항상 쓸 수 있다 | 모든 레슨에 긴 제한 / 제한 없음 | 짧은 레슨의 실수(무한 루프)는 10초 안에 끝나야 한다. 측정 레슨만 길게 허용한다. 제한 없음은 잊힌 프로세스를 남긴다 |
| 2 | 화면에서 이번 실행만 프로필을 바꿀 수 있다("길게 실행" 토글). 매니페스트는 바뀌지 않는다 | 매니페스트만 따름 | quick 레슨을 고치다가 측정을 해 보고 싶을 때 매니페스트를 고치지 않게 한다 |
| 3 | long 프로필은 **최적화 빌드**를 기본으로 쓴다: preset `linux-x64-playground-release`(RelWithDebInfo, `-O2 -g`). 매니페스트 `[run] build = "debug"`로 바꿀 수 있다. 화면의 모든 시간 옆에 빌드 종류를 표시한다 | 항상 Debug | Debug(-O0) 시간은 성능 판단을 왜곡한다(020-06 측정: Debug에서 span 하나 0.9–4 µs, Release 0.15–0.28 µs). 최적화 영향 자체를 비교하는 연습을 위해 debug 선택을 남긴다 |
| 4 | 모든 실행(quick 포함)에 서버가 `ATUGCC_TRACE_FLUSH_MS=100`을 설정한다(020-06 Assumption 6) | 줄마다 flush | 측정 대상보다 기록 비용이 커지지 않게 한다(020-06 Release: 줄마다 flush 3.0–6.9 µs → 100 ms 간격 2.4–4.1 µs). 화면 갱신 주기(100 ms)와 맞춘다 |
| 5 | **span 집계는 서버가 한다**(§2.4 설계 결정 기록, 안 A). 서버는 `span` 줄을 개별 이벤트로 보내거나 보관하지 않고, (file, line, label, meter) 키별 누적값을 100 ms 창마다 `spans` 이벤트로 보낸다. 브라우저는 받은 행을 표시만 한다 | 브라우저 집계(초안) / C++ 집계 스트림(안 B) | §2.4. 070-02 서버는 trace 이벤트를 전부 보관하고(늦게 연결한 스트림 재전송용) Events 탭도 전부 보관하므로, span을 그 경로로 보내면 메모리가 span 수에 비례해 늘어난다. C++을 바꾸지 않고 문제를 로컬 도구 안에 가둔다 |
| 6 | 백분위(p50, p95)와 분포 막대는 키마다 **실행 전체에서 균등하게 뽑은 표본 1024개**(reservoir sampling, Algorithm R)로 서버가 계산한다 | 최근 N개 창 / 전체 표본 보관 / 로그 히스토그램 | count·total·min·max와 같은 "실행 전체" 기준이다. 메모리가 키 수에만 비례한다. 1024개면 p95의 표본 오차가 실습 용도에 충분하다. 로그 히스토그램은 정확도가 버킷 폭(≈10%)에 묶인다 |
| 7 | **이전 실행 대비** 열: 레슨마다 직전 실행의 키별 mean과 빌드 종류를 브라우저 저장소에 두고 mean 변화율(%)을 표시한다 | 비교 없음 / 서버에 실행 이력 저장 | 성능 연습의 핵심은 "고치고 다시 재서 비교"다. 직전 한 번이면 충분하다(로컬 편의 기능) |
| 8 | long 실행의 Output 패널은 최근 5,000줄만 유지하고, 서버는 stdout·stderr를 합쳐 8 MiB까지 전송한다(초과분은 버리고 표시) | quick과 같은 1 MiB | 장시간 실행은 출력이 많다. 브라우저 메모리를 일정하게 유지한다 |
| 9 | **trace 파일 예산**: 실행마다 trace 파일이 1 GiB(프로필 표의 값)를 넘으면 서버가 실행을 중지하고 `done.run.traceLimit = true`로 알린다. 그때까지의 집계는 유지한다 | 제한 없음 / 읽기만 멈춤 | 쓰는 쪽은 레슨 프로그램이라 서버가 읽기를 멈춰도 파일은 계속 커진다. 초당 10만 span이면 25 MB/s(30분 long 실행이면 45 GB)다. 디스크를 지키는 확실한 방법은 실행을 멈추는 것이다 |
| 10 | 서버는 trace 파일을 100 ms마다 최대 4 MiB씩 읽는다. 처리하지 못한 양은 `spans.lagBytes`로 보내고 화면에 "집계 지연"으로 표시한다. 실행이 끝나면 남은 분량을 모두 읽는다 | 한 번에 전부 읽기(070-02) | 서버가 뒤처져도 한 번에 큰 덩어리를 메모리에 올리지 않는다. 4 MiB(약 1.6만 줄)는 측정한 파싱 속도로 약 80 ms다 |

## 1. Objective
성능 측정처럼 오래 걸리는 레슨을 웹에서 실행하면서, 코드 구간(020-06 span)별 시간을 **실행 중에 실시간으로** 보고 이전 실행과 비교한다. 070-02의 SSE 스트림과 프로필 표 위에 `long` 행, 서버 span 집계, Timings 화면을 더한다.

## 2. Requirement Details

### 2.1 서버
- 프로필 표(`runner.py` `PROFILES`)에 `long` 행 추가: 실행 제한 = 레슨 `timeout`, 출력 8 MiB, trace 예산 1 GiB. 빌드 preset은 `build`에 따라 `linux-x64-playground-release`(기본) 또는 `linux-x64-playground`. quick 행에도 trace 예산(1 GiB)을 둔다.
- 모든 실행의 환경에 `ATUGCC_TRACE_FLUSH_MS=100`.
- `POST /api/runs` body에 선택 필드 `profileOverride: "quick" | "long"`, `spanMeter: "wall" | "cpu"`(→ `ATUGCC_SPAN_METER`). 다른 값은 400.
- `phase` 이벤트에 `buildType`(`"Debug"` | `"RelWithDebInfo"`) 추가.
- `CMakePresets.json`: configure·build preset `linux-x64-playground-release`(070-02의 `linux-x64-playground`와 같고 build type만 RelWithDebInfo, 빌드 디렉터리 별도).
- trace 읽기(`TraceTail`): 한 번에 최대 4 MiB, 줄 단위로 끊는다. 파일 크기는 `os.stat`으로 매번 확인해 예산과 `lagBytes`를 계산한다.
- `span` 줄 처리(§2.3): `trace` 이벤트와 서버 이벤트 기록(`job.events`)에 넣지 않고 span 집계기(`spans.py`, 새 모듈)로 보낸다. `message`/`transition`/`node`/`diagram` 줄은 070-02와 같다.

### 2.2 SSE 이벤트 (070-02 표에 추가·변경)
| 이벤트 | `data` |
|---|---|
| `phase` | 070-02 필드 + `buildType` |
| `trace` | 070-02와 같다. 단 `kind: "span"` 줄은 들어가지 않는다 |
| `spans`(신규) | `{full: bool, rows: [SpanRow…], spanLines: N, lagBytes: N}`. 100 ms 창에 바뀐 키의 **누적값**만 보낸다(`full: false`). 실행이 끝나면 모든 키를 담은 `full: true` 하나를 `done` 직전에 보낸다 |
| `done` | 070-02 필드 + `run.traceLimit: bool` |

```text
SpanRow = { file, line, label, meter,            // 키 (file은 저장소 상대 경로, 070-02와 같은 변환)
            count, totalNs, minNs, maxNs,         // 실행 전체 누적, 정확한 값
            p50Ns, p95Ns,                         // 표본(최대 1024개)에서 계산
            hist: { loNs, hiNs, bins: [20개 정수] } }  // 표본의 로그 간격 분포
```
- 늦게 연결한 스트림: 070-02처럼 기록된 이벤트를 처음부터 받고, span은 첫 `spans` 이벤트로 **모든 키의 현재 누적값**을 받는다(실행이 끝난 뒤라면 `full: true`). 서버는 span 상태를 `job.events`에 누적하지 않으므로 보관 크기는 키 수에만 비례한다.

### 2.3 span 집계기 (`web/server/spans.py`)
- 입력: `kind: "span"`인 JSON 객체. 키 = (file, line, label, meter). 020-06 `spanStats()`와 같은 키다.
- 키마다 count, totalNs, minNs, maxNs를 정확히 누적하고, 표본 1024개를 Algorithm R로 유지한다(난수 seed는 생성자 인자, 테스트에서 고정).
- `drain() -> rows`: 마지막 drain 이후 바뀐 키의 누적 행. `snapshot() -> rows`: 모든 키.
- p50/p95: 표본을 정렬해 nearest-rank. `hist`: 표본의 min–max를 로그 간격 20칸으로 나눈 개수(min = max면 한 칸).
- `meter` 이름은 해석하지 않는다(020-06 Assumption 1a). 알 수 없는 이름도 그대로 키가 된다.

### 2.4 설계 결정 기록: span을 어디서 줄이는가
나중에 다른 방식을 검토할 때 비교 기준으로 쓴다. 숫자는 2026-10-29 측정(Windows 11 + WSL2 Ubuntu 24.04, GCC 13.3, MSVC 19.51, Python 3.12.3).

**문제.** 020-06은 span마다 JSON 한 줄을 trace 파일에 쓴다. 070-02의 기존 경로는 trace 줄을 전부 SSE `trace` 이벤트로 보내고, 서버(`job.events`, 늦게 연결한 스트림 재전송용)와 브라우저(Events 탭)가 **전부 보관**한다. span은 초당 수만~수십만 개가 될 수 있어 이 경로로는 메모리가 span 수에 비례해 늘어난다.

**측정값**
| 항목 | 값 | 출처 |
|---|---|---|
| span 한 줄 크기 | 215–222 B(probe), 레슨 경로·람다 함수명 기준 약 254 B | `trace_stream_probe` 출력, 2026-10-29 |
| trace 파일 증가 | 초당 1만 span ≈ 2.5 MB/s, 10만 span ≈ 25 MB/s | 줄 크기 × 속도 |
| C++ 기록 비용(Release) | sink 없음 148–278 ns, JSON + 100 ms flush 2.4–4.1 µs, 줄마다 flush 3.0–6.9 µs | 020-06 testrecord "Cost measurements" |
| 측정 대상 오버헤드 | 초당 10만 span이면 JSON 기록에 CPU 약 24%(Linux) | 2.4 µs × 10⁵/s |
| 서버 파싱·집계 | 약 20.7만 줄/s(Python `json.loads` + dict 누적, 코어 1개) | 254 B 줄 20만 개, 2026-10-29 |

**후보**
| | A. 서버 집계 (선택) | B. C++ 집계 스트림 | C. 브라우저 집계 (초안) |
|---|---|---|---|
| 어디서 줄이나 | 서버가 trace 파일의 span 줄을 읽어 키별로 누적 | Tracer가 span 줄 대신 100 ms마다 키별 델타 줄을 씀 | 서버는 전달만, 브라우저가 누적 |
| C++ 변경 | 없음 | 새 작업(020-07): 주기 집계, 표본, 새 JSON 종류 | 없음 |
| 측정 대상 비용(10만/s) | 2.4–4.1 µs/span (≈24%) | ≈0.15–0.28 µs/span + 100 ms마다 키 수만큼 줄 | A와 같음 |
| trace 파일 | span 수에 비례(예산 1 GiB로 중지, Assumption 9) | 키 수 × 실행 시간에 비례(작음) | A와 같음 |
| 서버 CPU | 10만/s ≈ 코어 0.5개 | 거의 없음 | 전달 비용(JSON 재직렬화) |
| 서버·브라우저 메모리 | 키 수 × 1024 표본 | 키 수 | 브라우저가 키 수 × 표본, 단 SSE·Events 경로를 별도로 막아야 함 |
| 네트워크(SSE) | 100 ms마다 바뀐 키만 | 같음 | span 수에 비례 |
| 백분위 | 서버 표본 1024개, 실행 전체 | C++ 쪽 표본 설계 필요(또는 히스토그램) | 브라우저 표본 |
| 개별 span 원본 | trace 파일에 있음(다른 도구가 재사용 가능) | 없음(집계만) | 있음 |
| 실패 격리 | 로컬 도구(Python) 안. 레슨·라이브러리 영향 없음 | 헤더 전용 라이브러리 안(동시성·수명 위험, 020-06 위험 목록 재적용) | 브라우저 탭 멈춤 위험 |
| 검증 | `test_server.py` unittest, 순수 Python 모듈 | GoogleTest + TSan + 서버 테스트 | vitest + 수동 부하 측정 |
| 뒤처질 때 | 화면만 늦어짐(`lagBytes`), 메모리 일정 | 해당 없음 | SSE 버퍼·탭 메모리 증가 |

**결정: A.** 사용자 결정(2026-10-29). span은 성능 측정을 위해 쓰고 버리는 데이터이므로 관리는 로컬 도구에서 해도 된다. 방금 검증한 C++ 라이브러리(020-06)를 다시 바꾸지 않고, 문제가 생겨도 서버 안에서 끝나며, span 원본 스키마가 그대로 남는다.

**A가 감수하는 것과 대응**
- 측정 대상 비용(초당 10만 span에서 약 24%)은 C++ 쪽 문제로 A·C 공통이다. 레슨 안내("핫 루프 안쪽 대신 바깥 구간을 재라", `lessons/README.md`)와 Timings 화면의 안내 문구로 다룬다.
- 파일 크기: 예산 1 GiB를 넘으면 실행 중지(Assumption 9).
- 서버가 뒤처짐: 읽기 4 MiB 제한과 `lagBytes` 표시(Assumption 10). 메모리는 늘지 않는다.

**다시 검토할 조건** (하나라도 생기면 B 또는 다른 안을 새 작업으로 검토한다)
- 측정 대상 오버헤드가 레슨 목적을 해칠 만큼 큰 레슨이 필요할 때(예: 초당 10만 span 이상을 정상 사용으로 둘 때).
- trace 예산(1 GiB)에 걸리는 실행이 흔해질 때.
- 서버 `lagBytes`가 계속 늘어나는 실행이 흔해질 때(서버 처리량 약 20만 줄/s를 넘는 경우).
- 웹이 아닌 소비자(CI, 다른 도구)가 실시간 집계를 필요로 할 때. 이때는 C++ 쪽 집계(B)가 소비자마다 집계기를 만드는 것보다 낫다.
- 다른 전달 방식도 후보다: trace 파일 대신 FIFO(쓰는 쪽에 역압, 디스크 사용 없음), 읽은 구간의 디스크 블록 해제(`fallocate` punch hole). 둘 다 070-02의 파일 경로와 Linux 전용 동작을 바꾸므로 이번 범위에서 제외했다.

### 2.5 화면
| 영역 | 내용 |
|---|---|
| 상단 | 프로필 표시와 "길게 실행" 토글, 측정기 선택(`wall`/`cpu`), 남은 제한 시간, 빌드 종류, 집계 지연(`lagBytes > 0`일 때) |
| **Timings 탭**(신규) | 행 = `spans`의 SpanRow. 열 = 라벨, 파일:줄, 측정기, count, total, mean(total/count), p50, p95, min, max, 이전 대비 mean 변화율. 열 정렬, 행을 누르면 에디터가 해당 줄로 이동. 받은 `spans` 이벤트마다 갱신(최대 100 ms 간격) |
| 에디터 | span 시작 줄 끝에 인라인 표시 `⏱ 1.23 ms avg ×120` (실행 중 갱신, 다음 실행 시작 시 지움). 같은 줄의 여러 행은 count 합과 가중 평균으로 한 줄 |
| 행 확장 | `hist`의 분포 막대(SVG) |
| Events 탭 | 070-02와 같다. span은 나오지 않는다 |

- 시간 단위는 값에 맞게 ns·µs·ms·s로 표시한다(020-06 §2.3과 같은 규칙).
- 숫자 열은 고정폭 숫자(tabular numerals)로 정렬한다.
- `done.run.traceLimit`이면 "trace 1 GiB 초과로 중지: span을 루프 바깥에서 재세요" 안내.

### 2.6 매니페스트
- `[run] build = "release" | "debug"`(선택). 기본: long은 `release`, quick은 `debug`. `release`는 `linux-x64-playground-release`, `debug`는 `linux-x64-playground`로 빌드한다.
- `tools/lessons.py check`가 `build` 값을 검사한다. CMake 정규식은 바꾸지 않는다(빌드 종류는 preset이 정하고, ctest 라벨과 무관하다).

## 3. C++ Standard Evolution
N/A (도구 작업. C++ 쪽은 020-06)

## 4. Edge Cases
- [x] span이 매우 많음(초당 수십만) → C++ flush 간격(Assumption 4), 서버 읽기 4 MiB 제한과 `lagBytes`(Assumption 10), trace 예산(Assumption 9). 서버·브라우저는 키별 누적만 보관한다(개별 span을 보관하지 않음)
- [x] 제한 시간 초과 → 그때까지의 집계를 `full` 스냅샷으로 보내고 `timedOut` 표시
- [x] 크래시 → 마지막으로 flush된 span까지 표시. 화면 안내: "마지막 flush 이후 기록은 빠질 수 있음". 손실은 100 ms로 묶이지 않는다: 100 ms 간격 안에 쓴 뒤 조용해진 프로그램은 다음 기록이나 종료 때까지 줄을 버퍼에 둔다(KI-016). 직전 flush에서 간격 이상 지난 뒤의 기록은 곧바로 flush된다(1초에 한 번씩 기록하는 레슨은 매 기록이 보인다)
- [x] 같은 줄에 라벨이 다른 span 여러 개 → 별도 행. 인라인 표시는 합쳐서 한 줄
- [x] 이전 실행과 빌드 종류가 다름 → 비교 열에 "빌드 다름" 표시, 변화율 숨김. 측정기가 다르면 같은 키가 아니므로 비교하지 않는다
- [x] 측정 방식을 모르는 레코드(새 `meter` 이름) → 이름 그대로 행을 만든다(020-06 Assumption 1a)
- [x] span 줄의 필드가 빠졌거나 타입이 틀림 → 그 줄은 건너뛰고 070-02의 `skippedTraceLines`에 더한다
- [x] 브라우저 저장소를 쓸 수 없음 → 비교 열만 사라지고 나머지는 동작
- [x] 늦게 연결한 스트림 → 현재 누적 스냅샷 하나(§2.2)
- [x] trace 예산 초과 → 실행 중지(프로세스 그룹 종료, 070-02와 같은 경로), 집계 유지, `traceLimit`
- N/A C++ 위험 목록: 이 작업은 C++ 코드를 바꾸지 않는다

## 5. Acceptance Criteria
| ID | Criterion | Verified by |
|---|---|---|
| AC-1 | `profile = "long"`, `timeout = 30` fixture 레슨이 25초 동안 실행되어 정상 종료하고, 같은 레슨이 quick 토글로는 10초에 `timedOut`이 된다 | unittest |
| AC-2 | long 실행은 `linux-x64-playground-release`로 빌드되고 `phase.buildType`이 `RelWithDebInfo`다. `build = "debug"`면 `Debug`다. `tools/lessons.py check`는 `build = "fast"`를 오류로 낸다 | unittest |
| AC-3 | 1초마다 span을 기록하는 fixture에서 `done` 전에 count가 증가한 `spans` 이벤트가 서로 다른 시각에 3번 이상 도착한다 | SSE unittest(도착 시각), 수동 스크린샷 |
| AC-4 | 정상 종료 후 마지막 `spans`(`full: true`)의 키별 count·totalNs·minNs·maxNs가, 같은 실행에서 fixture가 stdout에 출력한 `spanStats()` 값과 정확히 같다 | unittest(fixture가 `spanStats()`를 JSON 한 줄로 출력) |
| AC-5 | 코드를 바꿔 다시 실행하면 이전 대비 열에 mean 변화율이 나오고, 빌드 종류가 다르면 "빌드 다름"이 나온다 | vitest(비교 함수) + 수동 |
| AC-6 | span 시작 줄에 인라인 시간이 표시되고, 행을 누르면 에디터가 그 줄로 이동한다 | 수동, 스크린샷 |
| AC-7 | 초당 10만 span을 30초 기록하는 fixture에서: 서버 기록(`job.events`)의 이벤트 수가 span 수와 무관하게 유지되고(span 0개 실행 대비 `spans` 이벤트만 추가), `trace` 이벤트에 span이 없고, `spans` 이벤트가 500 ms 이상 끊기지 않으며, 서버 프로세스 RSS 증가가 50 MB 미만이다 | unittest |
| AC-8 | 초당 1만 span 레슨을 60초 실행하는 동안 브라우저 탭 메모리 증가가 50 MB 미만이고 Timings가 멈추지 않는다 | 수동 측정 기록 |
| AC-9 | 집계기 단위 검사: 정확한 count/total/min/max, 고정 seed에서 1..10000 균등 분포의 p50·p95가 참값의 ±5% 안, 표본이 키마다 1024개를 넘지 않음, `drain()`이 바뀐 키만 돌려줌 | unittest(`spans.py`) |
| AC-10 | trace 예산을 작게 둔 서버 설정에서 예산을 넘는 fixture가 중지되고 `done.run.traceLimit`이 true이며 임시 trace 파일이 지워진다 | unittest |
| AC-11 | `npm test`, `test_server.py`, `lint_docs.py` exit 0 | 실행 기록 |

## 6. Out of Scope
- C++ 쪽 집계 스트림(§2.4 안 B), FIFO 전달, 디스크 블록 해제 — §2.4 재검토 조건이 생기면 새 작업
- KI-016 해결(flush 간격의 버퍼 꼬리) — 이 작업은 화면 안내로 다룬다
- span 이외의 측정(하드웨어 카운터, 메모리 사용량) — 필요 시 새 작업
- 실행 이력 저장과 여러 실행 비교 — 직전 1회만(Assumption 7)
- 단계별 다이어그램 재생 — 070-07

## 7. Dependencies & Adapters
070-02와 같음. 그림(분포 막대)은 SVG로 직접 그린다(새 패키지 없음). 집계기는 Python 표준 라이브러리만 쓴다(`random`, `bisect`).

## 8. Documentation Updates
| Document | Section | Change |
|---|---|---|
| `web/README.md` | 프로필, Timings | long 프로필, 토글, 측정기 선택, Timings 화면, trace 예산과 집계 지연 |
| `lessons/README.md` | 매니페스트, 성능 측정 레슨 작성 | `[run] build`, long 레슨의 Release 빌드, 웹 Timings 화면 |
| `.agent/rules/config.md` | presets | `linux-x64-playground-release` 용도 |
| `docs/specs/070_02_web_playground.md` | History | `trace` 이벤트에서 span 제외, `spans` 이벤트 추가(070-06) |
| `docs/known_issues.md` | KI-016 | 070-06의 처리(화면 안내, §2.4) 기록 |

## 9. Technical Constraints
- 서버: Python 3.11+ stdlib. 프론트엔드: 070-02와 같은 패키지
- 서버는 Linux(WSL)에서 실행한다(070-02와 같음)

## 10. Context & References
- [로컬 웹 플레이그라운드 스펙](/docs/specs/070_02_web_playground.md) — SSE, 프로필 표, trace 수집
- [Tracer 구간 시간 측정 스펙](/docs/specs/020_06_tracer_span_timing.md) — span 스키마, 비용
- [020-06 testrecord](/docs/tasks/feature_020-06-tracer-span-timing/testrecord.md) — Release 비용 측정
- [레슨 구조 스펙](/docs/specs/070_01_lesson_structure.md) — `[run]`
- [Known issues](/docs/known_issues.md) — KI-016

## 11. Implementation Plan
- [x] Step 1: preset `linux-x64-playground-release`, `[run] build`(lessons.py), 서버 프로필 표 `long` 행, `profileOverride`·`spanMeter` + 테스트(AC-1, AC-2)
- [x] Step 2: `spans.py` 집계기 + 단위 테스트(AC-9)
- [x] Step 3: 서버 trace 경로: span 분리, 4 MiB 읽기, `lagBytes`, `spans` 이벤트, 스냅샷 재전송, trace 예산 + 테스트(AC-3, AC-4, AC-7, AC-10)
- [x] Step 4: Timings 탭, 비교 열, 에디터 인라인 표시, 분포 막대 + vitest(AC-5)
- [x] Step 5: 수동 측정(AC-3 스크린샷, AC-6, AC-8), 문서

## 12. Verification Plan
- [x] `py -3 web/server/test_server.py`(WSL), `npm --prefix web/frontend test`
- [x] `py -3 .agent/scripts/lint_docs.py`
- [x] 수동 시나리오 스크린샷과 측정값을 `testrecord.md`에
- [x] Every AC row has its evidence in `testrecord.md`

## History / Amendments
- 2026-10-28: 초안. 070-02 검토 중 사용자 요구(성능 측정 레슨은 10초로 부족, 구간별 시간 스트리밍)에서 분리.
- 2026-10-29: 020-06 결과 반영해 개정(승인 전). span 집계를 브라우저에서 서버로 옮김(사용자 결정, §2.4 설계 결정 기록: 후보 A/B/C 비교, 측정값, 재검토 조건). 백분위는 실행 전체 reservoir 1024개로 확정. trace 예산과 읽기 제한 추가(Assumption 9, 10). AC-4는 `formatTimings()` 표 대신 `spanStats()` 정확값과 비교. 크래시 손실 문구 수정(KI-016). `[run] build` 매니페스트 범위 추가.
- 2026-10-29: 구현 중 문구 정정(승인 범위 안): §2.2 늦게 연결한 스트림이 받는 것(진행 중에는 `full: false`로 모든 키), §4 flush 문구를 020-06 동작대로. `[run] build`는 index에 적힌 그대로 싣고(null = 기본), 페이지와 runner가 같은 규칙(`effective_build`)을 쓴다.
