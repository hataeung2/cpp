---
id: 070-16-01
title: 연습 백업을 레슨·유닛별 한 폴더에 모으기 (파일마다 최근 10개)
depends_on: [070-16]
unblocks: []
approved: 2026-11-12
---

# Spec 070-16-01: 연습 백업을 레슨·유닛별 한 폴더에 모으기 (파일마다 최근 10개)

## 0. Assumptions (please review)
| # | Decision | Rejected alternative | Why |
|---|---|---|---|
| 1 | **범위**: 백업을 남기는 위치와 이름, 보관 규칙만 바꾼다(`tools/practice.py`의 `_Backup`, 그 테스트, 문서). 되돌리기 동작과 상태 계산, 웹 API의 모양, 페이지 코드는 바꾸지 않는다 | 백업 목록·복원 명령도 같이 | 복원은 파일을 복사하면 되는 일이라 이 작업의 문제(흩어진 폴더)와 별개다. 필요해지면 새 작업 |
| 2 | **백업은 소유자(레슨 또는 유닛)별 폴더 하나**: `practice/backup/lessons/<레슨 id>/`, `practice/backup/units/<유닛 id>/`. 레슨과 유닛은 id가 같아도 되므로(070-01) 두 갈래로 나눈다. 폴더 이름은 폴더 번호(`11_thread_and_log`)가 아니라 **id**를 쓴다(폴더 번호는 070-03처럼 바뀐 적이 있음). 유닛 파일을 되돌리면 유닛 폴더로 간다(유닛 사본은 쓰는 레슨들이 같이 쓰므로) | (a) 되돌릴 때마다 시각 폴더(지금); (b) 날짜별 폴더; (c) 원본 경로 그대로(`lessons/tracks/01_essentials/11_thread_and_log/…`) | (a) 문제 그 자체. (b) 하루에 여러 레슨을 하면 섞이고, 레슨을 찾으려면 날마다 뒤져야 한다. (c) 깊이가 5단이고 폴더 번호가 바뀌면 옛 백업이 다른 곳에 남는다. 사용자는 "레슨 하나의 변경 내용을 한 폴더에서" 보려 한다 |
| 3 | **파일 이름은 `<이름>.<YYYYMMDD-HHMMSS>[-n]<확장자>`**: `main.cpp` → `main.20261112-103015.cpp`, `geometry.cppm` → `geometry.20261112-103015.cppm`. 한 번의 되돌리기에서 나온 파일은 **같은 시각**을 받는다(한 번에 되돌린 파일 묶음이 이름으로 보인다). 같은 파일이 같은 초에 또 백업되면 `-2`, `-3`을 붙인다(지금 폴더 이름의 규칙과 같음). 소스가 하위 폴더에 있으면 소유자 폴더 안에서 그 상대 경로를 지킨다 | (a) `main.cpp.20261112-103015`(시각을 끝에); (b) 파일마다 하위 폴더 `main.cpp/20261112-103015.cpp` | (a) 확장자가 사라져 에디터가 C++로 보지 않는다. (b) 레슨 하나에 소스가 많아야 3–5개(`modules`는 5개)라 한 폴더에 최대 50개 안팎이고, 이름순 정렬이 파일별로 시각순 묶음을 만든다. 하위 폴더를 더하면 한 번 더 열어야 한다(폴더 구조 판단은 §2.1) |
| 4 | **보관은 파일마다 최근 10개**: 같은 소유자 폴더에서 같은 원래 파일(상대 경로 + 이름 + 확장자가 같은 것)의 백업을 시각순으로 10개만 둔다. 다른 파일의 백업은 건드리지 않는다. 백업을 만든 직후 그 파일 것만 정리한다 | (a) 소유자 폴더 전체에서 10개; (b) 소유자별 시간 제한(30일 등) | (a) `main.cpp`를 열 번 되돌리면 `legacy_worker.hpp`의 백업이 사라진다. (b) 시계에 기대고 정리 시점이 따로 필요하다 |
| 5 | **옛 형식 폴더(`practice/backup/<시각>/…`)는 건드리지 않는다**: 새 코드는 읽지도 정리하지도 않는다(새 파일은 모두 `lessons/`, `units/` 아래에만 생기므로 이름이 겹치지 않는다). 사용자가 직접 지워도 된다. README에 한 줄로 알린다 | 처음 되돌릴 때 옮겨 담기(마이그레이션) | 한 번 쓰고 버릴 코드이고, 옛 백업은 개인 작업 폴더에 있는 10개뿐이다 |
| 6 | **소유자 id는 카탈로그(`tools/lessons.py`)에서 구한다**: 사본 경로 → 레슨 또는 유닛 → id. 카탈로그에 없으면(레슨이 지워진 뒤 남은 사본) 사본 폴더의 이름을 그대로 쓴다(`practice/backup/lessons/<폴더 이름>/`). 백업을 못 남기는 경우는 만들지 않는다 | 폴더 이름에서 `NN_`을 떼어 id로 | id와 폴더 이름이 다를 수 있고(`lessons.py`는 id를 매니페스트에서 읽음), 틀리면 백업이 다른 폴더에 들어간다 |
| 7 | **웹 API는 그대로**: `POST /api/practice/reset`의 `backup`은 계속 문자열 하나다. 값은 이번 작업의 소유자 폴더(`practice/backup/lessons/thread_and_log`)이고, 아무것도 백업하지 않았으면 `null`. 되돌리기 한 번은 소유자가 하나뿐이다(파일 하나, 레슨 하나는 유닛 제외, 유닛 하나). 자동 따라가기(`start`, `status`)의 백업은 소유자별 폴더에 남기고 값을 돌려주지 않는다(지금과 같음). 페이지의 문구("백업: {경로}")는 그대로 | `backup`을 폴더 목록으로 | 응답 모양을 바꾸면 페이지와 테스트가 같이 바뀐다. 소유자가 하나뿐이라 필요 없다 |

