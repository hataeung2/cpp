---
id: 070-27
title: 레슨·유닛 뼈대 생성 (`lessons.py new`, `new-unit`)
depends_on: [070-26]
unblocks: [090-13, 070-22, 070-23, 070-24]
approved: 2026-11-17
---

# Spec 070-27: 레슨·유닛 뼈대 생성 (`lessons.py new`, `new-unit`)

## 0. Assumptions (please review)
| # | Decision | Rejected alternative | Why |
|---|---|---|---|
| 1 | **명령은 `tools/lessons.py`의 하위 명령 둘**: `new <track> <id>`, `new-unit <id>`. 검사(`check`)와 같은 파일이라 id 규칙, 트랙 목록, 태그 어휘, `curriculum.toml` 읽기를 그대로 쓴다 | 새 스크립트 `tools/new_lesson.py` | 같은 규칙을 두 곳에 두면 어긋난다. `lessons.py`는 이미 카탈로그의 원본이다 |
| 2 | **뼈대는 만든 즉시 빌드되고 모든 검사를 통과한다**: `lesson_<id>`가 빌드되고, smoke test `lesson.<id>`와 `lesson.<id>.exercises_verify`가 통과하고, `lessons.py check`의 ERROR가 0이다. 남는 것은 아래 6의 WARN뿐이다 | 빈 파일만 만들고 작성자가 채움 | 070-26 Assumption 4와 같은 생각: 폴더를 만들자마자 빌드되고 페이지에 보여야 쓰면서 확인할 수 있다 |
| 3 | **레슨 뼈대의 파일**: `lesson.toml`, `README.md`, `README.en.md`, `main.cpp`, `exercises.toml`. README는 지금 레슨들의 절 순서(첫 절 비교 표 → `## 실행` → `## 볼 것` → `## 연습`, 영어판은 `## Run`, `## What to look for`, `## Exercises`)를 따른다. `main.cpp`는 두 언어 주석의 `@file` 머리와 영어 한 줄을 출력하는 `main`이다. `exercises.toml`은 **관찰 과제 하나**(규칙 없음)이고 README `## 연습`의 항목도 하나다 | (a) `exercises.toml` 없음; (b) 과제 0개 | (a) 레슨마다 `exercises.toml`이 있다는 지금의 규칙(070-20)과 어긋난다. (b) README 항목 수와 과제 수가 달라 WARN이 난다. 관찰 과제는 원본 통과 검사(`exercises_verify`)에서 늘 통과한다 |
| 4 | **첫 절의 제목은 하나로 둔다**: `## 예전 방식과 C++20` (영어 `## The old way and C++20`). `oop_basics`처럼 "흔한 실수 → 바른 방식"으로 쓰는 트랙은 작성자가 제목을 바꾼다. 절 바로 아래의 `[scaffold]` 줄이 두 가지 제목을 안내한다 | 트랙마다 다른 템플릿, `--style` 옵션 | 다른 것은 제목 한 줄이다. 템플릿 둘을 같이 고치는 일이 더 크다 |
| 5 | **템플릿은 파일로 `tools/lesson_templates/lesson/`, `tools/lesson_templates/unit/`에 둔다**. 이름은 `<만들 파일 이름>.tmpl`(`README.md.tmpl`, `main.cpp.tmpl`, 유닛 헤더는 `unit.hpp.tmpl` → `<id>.hpp`). 치환은 `string.Template`(`$id`, `$track`, `$title`, `$title_en`, `$summary`, `$summary_en`, `$tags`, `$uses`)이고 모르는 이름은 오류다 | (a) `lessons.py` 안의 문자열; (b) `lessons/` 아래 템플릿 폴더 | (a) 한국어·영어 Markdown과 C++이 Python 문자열 안에 있으면 읽고 고치기 어렵다. 파일이면 결과물과 같은 모양으로 보인다. (b) `lessons/`는 문서 gate가 Markdown 링크를 검사하고 CMake glob이 도는 곳이다. `.tmpl` 이름이면 `tools/` 안에서도 lint와 빌드가 건드리지 않는다. `$`는 C++과 이 Markdown에 나오지 않고, 나오면 `$$`로 쓴다 |
| 6 | **작성자가 채울 곳은 `[scaffold]` 표시**를 단다(README의 문단, `main.cpp`의 주석, `exercises.toml`의 `title`·`hint`). `lessons.py check`는 레슨·유닛 폴더의 파일(매니페스트, README 두 개, `sources`, `files`, `exercises.toml`)에 `[scaffold]`가 남아 있으면 **파일마다 WARN 한 줄**을 낸다 | (a) 표시 없음; (b) ERROR | (a) 다 채웠는지 사람이 눈으로만 찾게 된다. 090-13의 레슨 체크리스트가 "`[scaffold]` WARN 0"을 한 줄로 쓸 수 있다. (b) 쓰는 중에 빌드와 gate가 막히면 Assumption 2가 깨진다. 지금 저장소에는 `[scaffold]`라는 글이 없다 |
| 7 | **제목, 요약, 태그, `uses`는 옵션**이다: `--title`, `--title-en`, `--summary`, `--summary-en`, `--tags a,b`, `--uses unit:x,lib:y`. 빠진 제목·요약은 `[scaffold] …` 글로 들어간다(그래서 6의 WARN이 매니페스트에도 난다). `--tags`의 태그가 `tags.toml`에 없거나 `--uses`의 대상이 없으면 **아무것도 만들지 않고 오류**다(`check`에서는 태그가 WARN이지만, 만드는 순간에는 고칠 기회가 있다) | 대화형으로 묻기 | 이 저장소의 도구는 모두 비대화형이고, 에이전트도 같은 명령을 쓴다 |
| 8 | **`curriculum.toml`에 자동으로 넣는다**: 기본은 그 트랙 `lessons`의 끝, `--after <id>`나 `--before <id>`(같은 트랙의 레슨)면 그 자리. 파일은 **글 그대로 고친다**(주석과 줄 모양 유지): 그 트랙 `[[track]]` 블록의 여러 줄 `lessons = [ … ]` 안에 `  "<id>",` 한 줄을 넣는다. 배열이 한 줄로 쓰여 있거나 찾을 수 없으면 오류이고 아무것도 만들지 않는다 | TOML을 읽고 다시 씀 | 표준 라이브러리에 TOML 쓰기가 없고, 다시 쓰면 주석이 사라진다. 070-26이 만든 파일은 모두 여러 줄 배열이다 |
| 9 | **트랙은 이미 있어야 한다**: `lessons/tracks/<track>/track.toml`이 있고 `curriculum.toml`에 그 트랙이 있어야 한다. 새 트랙 만들기(`new-track`)는 이 작업에 없다 | `new`가 트랙도 만듦 | 트랙은 셋이고, 새 트랙은 드물며 제목과 자리를 사람이 정한다. 필요해지면 `track.toml` 하나와 `curriculum.toml`의 블록 하나다 |
| 10 | **실패하면 아무것도 바꾸지 않는다**: 먼저 모든 조건(id 형식, 레슨 id 중복, 폴더 존재, 트랙, 자리, 태그, `uses`)을 확인하고, 그다음 폴더를 만들고 파일을 쓴 뒤 `curriculum.toml`을 마지막에 쓴다. 쓰는 도중 실패하면 만든 폴더를 지우고 `curriculum.toml`을 원래 글로 되돌린다 | 만든 만큼 남김 | 반쯤 만든 폴더는 다음 `new`를 "이미 있음"으로 막는다 |
| 11 | **만든 뒤 `check`를 돌려 새 폴더에 대한 결과만 보여 준다**(위 6의 WARN 목록이 "채울 곳" 안내가 된다). 종료 코드는 만들었으면 0, 조건 실패면 1이다. 만든 파일 목록과 다음 할 일(빌드 명령, 페이지 새로고침)을 출력한다 | 출력 없음 | 무엇이 생겼고 무엇이 남았는지 한 번에 보인다 |
| 12 | **`new-unit <id>`의 파일**: `unit.toml`(`files = ["<id>.hpp"]`), `<id>.hpp`(`#pragma once`와 두 언어 머리 주석), `README.md`, `README.en.md`(지금 유닛 README의 절: `## 1. 개요 및 학습 포인트`, `## 2. 주요 인터페이스`, `## 3. 사용 예시`). 유닛 id는 유닛끼리 유일하고 레슨 id와는 같아도 된다(지금 규칙). 순서 목록은 없다(유닛은 트리에서 이름순). 레슨의 `uses`에 넣는 일은 작성자가 한다 | `--lesson <id>`로 레슨 `uses`에 추가 | `lesson.toml`을 글 그대로 고치는 두 번째 편집기가 생긴다. `uses` 한 줄을 고치는 것은 작은 일이다 |
| 13 | **`--gtest` 레슨 뼈대는 없다.** GoogleTest 레슨은 `testing` 레슨을 복사해 시작한다(지금 README의 방법) | `--gtest` 옵션 | GoogleTest 레슨은 하나이고, 앞으로 패턴 작업의 테스트는 `tests/scenario/`에 둔다(090-05 원칙) |
| 14 | **README의 "새 레슨 추가"는 이 명령을 첫 방법으로 쓴다.** 비슷한 레슨을 복사하는 방법은 한 줄로 남긴다(gtest 레슨, 모듈 레슨) | 복사 방법 삭제 | 모듈·GoogleTest 레슨은 여전히 복사가 빠르다 |

