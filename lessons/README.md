# lessons — 학습·연습용 레슨

atugcc를 직접 고치고 빌드하면서 익히는 레슨 모음입니다. 같은 레슨을 **로컬 preset 빌드**와 **웹 플레이그라운드**(070-02)에서 같은 소스, 같은 CMake 타깃으로 빌드하고 실행합니다. 스펙: [070-01](/docs/specs/070_01_lesson_structure.md).

## 구조
```text
lessons/
  CMakeLists.txt              레슨 자동 발견: 타깃 lesson_<id>, 테스트 lesson.<id>
  intro.md                    웹 플레이그라운드 소개 글 (ⓘ 소개), 영어판 intro.en.md
  tags.toml                   태그 어휘: 레슨의 tags는 여기 있는 키만 씀 (070-10)
  units/<unit>/               재사용 유닛: unit.toml, README.md, <unit>.hpp
  tracks/<NN_track>/          트랙: track.toml
    <NN_lesson>/              레슨: lesson.toml, README.md(영어판 README.en.md는 선택), main.cpp (실행 파일 하나)
                              선택: *.cppm 모듈 인터페이스·파티션, 모듈 구현 유닛 *.cpp (070-14)
practice/lessons/             연습 사본(저장소 루트, git이 무시): 아래 "연습 공간" (070-16)
```
- **트랙**은 학습 순서입니다. `01_essentials`(core, 문법, 스레드·로그 관리)를 먼저, 그다음 `02_patterns`(상황에 맞는 패턴 적용과 변형)를 봅니다.
- **유닛**은 트랙과 무관하게 여러 레슨이 가져다 씁니다. 예: `jthread_worker`는 essentials의 `thread_and_log`와 patterns의 `device_state_machine`이 함께 씁니다.
- 라이브러리 헤더는 복사하지 않고 `lib:atugcc/...`로 참조합니다. 라이브러리를 고치면 레슨에 바로 반영됩니다.
- `gtest = true`인 레슨은 GoogleTest 프로그램입니다. 테스트 소스(`TEST`가 든 `.cpp`)를 `sources`에 두고, 진입점의 `main`이 `RUN_ALL_TESTS()`를 돌려줍니다. 예: [`testing`](tracks/01_essentials/16_testing/README.md) (spec 070-15).
- 레슨 폴더에는 C++20 모듈 파일도 둘 수 있습니다. 모듈 인터페이스·파티션 유닛은 `.cppm`, 모듈 구현 유닛(`module <이름>;`)은 `.cpp`입니다. 진입점(`sources`의 첫 항목)은 `.cpp`여야 합니다. 예: [`modules`](tracks/01_essentials/15_modules/lesson.toml) (spec 070-14).
- 순서는 폴더 이름의 숫자 접두사로 정합니다. essentials 트랙의 번호는 최종 순서 번호입니다([레슨 후보 목록](/docs/lesson_candidates.md)의 폴더 열, spec 070-03). 새 레슨은 마지막 번호 다음 번호로 폴더를 만들고, 다른 폴더는 옮기지 않습니다(spec 070-14 Assumption 2).

