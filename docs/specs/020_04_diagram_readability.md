---
id: 020-04
title: 다이어그램 가독성 — 생성 예산 기반 분할과 반복 횟수 표기
depends_on: [090-02]
unblocks: []
approved: null
---

# Spec 020-04: 다이어그램 가독성 — 생성 예산 기반 분할과 반복 횟수 표기

## 0. Assumptions (please review)
| # | Decision | Rejected alternative | Why |
|---|---|---|---|
| 1 | 시퀀스는 **연속된** 동일 메시지만 `×N`으로 합치고, 사이에 다른 메시지가 있으면 다시 그린다 | 전체에서 동일 메시지 한 번만(현재 동작) / 전부 펼쳐 그리기 | 현재 동작은 순서와 횟수를 잃는다(KI-005). 전부 펼치면 Observer 브로드캐스트 반복으로 다이어그램이 길어진다. 연속 구간 합치기는 사실을 잃지 않으면서 길이를 줄인다 |
| 2 | 상태 다이어그램은 동일 간선(old, new, trigger)을 하나로 합치고 `×N`을 붙인다. 분할하지 않는다 | 상태 수로 분할 | 잘린 상태 기계는 존재하지 않는 종료 상태처럼 보여 오해를 만든다. 예산 초과 시 주석만 달고 뷰어가 스크롤한다 |
| 3 | 구조 트리의 중복 관계는 지금처럼 버린다(횟수 없음) | `×N` 표기 | 구조에는 시간이 없어서 같은 관계가 두 번 기록돼도 간선은 하나가 맞다 |
| 4 | 새 구조화 API `diagramParts()`가 조각 목록을 반환하고, 문자열 API는 그것을 이어 붙인다 | 문자열 API에 옵션만 추가 | 웹 플레이그라운드는 조각마다 별도 블록·제목·스크롤 컨테이너가 필요하다. 문자열을 다시 파싱하지 않게 한다 |
| 5 | 090-02(camelCase 이름 변경) 다음에 진행하고 새 함수는 camelCase로만 추가한다 | 지금 snake_case API 옆에 추가 | 같은 클래스에 명명 규칙이 세 번째로 섞이는 것을 막는다 |
| 6 | 기본 예산은 시퀀스 참여자 5명·메시지 15개, 상태 12개, 구조 노드 12개, 라벨 24자 | ai_sec 문서 한도(픽셀) 직접 적용 | 런타임 생성물은 픽셀을 미리 잴 수 없다. 참여자 5명은 ai_sec 문서 규칙(폭 1000px 한도)의 시퀀스 권장치와 같다. 값은 웹 뷰어 구현 때 실제 렌더링으로 다시 조정한다 |

## 1. Objective
Tracer가 만드는 다이어그램(PlantUML, Mermaid, D2)이 웹 화면에서 읽을 수 없을 만큼 축소되지 않도록, 생성 단계에서 조각으로 나누고 반복을 횟수로 표기한다. 동시에 현재 포매터가 반복 메시지를 버려서 순서와 횟수가 사라지는 문제(KI-005)를 고친다. 규칙: [diagrams.md](/.agent/rules/diagrams.md).

## 2. Requirement Details

### 2.1 Public API Surface
`include/atugcc/pattern/visualizer.hpp`:
```cpp
struct DiagramBudget {
    std::size_t maxParticipants = 5;
    std::size_t maxMessages     = 15;
    std::size_t maxStates       = 12;
    std::size_t maxNodes        = 12;
    std::size_t labelWrap       = 24;
};

enum class DiagramKind { Sequence, State, Structure };

struct DiagramPart {
    DiagramKind    kind;
    DiagramBackend backend;
    std::string    title;      // "Sequence (2/3)", 분할이 없으면 "Sequence"
    std::string    source;     // 백엔드 문법의 완결된 다이어그램 하나
    bool           overBudget; // 예산을 지킬 수 없는 조각(State 초과, 자식이 너무 많은 구조 노드)
};

class Tracer {
public:
    [[nodiscard]] std::vector<DiagramPart> diagramParts(
        DiagramBackend backend = DiagramBackend::PlantUML,
        const DiagramBudget& budget = {}) const;
    [[nodiscard]] std::string formatDiagram(
        DiagramBackend backend = DiagramBackend::PlantUML,
        const DiagramBudget& budget = {}) const;   // diagramParts를 이어 붙임; 조각이 2개 이상일 때만 각 조각 앞에 제목 주석을 쓴다
};
```
Designated initializer로 일부만 바꿀 수 있다: `tracer.formatDiagram(DiagramBackend::Mermaid, {.maxMessages = 30})`.

