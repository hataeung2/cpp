---
id: 070-16
title: 연습 작업 공간과 되돌리기 (원본을 건드리지 않는 레슨 연습)
depends_on: [070-02, 070-15]
unblocks: [070-17]
approved: 2026-11-10
---

# Spec 070-16: 연습 작업 공간과 되돌리기 (원본을 건드리지 않는 레슨 연습)

## 0. Assumptions (please review)
| # | Decision | Rejected alternative | Why |
|---|---|---|---|
| 1 | **범위는 다섯이다**: (a) git이 무시하는 연습 공간 `practice/`, (b) 연습 공간을 다루는 공용 모듈과 CLI `tools/practice.py`, (c) 연습 사본을 빌드하는 CMake 타깃 `practice_<id>`, (d) 서버 API와 파일 쓰기 규칙, (e) 페이지의 연습/원본 편집 모드, 되돌리기, 원본과 비교. **과제 확인은 070-17**이 한다 | 과제 확인까지 한 작업으로 | 사용자 결정(2026-11-10): 과제 확인은 다른 스펙으로 이 작업 다음에 한다 |
| 2 | **위치는 저장소 루트의 `practice/`**이고 `.gitignore`에 `/practice/`를 더한다 | (a) `out/practice/`; (b) 저장소 밖(사용자 홈); (c) git 브랜치나 stash | (a) `out/`은 빌드 산출물이라 지워도 되는 곳으로 여겨지고(`rm -rf out`), 그러면 사용자의 연습이 사라진다. (b) 기계마다 경로가 다르고 WSL과 Windows의 경로가 갈린다(규칙 1). (c) 서버가 git을 조작하면 작업 브랜치 규칙과 부딪히고(규칙 4), WSL에서 Windows 체크아웃을 다루면 *dubious ownership*이 난다. git이 무시하는 폴더는 저장소 검사(`repo_files`)에서도 저절로 빠진다 |
| 3 | **연습 공간은 원본 경로를 그대로 비춘다**: `practice/lessons/tracks/<track>/<lesson>/`, `practice/lessons/units/<unit>/`. 레슨 사본 = 그 레슨의 `lesson.toml`과 `sources` 전부(README 제외). 유닛 사본 = 그 레슨이 쓰는 유닛(전이 `uses`의 `unit:`)마다 `unit.toml`과 `files` 전부 | 고친 파일만 두는 덧씌우기(overlay) | 레슨 소스는 `#include "version.hpp"`처럼 같은 폴더를 먼저 찾는 따옴표 include를 쓴다. 고친 파일만 사본에 있으면 사본이 원본 폴더의 다른 파일을 찾지 못하거나, 원본과 사본이 한 빌드에 섞인다. 폴더째 복사하면 사본만으로 빌드된다. 레슨 하나는 수십 KB라 비용이 없다 |
| 4 | **사본을 만드는 때**: 연습 모드에서 레슨을 처음 열 때(페이지), 또는 `tools/practice.py start <lesson>`(로컬). 이미 있는 사본은 덮지 않는다. **유닛 사본은 레슨들이 같이 쓴다**(원본 유닛처럼). 레슨 A의 연습에서 고친 `jthread_worker`는 레슨 B의 연습 빌드에도 쓰인다 | 레슨마다 유닛 사본을 따로 | 유닛은 "여러 레슨이 같이 쓰는 코드"라는 뜻이고(070-01), 연습에서도 그 성질을 보여야 한다. 페이지는 고친 유닛을 "연습 사본(수정됨)"으로 표시하고, 유닛은 따로 되돌린다(Assumption 8) |
| 5 | **빌드**: [`lessons/CMakeLists.txt`](/lessons/CMakeLists.txt)가 `practice/lessons/tracks/*/*/lesson.toml`도 `CONFIGURE_DEPENDS`로 찾아, 원본과 같은 규칙으로 `practice_<id>` 실행 파일을 만든다(`bin/practice/`). include 경로는 `practice/lessons`가 먼저, 다음이 `lessons`. 연습 타깃은 `EXCLUDE_FROM_ALL`이고 smoke test(`add_test`)가 없다. 새 사본은 다음 빌드가 configure를 다시 돌려 찾는다(새 레슨 폴더를 찾는 지금의 방식) | (a) 원본 타깃의 소스를 configure 변수로 바꿔치기; (b) 서버가 컴파일러를 직접 부름 | (a) 원본과 연습을 바꿀 때마다 configure가 돌고, 두 타깃이 한 빌드 디렉터리에 같이 있을 수 없다. (b) preset으로만 빌드한다는 규칙 2를 어기고 컴파일 옵션이 두 곳에 생긴다. `EXCLUDE_FROM_ALL`과 smoke test 없음 덕분에 반쯤 고친 연습이 전체 빌드와 `ctest`를 깨지 않는다 |
| 6 | **연습 사본의 `lesson.toml`·`unit.toml`은 읽기 전용이고, 연습 공간에 새 파일을 만들 수 없다** | 연습에서 소스 추가 허용 | 소스를 더하려면 매니페스트를 고쳐야 하고, 그러면 되돌리기와 "원본 따라가기"(Assumption 7)가 매니페스트까지 다뤄야 한다. 지금 레슨의 연습 과제는 모두 있는 파일을 고친다. 새 파일이 필요한 과제가 생기면 KI로 남긴다 |
| 7 | **기준(base)을 기록한다**: `practice/state.json` = `{"version": 1, "files": {"<사본 경로>": {"origin": "<원본 경로>", "baseSha": "<sha256>"}}}`. 사본을 만들거나 되돌릴 때 원본의 sha를 적는다. 상태: **수정됨** = 사본 sha ≠ baseSha, **원본 바뀜** = 원본 sha ≠ baseSha. **수정하지 않은 사본은 원본이 바뀌면 저절로 새 원본을 받는다**(start·status 때). 수정한 사본은 그대로 두고 페이지가 알린다(비교, 원본 받기 = 되돌리기) | git `HEAD`를 기준으로 | 서버가 git을 불러야 하고(Assumption 2), 원본 편집 모드에서 저장했지만 아직 커밋하지 않은 원본과 기준이 어긋난다. 디스크의 원본과 sha를 비교하면 git 없이 된다(`files.py`의 sha와 같은 계산) |
| 8 | **되돌리기 단위는 셋**: 파일 하나(탭의 ↺), 레슨 하나(레슨 사본의 모든 파일, 유닛 제외), 유닛 하나. 되돌리기 전에 페이지의 대화상자가 사라질 수정 파일 목록을 보이고 묻는다. **되돌린 파일은 `practice/backup/<YYYYMMDD-HHMMSS>/<사본 경로>`에 남기고 최근 10번만 둔다** | 백업 없이 덮어쓰기 | 되돌리기는 사용자의 작업을 지우는 유일한 동작이다. 실수로 눌렀을 때 손으로 꺼낼 길을 남긴다(페이지는 그 경로를 한 줄로 알린다). 10번이면 수 MB를 넘지 않는다 |
| 9 | **원본과 비교**: 탭의 "비교"가 Monaco diff 편집기를 연다(왼쪽 원본 읽기 전용, 오른쪽 사본, 사본 쪽은 고칠 수 있음). 원본 바뀜 알림의 "비교"도 같은 화면 | 비교 없이 되돌리기만 | 되돌리기 전에 무엇을 잃는지, 원본이 바뀌었을 때 무엇이 바뀌었는지를 보는 방법이 있어야 되돌리기를 안심하고 쓴다. Monaco에 diff 편집기가 들어 있어 새 의존이 없다 |
| 10 | **모드는 둘**: 위쪽 막대의 `연습 | 원본 편집`. 기본은 연습. 원본 편집은 지금의 동작이다(`lessons/`에 저장, `lesson_<id>` 빌드). 원본 편집 모드에서는 위쪽 막대와 탭에 경고색 표시가 붙는다. 선택은 브라우저 저장소 `atugcc.mode`(읽지 못하면 연습) | 원본 편집 제거 | 페이지에서 레슨·소개 글을 고치는 일(070-08)은 레슨 작성자에게 필요하다. 기본을 연습으로 두어 배우는 사람이 원본을 실수로 바꾸지 않게 한다 |
| 11 | **연습 모드의 Run**: `POST /api/runs`에 `practice: true` → `cmake --build --preset <p> --target practice_<id>`, 실행 파일 `bin/practice/practice_<id>`, 작업 디렉터리는 레슨 사본 폴더. 이벤트·진단·Timings의 파일 경로는 사본 경로(`practice/lessons/…`)이고 편집기 탭도 사본 경로라서 줄 이동·표시가 그대로 이어진다. Timings의 "이전 실행 대비"는 레슨 id와 모드를 함께 열쇠로 쓴다 | 원본 경로로 바꿔 보여 주기 | 경로를 바꾸면 줄 이동이 원본 탭을 열어 사용자가 원본을 고치게 된다. 레슨이 작업 디렉터리에 쓰는 파일(`log/` 등)도 사본 폴더에 남아 git에 섞이지 않는다 |
| 12 | **파일 규칙**(`web/server/files.py`): 쓰기 허용 = `lessons/` 아래(원본 편집, 지금과 같음)와 `practice/lessons/` 아래의 **이미 있는** 파일 중 `lesson.toml`·`unit.toml`이 아닌 것. `practice/state.json`, `practice/backup/**`, `practice/` 아래 새 파일은 403. 원본 편집 모드가 아닌데 `lessons/`에 쓰는 것은 페이지가 막는다(서버는 모드를 모른다) | 서버가 모드를 기억 | 서버는 한 사용자의 로컬 도구이고 요청마다 모드를 들고 다니면 상태가 둘이 된다. 연습 모드의 탭은 `practice/` 경로만 열기 때문에 페이지만으로 충분하다 |
| 13 | **CLI가 서버와 같은 모듈이다**: `py -3 tools/practice.py start|status|reset|path <lesson> [--file <path>] [--unit <id>]`. 서버는 `tools/lessons.py`처럼 `load_module`로 같은 코드를 쓴다. 로컬 빌드는 `py -3 .agent/scripts/build.py --preset <p> --target practice_<id>` | 웹 전용 | 사용자는 VS Code에서도 공부한다(기억: 웹은 로컬 전용, 같은 레슨을 두 곳에서). 같은 연습 공간을 두 곳에서 쓰려면 규칙이 한 곳에 있어야 한다 |
| 14 | **README는 원본을 보인다**(두 모드 모두). 연습 모드의 README 탭은 읽기 전용이다 | README도 사본 | README는 설명이고 연습 대상이 아니다. 원본 편집 모드에서만 고친다 |
| 15 | **기존 README의 "확인한 뒤 되돌립니다" 문장**은 "되돌리기(↺)로 원본으로 돌아갑니다(웹), `tools/practice.py reset`(로컬)"으로 바꾼다. 대상 레슨은 DEV에서 `grep`으로 찾는다 | 그대로 둠 | 연습 공간이 생기면 원본을 고치지 않으므로 옛 문장은 틀린 안내다 |
| 16 | **C++20 모듈 레슨**(`15_modules`): 연습 타깃의 모듈 이름은 원본과 같다(`modules.geometry`). 두 타깃이 한 빌드에서 같은 이름의 모듈을 각자 만든다. CMake는 BMI를 타깃마다 따로 두고 둘을 함께 import하는 타깃이 없으므로 된다고 보고, **DEV 첫 단계에서 확인한다**. 안 되면 멈추고 스펙을 고친다 | 연습 사본의 모듈 이름을 바꿈 | 사용자 코드의 모듈 이름을 바꾸면 레슨 내용이 바뀐다 |
| 17 | **GoogleTest 레슨**: 연습 타깃의 `ATUGCC_SCENARIO_WORK_ROOT`는 `<빌드>/lessons/practice_scenario_work`(원본과 겹치지 않음) | 같은 곳 | 원본과 연습을 번갈아 돌릴 때 시나리오 `workDir`이 서로를 지운다 |
| 18 | **진행 순서**: 사용자 결정(2026-11-10)으로 070-16 → 070-17 → 070-18 → 070-07 → 070-19 → 070-20을 B(레슨과 엔진 병행)보다 먼저 한다. 이 스펙이 `agent_todo.md`의 진행 순서에 그것을 적는다 | — | 순서는 사용자 결정 |