## 매니페스트
```toml
# lessons/tracks/02_patterns/01_device_state_machine/lesson.toml
id      = "device_state_machine"        # [a-z0-9_], 레슨끼리 유일 (유닛과는 같아도 됨)
title      = "..."
title_en   = "..."                       # 영어 제목. 없으면 check가 경고, 페이지는 한국어로 대신 보여 줌 (070-10)
summary    = "..."
summary_en = "..."                       # 영어 요약. summary가 있으면 같이 씀
sources    = ["main.cpp"]                # 첫 항목이 진입점. 반드시 한 줄로
uses       = ["unit:jthread_worker", "lib:atugcc/pattern/state.hpp"]
tags       = ["state", "tracer"]         # lessons/tags.toml의 키만. 웹 검색이 태그 이름과 별칭으로 찾음
gtest      = true                        # 선택, 최상위(표 [run] 위). GoogleTest 링크 + 단계 도우미 (070-15)

[run]                                   # 선택. 없으면 quick
profile = "quick"                       # "quick" | "long"
timeout = 300                           # 초, long에서만 의미 (1..1800)
build   = "release"                     # 선택. "release" | "debug", 없으면 long은 release, quick은 debug (웹 실행의 빌드 종류)
```
```toml
# lessons/units/jthread_worker/unit.toml
id       = "jthread_worker"
title    = "..."
title_en = "..."
files    = ["jthread_worker.hpp"]
uses     = ["lib:atugcc/core/logger.hpp"]   # 유닛도 다른 유닛·라이브러리를 참조할 수 있음
```
- `uses`는 웹에서 "관련 파일" 탭으로 열리는 목록입니다. 실제 컴파일 의존성은 `#include`와 `import`가 정합니다. 종류는 넷입니다: `unit:<유닛 id>`, `lib:<경로>`(`include/<경로>`), `mod:<경로>`(`modules/<경로>`, 예: `mod:atugcc/core.cppm` → `modules/atugcc/core.cppm`), `test:<경로>`(`tests/<경로>`, 예: `test:scenario/scenario.hpp` → `tests/scenario/scenario.hpp`).
  - 유닛: `#include "units/<unit>/<unit>.hpp"` (include 경로: `lessons/`)
  - 라이브러리: `#include "atugcc/..."` (include 경로: `include/`)
  - 라이브러리 모듈: `import atugcc.core;` (`uses`에 `mod:atugcc/core.cppm`)
  - 단계 도우미: `#include "scenario.hpp"` (`gtest = true`일 때 include 경로: `tests/scenario`, `uses`에 `test:scenario/scenario.hpp`)
- `sources`의 `.cppm`은 `lessons/CMakeLists.txt`가 자동으로 레슨 타깃의 `CXX_MODULES` file set에 넣고, 나머지(모듈 구현 유닛 포함)는 일반 소스로 넣습니다. 매니페스트에 따로 쓸 것은 없습니다. 레슨이 만드는 모듈의 이름은 `<레슨 id>`이거나 `<레슨 id>.`으로 시작합니다(예: `modules.geometry`, 파티션 `modules.geometry:rect`). 유닛은 모듈을 담을 수 없습니다(KI-039).
- CMake는 TOML을 읽지 못해서 `id`, `sources`, `profile`, `timeout`, `gtest`를 줄 단위 정규식으로 읽습니다. 이 키들은 한 줄에, 줄 머리에서 쓰세요(`gtest`는 표 `[run]` 위 최상위에).
- `gtest = true`: [`cmake/atugcc_googletest.cmake`](/cmake/atugcc_googletest.cmake)의 GoogleTest(`tests/`와 같은 v1.14.0)를 링크하고, include 경로 `tests/scenario`, `ATUGCC_SCENARIO_WORK_ROOT`(`out/build/<preset>/lessons/scenario_work`), sanitizer preset에서는 `ATUGCC_SANITIZED_BUILD`를 줍니다. 플레이그라운드 preset도 첫 configure 때 GoogleTest를 받으므로 네트워크가 필요합니다. 레슨의 테스트는 smoke test `lesson.<id>` 하나로 돌고, 모두 통과해야 0으로 끝납니다.
- `track.toml`도 `title_en`, `summary_en`을 받습니다.
- 태그 어휘 [`tags.toml`](tags.toml): 태그마다 `ko`, `en`(페이지에 보이는 이름)과 `aliases`(검색 동의어: C++ 이름, 다른 언어의 낱말)를 둡니다. 새 기능의 레슨이면 태그를 먼저 어휘에 더합니다. 한 이름(대소문자·유니코드 정규화 무시)은 한 태그에만 둡니다.