### 2.2 Internal Implementation
- `detail/diagram_split.hpp` (신규): 백엔드와 무관한 분할·합치기. 입력은 이벤트 벡터, 출력은 조각별 이벤트 범위와 `×N` 횟수.
  - 시퀀스 분할: 메시지를 시간 순서로 하나씩 넣고, 서로 다른 참여자 수가 `maxParticipants`를 넘거나 메시지 수가 `maxMessages`를 넘으면 새 조각을 시작한다. 메시지 하나는 참여자가 최대 2명이라 항상 진행된다.
  - 연속 동일 메시지 합치기는 분할 전에 한다.
  - 구조 분할: 루트의 직계 하위 트리 단위로 묶어 `maxNodes` 이하가 되게 한다. 루트가 여럿이면 각 루트가 시작점. 하위 트리 하나가 `maxNodes`를 넘으면 그 안에서 다시 직계 하위 트리로 나눈다. 자식만으로 `maxNodes`를 넘는 노드는 나눌 수 없으므로 한 조각에 두고 `overBudget`을 켠다.
  - `overBudget` 조각의 `source`에는 백엔드 주석으로 `over budget: <kind> <count> > <limit>`을 넣는다.
- 세 포매터(`mermaid_formatter.hpp`, `plantuml_formatter.hpp`, `d2_formatter.hpp`)는 조각 하나를 그리는 함수만 가진다. `seen` 집합 기반 중복 제거는 시퀀스에서 제거하고, 구조 트리에서는 유지한다.
- 라벨 줄바꿈: 단어 경계 우선, 없으면 `labelWrap`에서 자른다. Mermaid는 `<br/>`, PlantUML·D2는 `\n`.
- Mermaid 메시지의 `;`는 `#59;`로 이스케이프한다.

### 2.3 Platform Specifics
none

## 3. C++ Standard Evolution
| Approach | Standard | Description |
|----------|----------|-------------|
| Legacy | C++11/14/17 | 옵션 구조체를 생성자나 setter 체인으로 채움 |
| Modern | C++20 | Designated initializer로 필요한 필드만 지정 (`{.maxMessages = 30}`), `std::ranges::views::chunk_by`류 사고방식의 구간 분할 |
| Latest | C++23 | `std::ranges::views::chunk_by`로 연속 동일 메시지 구간 계산 (MSVC·GCC 지원 확인 후 사용, 아니면 수동 루프) |

Reference: `/docs/cpp_evolution/designated_initializers.md` (§8에 신규 작성으로 등록)

## 4. Edge Cases
- [ ] Thread safety: `diagramParts`는 기존 포매터처럼 `shared_lock` 아래에서 이벤트를 복사한 뒤 락 밖에서 분할한다
- [ ] Resource lifetime: `DiagramPart`는 값 타입(`std::string` 소유), view를 반환하지 않는다
- [ ] Platform differences: `chunk_by` 지원 차이 → 수동 루프 대안
- [ ] Template instantiation: N/A (템플릿 없음)
- [ ] ODR: 새 헤더의 함수는 모두 `inline`
- [ ] Undefined behaviour: 예산 값 0 → 1로 보정(무한 루프 방지)
- [ ] 이벤트 0개 → 빈 벡터 / 빈 문자열 (현재 동작 유지)
- [ ] 참여자 이름이 24자를 넘음 → 이름은 줄바꿈하지 않고(식별자), 라벨만 줄바꿈
- [ ] 구조 노드 하나의 자식 수가 `maxNodes` 초과 → 나눌 수 없는 조각, `overBudget`

