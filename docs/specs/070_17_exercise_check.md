---
id: 070-17
title: 연습 과제 확인 (과제 정의, 자동 확인, 힌트·해설, 진행 기록)
depends_on: [070-16]
unblocks: [070-18, 070-20]
approved: 2026-11-10
---

# Spec 070-17: 연습 과제 확인 (과제 정의, 자동 확인, 힌트·해설, 진행 기록)

## 0. Assumptions (please review)
| # | Decision | Rejected alternative | Why |
|---|---|---|---|
| 1 | **범위**: (a) 레슨 폴더의 과제 정의 파일 `exercises.toml`, (b) 검사기 `tools/exercises.py`(서버와 CLI가 같이 씀), (c) 페이지의 오른쪽 패널 탭 **연습**(과제 목록, 결과, 힌트, 해설), (d) 진행 기록, (e) **시범 레슨 셋**의 과제 정의: `lambda_capture`, `error_expected`, `testing`. 나머지 레슨은 **070-20**이 채운다 | 모든 레슨을 이 작업에서 | 형식을 시범 레슨 셋으로 검증한 뒤 나머지 약 45개 과제에 쓰는 편이 안전하다. 셋은 확인 종류(빌드 실패, 종료 코드, 출력, 소스, 관찰)를 모두 쓴다(§2.4) |
| 2 | **확인은 연습 공간(070-16)에서만 한다**: 연습 Run의 빌드 로그·출력·종료 코드와 연습 사본 파일을 검사한다. 원본 편집 모드에서는 패널이 목록·힌트·해설만 보이고 "연습 모드에서 확인합니다"를 알린다 | 원본에서도 확인 | 원본에서 과제를 풀면 원본이 바뀐다. 070-16을 만든 이유 그 자체다 |
| 3 | **확인 규칙은 선언형이다**. 과제마다 아래 규칙의 조합(모두 맞아야 통과): `build = "ok" \| "fail"`(기본 `ok`), `build_expect = [정규식…]`(빌드 로그에 맞는 줄), `exit = <정수> \| "nonzero" \| "any"`(기본 0, `build = "fail"`이면 보지 않음), `expect = [정규식…]`(stdout에 맞는 줄), `forbid = [정규식…]`(맞는 줄이 없어야), `source = [{file, has = [...], lacks = [...]}]`(사본 파일 검사). 규칙이 하나도 없으면 **관찰 과제**(사용자가 스스로 "했음"으로 표시) | (a) 과제마다 GoogleTest 검사; (b) 과제마다 Python 검사 스크립트 | (a) 레슨은 `main`이 있는 프로그램이라 과제 코드를 테스트에 링크하려면 레슨마다 구조를 바꿔야 한다. (b) 임의 코드라 쓰기·리뷰가 무겁고, 지금 과제들은 선언형 규칙으로 표현된다(§2.4에서 확인). 비율 같은 수치 비교가 필요한 과제는 관찰 과제로 둔다 |
| 4 | **정규식은 Python `re`**(서버와 CLI가 같은 검사기). 줄 단위 `re.search`. 빌드 로그 정규식은 컴파일러마다 문구가 다르므로 둘 이상을 `|`로 쓰거나 공통 낱말을 고른다. `lessons.py check`가 정규식이 컴파일되는지 본다 | 브라우저(JS)에서 검사 | CLI에서도 같은 결과가 나와야 한다. 검사기는 한 곳 |
| 5 | **원본 그대로는 통과하지 않아야 한다**: 자동 과제는 (1) 레슨 사본 또는 유닛 사본 중 하나가 원본과 달라야(070-16의 `modified`) 통과하고, (2) `tools/exercises.py verify <lesson>`이 원본 프로그램의 빌드·실행 결과에 규칙을 대어 **어떤 자동 과제도 통과하지 않음**을 확인한다. `lessons.py check`는 빌드하지 않으므로 이 검사는 레슨을 빌드한 뒤의 CTest 테스트 `lesson.<id>.exercises_verify`로 돈다(§2.2) | 검사 없음 | 원본 출력에 이미 있는 줄을 `expect`로 쓰면 아무것도 안 해도 통과한다. 과제 작성 실수를 기계가 잡게 한다 |
| 6 | **풀 수 있음도 확인한다**: 과제마다 `answer`(해설 Markdown) 안의 코드대로 사본을 고쳐 통과하는 것을 DEV에서 한 번씩 돌려 testrecord에 남긴다(시범 레슨의 모든 자동 과제). 해답 파일을 저장소에 두지는 않는다 | 해답 소스를 `solutions/`에 두고 자동 검증 | 해답 파일이 레슨보다 커지고, 레슨이 바뀔 때마다 같이 고쳐야 한다. 시범 셋은 손으로 확인하고, 자동 검증은 필요해지면 KI |
| 7 | **언제 확인하는가**: 연습 Run이 끝날 때마다 서버가 그 레슨의 모든 자동 과제를 검사해 `done.exercises = [{id, passed, failures: [{rule, message}]}]`로 보낸다. 실행이 Stop·시간 초과로 끝나면 `exit` 규칙이 있는 과제는 실패다. 별도 "확인" 버튼은 없다(Run이 확인) | 과제마다 확인 버튼(그 과제만 실행) | 과제 하나를 확인하려면 어차피 빌드·실행해야 하고, 한 Run으로 모든 과제를 보면 "이 변경이 다른 과제도 풀었다"가 보인다 |
| 8 | **통과는 기록으로 남는다**(뒤에 코드를 다른 과제를 위해 바꿔도 지워지지 않음). 기록은 `practice/progress.json` = `{"version": 1, "lessons": {"<id>": {"<exercise>": {"passed": "<ISO 시각>", "how": "auto" \| "self"}}}}`. 레슨 되돌리기는 기록을 지우지 않고, 패널의 "기록 지우기"가 그 레슨의 기록만 지운다 | 브라우저 저장소 | 브라우저를 바꾸면 사라지고 CLI가 볼 수 없다. 연습 공간이 사용자의 자리다(070-16 Assumption 2) |
| 9 | **과제 문장은 README에 그대로 둔다.** `exercises.toml`은 id, 짧은 제목(두 언어), 규칙, 힌트, 해설만 갖는다. `lessons.py check`가 README의 "연습" 절 번호 항목 수와 과제 수가 다르면 WARN | 과제 문장을 `exercises.toml`로 옮기고 README는 링크 | 로컬에서 README만 읽는 사람이 과제를 못 본다. 제목만 겹친다 |
| 10 | **힌트·해설**: `hint`, `hint_en`, `answer`, `answer_en`(Markdown, TOML 여러 줄 문자열). 패널에서 "힌트"와 "해설" 버튼을 눌러야 보인다. 영어가 없으면 한국어를 안내 줄과 함께(README와 같은 규칙) | 해설을 README 끝에 | 먼저 스스로 풀어 보게 숨긴다. 한 파일에 두어야 과제와 해설이 어긋나지 않는다 |
| 11 | **실패 메시지**: 규칙마다 기본 문장("빌드가 실패해야 합니다", "출력에 `<정규식>`에 맞는 줄이 없습니다", "`main.cpp`에 `<정규식>`이 아직 있습니다", "종료 코드가 0이 아니어야 합니다")과, 과제가 준 `fail_hint`(선택)를 함께 보인다 | 규칙 이름만 | 배우는 사람이 무엇을 더 해야 하는지 알아야 한다 |
| 12 | **페이지**: 오른쪽 패널에 탭 **연습**(README 다음). 과제마다 번호, 제목, 종류 표시(자동/관찰), 상태(✓ 통과(시각), ✗ 마지막 Run에서 실패 + 메시지, — 아직), 힌트, 해설, 관찰 과제의 "했음" 체크. 레슨 트리의 레슨 옆에 `2/3` 진행 표시. Run이 새 과제를 통과시키면 그 탭에 점 표시 | 모달 대화상자 | 코드를 고치면서 옆에 계속 보여야 한다 |
| 13 | **CLI**: `py -3 tools/exercises.py check <lesson> --preset <p>`(연습 타깃 빌드·실행 후 표로 결과, 진행 기록 갱신), `verify <lesson> --preset <p>`(원본을 빌드·실행해 검사, Assumption 5; CTest는 `--exe`로 이미 빌드된 실행 파일을 넘김), `list <lesson>`. 빌드는 `build.py`로 | 웹 전용 | 070-16 Assumption 13과 같은 이유 |
| 14 | 시범 레슨의 과제 정의는 §2.4 표대로다. 컴파일 오류를 보는 과제의 `build_expect`는 Clang(웹)과 MSVC(로컬) 문구를 모두 받는다(DEV에서 두 컴파일러의 실제 문구로 확인) | Clang 문구만 | 로컬 Windows에서 같은 과제를 풀 때 통과하지 못한다 |

