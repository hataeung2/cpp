---
id: 070-07
title: 단계별 다이어그램 재생 (N번째 이벤트까지의 다이어그램)
depends_on: [070-02, 020-05]
unblocks: [070-04]
approved: 2026-11-10
---

# Spec 070-07: 단계별 다이어그램 재생 (N번째 이벤트까지의 다이어그램)

## 0. Assumptions (please review)
| # | Decision | Rejected alternative | Why |
|---|---|---|---|
| 1 | **범위는 넷이다**: (a) C++: 다이어그램 생성의 본체를 이벤트 목록을 받는 공개 자유 함수 `viz::diagramPartsOf(…)`로 빼고, 범위 `DiagramRange`(어느 seq까지, 마지막 이벤트 강조)를 받게 한다. `Tracer::diagramParts`는 그 함수를 부른다. (b) 도구 `atugcc_diagram_replay`(C++ 실행 파일): 020-05 JSON Lines 이벤트를 읽어 그 함수를 부르고 `diagram` 줄을 쓴다. (c) 서버 `GET /api/runs/<id>/diagrams?tracer=<t>&until=<seq>`. (d) 페이지: Diagrams 탭의 재생 막대와 Events·편집기 연동 | — | BACKLOG 줄의 "C++ diagramParts 범위 지정 필요"를 구체화한 것이다 |
| 2 | **다이어그램 생성기는 C++ 하나**다. 재생도 같은 C++ 코드로 만든다 | 서버(Python)나 페이지(TypeScript)로 Mermaid 생성기를 옮김 | 생성기가 둘이면 분할 규칙(diagrams.md §2의 예산), 줄 바꿈, 이름 이스케이프가 갈라진다. AC-1이 "끝까지 재생 = 소멸자가 쓴 다이어그램"을 바이트로 비교해 하나임을 보인다 |
| 3 | **재생 입력은 실행이 남긴 이벤트**다. 프로그램을 다시 돌리지 않는다. 서버는 실행의 `trace` 이벤트(message, transition, node)를 이미 들고 있고, 그것을 tracer별로 도구의 stdin에 준다 | 프로그램을 N번째 이벤트에서 멈추게 다시 실행 | 다시 돌리면 시간·스레드에 따라 이벤트가 달라지고(seq가 프로세스 전역), 느리다 |
| 4 | **Tracer에 이벤트를 다시 넣는 API는 만들지 않는다.** 분할·포맷의 본체를 `diagramPartsOf(std::span<const Message>, std::span<const Transition>, std::span<const Node>, DiagramBackend, const DiagramBudget&, const DiagramRange&)`로 공개하고, 도구는 이벤트에서 이 세 목록을 만든다 | `Tracer::replay(event)` | Tracer는 기록하는 쪽이다. 남의 seq·위치를 가진 이벤트를 넣는 길을 열면 seq가 겹치는 Tracer가 생긴다. 자유 함수는 상태가 없어 시험하기 쉽다 |
| 5 | **`DiagramRange { std::uint64_t untilSeq = max; bool markLast = false; }`**. `untilSeq` 이하의 seq를 가진 이벤트만 쓴다(세 종류 모두, seq는 프로세스 전역). `markLast`면 범위 안의 마지막 이벤트를 강조한다(Assumption 6). 기본값이면 지금과 같은 결과 | 이벤트 개수(N번째) | seq는 이벤트 스트림과 Events 탭이 이미 쓰는 열쇠라 페이지에서 그대로 쓴다 |
| 6 | **강조는 Mermaid만**: Sequence는 마지막 메시지를 `rect`로 감싼다. State는 마지막 전이의 도착 상태에 `classDef current` + `class <state> current`. Structure는 마지막 관계의 선에 `linkStyle <n>`. 색은 Mermaid 테마 변수와 어울리는 노랑 반투명(페이지의 `--line-highlight`와 같은 값). PlantUML·D2는 `markLast`를 무시한다(문서에 적음) | 세 백엔드 모두 | 웹은 Mermaid만 쓴다(diagrams.md §3). 나머지는 필요해질 때 |
| 7 | **이벤트 리더는 도구 안에 둔다**(`tools/diagram_replay/`, 라이브러리 아님): 020-05 형식(평평한 객체, 문자열·정수·불리언, `\"` `\\` `\n` `\uXXXX` 이스케이프)만 읽는 작은 리더. 모르는 키는 건너뛰고, `v`가 1이 아니면 그 줄을 건너뛰며 셈 | (a) 외부 JSON 라이브러리; (b) 서버가 다른 텍스트 형식으로 바꿔 줌 | (a) 외부 의존은 backend 뒤에 둬야 하고(impl.md §5) 이 일에는 과하다. (b) 이스케이프 규칙이 하나 더 생긴다. 리더는 쓰는 쪽(`toJsonLine`)과 같은 저장소에 있고 왕복 테스트로 묶는다 |
| 8 | **도구 빌드**: 루트 `CMakeLists.txt`가 `ATUGCC_BUILD_LESSONS`일 때 `tools/diagram_replay/`를 더한다. 웹 Run은 `--target lesson_<id> atugcc_diagram_replay`로 같이 빌드한다(처음 한 번만 실제로 빌드) | 재생을 처음 누를 때 빌드 | 재생 버튼이 빌드 때문에 수십 초 기다리는 일이 없다. 두 번째부터는 빌드할 것이 없다 |
| 9 | **재생은 실행이 끝난 뒤**(`done`)에만 켜진다. 재생할 수 있는 이벤트는 tracer당 5,000개까지(Events 탭의 `MAX_EVENTS`와 같음). 넘으면 막대가 꺼지고 이유를 보인다 | 실행 중 재생 | 실행 중에는 이벤트가 계속 늘어 "마지막"이 움직인다. 상한은 도구의 입력과 페이지의 그리기를 묶는다 |
| 10 | **페이지**: Diagrams 탭 위에 재생 막대(tracer 선택(둘 이상일 때), ⏮ ◀ ▶ ⏭, 슬라이더, `k / n` 단계와 이벤트 설명). 키 ←/→(패널에 포커스가 있을 때). 단계를 옮기면 (1) 그 단계의 다이어그램을 그리고(150ms 늦춰 몰아 요청, 결과는 `(tracer, seq)`로 캐시), (2) Events 탭의 그 행을 선택하고, (3) 편집기에서 그 이벤트의 소스 줄을 강조한다. Events 탭의 행을 누르면 재생도 그 단계로 간다. 막대를 끄면 지금처럼 완성된 다이어그램 | 슬라이더만 | 단계마다 "어느 코드 줄이 이 화살표를 만들었는가"를 보는 것이 재생의 목적이다 |
| 11 | **Sequence 조각**: `untilSeq`로 자른 뒤 예산대로 나누므로, 조각은 커서 이벤트가 든 조각까지만 생긴다. 페이지는 마지막 조각(커서가 있는 조각)을 펼치고 앞 조각은 접는다 | 모든 조각을 늘 보임 | 긴 시퀀스에서 지금 단계가 화면 밖에 있으면 재생의 뜻이 없다 |
| 12 | 서버는 tracer별로 도구를 한 번 띄워 요청마다 다시 띄운다(요청당 수 ms). 캐시는 페이지가 한다 | 서버에 상주 프로세스 | 로컬 한 사용자 도구라 단순한 쪽을 고른다(기억: 같은 동작이면 읽기 쉬운 설계) |
| 13 | 070-16 연습 모드에서도 같다(이벤트의 파일 경로가 사본 경로일 뿐) | — | 070-16 Assumption 11 |

