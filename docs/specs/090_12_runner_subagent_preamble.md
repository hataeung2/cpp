---
id: 090-12
title: 서브 에이전트는 부트를 읽지 않는다 — 러너가 첫 줄을 붙이고, 진입 파일이 건너뛰기를 말하고, 규칙이 lead를 정의함 (KI-047)
depends_on: [090-08]
unblocks: []
approved: 2026-11-06
---

# Spec 090-12: 서브 에이전트는 부트를 읽지 않는다

사용자 요청(2026-11-06): KI-047을 지금 진행한다. 서브 에이전트가 부트 시퀀스를 읽느라 토큰을 쓰지 않게 한다. 다른 git 저장소(ai_sec 사본)는 고려하지 않는다. 규칙은 lead가 누구인지 분명히 해서, lead가 codex인 경우와 다른 프로젝트로 옮길 때 고칠 곳이 한 곳이게 한다.

현재(2026-11-06):
- 090-08부터 lead가 모든 서브 에이전트 프롬프트 첫 줄에 "You are a sub-agent started with this task prompt. Do not run the repository's boot sequence; follow this prompt only."를 쓴다([delegation.md](/.agent/rules/delegation.md) §4, [develop-task skill](/.agent/skills/develop-task/SKILL.md) 4단계). lead가 빠뜨리면 서브 에이전트가 부트를 돈다.
- 진입 파일: [`.agent/rules/boot.md`](/.agent/rules/boot.md)(Antigravity)에는 건너뛰기 줄이 있다. [`CLAUDE.md`](/CLAUDE.md)와 [`AGENTS.md`](/AGENTS.md)에는 없다. 서브 에이전트(codex `exec`, Claude Code 서브 에이전트)는 이 파일을 읽고 `docs/agent_start_prompt.md`(약 5 KB)를 연 뒤에야 "서브 에이전트는 건너뜀"을 본다.
- delegation.md는 lead를 "the agent the user talks to"로만 적고, 리뷰어 표·체인이 Claude Code lead를 전제한다(`cpp-reviewer`는 Claude Code의 Agent tool로만 부를 수 있다).

## 0. Assumptions (please review)

| # | Decision | Rejected alternative | Why |
|---|---|---|---|
| 1 | **러너가 첫 줄을 붙인다**: `subagent_run.py`의 상수 `SUBAGENT_PREAMBLE`(위 문장 그대로)을 프롬프트 맨 앞에 붙인다. `Context files:` 목록보다 앞이다 | lead가 계속 씀 | 빠뜨릴 수 없다. lead가 매번 쓰는 수고도 없다 |
| 2 | **이미 첫 줄이 그 문장이면 다시 붙이지 않는다**(앞의 빈 줄, 앞뒤 공백 무시) | 항상 붙임 | 예전 습관대로 쓴 프롬프트에 같은 줄이 두 번 들어가지 않는다 |
| 3 | **`--resume`에도 붙인다** | resume에는 생략 | 한 줄(약 35 token)이고 규칙이 단순하다 |
| 4 | **러너와 테스트 docstring에서 ai_sec 동기화 문장을 지운다.** 다른 저장소용 KI는 만들지 않는다. KI-047은 CLOSED | 갈라진 점 기록 | 사용자 결정(2026-11-06): 다른 저장소는 고려하지 않는다 |
| 5 | **진입 파일 맨 앞에서 멈춘다**: `CLAUDE.md`, `AGENTS.md` 첫 줄에 "A sub-agent started with a task prompt stops here: skip the boot sequence and follow the prompt only." `boot.md`도 같은 문장으로 맞추고 순서를 바꿔 이 줄을 먼저 둔다 | 러너만 고침 | 러너를 거치지 않는 서브 에이전트(Claude Code의 `Explore`, `cpp-reviewer`)도 진입 파일에서 멈춘다. `agent_start_prompt.md`를 열지 않는다 |
| 6 | **`cpp-reviewer` 정의(`.claude/agents/cpp-reviewer.md`)에도 같은 문장** 한 줄 | 진입 파일에 맡김 | 정의가 그 서브 에이전트의 시스템 프롬프트라 매번 들어간다 |
| 7 | **delegation.md에 §0 "Roles"를 새로 둔다**: lead = 사용자가 시작한 세션의 agent(Claude Code, Codex, Antigravity 중 하나). 서브 에이전트 = lead가 task prompt로 시작한 agent. lead만 하는 일은 §7 그대로. 그리고 **lead tool별 표 하나**(§2.2)에 tool마다 다른 것만 모은다: 서브 에이전트를 부르는 방법, 첫 줄을 누가 넣는지, "fresh reviewer"가 누구인지, lead의 모델 계열 | 표 없이 본문에 tool별 예외 | 다른 프로젝트나 다른 lead에서는 이 표만 고치면 된다 |
| 8 | **본문의 `cpp-reviewer`를 역할 이름 "fresh reviewer"로 바꾼다**(§1 표, §1 목록, §6.2 3단계, §8). §8은 "fresh reviewer"의 조건(새 context, read-only, lead와 같은 계열이어도 됨, 그래서 ordinary 단위와 마지막 fallback만)과 Claude Code에서의 구현 `cpp-reviewer`를 적는다 | `cpp-reviewer` 이름 유지 | Codex가 lead면 `cpp-reviewer`를 부를 수 없다 |
| 9 | **교차 계열 규칙을 lead 계열로 적는다**: lead가 쓴 단위(doc, `lead (small)`, `lead (fallback)`)의 risky 리뷰는 lead와 다른 계열. 예: Claude Code lead → codex `luna`; Codex lead → agy `argon` | "codex가 리뷰" 고정 | Codex lead가 자기 계열에게 리뷰받는 일을 막는다 |
| 10 | **Codex lead의 fresh reviewer는 codex `luna --read-only`(러너), Antigravity lead는 agy `flash --read-only`(러너)**. 확인은 실제로 그 lead로 task를 할 때 한다 | 지금 세 tool로 직접 확인 | 이번 task의 lead는 Claude Code다. 표의 Codex·Antigravity 행은 설계값이다 |

