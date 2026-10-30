---
id: 090-05
title: 백로그 동기화와 진행 순서 정리 (2026-10-29 점검)
depends_on: [090-04]
unblocks: [010-08, 090-06]
approved: 2026-10-29
---

# Spec 090-05: 백로그 동기화와 진행 순서 정리

승인: 사용자가 2026-10-29 세션에서 백로그 점검 결과에 대한 결정(아래 §1 D1–D9)을 내리고, 다른 세션에서 이어갈 수 있게 정리하라고 지시함. 문서만 바꾸는 작업이다.

## 0. Assumptions (please review)
| # | Decision | Rejected alternative | Why |
|---|---|---|---|
| 1 | 020-03은 `agent_todo.md`에서 줄을 빼고, 스펙 파일은 남겨 맨 위에 취소 표시와 History를 단다. 취소 기록은 `agent_todo.md` 머리말의 "취소된 작업"에 남긴다 | `CANCELLED` 상태 추가 / 스펙 파일 삭제 | 상태 추가는 `lint_docs.py`와 테스트를 바꾸는 코드 작업이다. 스펙을 지우면 완료된 020-06 스펙(봉인)의 링크가 깨진다 |
| 2 | 020-03이 재려던 것 중 020-06이 다루지 않은 부분(`recordMessage`·`recordTransition`·`pushNode` 반복 비용, 전용 콘솔 on/off)은 KI-022로 남긴다 | 그냥 버림 | 020-06은 span 기록 비용만 잰다(`SpanCost`, AC-6·AC-8). 사용자 판단(성능 측정은 020-06에서 했다)과 맞추되 빈틈은 기록한다 |
| 3 | 외부 의존을 감싸는 층의 이름은 **pluggable backend**(교체 가능한 백엔드)로 한다. Phase 3 네임스페이스 `atugcc::backend`, 구현 `src/backends/`, 엔진 백엔드 `src/engine/backends/`. "adapter"는 GoF Adapter 패턴(022-02)에만 쓴다 | connector / integration / provider | 사용자 지시(D4): 느슨한 결합과 유연함을 강조하는 단어. "backend"는 DB, 창·렌더러, Steam 모두에 자연스럽고, "bridge"·"facade"처럼 다른 GoF 패턴 이름과 겹치지 않는다 |
| 4 | 이름 변경은 계획 문서와 규칙(`impl.md` §5, `test.md`, 스펙 템플릿 §7, README, 060-01 스펙)에만 적용한다. 레거시 스펙 파일 이름(`07_game_engine_adapters.md`)과 완료된 스펙 본문은 바꾸지 않는다 | 파일 이름까지 변경 | spec.md §5: 레거시 스펙은 이름을 바꾸지 않는다. 코드에는 `adapter` 네임스페이스나 파일이 없다 |
| 5 | 이미 헤더가 있는 패턴(Factory, Decorator, Command, Iterator, DI, Observer)은 BACKLOG를 유지하고, 노트에 "있는 것"과 "남은 일(`atugcc::pattern` 이전, Tracer 연결, 테스트, 레슨)"을 적는다. State는 020-01에서 헤더·Tracer·테스트·레슨이 모두 끝났으므로 legacy DONE으로 둔다 | 모두 DONE / 모두 그대로 | 사용자 지시(D3): 헤더가 동작하면 동기화하면서 레슨도 추가. 2026-10-29에 다섯 헤더의 샘플을 `linux-x64-debug`(`-Wall -Wextra -Werror`)로 빌드·실행해 정상 종료를 확인했다(testrecord R1). 테스트와 레슨이 없으므로 DONE은 아니다 |
| 6 | Phase 5는 그룹을 없애고 `docs/tasks/lesson_candidates.md`(레슨 후보 목록)로 옮긴다. KI-001의 주인도 이 목록으로 바꾼다 | `lessons/` 아래에 둠 | `lessons/`의 Markdown은 플레이그라운드가 레슨 자료로 읽는다. 후보 목록은 계획 문서다 |
| 7 | 새 작업 세 개: 010-08 Logger 정비(KI-013, KI-014, KI-021), 090-06 개발 도구 정비(KI-008, KI-011, KI-012), 070-09 플레이그라운드에서 엔진 출력 보기 | KI로만 둠 | 사용자 지시(D9): 열린 항목에 순서를 정해 처리. 070-09는 D8(엔진 기능을 플레이그라운드에서 실습)에 필요한데 백로그에 없던 빈틈이다 |
| 8 | 진행 순서는 `agent_todo.md` 머리말의 "진행 순서"에 둔다 | 별도 문서 | 부트 순서 2번이 `agent_todo.md`이므로 다음 세션이 바로 읽는다 |

## 1. Objective
2026-10-29 점검에서 백로그와 코드가 어긋난 곳, 기록되지 않은 문제, 주인 없는 열린 항목이 나왔다. 사용자 결정을 반영해 백로그를 코드와 맞추고 진행 순서를 정해, 다른 세션이 이 문서와 `agent_todo.md`만 읽고 이어갈 수 있게 한다.

사용자 결정(2026-10-29):
- **D1** 기록되지 않은 문제는 모두 KI로 등록한다.
- **D2** 020-03(벤치마크)은 020-06의 성능 측정으로 목적이 채워졌으므로 취소하고 기록을 남긴다.
- **D3** 백로그와 코드가 어긋난 부분은 동기화한다. 헤더가 정상 동작하면 동기화하면서 레슨에도 추가하는 방향으로 간다.
- **D4** "adapter"는 디자인 패턴에서만 쓴다. 060-01의 "어댑터 기반"은 느슨한 결합을 강조하려던 것이므로 유연함을 강조하는 단어로 바꾼다.
- **D5** Phase 4의 shape/sound는 현재 시점의 최신 C++로 현대화한다.
- **D6** 040-02의 의도: 단위 테스트 외에 **시나리오 테스트**를 추가하고 실행하는 기능. CTest에서 가능하면 이름을 CTest 기준으로 바꾼다.
- **D7** Phase 5는 웹 플레이그라운드 레슨에 넣을 자료 목록(레슨 후보)으로 바꾼다.
- **D8** Phase 6(게임 엔진)은 플레이그라운드와 멀지 않다. 엔진 기능을 모두 구현하면서 플레이그라운드에서도 해볼 수 있게 하는 것이 최종 목표다.
- **D9** 열린 KI 항목은 우선순위를 정해 차례대로 처리한다.