## 1. Objective
지금 Diagrams 탭은 실행이 끝난 뒤 완성된 다이어그램만 보인다. 패턴 레슨(021–024, 070-04)에서는 "이 메시지가 언제, 어느 줄에서 생겼고 그때까지 상태가 어땠는가"를 한 단계씩 보는 것이 이해의 핵심이다. 이 작업은 실행이 남긴 이벤트로 N번째 이벤트까지의 다이어그램을 같은 C++ 생성기로 다시 만들고, 페이지에서 앞뒤로 재생하며 Events 탭과 편집기 줄을 함께 움직이게 한다.

## 2. Requirement Details

### 2.1 Public API Surface
[`include/atugcc/pattern/visualizer.hpp`](/include/atugcc/pattern/visualizer.hpp):
```cpp
namespace atugcc::pattern::viz {
struct DiagramRange {
    std::uint64_t untilSeq = std::numeric_limits<std::uint64_t>::max();
    bool          markLast = false;   // Mermaid only
};

[[nodiscard]] std::vector<DiagramPart> diagramPartsOf(
    std::span<const Message> messages,
    std::span<const Transition> transitions,
    std::span<const Node> nodes,
    DiagramBackend backend = DiagramBackend::PlantUML,
    const DiagramBudget& budget = {},
    const DiagramRange& range = {});

class Tracer {
    // 기존 시그니처 유지, 범위를 받는 오버로드 추가
    [[nodiscard]] std::vector<DiagramPart> diagramParts(
        DiagramBackend backend, const DiagramBudget& budget, const DiagramRange& range) const;
};
}
```
기존 `diagramParts(backend, budget)`와 `formatDiagram`은 그대로 동작한다(기본 범위).

