---
id: 070-14
title: essentials modules 레슨(`.cppm` 레슨 소스 지원)과 `format_text`의 `std::print` 단계
depends_on: [070-13]
unblocks: []
approved: 2026-11-04
---

# Spec 070-14: essentials modules 레슨(`.cppm` 레슨 소스 지원)과 `format_text`의 `std::print` 단계

## 0. Assumptions (please review)
| # | Decision | Rejected alternative | Why |
|---|---|---|---|
| 1 | **범위는 셋이다**: (a) 레슨 소스에 `.cppm`(모듈 인터페이스 유닛)을 쓸 수 있게 한다(`lessons/CMakeLists.txt`, `tools/lessons.py`, 웹의 파일 쓰기와 편집기), (b) 새 레슨 `modules`, (c) `format_text`에 `std::print` 단계를 더하고 연습 3을 MSVC 전용이 아닌 연습으로 바꾼다(KI-033) | (a)를 따로 작업으로; (c)를 따로 작업으로 | BACKLOG 줄(070-13 Assumption 16)의 범위 그대로다. `.cppm` 지원을 처음 쓰는 곳이 이 레슨이라 같이 검증해야 한다. (c)는 한 단계와 README라 작다 |
| 2 | **트랙 안의 자리는 `15_modules`**(essentials 끝)이다. 기존 폴더는 옮기지 않는다 | 문법 묶음(`01_`–`08_`) 안에 넣고 `09_`–`14_`를 하나씩 뒤로 | 폴더 번호는 최종 순서이고 새 레슨은 다른 폴더를 옮기지 않는다(070-03 Assumption 3, `lessons/README.md`). 이 레슨은 `import atugcc.core;`로 `Expected`/`CoreError`(04 레슨)를 쓰므로 앞 레슨들 뒤가 자연스럽다. **순서를 바꾸는 것은 사용자 결정**이라 다른 자리를 원하면 알려 달라 |
| 3 | 레슨 id와 태그는 `modules`. 레슨이 만드는 **모듈 이름은 `<레슨 id>.`으로 시작한다**(`modules.geometry`). `lessons.py check`가 어긋나면 경고한다 | 짧은 이름(`geometry`) | 레슨마다 실행 파일이 따로라 이름이 같아도 지금은 빌드되지만, 접두사가 있으면 `atugcc.*`, 표준의 예약 이름(`std…`), 다른 레슨의 모듈과 겹칠 일이 없다. 규칙이 하나라 검사도 간단하다 |
| 4 | **파일 네 개**: `main.cpp`(진입점, import만), `geometry.cppm`(주 인터페이스 `export module modules.geometry;`), `geometry_rect.cppm`(파티션 `export module modules.geometry:rect;`), `geometry.cpp`(구현 유닛 `module modules.geometry;`). 유닛은 만들지 않는다 | `.cppm` 하나에 모두 | [`modules.md`](/docs/cpp_evolution/modules.md)가 설명하는 세 종류(인터페이스, 파티션, 구현 유닛)를 실제로 보이는 최소 구성이다. 구현 유닛이 있어야 연습 2(무엇이 다시 컴파일되는가)가 된다 |
| 5 | **CMake**: `sources` 중 확장자가 `.cppm`인 것은 `target_sources(lesson_<id> PRIVATE FILE_SET CXX_MODULES BASE_DIRS <레슨 폴더> FILES …)`로, 나머지(구현 유닛 `.cpp` 포함)는 지금처럼 `add_executable`의 소스로 넣는다. 구현 유닛은 스캔(070-13, 항상 켬)이 찾는다 | 모든 소스를 file set에; 레슨용 모듈 라이브러리 타깃을 따로 | CMake에서 인터페이스·파티션은 `CXX_MODULES` file set에 있어야 하고, 구현 유닛은 일반 소스다. 실행 파일 하나 = 레슨 하나(070-01)를 유지한다 |
| 6 | 지원하는 모듈 확장자는 **`.cppm` 하나**다. `.ixx`(MSVC 관례), `.mpp`, `.cxxm`은 받지 않는다(`lessons.py`가 레슨 `sources`의 이 확장자를 ERROR로) | MSVC에서 `.ixx`도 | CMake는 두 컴파일러 모두에서 `.cppm`을 모듈로 다룬다. 레슨은 두 호스트에서 같은 소스다. 프로젝트의 모듈 파일도 `.cppm`이다(impl.md §2a) |
| 7 | **`lessons.py check` 규칙 추가**(§2.3): 진입점(`sources[0]`)이 `.cppm`이면 ERROR, 유닛 `files`에 `.cppm`이면 ERROR, 모듈 선언의 이름이 `<id>`나 `<id>.`으로 시작하지 않으면 WARN, `import atugcc.<area>;`인데 `uses`에 `mod:atugcc/<area>.cppm`이 없으면 WARN. `.cppm`도 한글 리터럴 검사와 `#include`/`uses` 검사를 받는다(`CPP_SUFFIXES`에 더함) | 검사 없이 빌드 오류에 맡기기 | 진입점은 웹 인덱스의 `entry`이고 `add_executable`의 첫 소스다. 유닛은 헤더처럼 include되므로 모듈을 담을 타깃이 없다(KI-039). 나머지 둘은 기존 `#include`/`uses` 경고와 같은 성격이다 |
| 8 | **`uses`에 새 접두사 `mod:`**: `mod:atugcc/core.cppm`은 `modules/atugcc/core.cppm`을 가리킨다(`lib:`가 `include/`를 가리키는 것과 같은 방식). 웹의 "관련 파일" 탭으로 읽기 전용으로 열린다 | `lib:`가 `modules/`도 찾게; 관련 파일에 안 보이기 | 모듈 인터페이스는 `include/` 밖에 있다(070-13 Assumption 6). `lib:` 하나가 두 폴더를 찾으면 같은 이름이 두 곳에 있을 때 모호하다. 레슨이 import하는 모듈의 export 목록을 보여 주는 것이 레슨의 일부다 |
| 9 | **웹**: [`files.py`](/web/server/files.py)의 새 파일 확장자에 `.cppm`을 더한다(쓰기는 지금처럼 `lessons/` 아래만). 편집기 [`editor.ts`](/web/frontend/src/editor.ts) `languageOf`가 `.cppm`을 `cpp`로 칠한다. 진단 정규식(`runner.py`)은 그대로다(Clang의 모듈 오류도 `file:line:col: error:` 형식) | 웹은 그대로 | 웹에서 새 파티션 파일을 만들 수 없으면 연습이 막힌다. 구문 강조가 없으면 `.cppm`이 일반 텍스트로 보인다 |
| 10 | **레슨 단계**(§2.2): (1) import한 모듈의 export된 타입·함수(정의는 구현 유닛), (2) `export import :rect;`로 다시 내보낸 파티션의 함수, (3) 매크로는 import로 오지 않음(`#ifdef`의 결과를 출력), (4) `import atugcc.core;`로 라이브러리 쓰기, 그리고 import는 전이되지 않음(`geometry`가 `atugcc.core`를 import해도 `main.cpp`가 `CoreError`를 쓰려면 직접 import). export하지 않은 이름(`detail::`)이 보이지 않는 것은 컴파일 오류라 출력이 아니라 연습 1로 둔다 | export하지 않은 이름을 `requires`로 검사해 출력 | 템플릿 밖의 `requires` 식에서 이름 찾기가 실패하면 SFINAE가 아니라 프로그램이 ill-formed다. 보이지 않는다는 것은 컴파일 오류 자체가 가장 분명한 증거다 |
| 11 | **연습**: (1) `main.cpp`에서 export하지 않은 `modules::geometry::detail::clampSide`를 불러 오류 메시지 읽기, (2) `geometry.cpp`(구현 유닛)만 고치고 다시 빌드하면 그 파일만 컴파일되고, `geometry.cppm`(인터페이스)을 고치면 `main.cpp`도 다시 컴파일되는 것을 빌드 로그에서 보기, (3) `main.cpp`의 `import atugcc.core;`를 지워 오류를 보고, `geometry.cppm`을 `export import atugcc.core;`로 바꿔 고치기(그 대가: `geometry`를 import하는 모든 곳에 core 이름이 들어옴). **3의 앞 절반(오류)은 Clang에서만 난다**: MSVC 19.51은 `geometry.cppm`의 export하지 않은 import의 이름을 `main.cpp`에 보여 주어(표준에 어긋남) 그대로 빌드한다(DEV 리뷰, 사용자 결정 2026-11-04). README는 Clang(Linux preset, 웹 플레이그라운드)에서 해 보라고 하고 MSVC의 동작을 적는다 | include 순서 바꾸기 연습 | include-before-import는 실패가 컴파일러·헤더 조합에 따라 나기도 하고 안 나기도 해서(070-13 Assumption 11) 연습 결과를 약속할 수 없다. README의 규칙 설명과 `main.cpp`의 주석으로만 둔다 |
| 12 | **`format_text` 7단계 `std::print`**: `#include <print>`. (a) 2단계 표의 한 행을 `std::println`으로 다시 출력해 `std::cout << std::format(…) << '\n'`과 같은 줄임을 보이고, (b) `Vec2` formatter가 `std::println`에도 그대로 쓰이고(`{:.1}`), (c) `std::print(stdout, …)`로 스트림을 고른다. `std::cout`과 섞어도 순서가 맞는 것은 `std::cout`이 기본으로 C stdio와 동기화되기 때문(`sync_with_stdio(true)`)이라고 주석과 README에 적는다. 출력은 ASCII | `std::print(stderr, …)`도; 1–6단계를 모두 `std::print`로 바꾸기 | stderr는 웹과 ctest에서 stdout과 합쳐질 때 순서가 보장되지 않는다. 1–6단계는 `std::format`을 배우는 단계라 그대로 두고, 바꿔 보는 것은 연습 3이 한다 |
| 13 | **`format_text` 연습 3**(새 내용): 2단계의 표를 `std::println`으로 바꿔 보고(`<<`와 `'\n'`이 없어짐), 6단계의 실행 시간 문자열 `bad_pattern`을 `std::println`에 넘기면 컴파일 오류가 나는 것 보기(`std::print`도 `std::format_string`을 받음). 실행 시간 형식의 출력 함수 `std::vprint_unicode`는 README에 한 줄로만 | 옛 연습 3(MSVC에서만 `<print>`) 유지 | KI-033 Next 그대로다. 두 툴체인 모두 `<print>`가 있다(070-13에서 시험) |
| 14 | **KI-033은 닫지 않는다**: `std::print` 부분이 끝났다고 Update를 적고 상태는 PLANNED, Next는 libstdc++ 15를 기다리는 range 포맷·파이프 `ranges::to`·`std::forward_like`만 남긴다 | KI-033 닫기 | 남은 항목이 있다(KI-033 2026-11-04 Update) |
| 15 | 새 레슨은 070-03의 규칙을 따른다: `profile = "quick"`, 출력 영어, 주석은 한국어 줄 + 영어 줄, `README.md`와 `README.en.md`, 두 preset에서 경고 없이 빌드, 플랫폼 전용 API 없음 | — | 070-03 Assumption 9·10·12, 070-12 Assumption 3 |
| 16 | **진행 순서**: 070-14 다음은 040-02(이미 `agent_todo.md` 진행 순서 A.5). 이 스펙은 순서를 바꾸지 않는다 | — | 순서는 사용자 결정 |