## 1. Objective
070-26 뒤로는 새 레슨을 더할 때 폴더 하나와 `curriculum.toml` 한 줄이면 되지만, 지금은 비슷한 레슨을 복사한 뒤 매니페스트, 두 README, `main.cpp`, `exercises.toml`에서 옛 레슨의 글을 찾아 지워야 한다. 지우다 남긴 글은 검사가 잡지 못하고, 순서 목록 등록도 잊기 쉽다. OOP 후속 3개(070-22 ~ 070-24), 패턴 14개, 엔진 레슨을 더하기 전에, 명령 하나로 **바로 빌드되고 검사를 통과하는 뼈대**를 만들고 작성자가 채울 곳을 표시해 둔다. 090-13(레슨 경로: 레슨 하나는 체크리스트로 완료)은 이 뼈대와 `[scaffold]` WARN을 체크리스트의 출발점으로 쓴다.

## 2. Requirement Details

### 2.1 명령
```text
py -3 tools/lessons.py new <track> <id> [--after <id> | --before <id>]
        [--title T] [--title-en T] [--summary S] [--summary-en S]
        [--tags a,b] [--uses unit:x,lib:atugcc/core/error.hpp] [--root R]
py -3 tools/lessons.py new-unit <id>
        [--title T] [--title-en T] [--summary S] [--summary-en S]
        [--uses lib:…] [--root R]
```
출력 예:
```text
lessons: created lessons/tracks/oop_basics/composition/
  lesson.toml, README.md, README.en.md, main.cpp, exercises.toml
lessons: curriculum.toml: oop_basics, after inheritance_virtual
WARN lessons/tracks/oop_basics/composition/README.md: [scaffold] placeholder left (5 line(s), first at 3)
…
next: py -3 .agent/scripts/build.py --preset <preset> --target lesson_composition; reload the playground page
```

