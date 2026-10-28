---
id: 020-06
title: Tracer 구간 시간 측정 — span 이벤트와 집계
depends_on: [020-05]
unblocks: [070-06]
approved: null
---

# Spec 020-06: Tracer 구간 시간 측정 — span 이벤트와 집계

## 0. Assumptions (please review)
| # | Decision | Rejected alternative | Why |
|---|---|---|---|
| 1 | 구간은 코드에 표시한 범위만 재는 **RAII 구간 타이머**로 정한다. 단 **무엇으로 재는지**(측정기)는 `SpanMeter` 인터페이스 뒤에 두고 실행 중에 바꿀 수 있다. 기본 구현은 `wall`(경과 시간), 함께 `cpu`(스레드 CPU 시간)를 제공한다 | 시계 고정(steady_clock) / 템플릿 정책(컴파일 타임 선택) / 샘플링 프로파일러(`perf`) | 사용자 요구(2026-10-28): 측정 방식을 바꿀 수 있게 추상화. 실행 중 선택이면 같은 바이너리로 wall과 cpu를 비교할 수 있다(대기·I/O와 계산을 구분하는 연습). 가상 호출 비용은 시계 읽기보다 작다(AC-8에서 측정). `perf`는 WSL 커널과 권한에 따라 동작이 달라 기본값으로 부적합하다 |
| 1a | 다른 측정 방식(외부 프로파일러, 하드웨어 카운터 등)은 **같은 span 레코드**(라벨, 위치, 값, `meter` 이름)로 들어오게 한다. 진입점은 `recordSpan(label, duration, loc, meter)`이고, 웹(070-06)은 레코드만 보고 측정 방식은 모른다 | 방식마다 별도 이벤트 종류 | 소비자(콘솔 표, 웹 Timings)를 한 번만 만든다. 새 방식은 측정기 구현이나 레코드 생산자만 추가하면 된다 |
| 2 | span을 Tracer의 네 번째 이벤트 종류로 넣는다 | `atugcc::core`에 별도 Timer 모듈 | 020-05의 seq·tracerId·이벤트 sink·`ATUGCC_TRACE_OUT` 자동 연결과 콘솔 live 출력을 그대로 쓴다. 로컬 실행(콘솔)과 웹 실행(스트림)에서 같은 코드가 동작한다 |
| 3 | span은 이벤트 deque에 저장하지 않는다. 대신 (위치, 라벨)별 **집계**(count, total, min, max)만 메모리에 두고, 개별 span은 sink로만 흘려보낸다 | 다른 이벤트처럼 deque에 저장 | 핫 루프의 span은 수만 개가 될 수 있어 용량(기본 1024)을 금방 넘고 메모리가 늘어난다. 집계는 크기가 구간 수에 비례한다 |
| 4 | 위치는 구간 **시작 줄**(`source_location`)이다 | 시작·끝 줄 모두 | 소멸자는 `source_location`을 받을 수 없다. 화면은 시작 줄에 시간을 표시한다 |
| 5 | `wall` 측정기는 `std::chrono::steady_clock`, `cpu` 측정기는 POSIX `clock_gettime(CLOCK_THREAD_CPUTIME_ID)` / Windows `GetThreadTimes`. 단위는 ns | `system_clock` / `high_resolution_clock` | 단조 증가가 보장된다. `high_resolution_clock`은 구현에 따라 `system_clock`의 별칭이다 |
| 5a | 측정기 선택: `Tracer::setSpanMeter()`, 없으면 환경변수 `ATUGCC_SPAN_METER=wall\|cpu`, 없으면 `wall`. 구간은 시작할 때의 측정기를 끝까지 쓴다 | 프로세스 전역 하나 | Tracer마다 다르게 쓸 수 있고, 레슨 코드를 고치지 않고 웹이나 셸에서 바꿀 수 있다(020-05 Assumption 3과 같은 원칙) |
| 6 | `JsonLinesEventSink`에 flush 간격 옵션을 둔다(기본 0 = 줄마다 flush, 020-05와 같음). 환경변수 `ATUGCC_TRACE_FLUSH_MS`로도 지정한다 | 항상 줄마다 flush | 핫 루프에서 span마다 flush하면 측정 대상보다 기록 비용이 커진다. 웹 long 프로필(070-06)은 100ms를 쓴다 |