## 1. Objective
070-13이 두 호스트에서 C++20 모듈을 항상 켜고 `import atugcc.core;`를 만들었지만, 그것을 배우는 레슨이 없고 레슨 소스로 모듈 인터페이스(`.cppm`)를 쓸 수도 없다. 이 작업은 레슨 빌드·검사·웹이 `.cppm`을 다루게 하고, 그 첫 사용자로 essentials 마지막 레슨 `modules`를 만든다: 자기 모듈을 인터페이스·파티션·구현 유닛으로 나누고, 라이브러리를 `import`로 쓰고, include와 다른 점(매크로, 전이되지 않는 import, 다시 컴파일되는 범위)을 출력과 연습으로 확인한다. 같이 `format_text`에 이제 두 툴체인에서 되는 `std::print` 단계를 더한다(KI-033).

## 2. Requirement Details

### 2.1 트랙 안의 자리
| 폴더 | 레슨 id | 후보 | 상태 |
|---|---|---|---|
| `01_lambda_capture` – `14_span_timing` | (기존 14개) | | 그대로 (`02_format_text`만 7단계 추가) |
| `15_modules` | `modules` | E15 C++20 모듈 | **새로** |

[`lesson_candidates.md`](/docs/tasks/lesson_candidates.md) essentials 표에 E15 행을 더한다(비교: `#include`·include guard·PCH → named module, 출처 070-13, 기존 자료 `modules/atugcc/core.cppm`, `tests/modules/`, `modules.md`).