### 2.2 Internal Implementation
| 곳 | 바꾸는 것 |
|---|---|
| [`detail/diagram_parts.hpp`](/include/atugcc/pattern/detail/diagram_parts.hpp) | 본체를 `diagramPartsOf`로, 범위 거르기(seq), `Tracer::diagramParts`는 스냅숏을 떠서 호출 |
| Mermaid 포맷터(`detail/`) | `markLast` 강조(Assumption 6) |
| `tools/diagram_replay/` (새) | `CMakeLists.txt`(타깃 `atugcc_diagram_replay`), `event_reader.hpp`(Assumption 7), `main.cpp`: 인자 `--tracer <id> --until <seq> [--mark-last]`, stdin JSON Lines → stdout `diagram` 줄(020-05 형식, `toJsonLine`) |
| [`tests/pattern/`](/tests/pattern/) | `diagramPartsOf` 범위(처음, 중간, 끝, 범위 밖), 강조 출력, 리더 왕복(`toJsonLine` → 리더 → 같은 이벤트, 이스케이프), 시나리오 하나(`tests/scenario/`: 이벤트 파일 → 도구 → 다이어그램 줄) |
| [`web/server/runner.py`](/web/server/runner.py), [`server.py`](/web/server/server.py) | 실행의 trace 이벤트를 tracer별로 보관(상한 Assumption 9), 새 엔드포인트, 빌드 타깃에 도구 |
| [`web/frontend/src/diagrams.ts`](/web/frontend/src/diagrams.ts), `events.ts`, `main.ts`, `i18n.ts`, `theme.css` | 재생 막대, 캐시, 연동 |
| [`web/server/test_server.py`](/web/server/test_server.py), 프런트엔드 테스트 | 엔드포인트, 상한, 단계 이동 상태 |

### 2.3 Platform Specifics
도구는 두 OS에서 빌드된다(MSVC, Clang). 웹은 Linux에서만 부른다. 그 밖 none.

## 3. C++ Standard Evolution
| Approach | Standard | Description |
|----------|----------|-------------|
| Legacy | C++11/14/17 | 범위를 `(const std::vector<T>&, size_t first, size_t last)`로 넘김 |
| Modern | C++20 | `std::span<const T>`로 소유 없이 목록을 받음, `DiagramRange`를 designated initializers로(`{.untilSeq = 42, .markLast = true}`), `std::ranges::partition_point`로 seq 경계 찾기 |
| Latest | C++23 | N/A |

Reference: [`/docs/cpp_evolution/designated_initializers.md`](/docs/cpp_evolution/designated_initializers.md)(있음)에 `DiagramRange` 예 한 줄.