## 1. Objective
지금 웹 플레이그라운드는 Run할 때 수정한 탭을 **저장소의 레슨 파일**에 바로 저장한다. 연습 과제를 풀면 레슨 원본이 바뀌고, 원래대로 돌리는 기능이 없어 git을 손으로 써야 한다(README도 "확인한 뒤 되돌립니다"라고만 적는다). 바뀐 원본은 작업 트리에 남아 다음 작업 브랜치(규칙 4)에 섞인다. 이 작업은 원본을 건드리지 않는 연습 공간을 만든다: 레슨을 사본에서 고치고 빌드·실행하고, 파일·레슨·유닛 단위로 원본으로 되돌리고, 원본과 비교한다. 같은 공간을 웹과 로컬(VS Code, `build.py`)에서 쓴다. 070-17(과제 확인)이 이 공간의 실행 결과를 검사한다.

## 2. Requirement Details

### 2.1 Public API Surface
C++ API 변경 없음. 바뀌는 표면은 CMake 타깃, CLI, HTTP API다.

| 표면 | 내용 |
|---|---|
| CMake 타깃 | `practice_<id>`(`EXCLUDE_FROM_ALL`, `bin/practice/practice_<id>`), 연습 사본이 있는 레슨마다 |
| CLI | `tools/practice.py start <lesson>`: 레슨·유닛 사본을 만들고 경로를 찍는다. `status [<lesson>]`: 파일마다 `same`/`modified`/`origin-changed`/`both`. `reset <lesson>` / `reset --unit <id>` / `reset --file <사본 경로>`: 백업 후 원본으로. `path <lesson>`: 사본 폴더 경로. 종료 코드 0 / 1(오류) / 2(인자) |
| HTTP | `GET /api/practice?lesson=<id>` → `{lesson, dir, files: [{path, origin, state}], units: [{id, dir, files: [...]}]}` (자동 따라가기를 먼저 적용). `POST /api/practice/start {lesson}` → 같은 모양. `POST /api/practice/reset {lesson} | {unit} | {path}` → `{reset: [<경로>], backup: "<practice/backup/…>"}`. `POST /api/runs {…, practice: true}` |

