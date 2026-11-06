# Walkthrough 090-11: 어느 agent에서나 같은 guard

- Spec: [/docs/specs/090_11_portable_hooks.md](/docs/specs/090_11_portable_hooks.md) · Plan: [plan.md](plan.md) · Tests: [testrecord.md](testrecord.md)

## 결과
- **판정은 한 곳**: [`guard_rules.py`](/.agent/scripts/guard_rules.py)가 rule 1(machine path), 2(즉석 configure), 4(main/master commit)의 판정과 거부 문장을 가진다.
- **세 층**:
  - Claude Code hook([`.claude/hooks/guard.py`](/.claude/hooks/guard.py)): 동작은 이전과 같다.
  - Codex hook([`.codex/hooks/guard.py`](/.codex/hooks/guard.py), `.codex/hooks.json`): `Bash`와 `apply_patch`를 받는다.
  - git pre-commit hook([`.githooks/pre-commit`](/.githooks/pre-commit) → [`git_precommit.py`](/.agent/scripts/git_precommit.py)): 어느 agent든 사람이든 모든 commit에 적용된다.
- tool hook은 fail open, git hook은 fail closed다. `--no-verify`는 사람만 쓰고 agent는 쓰지 않는다.
- **설치**: 이 clone은 사용자 결정(2026-11-06)으로 `setup_hooks.py`를 실행해 `core.hooksPath=.githooks`가 되었다. 다른 clone은 각자 정한다. 설치되지 않은 clone에서는 `--boot`·`--status`가 그렇다고 알린다.
- **Antigravity: hook 없음, 하지 않음**(사용자 결정). git 층이 rule 1·4를 덮는다. rule 2는 Claude·Codex hook과 규칙 문서만 맡는다.
- **사용자 확인(AC-5)**: `/hooks` 신뢰 뒤 Codex가 즉석 configure를 우리 rule 2 문장으로 막았다. main commit 거부는 테스트와 git hook이 증거다(testrecord의 AC-5 범위).

## 계획과 다르게 된 것
- codex 이벤트를 실제로 기록하지 않았다. 신뢰 우회 플래그 실행이 권한 검사에서 막혔고, 사용자 결정으로 공식 문서 기준으로 진행했다.
- 강제로 add한 무시 대상 파일도 검사한다. commit되는 파일이기 때문이다(testrecord "Spec과 다르게 한 것").

## Follow-ups
- [KI-048](/docs/known_issues_deferred.md) (DEFERRED): Codex hook 명령의 `py -3`가 Linux 호스트에 없을 수 있다.
- [KI-049](/docs/known_issues_deferred.md) (DEFERRED): Windows의 Codex sandbox가 `py.exe`를 실행하지 못해 Codex가 lead일 때 부트와 게이트가 돌지 않는다.

## 단위와 작성자
코드·테스트 6개 단위는 agy `flash`가 썼다. lead는 다음을 했다.
- `guard.py`와 codex adapter를 검토 뒤 다시 썼다.
- `git_precommit.py`의 diff 해석을 다시 썼다.
- 잘못된 테스트 지시(강제 add 파일 예외)를 바로잡고, 작성자가 그 테스트에 맞추려 범위 밖에 넣은 `agent_common` 변경을 되돌렸다.
- 문서를 썼다.

검토는 cpp-reviewer(계열이 다름)가 했다. `lead (fallback)` 단위는 없다.
