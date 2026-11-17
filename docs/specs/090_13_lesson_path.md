---
id: 090-13
title: 레슨 경로 (트랙 spec 한 번 승인, 레슨 하나는 체크리스트로 완료)
depends_on: [070-27]
unblocks: [070-22, 070-23, 070-24]
approved: 2026-11-17
---

# Spec 090-13: 레슨 경로 (트랙 spec 한 번 승인, 레슨 하나는 체크리스트로 완료)

## 0. Assumptions (please review)
| # | Decision | Rejected alternative | Why |
|---|---|---|---|
| 1 | **레슨 경로를 쓰는 작업은 바뀌는 파일로 정한다**(§2.1 표). 레슨 폴더, 그 레슨만 쓰는 새 유닛, `curriculum.toml`의 그 레슨 줄, `tags.toml`에 더하는 태그, 다른 레슨 README의 링크 한 줄, 트랙 목록 문서와 `lesson_candidates.md`, `agent_todo.md`만 바뀌면 레슨 경로다. `include/`, `src/`, `modules/`, `tests/`, `tools/`, `web/`, CMake, 기존 유닛을 건드리면 지금의 전체 경로다 | (a) 작업 종류(그룹 번호 070)로 정함; (b) lead가 그때그때 판단 | (a) 070 그룹에는 도구·웹 작업(070-26, 070-27)도 있다. (b) 규칙 3을 푸는 범위가 사람마다 달라진다. 파일 목록이면 diff로 확인할 수 있다 |
| 2 | **패턴 작업(021–024)과 엔진 작업(060)은 레슨이 있어도 전체 경로다.** 헤더, Tracer 연결, 시나리오 테스트가 함께 바뀌기 때문이다(작업 공통 원칙). 그 작업의 레슨 부분도 그 작업의 spec이 정한다 | 레슨 부분만 떼어 레슨 경로로 | 한 기능의 헤더와 레슨이 다른 승인 아래 있으면 서로 어긋나도 아무도 보지 않는다 |
| 3 | **트랙 spec은 `docs/specs/tracks/<track>.md`** 파일 하나다. frontmatter는 `track: <트랙 id>`, `approved: <날짜>|null`, `tasks: [NNN-SS, …]`(이 트랙 spec 아래의 레슨 작업). 작업 spec(`NNN_SS_*.md`)과 달리 **고쳐 쓰는 문서**다: 행을 더하거나 규칙을 바꾸면 사용자 승인으로 `approved` 날짜를 새로 쓰고 `## History`에 한 줄을 남긴다 | (a) 트랙마다 `NNN_SS` 작업 spec; (b) `lessons/tracks/<track>/` 안에 둠 | (a) 작업 spec은 작업 하나의 id를 갖고 DONE이면 봉인된다(spec.md §4). 트랙은 레슨이 늘 때마다 바뀐다. (b) 그 폴더는 플레이그라운드가 읽고 CMake glob이 돈다. 승인 기록은 `docs/specs/`에 모은다 |
| 4 | **트랙 spec이 정하는 것**: 독자, 레슨 형식(첫 절의 비교 방식), 공통 규칙(UB를 돌리지 않음, 출력 안정성, 과제의 자동·관찰 기준, 언어, evolution 페이지를 쓸지), 커리큘럼 표(작업 ID, 레슨 id, 주제, 비교 한 줄, 선행 레슨, 상태). **단계 구성과 과제 목록은 정하지 않는다**: 레슨마다 lead가 체크리스트의 "설계" 절에 쓴다 | 레슨마다 단계·과제 초안까지 트랙 spec에 | 단계까지 미리 승인받으면 레슨마다 승인받는 지금과 같다. 사용자가 정하는 것은 "무엇을 어떤 방식으로 가르치나"이고, 몇 단계로 보일지는 레슨을 쓰며 정하는 편이 낫다(070-21에서도 초안 과제 하나가 실제 실행으로 바뀌었다) |
| 5 | **레슨 작업의 todo 줄은 트랙 spec에 링크**하고(§2.3), **`SPEC_DRAFT`를 거치지 않는다**: 트랙 spec이 승인되고 `tasks`에 그 ID가 있으면 `BACKLOG`에서 바로 `APPROVED`가 된다. 그 뒤 `DEV` → `TEST` → `DONE`은 지금과 같다 | 레슨 작업도 짧은 spec 파일 | 짧은 spec도 승인을 기다리는 단계다. 이 작업이 없애려는 것이 그 대기다 |
| 6 | **레슨 작업의 기록은 `checklist.md` 하나**다(`docs/tasks/feature_NNN-SS-<slug>/checklist.md`, 템플릿 `docs/specs/tracks/00_lesson_checklist.md`). 절은 설계(단계, 과제와 자동·관찰 분류, 트랙 spec 행과 다른 점), 체크리스트(§2.4, 항목마다 근거), 리뷰, 후속(KI). `plan.md`, `testrecord.md`, `walkthrough.md`를 대신한다 | 세 파일 유지 | 070-21의 세 파일은 대부분 같은 표(파일 목록, 빌드 결과, 과제 표)를 다른 모양으로 되풀이했다. 레슨 하나에는 한 곳이면 읽기 쉽다 |
| 7 | **체크리스트 항목은 고정**(§2.4)이고 모두 기계 근거(명령과 결과) 또는 리뷰 기록이다. 하나라도 `- [ ]`로 남거나 근거가 비면 `DONE`이 아니다. 항목이 맞지 않는 레슨(예: GoogleTest 레슨의 출력 비교)은 지우지 않고 `N/A: <이유>`로 체크한다 | 레슨마다 항목을 고름 | 고르면 빠진 항목이 눈에 안 띈다. 템플릿 하나를 고치면 다음 레슨부터 같이 바뀐다 |
| 8 | **병합은 체크리스트가 다 차면 묻지 않고 한다**(merge policy, 2026-10-28). 레슨마다 사용자가 페이지를 보고 승인하는 단계는 두지 않는다. 사용자는 `main`에서 언제든 보고, 고칠 곳은 KI나 다음 레슨 작업으로 온다 | 병합 전 사용자 확인 | 레슨마다 손 확인을 두면 승인 대기가 끝으로 옮겨갈 뿐이다. 트랙 spec 승인이 내용 방향을, 체크리스트가 품질을 맡는다 |
| 9 | **레슨 경로를 벗어나는 변경이 필요해지면 멈춘다**: 라이브러리·도구·웹 변경이 필요하면 그 부분을 새 작업(전체 경로)이나 KI로 등록하고 레슨 작업은 `BLOCKED`(이유, 해제 조건)로 둔다. 트랙 spec 행과 다른 주제·순서·새 레슨이 필요하면 트랙 spec을 고쳐 사용자 승인을 받는다. 레슨 안의 설계(단계, 과제, 글)는 lead가 정하고 체크리스트 "설계" 절에 남긴다 | 레슨 작업 안에서 같이 고침 | 규칙 3을 푸는 범위가 Assumption 1의 파일 목록 밖으로 새지 않게 한다 |
| 10 | **누가 쓰나는 지금 규칙(delegation.md §1)대로**: 레슨 코드는 몇십 줄이고 README와 함께 쓰므로 보통 `lead (small)`, 글은 lead, 첫 리뷰는 fresh reviewer(`cpp-reviewer`) 한 번(§6.3). 체크리스트의 리뷰 항목이 그 기록이다 | 레슨 경로 전용 위임 규칙 | 070-21에서 쓴 방식이고, 다르게 할 까닭이 없다 |
| 11 | **첫 트랙 spec은 `oop_basics`**이고 이 작업이 쓴다. 내용은 [070-21](/docs/specs/070_21_oop_basics_track.md)에서 이미 승인된 것(Assumption 2, 4, 5, 6, 8, 9, 10, 11과 §2.1 표)을 옮기고, `tasks: [070-22, 070-23, 070-24]`. 070-21은 고치지 않는다(봉인된 작업 spec). 파일은 `approved: null`로 만들고 **이 작업의 마지막에 사용자가 승인한다**(AC-7, 손 확인이므로 병합 전에 묻는다) | (a) 이 spec의 승인으로 트랙 spec도 승인된 것으로; (b) 070-21에 frontmatter를 더함 | (a) 사용자가 아직 보지 않은 파일을 승인한 것이 된다. 옮겨 적는 중에 바뀐 글이 있을 수 있다. (b) 봉인된 spec을 고치게 된다 |
| 12 | **essentials와 patterns는 지금 트랙 spec을 만들지 않는다.** essentials 후보는 모두 레슨이 있고, patterns 레슨은 패턴 작업이 만든다(Assumption 2). 새 essentials 레슨이 필요해지면 그때 트랙 spec을 먼저 쓴다 | 세 트랙 모두 지금 | 쓸 작업이 없는 트랙 spec은 승인할 내용이 없다 |
| 13 | **트랙 spec이 그 트랙 커리큘럼의 원본**이 된다. [`lesson_candidates.md`](/docs/lesson_candidates.md)의 OOP 절은 표를 지우고 트랙 spec 링크 한 줄로 바꾼다. 레슨 순서의 원본은 여전히 [`curriculum.toml`](/lessons/curriculum.toml)(070-26)이다 | 두 곳에 같은 표 | 같은 표가 두 곳이면 하나만 고쳐진다 |
| 14 | **문서 gate가 레슨 경로를 검사한다**(§2.5): 트랙 spec frontmatter, todo 줄과 `tasks`의 양쪽 일치, 승인 상태, `DONE` 레슨 작업의 `checklist.md`에 빈 칸 없음 | 사람이 지킴 | 규칙 3을 푸는 대신 기계가 그 경계를 본다. 지금의 spec 승인 검사(`check_specs`)와 같은 자리다 |