## 1. Objective
070-16으로 레슨을 사본에서 안전하게 고칠 수 있게 되지만, 과제를 제대로 풀었는지 알 길이 없다(README의 연습은 서술형이다). 이 작업은 과제를 선언형 규칙으로 정의하고, 연습 Run마다 자동으로 확인해 무엇이 아직 안 됐는지 알려 주고, 힌트와 해설을 숨겨 두었다가 보이며, 진행을 기록한다. 형식은 시범 레슨 셋으로 검증하고 나머지 레슨은 070-20이 채운다.

## 2. Requirement Details

### 2.1 Public API Surface
C++ API 변경 없음.

`exercises.toml`(레슨 폴더, 선택):
```toml
[[exercise]]
id       = "remove_mutable"          # [a-z0-9_], 레슨 안에서 유일, README 연습 순서와 같은 순서
title    = "mutable을 지우고 오류 읽기"
title_en = "Remove mutable and read the error"
build    = "fail"
build_expect = ['assign(ment)? to .*(read-only|const)|cannot assign to a variable captured by copy|C3491']
source   = [{ file = "main.cpp", lacks = ['\bmutable\b'] }]
fail_hint    = "makeCounterByValue의 람다에서 mutable만 지우세요"
fail_hint_en = "Remove only mutable from the lambda in makeCounterByValue"
hint     = """..."""
hint_en  = """..."""
answer   = """..."""
answer_en = """..."""
```
HTTP: `done`의 `exercises`(Assumption 7), `GET /api/exercises?lesson=<id>` → 정의(규칙 제외: 제목, 종류, 힌트, 해설) + 진행 기록, `POST /api/exercises/self {lesson, id, done}`(관찰 과제), `POST /api/exercises/clear {lesson}`.