## 1. Objective
"어떤 코드 구간이 얼마나 걸리는지"를 로컬 콘솔과 웹(070-06) 양쪽에서 보이게 한다. 성능 측정 레슨이 쓸 기본 도구다. 020-03(Tracer 자체의 오버헤드 벤치마크)과는 목적이 다르다. 020-03은 라이브러리 성능을, 이 작업은 사용자 코드의 성능을 잰다.

## 2. Requirement Details

### 2.1 Public API Surface
`include/atugcc/pattern/visualizer.hpp`:
```cpp
// 측정기: 구간의 시작과 끝에서 읽는 단조 증가 눈금(ns). 같은 스레드에서 읽는다
class SpanMeter {
public:
    virtual ~SpanMeter() = default;
    [[nodiscard]] virtual std::string_view name() const noexcept = 0;   // "wall", "cpu", ...
    [[nodiscard]] virtual std::uint64_t nowNs() const noexcept = 0;
};
class WallSpanMeter final : public SpanMeter { /* steady_clock */ };
class ThreadCpuSpanMeter final : public SpanMeter { /* 스레드 CPU 시간 */ };

// "wall" | "cpu" → 측정기, 모르는 이름은 nullptr
[[nodiscard]] std::shared_ptr<SpanMeter> makeSpanMeter(std::string_view name);

struct Span {
    std::string   label;
    std::string   meter;        // 측정기 이름 (recordSpan으로 들어온 값은 호출자가 지정)
    std::uint64_t durationNs;
    std::uint64_t threadId;     // std::this_thread::get_id()의 해시
    EventMeta     meta;         // location = 구간 시작, timestamp = 구간 끝
};

struct SpanStats {
    std::string   label;
    std::string   meter;
    std::string   file;
    std::uint32_t line;
    std::uint64_t count, totalNs, minNs, maxNs;
};

class ScopedSpan {                       // 복사·이동 불가
public:
    ScopedSpan(Tracer& tracer, std::string_view label,
               std::source_location loc = std::source_location::current());
    ~ScopedSpan();                       // noexcept, 아직 stop()하지 않았으면 기록
    void stop() noexcept;                // 구간을 일찍 끝냄(두 번째 호출은 무시)
    // 시작할 때 Tracer의 측정기(shared_ptr)를 복사해 두고 끝에서도 같은 것을 쓴다
};

class Tracer {
public:
    void setSpanMeter(std::shared_ptr<SpanMeter> meter);   // nullptr이면 기본(wall)
    [[nodiscard]] std::shared_ptr<SpanMeter> spanMeter() const;

    // auto s = tracer.timeScope("parse");  (C++17 보장된 복사 생략으로 반환)
    [[nodiscard]] ScopedSpan timeScope(std::string_view label,
        std::source_location loc = std::source_location::current());
    // 다른 방식으로 잰 값을 같은 레코드로 넣는 진입점 (Assumption 1a)
    core::Result recordSpan(std::string_view label, std::chrono::nanoseconds duration,
        std::source_location loc = std::source_location::current(),
        std::string_view meter = "manual");
    [[nodiscard]] std::vector<SpanStats> spanStats() const;   // total 내림차순
    [[nodiscard]] std::string formatTimings() const;           // 콘솔용 표
};

class TraceEventSink {
public:
    virtual void onEvent(const Span&) {}   // 기본 no-op: 020-05의 기존 sink 구현을 깨지 않음
};

[[nodiscard]] std::string toJsonLine(const Span&);
```

### 2.2 JSON Lines (스키마 v1에 종류 추가)
```jsonl
{"v":1,"kind":"span","seq":17,"tracer":1,"label":"parse","meter":"wall","durNs":1234567,"thread":3,"file":"…","line":42,"func":"…","tUs":…}
```

### 2.3 콘솔 출력
- live 출력이 켜져 있으면 span마다 한 줄: `⏱ parse  1.235 ms  (main.cpp:42)`
- `formatTimings()`: 라벨, 위치, count, total, mean, min, max 열의 표. 단위는 값에 맞게 ns·µs·ms·s로 바꾼다.

