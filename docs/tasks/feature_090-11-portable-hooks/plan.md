# Plan 090-11: 어느 agent에서나 같은 guard

- Spec: [/docs/specs/090_11_portable_hooks.md](/docs/specs/090_11_portable_hooks.md) (approved 2026-11-06)
- Branch: `feature/090-11-portable-hooks`

## Files
- [NEW] `.agent/scripts/guard_rules.py`: tool 형식을 모르는 판정(명령, 파일에 추가된 줄)과 거부 이유 문장
- [MODIFY] `.claude/hooks/guard.py`: Claude adapter (Claude 이벤트 → 추가된 줄 계산 → `guard_rules` → Claude 출력)
- [NEW] `.codex/hooks.json`, `.codex/hooks/guard.py`: codex adapter
- [NEW] `.githooks/pre-commit`, `.agent/scripts/git_precommit.py`, `.agent/scripts/setup_hooks.py`
- [MODIFY] `.agent/scripts/lint_docs.py`: `DOC_DIRS`에 `.codex`, `--status`·`--boot`의 hook 미설치 안내 줄
- [MODIFY] `.agent/scripts/test_agent_scripts.py`: codex adapter, git pre-commit, setup 테스트
- [MODIFY] `docs/agent_start_prompt.md`, `.agent/rules/config.md`, `.agent/rules/test.md`

C++ 변경 없음.

**Antigravity: hook 없음, 하지 않음** (spec §0의 8번, 사용자 결정 2026-11-06). Antigravity의 hook 지원을 확인하지 못했다. git pre-commit hook이 Antigravity에도 rule 1·4를 적용한다. KI는 만들지 않는다.

## codex 이벤트 형식 (U1)
공식 문서(2026-11-06, developers.openai.com/codex/hooks → learn.chatgpt.com/docs/hooks):
- 프로젝트 hook: `<repo>/.codex/hooks.json`, `{"hooks": {"PreToolUse": [{"matcher": "<regex>", "hooks": [{"type": "command", "command": "...", "timeout": <s>}]}]}}`. 명령은 세션 `cwd`에서 실행되고, 프로젝트 폴더 env var는 없다(문서는 `git rev-parse --show-toplevel` 사용을 권한다).
- stdin: `session_id`, `transcript_path`, `cwd`, `hook_event_name`, `model`, `permission_mode`, `turn_id`, `tool_name`, `tool_use_id`, `tool_input`. 셸은 `tool_name: "Bash"`, 파일 수정은 `"apply_patch"`, 둘 다 `tool_input.command`(apply_patch는 patch 본문 문자열, 형식은 문서에 없음).
- 거부: stdout `{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": "..."}}`(Claude와 같다), 또는 exit 2 + stderr.
- 실패·timeout 때 동작: 문서에 없다. 신뢰: 프로젝트 hook은 `/hooks`에서 신뢰해야 동작하고, 내용이 바뀌면 다시 신뢰해야 한다.
- 실제 이벤트 기록: 하지 않음. scratch 임시 저장소에서 `codex exec --dangerously-bypass-hook-trust`로 기록 전용 hook을 한 번 돌리려 했으나 자동 권한 검사가 신뢰 우회 플래그라 거부했다. 사용자 결정(2026-11-06): **문서 기준으로 진행**, 실제 동작은 AC-5(사용자가 `/hooks`로 신뢰한 뒤 main commit 거부 확인)에서 검증. spec §0의 3번("실제 이벤트가 기준")에서 벗어나는 점은 testrecord에 적는다.