## 1. Objective
**원본과의 관계**
- 원본: [070-16](/docs/specs/070_16_practice_workspace.md) (DONE). 바꾸는 것은 원본 Assumption 8의 마지막 문장 "**되돌린 파일은 `practice/backup/<YYYYMMDD-HHMMSS>/<사본 경로>`에 남기고 최근 10번만 둔다**" 하나다. 되돌리기 단위(파일, 레슨, 유닛), 상태 계산, 사본 구조, 파일 쓰기 규칙(`practice/backup/**`는 403)은 그대로다.
- 다시 여는 이유: 되돌리기 *한 번*마다 폴더가 하나 생겨서, 같은 레슨을 몇 번 되돌리면 폴더가 늘고(지금 `practice/backup/`에 `thread_and_log`의 `main.cpp`만 든 폴더가 10개) 한 레슨에서 고쳤던 내용을 한눈에 볼 수 없다. 원본의 보관 규칙("최근 10번")은 한 파일을 자주 되돌리면 다른 파일의 백업까지 밀어낸다.
- 원본 spec에는 `History / Amendments`에 이 서브 스펙으로의 링크 한 줄을 남긴다. 원본 작업 산출물 폴더(`docs/tasks/feature_070-16-*`)는 봉인이라 쓰지 않는다.

## 2. Requirement Details

### 2.1 폴더 구조
```text
practice/backup/
  lessons/
    thread_and_log/
      main.20261112-103015.cpp
      main.20261112-103031.cpp
      legacy_worker.20261112-103144.hpp
    modules/
      geometry.20261112-110000.cppm
      geometry.20261112-110000.cpp        ← 같은 시각 = 한 번에 되돌린 묶음
  units/
    jthread_worker/
      jthread_worker.20261112-110500.hpp
  20261112-103015/…                       ← 옛 형식, 건드리지 않음 (Assumption 5)
```
- **폴더 수**는 되돌린 적이 있는 레슨·유닛 수와 같다(사용자가 쓰는 만큼, 많아야 레슨 17개 + 유닛 몇 개). 시각 폴더처럼 계속 늘지 않는다.
- **파일 수**는 소유자마다 "소스 수 × 10"이 상한이다(레슨 소스는 1–5개이므로 10–50개). 이름순으로 파일별 묶음이 되고 그 안은 시각순이라 한 폴더에서 훑어볼 수 있다. 레슨 소스가 하위 폴더에 있으면 그 폴더가 소유자 폴더 안에 생긴다(지금 레슨은 모두 평평하다).
- **전체 크기**: 지금처럼 소스 몇 KB × 개수라 수 MB를 넘지 않는다. 지워진 레슨의 백업은 남는다(사용자가 지움; Out of Scope).
- 하위 폴더를 파일마다 두는 안(Assumption 3b)은 레슨당 파일 수가 지금보다 몇 배 늘어나 한 폴더가 보기 어려워지면 그때 바꾼다. 백업 규칙이 `_Backup` 한 곳에 있어 바꾸기 쉽다.