### 2.2 새 레슨 `modules`
`lessons/tracks/01_essentials/15_modules/lesson.toml`:
```toml
id         = "modules"
title      = "C++20 모듈: 인터페이스, 파티션, 구현 유닛과 import atugcc.core"
title_en   = "C++20 modules: interfaces, partitions, implementation units, and import atugcc.core"
summary    = "자기 모듈을 나눠 만들고 라이브러리를 import로 쓰며, include와 다른 점(매크로, 전이되지 않는 import)을 출력으로 본다"
summary_en = "Split your own module into units, use the library through import, and see how it differs from include (macros, non-transitive import) through output"
sources    = ["main.cpp", "geometry.cppm", "geometry_rect.cppm", "geometry.cpp"]
uses       = ["mod:atugcc/core.cppm", "lib:atugcc/core/error.hpp"]
tags       = ["modules", "error"]
```

파일(주석 규칙은 Assumption 15):
- `geometry_rect.cppm`: 파티션. `module;` + `#include <format>`, `#include <string>`, 그다음 `export module modules.geometry:rect;`. export: `namespace modules::geometry { struct Rect { double width; double height; }; std::string describe(const Rect&); }`(`describe`는 파티션 안에서 `inline`으로 정의). 타입과 그 글자 표현이 한 파티션에 있다. 파티션은 자기 주 인터페이스를 import할 수 없으므로(순환) `Rect`를 쓰는 `describe`는 `Rect`와 같은 파티션에 둔다.
- `geometry.cppm`: 주 인터페이스. global module fragment 없음(표준 헤더를 include하지 않으면 필요 없다는 것을 보임). `export module modules.geometry;`, `export import :rect;`, `import atugcc.core;`(export하지 않음). export: `double area(const Rect&); atugcc::core::Expected<Rect> makeRect(double w, double h);`. export하지 않음: `namespace modules::geometry::detail { double clampSide(double); }`. 모듈 안의 `#define GEOMETRY_UNIT_CM 1`(3단계용, 주석: 모듈은 매크로를 내보내지 않는다).
- `geometry.cpp`: `module modules.geometry;`(구현 유닛, 주 인터페이스의 선언이 보임). `area`, `makeRect`(`w <= 0` 또는 `h <= 0`이면 `std::unexpected(CoreError::InvalidArgument)`), `detail::clampSide`의 정의.
- `main.cpp`: `#include <iostream>`, `#include <format>`, … 를 **모두 먼저**, 그다음 `import modules.geometry;`, `import atugcc.core;`. `#include "atugcc/…"`는 없다.