`state`: `same`(수정 안 함, 원본과 같음), `modified`, `origin-changed`(수정 안 했는데 원본이 바뀜. 응답 전에 자동으로 따라가므로 응답에는 나오지 않고, 수정한 파일에만 생기는 `both`가 나온다), `both`(수정했고 원본도 바뀜).

### 2.2 Internal Implementation
| 곳 | 바꾸는 것 |
|---|---|
| `.gitignore` | `/practice/` |
| `tools/practice.py` (새) | 경로 변환(`lessons/…` ↔ `practice/lessons/…`), `start`(레슨 사본 + 전이 유닛 사본, 있으면 건너뜀), `status`(sha 비교, 수정 안 한 사본의 자동 따라가기), `reset`(백업 → 원본 복사 → baseSha 갱신, 백업 10개 유지), `state.json` 읽기·쓰기(임시 파일 + `os.replace`). 레슨 목록은 `tools/lessons.py`의 인덱스를 쓴다. CLI `main()` |
| `tools/test_practice.py` (새) | 임시 저장소에서 start / 수정 / status / 원본 바뀜 / 자동 따라가기 / reset 셋 / 백업 개수 / 읽기 전용 매니페스트 / 손상된 `state.json`(이름을 바꿔 두고 새로 만듦, 사본은 지우지 않음) |
| [`lessons/CMakeLists.txt`](/lessons/CMakeLists.txt) | 레슨 하나를 등록하는 본문을 `function(atugcc_add_lesson manifest prefix out_dir include_dirs)`로 빼서 원본(`lesson_`, `bin/lessons`, `lessons`)과 연습(`practice_`, `bin/practice`, `practice/lessons;lessons`)이 같이 쓴다. 연습은 `EXCLUDE_FROM_ALL`, `add_test` 없음, `ATUGCC_SCENARIO_WORK_ROOT`는 `practice_scenario_work` |
| [`web/server/files.py`](/web/server/files.py) | 쓰기 규칙(Assumption 12) |
| [`web/server/server.py`](/web/server/server.py) | `/api/practice` GET·POST(`start`, `reset`), `/api/runs`의 `practice` |
| [`web/server/runner.py`](/web/server/runner.py) | `Job`에 `practice`, 타깃·실행 파일·작업 디렉터리 선택 |
| [`web/server/test_server.py`](/web/server/test_server.py) | 파일 규칙 403 경우들, practice API, 연습 Run(fixture) |
| [`web/frontend/src`](/web/frontend/src/main.ts) | `main.ts`: 모드 전환, 레슨을 열 때 `start`, 탭 경로를 사본으로, Run에 `practice`. `editor.ts`: 탭의 ↺ 되돌리기·비교 버튼, 상태 점(수정됨 ●, 원본 바뀜 ⚠), diff 편집기. `lessonTree.ts`: 수정된 사본이 있는 레슨·유닛 표시. `api.ts`, `i18n.ts`(모든 새 문구 두 언어), `theme.css`(원본 편집 경고색) |
| 프런트엔드 테스트 | 모드 저장(저장소 막힘 포함), 경로 변환, 상태 표시 |

