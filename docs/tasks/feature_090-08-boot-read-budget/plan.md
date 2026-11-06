# Plan 090-08: 부트와 편집 때의 읽기 줄이기

- Spec: [/docs/specs/090_08_boot_read_budget.md](/docs/specs/090_08_boot_read_budget.md) (approved 2026-11-06)
- Branch: `feature/090-08-boot-read-budget`

## Files
- [NEW] `.agent/scripts/archive_docs.py`: KI·todo 파일 모델, 상태에 따른 이동, CLI
- [MODIFY] `.agent/scripts/lint_docs.py`: archive·deferred 파일 함께 읽기, 위치 WARN, DEFERRED 조건 ERROR, `--boot`·`--ki`·`--deferred`, 한도 줄
- [MODIFY] `.agent/scripts/agent_common.py`: `TaskLine.path` (archive에서 온 줄의 파일)
- [MODIFY] `.agent/scripts/test_agent_scripts.py`: `ArchiveDocsTest`, `LintDocsTest` 추가 테스트
- [NEW] `docs/archive/known_issues_closed.md`, `docs/archive/agent_todo_done.md`, `docs/known_issues_deferred.md` (스크립트가 만듦)
- [MODIFY] `docs/known_issues.md`, `docs/agent_todo.md` (스크립트 이동 + 첫 정리의 Status 칸, 머리말)
- [MODIFY] `docs/agent_start_prompt.md`, `.agent/rules/delegation.md`, `.agent/rules/test.md`, `.agent/workflows/start-develop-one-task.md`

C++ 변경 없음, cpp_evolution 페이지 없음.

## Design (units carry this, no judgment left)

### `archive_docs.py`
- 상수: `TODO`, `TODO_DONE = docs/archive/agent_todo_done.md`, `KNOWN_ISSUES`, `KI_DEFERRED = docs/known_issues_deferred.md`, `KI_CLOSED = docs/archive/known_issues_closed.md`, `KI_FILES = (KNOWN_ISSUES, KI_DEFERRED, KI_CLOSED)`, `KI_HOME = {OPEN, PLANNED → KNOWN_ISSUES; DEFERRED → KI_DEFERRED; CLOSED → KI_CLOSED}`.
- `KiDoc(preamble, rows: dict[id, line], statuses: dict[id, status], sections: dict[id, text])`. preamble = 처음부터 `| ID | Status |` 머리 다음의 `|---|` 줄까지. rows = 그 뒤 연속된 `| KI-NNN | STATUS |` 줄. sections = `## KI-NNN` 줄부터 다음 `## KI-` 앞까지(끝의 빈 줄 제거). 행 뒤·첫 섹션 앞에 빈 줄이 아닌 줄이 있으면 `ValueError`(글을 잃지 않게).
- `render_ki(doc)`: preamble + id 순 rows + 빈 줄 + id 순 sections를 빈 줄 하나로 이어 붙임, 끝에 줄바꿈 하나. 섹션이 없으면 rows 뒤에서 끝.
- 없는 파일은 파일별 머리말 상수로 시작(표 머리 포함).
- todo: `---` 줄까지가 preamble. 그 뒤 `## ` 제목, task 줄, 빈 줄. 들여쓰지 않은 DONE task와 그 아래 patch 줄이 **모두 DONE**이면 한 덩어리로 옮긴다. archive의 그룹 제목 = 제목에서 ` (k/n DONE)`를 뺀 것. archive 그룹 순서는 todo의 제목 순서, todo에 없는 그룹은 뒤에 원래 순서대로. 그룹 안은 원래 task id 순.
- `plan_moves(root) -> list[(id, src, dst)]`, `apply(root)`: 모든 파일 내용을 먼저 계산하고, 바뀐 파일만 쓴다(UTF-8, LF). 옮길 것이 없으면 아무것도 쓰지 않는다.
- CLI: `[--dry-run] [--root]`. `moved <id> -> <dst>` 줄, 없으면 `nothing to move`. 파싱 오류는 stderr와 exit 1, 아무것도 쓰지 않음.
- lint가 쓰는 함수: `read_ki_docs(root) -> dict[Path, KiDoc]`(있는 파일만), `movable_task_ids(todo_text) -> list[str]`, `archive_heading(heading) -> str`.