출력 단계(영어, 두 OS에서 같음):
1. `== 1. import a module ==`: `makeRect(3, 4)`로 만든 `Rect`의 `area` = `12`. 줄에 "defined in geometry.cpp (implementation unit)".
2. `== 2. partition re-exported ==`: `describe(rect)` = `Rect 3 x 4`. `describe`는 `:rect` 파티션에 있고(파티션은 주 인터페이스의 `area`를 볼 수 없어 넓이는 쓰지 않는다) 주 인터페이스의 `export import :rect;`로 보인다.
3. `== 3. macros do not cross import ==`: `#ifdef GEOMETRY_UNIT_CM`의 결과 `GEOMETRY_UNIT_CM is not defined in main.cpp`.
4. `== 4. import atugcc.core ==`: `makeRect(-1, 2)`의 오류를 `atugcc::core::to_string(error)`로 출력(`InvalidArgument` 계열 문자열, 라이브러리 값 그대로). "main.cpp imports atugcc.core itself: geometry's import is not re-exported".

README(두 판): `#include`와 모듈의 비교 표(파싱 횟수, 매크로, 순서 의존, 숨길 수 있는 것), 세 종류의 유닛과 이 레슨의 파일, CMake에서 `.cppm`이 `FILE_SET CXX_MODULES`로 들어간다는 것(`lessons/CMakeLists.txt`가 자동으로), include-before-import 규칙과 이유, `import std;`를 아직 안 쓰는 이유(KI-036), 로컬 편집기가 `import`에 빨간 줄을 그을 수 있음(KI-037, 빌드는 됨), 연습 3개(Assumption 11). 해설 링크 [`modules.md`](/docs/cpp_evolution/modules.md).

### 2.3 `.cppm` 레슨 소스 지원
| 곳 | 바꾸는 것 |
|---|---|
| [`lessons/CMakeLists.txt`](/lessons/CMakeLists.txt) | `_sources`를 확장자로 나눔: `.cppm` → `target_sources(lesson_${_id} PRIVATE FILE_SET CXX_MODULES BASE_DIRS "${_dir}" FILES …)`, 나머지 → `add_executable`. 머리 주석에 한 줄(spec 070-14) |
| [`tools/lessons.py`](/tools/lessons.py) `CPP_SUFFIXES` | `.cppm` 추가 |
| `tools/lessons.py` `check` | ERROR: `sources[0]`이 `.cppm`; 유닛 `files`에 `.cppm`; 레슨 `sources`에 `.ixx`/`.mpp`/`.cxxm`; `uses`의 `mod:<name>`에 `modules/<name>` 파일이 없음(경로 검사는 `lib:`와 같음); `uses` 접두사 오류 메시지에 `mod:` 추가. WARN: `sources`의 모듈 선언(`export module X`, `module X`, 파티션 `X:p`)에서 `X`가 `<id>`도 `<id>.…`도 아님; `import atugcc.<area>;`인데 전이 `uses`에 `mod:atugcc/<area>.cppm` 없음(유닛이 `mod:`를 갖는 것은 허용, 전이 계산은 `lib:`와 같음) |
| `tools/lessons.py` `ref_files` / `index` | `mod:<name>` → `modules/<name>` |
| [`tools/test_lessons.py`](/tools/test_lessons.py) | 위 규칙마다 한 경우, `.cppm` 리터럴의 한글 WARN, 인덱스의 `mod:` 경로 |
| [`web/server/files.py`](/web/server/files.py) | `NEW_FILE_SUFFIXES`에 `.cppm`, 머리 docstring |
| [`web/server/test_server.py`](/web/server/test_server.py) | `lessons/` 아래 새 `.cppm` 쓰기 성공, `include/`·`modules/` 아래 쓰기 거부 |
| [`web/frontend/src/editor.ts`](/web/frontend/src/editor.ts) | `languageOf`: `cppm` → `cpp`(+ 프런트엔드 단위 테스트가 있으면 한 줄) |

모듈 선언 찾기 정규식은 줄 머리의 `export module` / `module` 다음 이름(`[A-Za-z_][\w.]*`)과 선택적 `:partition`이다. global module fragment의 `module;`은 이름이 없어 건너뛴다. 주석·문자열 안은 `hangul_literals`처럼 건너뛰지 않아도 된다(줄 머리 기준, 오탐은 WARN 하나).