### 2.2 Public API Surface
`tools/practice.py`의 CLI와 `Workspace.reset()` 반환 모양(`{"reset": […], "backup": <폴더 또는 None>}`)은 그대로. 값만 소유자 폴더가 된다. HTTP 변경 없음. 이 스펙이 정하는 이름 규칙(Assumption 3)은 `practice.py`의 상수·함수로 둔다(예: 이름에서 소유 파일과 시각을 읽는 함수 하나를 정리와 테스트가 같이 쓴다).

### 2.3 Internal Implementation
| 파일 | 바꾸는 것 |
|---|---|
| [`tools/practice.py`](/tools/practice.py) | `_Backup`: 폴더를 한 번에 정하지 않고, `keep(path, move)`가 소유자 폴더(Assumption 6)와 파일 이름(Assumption 3)을 정해 복사 또는 이동하고 그 파일의 오래된 백업을 정리한다(Assumption 4). 한 번의 작업은 시각 하나(`_stamp()`를 작업 시작에 한 번). `finish()`는 이번 작업의 소유자 폴더를 돌려준다(Assumption 7). 모듈 머리 설명과 `KEEP_BACKUPS`의 뜻("파일마다")을 고친다. `_backup_order`는 이름 파서로 대체 |
| [`tools/test_practice.py`](/tools/test_practice.py) | 백업 위치·이름 확인으로 바꾸고, 파일별 보관, 같은 초 충돌, 유닛 폴더, 옛 폴더 무시를 더한다(AC) |
| [`web/server/test_server.py`](/web/server/test_server.py) | `body["backup"]` 아래에서 백업 파일을 찾는 두 곳(1435행 근처)을 새 이름 규칙에 맞춘다. `practice/backup/**` 쓰기 403 시험은 그대로 |
| 프런트엔드 | 변경 없음 (`backup`을 그대로 보임) |

### 2.4 Platform Specifics
none. 파일 이름에 `:` 등 Windows 금지 문자가 없다. 경로 구분자는 지금처럼 `/`로 다루고 `Path`가 변환한다.

## 3. C++ Standard Evolution
N/A.

## 4. Edge Cases
- [x] 같은 파일을 같은 초에 두 번 백업 — `-2`, `-3`. 번호는 "그 초에 이미 있는 번호의 다음"(정리로 빈 번호를 다시 쓰지 않음, 지금 규칙).
- [x] 시각순 정리의 정렬 — 시각 문자열 다음에 번호를 수로 비교한다(`-10`이 `-2`보다 뒤). 지금 `_backup_order`와 같은 이유.
- [x] 이름에 점이 여럿인 파일(`foo.bar.cpp`) — 백업 이름 `foo.bar.<시각>.cpp`에서 "마지막 시각 패턴"을 시각으로 읽는다. 원래 이름 안에 시각처럼 보이는 조각이 있어도 맨 끝 패턴만 본다.
- [x] 확장자가 없는 파일 — `<이름>.<시각>`. 소스에는 없지만 깨지지 않게.
- [x] 같은 소유자의 같은 이름이 다른 하위 폴더에 있음 — 상대 경로가 키의 일부라 따로 센다.
- [x] 정리가 방금 만든 백업을 지우지 않는다 — 방금 것이 가장 최근이므로 10개 안.
- [x] 유닛 사본을 쓰는 레슨이 여럿 — 유닛 폴더 하나. 어느 레슨에서 되돌렸는지는 남기지 않는다(유닛 사본은 레슨이 같이 쓰는 한 벌, 070-16 Assumption 3).
- [x] 카탈로그에 없는 소유자 — Assumption 6.
- [x] 옛 형식 폴더와의 공존 — Assumption 5. 새 코드는 `practice/backup/` 바로 아래의 시각 폴더를 읽지 않는다.
- [x] 같은 파일을 서버 요청 둘이 동시에 되돌림 — 다루지 않는다(지금과 같음, 로컬 한 사용자 도구).
- N/A Thread safety / memory ordering, template, ODR, UB — Python 도구라 해당 없음.