### 2.2 조건 (모두 `new`가 아무것도 쓰기 전에 확인, 하나라도 어기면 exit 1)
| 조건 | 메시지의 뜻 |
|---|---|
| id가 `check`의 id 규칙(`[a-z0-9_]+`)에 맞고 숫자로 시작하지 않음 | 잘못된 id |
| 레슨 id가 다른 레슨과 겹치지 않음 (유닛과는 겹쳐도 됨) | 중복 |
| `lessons/tracks/<track>/<id>/`가 없음 | 이미 있음 |
| `lessons/tracks/<track>/track.toml`이 있음, `curriculum.toml`에 그 트랙이 있음 | 트랙 없음 / 목록에 트랙 없음 |
| `--after`·`--before`의 id가 그 트랙 목록에 있음, 둘을 함께 쓰지 않음 | 자리 없음 |
| 그 트랙의 `lessons`가 여러 줄 배열임 | 고칠 수 없는 모양 |
| `--tags`가 모두 `tags.toml`에 있음 | 모르는 태그 |
| `--uses`의 형식과 대상이 `check`와 같은 규칙으로 맞음 | 없는 대상 |
`new-unit`은 id 규칙, 유닛 id 중복, `lessons/units/<id>/` 없음, `--uses`만 본다.

### 2.3 뼈대의 내용 (요지, 정확한 글은 템플릿 파일)
```toml
# lesson.toml
id         = "composition"
title      = "[scaffold] 한국어 제목"        # --title 이 있으면 그 값
title_en   = "[scaffold] English title"
summary    = "[scaffold] 한 줄 요약"
summary_en = "[scaffold] One-line summary"
sources    = ["main.cpp"]
uses       = []                               # --uses
tags       = []                               # --tags
```
```cpp
/**
 * @file main.cpp
 * @brief 레슨 composition — [scaffold] 한 줄 설명
 * @brief Lesson composition — [scaffold] one-line description
 */
#include <iostream>

int main() {
    // [scaffold] 단계마다 무엇을 보여 주는지 출력한다
    // [scaffold] Print what each step shows
    std::cout << "composition: scaffold\n";
    return 0;
}
```
```toml
# exercises.toml: 관찰 과제 하나 (규칙 없음, 사용자가 "했음"으로 표시)
[[exercise]]
id       = "first_exercise"
title    = "[scaffold] 첫 과제"
title_en = "[scaffold] First exercise"
hint     = '''[scaffold] …'''
hint_en  = '''[scaffold] …'''
```
README 두 개: `# 레슨: <title> (\`<id>\`)`, 첫 절, `## 실행`(지금 레슨들과 같은 웹·로컬 두 줄, `<id>`가 들어감), `## 볼 것`, `## 연습`(연습 공간 안내 문단과 항목 하나). 링크는 저장소 루트 기준(`/lessons/README.md`)만 써서 폴더 깊이와 상관없이 맞다.