### 2.4 `format_text` 7단계
- `main.cpp`: `#include <print>`. 6단계 뒤에 `== 7. std::print / std::println (C++23) ==`: `std::println("{}", formatRow(kRows[0]))`와 같은 행을 `std::cout << … << '\n'`으로도 출력(두 줄이 같음), `std::println("println: {:.1}", point)`, `std::print(stdout, "print to stdout: {} items\n", kRows.size())`. 주석: `std::print`는 `std::format_string`을 받는다(컴파일 시간 검사), `std::cout`과 순서가 맞는 이유(Assumption 12), Windows 콘솔에서는 유니코드 출력 API로 쓴다(P2093, 파이프로 보내면 바이트 그대로).
- README 두 판: 13행의 "아직 쓰지 않습니다" 문장을 7단계 설명으로, "볼 것"에 7단계, 연습 3을 Assumption 13으로.
- `lesson.toml`: `summary`/`summary_en`에 `std::print` 추가.

### 2.5 태그 어휘 (`lessons/tags.toml`에 더함)
| 키 | ko | en | aliases |
|---|---|---|---|
| `modules` | 모듈 | Modules | `import`, `export module`, `.cppm`, `module partition`, `파티션`, `global module fragment`, `BMI`, `atugcc.core`, `C++20 modules`, `모듈 인터페이스` |

`format` 태그의 별칭에는 이미 `std::print`가 있다. 별칭 중복 경고(070-10)를 지킨다(`import`가 다른 태그에 없는지 구현 때 확인).

### 2.6 Platform Specifics
- 모듈 BMI는 MSVC `.ifc`, Clang `.pcm`. 레슨 빌드는 CMake가 감춘다(070-13). 점이 든 모듈 이름과 파티션은 070-13 시험에서 Clang 20으로 빌드·실행됐다(`export import :text`). MSVC의 파티션은 이 저장소에서 아직 빌드한 적이 없어 DEV 첫 단계에서 확인한다(§10).
- `std::print`: MSVC는 `/utf-8`(프로젝트 옵션)일 때 콘솔에 유니코드 API로 쓰고, libstdc++ 14는 바이트를 쓴다. 7단계 출력은 ASCII라 차이가 보이지 않는다.
- 웹 플레이그라운드는 `linux-x64-playground`(Clang 20)로 빌드한다. 로컬 Windows와 웹의 레슨 출력이 같아야 한다(AC-2).

## 3. C++ Standard Evolution
| Approach | Standard | Description |
|----------|----------|-------------|
| Legacy | C++98–17 | `#include` + include guard, 헤더에 선언, `.cpp`에 정의, `detail` 네임스페이스로 "숨기기"(실제로는 보임), 매크로가 includer로 샘, 속도는 PCH. 출력은 `printf` / `std::cout << std::format(…)` |
| Modern | C++20 | named module: 인터페이스·파티션·구현 유닛, `export`한 것만 보임, 매크로는 안 감, import는 전이되지 않음(`export import`만), 구현 유닛만 고치면 importer는 다시 컴파일되지 않음 |
| Latest | C++23 | `std::print` / `std::println`(P2093, `<print>`), `import std;`(P2465, 쓰지 않음: KI-036) |

Reference: [`/docs/cpp_evolution/modules.md`](/docs/cpp_evolution/modules.md), [`/docs/cpp_evolution/format.md`](/docs/cpp_evolution/format.md) (둘 다 있음, 레슨 링크만 고침).