## 5. Acceptance Criteria
| ID | Criterion | Verified by |
|---|---|---|
| AC-1 | 레슨 되돌리기가 수정한 파일 둘을 `practice/backup/lessons/<id>/<이름>.<시각><확장자>`로 남기고, 내용은 되돌리기 전 수정본이며 두 이름의 시각이 같다. 반환 `backup`은 그 폴더다 | `tools/test_practice.py` |
| AC-2 | 유닛 되돌리기는 `practice/backup/units/<id>/`에 남기고, 레슨 되돌리기는 유닛 폴더를 만들거나 바꾸지 않는다. 레슨 id와 유닛 id가 같아도 섞이지 않는다 | `tools/test_practice.py` |
| AC-3 | 한 파일을 한 초 안에 12번 되돌리면 그 파일의 최근 10개(`-3`…`-12` 또는 시각순 10개)만 남고, 같은 폴더의 다른 파일의 백업 1개는 그대로 남는다 | `tools/test_practice.py` |
| AC-4 | 소스가 하위 폴더에 있는 레슨(시험용 임시 저장소)에서 백업이 소유자 폴더 안의 같은 상대 경로에 남는다. 이름에 점이 여럿이거나 확장자가 없는 파일도 정리 대상으로 올바르게 묶인다 | `tools/test_practice.py` |
| AC-5 | `practice/backup/` 바로 아래의 옛 형식 폴더(`20260101-000000/…`)가 되돌리기 뒤에도 그대로 있고(파일 수·내용), 정리 대상이 되지 않는다 | `tools/test_practice.py` |
| AC-6 | 자동 따라가기에서 원본에서 빠진 소스의 사본이 소유자 폴더로 이동한다(원래 위치에서는 사라진다) | `tools/test_practice.py` |
| AC-7 | `POST /api/practice/reset`의 `backup`이 `practice/backup/lessons/<id>`이고 그 아래에 백업 파일이 있다. 백업 폴더 아래 쓰기는 403이다 | `web/server/test_server.py` (`PlaygroundServer`) |
| AC-8 | 실제 저장소에서 레슨 하나의 파일 둘을 각각 세 번 고쳐 되돌린 뒤 `practice/backup/lessons/<id>/`에 6개가 보이고 `git status --porcelain`이 비어 있다(`practice/`는 git이 무시) | 실행 기록(`ls` 출력) |
| AC-9 | `lessons/README.md` "연습 공간"과 `tools/practice.py` 머리 설명이 새 구조를 설명하고, `lint_docs.py`가 exit 0이다. `tools/test_practice.py`, `PlaygroundServer`, 전체 suite(`windows-x64-debug`, `linux-x64-debug`), `npm --prefix web/frontend test`가 통과한다 | 명령 출력 |

## 6. Out of Scope
- 백업 목록·복원 명령(`practice.py backups`, `restore`), 페이지에서 백업 꺼내기 — 필요해지면 새 작업 (070-16이 "페이지에서 꺼내기"를 이미 제외)
- 지워진 레슨·유닛의 백업 폴더 정리, 총 용량 상한
- 옛 형식 폴더의 마이그레이션 또는 자동 삭제(Assumption 5)
- 진행 기록(`practice/progress.json`, 070-17)과 `state.json`의 모양

## 7. Dependencies & Backends
none.