### 2.2 Internal Implementation
| 곳 | 바꾸는 것 |
|---|---|
| `tools/exercises.py` (새) | 읽기·검증(스키마, id, 정규식 컴파일, `source.file`이 레슨 `sources`나 쓰는 유닛 `files`에 있음), `evaluate(defs, build_log, build_ok, stdout, exit, stopped, files)`, 진행 기록 읽기·쓰기, CLI(Assumption 13) |
| `tools/test_exercises.py` (새) | 규칙마다 통과·실패 경우, `exit` 세 형태, Stop·시간 초과, 수정 없음 → 통과 안 함, 기록 유지·지우기, 깨진 정의 |
| [`tools/lessons.py`](/tools/lessons.py) | `check`가 `exercises.toml`을 검증(ERROR: 스키마·정규식·없는 파일·중복 id; WARN: README 연습 항목 수 불일치, `title_en`·`hint_en`·`answer_en` 없음). 인덱스에 레슨의 과제 수 |
| [`lessons/CMakeLists.txt`](/lessons/CMakeLists.txt) | `exercises.toml`이 있는 레슨에 `ATUGCC_BUILD_TESTS`일 때 테스트 `lesson.<id>.exercises_verify`(label `lesson`): `tools/exercises.py verify <id> --exe $<TARGET_FILE:lesson_<id>>`를 부르고, 이미 빌드된 원본 실행 파일을 돌린 출력과 종료 코드로 원본이 어떤 자동 과제도 통과하지 않는지 본다(빌드 실패를 요구하는 과제는 원본 빌드가 성공하므로 저절로 통과하지 않음) |
| [`web/server/runner.py`](/web/server/runner.py) | 연습 Run의 끝에서 `evaluate` → `done.exercises`, 통과를 기록 |
| [`web/server/server.py`](/web/server/server.py) | `/api/exercises` GET, `self`, `clear` |
| [`web/frontend/src`](/web/frontend/src/main.ts) | 새 `exercises.ts`(패널), `main.ts`(탭, `done` 처리), `lessonTree.ts`(진행 표시), `i18n.ts`, `theme.css` |
| 테스트 | `test_server.py`(done의 exercises, API), 프런트엔드(패널 상태 그리기) |