## 4. Edge Cases
- [x] Thread safety / memory ordering — N/A: 레슨은 한 스레드, 라이브러리 변경 없음.
- [x] Resource lifetime / RAII / dangling views — `describe`는 `std::string`을 값으로 돌려준다. `Expected<Rect>`는 값. 뷰를 모듈 경계 밖으로 내보내지 않는다.
- [x] Platform differences (MSVC vs Clang) — 같은 소스, CMake의 file set. 출력의 `to_string(CoreError)` 문자열은 라이브러리 값이라 두 OS가 같다. `std::print` 차이는 §2.6.
- [x] Template instantiation / concept constraints — `Expected<Rect>`(별칭 템플릿)가 `modules.geometry`의 export된 함수 시그니처에 들어간다. 그 모듈은 `atugcc.core`를 export하지 않으므로, importer가 `Expected`라는 이름을 쓰려면 직접 import해야 한다(4단계). 타입 자체는 이름 없이(`auto`)도 쓸 수 있다는 것을 README에 적는다(reachable vs visible).
- [x] ODR — `Rect`와 함수는 모듈 `modules.geometry`에 붙는다(module linkage/attachment). 헤더 사본이 없으므로 중복 정의가 생기지 않는다. `atugcc.core`의 개체는 global module에 붙은 헤더 개체 그대로다(070-13 Assumption 7).
- [x] Undefined behaviour — `area`는 `double` 곱. `makeRect`가 0 이하를 거부한다. N/A 그 밖.
- [x] include-before-import — `main.cpp`와 `geometry_rect.cppm`, `geometry.cpp`(`<expected>`, DEV에서 추가)의 global module fragment가 표준 헤더를 `import`보다 먼저 include한다(impl.md §2a). `lessons.py`가 검사하지는 않는다(빌드가 알려 줌, 규칙은 README에).
- [x] 진입점이 모듈 파일 — `lessons.py` ERROR(Assumption 7). CMake도 `add_executable`에 비모듈 소스가 없으면 실패한다.
- [x] 웹에서 파일을 고친 뒤 모듈 이름을 바꾸거나 `export module` 줄을 지움 — 다음 빌드에서 CMake가 다시 스캔한다(dyndep). 스캔 오류는 `file:line:col` 형식이 아닐 수 있어 진단 표시는 안 되고 빌드 로그에만 보인다. README에 한 줄. 매니페스트를 고치지 않는 한 configure는 다시 하지 않는다(새 `.cppm`을 `sources`에 더하면 `CMAKE_CONFIGURE_DEPENDS`가 다시 configure).
- [x] 낡은 BMI — preset마다 빌드 디렉터리가 따로(070-13). 웹의 Debug/Release preset도 따로다.
- [x] 같은 모듈 이름을 두 레슨이 씀 — 실행 파일이 따로라 빌드는 되지만 Assumption 3의 접두사 WARN이 막는다.
- [x] `std::print`와 `std::cout` 순서 — `sync_with_stdio(true)`(기본)에서 둘 다 C stdio 버퍼를 지나므로 순서가 맞는다. 레슨은 `sync_with_stdio`를 바꾸지 않는다. ctest와 웹은 stdout을 파이프로 받는다(완전 버퍼링이어도 한 버퍼).
- [x] Sanitizer — 레슨은 `linux-x64-asan`/`tsan` 빌드에도 들어간다. 그 preset에서 `ctest -L lesson`이 통과해야 한다(AC-10).

## 5. Acceptance Criteria
| ID | Criterion | Verified by |
|---|---|---|
| AC-1 | 인덱스의 essentials 순서 끝에 `modules`가 온다(`…, lock_free_buffer, span_timing, modules`). 기존 레슨의 id와 순서는 그대로다. 인덱스의 `modules` 항목 `sources`에 `.cppm` 둘이 있고 `uses`의 `mod:atugcc/core.cppm`이 `modules/atugcc/core.cppm`으로 나온다 | `py -3 tools/lessons.py index -` 출력, testrecord |
| AC-2 | `modules`가 `windows-x64-debug`와 `linux-x64-debug`에서 경고 없이 빌드되고 smoke test가 통과한다. 출력에 §2.2의 4단계가 모두 있고 두 OS의 출력이 같다 | 빌드 로그, `ctest -R lesson.modules`, 두 출력의 diff(차이 없음), testrecord |
| AC-3 | `lesson_modules` 타깃의 `CXX_MODULES` file set에 `geometry.cppm`, `geometry_rect.cppm`이 있고 `geometry.cpp`, `main.cpp`는 일반 소스다. `main.cpp`에 `#include "atugcc` 가 없다 | 빌드 디렉터리의 모듈 산출물(MSVC `.ifc` / Clang `.pcm`에 `modules.geometry`, `modules.geometry-rect` 또는 `:rect`) 목록, `grep -c '#include "atugcc' …/main.cpp` = 0 |
| AC-4 | 연습 2의 동작이 사실이다: 빌드된 상태에서 `geometry.cpp`만 고치면 `main.cpp`는 다시 컴파일되지 않고, `geometry.cppm`을 고치면 `main.cpp`도 다시 컴파일된다(두 OS) | `build.py --target lesson_modules`의 Ninja 줄(다시 컴파일된 파일 목록) 두 경우, testrecord. 고친 내용은 되돌림 |
| AC-5 | 연습 1·3이 README가 말하는 대로 된다: `detail::clampSide` 호출은 컴파일 오류(두 OS), `main.cpp`의 `import atugcc.core;`를 지우면 `CoreError`/`to_string`을 찾지 못하는 오류(Clang, `linux-x64-debug`. MSVC는 빌드됨, Assumption 11), `geometry.cppm`을 `export import atugcc.core;`로 바꾸면 import 없는 `main.cpp`가 빌드됨(두 OS) | 임시로 고친 사본의 빌드 오류 첫 줄, testrecord. 커밋하지 않음 |
| AC-6 | `lessons.py check`의 새 규칙(§2.3)이 각 경우에 맞는 수준을 낸다: 진입점 `.cppm` ERROR, 유닛 `.cppm` ERROR, `.ixx` ERROR, 없는 `mod:` 경로 ERROR, 모듈 이름 접두사 WARN, `import atugcc.core;` + `mod:` 없음 WARN, `.cppm` 리터럴의 한글 WARN. 저장소 전체는 ERROR 0, WARN 0 | `py -3 tools/test_lessons.py`, `py -3 tools/lessons.py check` |
| AC-7 | 웹: 레슨 트리의 `modules`를 Run하면 4단계가 나온다. `.cppm` 탭이 C++로 칠해진다. "관련 파일"의 `modules/atugcc/core.cppm`이 읽기 전용으로 열린다. `lessons/…/15_modules/` 아래 새 `.cppm` 파일을 만들 수 있다. `geometry.cppm`에 문법 오류를 넣고 Run하면 그 파일의 줄에 진단 표시가 붙는다. 검색 `.cppm`, `import`, `모듈`이 `modules`를 찾는다 | 헤드리스 브라우저: 실행 출력, 스크린샷 2장(구문 강조, 진단 표시), 검색어 3개 결과, `web/server/test_server.py`의 새 파일 테스트 |
| AC-8 | `format_text`의 출력에 7단계가 있고, 7단계의 `std::println` 줄과 `std::cout` 줄이 같다. 두 preset에서 경고 없이 빌드되고 smoke test 통과. README 두 판에 "아직 쓰지 않습니다" 문장이 없고 연습 3이 툴체인을 가리지 않는다 | 두 OS 출력 전문, `grep`, testrecord |
| AC-9 | 새·고친 README의 영어판이 한국어판과 절 제목 수, 연습 수, 코드 블록 수가 같다. 새 소스의 stdout·stderr에 한글이 없고, 한글 주석 줄(문단)마다 바로 다음이 같은 뜻의 영어 주석이다 | 070-03의 비교 스크립트와 AC-5 스크립트, `cpp-reviewer` 번역 검토 한 번 |
| AC-10 | 전체 suite가 `windows-x64-debug`, `linux-x64-debug`에서 통과한다. `linux-x64-asan`, `linux-x64-tsan`에서 `ctest -L lesson`이 통과한다. `linux-x64-playground`, `linux-x64-playground-release`가 모든 레슨을 빌드한다. `npm --prefix web/frontend test`, `tools/test_lessons.py`, `PlaygroundServer` 통과 | `build.py --preset <p> --test`, 명령 출력, testrecord |
| AC-11 | §8 문서가 결과와 맞고 `lint_docs.py`가 exit 0이다 | 명령 출력 |