### 2.3 Platform Specifics
- 웹 서버는 WSL에서 Windows 체크아웃(`/mnt/c/…`)에 쓴다. 사본은 원본의 줄 끝(CRLF/LF)을 그대로 복사하고, 저장은 `files.py`의 지금 규칙(파일의 줄 끝 유지)을 따른다.
- 로컬 Windows preset도 `practice_<id>`를 만든다(Assumption 13). MSVC와 Clang 모두 경고 없이 빌드돼야 한다(원본과 같은 소스이므로 같은 조건).

## 3. C++ Standard Evolution
N/A (도구와 페이지 작업).

## 4. Edge Cases
- [x] Thread safety — 서버의 practice 동작은 `RepoFiles.write_lock` 아래에서 한 번에 하나. CLI와 서버가 동시에 `state.json`을 쓰면 나중 것이 이긴다(임시 파일 + 교체라 깨지지는 않음). 로컬 한 사용자 도구라 받아들인다.
- [x] Resource lifetime — 연습 Run 중에 되돌리기: 실행 파일은 이미 빌드됐으므로 실행은 계속되고 다음 Run이 되돌린 소스로 빌드한다. 페이지는 Run 중에 되돌리기 버튼을 끈다.
- [x] Platform differences — 줄 끝(§2.3). 경로는 저장소 상대 `/`만.
- [x] Template instantiation / concept constraints — N/A.
- [x] ODR — 연습 타깃과 원본 타깃은 다른 실행 파일이다. 유닛 헤더는 한 타깃 안에서 사본 하나만 보인다(include 경로 순서).
- [x] Undefined behaviour — N/A.
- [x] 사본이 없는데 연습 Run — 서버가 `start`를 먼저 부른다. 새 사본이면 그 빌드가 configure를 다시 돈다(빌드 시간 상한 안, AC-2에서 잰다).
- [x] 원본 레슨이 지워지거나 id가 바뀜 — `status`가 사본을 "원본 없음"으로 알리고 지우지 않는다. 연습 타깃은 사본의 매니페스트로 계속 빌드된다. 페이지는 트리에 없는 레슨의 사본을 보이지 않는다(`tools/practice.py status`로 보임).
- [x] 원본의 `sources`가 바뀜(파일 추가·삭제) — 매니페스트 사본은 수정할 수 없으므로 항상 따라간다. 새 소스는 사본에 복사하고, 빠진 소스의 사본은 백업으로 옮긴다.
- [x] 손상된 `state.json` — `state.json.broken-<시각>`으로 이름을 바꾸고 모든 사본을 "수정됨"으로 보며 baseSha를 현재 원본으로 다시 적는다. 사본은 지우지 않는다.
- [x] 같은 유닛을 쓰는 두 레슨 — 유닛 사본 하나(Assumption 4). 레슨 되돌리기는 유닛을 건드리지 않는다.
- [x] 원본 편집 모드에서 원본 저장 — 수정 안 한 사본은 다음 `status`에서 따라가고, 수정한 사본은 `both`가 된다.
- [x] 전체 빌드와 `ctest` — 연습 타깃은 `EXCLUDE_FROM_ALL`, smoke test 없음. 깨진 사본이 있어도 `build.py --test`가 통과한다(AC-8).
- [x] 저장소 검사 — `practice/`는 git이 무시하므로 `lint_docs.py`, `naming_check.py`, 기계 경로 hook, `lessons.py check`가 보지 않는다(`repo_files`).
- [x] 백업 폴더 시각 충돌(같은 초에 두 번) — 폴더 이름에 `-2`, `-3`을 붙인다.