### 2.4 Internal Implementation
- 집계 맵 키 = (file, line, label, meter). Tracer의 기존 `shared_mutex` 아래에서 갱신한다.
- 구간 시작 시 측정기를 읽는 비용: Tracer 락 없이 읽도록 측정기 포인터는 `std::atomic<std::shared_ptr<SpanMeter>>`(C++20)로 둔다.
- `recordSpan`은 seq를 부여하고, 락 밖에서 텍스트 sink와 이벤트 sink를 호출한다(020-05와 같은 경로).
- flush 간격: sink는 마지막 flush 시각을 기억하고, 간격이 지났을 때만 `fflush`한다. 소멸할 때 반드시 flush한다.

### 2.5 Platform Specifics
- `cpu` 측정기: Linux `CLOCK_THREAD_CPUTIME_ID`는 ns 단위다. Windows `GetThreadTimes`는 100ns 단위지만 실제 갱신은 스케줄러 틱(약 15.6ms) 단위라 짧은 구간은 0으로 나올 수 있다. 문서와 콘솔 표의 측정기 이름 옆에 해상도를 표시한다.
- `⏱`(U+23F1)은 UTF-8이다. Windows 콘솔 표시는 KI-011과 같은 문제가 있다. 대체 표기 `[t]`를 쓰는 옵션을 둘지는 KI-011 처리와 함께 정한다.

## 3. C++ Standard Evolution
| Approach | Standard | Description |
|----------|----------|-------------|
| Legacy | C++11/14/17 | `__LINE__` 매크로와 수동 `now()` 차이 계산, 출력은 `printf` |
| Modern | C++20 | `std::source_location` 기본 인자로 위치 자동 수집, RAII 타이머, `std::format`으로 단위 표시 |
| Latest | C++23 | `std::expected` 기반 기록 결과(기존 API와 동일) |

Reference: `/docs/cpp_evolution/source_location.md` (KI-001)

## 4. Edge Cases
- [x] Thread safety: 여러 스레드의 span이 같은 키를 갱신 → Tracer 락. TSan 테스트(AC-4)
- [x] Resource lifetime: `ScopedSpan`은 `Tracer&`를 보관한다. Tracer보다 오래 살면 dangling이다. 문서에 "Tracer보다 짧은 스코프에서만" 쓰라고 명시하고, Debug 빌드에서는 Tracer 소멸 시 살아 있는 span 수를 assert한다
- [x] 예외 전파 중 소멸: 소멸자는 noexcept이고 내부 예외를 삼킨다. 예외로 끝난 구간도 기록한다
- [x] 이동·복사: 삭제한다(이중 기록 방지)
- [x] `stop()` 두 번, `stop()` 후 소멸 → 한 번만 기록
- [x] ODR: 새 inline 함수만 추가한다. 전역 상태는 020-05의 것을 그대로 쓴다
- N/A UB(캐스트·정렬): 해당 없음

## 5. Acceptance Criteria
| ID | Criterion | Verified by |
|---|---|---|
| AC-1 | `sleep_for(20ms)` 구간의 `durationNs`가 20ms 이상 200ms 미만이고, `stop()` 뒤 소멸해도 한 번만 기록된다 | GoogleTest `SpanTiming.*` |
| AC-2 | 같은 위치·라벨 span 1000개의 `spanStats`가 count 1000, min ≤ mean ≤ max, total = 합계다 | GoogleTest |
| AC-3 | span 줄이 §2.2 스키마를 따르고 `json.loads`로 파싱된다. 020-05의 기존 이벤트 줄은 바뀌지 않는다 | GoogleTest + 020-05 검증 스크립트 확장 |
| AC-4 | 4개 스레드 × 10,000 span에서 집계 count가 40,000이고 TSan 경고가 없다 | `linux-x64-tsan` |
| AC-5 | `ATUGCC_TRACE_FLUSH_MS=100`일 때 span 10만 개 기록 시간이 줄마다 flush할 때보다 짧다. 두 경우 모두 파일의 줄 수는 같다 | 측정 테스트(결과는 testrecord에 기록, 통과 기준은 줄 수 일치와 "짧다"만) |
| AC-6 | span 하나의 기록 비용(sink 없음 / JSON sink + 100ms flush)을 Release에서 측정해 레슨 작성 안내(`lessons/README.md`)에 적는다 | 문서 리뷰 |
| AC-7 | Windows `/W4 /WX`, Linux 경고 없이 빌드되고 ASan/UBSan이 통과한다 | `build.py` |
| AC-8 | Linux에서 `sleep_for(20ms)` 구간이 `wall`로는 20ms 이상, `cpu`로는 5ms 미만이다. `ATUGCC_SPAN_METER=cpu`로 실행하면 span 줄의 `meter`가 `cpu`이고, `recordSpan(..., "perf")`로 넣은 값은 `meter: "perf"`로 따로 집계된다. 측정기 가상 호출을 포함한 span 하나의 비용을 AC-6 측정에 함께 적는다 | GoogleTest `SpanMeter.*` + 측정 기록 |
| AC-9 | 구간 도중 `setSpanMeter`로 측정기를 바꿔도 그 구간은 시작 때의 측정기로 끝나고 TSan 경고가 없다 | GoogleTest + `linux-x64-tsan` |

