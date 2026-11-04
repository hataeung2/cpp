# 레슨: C++20 모듈 — 인터페이스, 파티션, 구현 유닛과 `import atugcc.core` (`modules`)

`#include`는 헤더 본문을 포함할 때마다 다시 파싱하고 그 안의 매크로와 비공개 도우미까지 넘기지만, C++20 이름 있는 모듈(named module)은 인터페이스를 한 번 컴파일해 `export`한 이름만 내보냅니다. 이 레슨은 자체 모듈 `modules.geometry`를 주 인터페이스, 파티션, 구현 유닛 세 파일로 나누어 만들고, 라이브러리도 헤더 없이 `import atugcc.core;`로만 쓰며(`uses` 탭의 [`core.cppm`](/modules/atugcc/core.cppm), [`error.hpp`](/include/atugcc/core/error.hpp)), 구현 유닛 분리·파티션 재내보내기·매크로 격리·전이되지 않는 `import`를 네 단계로 출력합니다. 해설: [modules.md](/docs/cpp_evolution/modules.md)(영어).

## `#include`와 이름 있는 모듈
| | `#include` (헤더) | 이름 있는 모듈 (C++20) |
|---|---|---|
| 파싱 횟수 | 포함하는 번역 단위마다 헤더와 그 안의 헤더를 다시 파싱 | 인터페이스를 이진 모듈 인터페이스(BMI)로 한 번 컴파일하고 `import`가 읽음 |
| 매크로 | 헤더의 `#define`이 포함한 파일로 흘러 들어감 | `import`를 건너지 않음. 매크로가 필요하면 정의한 헤더를 `#include` |
| 포함 순서 | 앞 헤더의 매크로·선언에 따라 뒤 헤더의 뜻이 바뀔 수 있음 | 각 모듈이 독립되어 `import` 순서가 뜻을 바꾸지 않음 |
| 숨길 수 있는 것 | `detail::` 네임스페이스도 포함한 쪽의 이름 찾기에 그대로 보임 | `export`하지 않은 선언(`detail::clampSide`)은 모듈 밖에서 보이지 않음 |
| 다시 빌드되는 범위 | 헤더의 인라인 본문이나 도우미를 고치면 포함한 모든 파일을 다시 컴파일 | 구현 유닛(`.cpp`)만 고치면 그 파일만 다시 컴파일하고 링크; 인터페이스(`.cppm`)가 바뀔 때만 importer도 다시 컴파일 |

## 유닛 구성과 빌드
- **주 모듈 인터페이스 유닛 (`geometry.cppm`, `export module modules.geometry;`)**: `export import :rect;`로 파티션을 다시 내보내고, `import atugcc.core;`를 `export` 없이 가져오며, 공개 함수 `area`·`makeRect`와 비공개 `detail::clampSide`를 선언합니다. 이 파일은 어떤 헤더도 `#include`하지 않으므로 `module;`(global module fragment)이 없습니다.
- **모듈 파티션 인터페이스 유닛 (`geometry_rect.cppm`, `export module modules.geometry:rect;`)**: `module;` 뒤에서 `<format>`, `<string>`을 포함하고 `Rect`와 인라인 함수 `describe(const Rect&)`를 `export`하며, 주 인터페이스의 `export import :rect;`를 통해 외부에 공개됩니다. 파티션은 자기 주 인터페이스(`modules.geometry`)를 `import`할 수 없으므로(순환 의존), `Rect`를 쓰는 `describe`가 `Rect`와 함께 이 파티션에 있습니다.
- **모듈 구현 유닛 (`geometry.cpp`, `export` 없는 `module modules.geometry;`)**: 주 인터페이스의 모든 선언과 `import`를 물려받아 `area`, `makeRect`, `detail::clampSide`를 정의합니다. `makeRect`가 쓰는 `std::unexpected`를 위해 `module;` 뒤에 `#include <expected>`를 둡니다. `import`는 내보내지 않은 `std::` 이름을 주지 않으며, `import atugcc.core;`도 `std::` 이름을 내보내지 않기 때문입니다.
- **빌드**: `lesson.toml`의 `sources`에 적힌 `.cppm` 파일은 [`lessons/CMakeLists.txt`](/lessons/CMakeLists.txt)가 자동으로 CMake `CXX_MODULES` file set에 넣고, 첫 번째 소스는 지금처럼 진입점 `.cpp`(`main.cpp`)로 둡니다. 모듈 이름을 바꾸거나 `export module` 줄을 지우면 다음 빌드 때 다시 스캔하며, 스캔 오류는 `file:line:col` 표시 대신 빌드 로그에만 나올 수 있습니다.
- **`#include`가 `import`보다 먼저**: 한 파일 안에서는 모든 `#include`를 모든 `import`보다 앞에 둡니다([`impl.md`](/.agent/rules/impl.md) §2a). `import`한 모듈이 이미 포함한 표준 헤더를 그 뒤에서 다시 `#include`하면 선언이 부딪힐 수 있기 때문입니다.
- **`import std;`와 편집기**: `import std;`(C++23)는 아직 쓰지 않으므로([KI-036](/docs/known_issues.md)) 표준 헤더는 `#include`로 포함합니다. 로컬 편집기가 `import` 줄에 밑줄을 그을 수 있으나([KI-037](/docs/known_issues.md)), 빌드는 정상으로 됩니다.