## 1. Objective
서브 에이전트가 부트 시퀀스(부트 문서, `lint_docs.py --boot`, KI 읽기)를 돌지 않게 해서 토큰과 시간을 아낀다. lead가 첫 줄을 빠뜨려도 막히게 한다. 위임 규칙이 어떤 tool이 lead여도 읽히게 한다.

## 2. Requirement Details

### 2.1 Public API Surface
라이브러리 API 변경 없음. 러너 CLI 인자도 그대로다.

### 2.2 Internal Implementation
- `.agent/scripts/subagent_run.py`: `SUBAGENT_PREAMBLE` 상수. `build_prompt(text, files)`가 결과 맨 앞에 `SUBAGENT_PREAMBLE + "\n\n"`을 둔다. `text`의 첫 비어 있지 않은 줄이 이미 그 문장이면(strip 비교) 붙이지 않는다. agy 길이 한도 검사는 지금처럼 `build_prompt` 결과(머리말 포함)로 한다. docstring에서 ai_sec 문장을 지운다.
- `.agent/scripts/test_agent_scripts.py`: `test_build_prompt`를 새 동작으로, 중복 방지 case를 더한다. docstring에서 ai_sec 문장을 지운다.
- delegation.md §0 표(초안, 열 이름은 고정):

  | Lead tool | Lead family | Call sub-agents | First line | Fresh reviewer (§8) |
  |---|---|---|---|---|
  | Claude Code | Claude | runner (agy, codex); Agent tool (`Explore`, `cpp-reviewer`) | runner adds it; `CLAUDE.md` and the `cpp-reviewer` definition stop the others | `cpp-reviewer` |
  | Codex | GPT | runner (agy, codex) | runner adds it; `AGENTS.md` | codex `luna --read-only` |
  | Antigravity | Gemini | runner (agy, codex) | runner adds it; `.agent/rules/boot.md` | agy `flash --read-only` |

  표 위에 한 줄: "To use these rules in another project or with another lead, change this table and the aliases in `subagent_run.py`."
- §4 "Every prompt states"에서 첫 줄 항목을 지우고 "The first line comes from §0 (column First line); the lead does not write it."로 바꾼다.

### 2.3 Platform Specifics
none.

## 3. C++ Standard Evolution
N/A

