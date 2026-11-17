---
id: 070-26
title: 레슨 순서를 매니페스트로 옮기고 폴더 번호 제거
depends_on: [070-25]
unblocks: [070-27, 070-22, 070-23, 070-24]
approved: 2026-11-16
---

# Spec 070-26: 레슨 순서를 매니페스트로 옮기고 폴더 번호 제거

## 0. Assumptions (please review)
| # | Decision | Rejected alternative | Why |
|---|---|---|---|
| 1 | **폴더 번호를 없앤다**(사용자 결정 2026-11-16). 트랙 폴더는 `lessons/tracks/<트랙 id>/`, 레슨 폴더는 `lessons/tracks/<트랙 id>/<레슨 id>/`: `01_essentials/01_lambda_capture` → `essentials/lambda_capture`, `03_oop_basics/04_inheritance_virtual` → `oop_basics/inheritance_virtual` | 번호는 두고 매니페스트의 순서가 우선 | 번호와 실제 순서가 어긋난 채 남으면 더 헷갈린다 |
| 2 | **순서는 파일 하나 `lessons/curriculum.toml`에 둔다**: 트랙의 순서와 트랙 안 레슨의 순서를 함께. `track.toml`은 지금처럼 제목과 요약만 갖는다(§2.1) | (a) 트랙마다 `track.toml`에 `lessons = […]`, 트랙 순서는 다른 곳에; (b) 레슨마다 `lesson.toml`에 `order = 30` | (a) 순서가 네 파일에 흩어지고 트랙 순서를 둘 곳이 또 필요하다. (b) 끼워 넣을 때 다른 레슨의 숫자를 고쳐야 해서 폴더 번호와 같은 문제다. 한 파일이면 커리큘럼 전체를 한 화면에서 보고 줄을 옮겨 순서를 바꾼다 |
| 3 | **레슨 폴더 이름은 `id`와 같아야 한다**(유닛은 이미 그렇다). 다르면 `lessons.py check`가 ERROR. 트랙 id는 폴더 이름이고 `[a-z0-9_]+`이며 숫자로 시작하지 않는다 | 폴더 이름과 id를 따로 둠 | id 하나로 폴더, CMake 타깃 `lesson_<id>`, 연습 기록, 백업 폴더가 모두 정해진다. 찾을 때 이름이 하나다 |
| 4 | **목록에 없는 레슨은 그 트랙의 끝에 폴더 이름순으로 붙고 WARN**이다. 목록에 있는데 폴더가 없거나, 두 번 나오거나, 폴더가 다른 트랙에 있으면 ERROR. `curriculum.toml`에 없는 트랙 폴더는 맨 뒤에 붙고 WARN | 목록에 없으면 ERROR | 폴더를 만들자마자 빌드되고 페이지에 보여야 쓰면서 확인할 수 있다. 자리를 정하는 일은 한 줄을 더하는 것이고, 잊으면 문서 gate의 경고로 보인다(WARN은 gate를 막지 않는다) |
| 5 | **레슨을 다른 트랙으로 옮기는 일은 여전히 폴더 이동**이다(`git mv` + 목록 두 줄). 이 작업은 트랙 안의 순서와 끼워 넣기를 자유롭게 한다 | 레슨을 `lessons/<id>/`로 평평하게 두고 트랙은 목록에만 | 트랙 폴더는 22개(곧 40개 이상)의 레슨을 탐색기에서 묶어 준다. 트랙 사이 이동은 드물다. CMake glob과 연습 사본 경로의 깊이도 그대로 둔다 |
| 6 | **CMake는 바꾸지 않는다.** `lessons/CMakeLists.txt`는 `tracks/*/*/lesson.toml`을 찾고 순서를 쓰지 않는다. 타깃과 테스트 이름(`lesson_<id>`, `lesson.<id>`)도 그대로다 | CMake가 `curriculum.toml`을 읽음 | 빌드에는 순서가 필요 없다 |
| 7 | **링크는 lint가 ERROR로 보는 모든 파일에서 고친다**: 살아 있는 문서(`lessons/`, `docs/cpp_evolution/`, `docs/lesson_candidates.md`, `tests/README.md` 등 약 34개 파일 248곳), 그리고 끝난 작업의 spec(`docs/specs/`, 15개 파일)과 `docs/archive/`(1개)의 **링크 대상 경로만**. 끝난 spec의 본문에 글로 적힌 옛 폴더 이름(`11_thread_and_log`)은 그때의 기록이므로 두고, 이 spec이 그 예외("끝난 spec은 고치지 않는다", [spec.md](/.agent/rules/spec.md) §4)의 근거다. 봉인된 작업 폴더(`docs/tasks/`, 14개 파일)는 건드리지 않는다(깨진 링크는 lint에서 INFO) | (a) 끝난 spec도 봉인으로 보고 lint를 느슨하게; (b) spec마다 History 줄 추가 | (a) spec의 링크는 지금도 읽히는 길이고, lint 예외를 넓히면 진짜 깨진 링크가 숨는다. (b) 15개 파일에 같은 줄을 더하는 것은 정보가 없다 |
| 8 | **옮기기는 표 하나(옛 경로 → 새 경로)와 한 번 쓰는 스크립트로 한다**: `git mv`(이력 유지), 링크 치환, 로컬 연습 공간(`practice/lessons/tracks/…` 사본 이동, `practice/state.json`의 키와 `origin` 치환). 스크립트는 `tools/`에 두지 않고 작업 산출물 폴더(`docs/tasks/feature_070-26-…/`)에 기록으로 남긴다 | (a) `tools/practice.py migrate` 명령; (b) 연습 사본은 버리고 다시 만들기 | (a) 한 번 쓰고 죽는 코드가 도구에 남는다(070-16-01 Assumption 5와 같은 판단). (b) 사용자가 고친 사본(`modified`)이 사라진다. 진행 기록(`progress.json`)과 백업(`practice/backup/lessons/<id>/`)은 id가 키라 그대로다 |
| 9 | **페이지는 `index.json`의 순서를 그대로 쓴다**(지금과 같음). 프런트엔드 코드는 바꾸지 않는다. 트리의 접힘 상태는 트랙 id가 바뀌어 한 번 초기화된다 | 접힘 상태 옮기기 | 브라우저에 저장된 편의 값 세 개다 |
| 10 | **지금의 순서를 그대로 옮긴다.** `curriculum.toml`의 첫 내용은 지금 폴더 번호순과 같고(트랙 3개, 레슨 22개), 순서를 바꾸는 일은 이 작업에 없다 | 이참에 순서 조정 | 옮기기 전후의 `index.json` 순서가 같다는 것이 이 작업의 검증이다(AC-2) |
| 11 | **`docs/lesson_candidates.md`의 "폴더" 열은 레슨 id가 되고**, "새 레슨은 끝 번호 다음에, 순서 변경은 폴더 이동이라 사용자 결정"이라는 규칙과 OOP 트랙의 비워 둔 번호(`05_`–`07_`)를 지운다. 후보의 예정 순서는 표의 행 순서로 본다 | 표에 순서 번호 열 유지 | 순서의 원본은 `curriculum.toml` 하나다 |