## 1. Objective
규칙 3("승인된 spec 없이 구현 없음")은 레슨 하나에도 spec 한 편과 승인 대기를 요구한다. A3 다음에는 OOP 후속 3개, 그 뒤 엔진·패턴 레슨이 이어지는데, 레슨의 방향(독자, 형식, 규칙, 커리큘럼)은 트랙마다 한 번 정하면 되고 레슨마다 다시 승인받을 것이 거의 없다. 이 작업은 **트랙 spec 한 번의 승인으로 그 트랙의 레슨 작업을 시작할 수 있게** 규칙 3을 레슨에 한해 풀고, 그 대신 레슨 하나는 **고정된 체크리스트를 모두 채워야 완료**되게 한다. 경계(어떤 파일까지가 레슨인지, 승인 상태)는 문서 gate가 검사한다. 사용자 결정 2026-11-16.

## 2. Requirement Details

### 2.1 레슨 경로의 범위 (Assumption 1)
| 바꿔도 되는 것 | 조건 |
|---|---|
| `lessons/tracks/<track>/<id>/` | 그 레슨 작업의 레슨 폴더 |
| `lessons/units/<new>/` | 이 작업이 새로 만들고 이 레슨만 쓰는 유닛 |
| [`lessons/curriculum.toml`](/lessons/curriculum.toml) | 그 레슨의 줄(`lessons.py new`가 넣음) |
| [`lessons/tags.toml`](/lessons/tags.toml) | 태그 추가, 별칭 추가·이동 |
| 다른 레슨의 `README.md`, `README.en.md` | 이 레슨으로 가는 링크 줄 |
| [`lessons/README.md`](/lessons/README.md), [`lessons/intro.md`](/lessons/intro.md), [`intro.en.md`](/lessons/intro.en.md), [`docs/lesson_candidates.md`](/docs/lesson_candidates.md) | 트랙·레슨 목록 |
| 트랙 spec | 상태 열(`후보` → `레슨 있음`). 그 밖의 변경은 사용자 승인(Assumption 9) |
| [`docs/agent_todo.md`](/docs/agent_todo.md), `docs/known_issues*.md`, `docs/archive/*` | 상태, KI, 보관 |
| `docs/tasks/feature_NNN-SS-<slug>/checklist.md` | 기록 |

