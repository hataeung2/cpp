# Test Record: 090-05 백로그 동기화와 진행 순서 정리

- Spec: [/docs/specs/090_05_backlog_sync.md](/docs/specs/090_05_backlog_sync.md)
- Plan: [plan.md](/docs/tasks/feature_090-05-backlog-sync/plan.md)
- Date: 2026-10-29; host Windows 11, WSL Ubuntu 24.04 (GCC 13)

## Runs
| # | Command | Expected | Actual | Status |
|---|---|---|---|---|
| R1 | `main.cpp`의 `injectionSample`·`decoratorSample`·`factorySample`·`commandSample` 호출을 잠시 켬(`iteratorSample`은 원래 켜져 있음), `py -3 .agent/scripts/build.py --preset linux-x64-debug --target atugcc_sample`, 실행 | 빌드 경고 없음, exit 0 | `-Wall -Wextra -Werror`로 빌드, 다섯 샘플 출력 후 exit 0. `main.cpp`는 원본으로 복원(`git status` clean) | Pass |
| R2 | 같은 방법으로 `astate::stateChangeSample`·`observer::observerSample`도 켬 | — | 컴파일 오류: 두 namespace가 없다(020-01이 `atugcc::pattern::*`로 옮김) → KI-023에 기록 | Info |
| R3 | 레슨 폴더의 `log/` 확인 | — | `device_state_machine/log/`에 0바이트 `crash_dump_*.log` 6개, `thread_and_log/log/`에 3개(같은 밀리초) → KI-021 | Info |
| R4 | `grep -i adapter` (README, AGENTS/CLAUDE, `.agent/rules`, `.agent/workflows`, 부트 문서, `agent_todo.md`, 레슨 후보, 템플릿, 060-01 스펙, `docs/artifacts`) | GoF 패턴과 규칙 설명만 남음 | `impl.md` §5 명명 규칙, `agent_todo.md`의 원칙·022-02·변경 노트, 060-01 History만 | Pass |
| R5 | `py -3 .agent/scripts/lint_docs.py`, `py -3 .agent/scripts/naming_check.py` | exit 0 | 0 errors, 0 warnings, 19 info(기존 봉인 기록의 경로); 0 | Pass |

## Acceptance Criteria
| AC | Evidence | Status |
|---|---|---|
| AC-1 | KI-021(R3), KI-022(020-03 취소의 빈틈), KI-023(R1, R2), KI-024(CI 없음) 등록. 열린 KI 모두 표에 주인 또는 "—(조건)"이 있다 | Pass (lead review) |
| AC-2 | `agent_todo.md`에 020-03 줄 없음, 머리말 "취소된 작업", 스펙 맨 위 취소 표시와 History | Pass (lead review) |
| AC-3 | D3: 패턴 줄 노트, State legacy DONE. D4: R4. D5·D6: Phase 4 줄. D7: `lesson_candidates.md`, Phase 5 제거. D8: Phase 6 머리말, 070-09, 060-01 Objective, 블루프린트 | Pass (lead review) |
| AC-4 | 머리말 "진행 순서"(A 1–4, B 레슨 줄·엔진 줄, 그 밖), 각 단계가 작업 ID 또는 KI id를 가리킴 | Pass (lead review, 순서는 사용자 검토 2026-10-30) |
| AC-5 | R5 | Pass |

## Reviews
| Unit | Reviewer | Result |
|---|---|---|
| U1–U5 | lead | 문서만 변경 |
| AC-4, Assumption 3 | user (2026-10-30) | 진행 순서를 A(기반) → B(레슨·엔진 병행)로 수정, backend 이름 승인 |
