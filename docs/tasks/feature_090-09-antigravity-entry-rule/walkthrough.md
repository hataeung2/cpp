# Walkthrough 090-09: Antigravity 진입 rule

- Spec: [/docs/specs/090_09_antigravity_entry_rule.md](/docs/specs/090_09_antigravity_entry_rule.md) · Plan: [plan.md](plan.md) · Tests: [testrecord.md](testrecord.md)

## 결과
- [`.agent/rules/boot.md`](/.agent/rules/boot.md): Antigravity가 매 대화 로드하는 `always_on` rule. 본문은 172 B이고 두 가지만 말한다: 부트 문서를 먼저 따를 것, task 프롬프트로 시작한 서브 에이전트는 부트를 건너뛸 것.
- 문서 게이트(`lint_docs.py`)가 `.agent/rules/*.md`를 검사한다: 유효한 `trigger`, `model_decision`의 `description`, `glob`의 `globs`, `always_on`은 하나까지(본문 1 KiB 넘으면 WARN), 모든 `model_decision` rule이 부트 문서 트리거 표에 링크되어 있을 것. 표에 없는 rule은 Claude·codex가 찾지 못하기 때문이다.
- 사용자 확인(AC-4): Antigravity 새 대화가 `lint_docs.py --boot`부터 시작하는 부트 순서로 답했다.

## Follow-ups
없음. 메모: Antigravity의 답에 workflow에 없는 `git pull`이 있었다. 원격을 쓰는 경우의 일반 습관이고 규칙과 충돌하지 않아 KI로 남기지 않는다.

## 단위와 작성자
코드·테스트는 agy `flash`, 문서는 lead, 검토는 cpp-reviewer(계열이 다름). 검토 지적은 lead가 테스트 하나를 더해 메웠다. `lead (fallback)` 단위 없음.