## 새 레슨 추가
1. 비슷한 레슨 폴더를 복사해 `tracks/<track>/<NN_name>/`을 만듭니다.
2. `lesson.toml`의 `id`, `title`, `title_en`, `summary`, `summary_en`, `sources`, `uses`, `tags`를 고칩니다.
3. `py -3 tools/lessons.py check` (Linux: `python3`)로 확인합니다. 스키마, id 중복, 없는 파일, `uses` 대상(`mod:`는 `modules/`, `test:`는 `tests/` 아래 파일), `gtest`가 bool이 아닌 경우, `gtest = true` 없이 `<gtest/…>`·`<gmock/…>`·`"scenario.hpp"`를 include한 경우(쓰는 유닛의 파일 포함), 유닛 순환, `tags.toml` 형식, 진입점(`sources`의 첫 항목)이 `.cppm`인 경우, 유닛 `files`의 `.cppm`, `sources`의 `.ixx`·`.mpp`·`.cxxm`(모듈 확장자는 `.cppm`만)을 오류로 검사하고, `#include`가 `uses`에 빠져 있을 때, `import atugcc.<area>;`인데 `uses`에 `mod:atugcc/<area>.cppm`이 없을 때, `gtest = true`인데 어떤 소스도 `<gtest/gtest.h>`를 include하지 않을 때, `"scenario.hpp"`를 include했는데 `uses`에 `test:scenario/scenario.hpp`가 없을 때, 레슨 소스의 모듈 이름이 `<레슨 id>`도 `<레슨 id>.…`도 아닐 때, `title_en`·`summary_en`이 없을 때, 태그가 어휘에 없을 때, 한 이름이 두 태그에 있을 때, `README.md`는 있는데 `README.en.md`가 없을 때, 소스(`sources`, 유닛 `files`)의 문자열·문자 리터럴에 한글이 있을 때(주석은 보지 않음) 경고합니다. 이 검사는 `lint_docs.py`에도 들어 있고, `lint_docs.py`는 `lessons/` 아래 Markdown(README, `intro.md`, `intro.en.md`)의 깨진 링크도 오류로 잡습니다.
4. 빌드하면 CMake 파일을 고치지 않아도 `lesson_<id>`와 테스트 `lesson.<id>`가 생깁니다. Windows 콘솔 UTF-8 설정(아래 "실행")도 함께 링크되므로 레슨 코드에 따로 쓸 것이 없습니다.

## 실행
| 무엇 | 명령 |
|---|---|
| 레슨 하나 빌드 | `py -3 .agent/scripts/build.py --preset <preset> --target lesson_<id>` |
| 실행 | `out/build/<preset>/bin/lessons/lesson_<id>` (Windows: `.exe`) |
| 모든 레슨 smoke test | `ctest --preset <preset> -L lesson` |
| 오래 걸리는 레슨 빼고 | `ctest --preset <preset> -LE long` |
| 레슨 빌드 끄기 | configure 때 `-DATUGCC_BUILD_LESSONS=OFF` |
| 레슨 인덱스(JSON) | `py -3 tools/lessons.py index` → `out/lessons/index.json` |

레슨 출력은 UTF-8입니다(`×`, `µs`, `⏱`). Windows 콘솔에서 직접 실행하면 레슨이 시작할 때 콘솔의 출력 코드 페이지를 UTF-8로 바꾸고, 정상 종료할 때 원래 값(예: cp949)으로 되돌립니다. 크래시나 강제 종료 뒤에는 바뀐 채로 남으니 `chcp 949`처럼 되돌리면 됩니다. 출력을 파일이나 파이프로 보내면(ctest, 웹 플레이그라운드) 아무것도 바꾸지 않습니다. 모든 `lesson_<id>`에 [`support/console_utf8.cpp`](support/console_utf8.cpp)가 링크되므로 레슨 코드에는 따로 쓸 것이 없습니다(spec 090-06).

## 연습 공간
연습 과제는 원본이 아니라 **연습 사본**에서 풉니다. 원본(`lessons/`)은 바뀌지 않으므로 git 작업 트리가 깨끗하게 남고, 언제든 원본으로 되돌릴 수 있습니다(spec [070-16](/docs/specs/070_16_practice_workspace.md)).

