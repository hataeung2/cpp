---
id: 090-10
title: 어느 agent에서나 쓰는 skill — 원본은 `.agent/skills/` 한 곳, Claude·codex 위치로 복사, 문서 게이트가 차이를 검사
depends_on: [090-09]
unblocks: []
approved: 2026-11-06
---

# Spec 090-10: 어느 agent에서나 쓰는 skill

사용자 요청(2026-11-06): skill을 만들더라도 Claude 전용이 아니라 Antigravity·codex에서도 쓰게 한다.

조사 결과(2026-11-06):
- 세 tool 모두 Agent Skills 표준([agentskills.io](https://agentskills.io)) 형식을 쓴다: 폴더 하나에 `SKILL.md`, frontmatter `name`·`description`. 시작할 때는 이름과 설명만 읽고, 고른 skill의 본문만 나중에 읽는다.
- 프로젝트 skill 위치만 다르다: Claude Code `.claude/skills/<name>/`, codex `.agents/skills/<name>/`(s가 붙는다), Antigravity `.agent/skills/<name>/`.
- Claude Code가 `.agents/skills/`를 읽는지는 확인하지 못했다(관련 issue가 열려 있다는 제3자 자료만 있다).

## 0. Assumptions (please review)

| # | Decision | Rejected alternative | Why |
|---|---|---|---|
| 1 | **원본은 `.agent/skills/<name>/`** 한 곳이다. `.claude/skills/`와 `.agents/skills/`에는 스크립트가 만든 복사본을 둔다 | 원본을 `.agents/skills/`에 | 규칙의 원본이 이미 `.agent/`에 있고 Antigravity가 그 위치를 읽는다. `.agents/`가 표준 위치로 굳으면 원본만 옮기면 된다 |
| 2 | **복사본, symlink 아님**. 복사본의 frontmatter 바로 뒤에 `<!-- generated from .agent/skills/<name>/SKILL.md by sync_skills.py; edit the source -->` 한 줄 | git symlink | Windows에서는 개발자 모드와 `core.symlinks`가 필요하고 clone마다 다르다 |
| 3 | **`.agent/scripts/sync_skills.py`**: 기본은 복사본을 다시 만들고, `--check`는 쓰지 않고 차이만 출력하고 exit 1. 문서 게이트가 `--check`를 부른다(`lessons.py check`와 같은 방식). 원본에 없는 복사본 폴더는 지운다(기본 모드), `--check`에서는 ERROR | 손으로 맞춤 | 손으로 맞추면 언젠가 어긋난다 |
| 4 | **frontmatter는 `name`·`description`만** 허용한다. `name`은 폴더 이름과 같고 소문자·숫자·`-`, 64자 이하. `description`은 1024자 이하. 다른 키는 ERROR | Claude 전용 키(`allowed-tools` 등) 허용 | 표준이 정한 공통 부분만 쓰면 어느 tool에서나 같은 뜻이다 |
| 5 | **skill 본문은 짧은 안내만** 담고 규칙은 `.agent/rules/`·`.agent/workflows/`·스크립트를 가리킨다. 본문 4 KiB 넘으면 WARN | skill에 규칙을 옮김 | 규칙 원본은 하나로 둔다 |
| 6 | **처음 skill은 두 개**: `develop-task`(task 하나를 끝까지, [start-develop-one-task.md](/.agent/workflows/start-develop-one-task.md)를 따르게 함), `add-known-issue`(다음 KI id, 표 행, 맨 아래 섹션, lint) | rule 6개도 skill로 | rule은 이미 부트 문서의 트리거 표로 필요할 때만 읽는다. skill로도 만들면 설명이 세션마다 두 번 로드된다 |
| 7 | **Antigravity의 workflow 파일은 그대로 둔다**: `develop-task`와 `/start-develop-one-task`가 둘 다 보이지만 내용 원본은 workflow 하나다 | workflow 지움 | Antigravity의 slash command 사용법이 그대로 남는다 |
| 8 | **tool별 확인은 사용자가 직접 한다**(§12) | — | 자동 merge 조건을 채우지 못한다. merge 전에 묻는다 |

## 1. Objective
같은 skill이 Claude Code, codex, Antigravity에서 같은 이름과 설명으로 보이고, 원본은 하나다.

## 2. Requirement Details

### 2.1 Public API Surface
none. 스크립트 CLI: `py -3 .agent/scripts/sync_skills.py [--check]`.

### 2.2 Internal Implementation
- `.agent/skills/develop-task/SKILL.md`, `.agent/skills/add-known-issue/SKILL.md`
- `sync_skills.py`: 원본 폴더마다 파일 전체를 두 대상으로 복사하고, `SKILL.md`에는 생성 표시 줄을 넣는다. 비교는 바이트 단위, 줄바꿈은 LF로 쓴다(`.gitattributes` 확인).
- `lint_docs.py`: `sync_skills.py --check`를 부르고 frontmatter·크기를 검사한다.

### 2.3 Platform Specifics
none

## 3. C++ Standard Evolution
N/A

## 4. Edge Cases
- [x] 복사본을 직접 고친 경우: `--check`가 ERROR, 메시지는 원본 경로를 알려 준다.
- [x] 원본에서 지운 skill: 기본 모드는 복사본을 지우고, `--check`는 남은 복사본을 ERROR로.
- [x] 원본 폴더에 `SKILL.md`가 없음: ERROR.
- N/A Thread safety, lifetime, MSVC/Clang, templates, ODR, UB: C++ 변경 없음.

## 5. Acceptance Criteria

| ID | Criterion | Verified by |
|---|---|---|
| AC-1 | `sync_skills.py`가 원본 두 개를 두 위치로 복사하고, 다시 실행해도 바뀌는 파일이 없다 | `test_agent_scripts.py` 새 테스트(임시 폴더) + `git status` |
| AC-2 | 복사본 수정, 남은 복사본, `SKILL.md` 없는 원본에서 `--check`가 exit 1과 경로를 출력한다 | 같은 테스트 |
| AC-3 | 허용되지 않은 frontmatter 키, 폴더와 다른 `name`, 1024자 넘는 `description`은 ERROR, 4 KiB 넘는 본문은 WARN | 같은 테스트 |
| AC-4 | 문서 게이트가 `--check`를 부른다(복사본을 고치면 `lint_docs.py`가 실패) | 같은 테스트 |
| AC-5 | Claude Code, codex, Antigravity에서 각각 두 skill이 목록에 보인다 | **사용자 수동 확인**, testrecord |
| AC-6 | 회귀 없음: `test_agent_scripts.py` 전부 통과, `lint_docs.py` 경고 0 | 명령 출력 |

## 6. Out of Scope
- rule을 skill로 바꾸는 것 — 필요해지면 새 task
- 원본을 `.agents/skills/`로 옮기는 것 — Claude Code가 그 위치를 읽게 되면 새 KI

## 7. Dependencies & Backends
none

## 8. Documentation Updates

| Document | Section | Change |
|---|---|---|
| [agent_start_prompt.md](/docs/agent_start_prompt.md) | Quick reference | "Skills" 행: 원본 위치, `sync_skills.py` |
| [test.md](/.agent/rules/test.md) | Docs gate 문단 | skill 동기화 검사 |
| `.agent/skills/README.md` (새 파일) | 전체 | 원본·복사본 규칙, 새 skill 만드는 법 |

## 9. Technical Constraints
- Python 3.12+, 표준 라이브러리만.

## 10. Context & References
- [start-develop-one-task.md](/.agent/workflows/start-develop-one-task.md)
- [known_issues.md](/docs/known_issues.md) 머리말(등록 규칙)
- [lessons.py](/tools/lessons.py) `check`(문서 게이트가 부르는 방식)

## 11. Implementation Plan
- [ ] U1: AC-1~4 테스트를 먼저 쓴다 → `sync_skills.py`, lint 연결
- [ ] U2: skill 두 개와 `.agent/skills/README.md` (doc 단위) → `sync_skills.py` 실행
- [ ] U3: 부트 문서, test.md
- [ ] U4: 사용자에게 AC-5 확인 요청

## 12. Verification Plan
- [ ] `py -3 .agent/scripts/test_agent_scripts.py`
- [ ] `py -3 .agent/scripts/lint_docs.py` 경고 0
- [ ] AC-5: 사용자가 세 tool에서 확인

## History / Amendments
- 2026-11-06: 초안
- 2026-11-06: 승인