## 6. Out of Scope
- 유닛(`lessons/units/`)의 모듈 — 유닛은 include되는 헤더라 모듈을 담을 타깃이 없다. 여러 레슨이 같이 쓰는 모듈이 필요해지면 유닛마다 라이브러리 타깃을 만드는 작업 — **KI-039**(새)
- `import std;` — KI-036
- 편집기(clangd / IntelliSense)의 모듈 지원 — KI-037
- 설치된 모듈을 쓰는 사용자 프로젝트 — KI-038
- `.ixx` 등 다른 모듈 확장자, 헤더 유닛(`import "x.hpp";`) — 계획 없음(Assumption 6, 070-13)
- 기존 레슨을 `#include "atugcc/…"` 대신 `import atugcc.core;`로 바꾸기 — 하지 않는다. 레슨은 각자 가르치는 것에 맞는 방식을 쓴다
- range 포맷, 파이프 `ranges::to`, `std::forward_like` — KI-033(libstdc++ 15)
- `std::vprint_unicode`를 레슨 코드에 — README 한 줄만(Assumption 13)

## 7. Dependencies & Backends
none. 새 패키지·라이브러리 없음(070-13의 툴체인 그대로).

## 8. Documentation Updates
| Document | Section | Change |
|---|---|---|
| `lessons/tracks/01_essentials/15_modules/README.md`, `README.en.md` | 전체 | 새로 씀(§2.2) |
| `lessons/tracks/01_essentials/02_format_text/README.md`, `README.en.md` | 머리말 13행, 볼 것, 연습 3 | 7단계, Assumption 13 |
| [`lessons/README.md`](/lessons/README.md) | 구조, 매니페스트, 새 레슨 추가 3단계 | 레슨 폴더에 `.cppm`(모듈 인터페이스·파티션)과 구현 유닛 `.cpp`를 둘 수 있음, 진입점은 `.cpp`, 모듈 이름 `<id>.` 접두사, `uses`의 `mod:`, 새 check 항목 |
| [`lessons/tags.toml`](/lessons/tags.toml) | — | `modules` 태그(§2.5) |
| [`docs/tasks/lesson_candidates.md`](/docs/tasks/lesson_candidates.md) | Essentials 표 | `15_modules` E15 행, `레슨 있음` |
| [`docs/cpp_evolution/modules.md`](/docs/cpp_evolution/modules.md) | 머리 "Lesson: none yet" | 레슨 링크 |
| [`docs/cpp_evolution/format.md`](/docs/cpp_evolution/format.md) | `std::print` 항목 | "070-14에서" → 7단계가 있음 |
| [`.agent/rules/impl.md`](/.agent/rules/impl.md) | §2a | 레슨의 모듈: `.cppm`, 이름 `<레슨 id>.`, `lessons/CMakeLists.txt`가 file set으로 넣음(한 줄) |
| [`web/README.md`](/web/README.md) | 편집 가능한 파일 설명이 있으면 | 새 파일 확장자에 `.cppm` |
| [`docs/known_issues.md`](/docs/known_issues.md) | KI-033, 새 KI-039 | KI-033 Update(070-14: `std::print` 단계 끝, Next는 libstdc++ 15 항목만), 표의 Next 열. KI-039 유닛의 모듈 |
| [`docs/tasks/agent_todo.md`](/docs/tasks/agent_todo.md) | Phase 7, 진행 순서 A.4 | 070-14 줄(링크, 상태), 끝나면 "다음은 070-14" → 040-02 |