- **위치**: 저장소 루트의 `practice/`(git이 무시). 원본 경로를 그대로 비춥니다: `lessons/tracks/<track>/<lesson>/` → `practice/lessons/tracks/<track>/<lesson>/`, `lessons/units/<unit>/` → `practice/lessons/units/<unit>/`. 레슨 사본은 `lesson.toml`과 `sources`, 레슨이 쓰는 유닛마다 `unit.toml`과 `files`를 갖습니다. 유닛 사본은 그 유닛을 쓰는 레슨들이 같이 씁니다.
- **빌드**: 사본이 있는 레슨마다 CMake 타깃 `practice_<id>`(`bin/practice/`)가 생깁니다. include 경로는 `practice/lessons`가 먼저라서 유닛 사본이 원본 유닛보다 앞섭니다. `practice_<id>`는 전체 빌드에 들지 않고 smoke test도 없어서, 반쯤 고친 연습이 `build.py --test`를 깨지 않습니다. 새 사본은 다음 빌드가 찾습니다.
- **상태**: `practice/state.json`이 사본마다 원본과, 사본을 만들거나 되돌릴 때의 원본 sha를 적습니다. 그것과 비교해 `same`(그대로), `modified`(고침), `both`(고쳤는데 원본도 바뀜), `missing-origin`(원본 없음)으로 봅니다. 고치지 않은 사본은 원본이 바뀌면 저절로 새 원본을 받고, `lesson.toml`·`unit.toml` 사본은 늘 원본을 따릅니다(사본의 매니페스트는 고칠 수 없음). 연습 공간에 새 파일은 만들 수 없습니다.
- **되돌리기**: 파일 하나, 레슨 하나(유닛은 그대로), 유닛 하나 단위입니다. 덮어쓰는 사본은 `practice/backup/<YYYYMMDD-HHMMSS>[-n]/`에 먼저 남기고, 백업 폴더는 최근 10개만 둡니다.

| 무엇 | 웹 | 로컬 |
|---|---|---|
| 사본 만들기 | 연습 모드(기본)에서 레슨을 열면 | `py -3 tools/practice.py start <id>` |
| 상태 | 탭의 밑줄(고침), `⚠`(원본도 바뀜), 트리의 `✎` | `py -3 tools/practice.py status [<id>]` |
| 빌드·실행 | Run | `py -3 .agent/scripts/build.py --preset <preset> --target practice_<id>` 뒤 `out/build/<preset>/bin/practice/practice_<id>` |
| 원본과 비교 | 편집기 위의 "원본과 비교" | `git diff --no-index lessons/… practice/lessons/…` |
| 되돌리기 | ↺ 되돌리기(파일), 레슨 되돌리기 | `py -3 tools/practice.py reset <id>`, `--unit <id>`, `--file <사본 경로>` |
| 사본 폴더 | — | `py -3 tools/practice.py path <id>` |

레슨을 **고쳐서 저장소에 남기려면**(레슨 작성) 웹 위쪽의 모드를 **원본 편집**으로 바꿉니다. 그 모드에서는 지금처럼 `lessons/`의 파일을 저장하고 `lesson_<id>`를 빌드합니다. 위쪽 막대와 탭에 경고색이 붙습니다.

## 연습 과제 정의
README의 "연습" 항목마다 레슨 폴더의 `exercises.toml`에 과제 하나를 정의하면, 연습 사본을 Run할 때마다 자동으로 확인합니다(spec [070-17](/docs/specs/070_17_exercise_check.md)). 과제 문장은 README에 그대로 두고, `exercises.toml`은 id, 짧은 제목(두 언어), 확인 규칙, 힌트와 해설만 갖습니다. 예: [`01_lambda_capture/exercises.toml`](tracks/01_essentials/01_lambda_capture/exercises.toml).