### 2.3 Platform Specifics
- 빌드 로그 정규식: Clang(웹, `linux-x64-*`)과 MSVC(`windows-x64-*`)의 오류 문구가 다르다(Assumption 14).
- 출력 정규식: 레슨 출력은 영어이고 두 OS에서 같게 쓰여 있다(070-03). 경로·시간이 들어간 줄은 `expect`에 쓰지 않는다.

### 2.4 시범 레슨의 과제 정의
README의 지금 과제를 바꾸지 않고 규칙만 붙인다(문구는 DEV에서 실제 출력으로 맞춤).

| 레슨 | 과제 | 종류 | 규칙 |
|---|---|---|---|
| `lambda_capture` | 1 `mutable` 지우기 | 자동 | `build = "fail"`, `build_expect`(두 컴파일러 문구), `source.lacks = mutable` |
| | 2 참조 캡처 람다 반환(ASan) | 관찰 | ASan 실행은 로컬 preset이라 자동 확인하지 않음. 해설에 ASan 출력 예 |
| | 3 `holder`를 `std::function<int()>`로 | 자동 | `build = "fail"`, `build_expect`, `source.has = std::function<int\(\)>` |
| `error_expected` | 1 `catch (const std::out_of_range&)` 지우기 | 자동 | `exit = "nonzero"`, `source.lacks = catch \(const std::out_of_range` |
| | 2 `transform` 람다가 `Expected`를 돌려주게 | 자동 | `build = "ok"`, `source.has = and_then` 와 `Expected<std::string>` |
| | 3 `enum class PortError` | 자동 | `source.has = enum class PortError`, `std::expected<std::uint16_t, PortError>`; `expect`: 범위 밖과 숫자 아님이 다른 줄(DEV에서 해설의 출력 문장으로 정함) |
| `testing` | 1 `EXPECT_EQ` 틀리게 → `ASSERT_EQ` → `PrintTo` 지우기 | 자동 + 관찰 | 1a: `exit = 1`, `expect = Expected equality of these values`; 1b·1c는 관찰(단계를 지나가는 과제) |
| | 2 시나리오 3단계 깨기 | 자동 | `exit = 1`, `expect = \[skip 4\]` 와 `step 3: parse the file` |
| | 3 로컬 리포트 읽기 | 관찰 | 로컬 `build.py --report` 과제 |

과제 하나가 여러 단계를 거치는 경우(testing 1)는 단계마다 별도 과제 id로 나눌 수 있다. README의 번호 항목 수 WARN(Assumption 9)은 "하위 과제"(`id`에 `_a`, `_b`)를 하나로 센다.

## 3. C++ Standard Evolution
N/A (도구와 페이지 작업). 시범 과제의 내용은 각 레슨의 기존 비교를 따른다.

## 4. Edge Cases
- [x] Thread safety — 확인은 Run이 끝난 뒤 서버의 작업 스레드에서 한 번. 진행 기록 쓰기는 `write_lock` 아래, 임시 파일 + 교체.
- [x] Resource lifetime — 검사 대상 stdout은 출력 상한(`output_bytes`)까지. 상한을 넘겨 잘렸으면(`truncated`) `expect`·`forbid` 규칙이 있는 과제는 "출력이 잘려 확인하지 못함"으로 실패가 아닌 미확인으로 보낸다.
- [x] Platform differences — 빌드 로그 문구(§2.3). 줄 끝은 검사 전에 LF로.
- [x] Template instantiation / concept constraints — N/A.
- [x] ODR — N/A.
- [x] Undefined behaviour — N/A. (UB를 보는 과제, ASan은 관찰 과제)
- [x] 정규식이 너무 넓음(`.*`만) — `lessons.py check`가 빈 문자열에 맞는 `expect`·`build_expect`·`has`를 WARN. 원본 통과 검사(Assumption 5)가 다른 실수를 잡는다.
- [x] 사본 파일이 지워진 상태 — 070-16에서 사본 파일은 지울 수 없다. 있다고 본다. 없으면 `source` 규칙은 "파일 없음"으로 실패.
- [x] `exercises.toml`이 깨짐 — 페이지는 패널에 오류를 보이고 Run은 그대로 된다(확인만 빠짐). `lessons.py check`가 ERROR.
- [x] 진행 기록이 깨짐 — 070-16의 `state.json`과 같이 이름을 바꿔 두고 새로 시작.
- [x] 레슨 id 바뀜 — 기록은 옛 id로 남고 보이지 않는다(받아들임).