이 밖의 파일이 diff에 있으면 레슨 경로가 아니다(체크리스트 항목 C1이 `git diff --stat main...`으로 확인).

### 2.2 트랙 spec 파일
```markdown
---
track: oop_basics
approved: 2026-11-17          # YYYY-MM-DD, 사용자가 승인할 때마다 새로 씀
tasks: [070-22, 070-23, 070-24]
---

# Track spec: OOP 입문 (`oop_basics`)

## 0. Assumptions (please review)      ← 독자, 형식, 공통 규칙 (작업 spec과 같은 표)
## 1. 독자와 목표
## 2. 레슨 형식                         ← 첫 절 제목, 단계 머리줄, 출력, 언어
## 3. 공통 규칙                         ← UB, 출력 안정성, 과제 자동·관찰 기준, evolution 페이지, 태그
## 4. 커리큘럼
| 작업 | 레슨 id | 주제 | 흔한 실수 → 바른 방식 | 선행 | 상태 |
## 5. Out of Scope
## History                             ← 승인마다 한 줄: 날짜, 바뀐 것
```
템플릿은 `docs/specs/tracks/00_template.md`(새 파일). 이미 있는 레슨(작업 ID가 legacy·DONE인 것)은 표에서 작업 열에 그 작업 ID(`070-21`)를 쓰고 `tasks`에는 넣지 않는다.

