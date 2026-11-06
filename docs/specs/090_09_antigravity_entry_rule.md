---
id: 090-09
title: Antigravity 진입 rule — `always_on` rule 하나로 부트 문서를 가리키고, rule frontmatter를 문서 게이트가 검사
depends_on: [090-08]
unblocks: []
approved: 2026-11-06
---

# Spec 090-09: Antigravity 진입 rule

사용자 요청(2026-11-06): lead가 Claude가 아닐 때도 같은 규칙으로 시작하게 한다. 이 task는 Antigravity(agy) 쪽을 맡는다.

점검 결과(2026-11-06):
- 부트 문서는 "Antigravity (`.agent/`)"가 진입점이라고 하지만 `.agent/rules/*.md` 6개가 모두 `trigger: model_decision`이고 `always_on` rule이 없다. Antigravity가 부트 문서를 보게 하는 장치가 없다.
- 제3자 자료에 따르면 Antigravity는 v1.20.3(2026-03)부터 루트 `AGENTS.md`를 읽는다. 공식 문서로는 확인하지 못했고 버전에 따라 다르다.
- 부트 문서의 트리거 표는 rule 6개를 모두 나열한다. 표와 rule 파일이 어긋나도 지금은 아무것도 잡지 못한다.

## 0. Assumptions (please review)

| # | Decision | Rejected alternative | Why |
|---|---|---|---|
| 1 | **`.agent/rules/boot.md` 하나를 `trigger: always_on`으로** 만든다. 본문은 "부트 문서를 따른다"와 090-08의 서브 에이전트 문장 두 가지뿐이다 | `AGENTS.md`에만 기댐 / 부트 문서 내용을 rule에 복사 | `AGENTS.md` 지원은 확인되지 않았고 버전마다 다르다. 복사하면 원본이 둘이 된다. `always_on`은 매 대화 로드되므로 짧아야 한다 |
| 2 | **`AGENTS.md`는 그대로 둔다.** Antigravity가 둘 다 읽으면 같은 안내가 두 번 들어간다(합쳐 1 KB 미만) | `AGENTS.md`를 Antigravity에서 숨김 | 방법이 없고, 중복 비용이 작다 |
| 3 | **문서 게이트가 `.agent/rules/*.md` frontmatter를 검사한다**: `trigger`는 `always_on`·`model_decision`·`glob`·`manual` 중 하나, `model_decision`은 `description`이 있어야 하고 `glob`은 `globs`가 있어야 한다. `always_on` rule은 최대 하나, 본문 1 KiB 이하. 위반은 ERROR, 크기만 WARN | 검사 없음 | `always_on` rule이 늘거나 커지면 모든 agy 대화의 시작 비용이 된다. 090-08의 `--boot` 상한과 같은 생각이다 |
| 4 | **부트 문서의 트리거 표와 rule 파일을 맞춘다**: `model_decision` rule은 모두 표에 링크되어야 하고, 표의 링크는 모두 있는 rule 파일이어야 한다. 어긋나면 ERROR | — | Claude·codex는 이 표로만 rule을 찾는다. 표에 없는 rule은 그 tool들에서 읽히지 않는다 |
| 5 | **확인은 사용자가 Antigravity에서 직접 한다**(§12). 자동 검사로는 Antigravity의 rule 로드를 볼 수 없다 | — | 그래서 이 task는 자동 merge 조건을 채우지 못한다. merge 전에 사용자에게 묻는다 |

## 1. Objective
Antigravity에서 새 대화를 열면 부트 문서를 따라 시작한다. Claude·codex와 같은 순서, 같은 비용이다.

## 2. Requirement Details

### 2.1 Public API Surface
none

### 2.2 Internal Implementation
- `.agent/rules/boot.md`:
  ```markdown
  ---
  trigger: always_on
  ---
  Before anything else, follow docs/agent_start_prompt.md (atugcc boot sequence).
  A sub-agent started with a task prompt skips the boot sequence and follows its prompt only.
  ```
- `lint_docs.py`: `check_rule_frontmatter(root, report)`, `check_rule_table(root, report)`. frontmatter는 `---` 사이의 `key: value` 줄만 읽는다(YAML 라이브러리 없이, `spec` frontmatter를 읽는 방법과 같다).

### 2.3 Platform Specifics
none

## 3. C++ Standard Evolution
N/A

## 4. Edge Cases
- [x] frontmatter가 없는 rule 파일: ERROR(지금 6개는 모두 있다).
- [x] 트리거 표에 `boot.md`는 넣지 않는다(`always_on`은 검사 4번의 대상이 아니다).
- [x] `.agent/workflows/*.md`는 Antigravity에서 `trigger`가 아니라 `description`만 쓴다. 이 검사 대상이 아니다.
- N/A Thread safety, lifetime, MSVC/Clang, templates, ODR, UB: C++ 변경 없음.

## 5. Acceptance Criteria

| ID | Criterion | Verified by |
|---|---|---|
| AC-1 | `.agent/rules/boot.md`가 있고 `trigger: always_on`, 본문 1 KiB 이하 | lint 통과 + `wc -c` |
| AC-2 | 잘못된 `trigger` 값, `description` 없는 `model_decision`, `always_on` 두 개는 각각 ERROR. 1 KiB 넘는 `always_on` 본문은 WARN | `test_agent_scripts.py` LintDocsTest 새 테스트 |
| AC-3 | 표에 없는 `model_decision` rule, 표에 있지만 파일이 없는 rule은 각각 ERROR | 같은 테스트 클래스 |
| AC-4 | Antigravity 새 대화에서 "이 저장소에서 작업을 시작하는 순서"를 물으면 agent가 `docs/agent_start_prompt.md`의 부트 순서로 답한다 | **사용자 수동 확인**, 결과를 testrecord에 적음 |
| AC-5 | 회귀 없음: `test_agent_scripts.py` 전부 통과, `lint_docs.py` 경고 0 | 명령 출력 |

## 6. Out of Scope
- Antigravity skill — 090-10
- Antigravity hook — 만들지 않음(hook 없음, 090-11 §0의 8번)

## 7. Dependencies & Backends
none

## 8. Documentation Updates

| Document | Section | Change |
|---|---|---|
| [agent_start_prompt.md](/docs/agent_start_prompt.md) | 머리 인용문 | "Antigravity (`.agent/`)" → "Antigravity (`.agent/rules/boot.md`)" |
| [test.md](/.agent/rules/test.md) | Docs gate 문단 | rule frontmatter·트리거 표 검사를 더함 |

## 9. Technical Constraints
- Python 3.12+, 표준 라이브러리만.

## 10. Context & References
- [.agent/rules/](/.agent/rules/) 6개 rule의 frontmatter
- [lint_docs.py](/.agent/scripts/lint_docs.py) `check_specs`(frontmatter 읽기)

## 11. Implementation Plan
- [ ] U1: AC-2·3 테스트를 먼저 쓴다 → `check_rule_frontmatter`, `check_rule_table`
- [ ] U2: `.agent/rules/boot.md`, 부트 문서, test.md (doc 단위)
- [ ] U3: 사용자에게 AC-4 확인 요청

## 12. Verification Plan
- [ ] `py -3 .agent/scripts/test_agent_scripts.py`
- [ ] `py -3 .agent/scripts/lint_docs.py` 경고 0
- [ ] AC-4: 사용자가 Antigravity에서 확인

## History / Amendments
- 2026-11-06: 초안
- 2026-11-06: 승인
