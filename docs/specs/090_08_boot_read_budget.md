---
id: 090-08
title: 부트와 편집 때의 읽기 줄이기 — `lint_docs.py --boot`·`--ki`, CLOSED KI·DONE task archive, 서브 에이전트는 부트를 건너뜀
depends_on: []
unblocks: [090-09, 090-10, 090-11]
approved: 2026-11-06
---

# Spec 090-08: 부트 단계의 읽기 줄이기

사용자 요청(2026-11-06): 시작할 때 토큰을 불필요하게 많이 쓰도록 설정되어 있는지 점검하고 줄인다. lead는 Claude가 아닐 수도 있으므로 특정 tool의 기능에 기대지 않는다.

점검 결과(2026-11-06, 이 스펙의 근거):
- tool이 자동으로 읽는 파일(`CLAUDE.md` 441 B, `AGENTS.md` 291 B)은 작다. 비용은 부트 순서가 읽으라고 시키는 파일에서 나온다.
- 부트 2단계 `docs/agent_todo.md` 22.5 KB(한글 위주, 약 7k 토큰), 3단계 `docs/known_issues.md` 52.7 KB(약 13k 토큰). 스펙을 읽기 전에 매 세션 약 2만 토큰을 쓰고, 그 90% 이상이 이 두 파일이다.
- 그중 실제로 필요한 부분은 todo의 머리말(첫 `---` 앞: Grammar, 진행 순서, 공통 원칙, 취소된 작업) 4.3 KB와 KI 표에서 CLOSED가 아닌 행 3.3 KB다. todo의 Phase 목록은 DONE 줄이 대부분이고, KI 46개 중 21개가 CLOSED다.
- `lint_docs.py --status`는 이미 291 B로 상태 요약과 다음 task를 보여 준다.
- 서브 에이전트(`subagent_run.py`의 agy·codex)는 저장소 루트를 작업 폴더로 실행된다. codex는 `AGENTS.md`를 읽으므로 부트 순서를 따라 두 파일을 읽을 수 있다. 070-15 U1의 review 한 번이 입력 119k 토큰이었다. 원인은 확인되지 않았다(§12에서 측정).
- 부트 문서의 hook 설명 문단은 [config.md](/.agent/rules/config.md) 첫 문단과 같은 내용이다.
- 두 파일은 부트 때만 읽히는 게 아니다. KI 등록, task 상태 변경 때마다 고치려고 전체를 읽는다(Claude Edit은 먼저 Read해야 하고, 다른 agent도 대개 전체를 읽는다). `known_issues.md`의 CLOSED 본문은 25.2 KB, 표 행은 2.3 KB이고, `agent_todo.md`의 DONE 줄은 12.6 KB다(2026-11-06 측정). `known_issues.md#` 앵커 링크는 저장소에 없다.
- 사용자 요청(2026-11-06, 같은 날 추가): 두 파일의 CLOSED·DONE 항목은 archive로 옮겨 읽지 않게 한다.
- 열린 KI 25개(OPEN 20, PLANNED 5) 중 19개는 Owner가 `—`이고 "~일 때 다시 본다"는 조건부 항목이다. 바이트 상한 16 KiB 하나로는 열린 KI 약 80개까지 경고가 나지 않아 정리를 재촉하지 못한다(머리말 4.5 KB, 행 평균 약 133 B).
- 사용자 결정(2026-11-06 질문 답): 열린 KI 한도 20, 한도는 **task를 고를 때** 적용(lint로 막지 않음), 조건부 KI는 **별도 파일**에 DEFERRED로 두어 중요도를 한눈에 보게 한다.

## 0. Assumptions (please review)