### 2.3 상태와 todo 줄 (Assumption 5)
- 레슨 작업 줄: `- !<STATE> | NNN-SS | [<제목>](/docs/specs/tracks/<track>.md)`.
- `BACKLOG`: 트랙 spec이 아직 승인되지 않았거나 행만 있는 상태.
- 트랙 spec이 승인되면 `tasks`의 작업은 lead가 `APPROVED`로 올린다. `SPEC_DRAFT`는 쓰지 않는다.
- `DEV`에서 `checklist.md`를 만들고 "설계" 절부터 쓴다. `TEST`에서 체크리스트를 채운다. 모두 체크되면 `DONE`, 병합(Assumption 8).

### 2.4 체크리스트 (`00_lesson_checklist.md`의 항목, Assumption 7)
| # | 항목 | 근거 |
|---|---|---|
| C1 | 바뀐 파일이 §2.1 표 안에 있다 | `git diff --stat main...` |
| C2 | 설계 절이 트랙 spec 행(주제, 비교)과 맞고, 다른 점은 적혀 있다. 트랙 spec을 고칠 일이면 멈췄다(Assumption 9) | 설계 절 |
| C3 | `lessons.py check`: ERROR 0, 이 레슨·유닛에 WARN 0(`[scaffold]` 포함) | 명령 출력 |
| C4 | `lesson_<id>`가 `windows-x64-debug`와 `linux-x64-debug`에서 경고 없이 빌드된다 | `build.py --preset <p> --target lesson_<id>` |
| C5 | 두 OS의 출력이 같다(줄 끝 제외). 주소·시간·해시 없음 | 두 실행의 비교 |
| C6 | `--label lesson`이 두 preset과 `linux-x64-asan`에서 통과한다(`lesson.<id>`, `lesson.<id>.exercises_verify`) | `build.py --preset <p> --test --label lesson --report` |
| C7 | 자동 과제마다 답의 변경으로 두 컴파일러에서 통과한다. 관찰 과제는 이유가 적혀 있다 | `tools/exercises.py check <id> --preset <p>` 표 |
| C8 | README 두 판의 절, 과제, 코드 블록 수가 같고, README "연습" 항목 수 = `exercises.toml` 과제 수 | 세어 본 수 |
| C9 | 레슨 작성 안내([lessons/README.md](/lessons/README.md) "레슨 작성 안내")와 트랙 spec 공통 규칙: 영어 출력, 두 언어 주석, UB를 돌리지 않음 | 리뷰 |
| C10 | fresh reviewer 한 번, 지적은 모두 고침 또는 이유를 적고 남김 | 리뷰 절 |
| C11 | 목록 문서(트랙 spec 상태 열, `lesson_candidates.md`, 필요하면 `intro`, 링크 줄)가 맞다 | `lint_docs.py` 와 diff |
| C12 | 후속은 KI로 등록했다 | KI id 또는 "없음" |
| C13 | `lint_docs.py` exit 0 | 명령 출력 |