## 4. Edge Cases
- [x] 프롬프트가 이미 머리말로 시작: 붙이지 않음(§0 #2). 앞에 빈 줄이 있어도 같음.
- [x] 머리말 때문에 agy 한도를 넘음: 지금처럼 `InputError`(exit 2), 한도는 머리말 포함 길이.
- [x] `--files` 있음: 순서는 머리말, 빈 줄, `Context files:` 목록, 빈 줄, 본문.
- [x] lead가 Codex인데 risky 단위를 직접 씀: 리뷰는 lead와 다른 계열(§0 #9).
- N/A Thread safety, lifetime, MSVC/Clang, templates, ODR, UB: C++ 코드 없음.

## 5. Acceptance Criteria

| ID | Criterion | Verified by |
|---|---|---|
| AC-1 | `build_prompt("X", [])`의 첫 줄이 `SUBAGENT_PREAMBLE`이고 본문 `X`가 뒤에 온다. `--files`가 있으면 머리말 → 목록 → 본문 순서 | `test_agent_scripts.py` `test_build_prompt` |
| AC-2 | 본문 첫 비어 있지 않은 줄이 이미 머리말이면 결과에 머리말이 한 번만 있다 | `test_agent_scripts.py` 새 case |
| AC-3 | `CLAUDE.md`, `AGENTS.md`, `.agent/rules/boot.md`의 첫 본문 줄과 `cpp-reviewer.md`에 §0 #5 문장이 있다 | `grep -c` 4개 파일 |
| AC-4 | delegation.md에 §0 Roles와 lead tool 표가 있고, 본문에 `cpp-reviewer`는 §0 표와 §8에만 남는다. 프롬프트 첫 줄을 lead가 쓰라는 문장이 delegation.md와 develop-task skill(원본, 두 복사본)에 없다 | `grep -n cpp-reviewer`, `grep -c "follow this prompt only"`; `sync_skills.py --check` |
| AC-5 | `subagent_run.py`, `test_agent_scripts.py`에 `ai_sec`가 없다. KI-047은 CLOSED. 문서 게이트 exit 0 | `grep -c ai_sec`; `lint_docs.py` |
| AC-6 | 러너로 실제 서브 에이전트를 한 번 불러, 머리말 없이 쓴 프롬프트에서도 부트 명령(`lint_docs.py --boot`)을 돌지 않는다 | `subagent_run.py --model flash --read-only`로 짧은 질문 하나, 결과 JSON의 명령 기록을 `testrecord.md`에 |

## 6. Out of Scope
- 다른 git 저장소(ai_sec 등) — 사용자 결정으로 고려하지 않음.
- Codex·Antigravity를 lead로 한 실제 확인 — 그 tool이 처음 lead로 task를 할 때. KI-049(Codex Windows sandbox)와 함께.

## 7. Dependencies & Backends
none.

## 8. Documentation Updates

| Document | Section | Change |
|---|---|---|
| [delegation.md](/.agent/rules/delegation.md) | 새 §0, §1, §4, §6.2, §8 | Roles와 lead tool 표; `cpp-reviewer` → fresh reviewer; 첫 줄은 §0 |
| [develop-task skill](/.agent/skills/develop-task/SKILL.md) | 4단계 | 첫 줄 문장 삭제, delegation.md §0 참조. `sync_skills.py`로 복사본 갱신 |
| [start-develop-one-task.md](/.agent/workflows/start-develop-one-task.md) | 단위 작성자·리뷰어 문장 | `cpp-reviewer`가 있으면 fresh reviewer로 |
| [CLAUDE.md](/CLAUDE.md), [AGENTS.md](/AGENTS.md), [boot.md](/.agent/rules/boot.md) | 첫 줄 | 건너뛰기 문장 |
| [cpp-reviewer](/.claude/agents/cpp-reviewer.md) | Hard limits | 건너뛰기 문장 |
| [agent_start_prompt.md](/docs/agent_start_prompt.md) | 서브 에이전트 문장 | 진입 파일이 먼저 멈춘다는 것과 맞춤 |
| [known_issues_deferred.md](/docs/known_issues_deferred.md) | KI-047 | CLOSED(archive로) |

## 9. Technical Constraints
Python 3 (Windows `py -3`, Linux `python3`). C++ 빌드와 무관.

## 10. Context & References
- [subagent_run.py](/.agent/scripts/subagent_run.py) `build_prompt`, `load_prompt`
- [test_agent_scripts.py](/.agent/scripts/test_agent_scripts.py) `SubagentRunTest`
- [090-08 spec](/docs/specs/090_08_boot_read_budget.md)

## 11. Implementation Plan
- [ ] U1 `subagent_run.py` 머리말 + docstring (lead (small))
- [ ] U2 `test_agent_scripts.py` AC-1, AC-2 (lead (small))
- [ ] U3 진입 파일 3개·`cpp-reviewer.md`·`agent_start_prompt.md` (lead)
- [ ] U4 delegation.md, workflow, develop-task skill + `sync_skills.py` (lead)
- [ ] U5 KI-047 CLOSED, `archive_docs.py` (lead)
- [ ] U1–U4 diff 리뷰: fresh reviewer `cpp-reviewer`
- [ ] U6 AC-6 실제 호출

## 12. Verification Plan
- [ ] `py -3 .agent/scripts/test_agent_scripts.py`
- [ ] `py -3 .agent/scripts/sync_skills.py --check`
- [ ] `py -3 .agent/scripts/lint_docs.py` exit 0
- [ ] AC-6 호출 결과를 `testrecord.md`에

## History / Amendments
- 2026-11-06: 초안.
- 2026-11-06: 사용자 의견 반영 — ai_sec 고려 안 함(#4), 진입 파일에서 바로 멈춤(#5), lead 정의와 lead tool 표(#7–#10).
- 2026-11-06 (구현 중, U4 리뷰): Antigravity lead의 fresh reviewer를 agy `flash --read-only`에서 agy `sonnet --read-only`로 바꿈(§0 #10). flash는 ordinary 코드 작성자와 같은 계열(Gemini)이라 교차 리뷰가 되지 않는다.
- 2026-11-06: 다시 엶 — [090-12-01](/docs/specs/090_12_01_subagent_rules.md), 서브 에이전트가 프로젝트 규칙을 받지 못함("follow this prompt only").
