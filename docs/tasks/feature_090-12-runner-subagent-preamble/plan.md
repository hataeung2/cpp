# Plan 090-12: 서브 에이전트는 부트를 읽지 않는다

- Spec: [/docs/specs/090_12_runner_subagent_preamble.md](/docs/specs/090_12_runner_subagent_preamble.md) (approved 2026-11-06)
- Branch: `feature/090-12-runner-subagent-preamble`
- Lead: Claude Code

## Files
- [MODIFY] `.agent/scripts/subagent_run.py`: `SUBAGENT_PREAMBLE`, `strip_preamble`, `build_prompt`, docstring
- [MODIFY] `.agent/scripts/test_agent_scripts.py`: `test_build_prompt`, `test_build_prompt_keeps_one_preamble`, agy 한도, `test_run_codex` 입력, docstring
- [MODIFY] `CLAUDE.md`, `AGENTS.md`, `.agent/rules/boot.md`, `.claude/agents/cpp-reviewer.md`, `docs/agent_start_prompt.md`
- [MODIFY] `.agent/rules/delegation.md`, `.agent/workflows/start-develop-one-task.md`, `.agent/skills/develop-task/SKILL.md` (+ `sync_skills.py` 복사본)
- [MODIFY] `docs/known_issues_deferred.md` → `docs/archive/known_issues_closed.md` (KI-047)

C++ 변경 없음.

## Units

| Unit | File | Change (what, where, AC) | Check | Risky | Author | Reviewer | Tokens (in / out) | Status |
|---|---|---|---|---|---|---|---|---|
| U1 | `.agent/scripts/subagent_run.py` | 머리말 상수, 중복 제거, `build_prompt` 맨 앞 (AC-1, AC-2) | `test_agent_scripts.py` | no | lead (small) | agy flash: none | — | done |
| U2 | `.agent/scripts/test_agent_scripts.py` | AC-1, AC-2, 한도에 머리말 포함 | 156 tests OK | no | lead (small) | agy flash: none | — | done |
| U3 | 진입 파일 3개, `cpp-reviewer.md`, `agent_start_prompt.md` | 첫 줄 건너뛰기 문장 (AC-3) | `grep -c` | no | lead | agy flash: none | — | done |
| U4 | `delegation.md`, workflow, skill | §0 Roles·lead tool 표, fresh reviewer, 첫 줄은 러너 (AC-4) | `grep -n cpp-reviewer`, `sync_skills.py --check` | no | lead | agy flash: 2 findings → lead fix → none | — | done |
| U5 | KI-047 | CLOSED, `archive_docs.py` (AC-5) | `lint_docs.py` | no | lead | — | — | done |
| U6 | — | 머리말 없는 프롬프트로 실제 호출 (AC-6); U1–U4 리뷰를 겸함 | agy 대화 기록 첫 줄, 응답 Q4 | — | — | — | 59k / 18k, resume 77k / 21k | done |

`cpp-reviewer.md`를 이 세션에서 고쳤으므로 fresh reviewer 대신 agy `flash`([delegation.md](/.agent/rules/delegation.md) §8).