## 4. Edge Cases
- [x] Thread safety — `Tracer::diagramParts`는 지금처럼 `shared_lock` 아래에서 복사한 뒤 자유 함수를 부른다. 자유 함수는 상태가 없다.
- [x] Resource lifetime / dangling views — `std::span`은 호출 동안만 쓰고 결과(`DiagramPart`)는 문자열을 소유한다.
- [x] Platform differences — N/A(같은 포맷터).
- [x] Template instantiation / concept constraints — N/A.
- [x] ODR — 새 함수는 헤더의 `inline`. 도구의 리더는 도구 안 한 TU.
- [x] Undefined behaviour — 리더는 잘못된 줄을 건너뛰고 센다(`skipped`를 stderr 마지막 줄에). 범위 밖 `untilSeq`(첫 이벤트보다 작음)는 빈 결과.
- [x] seq가 정렬되지 않은 입력 — 여러 스레드의 이벤트는 파일 순서와 seq 순서가 다를 수 있다. 도구는 seq로 정렬한 뒤 자른다. 소멸자 쪽 결과와 같게 하려고 Tracer 안의 순서(기록 순서)를 쓰는지, seq 순서를 쓰는지 DEV 첫 단계에서 확인하고 AC-1이 같음을 보인다.
- [x] 이벤트가 없는 tracer — 막대가 꺼진다.
- [x] span 이벤트 — 단계에 넣지 않는다(다이어그램에 나오지 않음).
- [x] 상태 예산 초과(State는 나누지 않음) — 지금처럼 한 조각 + 초과 표시. 강조도 그대로.

## 5. Acceptance Criteria
| ID | Criterion | Verified by |
|---|---|---|
| AC-1 | Tracer를 쓰는 모든 레슨에서, 실행의 이벤트를 도구에 마지막 seq까지(`markLast` 없이) 주면 그 실행의 소멸자가 쓴 `diagram` 줄과 바이트가 같다 | 시나리오 테스트 + 레슨별 비교 스크립트 기록(testrecord) |
| AC-2 | `diagramPartsOf`가 처음·중간·끝·범위 밖에서 맞는 이벤트만 쓰고, 기본 범위의 결과는 이 작업 전의 `diagramParts`와 같다 | GoogleTest(`tests/pattern/`), 기존 다이어그램 테스트 통과 |
| AC-3 | `markLast`가 Mermaid 세 종류에서 Assumption 6의 강조를 넣고, Mermaid가 그것을 오류 없이 그린다 | GoogleTest(문자열), 헤드리스 브라우저 렌더 |
| AC-4 | 리더가 `toJsonLine`의 모든 이벤트 종류와 이스케이프를 왕복하고, 깨진 줄·`v` 다른 줄을 건너뛰고 센다 | GoogleTest |
| AC-5 | 웹: `device_state_machine`에서 재생 막대로 단계를 옮기면 다이어그램이 그 단계까지로 바뀌고 마지막 이벤트가 강조되며, Events 행 선택과 편집기 줄 강조가 같이 움직인다. Events 행을 누르면 재생이 그 단계로 간다. 5,000개를 넘는 실행에서는 막대가 꺼지고 이유가 보인다 | 헤드리스 브라우저 스크린샷 3장(처음, 중간, 끝), `test_server.py`의 상한 |
| AC-6 | 전체 suite(`windows-x64-debug`, `linux-x64-debug`), 새 시나리오(`--label scenario`), 프런트엔드 테스트, `PlaygroundServer`가 통과하고 §8 문서가 결과와 맞으며 `lint_docs.py`가 exit 0이다 | 명령 출력 |

## 6. Out of Scope
- PlantUML·D2의 강조 — 필요해지면 KI
- 실행 중 재생 — Assumption 9
- 재생을 GIF·동영상으로 저장 — 계획 없음
- Mermaid 제목이 코드 펜스 밖(KI-010) — 이 작업과 무관(웹은 영향 없음)

## 7. Dependencies & Backends
없음. 도구의 JSON 리더는 자체 코드(Assumption 7).

