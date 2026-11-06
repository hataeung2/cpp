# Walkthrough 090-10: 어느 agent에서나 쓰는 skill

- Spec: [/docs/specs/090_10_portable_skills.md](/docs/specs/090_10_portable_skills.md) · Plan: [plan.md](plan.md) · Tests: [testrecord.md](testrecord.md)

## 결과
- Skill 원본은 [`.agent/skills/`](/.agent/skills/README.md) 한 곳에 있다. Antigravity가 이 폴더를 읽는다. `py -3 .agent/scripts/sync_skills.py`가 Claude Code(`.claude/skills/`)와 codex(`.agents/skills/`)가 읽는 복사본을 만든다. 복사본에는 "생성됨, 원본을 고칠 것" 표시 줄이 들어가고, 원본이 없는 복사본은 지운다. 파일을 잃을 수 있는 상황(원본 폴더 없음, 잘못된 원본, 파일·폴더 충돌)이면 아무것도 쓰지 않고 거부한다.
- 문서 게이트가 `sync_skills.py --check`를 부른다. 복사본을 직접 고치거나 sync를 잊으면 lint가 실패한다.
- Frontmatter는 Agent Skills 표준의 공통 부분인 `name`·`description`만 허용한다. 본문은 규칙을 복사하지 않고 `.agent/rules/`·workflow·스크립트를 가리킨다.
- 처음 skill: `develop-task`(task 하나를 끝까지), `add-known-issue`(KI 등록·상태 변경).
- `core.autocrlf=true` 저장소라 `.gitattributes`로 세 skill 폴더를 LF로 고정했다. 비교는 줄바꿈 차이를 무시한다.
- 사용자 확인(AC-5): 세 tool 모두 두 skill을 이 저장소 전용 skill로 보여 줬다.

## Follow-ups
없음. rule을 skill로 바꾸는 일과 원본을 `.agents/skills/`로 옮기는 일은 spec §6대로 범위 밖이다. 원본 위치는 Claude Code가 `.agents/skills/`를 읽게 되면 다시 본다(같은 spec §6).

## 단위와 작성자
코드·테스트는 agy `flash`가 썼다. `lint_docs.py` 연결과 문서는 lead가 썼고, 검토 지적의 수정도 lead가 했다(plan.md 단위 표). 검토는 cpp-reviewer(계열이 다름). 검토에서 테스트 버그 2건이 나왔고, agy가 그 테스트에 맞추려고 계약 밖 동작을 넣은 것을 lead가 찾아 되돌렸다. `lead (fallback)` 단위는 없다.