### codex adapter 설계 (`.codex/hooks/guard.py`)
- 입력: stdin JSON. `tool_name`과 `tool_input.command`만 쓴다. `cwd`가 있으면 patch 경로의 기준 폴더로 쓰고, 없으면 저장소 루트.
- `Bash` → `guard_rules.check_command(command, "bash")`. `command`가 문자열 목록이면 `shlex.join`으로 잇는다(인자 경계를 지켜 `["bash", "-lc", "git commit"]`의 script가 한 인자로 남게; U4 review). 별칭 이름(`shell` 등)은 matcher가 들이지 않으므로 두지 않는다(U4 review).
- `apply_patch` → patch 본문(`*** Begin Patch` … `*** End Patch`; 앞의 BOM·공백·다른 줄은 건너뛰고 `*** Begin Patch` 줄부터, 머리 줄은 앞뒤 공백을 무시)을 읽는다: `*** Add File: <path>`, `*** Update File: <path>`(뒤의 `*** Move to: <path>`가 있으면 그 경로)마다 그 파일 블록의 `+`로 시작하는 줄(맨 앞 `+` 제외)이 추가된 줄. 파일마다 `guard_rules.check_added_lines`. `*** Delete File:`은 검사하지 않는다.
- 그 밖의 tool: 통과.
- 출력: 거부면 stdout `{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": <reason>}}`, exit 0. 통과면 아무것도 출력하지 않고 exit 0.
- 실패(import 실패, JSON 아님): Claude adapter와 같이 fail open(stderr에 이유, exit 0). 문서에 실패 동작이 없으므로 hook 쪽에서 정한다.
- `.codex/hooks.json`: `{"hooks": {"PreToolUse": [{"matcher": "^(Bash|apply_patch)$", "hooks": [{"type": "command", "command": "py -3 \"$(git rev-parse --show-toplevel)/.codex/hooks/guard.py\"", "timeout": 15, "statusMessage": "Checking project rules"}]}]}}`. `$(…)`는 bash와 PowerShell 둘 다 받는다. Linux 호스트의 `py` 부재는 이 task에서 풀지 않는다(KI, DEFERRED).

### git hook 설계
- `guard_rules`: U2 리뷰 뒤 lead가 rule 1을 `is_checked_file(path, root)` + `machine_path_reason(lines)`로 나누고(`check_added_lines`는 둘의 조합), rule 4의 문장을 `protected_branch_reason(branch)`로 뺐다. Claude adapter는 HEAD처럼 파일을 읽기 전에 대상 여부를 판정한다.
- `.agent/scripts/git_precommit.py`:
  - `current_branch(root) -> str`: `git symbolic-ref --short -q HEAD`(첫 commit 전 브랜치도 이름이 나온다). detached HEAD면 `""`.
  - `staged_added_lines(root) -> dict[str, list[str]]`: `git diff --cached --no-color --no-ext-diff -U0 --diff-filter=ACMR`를 읽어 `+++ b/<path>` 다음의 `+` 줄(`+++` 제외, 맨 앞 `+` 제외)을 path별로. 바이너리(`Binary files … differ`)는 줄이 없다. 경로는 `core.quotepath=off`로 받는다.
  - `check(root) -> list[str]`: 거부 이유 목록. `guard_rules.protected_branch_reason(branch)`, path마다 `guard_rules.check_added_lines(root / path, lines, root)`.
  - `main(argv) -> int`: `--root`(숨김). 이유가 있으면 stderr에 `pre-commit: <reason>` 줄마다 + 마지막 줄 `pre-commit: commit refused (a person may bypass with git commit --no-verify; agents never do)`, exit 1. 없으면 exit 0, 출력 없음. **스크립트 자체 오류**(git 실패, 예외)는 stderr에 `pre-commit: guard failed: <error>`와 exit 1(fail closed, spec §4).
