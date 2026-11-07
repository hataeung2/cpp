# Plan 090-12-01: 서브 에이전트가 프로젝트 규칙을 빠짐없이 받는다

## Prior Round Reference
- Original spec: [/docs/specs/090_12_runner_subagent_preamble.md](/docs/specs/090_12_runner_subagent_preamble.md)
- Original artifacts: [/docs/tasks/feature_090-12-runner-subagent-preamble/walkthrough.md](/docs/tasks/feature_090-12-runner-subagent-preamble/walkthrough.md)
- Reason for reopen: 090-08과 090-12의 "follow this prompt only" 때문에 서브 에이전트가 `impl.md`·`test.md`·레슨 작성 규칙과 리뷰 체크리스트를 받지 못한다(ai_sec 평가, 2026-11-06). 재작업이 생기면 090-12의 목표(토큰 절약)를 이루지 못한다.

- Spec: [/docs/specs/090_12_01_subagent_rules.md](/docs/specs/090_12_01_subagent_rules.md) (approved 2026-11-06)
- Branch: `feature/090-12-01-subagent-rules`
- Lead: Claude Code

## Files
- [MODIFY] `.agent/rules/impl.md`: `## Core`(1,489 B), 뒤 절에서 Core 규칙 삭제
- [MODIFY] `.agent/rules/delegation.md`: §0 표 열, §4 러너가 붙이는 것·`### Sub-agent limits`, §6.2 `--kind review`, §8 `### Review checklist`
- [MODIFY] `.agent/scripts/subagent_run.py`: `COMMON_RULES`, `RULE_SECTIONS`, `extract_section`, `rule_bundle`, `--kind`, `--print-rules`, 머리말 문장
- [MODIFY] `.agent/scripts/lint_docs.py`: `check_rule_bundles`, `--boot`의 Core
- [MODIFY] `.agent/scripts/test_agent_scripts.py`
- [MODIFY] `.claude/agents/cpp-reviewer.md`, `CLAUDE.md`, `AGENTS.md`, `.agent/rules/boot.md`, `docs/agent_start_prompt.md`, develop-task skill(+복사본)

C++ 변경 없음.

## Units

| Unit | File | Change (what, where, AC) | Check | Risky | Author | Reviewer | Tokens (in / out) | Status |
|---|---|---|---|---|---|---|---|---|
| U1 | `impl.md` | Core, 뒤 절 정리 (AC-6) | Core 1,489 B; `grep` | no | lead | agy flash: none | — | done |
| U2 | `delegation.md` | limits, checklist, §4, §6.2 (AC-6) | `grep`, lint | no | lead | agy flash: none | — | done |
| U3 | `subagent_run.py` | 묶음, `--kind`, `--print-rules` (AC-1–AC-3) | `--print-rules` 5종, tests | no | lead (small) | agy flash: none | — | done |
| U4 | `lint_docs.py` | 묶음 검사, `--boot` Core (AC-4, AC-5) | lint 0 error, tests | no | lead (small) | agy flash: none | — | done |
| U5 | `test_agent_scripts.py` | AC-1–AC-5 | 163 tests OK | no | lead | agy flash: none | — | done |
| U6 | 진입 파일, `cpp-reviewer.md`, 부트 문서, skill | §0 #5, #8, #11 | `sync_skills.py --check`, lint | no | lead | agy flash: none | — | done |
| U7 | — | AC-7 실제 호출(리뷰와 겸함) | 응답 Q4 | — | — | — | 77k / 15k | done |
| U8 | — | AC-8 `cpp-reviewer`가 `--print-rules review`를 씀 | 새 세션 | — | user | cpp-reviewer: 2 (형태) | — | done |

U3·U4는 prompt가 코드만큼 길어 `lead (small)`. `cpp-reviewer.md`를 이 세션에서 고쳤으므로 리뷰는 agy `flash`(delegation.md §8).