## 5. Acceptance Criteria
| ID | Criterion | Verified by |
|---|---|---|
| AC-1 | `start lambda_capture`가 레슨 사본(`lesson.toml`, `sources`)과 쓰는 유닛 사본을 만들고, `state.json`에 파일마다 원본 sha를 적는다. 그 뒤 `git status --porcelain`이 비어 있다 | `tools/test_practice.py`, 실제 저장소에서 CLI 실행 기록 |
| AC-2 | 연습 Run은 `practice_<id>`를 사본으로 빌드해 실행한다. 사본의 출력 문자열을 바꾸면 Run 출력이 바뀌고, 원본 `lessons/` 파일의 sha와 `lesson_<id>`의 출력은 그대로다. 새 사본의 첫 연습 Run(configure 포함) 시간을 기록하고 빌드 상한 안이다 | `test_server.py`의 연습 Run, 헤드리스 브라우저, 시간 기록 |
| AC-3 | 연습 모드에서 탭을 저장하면 `practice/…`만 바뀐다. `PUT`으로 사본의 `lesson.toml`, `unit.toml`, `practice/state.json`, `practice/backup/…`, `practice/` 아래 새 파일을 쓰면 403이다 | `test_server.py` |
| AC-4 | 되돌리기 셋(파일, 레슨, 유닛)이 대상 파일을 원본과 같은 바이트로 되돌리고 상태가 `same`이 된다. 되돌린 수정 파일은 `practice/backup/<시각>/`에 있고, 백업은 최근 10개만 남는다. 레슨 되돌리기는 유닛 사본을 바꾸지 않는다 | `tools/test_practice.py`, `test_server.py` |
| AC-5 | 원본을 바꾸면 수정하지 않은 사본은 다음 status에서 새 원본이 되고, 수정한 사본은 그대로이며 `both`로 나온다. 페이지는 그 탭에 ⚠와 "비교 / 원본 받기"를 보이고, 비교는 원본과 사본을 나란히 보인다 | `tools/test_practice.py`, 헤드리스 브라우저 스크린샷 |
| AC-6 | 모드 전환이 동작한다: 기본 연습, 원본 편집 모드는 이 작업 전과 같다(저장 대상 `lessons/`, 타깃 `lesson_<id>`, 기존 웹 테스트 통과). 선택은 새로 고침 뒤에도 남고, 저장소가 막히면 연습이다 | 프런트엔드 테스트, 헤드리스 브라우저 |
| AC-7 | 로컬: `windows-x64-debug`와 `linux-x64-debug`에서 사본을 만든 뒤 `build.py --preset <p> --target practice_lambda_capture`가 경고 없이 빌드되고 실행된다. `modules`(`15_modules`)와 `testing`(`16_testing`)도 연습 타깃이 빌드·실행된다(Assumption 16, 17) | 빌드 로그와 실행 출력, testrecord |
| AC-8 | 연습 사본이 있고 그중 하나가 일부러 컴파일되지 않을 때도 `build.py --preset <p> --test`가 통과하고, `ctest -N`의 테스트 목록은 사본이 없을 때와 같다 | 두 목록 비교, 빌드·테스트 출력 |
| AC-9 | 헤드리스 브라우저: 레슨을 열면 탭 경로가 `practice/lessons/…`이다. 고치고 Run → 출력 반영, ●표시, ↺ → 확인 대화상자의 파일 목록 → 원본 내용, 백업 경로 안내 줄 | 스크린샷 3장(수정, 대화상자, 되돌린 뒤) |
| AC-10 | 이벤트 행 클릭, 빌드 진단, GoogleTest 실패 표시(070-15), Timings 줄 이동이 연습 모드에서 사본 탭으로 간다 | 헤드리스 브라우저(`device_state_machine`, `testing`, `span_timing`) |
| AC-11 | 전체 suite(`windows-x64-debug`, `linux-x64-debug`), `npm --prefix web/frontend test`, `PlaygroundServer`, `tools/test_practice.py`, `tools/test_lessons.py`가 통과하고 §8 문서가 결과와 맞으며 `lint_docs.py`가 exit 0이다 | 명령 출력 |