### `lint_docs.py`
- `parse_todo`: `TODO_DONE`가 있으면 함께 읽는다. archive의 task는 DONE만(아니면 ERROR), `TaskLine.path = TODO_DONE`. 그룹 수 = todo 줄 + 같은 archive 제목의 줄. todo에 제목이 없는 archive 그룹은 ERROR. 같은 id가 두 파일에 있으면 기존 "used N times" ERROR. todo에 옮길 수 있는 DONE이 있으면 WARN `<id> is DONE: run py -3 .agent/scripts/archive_docs.py`.
- `check_specs`의 todo 쪽 보고는 `task.path`의 파일에.
- `check_known_issues`: 세 파일 각각 표·섹션 짝 검사, 알 수 없는 상태 ERROR, 상태와 파일이 맞지 않으면 WARN(`... run py -3 .agent/scripts/archive_docs.py`), 같은 id가 두 파일에 ERROR, DEFERRED의 Owner 칸이 비었거나 `—`뿐이면 ERROR, KI 참조는 세 파일의 합으로 확인.
- `BUDGET = {"open_ki": 20, "deferred_ki": 30, "header_bytes": 5120, "boot_bytes": 16384}`. `budget_items(root) -> list[str]`: 열린 KI(OPEN+PLANNED, 세 파일), DEFERRED 수, todo 머리말 바이트, 머리말의 `~~…~~ (DONE`, `--boot` 본문 바이트.
- `boot_text(root)`: (한도를 넘으면) `BUDGET: <item>; <item>: triage before the next task` → todo 머리말(`---` 앞) → 빈 줄 → `--status`와 같은 줄 → 빈 줄 → `known_issues.md` 표 머리 두 줄과 OPEN·PLANNED 행 → 빈 줄 → `DEFERRED: N in docs/known_issues_deferred.md (check its Area column for the area you change)`. `---`가 없으면 첫 줄 NOTE와 todo 전체.
- `--boot`, `--ki <id>...`(세 파일에서 섹션, 없는 id는 stderr와 exit 1, 찾은 것은 출력, 중복 한 번), `--deferred`(deferred 표 머리와 행, 파일이 없으면 `no deferred KIs`). 한도는 lint finding이 아니다.

## Units

| Unit | File | Change (what, where, AC) | Check | Risky | Author | Reviewer | Tokens (in / out) | Status |
|---|---|---|---|---|---|---|---|---|
| U1 | `test_agent_scripts.py` | `ArchiveDocsTest` (AC-7): 상태별 이동, DEFERRED → OPEN 되돌림, patch가 남은 task 유지, 두 번째 실행 무변경, 파싱 오류 시 무기록 | 새 테스트가 지금 실패(모듈 없음) | no | agy flash; review fixes lead (small) | cpp-reviewer: 단언 약함·빠진 사례 7건 → lead가 보강 | 119k / 41k | done |
| U2 | `archive_docs.py` | Design §archive_docs (AC-7) | U1 통과 | no | agy flash (+ `--resume` 1회); review fixes lead (small) | cpp-reviewer: 글 손실 경로 5건 → agy 수정, 재검토: dry-run과 apply 불일치 1건 → lead 수정, 거부 사례 테스트 lead 보강 | 154k / 61k + 220k / 96k | done |
| U3 | `test_agent_scripts.py` | `LintDocsTest` archive 쪽 (AC-8, AC-4a의 ERROR) | 새 테스트 12개가 지금 실패 | no | agy flash; review fixes lead (small) | cpp-reviewer: 다른 ERROR로 통과 가능 4건 → lead 수정 | 123k / 38k | done |
| U4 | `lint_docs.py`, `agent_common.py` | Design §lint_docs의 parse_todo·check_specs·check_known_issues (AC-8) | U3 통과, 기존 테스트 통과 | no | agy flash; review fixes lead (small) | cpp-reviewer: ValueError 삼킴·archive 제목 앞 task·연쇄 오류·죽은 변수 → lead 수정 + 테스트 1개 | 188k / 67k | done |
| U5 | `test_agent_scripts.py` | `LintDocsTest` boot 쪽 (AC-1~4, AC-4a의 출력) | 새 테스트 6개가 지금 실패 | no | agy flash; review fixes lead (small) | cpp-reviewer: 11건 → lead가 테스트 3개 추가, 재검토 3건 → lead 수정 | 117k / 30k | done |
| U6 | `lint_docs.py` | Design §lint_docs의 BUDGET·boot·`--ki`·`--deferred` (AC-1~4a) | U5 통과 | no | agy flash; review fixes lead (small) | cpp-reviewer: 6건 → lead 수정 + 테스트 2개, 재검토 none | 178k / 63k | done |
| U7 | docs (스크립트 결과) | `archive_docs.py` 첫 실행 (AC-9) | KI 25.5 KB, todo 11.0 KB, lint 경고 0, 글 손실 대조 0 | no | lead (scripted) | — (스크립트, 테스트 있음) | — | done |
| U8 | `docs/known_issues.md`, `docs/agent_todo.md` | 첫 정리: 사용자 결정대로 Status 칸·진행 순서 → 두 번째 실행 (AC-9a) | `--boot`에 `BUDGET:` 없음 | no | lead (scripted) | cpp-reviewer: 결정과 일치, 손실 없음; KI-002 Owner 형식 → 수정 | — | done |
| U9 | 부트 문서, delegation.md, config.md, test.md, workflow, todo Grammar, KI·deferred·archive 머리말 | §8 Documentation Updates (AC-5) | lint 경고 0 | no | lead | cpp-reviewer: archive 머리말, config.md 문장, workflow 순서·다음 ID → 수정 | — | done |
| U10 | `docs/known_issues.md` | 러너 자동 머리말 KI (KI-047, DEFERRED) | lint | no | lead | U9와 함께 | — | done |

순서는 spec §11대로 테스트 단위를 먼저 둔다(지금 코드에서 실패해야 증거가 된다).
