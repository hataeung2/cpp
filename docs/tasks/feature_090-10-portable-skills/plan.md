# Plan 090-10: 어느 agent에서나 쓰는 skill

- Spec: [/docs/specs/090_10_portable_skills.md](/docs/specs/090_10_portable_skills.md) (approved 2026-11-06)
- Branch: `feature/090-10-portable-skills`

## Files
- [NEW] `.agent/scripts/sync_skills.py`: 원본 검사, 복사본 생성·비교·정리, CLI
- [MODIFY] `.agent/scripts/lint_docs.py`: `check_skills` (sync_skills의 finding을 그대로 보고, `check_lessons`와 같은 방식)
- [MODIFY] `.agent/scripts/test_agent_scripts.py`: `SyncSkillsTest`, lint 연결 테스트
- [NEW] `.agent/skills/develop-task/SKILL.md`, `.agent/skills/add-known-issue/SKILL.md`, `.agent/skills/README.md`
- [NEW, 생성됨] `.claude/skills/<name>/SKILL.md`, `.agents/skills/<name>/SKILL.md`
- [MODIFY] `.gitattributes`: skill 폴더 세 곳 `text eol=lf`
- [MODIFY] `docs/agent_start_prompt.md` (Quick reference), `.agent/rules/test.md` (Docs gate)

C++ 변경 없음.

## Design

### `sync_skills.py`
- 상수: `SOURCE = Path(".agent/skills")`, `TARGETS = (Path(".claude/skills"), Path(".agents/skills"))`, `NAME_RE = ^[a-z0-9]+(-[a-z0-9]+)*$`(64자 이하), `DESCRIPTION_LIMIT = 1024`, `BODY_LIMIT = 4096`, `ALLOWED_KEYS = ("name", "description")`.
- 원본 skill = `SOURCE` 바로 아래의 폴더 하나(`README.md` 같은 파일은 skill이 아니다). 폴더 안의 모든 파일이 복사 대상이다(하위 폴더 포함).
- `MARKER = "<!-- generated from .agent/skills/{name}/SKILL.md by .agent/scripts/sync_skills.py; edit the source -->"`: 복사본 `SKILL.md`에서 frontmatter를 닫는 `---` 줄 바로 다음 줄. 다른 파일은 내용 그대로.
- `@dataclass Finding(level: str, path: str (repo 상대 posix), line: int, message: str)`.
- `validate(root) -> list[Finding]`: 원본마다
  - `SKILL.md` 없음 → ERROR.
  - frontmatter(`agent_common.read_frontmatter`) 없음 → ERROR. 허용되지 않은 키 → 키마다 ERROR. `name` 없음·`NAME_RE`에 안 맞음·64자 초과·폴더 이름과 다름 → ERROR. `description` 없음·빈 값·1024자 초과 → ERROR.
  - 본문(닫는 `---` 뒤) UTF-8 > 4096 B → WARN.
  - UTF-8이 아닌 파일 → ERROR.
- `expected(root) -> dict[Path, str]`: 대상 경로(`<target>/<name>/<file>`) → 내용(LF). 원본에 ERROR가 있는 skill은 빼지 않는다(비교는 그대로 하고, 쓰기는 `sync`가 거부한다).
- `check(root) -> list[Finding]`: `validate` + 대상 비교. 비교는 `\r\n`을 `\n`으로 바꾼 텍스트끼리.
  - 없는 복사본·내용이 다른 복사본 → ERROR `<path>: out of date with .agent/skills/<name>/<file>: run py -3 .agent/scripts/sync_skills.py`.
  - 대상 폴더 아래에서 원본에 없는 파일(원본이 없는 skill 폴더 포함) → ERROR `<path>: no source in .agent/skills (generated folder): run py -3 .agent/scripts/sync_skills.py`.
  - `SOURCE`가 없고 대상도 없으면 finding 없음.
- `sync(root) -> list[str]`: `validate`에 ERROR가 있으면 아무것도 쓰지 않고 `ValueError`(메시지에 ERROR들). 아니면 없는·다른 복사본을 쓰고(UTF-8, LF), 원본에 없는 파일을 지우고 빈 폴더를 지운다. 바뀐 경로(쓰거나 지운 것)를 돌려준다. 바뀐 것이 없으면 아무것도 쓰지 않는다.
- CLI: `[--check] [--root]`. 기본: `sync`, 바뀐 경로마다 `wrote <path>` / `removed <path>`, 없으면 `skills up to date`; `ValueError`면 stderr `sync_skills: ...`와 exit 1. `--check`: finding을 `LEVEL path:line: message`로 출력, ERROR가 있으면 exit 1.

### `lint_docs.py`
- `check_skills(root, report)`: `sync_skills.check(root)`의 finding마다 `report.add(level, root / path, line, "skills: " + message)`. `lint()`에서 `check_lessons` 다음.

### 줄바꿈
`core.autocrlf=true`이고 `.gitattributes`는 `*.py`만 LF로 고정한다. 복사본 비교는 줄바꿈을 정규화하고, `.gitattributes`에 `.agent/skills/** text eol=lf`, `.claude/skills/** text eol=lf`, `.agents/skills/** text eol=lf`를 더해 세 곳이 어느 checkout에서나 같은 바이트가 되게 한다.

## Units

| Unit | File | Change (what, where, AC) | Check | Risky | Author | Reviewer | Tokens (in / out) | Status |
|---|---|---|---|---|---|---|---|---|
| U1 | `test_agent_scripts.py` | `SyncSkillsTest` (AC-1~3), lint 연결 (AC-4) | 새 테스트가 지금 실패(`import sync_skills`) | no | agy flash; review fixes lead (small) | cpp-reviewer: 테스트 버그 2건(1024자 사례가 올바른 구현에서 실패, `''`는 빈 값이 아님), 약함 9건 → lead가 수정과 `test_review_*` 7개 | 132k / 43k | done |
| U2 | `sync_skills.py` | Design §sync_skills (AC-1~3) | U1의 SyncSkillsTest 통과 | no | agy flash; review fixes lead (small) | lead 확인: 대상 폴더가 없으면 복사본 없음을 보고하지 않음, 계약 밖 따옴표 처리 → lead 수정. cpp-reviewer: BOM, 원본 폴더 없을 때 전부 삭제, OSError, `#` 잘림 → lead 수정 | 145k / 55k | done |
| U3 | `lint_docs.py` | `check_skills` (AC-4) | U1 전부 통과 | no | lead (small) | cpp-reviewer: none | — | done |
| U4 | skill 두 개, `.agent/skills/README.md`, `.gitattributes`, 부트 문서, test.md, 생성된 복사본 | spec §2.2, §8 | `sync_skills.py --check` exit 0, lint 0/0 | no | lead | cpp-reviewer: develop-task가 검토 규칙을 잘못 옮김, add-known-issue에 archive 단계 없음, test.md 문장 → 수정 | — | done |
| U5 | — | 사용자에게 AC-5 확인 요청 (세 tool의 skill 목록) | 사용자 답 | no | user | — | — | done |