| # | Decision | Rejected alternative | Why |
|---|---|---|---|
| 1 | **새 옵션 `lint_docs.py --boot`**: todo 머리말 + `--status`와 같은 상태 요약 + KI 표의 CLOSED가 아닌 행을 한 번에 출력한다. `--status`는 그대로 둔다 | `--status`를 넓힘 | 출력 계약이 다르다. `--status`는 짧은 상태 확인용으로 남긴다 |
| 2 | **머리말의 끝은 첫 `---` 줄**, `parse_todo`가 task 목록의 시작으로 보는 줄과 같다 | 첫 `## Phase` 제목 / 새 표식 | 경계 규칙이 하나다. 이미 lint가 이 경계로 todo를 읽는다 |
| 3 | **`--ki KI-NNN [KI-NNN ...]`**: 각 KI의 본문(`## KI-NNN` 제목부터 다음 `## ` 앞까지)을 출력한다. 없는 id는 이유를 출력하고 exit 1 | agent가 grep·줄 범위로 직접 읽음 | tool마다 읽는 방법이 다르다. 스크립트 출력은 어느 agent에게나 같다 |
| 4 | **CLOSED KI와 DONE task는 archive로 옮긴다**: `docs/archive/known_issues_closed.md`(CLOSED 표 행과 본문, 같은 표 머리), `docs/archive/agent_todo_done.md`(DONE task 줄, todo와 같은 그룹 제목 아래). 부트(`--boot`)는 이미 둘을 빼므로 이득은 **파일을 고칠 때의 전체 읽기**다(KI 52.4 → 약 25 KB, todo 22.4 → 약 10 KB) | 옮기지 않고 `--boot`만 / 옮긴 뒤 원래 파일에 id만 남김 | 편집 때의 읽기는 task마다 여러 번이다. id만 남기면 줄은 줄어도 두 곳을 맞춰야 한다 |
| 4a | **옮기기는 스크립트가 한다**: `py -3 .agent/scripts/archive_docs.py`. 문서 게이트는 원래 파일에 CLOSED KI나 옮길 수 있는 DONE 줄이 남아 있으면 WARN을 낸다(완료 조건이 경고 0이라 task 완료 때 실행된다) | lead가 손으로 옮김 | 스크립트는 파일을 agent 컨텍스트에 읽지 않고 옮긴다. 손으로 옮기면 그 자체가 전체 읽기다 |
| 4b | **todo 그룹 제목과 `(k/n DONE)`은 todo에 남고 수는 두 파일을 합친 값이다.** 모두 DONE인 그룹은 제목만 남는다. 원래 task와 그 아래 patch 줄(`NNN-SS-PP`)은 **모두 DONE일 때 함께** 옮긴다 | 다 끝난 그룹 제목도 옮김 | 다 끝난 그룹에도 새 task가 생긴다(Phase 9처럼). ID 다음 번호를 고를 때 그룹이 한 곳에 보여야 한다 |
| 4c | **lint는 두 파일을 함께 읽는다**: KI id 존재(`KI_REF_RE`), 그룹 수, DONE task의 봉인된 기록 폴더, 스펙 승인 상태. CLOSED 항목을 다시 여는 일은 없다(새 KI가 옛 id를 가리킨다, 지금 규칙과 같다) | — | 봉인된 기록과 스펙이 가리키는 KI id·task가 archive에 있어도 검사가 같아야 한다 |
| 5 | **부트 2·3단계를 바꾼다**: "`--boot` 실행" + "task의 스펙이나 표가 이름 붙인 KI는 `--ki`로". 두 파일 전체는 고칠 때만 읽는다 | — | — |
| 6 | **항목별 한도**(사용자 결정 2026-11-06): 열린 KI(OPEN+PLANNED) **20개**, DEFERRED **30개**, todo 머리말 **5 KiB**, 진행 순서에 끝난 항목(`~~…~~ (DONE …)`) 없음. `--boot` 전체 16 KiB는 위 한도가 놓친 것(긴 행 등)을 잡는 마지막 안전장치 | `--boot` 바이트 상한 하나 | 바이트 합계로는 무엇이 늘었는지 모르고, 16 KiB는 열린 KI 약 80개까지 허용해 정리를 재촉하지 못한다. DEFERRED 30은 조건부 항목이 보이지 않는 곳에 쌓이지 않게 하는 한도다(사용자가 바꿀 수 있는 제안값) |
| 6a | **한도는 task를 고를 때 적용한다**(사용자 결정): 한도를 넘으면 `--boot` 맨 위에 `BUDGET: open KI 25/20, ...: triage before the next task`. [워크플로](/.agent/workflows/start-develop-one-task.md) 2단계: 이 줄이 있으면 lead는 다음 task 전에 정리안(KI마다 닫기·DEFERRED·합치기·task로 올리기, todo 머리말 줄이기)을 사용자에게 내고, 결정은 사용자가 한다. 문서 게이트는 한도를 검사하지 않는다 | lint WARN | 경고 0이 완료 조건이라 상관없는 task 완료 시점에 정리가 끼어든다 |
| 6b | **DEFERRED 상태와 별도 파일 `docs/known_issues_deferred.md`**(사용자 제안): "조건이 오면 다시 본다"는 항목. Owner 칸에 다시 볼 조건을 적는다(없으면 ERROR). `--boot`는 행을 보여 주지 않고 `DEFERRED: N in docs/known_issues_deferred.md (check its Area column for the area you change)` 한 줄만 낸다. `lint_docs.py --deferred`는 그 표를 출력한다. 조건이 오면 상태를 OPEN으로 바꾸고 스크립트가 원래 파일로 옮긴다 | archive에 DEFERRED로 / OPEN에 남김 | archive는 끝난 기록이라 섞으면 "다시 볼 것"이 묻힌다. 별도 파일이면 `known_issues.md`는 지금 처리할 것만 남아 중요도가 바로 보인다 |
| 6c | **"지우기"는 닫기**: 쓸모없어진 KI는 `CLOSED`와 `dropped: <reason>`으로 닫아 archive로 보낸다. 줄을 지우지 않는다 | 실제 삭제 | 봉인된 기록과 스펙이 KI id를 가리키고 lint가 그 id의 존재를 검사한다 |
| 6d | **첫 정리는 이 task 안에서**: 열린 25개를 lead가 분류안(열린 채 / DEFERRED / 닫기 / 합치기)으로 내고 사용자가 정한다. 적용은 Status 칸만 고치고 스크립트로 옮긴다. 후보 예: KI-002(정보용, 닫기), KI-034(검사 한 줄로 해결), KI-018·020·046(부하 아래 한 번 실패, 하나로 합치기), KI-031(KI-023에 합치기), Owner `—`인 조건부 항목(DEFERRED) | 다음 task에서 | 한도 20을 지금 넘는다. 이 task가 끝나면 한도 안에서 시작해야 한다 |
| 7 | **서브 에이전트는 부트를 건너뛴다**: 부트 문서 맨 위에 "task 프롬프트를 받고 시작한 서브 에이전트는 이 파일과 부트 순서를 따르지 않고 프롬프트만 따른다"를 두고, [delegation.md](/.agent/rules/delegation.md) §4 "Every prompt states"에 같은 문장을 더한다 | `subagent_run.py`가 프롬프트에 머리말을 자동으로 붙임 | `subagent_run.py`는 ai_sec 사본과 같아야 한다(파일 머리 docstring). 스크립트 변경은 공유 kit로 옮길 때 같이 한다(KI 등록) |
| 8 | **부트 문서의 hook 문단은 한 줄로 줄이고** 자세한 설명은 config.md에 둔다(이미 있다) | 그대로 둠 | 같은 설명이 두 곳에 있다. 부트 문서는 모든 세션이 읽는다 |
| 9 | **`cpp-reviewer.md`의 위험 목록은 그대로 둔다** | delegation.md §3을 가리키게 함 | 같은 목록이 아니다. §3은 "위험한 단위"를 고르는 기준이고 reviewer 목록은 검토 항목(naming, modules, 테스트 포함)이다. 서브 에이전트는 새 컨텍스트로 시작하므로 목록을 직접 가져야 한다 |

