# Walkthrough: 090-05 백로그 동기화와 진행 순서 정리

- Spec: [/docs/specs/090_05_backlog_sync.md](/docs/specs/090_05_backlog_sync.md) (사용자 결정 D1–D9)
- Evidence: [testrecord.md](/docs/tasks/feature_090-05-backlog-sync/testrecord.md)
- Branch: `feature/090-05-backlog-sync`

## Result
- `agent_todo.md` 머리말에 **진행 순서**와 작업 공통 원칙이 생겼다. 다음 세션은 부트 순서 2번에서 이 목록을 읽고 1번(010-08 Logger 정비)부터 고른다.
- 020-03은 취소했다. 스펙은 기록으로 남고, 020-06이 재지 않는 부분은 KI-022.
- 헤더가 이미 있는 패턴 6개에 "있음 / 남은 일" 노트를 달았다. State는 020-01에서 끝났으므로 legacy DONE으로 바꿨다.
- 외부 의존을 감싸는 층은 "pluggable backend"(`atugcc::backend`, `src/backends/`)로 부른다. "adapter"는 GoF 패턴(022-02)에만 쓴다.
- Phase 4는 최신 C++ 현대화와 CTest 시나리오 테스트, Phase 5는 [레슨 후보 목록](/docs/tasks/lesson_candidates.md)으로 바꿨다. Phase 6에는 플레이그라운드 실습 목표와 070-09를 붙였다.
- 새 작업: 010-08, 070-09, 090-06.

## Next session
1. 010-08 스펙 초안. 먼저 사용자에게 KI-014 계약(하나의 `Logger`를 여러 스레드가 공유하는가)을 묻는다.
2. 그 뒤 진행 순서를 따른다.

## Follow-ups
- KI-021, KI-022, KI-023, KI-024: 새로 등록.
- KI-001: 주인을 레슨 후보 목록으로 변경.