## 6. Out of Scope
- 웹 Timings 화면, long 프로필 — 070-06
- Tracer 자체 오버헤드 벤치마크 — 020-03
- 하드웨어 카운터(캐시 미스 등), 외부 샘플링 프로파일러 연동, 플레임 그래프 — 필요 시 새 작업. `SpanMeter` 구현이나 `recordSpan(..., meter)` 생산자로 추가한다(Assumption 1, 1a)

## 7. Dependencies & Adapters
없음 (표준 C++).

## 8. Documentation Updates
| Document | Section | Change |
|---|---|---|
| `include/atugcc/pattern/visualizer.hpp` | 머리 주석 | span 사용법, 수명 주의 |
| `lessons/README.md` | 성능 측정 레슨 작성 | span 사용법, 기록 비용(AC-6), 핫 루프 안쪽 대신 바깥 구간을 재라는 안내 |
| `README.md` | Features | 구간 시간 측정 한 줄 |

## 9. Technical Constraints
- Compiler: MSVC (VS 2026) / GCC 13+
- CMake: 3.26+
- C++ Standard: C++23 (C++20 minimum)

## 10. Context & References
- [Tracer 이벤트 스트림 스펙](/docs/specs/020_05_tracer_event_stream.md)
- [Tracer](/include/atugcc/pattern/visualizer.hpp)
- [벤치마크 스펙(020-03)](/docs/specs/08_002_benchmark.md)
- [장시간 실행과 Timings 화면 스펙](/docs/specs/070_06_long_run_timings.md)

## 11. Implementation Plan
- [ ] Step 1: `Span`, `recordSpan`, 집계, `spanStats` + 테스트(AC-1, AC-2)
- [ ] Step 2: `SpanMeter`, `WallSpanMeter`, `ThreadCpuSpanMeter`, `makeSpanMeter`, 환경변수 선택 + 테스트(AC-8)
- [ ] Step 3: `ScopedSpan`, `timeScope` + 테스트(AC-9)
- [ ] Step 4: `toJsonLine(Span)`, sink `onEvent(Span)`, flush 간격 + 테스트(AC-3, AC-5)
- [ ] Step 5: live 콘솔 줄, `formatTimings`
- [ ] Step 6: TSan(AC-4, AC-9), 비용 측정(AC-6, AC-8), 문서

## 12. Verification Plan
- [ ] `py -3 .agent/scripts/build.py --preset windows-x64-debug --test`
- [ ] `py -3 .agent/scripts/build.py --preset linux-x64-debug --test`, `linux-x64-asan`, `linux-x64-tsan`
- [ ] Every AC row has its evidence in `testrecord.md`

## History / Amendments
- 2026-10-28: 초안. 070-02 검토 중 사용자 요구("어떤 코드 라인에서 얼마나 걸리는지 스트리밍")에서 분리.
- 2026-10-28: 검토 반영: 측정 방식을 `SpanMeter`로 추상화(wall, cpu), 외부 방식은 `recordSpan(..., meter)`로 같은 레코드에 합류(Assumption 1, 1a, 5a).