## 9. Technical Constraints
- Compiler: MSVC (VS 2026) / Clang 20 with libstdc++ 14 (Linux)
- CMake: 4.0+ (C++20 modules always on), Ninja
- C++ Standard: C++23 (C++20 minimum). 모듈 C++20, `std::print` C++23

## 10. Context & References
- [070-13 스펙](/docs/specs/070_13_modules_clang_toolchain.md) Assumption 6·7·11·15·16, [`modules/atugcc/core.cppm`](/modules/atugcc/core.cppm), [`tests/modules/test_core_module.cpp`](/tests/modules/test_core_module.cpp)
- [070-03 스펙](/docs/specs/070_03_essentials_curriculum.md) Assumption 3·5·12·13, [070-01 스펙](/docs/specs/070_01_lesson_structure.md)
- [`lessons/CMakeLists.txt`](/lessons/CMakeLists.txt), [`tools/lessons.py`](/tools/lessons.py)(`CPP_SUFFIXES`, `check`, `ref_files`), [`web/server/files.py`](/web/server/files.py), [`web/server/runner.py`](/web/server/runner.py)(`DIAGNOSTIC_RE`), [`web/frontend/src/editor.ts`](/web/frontend/src/editor.ts)(`languageOf`)
- [`format_text` main.cpp](/lessons/tracks/01_essentials/02_format_text/main.cpp), [KI-033](/docs/known_issues.md)
- 2026-11-03 툴체인 시험(070-13 §10): 점 이름 모듈, `export import :text` 파티션, 구현 유닛, `<print>`가 Clang 20 + libstdc++ 14에서 빌드·실행됨. MSVC에서 확인된 것은 `<print>`와 저장소의 `atugcc.core`(파티션 없음)뿐이다. 이 스펙은 새 시험을 하지 않았다. 레슨 구성(파티션 `:rect`, 구현 유닛, `.cppm` file set을 가진 실행 파일)은 DEV 첫 단계에서 두 호스트로 확인하고, 안 되는 것이 있으면 멈추고 스펙을 고친다

## 11. Implementation Plan
- [ ] Step 1: `lessons/CMakeLists.txt`의 `.cppm` 분리. 빈 연습용 레슨 없이 Step 3의 레슨 파일로 바로 두 호스트 빌드 확인
- [ ] Step 2: `tools/lessons.py`(`CPP_SUFFIXES`, `mod:`, check 규칙, 인덱스)와 `tools/test_lessons.py`
- [ ] Step 3: `15_modules` 레슨(`lesson.toml`, 소스 4개, README 두 판), `tags.toml`
- [ ] Step 4: 웹 `files.py`, `test_server.py`, `editor.ts`
- [ ] Step 5: `format_text` 7단계, README 두 판, 매니페스트 요약
- [ ] Step 6: §8 문서, KI-033 Update, KI-039

## 12. Verification Plan
- [ ] `py -3 .agent/scripts/build.py --preset windows-x64-debug --test`, `--preset linux-x64-debug --test`
- [ ] `--preset linux-x64-asan`, `--preset linux-x64-tsan` 빌드와 `ctest -L lesson`
- [ ] `--preset linux-x64-playground`, `linux-x64-playground-release` 빌드
- [ ] `lesson_modules`, `lesson_format_text` 출력 두 OS diff
- [ ] 연습 1–3을 임시 사본으로(AC-4, AC-5)
- [ ] `py -3 tools/test_lessons.py`, `npm --prefix web/frontend test`, `ctest -R PlaygroundServer`
- [ ] 헤드리스 브라우저(AC-7)
- [ ] `lint_docs.py`, `lessons.py check` exit 0
- [ ] 모든 AC 행의 증거가 `testrecord.md`에

## History / Amendments
- 2026-11-04: 초안
- 2026-11-04: 승인
- 2026-11-04 (DEV, agy opus 리뷰): MSVC 19.51은 연습 3의 오류를 내지 않는다(export하지 않은 import의 이름이 importer에 보임). 사용자 결정으로 연습은 유지하고 3의 오류는 Clang 기준(Assumption 11, AC-5). `geometry.cpp`에 `<expected>` global module fragment(첫 Clang 빌드, §4)
