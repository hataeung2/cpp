---
id: 090-02
title: 함수 명명 camelCase 통일
depends_on: [090-01]
unblocks: [020-04]
approved: 2026-10-28
---

# Spec 090-02: 함수 명명 camelCase 통일

## 0. Assumptions (please review)
| # | Decision | Rejected alternative | Why |
|---|---|---|---|
| 1 | 호환용 별칭(`[[deprecated]] format_diagram()` → `formatDiagram()`) 없이 한 번에 바꾼다 | 한 릴리스 동안 deprecated 별칭 유지 | 버전 0.1.0, 외부 사용자 없음. 별칭은 같은 클래스에 두 명명을 남겨 학습용 코드의 일관성을 해친다 |
| 2 | 예외: 표준·외부 규약이 이름을 정하는 경우는 그대로 둔다 — `to_string(ErrorCode)`(std 관례 ADL 오버로드), POSIX `localtime_r`, Boost `consume_all`, `std::` 멤버 | 예외 없이 전부 변경 | 규약 이름을 바꾸면 ADL·관용 호출이 깨지고 읽는 사람이 표준 함수와 구분하지 못한다 |
| 3 | concept 요구사항도 바꾼다: `EventSink`의 `on_event` → `onEvent`, Observer의 `on_notify` → `onNotify` | concept 요구는 유지 | concept 이름도 프로젝트 공개 API다. 사용자 정의 sink가 따라야 할 규칙이 하나여야 한다 |
| 4 | 멤버 변수(`snake_case_`)·상수·네임스페이스는 범위 밖 | 같이 정리 | 이미 impl.md 규칙과 일치한다 |
| 5 | 레거시 스펙·작업 기록의 옛 이름은 고치지 않는다 | 문서 전체 치환 | 봉인 기록이다(spec.md §5). 현재 문서(README, 헤더 주석, 예제)만 갱신 |

## 1. Objective
사용자 결정(2026-10-28)에 따라 프로젝트가 정의한 모든 함수·메서드 이름을 camelCase로 통일한다. 현재 `Tracer`에는 `record_message`/`format_diagram`(snake)과 `setOutputSink`(camel)가 섞여 있다.

## 2. Requirement Details
### 2.1 Public API Surface (rename map)
| Header | Before → After |
|---|---|
| `pattern/visualizer.hpp` | `record_message` → `recordMessage`, `record_transition` → `recordTransition`, `push_node` → `pushNode`, `format_terminal` → `formatTerminal`, `format_diagram` → `formatDiagram`, `format_plantuml` → `formatPlantuml`, `format_mermaid` → `formatMermaid`, `format_d2` → `formatD2`, `snapshot_messages/_transitions/_nodes` → `snapshotMessages/Transitions/Nodes`, `get_global_tracer` → `getGlobalTracer`, concept `on_event` → `onEvent` |
| `pattern/detail/*_formatter.hpp` | `sequence_diagram` → `sequenceDiagram`, `state_diagram` → `stateDiagram`, `class_tree` → `classTree`, `message_flow` → `messageFlow`, `state_flow` → `stateFlow`, `structure_tree` → `structureTree`, `plantuml_id`/`mermaid_id`/`d2_id` → `plantumlId`/`mermaidId`/`d2Id`, `format_tree`/`format_messages`/`format_transitions` → `formatTree`/`formatMessages`/`formatTransitions`, `render_node` → `renderNode`, `section_header` → `sectionHeader`, `enable_windows_ansi` → `enableWindowsAnsi` |
| `pattern/observer.hpp` | `register_observer` → `registerObserver`, `notify_observers` → `notifyObservers`, `remove_expired` → `removeExpired`, `set_data` → `setData`, `collect_displays` → `collectDisplays`, `on_notify` → `onNotify` |
| `pattern/state.hpp` | `state_name` → `stateName`, `current_state_name` → `currentStateName`, `is_transition_allowed` → `isTransitionAllowed` |
| `core/memory_dump.hpp` | `safe_write` → `safeWrite`, `ignore_result` → `ignoreResult` |
| `src/pattern/example_visualizer.cpp` and other samples | `try_transition`, `run_cycle`, `update_io`, `emergency_stop`, `get_local_time` 등 예제 내부 함수 |

The final list is produced by the first unit (a scripted inventory) and attached to `plan.md`; the table above is from a grep on 2026-10-28.

### 2.2 Internal Implementation
- 이름 변경만. 동작·시그니처·`[[nodiscard]]` 변경 없음.
- 호출부: `src/`, `tests/`, `sample/`, `main.cpp`, 헤더 주석의 사용 예.

### 2.3 Platform Specifics
none

## 3. C++ Standard Evolution
N/A

## 4. Edge Cases
- [x] ADL: `to_string` 오버로드는 예외 (Assumption 2)
- [x] concept 요구사항 변경 → 그 concept를 만족하던 테스트 mock도 함께 변경
- [x] 매크로·문자열 안의 함수 이름(로그 메시지 등): 출력 문자열은 바꾸지 않는다, 코드 식별자만
- [x] ODR: 이름만 바뀌므로 해당 없음

## 5. Acceptance Criteria
| ID | Criterion | Verified by |
|---|---|---|
| AC-1 | `include/`, `src/`, `tests/`, `sample/`, `main.cpp`에서 프로젝트가 정의한 snake_case 함수 이름이 0개 (예외 목록 제외) | 인벤토리 스크립트 재실행 결과 0 |
| AC-2 | `windows-x64-debug`, `linux-x64-debug` 경고 0 빌드, 전체 테스트 통과 | `build.py --test` 두 preset |
| AC-3 | 테스트 수와 이름이 변경 전후 같다(테스트 본문의 호출만 바뀜) | `atugcc_tests --gtest_list_tests` 비교 |
| AC-4 | README·헤더 주석의 사용 예가 새 이름을 쓴다 | grep |

## 6. Out of Scope
- 레거시 스펙·작업 기록 (Assumption 5)
- 다이어그램 분할 기능 — 020-04

## 7. Dependencies & Adapters
none

## 8. Documentation Updates
| Document | Section | Change |
|---|---|---|
| `include/atugcc/pattern/visualizer.hpp` | 파일 머리 주석 | 새 이름 |
| `README.md` | 예제가 있는 절 | 새 이름 (있으면) |
| `docs/specs/020_04_diagram_readability.md` | §2.1 | 이미 새 이름 기준 — 변경 없음 |

## 9. Technical Constraints
- Compiler: MSVC (VS 2026) / GCC (latest stable)

## 10. Context & References
- [impl.md naming rule](/.agent/rules/impl.md)
- [visualizer.hpp](/include/atugcc/pattern/visualizer.hpp)

## 11. Implementation Plan
위험 단위(공개 헤더 API, delegation.md §3): agy 작성 + codex 1차 검토 + 리드 확인.
- [ ] U1 인벤토리 스크립트: 정의된 snake_case 함수와 예외 목록 → `plan.md`
- [ ] U2–U6 헤더별 변경 + 그 헤더의 호출부 (visualizer, formatters, observer, state, memory_dump) — 단위마다 두 preset 빌드
- [ ] U7 예제·샘플
- [ ] U8 문서(헤더 주석, README)

## 12. Verification Plan
- [ ] AC-1–AC-4 증거를 `testrecord.md`에 기록

## History / Amendments
- 2026-10-28: 초안 (사용자 결정 "함수 네이밍은 camel"). 같은 날 사용자 승인.