## 1. Objective
- 세션 시작 비용을 약 2만 토큰에서 3천 토큰 안팎으로 줄인다. 같은 정보를 어느 agent든 같은 명령으로 얻는다.
- todo·KI를 고칠 때 읽는 양을 약 75 KB에서 약 35 KB로 줄인다(끝난 항목은 archive).
- 서브 에이전트 호출이 부트 비용을 다시 내지 않게 한다.

## 2. Requirement Details

### 2.1 Public API Surface
none (C++ 코드 변경 없음). 스크립트 CLI: `lint_docs.py --boot`, `lint_docs.py --ki <id> [<id> ...]`.

### 2.2 Internal Implementation
- `lint_docs.py`:
  - `boot_text(root) -> str`: todo 머리말(첫 `---` 앞, 그 줄 제외), 빈 줄, `print_status`와 같은 상태 요약, 빈 줄, KI 표의 머리 두 줄(제목·구분선)과 CLOSED가 아닌 행. KI 표는 `known_issues.md`의 첫 표다.
  - `--boot`는 `boot_text`를 출력하고 exit 0. todo에 `---`가 없으면 todo 전체를 출력하고 첫 줄에 `NOTE: no '---' in docs/agent_todo.md; printed the whole file`.
  - `--ki`: 인자마다 본문 섹션을 출력한다. 하나라도 없으면 그 id를 stderr로 출력하고 exit 1(찾은 섹션은 출력한다).
  - `budget_lines(root) -> list[str]`: §0의 6번 한도를 넘은 항목마다 한 줄. `--boot`는 있으면 맨 위에 `BUDGET: ...: triage before the next task`로 출력한다. 한도 값은 `lint_docs.py` 상수 한 곳(`BUDGET = {...}`)에 둔다.
  - `--deferred`: DEFERRED 표를 출력한다.
  - `parse_todo`·`check_known_issues`·`sealed_task_dirs`는 archive와 deferred 파일도 읽는다(없으면 빈 것으로). KI 상태와 파일 위치가 맞지 않으면(CLOSED가 원래·deferred 파일에, DEFERRED가 원래 파일에, OPEN·PLANNED가 다른 파일에) WARN `... run py -3 .agent/scripts/archive_docs.py`. 옮길 수 있는 DONE 줄이 todo에 있어도 같은 WARN. DEFERRED의 Owner 칸이 비었거나 `—`뿐이면 ERROR.