## 5. Acceptance Criteria
| ID | Criterion | Verified by |
|---|---|---|
| AC-1 | 규칙 여섯 가지와 `exit`의 세 형태가 각각 통과·실패를 맞게 낸다. 수정하지 않은 사본은 어떤 자동 과제도 통과하지 않는다. Stop·시간 초과·잘린 출력이 Assumption 7과 §4대로 처리된다 | `py -3 tools/test_exercises.py` |
| AC-2 | 시범 레슨 셋의 모든 자동 과제가 해설대로 고친 사본에서 웹과 로컬(`windows-x64-debug`) 둘 다 통과하고, 원본 그대로는 통과하지 않는다 | 과제마다 실행 기록(사본 diff 요약, 결과), `ctest -R exercises_verify` |
| AC-3 | 패널: 연습 Run 뒤 과제마다 ✓/✗/—와 실패 메시지(`fail_hint` 포함)가 보이고, 힌트·해설은 누르기 전에는 숨겨져 있다. 관찰 과제의 "했음"이 기록된다. 트리의 진행 표시가 맞다. 원본 편집 모드에서는 확인 없이 안내 줄이 보인다 | 헤드리스 브라우저 스크린샷(통과, 실패, 해설 펼침), 프런트엔드 테스트 |
| AC-4 | 통과 기록은 다른 과제를 위해 코드를 바꾼 뒤에도, 레슨 되돌리기 뒤에도 남고, "기록 지우기"는 그 레슨의 기록만 지운다. 브라우저를 바꿔도 같은 기록이 보인다 | `test_server.py`, `test_exercises.py` |
| AC-5 | CLI `check`가 웹과 같은 결과를 표로 찍고 같은 진행 기록을 쓴다 | 같은 사본에 대한 두 결과 비교 |
| AC-6 | `lessons.py check`가 새 규칙(§2.2)마다 맞는 수준을 내고, 저장소 전체는 ERROR 0, WARN 0이다 | `py -3 tools/test_lessons.py`, `py -3 tools/lessons.py check` |
| AC-7 | 영어 화면에서 제목·힌트·해설이 영어로 나오고(없으면 안내 줄과 한국어), 새 문구는 모두 `i18n.ts`에 있다 | 프런트엔드 테스트(`i18n.test.ts`), 스크린샷 |
| AC-8 | 전체 suite, 프런트엔드 테스트, `PlaygroundServer`, 도구 테스트가 통과하고 §8 문서가 결과와 맞으며 `lint_docs.py`가 exit 0이다 | 명령 출력 |

## 6. Out of Scope
- 나머지 레슨(essentials 12개, patterns 1개)의 과제 정의 — **070-20**. `thread_and_log`는 070-18이 정의한다
- 수치 비교 규칙(비율, 범위), Tracer 이벤트를 보는 규칙 — 필요한 과제가 생기면 KI
- 해답 소스의 자동 검증 — Assumption 6
- 테스트 결과 탭(KI-042)

## 7. Dependencies & Backends
없음(Python 3.11+의 `tomllib`, `re`).

