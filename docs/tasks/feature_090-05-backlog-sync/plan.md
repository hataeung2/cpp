# Plan: 090-05 백로그 동기화와 진행 순서 정리

- Spec: [/docs/specs/090_05_backlog_sync.md](/docs/specs/090_05_backlog_sync.md)
- Branch: `feature/090-05-backlog-sync` (from `main` at `5000f3b`)

## Units
| Unit | File | Change | Check | Risky | Author |
|---|---|---|---|---|---|
| U1 | [agent_todo.md](/docs/tasks/agent_todo.md) | 진행 순서, 공통 원칙, 취소된 작업; 그룹 동기화; 새 작업 010-08, 070-09, 090-05, 090-06 | docs gate (그룹 숫자, 상태, 링크) | no | lead |
| U2 | [known_issues.md](/docs/known_issues.md) | KI-021–KI-024, 열린 KI의 주인, KI-001 갱신 | docs gate (KI id 정의) | no | lead |
| U3 | [lesson_candidates.md](/docs/tasks/lesson_candidates.md) | 새 문서: 옛 Phase 5 + KI-001 + 기존 학습 문서 | docs gate (링크) | no | lead |
| U4 | [08_002_benchmark.md](/docs/specs/08_002_benchmark.md) | 취소 표시, History | 리뷰 | no | lead |
| U5 | [07_game_engine_adapters.md](/docs/specs/07_game_engine_adapters.md), [00_template.md](/docs/specs/00_template.md), [impl.md](/.agent/rules/impl.md), [test.md](/.agent/rules/test.md), [README.md](/README.md), [project_blueprint.md](/docs/artifacts/project_blueprint.md) | adapter → pluggable backend, 로드맵과 최종 목표 | `grep -i adapter` (AC-3) | no | lead |

코드는 바꾸지 않는다. 패턴 헤더 확인을 위해 `main.cpp`의 샘플 호출을 잠시 켜고 빌드·실행한 뒤 원래대로 되돌렸다(testrecord R1).