## 6. Out of Scope
- 연습 과제 확인과 진행 기록 — 070-17
- 연습 공간에서 새 소스 파일 만들기, 매니페스트 고치기 — 하지 않는다(Assumption 6). 필요한 과제가 생기면 KI
- 백업을 페이지에서 꺼내기 — 하지 않는다(경로만 알림)
- `lib:` 헤더(`include/`)의 연습 사본 — 하지 않는다. 라이브러리 고치기는 원본 작업이다
- 여러 사용자, 공개 플레이그라운드 — 070-05

## 7. Dependencies & Backends
없음(Python 표준 라이브러리, 이미 쓰는 Monaco의 diff 편집기).

## 8. Documentation Updates
| Document | Section | Change |
|---|---|---|
| [`lessons/README.md`](/lessons/README.md) | 새 절 "연습 공간" | `practice/`의 구조, 웹의 두 모드, `tools/practice.py` 명령, `practice_<id>` 로컬 빌드, 되돌리기와 백업 |
| [`web/README.md`](/web/README.md) | 첫 문단, API, Page, Tests | "저장소 파일을 고친다" → 모드 둘; `/api/practice`, `practice` Run; 모드·되돌리기·비교; 새 테스트 |
| [`lessons/intro.md`](/lessons/intro.md), [`intro.en.md`](/lessons/intro.en.md) | 할 수 있는 일 | 연습 모드는 원본을 바꾸지 않고 ↺로 되돌린다는 한 줄 |
| 레슨 README(두 판) 중 "되돌립니다"가 있는 것 | 연습 | Assumption 15의 문장으로 |
| [`.agent/rules/config.md`](/.agent/rules/config.md) | 빌드 타깃 | `practice_<id>`가 있다는 것, `EXCLUDE_FROM_ALL`(한 줄) |
| [`docs/agent_todo.md`](/docs/agent_todo.md) | 진행 순서, Phase 7 | 사용자 결정 2026-11-10의 순서(Assumption 18), 070-16 줄 |