### 2.5 문서 gate ([`lint_docs.py`](/.agent/scripts/lint_docs.py))
`check_specs`에 레슨 작업 분기를 더하고, `docs/specs/tracks/*.md`(`00_`로 시작하는 템플릿 제외)를 읽는 검사를 더한다.
| 검사 | 수준 |
|---|---|
| 트랙 spec에 frontmatter `track`, `approved`, `tasks`가 있고 `approved`는 `null` 또는 날짜 | ERROR |
| `track`이 `curriculum.toml`의 트랙 id | ERROR |
| todo 줄이 트랙 spec에 링크하면 그 ID가 `tasks`에 있다 | ERROR |
| `tasks`의 ID마다 todo(또는 archive)에 그 트랙 spec에 링크한 줄이 있다 | ERROR |
| `APPROVED` 이상인 레슨 작업의 트랙 spec이 `approved: null` | ERROR |
| 레슨 작업이 `SPEC_DRAFT` | ERROR |
| 트랙 spec이 승인됐는데 레슨 작업이 `BACKLOG` | WARN |
| `DONE` 레슨 작업에 `docs/tasks/feature_<ID>-*/checklist.md`가 없거나 `- [ ]`가 남음 | ERROR |
| 트랙 spec이 todo 어디에서도 링크되지 않음 | WARN |
`--boot`, `--status`는 바꾸지 않는다: 레슨 작업도 같은 상태 이름이라 "next approved task"에 그대로 나온다.

### 2.6 Internal Implementation
| 파일 | 바꾸는 것 |
|---|---|
| [`.agent/scripts/lint_docs.py`](/.agent/scripts/lint_docs.py) | §2.5. docstring 첫 줄에 "track specs" |
| [`.agent/scripts/test_agent_scripts.py`](/.agent/scripts/test_agent_scripts.py) | §2.5 검사마다 테스트(임시 저장소 모양) |
| `docs/specs/tracks/00_template.md` [NEW] | §2.2 |
| `docs/specs/tracks/00_lesson_checklist.md` [NEW] | 설계, 체크리스트(§2.4), 리뷰, 후속 |
| `docs/specs/tracks/oop_basics.md` [NEW] | Assumption 11. `approved: null` |
| [`docs/agent_todo.md`](/docs/agent_todo.md) | 070-22 ~ 070-24 줄이 트랙 spec에 링크(`BACKLOG`), 머리의 Grammar에 레슨 작업 한 줄 |
| §8의 문서 | 규칙 3과 절차 |

### 2.7 Platform Specifics
none (Python 표준 라이브러리, 문서).

## 3. C++ Standard Evolution
N/A.

## 4. Edge Cases
- [x] Thread safety, RAII, 플랫폼, 템플릿, ODR, UB: N/A (C++ 변경 없음).
- [x] 트랙 spec 승인 뒤 행을 더함: 사용자 승인으로 `approved`를 새 날짜로, History 한 줄. 승인 전까지 새 행의 작업은 `BACKLOG`이고, 이미 `APPROVED` 이상인 작업은 그대로(이전 승인으로 시작한 것). gate는 날짜만 보므로 "새 행만 미승인"은 todo 상태(`BACKLOG`)로 표시한다.
- [x] 진행 중인 레슨 작업이 있을 때 트랙 spec의 공통 규칙이 바뀜: 그 작업은 새 규칙으로 체크리스트를 채운다(완료 전이므로). 이미 `DONE`인 레슨은 고치지 않고 필요하면 KI.
- [x] 레슨 작업 도중 라이브러리 버그 발견: Assumption 9, `BLOCKED`.
- [x] `DONE` 레슨 작업이 archive로 옮겨짐: gate는 archive의 줄도 `tasks`와 맞춘다(§2.5 넷째 줄). 작업 폴더는 지금처럼 봉인.
- [x] 체크리스트 템플릿이 바뀜: 이미 만든 `checklist.md`는 만든 때의 항목을 쓴다. gate는 빈 칸만 보고 항목 이름은 보지 않는다.
- [x] GoogleTest·모듈 레슨: 항목은 같고, 맞지 않는 항목은 `N/A: <이유>`(Assumption 7).
- [x] 한 레슨 작업이 레슨 둘을 만듦: 허용하지 않는다. 레슨 하나 = 작업 하나 = 트랙 spec 행 하나.
- [x] 기존 레슨 고치기: 이 경로에 없음(§6).