- `.agent/scripts/archive_docs.py`(새 파일): **위치는 상태가 정한다.** KI 표 행과 `## KI-NNN` 본문을 상태에 따라 옮긴다: OPEN·PLANNED → `docs/known_issues.md`, DEFERRED → `docs/known_issues_deferred.md`, CLOSED → `docs/archive/known_issues_closed.md`. DONE task 줄(patch 줄은 원래 task와 함께, 모두 DONE일 때)은 `docs/archive/agent_todo_done.md`의 같은 그룹 제목 아래로. 각 파일 안에서는 id 순서를 지킨다. 옮긴 것이 없으면 파일을 쓰지 않는다. `--dry-run`은 옮길 id와 목적지만 출력한다.
- 첫 실행으로 지금의 CLOSED KI 21개와 DONE task 40개를 옮긴다. 이어서 사용자가 정한 첫 정리(§0의 6d)를 Status 칸 수정과 두 번째 실행으로 적용한다.
- `known_issues.md` 머리말의 Status 목록에 `DEFERRED`(Owner 칸 = 다시 볼 조건)를 더한다.
- [start-develop-one-task.md](/.agent/workflows/start-develop-one-task.md) 6단계: KI 등록·todo 갱신 뒤 `archive_docs.py`, 그다음 `lint_docs.py`.
- 부트 문서: Boot 2·3단계, 맨 위 서브 에이전트 문장, Quick reference의 "Task states, next task" 행, hook 문단.
- delegation.md §4: 서브 에이전트 문장.

### 2.3 Platform Specifics
none. 출력은 UTF-8(`main`이 이미 `sys.stdout.reconfigure`).

## 3. C++ Standard Evolution
N/A

## 4. Edge Cases
- [x] KI 표 행의 Status 칸이 `CLOSED`인지는 칸 단위로 판정한다(Area나 Owner 칸에 "closed by"가 있어도 영향 없음).
- [x] `--ki`에 같은 id를 두 번 주면 한 번만 출력한다.
- [x] todo에 `---`가 없거나 KI 파일이 없을 때: `--boot`는 있는 것만 출력하고 NOTE로 알린다(부트가 막히지 않게). lint는 기존 ERROR가 그대로 잡는다.
- [x] 원래 task는 DONE인데 patch 줄이 아직 DONE이 아님: 둘 다 옮기지 않는다(WARN도 없음).
- [x] 같은 id가 원래 파일과 archive에 둘 다 있음: lint ERROR(옮기다 멈춘 상태).
- [x] archive 파일이 아직 없음: 스크립트가 머리말과 함께 만든다. lint는 없는 archive를 빈 것으로 본다.
- [x] `archive_docs.py`를 두 번 실행: 두 번째는 아무것도 쓰지 않는다.
- N/A Thread safety, lifetime, MSVC/Clang, templates, ODR, UB: C++ 변경 없음.