## 8. Documentation Updates
| Document | Section | Change |
|---|---|---|
| [`docs/specs/070_16_practice_workspace.md`](/docs/specs/070_16_practice_workspace.md) | History / Amendments | 이 서브 스펙으로의 링크 한 줄(본문은 고치지 않음) |
| [`lessons/README.md`](/lessons/README.md) | "연습 공간" 되돌리기 항목 | 백업 위치(`practice/backup/lessons/<id>/`, `units/<id>/`), 이름 규칙, 파일마다 최근 10개, 옛 형식 폴더는 지워도 됨 |
| [`web/README.md`](/web/README.md) | 연습 공간이 언급되는 곳 | 백업 경로가 적혀 있으면 새 경로로 |
| `tools/practice.py` | 모듈 머리 설명 | 새 보관 규칙 |
| [`docs/agent_todo.md`](/docs/agent_todo.md) | 070-16-01 줄 | 상태 |

## 9. Technical Constraints
- Python 3 표준 라이브러리만 (`tools/practice.py`의 지금 의존과 같음)
- 외부 의존 없음, C++ 변경 없음

## 10. Context & References
- [070-16 스펙](/docs/specs/070_16_practice_workspace.md) Assumption 8, §2.2, AC-4
- [`tools/practice.py`](/tools/practice.py) `_Backup`, `Workspace.reset`, `Workspace._follow`
- [`tools/test_practice.py`](/tools/test_practice.py) `test_06`, `test_07`, `test_11`
- [`web/server/test_server.py`](/web/server/test_server.py) (reset와 백업 시험)
- 이 작업의 계기: `practice/backup/`에 같은 레슨의 폴더 10개 (사용자 관찰, 2026-11-12)

## 11. Implementation Plan
- [ ] Step 1: 이름 규칙 함수(만들기·읽기)와 소유자 폴더 결정, 단위 시험
- [ ] Step 2: `_Backup`을 새 규칙으로 바꾸고 `reset`, `_follow`의 호출을 맞춤
- [ ] Step 3: `test_practice.py`, `test_server.py` 갱신
- [ ] Step 4: 문서(`lessons/README.md`, `web/README.md`, 모듈 머리 설명, 070-16 History)
- [ ] Step 5: 실제 저장소 확인(AC-8), 전체 시험

## 12. Verification Plan
- [ ] `py -3 tools/test_practice.py`
- [ ] `py -3 -m unittest web/server/test_server.py` 또는 CTest `PlaygroundServer`
- [ ] `npm --prefix web/frontend test`
- [ ] `py -3 .agent/scripts/build.py --preset windows-x64-debug --test`, `--preset linux-x64-debug`
- [ ] `py -3 .agent/scripts/lint_docs.py` exit 0
- [ ] 모든 AC 행의 증거가 `testrecord.md`에 (이 서브 스펙의 새 산출물 폴더)

## History / Amendments
- 2026-11-12: 초안
- 2026-11-12: 승인(사용자)
- 2026-11-12 (DEV, Assumption 6의 예외 하나): 소유자를 카탈로그에서도, 사본 폴더 이름에서도 구할 수 없는 경로(`practice/lessons/tracks/…`, `practice/lessons/units/…` 모양이 아님)는 `PracticeError`를 낸다. 이런 경로는 `state.json`을 손으로 고쳐야만 생기고, 대신 만들 소유자 이름은 근거가 없는 값이 된다. `reset --file`이 기록되지 않은 경로에 오류를 내는 것과 같다. 시험: `test_20`
- 2026-11-12 (DEV, 한계): 확장자가 없고 이름이 시각처럼 보이는 조각으로 끝나는 파일(`x.20250101-000000`)은 "맨 끝 패턴이 시각"이라는 §4의 규칙 때문에 다른 파일로 묶인다. 레슨 소스에는 없는 모양이라 고치지 않는다
- 2026-11-12 (DEV, 동작 변화 없음): 정리는 방금 만든 백업을 후보에서 뺀다(시계를 뒤로 돌려 그 시각이 가장 오래돼 보여도 지워지지 않음, §4 "정리가 방금 만든 백업을 지우지 않는다"를 시계가 앞으로만 간다는 가정 없이 지킴). 시험: `test_21`