## 9. Technical Constraints
- Compiler: MSVC (VS 2026) / Clang 20 with libstdc++ 14 (Linux)
- CMake: 4.0+ (C++20 modules always on), Ninja
- Python 3.11+ 표준 라이브러리만(서버, 도구)
- 프런트엔드: 지금의 Vite + TypeScript + Monaco(새 패키지 없음)

## 10. Context & References
- [070-01 스펙](/docs/specs/070_01_lesson_structure.md)(레슨·유닛 구조), [070-02 스펙](/docs/specs/070_02_web_playground.md)(파일 API, Run), [070-15 스펙](/docs/specs/070_15_essentials_testing_lesson.md) Edge Cases "연습 뒤 되돌리라"
- [`lessons/CMakeLists.txt`](/lessons/CMakeLists.txt), [`tools/lessons.py`](/tools/lessons.py), [`web/server/files.py`](/web/server/files.py), [`web/server/runner.py`](/web/server/runner.py)(`_build`, `_execute`), [`web/frontend/src/editor.ts`](/web/frontend/src/editor.ts)
- [`.agent/scripts/agent_common.py`](/.agent/scripts/agent_common.py) `repo_files`(git이 무시하는 파일을 빼는 근거)
- 이 스펙은 새 시험을 하지 않았다. 같은 모듈 이름의 두 타깃(Assumption 16)과 `CONFIGURE_DEPENDS`가 새 사본을 찾는지는 DEV 첫 단계에서 확인한다

