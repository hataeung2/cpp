---
id: 020-05
title: Tracer 이벤트 스트림 — JSON Lines 구조화 출력
depends_on: []
unblocks: [070-02, 020-06]
approved: 2026-10-28
---

# Spec 020-05: Tracer 이벤트 스트림 — JSON Lines 구조화 출력

## 0. Assumptions (please review)
| # | Decision | Rejected alternative | Why |
|---|---|---|---|
| 1 | 출력 형식은 JSON Lines(한 줄에 이벤트 하나)이다 | stdout에 marker를 넣어 완성된 다이어그램 문자열 전달 / 종료 시 JSON 문서 하나 | marker는 사용자 출력이나 다른 스레드 출력이 끼어들면 깨지고, 완성된 그림만 전달된다. 줄 단위로 쓰면 크래시 직전까지의 이벤트가 남고 쓰는 쪽에서 버퍼링할 필요가 없다 |
| 2 | 텍스트 sink(`TraceOutputSink`)와 별개로 **이벤트 sink** 연결점을 추가한다 | 기존 텍스트 sink에 "live 포맷 선택"만 추가 | 텍스트 sink는 포맷된 문자열을 받는다. 웹은 이벤트 원본(필드, 소스 위치)이 필요하고, 콘솔 출력과 이벤트 기록을 동시에 켤 수 있어야 한다 |
| 3 | 환경변수 `ATUGCC_TRACE_OUT=<파일 경로>`가 있으면 모든 `Tracer`가 프로세스 공용 JSON Lines sink에 자동으로 연결된다 | 레슨 코드가 직접 sink를 설정 | 같은 레슨 코드를 로컬 빌드와 웹 실행에서 수정 없이 돌리기 위해서다(070 그룹 목표: 직접 컴파일과 웹 작업 반반). 변수가 없으면 지금과 동작이 같다 |
| 4 | `EventMeta`에 프로세스 전역 `seq`(1부터 증가)와 `tracerId`를 추가한다 | timestamp로 정렬 | 이벤트 세 종류가 서로 다른 deque에 저장되어 종류 간 순서가 없다. 같은 시각의 이벤트는 timestamp로 순서를 정할 수 없다. Tracer가 여러 개면(예제처럼 데모마다 하나) 구분이 필요하다 |
| 5 | Tracer 소멸자가 Mermaid `diagramParts()`를 `diagram` 줄로 내보낸다 (이벤트 sink가 있을 때만) | 웹(TypeScript)에서 이벤트로 다이어그램을 다시 생성 | 분할 예산·`×N` 규칙(020-04)의 구현을 C++ 하나로 유지한다. 단계별 다이어그램 재생은 범위 밖(§6) |
| 6 | JSON 직렬화는 손으로 작성한다 (문자열 escape만 필요) | nlohmann/json 의존성 추가 | 필드가 고정된 세 종류 이벤트뿐이다. 라이브러리의 "표준 C++만" 원칙(spec 08)을 유지한다 |

## 1. Objective
웹 플레이그라운드(070-02)가 Tracer의 실행 기록을 **구조화된 데이터**로 받게 한다. 그래야 이벤트 목록, 이벤트별 소스 줄 표시(`EventMeta::location`), 다이어그램 조각 렌더링을 브라우저에서 할 수 있다. 콘솔 출력(텍스트 sink, `formatTerminal`)은 그대로 둔다.

## 2. Requirement Details

### 2.1 Public API Surface
`include/atugcc/pattern/visualizer.hpp`:
```cpp
struct EventMeta {
    std::source_location location;
    std::chrono::system_clock::time_point timestamp{ std::chrono::system_clock::now() };
    std::uint64_t seq{ 0 };       // 신규: 기록 시 Tracer가 부여, 프로세스 전역 단조 증가
    std::uint32_t tracerId{ 0 };  // 신규: Tracer 생성 순서 (1부터)
};

// 이벤트 sink: 기존 EventSink concept(onEvent)을 만족하는 다형 인터페이스
class TraceEventSink {
public:
    virtual ~TraceEventSink() = default;
    virtual void onEvent(const Message&) = 0;
    virtual void onEvent(const Transition&) = 0;
    virtual void onEvent(const Node&) = 0;
    virtual void onDiagramParts(std::uint32_t tracerId, const std::vector<DiagramPart>&) = 0;
};

class JsonLinesEventSink final : public TraceEventSink {
public:
    [[nodiscard]] static std::shared_ptr<JsonLinesEventSink> open(const std::filesystem::path& path); // 실패 시 nullptr
    // onEvent / onDiagramParts: 한 줄 쓰고 flush, 내부 mutex로 줄 단위 원자성
};

// 이벤트 하나를 JSON 한 줄(개행 없음)로 — 테스트와 다른 sink에서 재사용
[[nodiscard]] std::string toJsonLine(const Message&);
[[nodiscard]] std::string toJsonLine(const Transition&);
[[nodiscard]] std::string toJsonLine(const Node&);

class Tracer {
public:
    void setEventSink(std::shared_ptr<TraceEventSink> sink);
    [[nodiscard]] std::shared_ptr<TraceEventSink> eventSink() const;
    [[nodiscard]] std::uint32_t id() const noexcept;
    ~Tracer();  // 이벤트 sink가 있으면 diagramParts(Mermaid)를 내보낸다. 예외를 밖으로 내지 않는다
};

// ATUGCC_TRACE_OUT이 설정되어 있으면 프로세스 공용 sink, 아니면 nullptr. 첫 호출 때 한 번만 연다
[[nodiscard]] std::shared_ptr<TraceEventSink> environmentEventSink();
```
Tracer 생성자는 `environmentEventSink()`를 기본 이벤트 sink로 설정한다. `setEventSink(nullptr)`로 끌 수 있다.