## 1. Objective
레슨의 순서가 폴더 이름(`NN_`)에 들어 있어서, 레슨을 끼워 넣거나 순서를 바꾸려면 폴더를 옮기고 번호 붙은 경로를 가리키는 링크(지금 34개 파일 248곳)를 고쳐야 한다. 그래서 지금 규칙은 "새 레슨은 끝 번호에만"이고, OOP 트랙은 후속 레슨의 번호를 미리 비워 두었다. OOP 후속 3개, 패턴 14개, 엔진 레슨이 더해지기 전에 순서를 매니페스트 한 곳으로 옮겨, 순서 변경이 한 줄 이동이 되게 한다.

## 2. Requirement Details

### 2.1 `lessons/curriculum.toml`
```toml
# 트랙의 순서와 트랙 안 레슨의 순서. 폴더 이름은 순서를 정하지 않는다.
# 레슨을 더하면 그 트랙의 lessons에 id를 넣는다 (없으면 트랙 끝에 붙고 check가 경고).

[[track]]
id = "essentials"
lessons = [
  "lambda_capture",
  "format_text",
  # …
  "testing",
]

[[track]]
id = "patterns"
lessons = ["device_state_machine"]

[[track]]
id = "oop_basics"
lessons = ["class_basics", "object_lifetime", "copy_and_move", "inheritance_virtual"]
```
- `[[track]]`의 순서가 트랙 순서, `lessons`의 순서가 레슨 순서다.
- 파일이 없거나 TOML이 깨졌으면 ERROR이고, 순서는 폴더 이름순으로 대신한다(인덱스는 계속 만들어져 페이지가 열린다).