## 5. Acceptance Criteria

| ID | Criterion | Verified by |
|---|---|---|
| AC-1 | `--boot`는 todo 머리말, 상태 요약, CLOSED가 아닌 KI 행만 출력한다. Phase 목록의 task 줄과 CLOSED 행은 나오지 않는다 | `test_agent_scripts.py` LintDocsTest 새 테스트(임시 저장소 fixture) |
| AC-2 | `--ki KI-002`는 그 섹션만 출력한다. 없는 id가 섞이면 exit 1, 찾은 섹션은 출력한다 | 같은 테스트 클래스 |
| AC-3 | todo에 `---`가 없으면 `--boot`는 전체를 출력하고 NOTE 줄을 낸다 | 같은 테스트 클래스 |
| AC-4 | 한도마다(열린 KI 21개, DEFERRED 31개, 머리말 5 KiB 초과, 진행 순서의 `~~…~~ (DONE …)`, `--boot` 16 KiB 초과) `--boot` 맨 위에 그 `BUDGET:` 줄이 나오고, 한도 안이면 나오지 않는다. 문서 게이트는 한도로 WARN을 내지 않는다 | 같은 테스트 클래스 |
| AC-4a | `--boot`는 DEFERRED 행을 보여 주지 않고 개수 한 줄만 낸다. `--deferred`는 DEFERRED 표를 출력한다. Owner 칸이 `—`뿐인 DEFERRED는 lint ERROR | 같은 테스트 클래스 |
| AC-5 | 부트 문서 2·3단계가 `--boot`·`--ki`를 쓰고, 맨 위에 서브 에이전트 문장이 있고, hook 문단이 한 줄이다. delegation.md §4에 같은 서브 에이전트 문장이 있다 | diff 읽기 + `lint_docs.py` exit 0 |
| AC-6 | 지금 저장소에서 `--boot` 출력이 10 KB 이하다(전: 부트 2·3단계 합계 75.2 KB) | `wc -c` 출력, testrecord |
| AC-7 | `archive_docs.py`는 KI(표 행과 본문)를 상태에 맞는 파일로(DEFERRED → deferred 파일, CLOSED → archive, DEFERRED에서 OPEN으로 바뀐 것 → 원래 파일) 옮기고, DONE task 줄을 archive로 옮기고, 아직 DONE이 아닌 patch가 있는 task는 남기며, 두 번째 실행은 아무것도 바꾸지 않는다 | `test_agent_scripts.py` 새 테스트(임시 저장소 fixture) |
| AC-8 | 옮긴 뒤에도 lint 결과가 같다: archive에 있는 KI id를 가리키는 참조는 통과하고, 그룹 `(k/n DONE)` 수는 두 파일 합으로 맞고, DONE task의 봉인된 폴더는 그대로 봉인이다. 원래 파일에 CLOSED KI가 남으면 WARN, 같은 id가 두 파일에 있으면 ERROR | 같은 테스트 클래스 |
| AC-9 | 지금 저장소에서 첫 실행 뒤 `known_issues.md` 30 KB 이하, `agent_todo.md` 12 KB 이하, `lint_docs.py` 경고 0 | `wc -c`, 명령 출력, testrecord |
| AC-9a | 첫 정리(§0의 6d)를 적용한 뒤 `--boot`에 `BUDGET:` 줄이 없다(열린 KI 20개 이하, 머리말 5 KiB 이하, 진행 순서에 끝난 항목 없음). 분류는 사용자 결정 기록과 일치한다 | `--boot` 출력, testrecord의 결정 표 |
| AC-10 | 회귀 없음: `test_agent_scripts.py` 전부 통과, `lint_docs.py` 경고 0 | 명령 출력 |

## 6. Out of Scope
- `subagent_run.py`가 프롬프트에 서브 에이전트 머리말을 자동으로 붙이는 것 — 새 KI(러너가 공유 kit로 옮겨질 때)
- Antigravity 진입 rule — 090-09
- skill, hook — 090-10, 090-11