## 5. Acceptance Criteria
| ID | Criterion | Verified by |
|---|---|---|
| AC-1 | 트랙 spec에 링크하고 `tasks`에 있는 레슨 작업은 트랙 spec이 승인되면 spec 파일 없이 `APPROVED`·`DEV`·`TEST`·`DONE`이 되어도 gate가 ERROR를 내지 않는다 | `test_agent_scripts.py` 새 테스트 |
| AC-2 | §2.5의 ERROR·WARN 줄마다 그 경우를 만든 저장소에서 그 메시지가 난다(`tasks`에 없음, `tasks`의 고아 ID, 승인 없음, `SPEC_DRAFT`, frontmatter 빠짐, 모르는 트랙, `DONE`인데 `checklist.md` 없음, `- [ ]` 남음, 승인됐는데 `BACKLOG`, 링크되지 않은 트랙 spec) | `test_agent_scripts.py` |
| AC-3 | 지금의 작업 spec 검사는 그대로다: 기존 테스트가 모두 통과하고 `00_` 템플릿 파일은 검사하지 않는다 | `py -3 -m unittest discover -s .agent/scripts -p "test_*.py"` |
| AC-4 | `00_template.md`와 `00_lesson_checklist.md`가 §2.2, §2.4와 같은 절·항목을 갖는다 | 리뷰(fresh reviewer, 체크 목록 대 spec) |
| AC-5 | 규칙 3의 글(boot 파일), spec.md, workflow, skill(원본과 복사본), todo Grammar, `lessons/README.md`가 §8대로 레슨 경로를 말하고 서로 어긋나지 않는다 | 리뷰, `sync_skills.py --check`(gate에 포함) |
| AC-6 | `oop_basics.md`가 070-21의 승인된 내용(Assumption 11의 목록)과 뜻이 같고, `lesson_candidates.md`의 OOP 표가 링크 한 줄로 바뀌고, 070-22 ~ 070-24 줄이 트랙 spec에 링크한다. gate exit 0 | 리뷰(070-21 대 트랙 spec), `lint_docs.py` |
| AC-7 | 사용자가 `oop_basics.md`를 읽고 승인한다. 승인 뒤 `approved` 날짜, 070-22 ~ 070-24 `APPROVED`, gate exit 0 | 사용자 확인 (손 확인, 병합 전에 묻는다) |
| AC-8 | 전체 Python 테스트와 문서 gate 통과 | `py -3 -m unittest`(tools, `.agent/scripts`, `web/server`), `py -3 .agent/scripts/lint_docs.py` exit 0 |

## 6. Out of Scope
- 이미 있는 레슨 고치기(다시 쓰기, 과제 추가): 지금처럼 KI → 작업. 잦아지면 트랙 spec의 `tasks`에 "고치기" 행을 두는 방식을 새 작업으로.
- essentials, patterns 트랙 spec: Assumption 12. 필요해질 때.
- 체크리스트 항목을 실행해 채우는 스크립트(C3–C8 자동 실행): 레슨 두세 개를 손으로 해 본 뒤 판단(070-28과 같은 시점).
- CI에서 레슨 경로 검사: 090-14(KI-024).

## 7. Dependencies & Backends
none.