### 2.2 폴더 구조
```text
lessons/
  curriculum.toml             순서 (새 파일)
  tracks/<트랙 id>/track.toml  제목, 요약 (그대로)
  tracks/<트랙 id>/<레슨 id>/  lesson.toml, README.md, README.en.md, exercises.toml, 소스
  units/<유닛 id>/             그대로
practice/lessons/tracks/<트랙 id>/<레슨 id>/   연습 사본 (원본 경로를 비춤, 그대로)
```

### 2.3 Internal Implementation
| 파일 | 바꾸는 것 |
|---|---|
| `lessons/curriculum.toml` [NEW] | Assumption 10의 내용 |
| `lessons/tracks/**` | 트랙 3개, 레슨 22개 폴더 이름(`git mv`) |
| [`tools/lessons.py`](/tools/lessons.py) | `load()`가 `curriculum.toml`을 읽어 트랙과 레슨을 그 순서로 싣는다. 검사: Assumption 3, 4. `index`의 출력 모양(`version`, `tracks[].lessons[]`, `path`)은 그대로이고 값만 새 경로다 |
| [`tools/test_lessons.py`](/tools/test_lessons.py) | 순서, 목록 오류, 폴더 이름 검사의 테스트. 번호 붙은 픽스처 이름 정리 |
| `tools/test_exercises.py`, `tools/test_practice.py`, `web/server/test_server.py`, `.agent/scripts/test_agent_scripts.py`, `web/frontend/test/*.ts` | 픽스처가 레슨 폴더 이름 ≠ id이면 고친다. 실제 레슨 경로를 쓰는 곳은 새 경로로 |
| 문서 | §8 |
| 로컬 `practice/` | Assumption 8의 스크립트로 한 번 옮김 (저장소 밖 상태, 커밋 없음) |

바꾸지 않는 것: `lessons/CMakeLists.txt`, `web/server/`, `web/frontend/src/`, `tools/practice.py`, `tools/exercises.py`(모두 카탈로그와 인덱스의 경로를 받아 쓴다. 구현 중 번호에 기대는 코드가 나오면 그 파일을 이 표에 더하고 plan에 적는다).

### 2.4 Platform Specifics
none. Windows와 WSL이 같은 체크아웃을 보므로 폴더 이동은 한 번이다. 빌드 폴더(`out/build/<preset>`)는 다음 configure가 새 경로를 찾는다(glob `CONFIGURE_DEPENDS`). 옮긴 뒤 두 호스트에서 한 번씩 빌드해 확인한다.

## 3. C++ Standard Evolution
N/A.