```toml
[[exercise]]
id       = "remove_mutable"          # [a-z0-9_], README 연습 순서와 같은 순서
title    = "mutable을 지우고 오류 읽기"
title_en = "Remove mutable and read the error"
build    = "fail"
build_expect = ['captured by copy in a non-mutable lambda|C3491']   # Clang | MSVC 문구
source   = [{ file = "lambda_capture.hpp", lacks = ['\[count = start\]\s*\(\)\s*mutable'] }]
fail_hint    = "…"        # 실패 메시지 뒤에 붙는 한 줄 (fail_hint_en)
hint     = """…"""       # Markdown, 패널에서 "힌트"를 눌러야 보임 (hint_en)
answer   = """…"""       # Markdown, "해설" (answer_en)
```

| 규칙 | 값 | 통과 조건 |
|---|---|---|
| `build` | `"ok"`(기본) \| `"fail"` | 빌드가 성공 / 실패 |
| `build_expect` | 정규식 목록 (`build = "fail"`일 때만) | 빌드 로그에 정규식마다 맞는 줄이 있음 |
| `exit` | 정수(기본 0) \| `"nonzero"` \| `"any"` | 종료 코드가 그 값 / 0이 아님(신호 포함) / 상관없음 (`build = "fail"`이면 쓰지 않음) |
| `expect` | 정규식 목록 | stdout에 정규식마다 맞는 줄이 있음 |
| `forbid` | 정규식 목록 | stdout에 맞는 줄이 없음 |
| `source` | `[{file, has = [...], lacks = [...]}]` | 연습 사본 파일에 `has`마다 맞는 줄이 있고 `lacks`에 맞는 줄이 없음. `file`은 레슨 `sources`나 쓰는 유닛 `files`의 이름 |

- 규칙은 모두 맞아야 통과합니다. 정규식은 Python `re`이고 줄 단위 `re.search`입니다(줄 끝은 LF로 맞춘 뒤). 컴파일러 문구는 Clang(웹)과 MSVC(로컬)를 둘 다 `|`로 받거나 공통 낱말을 고릅니다.
- 규칙이 하나도 없으면 **관찰 과제**입니다: 사용자가 패널에서 "했음"으로 표시합니다(ASan, 로컬 리포트처럼 웹에서 확인할 수 없는 과제).
- 자동 과제는 연습 사본(레슨 또는 유닛) 중 하나가 원본과 달라야 통과합니다. Stop이나 시간 초과로 끝난 Run에서는 통과하지 않고, 출력이 상한을 넘겨 잘리면 `expect`·`forbid`가 있는 과제는 "확인하지 못함"입니다.
- 단계가 여러 개인 항목은 id 끝에 `_a`, `_b`를 붙여 나눕니다. `lessons.py check`는 README "연습"의 번호 항목 수와 과제 수(하위 과제는 하나로)를 비교해 다르면 WARN입니다. 스키마, 정규식, 없는 파일, 중복 id는 ERROR, 영어 필드가 빠지거나 빈 문자열에 맞는 정규식은 WARN입니다.
- **원본 통과 검사**: 고치지 않은 원본이 어떤 자동 과제도 통과하지 않아야 합니다(원본 출력에 이미 있는 줄을 `expect`로 쓰는 실수). 레슨을 빌드한 뒤 CTest 테스트 `lesson.<id>.exercises_verify`(label `lesson`)가 확인합니다.
- **진행 기록**: `practice/progress.json`. 통과는 한 번 기록되면 남습니다(코드를 다른 과제를 위해 바꾸거나 레슨을 되돌려도). 패널의 "기록 지우기"가 그 레슨의 기록만 지웁니다.

| 무엇 | 웹 | 로컬 |
|---|---|---|
| 과제 목록·힌트·해설 | 오른쪽 **연습** 탭 | `py -3 tools/exercises.py list <id>` |
| 확인 | 연습 모드의 Run마다 | `py -3 tools/exercises.py check <id> --preset <preset>` (연습 사본을 빌드·실행하고 표로 결과, 같은 기록에 씀) |
| 원본 통과 검사 | — | `py -3 tools/exercises.py verify <id> --preset <preset>`, 또는 `build.py --test --label lesson` |

