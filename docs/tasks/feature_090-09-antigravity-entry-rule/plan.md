# Plan 090-09: Antigravity 진입 rule

- Spec: [/docs/specs/090_09_antigravity_entry_rule.md](/docs/specs/090_09_antigravity_entry_rule.md) (approved 2026-11-06)
- Branch: `feature/090-09-antigravity-entry-rule`

## Files
- [NEW] `.agent/rules/boot.md`: `trigger: always_on`, 부트 문서를 가리키는 두 줄
- [MODIFY] `.agent/scripts/lint_docs.py`: `check_rule_frontmatter`, `check_rule_table`, `lint()`에 연결
- [MODIFY] `.agent/scripts/test_agent_scripts.py`: `LintDocsTest`에 rule 검사 테스트
- [MODIFY] `docs/agent_start_prompt.md` (머리 인용문), `.agent/rules/test.md` (Docs gate)

C++ 변경 없음.

## Design
- 상수: `RULES_DIR = Path(".agent/rules")`, `BOOT_PROMPT = Path("docs/agent_start_prompt.md")`, `RULE_TRIGGERS = ("always_on", "model_decision", "glob", "manual")`, `ALWAYS_ON_BODY_LIMIT = 1024`.
- `check_rule_frontmatter(root, report)`: `.agent/rules/*.md`마다 (폴더가 없으면 아무것도 하지 않음)
  - `ac.read_frontmatter`가 None → ERROR `rule has no frontmatter`.
  - `trigger`가 없거나 `RULE_TRIGGERS`에 없음 → ERROR `trigger must be one of ...`.
  - `model_decision`에 `description`이 없거나 빈 값 → ERROR. `glob`에 `globs`가 없거나 빈 값 → ERROR.
  - `always_on` rule이 둘 이상 → 두 번째부터 각 파일에 ERROR `only one always_on rule (first: <file>)`(파일 이름 순).
  - `always_on` 본문(닫는 `---` 뒤) UTF-8 바이트 > 1024 → WARN `always_on body is N bytes (limit 1024): every Antigravity conversation loads it`.
- `check_rule_table(root, report)`: rule 폴더에 `model_decision` rule이 있을 때만.
  - `BOOT_PROMPT`가 없으면 ERROR 한 번.
  - 부트 문서 본문(`ac.strip_code` 뒤)의 링크 중 대상이 `/.agent/rules/<name>.md`인 것 = 표의 rule. `model_decision` rule이 그 집합에 없으면 그 rule 파일 1행에 ERROR `not linked from the trigger table in docs/agent_start_prompt.md`.
  - 표의 링크가 없는 파일을 가리키면: 기존 broken link ERROR가 이미 잡는다(새 메시지 없음).
- 두 함수 모두 `lint()`에서 `check_known_issues` 다음에 부른다.
- 구현(U2)에서 바뀐 시그니처: `check_rule_frontmatter`는 찾은 `model_decision` rule 목록을 돌려주고, `check_rule_table(root, report, model_decision_rules=None)`은 그 목록을 받아 rule 파일을 다시 읽지 않는다(`None`이면 직접 읽는다). 동작은 위와 같다(U2 review).

## Units

| Unit | File | Change (what, where, AC) | Check | Risky | Author | Reviewer | Tokens (in / out) | Status |
|---|---|---|---|---|---|---|---|---|
| U1 | `test_agent_scripts.py` | `LintDocsTest` rule 검사 테스트 (AC-2, AC-3) | 새 테스트 5개가 지금 실패(정상·기존 broken link 사례 2개는 원래 통과) | no | agy flash; review fixes lead (small) | cpp-reviewer: 7건 → lead가 `test_rules_review_gaps` 추가; 재검토: 값 사례 단언 1건 → 수정 | 145k / 33k | done |
| U2 | `lint_docs.py` | Design (AC-2, AC-3) | U1 통과, 전체 통과 | no | agy flash | cpp-reviewer: 시그니처가 Design과 다름(동작 같음) → plan 갱신 | 191k / 57k | done |
| U3 | `.agent/rules/boot.md`, 부트 문서, test.md | spec §2.2, §8 (AC-1) | lint 0/0, 본문 172 B | no | lead | cpp-reviewer: none(부트 문서 문구가 §8보다 길다, 뜻 같음) | — | done |
| U4 | — | 사용자에게 AC-4 확인 요청 (Antigravity 새 대화) | 사용자 답 | no | user | — | | |
