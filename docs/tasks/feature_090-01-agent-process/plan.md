# Plan: 090-01 에이전트 운영 규칙 개선

- Spec: [/docs/specs/090_01_agent_process.md](/docs/specs/090_01_agent_process.md) (approved 2026-10-28)
- Branch: `feature/090-01-agent-process` (from `feature/dedicated-console` tip, KI-003)

## Files

### Step 1 — 진입점, 규칙 모순
- [NEW] `/CLAUDE.md`, `/AGENTS.md`: 진입 파일, boot 문서만 가리킴
- [NEW] `/docs/agent_start_prompt.md`: 단일 boot 문서, 규칙 trigger 표, non-negotiable 6개
- [MODIFY] `/.agent/rules/test.md`: 즉석 cmake 제거, 실제 경고 수준(`/W4`, `-Wall -Wextra`), `atugcc_tests` 좁은 실행, AC 증거표
- [MODIFY] `/.agent/workflows/start-develop-one-task.md`: 5단계 중복 제거, 상태 전이, 스펙 승인 확인
- [MODIFY] `/.agent/rules/config.md`: 절대 경로 → `%VSDEVCMD%`, `VCPKG_ROOT`, binaryDir 예시를 실제 preset과 일치
- [MODIFY] `/.agent/rules/impl.md`: camelCase 확정, legacy snake_case는 090-02

### Step 2 — 스펙·작업 관리
- [MODIFY] `/docs/specs/00_template.md`: frontmatter, Assumptions, AC, Out of Scope, Documentation Updates, History
- [MODIFY] `/.agent/rules/spec.md`: `NNN_SS` 이름, 승인 절차, 재오픈, legacy 번호
- [MODIFY] `/docs/tasks/agent_todo.md`: 새 문법, 누락 작업 010-07 보충, 020-04 / 090-01 / 090-02 추가
- [NEW] `/docs/known_issues.md`: KI-001–KI-005
- [MODIFY] `/docs/specs/08_002_benchmark.md`, `/docs/specs/07_game_engine_adapters.md`: frontmatter (`approved: null`)
- [MODIFY] `/README.md`: docs 트리, 에이전트 진입점 안내

### Step 3 — 위임·검토·테스트 순서
- [NEW] `/.agent/rules/delegation.md`: 작성자≠검증자, 위험도 기준 작성자 배정, C++ 위험 목록, 호출 규칙, 모델 체인, 단위표 형식
- [NEW] `/.agent/scripts/subagent_run.py`: ai_sec에서 그대로 복사 (출처 주석만 추가)
- [NEW] `/.agent/scripts/test_agent_scripts.py`: ai_sec `SubagentRunTest` 이식 (24 tests)
- [NEW] `/.claude/agents/cpp-reviewer.md`: Claude 읽기 전용 리뷰어
- [MODIFY] `/.agent/workflows/start-develop-one-task.md`: 단위표 → 단위별 실행·검토·확인 → Tester 단계(AC 기준) → 통합
- [MODIFY] `/docs/agent_start_prompt.md`: 규칙 표에 delegation 추가

### Step 4–5
Spec §12 참조. 각 단계 완료 시 이 목록에 추가.

## Decisions during implementation
- 상태 문법은 ai_sec의 `!STATE | ID |`를 따르되 상태를 7개로 줄임 (spec Assumption 3).
- legacy 스펙 링크(`ring_buffer.h`)는 고치지 않고 KI-002로 기록 (spec.md §5).
- `CMakePresets.json` 절대 경로는 README가 기록한 Windows 환경 변수 문제 때문에 env var가 아니라 `CMakeUserPresets.json`으로 옮기는 방향 (KI-004, Step 5).