## 8. Documentation Updates
| Document | Section | Change |
|---|---|---|
| [`include/atugcc/pattern/visualizer.hpp`](/include/atugcc/pattern/visualizer.hpp) | 머리 주석 | `diagramPartsOf`, `DiagramRange` 사용 예 |
| [`.agent/rules/diagrams.md`](/.agent/rules/diagrams.md) | §3 Viewer policy | 재생 중 강조와 조각 접기(한두 줄) |
| [`web/README.md`](/web/README.md) | API, Page | 새 엔드포인트, 재생 막대 |
| [`docs/specs/020_05_tracer_event_stream.md`](/docs/specs/020_05_tracer_event_stream.md) | — | 고치지 않는다(봉인된 스펙). 이 스펙이 형식을 그대로 읽는다 |
| [`docs/cpp_evolution/designated_initializers.md`](/docs/cpp_evolution/designated_initializers.md), `.en.md` | 예 | `DiagramRange` 한 줄 |
| [`lessons/README.md`](/lessons/README.md) | 웹에서 보이는 방식 | Diagrams 탭의 재생 한 줄 |
| [`docs/agent_todo.md`](/docs/agent_todo.md) | Phase 7, 진행 순서 | 070-07 줄 |

## 9. Technical Constraints
- Compiler: MSVC (VS 2026) / Clang 20 with libstdc++ 14 (Linux)
- CMake: 4.0+ (C++20 modules always on)
- C++ Standard: C++23 (C++20 minimum)

## 10. Context & References
- [020-05 스펙](/docs/specs/020_05_tracer_event_stream.md)(이벤트 형식, Out of Scope의 070-07), [020-04 스펙](/docs/specs/020_04_diagram_readability.md)(분할 예산)
- [`detail/diagram_parts.hpp`](/include/atugcc/pattern/detail/diagram_parts.hpp), [`detail/event_stream.hpp`](/include/atugcc/pattern/detail/event_stream.hpp)(`toJsonLine`, `onDiagramParts`)
- [`web/frontend/src/diagrams.ts`](/web/frontend/src/diagrams.ts), [`events.ts`](/web/frontend/src/events.ts)
- [.agent/rules/diagrams.md](/.agent/rules/diagrams.md)

## 11. Implementation Plan
- [ ] Step 1: `DiagramRange`, `diagramPartsOf`, `Tracer::diagramParts` 오버로드, 순서 확인(§4), 테스트
- [ ] Step 2: Mermaid 강조와 테스트
- [ ] Step 3: `tools/diagram_replay/`(리더, main, CMake)와 테스트, 시나리오
- [ ] Step 4: 서버(이벤트 보관, 엔드포인트, 빌드 타깃)와 테스트
- [ ] Step 5: 페이지(막대, 캐시, 연동, i18n)와 테스트
- [ ] Step 6: §8 문서

## 12. Verification Plan
- [ ] `py -3 .agent/scripts/build.py --preset windows-x64-debug --test`, `--preset linux-x64-debug --test`
- [ ] `--label scenario`
- [ ] AC-1 레슨별 비교
- [ ] `npm --prefix web/frontend test`, `ctest -R PlaygroundServer`, 헤드리스 브라우저
- [ ] `lint_docs.py` exit 0
- [ ] 모든 AC 행의 증거가 `testrecord.md`에

## History / Amendments
- 2026-11-10: 초안
- 2026-11-10: 승인(사용자, 070-16·070-17·070-18·070-19와 함께)
- 2026-11-12: 구현 중 확인(Mermaid 12.2.0, 헤드리스 브라우저 렌더). Assumption 6의 Structure `linkStyle <n>`은 classDiagram에서 효과가 없다: `mermaid.parse`는 통과하지만 그 줄을 `linkStyle1stroke`라는 클래스로 읽는다. 대신 마지막 관계의 child에 `style <child> fill:#fff3b0,stroke:#e0a800,color:#000`을 쓴다(State의 도착 상태와 같은 생각). 따옴표가 필요한 이름(`[A-Za-z0-9_]` 밖)은 State의 `class`와 Structure의 `style` 모두 파싱 오류가 나서 강조 없이 그린다(다이어그램은 유효). 노랑은 Sequence `rect rgba(255, 235, 59, 0.35)`, State·Structure `fill:#fff3b0`