## 2. Requirement Details
### 2.1 Public API Surface
none.
### 2.2 Internal Implementation
문서만 바꾼다. §8의 표가 변경 전체다.
### 2.3 Platform Specifics
none.

## 3. C++ Standard Evolution
N/A.

## 4. Edge Cases
- [x] Thread safety, lifetime, platform, templates, ODR, UB — N/A (문서 작업). 점검 중 찾은 코드 결함은 KI-021, KI-023으로 기록만 한다
- [x] 020-03을 링크하는 다른 문서 — 020-06 스펙(봉인)이 `08_002_benchmark.md`를 링크하므로 파일을 남긴다(Assumption 1)
- [x] 그룹 머리말의 `(k/n DONE)` — 줄을 빼고 더한 뒤 문서 게이트가 숫자를 검사한다
- [x] State를 DONE으로 바꿀 때 — legacy DONE은 레거시 이름의 스펙 링크가 필요하다. 구현한 020-01의 스펙(`08_pattern_visualizer.md`)을 링크한다

## 5. Acceptance Criteria
| ID | Criterion | Verified by |
|---|---|---|
| AC-1 | D1: 점검에서 찾은 기록되지 않은 문제가 KI-021–KI-024로 등록되어 있고, 열린 KI마다 주인(작업 ID) 또는 "—"와 다음 조치가 있다 | `known_issues.md` 리뷰 |
| AC-2 | D2: 020-03이 `agent_todo.md`에 없고, 취소 기록(머리말)과 스펙의 취소 표시·History가 있다 | 리뷰 |
| AC-3 | D3–D8이 `agent_todo.md`, 규칙, README, 060-01 스펙, 레슨 후보 목록에 반영되어 있다. 계획 문서와 규칙에 외부 의존 층을 뜻하는 "adapter"가 남지 않는다 | 리뷰 + `grep -i adapter` |
| AC-4 | D9: `agent_todo.md` 머리말에 진행 순서가 있고, 각 단계가 작업 ID나 KI id를 가리킨다 | 리뷰 |
| AC-5 | `lint_docs.py` exit 0, `naming_check.py` 0 | 명령 출력 |

## 6. Out of Scope
- KI-021, KI-023의 코드 수정 — 010-08, 각 패턴 작업
- `CANCELLED` 상태 추가 — 필요해지면 KI
- CI 도입 — KI-024 (사용자 결정)

## 7. Dependencies & Backends
none.

## 8. Documentation Updates
| Document | Section | Change |
|---|---|---|
| [`docs/tasks/agent_todo.md`](/docs/tasks/agent_todo.md) | 머리말, 전체 | 진행 순서, 취소된 작업; 020-03 제거; 패턴 줄 노트; State legacy DONE; Phase 3·4·6 이름과 노트; Phase 5 제거; 010-08, 070-09, 090-05, 090-06 추가 |
| [`docs/known_issues.md`](/docs/known_issues.md) | 표, KI-001, 새 항목 | KI-021–KI-024 추가, 열린 KI의 주인, KI-001 주인과 `tracer_benchmarking.md` |
| [`docs/tasks/lesson_candidates.md`](/docs/tasks/lesson_candidates.md) | 새 문서 | 레슨 후보 목록(옛 Phase 5 + KI-001 + 기존 학습 문서) |
| [`docs/specs/08_002_benchmark.md`](/docs/specs/08_002_benchmark.md) | 맨 위, History | 취소 표시 |
| [`docs/specs/07_game_engine_adapters.md`](/docs/specs/07_game_engine_adapters.md) | 제목, 본문, History | pluggable backend 용어, 플레이그라운드 목표(D8) |
| [`docs/specs/00_template.md`](/docs/specs/00_template.md) | §7 | "Dependencies & Backends" |
| [`.agent/rules/impl.md`](/.agent/rules/impl.md) | §5 | pluggable backend, "adapter"는 GoF 패턴에만 |
| [`.agent/rules/test.md`](/.agent/rules/test.md) | §2 | `tests/backend/` |
| [`README.md`](/README.md) | 구조, Phase Roadmaps | backend 디렉터리(계획), 현재 Phase 목록 |
| [`docs/artifacts/project_blueprint.md`](/docs/artifacts/project_blueprint.md) | §1, §2 | backend 원칙, 최종 목표(D8), Phase 3·4 갱신, Phase 6·7 추가 |

## 9. Technical Constraints
- 문서 게이트 통과

## 10. Context & References
- [agent_todo.md](/docs/tasks/agent_todo.md), [known_issues.md](/docs/known_issues.md), [020-06](/docs/specs/020_06_tracer_span_timing.md), [020-01](/docs/specs/08_pattern_visualizer.md)

## 11. Implementation Plan
- [x] §8 표의 문서를 차례로 수정

## 12. Verification Plan
- [x] 패턴 헤더 샘플 빌드·실행(Assumption 5)
- [x] `py -3 .agent/scripts/lint_docs.py`, `py -3 .agent/scripts/naming_check.py`

## History / Amendments
- 2026-10-29: 초안, 같은 날 승인(세션 지시 D1–D9)