### 2.4 Internal Implementation
| 파일 | 바꾸는 것 |
|---|---|
| [`tools/lessons.py`](/tools/lessons.py) | `new`, `new-unit` 하위 명령(argparse를 하위 명령 방식으로), 조건 확인, 템플릿 채우기, `curriculum.toml` 글 편집, 실패 시 되돌리기. `check`에 `[scaffold]` WARN(Assumption 6). docstring의 Usage |
| `tools/lesson_templates/lesson/*.tmpl` [NEW] | `lesson.toml`, `README.md`, `README.en.md`, `main.cpp`, `exercises.toml` |
| `tools/lesson_templates/unit/*.tmpl` [NEW] | `unit.toml`, `unit.hpp`, `README.md`, `README.en.md` |
| [`tools/test_lessons.py`](/tools/test_lessons.py) | AC-1 ~ AC-6의 테스트(임시 `--root`에 작은 저장소 모양) |
| [`lessons/curriculum.toml`](/lessons/curriculum.toml) | 머리 주석에 `lessons.py new`가 넣는다는 한 줄 |

바꾸지 않는 것: `lessons/CMakeLists.txt`(glob `CONFIGURE_DEPENDS`가 새 폴더를 찾는다), `web/`(서버는 요청마다 카탈로그를 읽는다), `tools/exercises.py`, `tools/practice.py`.

### 2.5 Platform Specifics
파일은 UTF-8, 줄 끝은 LF로 쓴다(`newline="\n"`). `curriculum.toml`의 줄 끝은 읽은 그대로 둔다. Windows와 WSL 어느 쪽에서 실행해도 결과가 같다.

## 3. C++ Standard Evolution
N/A.