`check`와 `verify`는 그 OS의 preset만 받습니다(Windows에서 `linux-*` preset은 WSL에서 `python3 tools/exercises.py …`). Windows Debug 빌드에서 잡히지 않은 예외로 `abort()`가 불리면 CRT 대화상자가 떠서 누를 때까지 프로그램이 끝나지 않습니다([KI-050](/docs/known_issues.md)).

## 실행 프로필
- `quick`(기본): 짧은 예제입니다. smoke test 제한은 10초이고, 웹(070-02)에서도 10초로 제한합니다.
- `long`: 성능 측정처럼 오래 걸리는 레슨입니다. 제한은 `timeout`이고, ctest 라벨 `long`이 붙습니다.
  - 웹에서는 최적화 빌드(`linux-x64-playground-release`, RelWithDebInfo)로 실행합니다. Debug(-O0) 시간은 성능 판단을 왜곡하기 때문입니다. 최적화 영향을 비교하는 연습에서는 `build = "debug"`를 씁니다.
  - stdout·stderr는 합쳐 8 MiB까지 받고, 화면은 최근 5,000줄을 유지합니다.
  - [070-06](/docs/specs/070_06_long_run_timings.md)
- 웹의 **길게 실행** 토글로 이번 실행만 다른 프로필로 돌릴 수 있습니다. 매니페스트는 바뀌지 않습니다.
- 웹 실행의 trace 파일은 1 GiB가 상한입니다. 넘으면 실행이 중지됩니다(span을 너무 촘촘히 잰 경우).

## 웹 플레이그라운드에서 보이는 방식
`py -3 tools/playground.py --open`(또는 VS Code 태스크 `Playground: start`)으로 띄운 페이지([web/README.md](/web/README.md))는 이 폴더를 그대로 씁니다.
- 소개: 상단 **ⓘ 소개**, 그리고 레슨을 고르지 않고 연 첫 화면은 [`intro.md`](intro.md)입니다(영어 화면에서는 [`intro.en.md`](intro.en.md), 읽지 못하면 `intro.md`). 일반 Markdown 파일이라 고쳐도 프론트엔드를 다시 빌드할 필요가 없습니다. 패널 위의 경로를 누르면 README와 소개 글을 에디터에서 열어 고칠 수 있습니다. 링크는 README와 같은 규칙(`.md`는 패널, 다른 파일은 에디터)으로 열리고, 저장소 루트 기준(`/lessons/...`)으로 씁니다. 레슨 폴더 이름을 바꾸면 두 소개 파일의 링크도 고칩니다(깨진 링크는 `lint_docs.py`가 잡습니다).
- 왼쪽 트리: 트랙 순서대로 레슨(`title`, 영어 화면에서는 `title_en`), 그 아래 유닛과 "사용: …"(이 유닛을 쓰는 레슨, `uses`를 따라간 결과).
- 검색(070-10): 트리 위 검색창이 id, 제목·요약(두 언어), 태그와 그 이름·별칭, `uses`(유닛 id, `lib:` 헤더 경로), 트랙 제목으로 레슨을, id, 제목·요약, `files`, `uses`로 유닛을 거릅니다. 그래서 `title_en`과 태그가 맞아야 영어로도, 기능 이름으로도 찾힙니다.
- 에디터 탭: `sources`, 그리고 `uses`를 따라간 파일(유닛 헤더, `lib:` 헤더). `lessons/` 밖 파일(`include/…`)은 🔒 읽기 전용입니다.
- README 탭: 레슨 폴더의 `README.md`(영어 화면에서는 `README.en.md`가 있으면 그것). 위에 레슨의 태그가 나오고, 누르면 그 태그로 검색합니다. 상대 링크로 다른 README나 소스를 열 수 있습니다.
- 모드(070-16): 위쪽의 **연습**(기본)은 연습 사본(`practice/lessons/…`)을 탭에 열고 `practice_<id>`를 빌드합니다. README 링크도 사본이 있으면 사본을 엽니다. 사본이 없는 `lessons/` 파일(다른 레슨으로 가는 링크, 이 레슨이 쓰지 않는 유닛)은 🔒 읽기 전용입니다. **원본 편집**은 `lessons/`의 파일을 열고 저장합니다. 위의 "연습 공간"을 보세요.
- Run: 수정한 탭을 저장한 뒤(연습 모드는 사본, 원본 편집 모드는 `lessons/`) `practice_<id>` 또는 `lesson_<id>`를 빌드해 실행합니다. 연습 모드의 실행 디렉터리는 사본 폴더입니다. preset은 Debug 빌드면 `linux-x64-playground`, Release 빌드(long 프로필의 기본, 또는 `build = "release"`)면 `linux-x64-playground-release`입니다. 출력은 실행 중에 줄 단위로 나옵니다(`stdbuf -oL`). 레슨이 `std::ios::sync_with_stdio(false)`를 쓰면 줄 단위 출력이 꺼져 끝날 때 한꺼번에 나옵니다.
- Events·Diagrams 탭: Tracer를 쓰는 레슨이면 이벤트(소스 줄로 이동)와 Mermaid 다이어그램이 나옵니다. 다이어그램은 Tracer 소멸자가 쓰므로 정상 종료한 경우에만 생깁니다.
- Timings 탭(070-06): span(`timeScope`, `recordSpan`)을 쓰는 레슨이면 실행 중에 구간별 시간이 나옵니다.
  - 열: count, total, mean, p50, p95, min, max, 이전 실행 대비 mean 변화율. 행의 키에 줄 번호가 들어 있으므로, span보다 위에서 줄을 더하거나 지우면 이전 실행과 비교되지 않습니다(바꿀 줄은 주석 처리하는 편이 낫습니다).
  - 에디터의 span 시작 줄 끝에도 `⏱ 평균 avg ×횟수`가 나옵니다.
  - 상단의 측정기 선택(`wall`/`cpu`)은 `ATUGCC_SPAN_METER`로 전달됩니다.
  - 예: [`span_timing`](tracks/01_essentials/14_span_timing/README.md)