## 4. Edge Cases
- [x] Thread safety, RAII, 템플릿, ODR, UB: N/A (C++ 코드 변경 없음).
- [x] Platform differences: §2.4. Windows는 대소문자를 가리지 않으므로 id는 지금처럼 소문자만.
- [x] 목록과 폴더의 불일치: Assumption 4의 네 경우 모두 테스트(AC-4).
- [x] 레슨 id와 유닛 id가 같은 경우(`lambda_capture`): 폴더가 `tracks/`와 `units/`로 갈라져 있어 겹치지 않는다. 지금도 허용된다.
- [x] 옮기는 중간 상태: 폴더 이동, `curriculum.toml`, 링크 치환을 한 커밋으로 한다. 중간 커밋에서 lint가 깨지지 않게.
- [x] 연습 공간에 고친 사본이 있는 경우: 옮기기 전후의 `practice.py status`가 같아야 한다(AC-7). `state.json`이 없거나 사본이 없으면 스크립트는 그 단계를 건너뛴다.
- [x] 열려 있는 플레이그라운드 서버나 빌드: 옮기기 전에 끈다(Windows에서 열린 파일은 이동이 실패한다). 스크립트는 실패하면 아무것도 바꾸지 않은 상태로 멈춘다(먼저 모든 대상의 존재와 충돌을 확인한 뒤 이동).
- [x] 다른 브랜치의 옛 경로: 열린 기능 브랜치가 없다(모두 병합됨). 이 작업은 다른 작업과 겹치지 않게 혼자 진행한다.

## 5. Acceptance Criteria
| ID | Criterion | Verified by |
|---|---|---|
| AC-1 | `lessons/tracks/` 아래에 숫자로 시작하는 폴더가 없고, 모든 레슨 폴더 이름이 그 `id`와 같다 | `py -3 tools/lessons.py check` 오류 0, 폴더 목록 |
| AC-2 | 옮기기 전과 후의 `lessons.py index`에서 트랙 id(번호를 뗀 것)와 레슨 id의 순서가 같고, 레슨 수(22)와 유닛 수(2)가 같다 | 전후 `index.json`의 id 순서 비교(testrecord) |
| AC-3 | `curriculum.toml`에서 두 레슨 id의 자리를 바꾸면 다른 파일을 고치지 않고 인덱스의 순서가 바뀐다. 새 레슨을 목록 가운데에 넣으면 그 자리에 나온다 | `tools/test_lessons.py`의 새 테스트 |
| AC-4 | 목록에 있는데 없는 레슨, 중복, 다른 트랙의 레슨, 폴더 이름 ≠ id는 ERROR. 목록에 없는 레슨과 트랙은 WARN이고 끝에 나온다. `curriculum.toml`이 없으면 ERROR이고 폴더 이름순 | `tools/test_lessons.py`의 새 테스트 |
| AC-5 | 봉인되지 않은 파일에 번호 붙은 레슨 경로가 없고 문서 gate가 통과한다 | `git grep -E "tracks/[0-9]{2}_" -- . ":!docs/tasks"` 결과 0줄(끝난 spec 본문의 글은 경로 형태가 아님), `py -3 .agent/scripts/lint_docs.py` exit 0 |
| AC-6 | 두 호스트에서 전체 빌드와 테스트가 통과한다: 레슨 22개의 `lesson.<id>`와 `exercises_verify`, 도구·서버·프런트엔드 테스트 | `build.py --preset windows-x64-debug --test --report`, `linux-x64-debug` 같은 명령, `npm --prefix web/frontend test` |
| AC-7 | 로컬 연습 공간: 옮기기 전후에 `py -3 tools/practice.py status`의 파일별 상태(`same`/`modified`/`both`)가 같고 `missing-origin`이 없다. `progress.json`은 바뀌지 않는다 | 전후 출력 비교(testrecord) |
| AC-8 | 플레이그라운드에서 트리의 순서가 전과 같고, 레슨 하나를 연습 모드로 열어 Run하면 과제 확인까지 된다. README 사이의 링크가 열린다 | `tools/test_playground.py`, 서버 테스트 + 수동 확인 한 번(사용자) |

## 6. Out of Scope
- 레슨·유닛 뼈대 생성 명령과 목록 자동 등록: 070-27.
- 페이지에서 순서를 끌어 바꾸기, 트리에 순서 번호 보이기: 요청이 생기면 새 작업.
- 레슨을 트랙 없이 평평하게 두기(Assumption 5): 트랙 사이 이동이 잦아지면 다시 본다.
- 순서 자체의 변경: 이 작업 뒤에는 `curriculum.toml`의 한 줄 이동이다.