## 4. Edge Cases
- [x] Thread safety, RAII, 템플릿, ODR, UB: N/A (생성되는 C++은 `main` 하나, 도구는 Python).
- [x] Platform differences: §2.5. id는 소문자만이라 대소문자를 가리지 않는 Windows에서도 겹치지 않는다.
- [x] 같은 id의 유닛이 있는 레슨(`lambda_capture`): 허용(지금 규칙). `units/`와 `tracks/`로 폴더가 갈라진다.
- [x] `curriculum.toml`에 주석, 빈 줄, 마지막 쉼표가 없는 줄: 마지막 항목에 쉼표가 없으면 넣기 전에 붙인다. 주석 줄은 그대로 둔다. 테스트한다(AC-3).
- [x] `curriculum.toml`이 깨졌거나 없음: `new`는 오류(자리를 정할 수 없음). `check`는 070-26대로.
- [x] 템플릿에 모르는 `$이름` 또는 템플릿 파일 없음: 아무것도 쓰기 전에 오류(템플릿을 모두 먼저 채워 본 뒤 쓴다).
- [x] 제목·요약에 따옴표나 역슬래시: TOML 기본 문자열로 이스케이프해 넣는다. 줄바꿈은 오류.
- [x] 소스에 한글 리터럴 금지(070-10 WARN): `main.cpp`의 출력은 영어, 한국어는 주석에만.
- [x] 열려 있는 플레이그라운드: 서버가 요청마다 카탈로그를 읽으므로 페이지를 새로고침하면 트리에 보인다. 빌드 폴더는 다음 configure가 새 폴더를 찾는다.
- [x] 연습 공간: 새 레슨의 사본은 처음 연습 모드로 열 때 생긴다(지금과 같음).

## 5. Acceptance Criteria
| ID | Criterion | Verified by |
|---|---|---|
| AC-1 | `new <track> <id>`가 레슨 폴더에 다섯 파일을 만들고, 그 뒤 `check`가 ERROR 0이며 새 폴더의 WARN은 `[scaffold]` 줄뿐이다. `index`에 새 레슨이 나온다 | `tools/test_lessons.py`의 새 테스트 |
| AC-2 | `--title` 등 옵션의 값이 매니페스트와 README 제목에 들어가고 그 필드에는 `[scaffold]`가 없다. 따옴표가 든 제목도 TOML로 읽힌다 | `tools/test_lessons.py` |
| AC-3 | 자리: 옵션 없음은 트랙 끝, `--after`·`--before`는 그 자리이며, `index`의 순서가 그대로 바뀐다. `curriculum.toml`의 다른 줄(주석 포함)은 글자 그대로 남는다. 마지막 항목에 쉼표가 없던 경우도 맞게 넣는다 | `tools/test_lessons.py` |
| AC-4 | §2.2의 조건마다 exit 1이고, 저장소 모양(파일 목록과 `curriculum.toml`의 바이트)이 실행 전과 같다. 쓰는 도중의 실패(템플릿 하나를 쓸 수 없게 만든 경우)도 같다 | `tools/test_lessons.py` |
| AC-5 | `new-unit <id>`가 네 파일을 만들고 `check` ERROR 0, WARN은 `[scaffold]`뿐이다. 중복 유닛 id와 있는 폴더는 exit 1이고 아무것도 바뀌지 않는다 | `tools/test_lessons.py` |
| AC-6 | `check`는 레슨·유닛 파일에 남은 `[scaffold]`를 파일마다 WARN 한 줄로 낸다. 지금 저장소의 22개 레슨과 2개 유닛에서는 아무것도 내지 않는다 | `tools/test_lessons.py`, `py -3 tools/lessons.py check` |
| AC-7 | 실제 저장소에서 만든 레슨 하나와 그 레슨이 쓰는 새 유닛 하나가 두 호스트에서 빌드되고 `lesson.<id>`, `lesson.<id>.exercises_verify`가 통과한다(검증 뒤 지우고 커밋하지 않음) | `build.py --preset windows-x64-debug --test --report`, WSL `linux-x64-debug` 같은 명령 (testrecord) |
| AC-8 | 전체 테스트와 문서 gate가 통과한다 | `py -3 -m unittest`(tools, `.agent/scripts`, `web/server`), `py -3 .agent/scripts/lint_docs.py` exit 0 |