## 7. Dependencies & Backends
none

## 8. Documentation Updates

| Document | Section | Change |
|---|---|---|
| [agent_start_prompt.md](/docs/agent_start_prompt.md) | 맨 위, Boot 2·3, Quick reference, hook 문단 | 서브 에이전트 문장, `--boot`·`--ki`, hook 문단 한 줄 |
| [delegation.md](/.agent/rules/delegation.md) | §4 Every prompt states | 서브 에이전트 문장 |
| [test.md](/.agent/rules/test.md) | Docs gate 문단 | KI 상태와 파일 위치, DEFERRED 조건 칸 검사를 더함(한도는 게이트가 아니라 `--boot`) |
| `docs/known_issues_deferred.md` (새 파일) | 머리말 | DEFERRED의 뜻, 다시 OPEN으로 바꾸는 법 |
| [known_issues.md](/docs/known_issues.md) | 머리말, 새 KI | 머리말: "부트는 `--boot`로 표만 읽는다", "CLOSED는 archive로 옮겨진다(옛 문장 'Closed entries stay as a record'를 바꿈)". 러너 자동 머리말 KI |
| [agent_todo.md](/docs/agent_todo.md) | Grammar | DONE 줄은 archive에 있고 그룹 수는 두 파일의 합 |
| `docs/archive/known_issues_closed.md`, `docs/archive/agent_todo_done.md` (새 파일) | 머리말 | 무엇이 언제 옮겨지는지, 고치지 않는 기록이라는 것 |
| [start-develop-one-task.md](/.agent/workflows/start-develop-one-task.md) | 2단계, 6단계 | 2: `BUDGET:` 줄이 있으면 정리안을 먼저 사용자에게. 6: `archive_docs.py` 실행 |
| [agent_start_prompt.md](/docs/agent_start_prompt.md) | Quick reference | "Archive" 행 |

## 9. Technical Constraints
- Python 3.12+, 표준 라이브러리만(`agent_common.py`와 같다).

## 10. Context & References
- [lint_docs.py](/.agent/scripts/lint_docs.py) `parse_todo`, `print_status`
- [test_agent_scripts.py](/.agent/scripts/test_agent_scripts.py) `LintDocsTest`
- [subagent_run.py](/.agent/scripts/subagent_run.py) (변경 없음)

## 11. Implementation Plan
- [ ] U1: AC-1~4 테스트를 먼저 쓴다(지금 코드에서 실패) → `boot_text`, `--boot`, `--ki`, 크기 WARN
- [ ] U2: AC-7·8 테스트를 먼저 쓴다 → lint가 archive를 함께 읽게 함, `archive_docs.py`
- [ ] U3: `archive_docs.py` 첫 실행(스크립트 결과만, 손 편집 없음) → AC-9
- [ ] U3a: 열린 KI 25개 분류안과 진행 순서 정리안을 사용자에게 → 결정대로 Status 칸·진행 순서 수정 → `archive_docs.py` 두 번째 실행 → AC-9a
- [ ] U4: 부트 문서, delegation.md §4, test.md, workflow 6단계, todo Grammar, archive 머리말 (doc 단위)
- [ ] U5: known_issues.md 머리말과 새 KI

## 12. Verification Plan
- [ ] `py -3 .agent/scripts/test_agent_scripts.py`
- [ ] `py -3 .agent/scripts/lint_docs.py` 경고 0
- [ ] `py -3 .agent/scripts/lint_docs.py --boot | wc -c` (AC-6)
- [ ] `py -3 .agent/scripts/archive_docs.py` 뒤 `wc -c docs/known_issues.md docs/agent_todo.md` (AC-9)
- [ ] 측정(통과 조건 아님): 같은 read-only codex review 프롬프트를 변경 전·후로 한 번씩 실행해 러너가 출력한 입력 토큰을 testrecord에 적는다. 차이가 없으면 119k의 원인은 다른 곳이므로 KI로 남긴다

## History / Amendments
- 2026-11-06: 초안
- 2026-11-06: archive(사용자 요청), 항목별 한도·task 선택 때 적용·DEFERRED 별도 파일(사용자 결정)을 반영
- 2026-11-06: 승인