## 11. Implementation Plan
- [ ] Step 1: `lessons/CMakeLists.txt` 함수화와 연습 타깃. 손으로 만든 사본으로 `practice_lambda_capture`, `practice_modules`, `practice_testing`을 두 호스트에서 빌드(Assumption 16 확인), 새 사본 → 다음 빌드의 configure 확인
- [ ] Step 2: `tools/practice.py`, `tools/test_practice.py`, `.gitignore`
- [ ] Step 3: 서버(`files.py`, `server.py`, `runner.py`)와 `test_server.py`
- [ ] Step 4: 프런트엔드(모드, 탭 경로, ↺, 비교, 상태 표시, 트리 표시, i18n)와 테스트
- [ ] Step 5: §8 문서, 레슨 README 문장

## 12. Verification Plan
- [ ] `py -3 .agent/scripts/build.py --preset windows-x64-debug --test`, `--preset linux-x64-debug --test` (사본 있음, 깨진 사본 하나 포함)
- [ ] `ctest -N` 목록 비교(AC-8)
- [ ] `py -3 tools/test_practice.py`, `py -3 tools/test_lessons.py`, `npm --prefix web/frontend test`, `ctest -R PlaygroundServer`
- [ ] 헤드리스 브라우저(AC-2, 5, 6, 9, 10)
- [ ] `lint_docs.py` exit 0
- [ ] 모든 AC 행의 증거가 `testrecord.md`에

## History / Amendments
- 2026-11-10: 초안
- 2026-11-10: 승인(사용자, 070-07·070-17·070-18·070-19와 함께)
- 2026-11-10 (DEV, 동작 변화 없음): Assumption 15의 문장 바꾸기는 레슨 README 다섯 쌍(03, 04, 12, 15, 16)의 연습 절 머리(16은 "파일과 실행" 목록)에 되돌리는 방법을 한 줄 두는 것으로 했다. "되돌립니다"가 한 README에 많게는 8번 나와 문장마다 명령을 붙이면 읽기 어렵다. `tools/practice.py`에 `status_all()`(쓰는 레슨이 없어진 유닛 사본과 원본이 사라진 사본을 보임, §4)을 더했다. 페이지는 연습 모드에서 잠긴 원본 탭의 툴팁으로 안내한다(`practice.readOnlyOriginal`). 모드를 바꾸기 전에 열린 탭을 저장한다(원본 편집 모드의 편집이 연습 모드에서 읽기 전용이 되어 남지 않게)
- 2026-11-12 (서브 스펙 [070-16-01](/docs/specs/070_16_01_backup_by_owner.md)): Assumption 8의 백업 보관 규칙을 "되돌릴 때마다 시각 폴더, 최근 10번"에서 "레슨·유닛별 폴더, 파일마다 최근 10개"로 바꾼다. 이 문서의 본문은 고치지 않는다