## 5. Acceptance Criteria
| ID | Criterion | Verified by |
|---|---|---|
| AC-1 | 참여자 3명, 서로 다른 메시지 40개 → 시퀀스 조각 3개(15, 15, 10), 조각 제목 `(1/3)`–`(3/3)`, 모든 메시지가 원래 순서로 정확히 한 번 나타난다 | gtest, 세 백엔드 |
| AC-2 | 참여자 8명이 섞인 메시지 → 모든 조각의 서로 다른 참여자 수 ≤ 5, 메시지 총수 보존, 조각들의 참여자 합집합 = 기록된 참여자 전체 | gtest, 세 백엔드 |
| AC-3 | `notify()`가 연속 3번 → 화살표 하나 `notify() ×3`. `A→B a`, `A→B b`, `A→B a` → 화살표 3개 | gtest, 세 백엔드 |
| AC-4 | 같은 상태 전이 2번 → 간선 하나 `trigger ×2`. 상태 13개 → 조각 1개, `overBudget == true`, `source`에 `over budget` 주석 | gtest, 세 백엔드 |
| AC-5 | 구조 관계 중복 → 간선 하나(횟수 없음). 노드 20개 → 각 조각 ≤ 12 노드, 제목 `Structure (k/n)`, 모든 관계가 정확히 한 조각에 나타남. 자식 13개인 노드 → 조각 1개, `overBudget == true` | gtest, 세 백엔드 |
| AC-6 | 30자 라벨 → 백엔드별 줄바꿈 문자로 나뉨. Mermaid 메시지의 `;` → `#59;` | gtest, 세 백엔드 |
| AC-7 | 예산 안이고 반복 없는 trace → 조각 제목은 `(k/n)` 없이 `Sequence` / `State` / `Structure`, `formatDiagram()` 출력이 변경 전 출력과 같다(기존 테스트 `PlantUMLFmtTest`, `D2FmtTest`, Mermaid 테스트 통과) | gtest, 기존 gtest |
| AC-8 | `{.maxMessages = 0}` → 1로 보정되어 종료한다 | gtest |
| AC-9 | MSVC, GCC 모두 경고 0, 전체 스위트 통과 | 빌드·ctest 기록 |
| AC-10 | 분할된 trace → `formatDiagram()`이 `diagramParts()`의 `source`를 순서대로 이어 붙이고, 각 조각 앞에 백엔드 주석으로 제목(`(k/n)` 포함)을 쓴다 | gtest, 세 백엔드 |

## 6. Out of Scope
- 웹 뷰어 구현(축소 하한, 스크롤 컨테이너) — 웹 플레이그라운드 작업에서 [diagrams.md](/.agent/rules/diagrams.md) §3을 따른다
- 렌더링 결과 픽셀 측정 — KI-006
- 터미널(ASCII) 출력의 폭 제한 — 필요 시 별도 작업

## 7. Dependencies & Adapters
none

## 8. Documentation Updates
| Document | Section | Change |
|---|---|---|
| `include/atugcc/pattern/visualizer.hpp` | 파일 머리 주석 | `diagramParts`, `DiagramBudget` 사용 예 |
| `src/pattern/example_visualizer.cpp` | 데모 | 조각 출력 예시 한 개 |
| `docs/specs/08_pattern_visualizer.md` | History / Amendments | 020-04 항목 추가 |
| `docs/cpp_evolution/designated_initializers.md` | 신규 | Legacy → C++20 비교 |
| `docs/known_issues.md` | KI-005 | CLOSED (020-04) |

## 9. Technical Constraints
- Compiler: MSVC (VS 2026) / GCC (latest stable)
- CMake: 3.26+
- C++ Standard: C++23 (C++20 minimum)

## 10. Context & References
- [Tracer](/include/atugcc/pattern/visualizer.hpp)
- [Mermaid formatter](/include/atugcc/pattern/detail/mermaid_formatter.hpp), [PlantUML formatter](/include/atugcc/pattern/detail/plantuml_formatter.hpp), [D2 formatter](/include/atugcc/pattern/detail/d2_formatter.hpp)
- [Visualizer tests](/tests/pattern/test_visualizer.cpp)
- [Diagram rules](/.agent/rules/diagrams.md)

## 11. Implementation Plan
위험 단위(delegation.md §3: 공개 헤더 API 변경, 3개 파일 동시 변경)는 agy 작성 + codex 검토.
- [ ] U1 `visualizer.hpp`: `DiagramBudget`, `DiagramKind`, `DiagramPart`, `diagramParts`/`formatDiagram` 선언 (risky)
- [ ] U2 `detail/diagram_split.hpp`: 분할·합치기·라벨 줄바꿈
- [ ] U3–U5 세 포매터: 조각 하나 그리기, 시퀀스 `seen` 제거, `×N` 라벨
- [ ] U6 `diagramParts`/`formatDiagram` 구현
- [ ] U7 테스트: AC-1–AC-8, 세 백엔드 파라미터화
- [ ] U8 예제, 문서(§8)

## 12. Verification Plan
- [ ] Build, zero warnings: `cmake --build --preset windows-x64-debug` and `cmake --build --preset linux-x64-debug`
- [ ] Full suite: `ctest --test-dir out/build/<preset> --output-on-failure` on both presets
- [ ] Every AC row has its evidence in `testrecord.md`

## History / Amendments
- 2026-10-28: 초안 (090-01 Step 4).