## 실행
- 웹 플레이그라운드: 레슨 트리에서 선택 후 Run
- 로컬: `cmake --build --preset <preset> --target lesson_modules` 후 `bin/lessons/lesson_modules`, 또는 `ctest --preset <preset> -R lesson.modules`

## 볼 것
- 1단계: `main.cpp`가 `import modules.geometry;`로 `makeRect(3.0, 4.0)`과 `area(rect)`를 불러 넓이 `12`를 얻습니다. 두 함수의 본문은 헤더가 아니라 구현 유닛 `geometry.cpp`에 있습니다.
- 2단계: `describe(rect)`가 `Rect 3 x 4`를 돌려줍니다. `Rect`와 `describe`는 `:rect` 파티션에 있지만, 주 인터페이스가 `export import :rect;`로 다시 내보냈으므로 `main.cpp`는 `modules.geometry`만 `import`해 씁니다(파티션은 모듈 밖에서 직접 `import`하지 않습니다).
- 3단계: `geometry.cppm` 안에 `#define GEOMETRY_UNIT_CM 1`이 있어도 `main.cpp`의 `#ifdef GEOMETRY_UNIT_CM`은 거짓(`GEOMETRY_UNIT_CM is not defined in main.cpp`)입니다. 매크로는 `import`를 건너지 않습니다.
- 4단계: `makeRect(-1.0, 2.0)`이 돌려준 실패를 `atugcc::core::to_string`으로 출력합니다([04_error_expected](../04_error_expected/README.md)). `geometry.cppm`의 `import atugcc.core;`는 `export`하지 않았으므로 전이되지 않습니다. 반환값 자체는 `auto`로 받아 쓸 수 있지만(도달 가능, reachable), `to_string`이나 `CoreError` 같은 이름을 쓰려면(가시적, visible) `main.cpp`가 직접 `import atugcc.core;`를 해야 합니다.

## 연습
1. `main.cpp`에서 `modules::geometry::detail::clampSide(5.0)`을 호출해 보세요. 두 컴파일러 모두 컴파일 오류를 냅니다. 요지는 MSVC `error C2039: 'clampSide': is not a member of 'modules::geometry::detail'`, Clang `declaration of 'clampSide' must be imported from module 'modules.geometry' before it is required`입니다. `geometry.cppm`(인터페이스)에 선언되어 있어 도달 가능(reachable)하지만 `export`되지 않아 외부 이름 찾기에는 보이지 않기(not visible) 때문입니다. 확인한 뒤 되돌립니다.
2. `geometry.cpp`만 고쳐(예: `kMaxSide` 값 변경) 다시 빌드해 보세요. 빌드 로그(웹 빌드 출력 또는 로컬 Ninja 줄)에서 `geometry.cpp`만 다시 컴파일하고 링크하는 것을 확인합니다. 이어서 `geometry.cppm`을 고쳐 다시 빌드하면 인터페이스 BMI가 바뀌어 그 모듈을 쓰는 `main.cpp`와 구현 유닛 `geometry.cpp`도 함께 다시 컴파일됩니다. 확인한 뒤 되돌립니다.
3. `main.cpp`에서 `import atugcc.core;`를 지우고 빌드해 보세요. Clang(Linux preset, 웹 플레이그라운드)에서는 `atugcc::core::to_string` / `CoreError` 자리에서 실패합니다(고치는 방법은 `import`인데도 Clang 오류 문구는 `"missing '#include'"`라고 나옵니다). 반면 MSVC 19.51은 `geometry.cppm`의 `export`하지 않은 `import` 이름을 importer에 새어 나가게 해 그대로 빌드하므로(표준이 허용하지 않는 동작), 앞부분은 Clang에서 확인하세요. 그다음 `geometry.cppm`의 줄을 `export import atugcc.core;`로 바꾸면 두 컴파일러 모두에서 `main.cpp`가 자기 `import` 없이 빌드됩니다. 그 대가로 `modules.geometry`를 `import`하는 모든 파일에 `atugcc.core`의 이름까지 들어옵니다. 확인한 뒤 되돌립니다.