## 레슨 작성 안내
- 레슨은 Windows(MSVC)와 Linux(Clang 20, libstdc++ 14) preset 모두에서 경고 없이 빌드돼야 합니다. 플랫폼 전용 API(`memory_dump`, 데스크톱 콘솔 sink)는 쓰지 않습니다.
- 소스와 README는 UTF-8로 씁니다.
- **프로그램 출력은 영어로 씁니다**(stdout, stderr, 로그, Tracer 이벤트, 다이어그램 문구). 페이지 언어와 상관없이 같습니다(070-10 Assumption 14).
- 영어 README는 같은 폴더의 `README.en.md`입니다. 레슨과 유닛마다 둡니다(없으면 check가 경고, 영어 화면에서는 한국어 README를 안내 줄과 함께 보여 줌). 한국어판과 절, 연습 과제, 코드 블록을 같게 두고, 영어판의 링크는 영어판이 있는 README면 `README.en.md`를 가리킵니다.
- **코드 주석은 한국어와 영어 둘 다** 씁니다(spec 070-03 Assumption 12). 한국어 주석 줄 바로 아래에 같은 뜻의 영어 줄을 둡니다. 블록 주석은 한국어 문단 다음에 영어 문단이고, `[학습]`은 영어 쪽에서 `[Learn]`입니다.
  ```cpp
  // 값 캡처: 두 counter 는 서로의 count 를 모른다
  // By-value capture: the two counters do not know each other's count
  ```
- Tracer를 쓰는 레슨은 환경변수 `ATUGCC_TRACE_OUT`만 설정하면 이벤트가 JSON Lines로 나옵니다([020-05](/docs/specs/020_05_tracer_event_stream.md)). 웹은 이것으로 이벤트와 다이어그램을 보여 줍니다. 레슨 코드는 고칠 필요가 없습니다.
- README에는 무엇을 보여 주는지, 실행 방법, 짧은 연습 과제 2–3개를 적습니다.