## 6. Out of Scope
- 새 트랙 만들기(`new-track`): Assumption 9. 필요해지면 새 작업.
- 레슨의 `uses`에 유닛 추가, 레슨 이름 바꾸기·트랙 옮기기 명령: 손으로 한다(070-26 Assumption 5).
- GoogleTest·모듈 레슨 뼈대: Assumption 13, 14.
- 페이지에서 레슨 만들기 버튼: 요청이 생기면 새 작업.
- 레슨 완료 체크리스트와 규칙 3의 완화: 090-13.

## 7. Dependencies & Backends
none (Python 3.11+ 표준 라이브러리: `tomllib`, `string.Template`).

## 8. Documentation Updates
| Document | Section | Change |
|---|---|---|
| [`lessons/README.md`](/lessons/README.md) | 새 레슨 추가 | 첫 방법을 `lessons.py new`로(옵션, `[scaffold]` 표시, 자리 옵션), 복사는 gtest·모듈 레슨용 한 줄. 유닛 추가(`new-unit`, `uses`에 넣기) 문단 |
| [`lessons/README.md`](/lessons/README.md) | 구조 | `curriculum.toml` 줄에 "`new`가 등록" |
| [`tools/lessons.py`](/tools/lessons.py) | docstring | Usage에 두 명령, 템플릿 위치 |
| [`lessons/curriculum.toml`](/lessons/curriculum.toml) | 머리 주석 | 한 줄 |
| [`docs/agent_start_prompt.md`](/docs/agent_start_prompt.md) | Quick reference, "Lesson manifests" 행 | 새 레슨·유닛: `py -3 tools/lessons.py new <track> <id>`, `new-unit <id>` |

## 9. Technical Constraints
- Python 3.11+ (`tomllib`)
- 생성된 레슨은 MSVC와 Clang 20에서 경고 없이 빌드된다(Core 규칙)

## 10. Context & References
- [070-26](/docs/specs/070_26_lesson_order_manifest.md): `curriculum.toml`, 폴더 이름 = id, 목록에 없는 레슨은 WARN
- [070-01](/docs/specs/070_01_lesson_structure.md) 레슨 구조, [070-10](/docs/specs/070_10_lesson_search_i18n.md) 영어 필드와 한글 리터럴, [070-17](/docs/specs/070_17_exercise_check.md) 관찰 과제와 원본 통과 검사, [070-20](/docs/specs/070_20_remaining_exercises.md) 레슨마다 `exercises.toml`
- [tools/lessons.py](/tools/lessons.py), [tools/exercises.py](/tools/exercises.py), [lessons/CMakeLists.txt](/lessons/CMakeLists.txt)
- 본보기: [class_basics](/lessons/tracks/oop_basics/class_basics/README.md), [jthread_worker](/lessons/units/jthread_worker/README.md)

## 11. Implementation Plan
- [ ] U1: 템플릿 파일(레슨 다섯, 유닛 넷), 두 언어 글
- [ ] U2: `lessons.py` — 하위 명령, 조건 확인, 템플릿 채우기, 쓰기와 되돌리기, `curriculum.toml` 글 편집
- [ ] U3: `check`의 `[scaffold]` WARN
- [ ] U4: `test_lessons.py` 테스트(AC-1 ~ AC-6)
- [ ] U5: 실제 저장소에서 레슨·유닛 하나 만들어 두 호스트 빌드(AC-7), 지움
- [ ] U6: 문서(§8), KI 확인, gate

## 12. Verification Plan
- [ ] `py -3 -m unittest discover -s tools -p "test_*.py"`, `.agent/scripts`, `web/server`
- [ ] `py -3 tools/lessons.py check`
- [ ] AC-7: `py -3 .agent/scripts/build.py --preset windows-x64-debug --test --report`, WSL에서 `linux-x64-debug`
- [ ] `py -3 .agent/scripts/lint_docs.py`
- [ ] Every AC row has its evidence in `testrecord.md` (evidence runs with `--report`, [test.md](/.agent/rules/test.md) §6)

## History / Amendments
