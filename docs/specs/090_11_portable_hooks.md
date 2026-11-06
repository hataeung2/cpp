---
id: 090-11
title: 어느 agent에서나 같은 guard — 판정은 `.agent/scripts/`, Claude·codex hook은 얇은 adapter, git pre-commit hook이 공통 바닥
depends_on: [090-10]
unblocks: []
approved: 2026-11-06
---

# Spec 090-11: 어느 agent에서나 같은 guard

사용자 요청(2026-11-06): hook을 Claude 전용이 아니라 Antigravity·codex에서도 쓰게 한다.

조사 결과(2026-11-06):
- hook은 공통 표준이 없다. Claude Code는 `.claude/settings.json`, codex는 `.codex/hooks.json`(또는 `config.toml`의 `[hooks]`)에 `PreToolUse`가 있다. codex의 입력은 stdin JSON `tool_input`이고, 거부 출력은 `permissionDecision: "deny"`로 Claude와 거의 같다(공식 문서 기준, 세부는 §12에서 실제 이벤트로 확인). 새 hook이나 바뀐 hook은 codex `/hooks`에서 사용자가 신뢰해야 동작한다.
- Antigravity의 hook 지원은 확인하지 못했다.
- 사용자 결정(2026-11-06): tool hook은 Claude·codex만 만든다. Antigravity는 hook이 없어서 하지 않았다는 사실만 이 task의 산출물(plan.md, walkthrough.md)에 적는다. 언제 생길지 모르므로 KI는 만들지 않는다.
- 지금 [guard.py](/.claude/hooks/guard.py)의 판정 중 명령 분해·패턴은 이미 [agent_common.py](/.agent/scripts/agent_common.py)에 있다(090-06). `check_command`, `written_lines`, `check_write`, `decide`는 guard.py 안에 있다.
- 세 규칙 중 main commit 금지, machine path 금지는 git이 알 수 있다. 즉석 CMake configure는 git이 알 수 없다.

## 0. Assumptions (please review)

| # | Decision | Rejected alternative | Why |
|---|---|---|---|
| 1 | **판정을 `.agent/scripts/guard_rules.py`로 옮긴다**: `check_command(command, shell)`, `check_write(path, added_lines)`, 거부 이유 문장. tool 입력 형식은 모른다 | guard.py에 둠 | tool마다 adapter가 같은 판정을 부른다 |
| 2 | **`.claude/hooks/guard.py`는 Claude adapter**로 남는다: Claude 이벤트 → 추가된 줄 계산(`written_lines`, Claude의 Write·Edit 형식에 묶여 있어 여기 둔다) → `guard_rules` → Claude 출력. 동작은 바뀌지 않는다 | — | 기존 GuardHookTest가 그대로 통과해야 한다 |
| 3 | **codex adapter `.codex/hooks/guard.py` + `.codex/hooks.json`**: 셸 tool은 `check_command`, 파일 수정(`apply_patch`)은 patch의 `+` 줄을 추가된 줄로 보고 `check_write`. 구현 전에 실제 codex 이벤트를 기록해 tool 이름과 필드를 확인한다(U1). 기록은 저장소 밖 scratch에 두고, 테스트 fixture에는 경로를 지운 사본만 넣는다 | 문서만 보고 구현 | 제3자 자료끼리 설정 키가 다르다. 실제 이벤트가 기준이다 |
| 4 | **git pre-commit hook이 공통 바닥**: `.githooks/pre-commit`(sh, `py -3` 없으면 `python3`) → `.agent/scripts/git_precommit.py`: 현재 브랜치가 `main`·`master`이면 거부, staged diff의 추가된 줄에 machine path가 있으면 거부(무시된 파일 제외, guard와 같은 예외) | tool hook만 | 어느 agent든, 사람이든 commit은 git을 거친다. Antigravity처럼 hook이 없는 tool도 막힌다 |
| 5 | **설치는 `py -3 .agent/scripts/setup_hooks.py`**가 이 clone의 로컬 설정에 `core.hooksPath=.githooks`를 쓴다. 실행 여부는 clone마다 사용자 결정이다. 설치되지 않았으면 `lint_docs.py --status`·`--boot`에 `git hooks: not installed (py -3 .agent/scripts/setup_hooks.py)` 한 줄 | lint ERROR / 자동 설치 | git 설정은 사용자의 것이다(부트 문서의 `safe.directory`와 같은 원칙) |
| 6 | **merge는 막지 않는다**: pre-commit은 `git commit`에만 돈다. lead의 main merge(워크플로 6단계)는 non-ff여도 `pre-merge-commit`이라 영향이 없다. `pre-merge-commit`은 만들지 않는다 | merge도 검사 | 워크플로가 main merge를 허용한다 |
| 7 | **사람은 `git commit --no-verify`로 우회할 수 있다**. agent는 우회하지 않는다(부트 문서 규칙으로 명시) | 우회 불가 | git hook은 원래 우회할 수 있다. 사용자 결정(KI-003처럼)으로 main에 직접 commit할 길을 남긴다 |
| 8 | **Antigravity hook은 만들지 않고 KI도 만들지 않는다**(사용자 결정 2026-11-06). plan.md와 walkthrough.md에 "Antigravity: hook 없음, 하지 않음"만 적는다 | 추측으로 설정 / KI 등록 | 지원 여부를 확인하지 못했고 언제 생길지 모른다. git hook이 두 규칙을 막는다 |

## 1. Objective
non-negotiable rule 1·2·4 중 기계가 검사할 수 있는 것을 lead가 어느 tool이든 같은 판정으로 막는다. 판정 원본은 하나다.

## 2. Requirement Details

### 2.1 Public API Surface
none. 스크립트: `guard_rules.py`(모듈), `git_precommit.py`, `setup_hooks.py`.