- `.githooks/pre-commit`(LF, 실행 비트): `#!/bin/sh` → 저장소 루트(`git rev-parse --show-toplevel`)의 `.agent/scripts/git_precommit.py`를 `py -3`(있으면) 또는 `python3`로 `exec`.
- `.agent/scripts/setup_hooks.py`: `git config --local --get core.hooksPath`가 비면 `.githooks`로 설정하고 `installed: core.hooksPath=.githooks`; 이미 `.githooks`면 `already installed`; 다른 값이면 바꾸지 않고 그 값을 알리며 exit 1. `hooks_installed(root) -> bool | None`(git 저장소가 아니면 None).
- `lint_docs.py`: `status_lines` 끝(그래서 `--status`와 `--boot` 둘 다)에, `hooks_installed(root)`가 `False`일 때만 `git hooks: not installed (py -3 .agent/scripts/setup_hooks.py; the user decides per clone)`. `DOC_DIRS`에 `.codex`.
- `.gitattributes`: `.githooks/* text eol=lf`.

## Units

| Unit | File | Change (what, where, AC) | Check | Risky | Author | Reviewer | Tokens (in / out) | Status |
|---|---|---|---|---|---|---|---|---|
| U1 | (scratch) | codex 이벤트 기록 → fixture 사본 | — | no | lead | — | — | 하지 않음: `--dangerously-bypass-hook-trust` 실행이 자동 권한 검사에서 거부, 사용자 결정으로 문서 기준 |
| U2 | `guard_rules.py`, `.claude/hooks/guard.py` | 판정을 옮기고 guard.py는 adapter로 (AC-1) | 기존 GuardHookTest·CommandPositionTest 그대로 통과 | no | agy flash; lead rewrite of guard.py | cpp-reviewer: 파일을 판정 전에 읽음, 죽은 대체 코드, 공용 함수 바꿔치기 → lead가 guard.py 다시 씀, rule 1을 `is_checked_file`·`machine_path_reason`으로, `protected_branch_reason` 추가 | 130k / 33k | done |
| U3 | `test_agent_scripts.py` | codex adapter 테스트 (AC-2) | 8개가 지금 실패 | no | agy flash; review fixes lead (small) | cpp-reviewer: 정확한 이유 미비교, cwd·Move to·config 형식 → lead 테스트 추가 | 149k / 52k | done |
| U4 | `.codex/hooks.json`, `.codex/hooks/guard.py` | codex adapter (AC-2) | U3 통과 | no | agy flash; lead rewrite | cpp-reviewer: 목록 명령 공백 join(거부 누락), 별칭이 matcher와 모순, patch 시작 조건, 죽은 대체 코드 → lead가 다시 씀 + 테스트. 최종 검토: 문맥 줄 ` *** End Patch` 오인, `splitlines` → lead 수정 + 테스트 | 119k / 27k | done |
| U5 | `test_agent_scripts.py` | git pre-commit, setup, 안내 줄 테스트 (AC-3, AC-4) | 10개가 지금 실패 | no | agy flash; review fixes lead (small) | cpp-reviewer: case 4가 잘못된 해석(강제 add 파일 예외) → lead가 '검사함'으로 바로잡음; 약함 7건 → lead 테스트 추가 | 156k / 51k | done |
| U6 | `git_precommit.py`, `.githooks/pre-commit`, `setup_hooks.py`, `lint_docs.py` | spec §2.2 (AC-3, AC-4) | U5 통과 | no | agy flash; review fixes lead (small) | lead: 작성자가 범위 밖 `agent_common.is_ignored`에 `--no-index`를 넣음 → 되돌림. cpp-reviewer: diff 해석이 `+++` 내용 줄·접두사 설정·공백/따옴표 경로·form feed에 속음, symbolic-ref 오류 → lead가 파일별 diff로 다시 씀 + 테스트, 실제 hook을 거친 `git commit` 테스트 | 167k / 35k | done |
| U7 | 문서 | spec §8 (Antigravity hook 없음 기록 포함) | lint 0/0 | no | lead | cpp-reviewer: merge 충돌 뒤 commit, Antigravity가 덮는 규칙 범위, master, 문구 → 수정 | — | done |
| U8 | — | 사용자: `setup_hooks.py` 실행 여부, codex `/hooks` 신뢰 뒤 AC-5 | 사용자 답 | no | user | — | | |
