# Walkthrough 090-12: 서브 에이전트는 부트를 읽지 않는다

- Spec: [/docs/specs/090_12_runner_subagent_preamble.md](/docs/specs/090_12_runner_subagent_preamble.md) · Plan: [plan.md](plan.md) · Tests: [testrecord.md](testrecord.md)

## 결과
- **러너가 첫 줄을 붙인다**: [`subagent_run.py`](/.agent/scripts/subagent_run.py)가 `SUBAGENT_PREAMBLE`을 모든 프롬프트(`--resume` 포함) 맨 앞에 둔다. 프롬프트 파일이 이미 그 줄로 시작하면 한 번만. agy 한도는 머리말 포함 길이로 잰다. lead는 이제 그 줄을 쓰지 않는다.
- **진입 파일에서 멈춘다**: `CLAUDE.md`, `AGENTS.md`, `.agent/rules/boot.md`의 첫 본문 줄이 "A sub-agent started with a task prompt stops here: …"다. 러너를 거치지 않는 서브 에이전트(Claude Code의 `Explore`, `cpp-reviewer`)도 `agent_start_prompt.md`를 열지 않는다. `cpp-reviewer` 정의에도 같은 뜻의 줄.
- **lead를 정의한 규칙**: [delegation.md](/.agent/rules/delegation.md) §0 Roles(lead, 서브 에이전트, fresh reviewer, other-family reviewer)와 lead tool 표 하나(Claude Code, Codex, Antigravity). 다른 프로젝트나 다른 lead에서는 이 표와 러너의 별칭만 고친다. 본문의 `cpp-reviewer`는 역할 이름 fresh reviewer로 바뀌었다.
- 러너와 테스트에서 ai_sec 동기화 문장을 지웠다(사용자 결정: 다른 저장소는 고려하지 않는다). KI-047 CLOSED.
- 실제 호출(AC-6) 한 번: 머리말 없이 쓴 프롬프트가 agy에 머리말과 함께 도착했고, 서브 에이전트는 셸 명령을 돌리지 않았다고 답했다.

## 계획과 다르게 된 것
- Antigravity lead의 fresh reviewer: agy `flash` → agy `sonnet`(리뷰 지적, 교차 계열).
- U1–U4 리뷰는 `cpp-reviewer` 대신 agy `flash`: 이 세션에서 정의 파일을 고쳤다(§8).

## Follow-ups
- 새 KI 없음. Codex·Antigravity 행은 그 tool이 처음 lead로 task를 할 때 확인한다(delegation.md §0에 적음; Codex Windows는 KI-049와 함께).