## 8. Documentation Updates
| Document | Section | Change |
|---|---|---|
| [`lessons/README.md`](/lessons/README.md) | 새 절 "연습 과제 정의" | `exercises.toml` 형식, 규칙 표, 원본 통과 검사, CLI |
| [`web/README.md`](/web/README.md) | API, Page | `done.exercises`, `/api/exercises`, 연습 탭 |
| [`lessons/intro.md`](/lessons/intro.md), [`intro.en.md`](/lessons/intro.en.md) | 할 수 있는 일 | 연습 탭과 자동 확인 한 줄 |
| [`docs/lesson_candidates.md`](/docs/lesson_candidates.md) | 머리말 | 새 레슨은 `exercises.toml`을 둔다(한 줄) |
| 시범 레슨 셋 | `exercises.toml` (새) | §2.4 |
| [`docs/agent_todo.md`](/docs/agent_todo.md) | Phase 7 | 070-17 줄 |

## 9. Technical Constraints
- Compiler: MSVC (VS 2026) / Clang 20 with libstdc++ 14 (Linux)
- CMake: 4.0+, Python 3.11+ 표준 라이브러리만
- 프런트엔드: 새 패키지 없음

## 10. Context & References
- [070-16 스펙](/docs/specs/070_16_practice_workspace.md)(연습 공간, `modified` 상태, `practice/`)
- [`lessons/tracks/01_essentials/01_lambda_capture/README.md`](/lessons/tracks/essentials/lambda_capture/README.md), [`04_error_expected/README.md`](/lessons/tracks/essentials/error_expected/README.md), [`16_testing/README.md`](/lessons/tracks/essentials/testing/README.md)의 연습 절
- [`web/server/runner.py`](/web/server/runner.py)(`parse_diagnostics`, `parse_test_failures`, `done`), [`tools/lessons.py`](/tools/lessons.py)
- 이 스펙은 새 시험을 하지 않았다. 시범 과제의 컴파일러 문구는 DEV에서 두 컴파일러로 확인한다

## 11. Implementation Plan
- [ ] Step 1: `tools/exercises.py`와 `tools/test_exercises.py`
- [ ] Step 2: `lessons.py check` 규칙, `lessons/CMakeLists.txt`의 `exercises_verify`
- [ ] Step 3: 시범 레슨 셋의 `exercises.toml`(두 컴파일러 문구 확인, 해설대로 풀어 보기)
- [ ] Step 4: 서버(`runner.py`, `server.py`)와 테스트
- [ ] Step 5: 프런트엔드(연습 탭, 트리 진행, i18n)와 테스트
- [ ] Step 6: §8 문서

## 12. Verification Plan
- [ ] `py -3 .agent/scripts/build.py --preset windows-x64-debug --test`, `--preset linux-x64-debug --test`
- [ ] `py -3 tools/test_exercises.py`, `py -3 tools/test_lessons.py`, `npm --prefix web/frontend test`, `ctest -R PlaygroundServer`
- [ ] 시범 과제마다 웹·로컬 풀이 기록(AC-2)
- [ ] 헤드리스 브라우저(AC-3, AC-7)
- [ ] `lint_docs.py` exit 0
- [ ] 모든 AC 행의 증거가 `testrecord.md`에

## History / Amendments
- 2026-11-10: 초안
- 2026-11-10: 승인(사용자, 070-07·070-16·070-18·070-19와 함께)
- 2026-11-10 (DEV): `source.file`은 레슨 `sources`나 쓰는 유닛 `files`의 파일 이름(같은 이름이 둘이면 ERROR). 실패 메시지는 규칙 이름과 값으로 보내고 문장은 페이지의 `i18n.ts`(두 언어)와 CLI(영어)가 만든다. 트리의 `2/3`을 위해 `GET /api/exercises/summary`를 더했다. 진행 기록은 `exercises.py`의 모듈 잠금 아래에서 쓴다(서버의 `write_lock`은 저장소 파일용이고, 기록 파일은 이 모듈만 씀). Windows Debug의 `abort()` 대화상자 때문에 `error_expected` `remove_catch`는 무인 확인에서 시간 초과가 된다(KI-050). `dangling_return` 해설: Clang 20은 `return [&local]{…};`를 빌드에서 잡으므로(`-Wreturn-stack-address`) 람다를 변수에 담아 돌려주는 모양으로 쓴다.