## 8. Documentation Updates
| Document | Section | Change |
|---|---|---|
| [`docs/agent_start_prompt.md`](/docs/agent_start_prompt.md) | Non-negotiable rules 3 | "레슨 작업은 승인된 트랙 spec의 `tasks`에 있으면 된다(spec.md §6)" 한 문장 |
| [`docs/agent_start_prompt.md`](/docs/agent_start_prompt.md) | Boot 4, Quick reference | 레슨 작업: 트랙 spec과 체크리스트 템플릿을 읽음. Quick reference에 "Track spec, lesson checklist" 행 |
| [`.agent/rules/spec.md`](/.agent/rules/spec.md) | 새 §6 Track specs | 파일 위치, frontmatter, 정하는 것과 정하지 않는 것, 고치기와 재승인, 범위(§2.1) |
| [`.agent/workflows/start-develop-one-task.md`](/.agent/workflows/start-develop-one-task.md) | 2 Check the spec, 4–6 | 레슨 작업 분기: 트랙 spec 승인 확인, `checklist.md`가 plan·testrecord·walkthrough를 대신함, 병합 조건 |
| [`.agent/skills/develop-task/SKILL.md`](/.agent/skills/develop-task/SKILL.md) (+ `sync_skills.py`로 복사본) | 2, 4, 6, 7 | 레슨 작업이면 트랙 spec과 `checklist.md` |
| [`docs/agent_todo.md`](/docs/agent_todo.md) | Grammar | 레슨 작업 줄의 링크와 `SPEC_DRAFT` 없음 |
| [`lessons/README.md`](/lessons/README.md) | 새 레슨 추가 | 첫 줄에 "저장소 작업으로 레슨을 더할 때는 트랙 spec과 체크리스트(spec.md §6)" |
| [`docs/lesson_candidates.md`](/docs/lesson_candidates.md) | 머리말, OOP 입문 트랙 | 트랙 spec이 있는 트랙은 그 파일이 원본. OOP 표를 링크 한 줄로 |
| [`.agent/rules/delegation.md`](/.agent/rules/delegation.md) | — | 바꾸지 않음(Assumption 10) |

## 9. Technical Constraints
- Python 3.11+ (`lint_docs.py`가 이미 쓰는 범위)

## 10. Context & References
- [070-21](/docs/specs/070_21_oop_basics_track.md): OOP 트랙의 승인된 형식과 커리큘럼, 기록 본보기 [plan](/docs/tasks/feature_070-21-oop-basics-track/plan.md), [testrecord](/docs/tasks/feature_070-21-oop-basics-track/testrecord.md)
- [070-27](/docs/specs/070_27_lesson_scaffold.md): `lessons.py new`, `[scaffold]` WARN (체크리스트 C3의 출발점)
- [070-26](/docs/specs/070_26_lesson_order_manifest.md): `curriculum.toml`
- [spec.md](/.agent/rules/spec.md), [workflow](/.agent/workflows/start-develop-one-task.md), [delegation.md](/.agent/rules/delegation.md) §1, [lint_docs.py](/.agent/scripts/lint_docs.py) `check_specs`

## 11. Implementation Plan
- [ ] U1: 템플릿 둘(`00_template.md`, `00_lesson_checklist.md`)
- [ ] U2: `lint_docs.py` §2.5
- [ ] U3: `test_agent_scripts.py` (AC-1 ~ AC-3)
- [ ] U4: `oop_basics.md` (070-21에서 옮김), `lesson_candidates.md`, todo 줄과 Grammar
- [ ] U5: 문서(§8), `sync_skills.py`
- [ ] U6: 리뷰(AC-4 ~ AC-6), gate, 사용자에게 트랙 spec 승인 요청(AC-7)

## 12. Verification Plan
- [ ] `py -3 -m unittest discover -s .agent/scripts -p "test_*.py"`, `tools`, `web/server`
- [ ] `py -3 .agent/scripts/lint_docs.py`
- [ ] C++ 변경이 없으므로 preset 빌드는 하지 않는다(레슨 경로의 첫 실제 사용은 070-22)
- [ ] Every AC row has its evidence in `testrecord.md`

## History / Amendments