## 성능 측정 레슨 작성
코드 구간의 시간은 Tracer의 span으로 잽니다([020-06](/docs/specs/020_06_tracer_span_timing.md)). 예제 레슨: [`span_timing`](tracks/01_essentials/14_span_timing/README.md).
- 매니페스트에 `[run] profile = "long"`과 `timeout`을 둡니다. 웹은 최적화 빌드로 실행하고 Timings 탭에 실행 중 시간을 보여 줍니다(070-06).
- 정해진 작업량 대신 **정해진 시간** 동안 반복하게 쓰면, Debug·sanitizer smoke test에서도 실행 시간이 일정합니다(`span_timing`의 `kRunFor`).
- 계산 결과를 출력 등에 쓰세요. 쓰지 않는 결과는 최적화 빌드가 계산째 지울 수 있습니다.
```cpp
viz::Tracer tracer;
{
    auto span = tracer.timeScope("parse");   // 스코프가 끝날 때 기록, 위치는 이 줄
    parse(input);
}
std::cout << tracer.formatTimings();          // (위치, 라벨, 측정기)별 count, total, mean, min, max
```
- **측정기**: 기본은 `wall`(경과 시간)입니다. `ATUGCC_SPAN_METER=cpu`로 실행하거나 `tracer.setSpanMeter(viz::makeSpanMeter("cpu"))`로 바꾸면 스레드 CPU 시간을 잽니다. 둘을 비교하면 대기·I/O와 계산을 구분할 수 있습니다. Windows의 `cpu`는 스케줄러 틱(약 15.6 ms) 단위로 올라가서, 짧은 구간은 대개 0이고 틱이 걸리면 약 15.6 ms로 나옵니다. Linux는 ns 단위입니다.
- **다른 방식으로 잰 값**: `(void)tracer.recordSpan("io", duration, loc, "perf");`처럼(반환값은 `core::Result`, `[[nodiscard]]`) 측정기 이름을 붙여 넣으면 같은 표와 스트림에 따로 집계됩니다.
- **핫 루프 안쪽 대신 바깥 구간을 재세요.** span 하나에도 비용이 있습니다(아래 표): sink가 없으면 수백 ns, 이벤트 스트림을 켜면 수 µs입니다. 그보다 짧은 일을 하나씩 재면 측정 비용이 결과를 덮습니다. 루프 전체를 한 구간으로 재고 반복 횟수로 나누세요.
- **스트림 flush**: 이벤트 스트림(`ATUGCC_TRACE_OUT`)을 켜고 span을 많이 쓰면 `ATUGCC_TRACE_FLUSH_MS=100`을 함께 설정합니다. 기본(0)은 줄마다 flush합니다. 간격을 두면 프로그램이 조용해진 뒤 마지막 줄이 늦게 보일 수 있습니다(KI-016).
- **수명**: `ScopedSpan`은 Tracer보다 짧은 스코프에서만 씁니다.

span 하나의 기록 비용(`tests/pattern/span_cost_probe.cpp`, Release, 200,000회 평균, 2026-10-29 측정, 측정기 가상 호출 포함):

| 구성 | Windows (MSVC) | Linux (GCC 13, WSL2) |
|---|---|---|
| 측정기 읽기 1회, `wall` | 18 ns | 23 ns |
| 측정기 읽기 1회, `cpu` | 129 ns | 213 ns |
| span, `wall`, sink 없음 | 278 ns | 148 ns |
| span, `cpu`, sink 없음 | 495 ns | 546 ns |
| span, `wall`, JSON sink + flush 100 ms | 4.1 µs | 2.4 µs |
| span, `wall`, JSON sink, 줄마다 flush | 6.9 µs | 3.0 µs |

값은 기계마다 다릅니다. 직접 재려면 `py -3 .agent/scripts/build.py --preset <os>-x64-release --target span_cost_probe` 후 `out/build/<preset>/bin/span_cost_probe`를 실행합니다.
