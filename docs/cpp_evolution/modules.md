# C++ Evolution: Modules

## Why
`#include`는 헤더의 텍스트를 그것을 포함하는 모든 소스에 붙여 넣습니다. 소스마다 같은 표준 헤더와 라이브러리 헤더를 다시 파싱하고, 헤더의 모든 매크로와 내부 도우미가 포함하는 쪽으로 새어 나가며, include 순서가 뜻을 바꿀 수 있습니다. 미리 컴파일된 헤더(PCH)는 시간은 아껴 주지만 새는 것은 막지 못합니다. C++20 이름 있는 모듈(named module)은 인터페이스를 한 번 컴파일해 바이너리 모듈 인터페이스(BMI)로 만들고, `import`는 모듈이 export한 것만 가져옵니다. 매크로도, 내부 도우미도 없고, import 순서에도 상관없습니다. atugcc는 모듈을 늘 켜고 빌드합니다(스펙 [070-13](/docs/specs/070_13_modules_clang_toolchain.md)). `import atugcc.core;`는 core 헤더의 모듈 형태입니다.

레슨: [`modules`](/lessons/tracks/01_essentials/15_modules/README.md)(essentials 트랙)는 자기 모듈을 인터페이스, 파티션, 구현 유닛으로 나누고, `import atugcc.core;`로 라이브러리를 쓰며, 매크로가 import를 넘지 않는다는 것과 import가 그것을 import하는 쪽으로 전달되지 않는다는 것을 보여 줍니다.

## C++98/17 (Legacy): 헤더
```cpp
// widget.hpp
#pragma once                       // or an include guard
#include <string>
#define WIDGET_MAX 16              // leaks into every includer
namespace lib {
namespace detail { inline int helper() { return 1; } }   // visible to every includer
inline std::string name() { return "widget"; }
}

// user.cpp
#include "widget.hpp"              // re-parsed in every source; <string> too
int n = lib::detail::helper() + WIDGET_MAX;   // nothing stops this
```
- 컴파일 시간이 소스 수 곱하기 그 소스들이 포함하는 헤더 크기만큼 늘어납니다.
- 헤더 안의 모든 것이, 의도했든 아니든 인터페이스의 일부입니다.

## C++20: 이름 있는 모듈
```cpp
// widget.cppm (module interface unit)
module;                            // global module fragment: only preprocessor directives
#include <string>
export module lib.widget;          // the module's name
namespace lib {
namespace detail { int helper() { return 1; } }   // not exported: invisible to importers
export std::string name() { return "widget"; }
}

// user.cpp
import lib.widget;
std::string s = lib::name();       // ok
// lib::detail::helper();          // error: not exported
```
- 빌드 시스템은 모든 소스에서 `import` / `export module`을 찾아(P1689) 인터페이스를 그것을 import하는 쪽보다 먼저 빌드합니다. CMake는 이것을 `FILE_SET CXX_MODULES`와 `CMAKE_CXX_SCAN_FOR_MODULES`(Ninja 생성기)로 합니다. 스캐너는 MSVC에서 `cl /scanDependencies`, Clang에서 `clang-scan-deps`(Ubuntu 패키지 `clang-tools-20`)입니다.
- BMI는 컴파일러와 플래그에 따라 다릅니다(MSVC `.ifc`, Clang `.pcm`). 설치하거나 공유하지 않고, 쓰는 쪽이 설치된 `.cppm`에서 자기 BMI를 만듭니다.
- **파티션**은 모듈 하나를 나눕니다: 한 파일에 `export module lib.widget:text;`, 주 인터페이스에 `export import :text;`.
- **구현 유닛**(`export` 없는 `module lib.widget;`)은 정의를 인터페이스 밖에 두므로, 고쳐도 import하는 쪽을 다시 빌드하지 않습니다.
- 매크로는 `import`를 절대 넘지 않습니다. 매크로가 필요한 코드는 그것을 정의한 헤더를 include합니다.
- 헤더 유닛(`import "widget.hpp";`)도 표준이지만 CMake가 지원하지 않으므로 atugcc는 쓰지 않습니다.

## C++23: `import std`
```cpp
import std;                        // the whole standard library, as one module (P2465)
```
MSVC에는 있습니다. libstdc++는 GCC 15에서 `std` 모듈을 얻고, CMake는 `import std`를 아직 실험 기능으로 둡니다. atugcc는 아직 쓰지 않습니다: [KI-036](/docs/known_issues.md).

## C++20 (Current, atugcc)
[`modules/atugcc/core.cppm`](/modules/atugcc/core.cppm)은 **감싸는 모듈(wrapper module)**입니다. global module fragment에서 공개 core 헤더들을 include하고, 모듈은 그 공개 이름들을 `using` 선언으로 export합니다.
```cpp
module;
#include "atugcc/core/logger.hpp"   // ... and the other public core headers
export module atugcc.core;
export namespace atugcc::core {
using ::atugcc::core::Logger;
using ::atugcc::core::operator|;   // ADL-only operators are exported by name
// ...
}
```
- 헤더가 계속 기준이므로 헤더를 쓰는 쪽과 모듈을 쓰는 쪽이 빌드 하나를 공유합니다. global module fragment의 선언은 전역 모듈에 속하므로, `logger.hpp`를 include하면서 **동시에** `atugcc.core`를 import하는 소스는 `Logger`를 둘이 아니라 하나로 봅니다([`test_core_module_mixed.cpp`](/tests/modules/test_core_module_mixed.cpp)).
- 그런 소스에서는 모든 `#include`가 모든 `import`보다 앞에 옵니다(어떤 모듈이 이미 include한 표준 헤더를 그 모듈의 import 뒤에 include하면 MSVC와 Clang 모두 실패한 적이 있습니다).
- [`test_core_module.cpp`](/tests/modules/test_core_module.cpp)는 라이브러리를 `import atugcc.core;`로만 씁니다.
- 새 모듈의 규칙(이름 `atugcc.<area>`, 파일 `modules/atugcc/<area>.cppm`, 새 공개 헤더 이름은 같은 변경에서 export 목록에 넣음): [`impl.md`](/.agent/rules/impl.md) §2a.
- 툴체인: Windows는 MSVC(VS 2026), Linux는 Clang 20과 libstdc++ 14, CMake 4.0 이상, Ninja.