### 2.2 Internal Implementation
| 파일 | 내용 |
|---|---|
| `.agent/scripts/guard_rules.py` | 판정과 이유 문장(guard.py에서 옮김) |
| `.claude/hooks/guard.py` | Claude adapter (fail open 유지) |
| `.codex/hooks.json`, `.codex/hooks/guard.py` | codex adapter (fail open) |
| `.githooks/pre-commit`, `.agent/scripts/git_precommit.py` | git 바닥. 거부는 exit 1과 이유, 스크립트 자체 오류는 fail open이 아니라 **이유를 출력하고 거부**한다 |
| `.agent/scripts/setup_hooks.py` | `git config --local core.hooksPath .githooks`, 이미 다른 값이면 바꾸지 않고 알린다 |

### 2.3 Platform Specifics
Windows: Git for Windows가 hook을 자체 sh로 실행한다. `.githooks/pre-commit`은 LF로 커밋하고 실행 비트를 준다(`git update-index --chmod=+x`).

## 3. C++ Standard Evolution
N/A

## 4. Edge Cases
- [x] git hook 오류 처리: tool hook은 fail open(작업을 막지 않음, lint가 다시 검사), git hook은 fail closed. commit은 되돌리기 어렵고 `--no-verify`라는 출구가 있다. 이 차이를 테스트한다.
- [x] staged diff의 rename·삭제·바이너리: 추가된 텍스트 줄만 본다.
- [x] detached HEAD: 브랜치 검사는 통과, path 검사는 한다.
- [x] codex adapter가 모르는 tool: 통과.
- N/A Thread safety, lifetime, MSVC/Clang, templates, ODR, UB: C++ 변경 없음.

## 5. Acceptance Criteria

| ID | Criterion | Verified by |
|---|---|---|
| AC-1 | 기존 GuardHookTest·CommandPositionTest가 바뀌지 않고 통과한다(Claude 동작 동일) | `test_agent_scripts.py` |
| AC-2 | codex adapter: 기록한 이벤트 fixture로 즉석 configure, main commit, machine path가 든 patch를 거부하고, 각각의 허용 사례는 통과한다 | 새 테스트 |
| AC-3 | git pre-commit: 임시 저장소에서 main commit 거부, feature 브랜치의 machine path 추가 거부, 깨끗한 commit 허용, 무시된 파일 예외, 스크립트 오류 시 거부 | 새 테스트(임시 git 저장소) |
| AC-4 | `setup_hooks.py`가 설정을 쓰고, 다른 값이 있으면 바꾸지 않는다. 설치되지 않았을 때 `--status`·`--boot`에 안내 줄이 나온다 | 새 테스트 |
| AC-5 | codex에서 `/hooks` 신뢰 뒤 main 브랜치에서 commit을 시도하면 거부된다 | **사용자 수동 확인**, testrecord |
| AC-6 | 회귀 없음: `test_agent_scripts.py` 전부 통과, `lint_docs.py` 경고 0 | 명령 출력 |

## 6. Out of Scope
- Antigravity hook — 하지 않음(hook 없음, 사용자 결정 2026-11-06). KI 없이 walkthrough에 기록
- 즉석 CMake configure를 git 단계에서 잡는 것 — 불가능, tool hook과 rule 문서가 맡는다

## 7. Dependencies & Backends
none

## 8. Documentation Updates

| Document | Section | Change |
|---|---|---|
| [agent_start_prompt.md](/docs/agent_start_prompt.md) | hook 줄(090-08에서 줄인 것), Environment notes | 세 층(tool hook, git hook), `setup_hooks.py`, agent는 `--no-verify`를 쓰지 않는다 |
| [config.md](/.agent/rules/config.md) | hook 문단 | Claude·codex adapter, git hook, 판정 원본 `guard_rules.py` |
| [test.md](/.agent/rules/test.md) | Docs gate 문단 | `.codex/hooks/`, `.githooks/` 변경도 `test_agent_scripts.py` 대상 |
| [lint_docs.py](/.agent/scripts/lint_docs.py) | `DOC_DIRS` | `.codex` 추가(링크·machine path 검사) |

## 9. Technical Constraints
- Python 3.12+, 표준 라이브러리만. git 2.9+(`core.hooksPath`).

## 10. Context & References
- [guard.py](/.claude/hooks/guard.py), [agent_common.py](/.agent/scripts/agent_common.py), [shell_commands.py](/.agent/scripts/shell_commands.py)
- [.claude/settings.json](/.claude/settings.json)
- [090-06 스펙](/docs/specs/090_06_dev_tools_cleanup.md) (명령 위치 판정)

## 11. Implementation Plan
- [ ] U1: codex 이벤트 기록(scratch의 로그 hook, 커밋하지 않음) → fixture 사본
- [ ] U2: `guard_rules.py`로 옮김, guard.py adapter화, AC-1 통과 확인
- [ ] U3: AC-2 테스트 → codex adapter
- [ ] U4: AC-3·4 테스트 → `git_precommit.py`, `.githooks/pre-commit`, `setup_hooks.py`, lint 안내 줄
- [ ] U5: 문서(doc 단위). plan.md·walkthrough.md에 Antigravity hook 없음 기록
- [ ] U6: 사용자에게 `setup_hooks.py` 실행 여부와 AC-5 확인 요청

## 12. Verification Plan
- [ ] `py -3 .agent/scripts/test_agent_scripts.py`
- [ ] `py -3 .agent/scripts/lint_docs.py` 경고 0
- [ ] AC-5: 사용자가 codex에서 확인

## History / Amendments
- 2026-11-06: 초안
- 2026-11-06: Antigravity hook은 KI 없이 기록만(사용자 결정). 승인