## 7. Dependencies & Backends
none.

## 8. Documentation Updates
| Document | Section | Change |
|---|---|---|
| [`lessons/README.md`](/lessons/README.md) | 구조, 매니페스트, 새 레슨 추가, 연습 공간의 경로 예 | `curriculum.toml`, 번호 없는 폴더, "폴더 이름 = id", 순서를 바꾸는 법. "새 레슨은 마지막 번호 다음" 문장 삭제 |
| [`docs/lesson_candidates.md`](/docs/lesson_candidates.md) | 머리말, 세 트랙 표 | Assumption 11 |
| `lessons/intro.md`, `intro.en.md`, 레슨·유닛 README(두 언어), `exercises.toml`의 링크 | 링크 | 새 경로 |
| `docs/cpp_evolution/*.md`(24개), `docs/cpp_evolution.md`, `.en.md`, [`tests/README.md`](/tests/README.md), [`web/README.md`](/web/README.md) | 레슨 링크 | 새 경로 |
| `docs/specs/`(15개), `docs/archive/`(1개) | 링크 대상만 | Assumption 7 |
| [`docs/agent_todo.md`](/docs/agent_todo.md) | 070-22 ~ 070-24의 줄 | 폴더 이름 표기 확인(이미 id로 적음) |

## 9. Technical Constraints
- Python 3.11+ (`tomllib`), CMake 4.0+
- 두 호스트(Windows, WSL)가 같은 체크아웃을 쓴다

## 10. Context & References
- [070-01 레슨 구조](/docs/specs/070_01_lesson_structure.md), [070-03](/docs/specs/070_03_essentials_curriculum.md)(폴더 번호 = 최종 순서), [070-14](/docs/specs/070_14_essentials_modules_lesson.md) Assumption 2(끝 번호에 붙이기), [070-21](/docs/specs/070_21_oop_basics_track.md)(비워 둔 번호)
- [070-16](/docs/specs/070_16_practice_workspace.md), [070-16-01](/docs/specs/070_16_01_backup_by_owner.md): 연습 사본 경로, id 기준 백업
- [tools/lessons.py](/tools/lessons.py), [lessons/CMakeLists.txt](/lessons/CMakeLists.txt), [lint_docs.py](/.agent/scripts/lint_docs.py)(봉인 폴더의 링크는 INFO)

## 11. Implementation Plan
- [ ] U1: `lessons.py` — `curriculum.toml` 읽기, 순서, 검사 (번호 폴더에서도 도는 상태로: 목록이 폴더 이름을 id로 찾기 전 단계의 테스트 포함)
- [ ] U2: `test_lessons.py` 새 테스트(AC-3, AC-4)와 픽스처
- [ ] U3: 옮기기 표와 스크립트(산출물 폴더), 모의 실행으로 대상·충돌 확인 (Risky)
- [ ] U4: 옮기기 실행 한 커밋: `git mv`, `curriculum.toml`, 링크 치환, 나머지 테스트 픽스처
- [ ] U5: 로컬 `practice/` 옮기기, 전후 `status` 비교
- [ ] U6: 문서(§8의 글 부분), KI 없음 확인, gate

## 12. Verification Plan
- [ ] 옮기기 전: `lessons.py index` 저장, `practice.py status` 저장
- [ ] `py -3 tools/lessons.py check`, `py -3 -m unittest`(tools, `.agent/scripts`, `web/server`)
- [ ] `py -3 .agent/scripts/build.py --preset windows-x64-debug --test --report`, WSL에서 `linux-x64-debug`
- [ ] `npm --prefix web/frontend test`, `py -3 tools/test_playground.py`
- [ ] `py -3 .agent/scripts/lint_docs.py`
- [ ] AC-8의 수동 확인(사용자)

## History / Amendments