### 2.2 JSON Lines 스키마 (v1)
모든 줄에 `"v":1`, `"kind"`가 있다. 문자열은 UTF-8, JSON escape(`"`, `\`, 제어 문자 `\u00XX`).
```jsonl
{"v":1,"kind":"message","seq":3,"tracer":1,"from":"Subject","to":"Observer1","action":"notify()","file":"main.cpp","line":42,"func":"void run()","tUs":1761600000123456}
{"v":1,"kind":"transition","seq":4,"tracer":1,"old":"IDLE","new":"STANDBY","trigger":"init","file":"main.cpp","line":51,"func":"...","tUs":...}
{"v":1,"kind":"node","seq":5,"tracer":2,"parent":"Coffee","child":"Milk","relation":"wraps","file":"...","line":...,"func":"...","tUs":...}
{"v":1,"kind":"diagram","tracer":1,"part":0,"parts":2,"diagram":"sequence","backend":"mermaid","title":"Sequence (1/2)","overBudget":false,"source":"sequenceDiagram\n..."}
```
- `file`은 `source_location::file_name()` 그대로다. 저장소 상대 경로로 바꾸는 일은 소비자(070-02 서버)가 한다.
- `tUs`: Unix epoch 기준 마이크로초.

### 2.3 Internal Implementation
- `detail/json_lines.hpp` (신규): escape 함수와 `toJsonLine` 구현.
- `seq`: `inline std::atomic<std::uint64_t>` 전역 카운터. `record*`의 unique_lock 안에서 부여한다(같은 Tracer 안에서 저장 순서 = seq 순서).
- 이벤트 sink 호출은 기존 텍스트 sink와 같이 **Tracer 락 밖에서** 한다. 그래서 여러 스레드가 쓸 때 파일의 줄 순서는 seq 순서와 다를 수 있다. 소비자는 seq로 정렬한다.
- 용량 초과로 기록이 실패한 이벤트(`std::unexpected`)는 sink로도 보내지 않는다.

### 2.4 Platform Specifics
- `std::getenv`는 MSVC에서 C4996 경고가 난다. `/WX` preset이 있으므로 Windows에서는 `_dupenv_s`를 쓰거나 해당 줄만 경고를 억제한다.
- 파일 열기: `std::filesystem::path`로 열어 Windows에서 비 ASCII 경로를 지원한다. 쓰기는 binary 모드로 한다(개행 `\n` 고정).

## 3. C++ Standard Evolution
| Approach | Standard | Description |
|----------|----------|-------------|
| Legacy | C++11/14/17 | `__FILE__`/`__LINE__` 매크로로 위치 전달, 출력 경로는 호출자가 분기 |
| Modern | C++20 | `std::source_location` 기본 인자로 위치 자동 수집, `std::format`으로 직렬화, concept(`EventSink`)으로 sink 계약 표현 |
| Latest | C++23 | 실패를 `std::expected`로 반환하는 record API와 결합(기존 유지) |

Reference: `/docs/cpp_evolution/source_location.md` (KI-001: 아직 없음, 이 작업에서 만들지 않음)

## 4. Edge Cases
- [x] Thread safety: seq는 atomic, sink 호출은 Tracer 락 밖, `JsonLinesEventSink`는 자체 mutex로 줄 단위 원자성 보장. TSan preset으로 검증(AC-6).
- [x] Resource lifetime: 공용 sink는 함수 내부 static `shared_ptr`가 소유하고, 각 Tracer가 복사본을 가진다. 그래서 정적 소멸 순서와 관계없이 `Tracer::global()`의 소멸자가 sink를 안전하게 쓴다.
- [x] 소멸자 안의 I/O: 예외를 잡아 삼킨다. 파일 쓰기 실패는 무시한다(트레이스는 진단용이다).
- [x] Platform differences: §2.4.
- [x] ODR: 전역 카운터와 공용 sink는 `inline` 변수와 `inline` 함수의 static local이라 TU마다 하나가 아닌 프로그램 전체에 하나다.
- [x] 크래시와 `std::exit`: 이벤트 줄은 쓸 때마다 flush되어 남는다. `diagram` 줄은 소멸자가 실행되지 않으면 없다. 소비자는 diagram 줄이 없어도 동작해야 한다(070-02).
- [x] 변수가 설정됐지만 파일을 열 수 없을 때: sink 없음(nullptr), 프로그램은 그대로 실행된다.
- N/A Template instantiation: 새 템플릿 없음.

## 5. Acceptance Criteria
| ID | Criterion | Verified by |
|---|---|---|
| AC-1 | `ATUGCC_TRACE_OUT`이 없을 때 기존 테스트 전체와 `atugcc_pattern_example`의 stdout이 변경 전과 같다 | 전체 ctest, 예제 출력 diff |
| AC-2 | 세 종류 이벤트 각각의 `toJsonLine`이 §2.2 스키마의 모든 필드를 가지며, 따옴표·역슬래시·개행·제어 문자·한글이 포함된 라벨이 유효한 JSON으로 escape된다 | GoogleTest `JsonLines.*` (Python `json.loads`로 교차 확인하는 테스트 스크립트 포함) |
| AC-3 | 한 Tracer 안에서 seq는 기록 순서대로 엄격히 증가하고, 두 Tracer의 seq는 겹치지 않는다 | GoogleTest |
| AC-4 | 환경변수를 지정해 예제를 실행하면 파일의 모든 줄이 `json.loads`로 파싱되고, 기록된 이벤트 수와 이벤트 줄 수가 같으며, Tracer마다 `diagram` 줄이 `diagramParts(Mermaid)`의 조각 수만큼 있다 | 테스트 스크립트(`tests/` 아래 Python, ctest에 등록) |
| AC-5 | 열 수 없는 경로를 지정해도 프로그램이 정상 종료하고 stdout이 AC-1과 같다 | 같은 스크립트 |
| AC-6 | 4개 스레드가 동시에 기록해도 모든 줄이 온전하고(줄 섞임 없음) TSan 경고가 없다 | `linux-x64-tsan` preset 테스트 |
| AC-7 | Windows `/W4 /WX`, Linux `-Wall -Wextra` 경고 없이 빌드되고 ASan/UBSan preset이 통과한다 | `build.py --preset windows-x64-debug --test`, `linux-x64-asan` |

## 6. Out of Scope
- 이벤트 단위 다이어그램 재생(N번째 이벤트까지의 다이어그램) — 070-07
- 코드 구간 시간 측정(span 이벤트) — 020-06
- PlantUML/D2 조각을 `diagram` 줄로 내보내기 — 웹은 Mermaid만 렌더링(070-02 Assumption). 필요하면 백엔드 선택 변수를 추가
- `docs/cpp_evolution/source_location.md` 작성 — KI-001

## 7. Dependencies & Adapters
없음 (표준 C++만).

## 8. Documentation Updates
| Document | Section | Change |
|---|---|---|
| `include/atugcc/pattern/visualizer.hpp` | 파일 머리 주석 "학습 포인트" | 이벤트 sink와 `ATUGCC_TRACE_OUT` 추가 |
| `docs/specs/08_pattern_visualizer.md` | — | 수정하지 않음(legacy). 이 스펙이 후속 |
| `README.md` | Features | Tracer JSON Lines 출력 한 줄 |
| `src/pattern/example_visualizer.cpp` | 머리 주석 | `ATUGCC_TRACE_OUT` 사용법 |

## 9. Technical Constraints
- Compiler: MSVC (VS 2026) / GCC 13+ (WSL Ubuntu 24.04 기준 13.3)
- CMake: 3.26+
- C++ Standard: C++23 (C++20 minimum)

## 10. Context & References
- [Tracer](/include/atugcc/pattern/visualizer.hpp)
- [다이어그램 가독성 스펙](/docs/specs/020_04_diagram_readability.md) — `diagramParts`
- [diagrams.md](/.agent/rules/diagrams.md) §2 Structured output
- [웹 플레이그라운드 스펙](/docs/specs/070_02_web_playground.md)

## 11. Implementation Plan
- [ ] Step 1: `EventMeta`에 seq·tracerId 추가, `record*`에서 부여
- [ ] Step 2: `detail/json_lines.hpp` — escape, `toJsonLine` + GoogleTest
- [ ] Step 3: `TraceEventSink`, `JsonLinesEventSink`, `Tracer::setEventSink`, 락 밖 호출
- [ ] Step 4: `environmentEventSink()`, 생성자 기본 연결, 소멸자의 diagram 줄
- [ ] Step 5: Python 검증 스크립트(AC-4, AC-5)와 ctest 등록, TSan 테스트(AC-6)

## 12. Verification Plan
- [ ] `py -3 .agent/scripts/build.py --preset windows-x64-debug --test`
- [ ] `py -3 .agent/scripts/build.py --preset linux-x64-debug --test`, `linux-x64-asan`, `linux-x64-tsan`
- [ ] Every AC row has its evidence in `testrecord.md`

## History / Amendments
- 2026-10-28: 초안. 웹 플레이그라운드(070 그룹) 논의에서 분리한 선행 작업.
- 2026-10-28: 사용자 승인.
