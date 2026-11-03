---
id: 070-13
title: C++20 modules를 Windows·Linux 양쪽에서 (Linux 툴체인 Clang 20, CMake 4)
depends_on: []
unblocks: [070-14]
approved: 2026-11-03
---

# Spec 070-13: C++20 modules를 Windows·Linux 양쪽에서 (Linux 툴체인 Clang 20, CMake 4)

## 0. Assumptions (please review)
근거는 2026-11-03 툴체인 시험이다(WSL Ubuntu 24.04, 패키지 `clang-20` 20.1.2, `clang-tools-20`, `libstdc++-14-dev` 14.2, Kitware APT의 CMake 4.4.5, Ninja 1.11.1). 내용은 §10.

| # | Decision | Rejected alternative | Why |
|---|---|---|---|
| 1 | **Linux 컴파일러는 Clang 20 하나**(`clang++-20`, Ubuntu 패키지 `clang-20`). 플레이그라운드 preset을 포함한 모든 `linux-x64-*` preset이 쓴다. GCC는 Linux preset에서 빠진다(사용자 결정 2026-11-03: 필수가 아니면 컴파일러를 여러 개 두지 않는다) | GCC 14; GCC와 Clang 병행 | Linux에서 모듈 지원이 가장 성숙한 것은 Clang이다. GCC 모듈은 GCC 16에서도 experimental(`-fmodules`)이다. Linux 컴파일러를 둘 두면 검증 매트릭스가 두 배가 되는데 그럴 요구가 없다. Windows는 MSVC 그대로 |
| 2 | **Linux 표준 라이브러리는 libstdc++ 14**(`libstdc++-14-dev`). Clang이 가장 새 GCC 설치를 고르는 기본 동작(`Selected GCC installation: …/14`)을 쓴다. `g++-14`는 설치하지 않는다 | libc++(`libc++-20-dev`); libstdc++ 13 | libstdc++는 시스템 패키지(apt의 Boost)와 ABI가 같다. libc++를 쓰면 시스템 바이너리 의존성이 있을 때 한 프로세스에 표준 라이브러리가 둘이 된다. 14에는 `<print>`, `std::chrono::parse`, `clock_cast`가 있다(모두 시험) |
| 3 | 컴파일러는 `linux-base`에 경로가 아닌 프로그램 이름 `clang++-20`으로 둔다. 이름이 다른 배포판(`clang++`만 있는 경우)은 커밋하지 않는 `CMakeUserPresets.json`에서 덮어쓴다 | `clang++`(버전 없는 이름) | Ubuntu 24.04의 `clang++`은 Clang 18이거나 아예 없다. 버전이 붙은 이름이 시험한 컴파일러를 고정한다. 이름은 기계 경로가 아니다(규칙 1) |
| 4 | **두 호스트 모두 CMake 4.0 이상**: `CMakePresets.json`의 `cmakeMinimumRequired`를 4.0으로, `CMakeLists.txt`를 `cmake_minimum_required(VERSION 4.0)`으로. Linux는 Kitware APT 저장소에서 설치하고 Windows는 VS 2026에 들어 있는 CMake를 쓴다(2026-11-03 기준 4.3.1). 하위 `CMakeLists.txt`에는 `cmake_minimum_required`가 없다(2026-11-03 확인). 그래서 최소 버전을 적는 곳은 이 두 곳이다 | 3.26 유지 / Ubuntu 기본 3.28.3 | 사용자 결정 2026-11-03(최소 버전도 4 이상, 모듈을 항상 쓰는 개발). 모듈의 최소 버전은 3.28이지만, 두 호스트의 메이저 버전을 맞춰야 모듈 동작이 같다. FetchContent googletest 1.14도 CMake 4에서 configure된다(시험) |
| 5 | **모든 타깃에서 모듈 스캔을 켠다**: `base` preset의 `CMAKE_CXX_SCAN_FOR_MODULES`를 `ON`으로 하고, `CMakeLists.txt`의 Windows 전용 `set(CMAKE_CXX_SCAN_FOR_MODULES ON)`은 지운다. **모듈을 끄는 옵션은 두지 않는다**(사용자 결정 2026-11-03: 모듈을 항상 쓴다). `CMakeLists.txt`는 `CMAKE_CXX_SCAN_FOR_MODULES`가 켜져 있지 않으면 configure에서 `FATAL_ERROR`로 멈춘다(값을 정하지 않고 검사만 하므로 설정의 출처는 계속 preset) | 타깃별 스캔(import하는 타깃에만 `CXX_SCAN_FOR_MODULES`); 끄는 옵션 | 어떤 소스(테스트, 레슨, 샘플)든 `import`할 수 있어야 한다. 타깃별 스위치는 새 타깃을 만들 때마다 잊기 쉬운 단계다. 스캔 비용은 소스 하나당 `clang-scan-deps` / `cl /scanDependencies` 한 번이고, testrecord에 전체 빌드 시간을 전후로 남긴다 |
| 6 | **모듈 이름**은 점으로 구분한 `atugcc.<area>`, 하위 부분은 파티션(`atugcc.core:log`)으로 둔다. 공개 인터페이스 유닛은 `modules/atugcc/<area>.cppm`에 둔다 | `src/<area>/*.cppm`(지금 `alog.cppm` 위치); `atugcc.` 접두사 없는 이름 | 공개 인터페이스를 한 디렉터리에 모으면 `include/atugcc/`와 같은 구조가 되고 설치도 한 디렉터리다. 접두사가 있어야 사용자 자신의 모듈과 이름이 겹치지 않는다 |
| 7 | **첫 라이브러리 모듈 `atugcc.core`는 래퍼다**: global module fragment에서 공개 core 헤더를 include하고 그 공개 이름을 `using` 선언으로 export한다(목록 §2.1). 기준은 계속 헤더이고 구현을 모듈 유닛으로 옮기지 않는다 | core 구현을 모듈 유닛으로 옮기기 | 헤더 사용자는 그대로 쓰고 한 빌드가 두 방식의 사용자에게 함께 쓰인다. global module fragment의 개체는 global module에 붙으므로 헤더를 include하면서 모듈도 import하는 TU에서도 개체가 하나다(ODR 중복 없음). 구현 이동은 영역별로 나중에 한다(Out of Scope) |
| 8 | `atugcc.core`는 `atugcc_core` 타깃(`FILE_SET CXX_MODULES`)에 속한다. `atugcc_core`를 링크하는 모든 타깃이 `import atugcc.core;`를 쓸 수 있다 | 별도 `atugcc_modules` 타깃 | 두 방식 모두 링크 한 줄이다. 프로젝트 타깃은 모두 `atugcc_headers`의 컴파일 옵션을 공유해서 BMI 하나가 모든 importer에 맞는다(sanitizer preset은 자기 BMI를 따로 만든다) |
| 9 | `src/core/alog.cppm`(모듈 `alog`: deprecated된 `Logger` 별칭 하나)과 `modules/sample_module.cppm`(자리 표시용)을 **지운다**. `main.cpp`의 `_WIN32` 조건 `import sample_module;`도 지운다 | 둘을 옮겨 살리기 | 둘 다 import하는 곳이 없다(2026-11-03 확인). 프로젝트의 모듈은 `atugcc.core`가 대신한다. 헤더 쪽의 `alog::Logger` 별칭은 그대로 둔다(010-08이 남김) |
| 10 | **테스트**는 `atugcc_tests`에 새 파일 둘이다. `tests/modules/test_core_module.cpp`는 라이브러리를 `import atugcc.core;`로**만** 쓴다(`<gtest/gtest.h>`와 표준 헤더 외에는 include 없음). `tests/modules/test_core_module_mixed.cpp`는 `atugcc/core/logger.hpp`를 include하면서 모듈도 import하고, 두 쪽 이름이 같은 개체임을 확인한다 | 테스트 파일 하나; 별도 테스트 실행 파일 | 첫째는 export 목록만으로 라이브러리를 쓸 수 있음을, 둘째는 Assumption 7의 include·import 혼용을 증명한다. 둘 다 모든 preset의 `AllTests`에서 돈다 |
| 11 | 한 소스 파일에서 **모든 `#include`가 모든 `import`보다 앞에 온다**(`impl.md`에 규칙 추가) | 순서 자유 | MSVC와 Clang 모두 모듈의 fragment가 include한 표준 헤더를 `import` 뒤에서 다시 include할 때 실패한 사례가 있다. include를 먼저 두면 둘 다 된다(Clang 20에서 시험). 두 호스트에 같은 규칙 하나 |
| 12 | 전체 빌드에서 나온 **Clang 경고 세 개**(2026-11-03)는 끄지 않고 코드에서 고친다: `ACarFactory`(`pattern/factory.hpp`)와 `Impl`(`pattern/iterator_concept.hpp`)에 `virtual` 소멸자 | `-Wno-delete-non-abstract-non-virtual-dtor` | 실제 결함이다: `shared_ptr`/`unique_ptr`가 virtual 소멸자 없는 base로 지운다. 나머지 타깃은 Clang 20 `-Wall -Wextra -Werror`에서 경고가 없다(시험) |
| 13 | TSan `setarch -R` 런처는 그대로 둔다. 주석에서 "GCC 13"을 빼고 ASLR 문제로 적는다 | Clang이니 지우기 | 비용이 없고 preset마다 `build.py --gtest-filter`와 ctest가 같게 유지된다. Clang 20의 TSan에 아직 필요한지는 testrecord에 남긴다 |
| 14 | **설치**: 두 호스트 모두 모듈 인터페이스를 내보낸다. `FILE_SET CXX_MODULES` 설치와 `install(EXPORT … CXX_MODULES_DIRECTORY cxx-modules)`에서 Windows 전용 분기를 없앤다. BMI는 설치하지 않는다(컴파일러·옵션마다 다름). 사용하는 쪽에서 다시 만든다 | Windows만 설치; BMI 설치 | 어느 호스트의 사용자든 같은 패키지를 받는다. 실제 사용자 프로젝트로 하는 테스트는 Out of Scope(KI-038) |
| 15 | **`import std`**는 넣지 않는다(사용자 결정 2026-11-03). 새 KI-036. libstdc++ 14에는 `std` 모듈이 없고(GCC 15부터), CMake 4도 `import std`를 아직 실험용 UUID 뒤에 둔다 | MSVC에서만 켜기 | 레슨과 테스트는 두 호스트에서 같은 소스로 빌드돼야 한다 |
| 16 | essentials **modules 레슨**과 KI-033의 `std::print` 단계는 새 작업 **070-14**로 옮기고, 이 작업이 그것을 연다. 070-13은 툴체인, 모듈, 그 테스트를 낸다 | 070-13 안에 레슨(070-13 BACKLOG 줄의 범위) | 레슨에는 `lessons/CMakeLists.txt`와 `tools/lessons.py`의 `.cppm` 지원과 070-03의 한/영 레슨 작업이 필요하다. 툴체인 교체와 한 브랜치에 넣으면 리뷰 단위가 너무 커진다(070-03 Assumption 1과 같은 이유) |
| 17 | KI-033의 제목을 "Linux 툴체인에 없는 C++23 기능"으로 바꾸고 목록을 시험 결과로 고친다. `std::print`, `chrono::parse`, `clock_cast`, deducing this는 이제 빌드된다. **range 포맷**(`std::format("{}", vector)`, libstdc++ 15)과 **파이프 형식 `ranges::to`**(`v | std::ranges::to<…>()`, Clang 20 + libstdc++ 14.2의 `forward_like` 버그. 호출 형식 `std::ranges::to<std::vector>(v)`는 빌드됨)는 안 된다 | KI-033 닫기 | 초안 070-11, 070-12가 GCC 13의 빈 곳을 이 KI에 기대어 적었다. 두 초안은 승인 전에 새 목록으로 고친다 |
| 18 | **TSan 빌드 우회**: `LogService::tryLockService(deadline)`([`log_service.cpp`](/src/core/log_service.cpp))의 `service_mutex_.try_lock_until(deadline)`을 `try_lock_for(deadline - std::chrono::steady_clock::now())`로 바꾸고, 이유를 주석에 적는다. libstdc++ 14.2의 `<mutex>`가 TSan에서 `_GLIBCXX_USE_PTHREAD_MUTEX_CLOCKLOCK`(TSan이면 `0`으로 정의됨)을 191행은 `#ifdef`, 300행은 `#if`로 검사해서 `steady_clock` 기한의 `try_lock_until`이 선언되지 않은 `_M_clocklock`을 부른다(2026-11-03 최소 예제로 확인, `try_lock_for`와 ASan은 문제없음). 컴파일러가 아니라 라이브러리 버그라서 GCC 14 TSan에도 같다 | `std::timed_mutex`를 다른 잠금으로 바꾸기; 매크로 재정의 | 의미가 같다: 지난 기한은 음수 기간이 되어 `try_lock_for`가 한 번만 시도한다. 한 줄이고 두 호스트에서 같은 소스다. 매크로는 `c++config.h`가 무조건 정의해서 덮을 수 없다. TSan에서 libstdc++는 `try_lock_for`를 `system_clock` 기준으로 기다리므로, 대기 중 벽시계가 바뀌면 대기 시간이 달라질 수 있다(TSan 빌드에서만, 정확성은 같음) |

## 1. Objective
C++20 named module을 두 호스트에서 atugcc를 쓰는 정식 방법으로 만들고, 그것을 지원하는 툴체인으로 Linux를 옮긴다. 지금은 모듈이 Windows에서만 빌드되고, 모듈 코드를 호출하는 곳도 없으며, Linux 빌드(GCC 13.3, CMake 3.28.3)는 모듈을 스캔하지 못한다(KI-035). 이 작업이 끝나면 모든 preset에서 `import atugcc.core;`가 빌드·링크·실행되고, 테스트가 그것을 증명하고, 규칙 문서가 다음 작업에 모듈 쓰는 법을 알려 준다.

## 2. Requirement Details

### 2.1 Public API Surface
새 모듈 인터페이스 유닛 `modules/atugcc/core.cppm`, 모듈 `atugcc.core`:
```cpp
module;
#include "atugcc/core/error.hpp"
#include "atugcc/core/log_buffer_config.hpp"
#include "atugcc/core/logger.hpp"
#include "atugcc/core/ring_buffer.hpp"
#include "atugcc/core/timestamp.hpp"
export module atugcc.core;

export namespace atugcc::core {
// error.hpp
using ::atugcc::core::CoreError;
using ::atugcc::core::to_string;
using ::atugcc::core::Expected;
using ::atugcc::core::Result;
// logger.hpp
using ::atugcc::core::FormatWithLocation;
using ::atugcc::core::Logger;
// log_buffer_config.hpp
using ::atugcc::core::Delivery;
using ::atugcc::core::OverflowPolicy;
using ::atugcc::core::Durability;
using ::atugcc::core::LogBufferConfig;
using ::atugcc::core::configureLogBuffers;
using ::atugcc::core::currentLogBufferConfig;
using ::atugcc::core::LogMapRecovery;
using ::atugcc::core::recoverLogMaps;
// ring_buffer.hpp
using ::atugcc::core::Level;
using ::atugcc::core::RingBuffer;
// timestamp.hpp
using ::atugcc::core::TimeStamp;
using ::atugcc::core::operator|;
}
```
- export하는 것: 다섯 헤더의 사용자가 지금 코드에 쓰는 이름. export하지 않는 것: `detail::`, 링 버퍼의 블록 헤더 도우미와 상수(`kLevelShift`, `encodeHeader`, …), 매크로(모듈은 매크로를 export할 수 없다. `adefine.hpp` 사용자는 include를 유지).
- 자유 연산자는 이름으로 export한다(`operator|`). 그래야 importer의 `Option::A | Option::B`가 찾는다.
- `core.cppm` 머리 주석: export 목록, 기준은 헤더라는 것, include-before-import 규칙(Assumption 11). 주석은 기존 코드처럼 영어.

### 2.2 Internal Implementation
- [`CMakePresets.json`](/CMakePresets.json): `cmakeMinimumRequired` 4.0. `base`: `CMAKE_CXX_SCAN_FOR_MODULES` `ON`. `linux-base`: `CMAKE_CXX_COMPILER` `clang++-20`, description에 패키지(`clang-20 clang-tools-20 libstdc++-14-dev`, Kitware APT의 CMake 4)를 적는다. 옛 preset `Configure preset using toolchain file`은 건드리지 않는다.
- [`CMakeLists.txt`](/CMakeLists.txt): `cmake_minimum_required(VERSION 4.0)`. Windows 전용 스캔 `set`을 지우고, `project()` 뒤에 `if(NOT CMAKE_CXX_SCAN_FOR_MODULES) message(FATAL_ERROR …)`(preset 이름을 알려 주는 메시지)를 둔다. 모든 호스트에서 `target_sources(atugcc_core PUBLIC FILE_SET CXX_MODULES BASE_DIRS modules FILES modules/atugcc/core.cppm)`. file set 설치와 `CXX_MODULES_DIRECTORY`도 모든 호스트에서(`install(TARGETS …)` 하나). TSan 런처 주석(Assumption 13). `-Wall -Wextra`는 이미 비MSVC 분기라 Clang에도 걸린다.
- `src/core/alog.cppm`, `modules/sample_module.cppm`를 지운다. [`main.cpp`](/main.cpp)에서 조건부 import와 주석 처리된 호출을 지운다.
- [`include/atugcc/pattern/factory.hpp`](/include/atugcc/pattern/factory.hpp)의 `ACarFactory`, [`include/atugcc/pattern/iterator_concept.hpp`](/include/atugcc/pattern/iterator_concept.hpp)의 `Impl`: `virtual ~X() = default;`.
- [`src/core/log_service.cpp`](/src/core/log_service.cpp) `tryLockService(deadline)`: Assumption 18의 한 줄과 주석.
- [`tests/CMakeLists.txt`](/tests/CMakeLists.txt): Assumption 10의 테스트 파일 둘을 더한다.
- [`web/server/runner.py`](/web/server/runner.py) `compiler_version()`: 첫 configure 전의 대체값을 `g++`에서 `clang++-20`으로(docstring 포함).

### 2.3 Platform Specifics
- Windows: MSVC(VS 2026), VS의 CMake. 모듈 스캔은 `cl /scanDependencies`, BMI는 `.ifc`. 컴파일러 변경 없음.
- Linux: Clang 20 + libstdc++ 14, `clang-scan-deps-20`(패키지 `clang-tools-20`. CMake가 `clang++-20` 옆에서 찾는다). BMI는 `.pcm`.
- 공통: Ninja 생성기(preset이 이미 씀), CMake 4.0 이상. 기계 준비 사항은 [`docs/artifacts/linux_build_setup.md`](/docs/artifacts/linux_build_setup.md)에.

## 3. C++ Standard Evolution
| Approach | Standard | Description |
|----------|----------|-------------|
| Legacy | C++98–17 | `#include`가 헤더 텍스트를 모든 TU에 붙여 넣는다. include guard / `#pragma once`, 시간을 줄이려 precompiled header. 헤더의 매크로와 내부 도우미가 사용자 TU로 새고, include 순서가 의미를 바꿀 수 있다 |
| Modern | C++20 | named module: `export module atugcc.core;`가 BMI로 한 번 컴파일된다. `import`는 export된 이름만 가져오고 매크로는 가져오지 않으며 import 순서와 무관하다. global module fragment로 기존 헤더를 감싼다. 파티션으로 모듈을 나눈다. 빌드 시스템이 의존성을 스캔한다(P1689) |
| Latest | C++23 | `import std;` / `import std.compat;`(P2465). 여기서는 쓰지 않는다(Assumption 15, KI-036) |

Reference: `/docs/cpp_evolution/modules.md`(새 페이지, §8).

## 4. Edge Cases
- [x] Thread safety / memory ordering — 모듈은 기존 개체를 다시 export만 한다. 잠금 코드 변경은 Assumption 18의 한 줄뿐이다: 같은 mutex, 같은 기한, 같은 `tServiceMutexHeld` 처리. 기한이 지났으면 `try_lock_for`가 음수 기간으로 한 번만 시도한다(`try_lock_until`의 지난 기한과 같음). risky unit(잠금)이라 `linux-x64-tsan` 전체 테스트(AC-6)와 delegation.md §6.2 리뷰를 거친다.
- [x] Resource lifetime / RAII / dangling views — N/A: 헤더와 같은 개체. virtual 소멸자 두 개(Assumption 12)는 base를 통해 지우는 수명 결함을 없앤다.
- [x] Platform differences — MSVC와 Clang은 BMI 형식과 스캔 도구가 다르고 CMake가 그 차이를 감춘다. import 뒤 include 문제는 Assumption 11로 피한다. 두 호스트가 같은 모듈 테스트 두 개를 돌린다.
- [x] Template instantiation / concept constraints — `RingBuffer`(제약이 있는 클래스 템플릿)와 `Expected<T>`(별칭 템플릿)는 `using`으로 export하고, 인스턴스화는 importer에서 일어난다. `test_core_module.cpp`가 둘 다 인스턴스화한다.
- [x] ODR — 헤더의 개체는 global module에 붙으므로(global module fragment) 헤더 사용자와 모듈 사용자가 정의 하나를 공유한다(Assumption 7). `test_core_module_mixed.cpp`가 `std::is_same_v`와, export한 자유 함수 하나의 주소를 두 방식에서 비교해 확인한다. 헤더의 `inline` 변수와 static local도 하나로 남는다.
- [x] Undefined behaviour — virtual 소멸자 외에는 N/A.
- [x] 모듈을 통한 이름 찾기 — export하지 않은 ADL 전용 자유 함수는 importer에서 보이지 않는다(global module fragment의 선언은 도달할 수 없으면 버려진다). `operator|`는 이름으로 export하고 테스트가 쓴다.
- [x] 매크로 — export되지 않는다. `test_core_module.cpp`는 atugcc 매크로를 쓰지 않는다(`core.cppm`과 `modules.md`에 적음).
- [x] 낡은 BMI / 옵션 불일치 — preset마다 빌드 디렉터리가 따로라 sanitizer 옵션과 일반 BMI가 섞이지 않는다. 다시 configure할 때는 `build.py --fresh`.
- [x] Sanitizer — `linux-x64-asan`과 `linux-x64-tsan`이 모듈 테스트를 빌드하고 실행한다(AC-6).

## 5. Acceptance Criteria
| ID | Criterion | Verified by |
|---|---|---|
| AC-1 | 모든 `linux-x64-*` preset이 Clang 20과 CMake 4.0 이상으로, `windows-x64-debug`가 MSVC와 CMake 4.0 이상으로 configure된다 | 각 빌드 디렉터리 cache의 `CMAKE_CXX_COMPILER_ID`/`_VERSION`, `CMAKE_COMMAND --version`을 testrecord에 |
| AC-2 | `windows-x64-debug`와 `linux-x64-debug`가 경고를 오류로 켠 채 모든 타깃을 경고 없이 빌드한다 | 두 preset에서 `build.py --preset <p>` exit 0 |
| AC-3 | `test_core_module.cpp`는 라이브러리를 `import atugcc.core;`로만 쓰고, 그 테스트가 두 호스트에서 통과한다: `Logger`로 줄을 쓰고 `snapshot()`으로 읽기, `RingBuffer` 쓰고 읽기, `Expected`/`CoreError` 반환, `TimeStamp::Option` 값을 `operator|`로 합치기 | `grep -c '#include "atugcc' tests/modules/test_core_module.cpp` = 0; 두 호스트에서 `build.py --preset <p> --gtest-filter "CoreModule.*"` |
| AC-4 | `test_core_module_mixed.cpp`는 `atugcc/core/logger.hpp`를 include하면서 모듈을 import하고, 이름이 같은 개체임을 보인다(`Logger`, `Expected<int>`, `CoreError`의 `std::is_same_v`, `configureLogBuffers` 주소가 같음) | 두 호스트에서 `--gtest-filter "CoreModuleMixed.*"` |
| AC-5 | `windows-x64-debug`와 `linux-x64-debug`에서 전체 테스트가 통과한다 | 두 preset에서 `build.py --preset <p> --test` exit 0 |
| AC-6 | `linux-x64-asan`과 `linux-x64-tsan`이 Clang 20으로 빌드되고 전체 테스트가 통과한다 | 두 preset에서 `build.py --preset <p> --test` exit 0 |
| AC-7 | `linux-x64-playground`와 `linux-x64-playground-release`가 Clang 20으로 모든 레슨을 빌드하고, 플레이그라운드 서버 테스트가 통과한다 | `build.py --preset linux-x64-playground`(과 `-release`) exit 0; `linux-x64-debug`에서 `ctest -L playground` |
| AC-8 | `src/core/alog.cppm`과 `modules/sample_module.cppm`이 없고 이를 가리키는 파일이 없으며, `CMakeLists.txt`에 `CMAKE_CXX_SCAN_FOR_MODULES`를 정하는 `set`도 Windows 전용 모듈 분기도 없다. 스캔을 끈 configure(`-DCMAKE_CXX_SCAN_FOR_MODULES=OFF`)는 실패한다 | `git ls-files`; `docs/specs`, `docs/tasks/feature_*` 밖에서 `grep -rn "alog.cppm\|sample_module"` 결과 없음; `CMakeLists.txt`의 `grep -c`; `cmake --preset linux-x64-debug -DCMAKE_CXX_SCAN_FOR_MODULES=OFF`가 0이 아닌 코드로 끝나고 메시지를 냄 |
| AC-9 | `linux-x64-debug`와 `windows-x64-debug`의 `cmake --install`이 설치 트리에 `atugcc/core.cppm`을 두고, export 파일이 `CXX_MODULES` file set을 가리킨다 | `out/install/<p>` 파일 목록을 testrecord에 |
| AC-10 | §8의 모든 문서가 결과와 맞고 `lint_docs.py`, `lessons.py check`가 exit 0 | `py -3 .agent/scripts/lint_docs.py`, `py -3 tools/lessons.py check` |

## 6. Out of Scope
- essentials modules 레슨, 레슨 매니페스트·`lessons/CMakeLists.txt`의 `.cppm` 소스, `format_text`의 `std::print` 단계 — **070-14**(새 작업, BACKLOG)
- `import std` / `import std.compat` — KI-036(새): Linux 표준 라이브러리에 `std` 모듈이 생기고(libstdc++ 15 이상 또는 libc++) CMake 지원이 실험 단계를 벗어나면
- 모듈과 clangd / VS Code IntelliSense(`--experimental-modules-support`, BMI가 든 `compile_commands.json`) — KI-037(새)
- `find_package(atugcc)`로 설치된 모듈을 import하는 사용자 프로젝트 — KI-038(새)
- core 구현을 모듈 유닛으로 옮기기, `pattern`·`engine`·`libs`의 모듈 — 070-14 뒤 영역별 작업
- 헤더 유닛(`import "x.hpp";`) — CMake 미지원, 계획 없음
- Linux의 GCC — 뺐다(Assumption 1). 나중에 필요하면 새 작업
- CI — KI-021은 그대로, "Linux GCC presets" 문구만 §8에 따라 고친다

## 7. Dependencies & Backends
- Linux 기계 패키지: `clang-20`, `clang-tools-20`, `libstdc++-14-dev`(Ubuntu 24.04 universe), `cmake` 4.0 이상(Kitware APT), `ninja-build`(기존). 새 라이브러리 의존성 없음. `vcpkg.json`은 그대로.

## 8. Documentation Updates
| Document | Section | Change |
|---|---|---|
| [`README.md`](/README.md) | 트리 주석, 기능 목록, preset 표, 플레이그라운드 준비, Workflow 4단계, Windows 메모 | GCC → Clang 20. `import atugcc.core;` 한 문장과 `modules.md` 링크 |
| [`docs/artifacts/linux_build_setup.md`](/docs/artifacts/linux_build_setup.md) | 설치 | `clang-20 clang-tools-20 libstdc++-14-dev`, CMake 4의 Kitware APT, 버전 확인 명령. `g++`는 이제 필요 없음 |
| [`.agent/rules/impl.md`](/.agent/rules/impl.md) | Primary Targets, 새 "Modules" 항목 | Linux(Clang 20). 모듈 이름 `atugcc.<area>`, `modules/atugcc/`, 래퍼 패턴, include-before-import, 모듈로는 매크로가 안 감 |
| [`.agent/rules/test.md`](/.agent/rules/test.md) | §3, §4 | `-Wall -Wextra`(Clang). 매트릭스 "Clang 20: `linux-x64-debug`" |
| [`.agent/rules/config.md`](/.agent/rules/config.md) | §2, §3, §5 | preset은 Clang 20, CMake 4.0 이상. 실패 행: `clang-scan-deps`를 못 찾음 → `clang-tools-20`, 컴파일러를 바꾼 뒤 낡은 BMI → `--fresh` |
| [`.claude/agents/cpp-reviewer.md`](/.claude/agents/cpp-reviewer.md) | 위험 목록 | "MSVC / GCC" → "MSVC / Clang". 모듈 위험(빠진 export, import 뒤 include) |
| [`docs/specs/00_template.md`](/docs/specs/00_template.md) | §2.3, §9 | MSVC vs Clang; CMake 4.0+ |
| [`docs/artifacts/project_blueprint.md`](/docs/artifacts/project_blueprint.md) | 컴파일러 행 | Clang 20(Linux) |
| [`lessons/README.md`](/lessons/README.md) | 빌드 규칙, 구성 표 | Linux(Clang 20, libstdc++ 14) |
| [`lessons/intro.md`](/lessons/intro.md), [`intro.en.md`](/lessons/intro.en.md) | Windows 빌드 항목 | "WSL의 GCC" → Clang |
| [`web/README.md`](/web/README.md) | Requirements | GCC → Clang 20 + CMake 4 |
| [`docs/cpp_evolution/format.md`](/docs/cpp_evolution/format.md) | `std::print` 지원 | Linux 툴체인에 이제 `<print>`가 있음. 레슨 단계는 070-14 |
| `lessons/tracks/01_essentials/02_format_text/README.md`, `README.en.md` | `std::print` 메모 | "GCC 13에 `<print>` 없음" → 있음. 단계는 070-14가 더함 |
| `docs/cpp_evolution/modules.md` | 새 페이지(영어, 기존 페이지 형식) | §3 비교, `core.cppm`의 래퍼 패턴, 컴파일러별 BMI·스캔, include-before-import, 모듈이 나르지 않는 것(매크로), 테스트 링크 |
| [`docs/known_issues.md`](/docs/known_issues.md) | KI-033, KI-035, KI-021, 새 KI-036–038 | KI-035는 070-13으로 CLOSED. KI-033 제목과 목록 변경(Assumption 17), Next → 070-14. KI-021 문구. KI-036 `import std`, KI-037 IDE, KI-038 사용자 프로젝트 테스트 |
| [`docs/tasks/agent_todo.md`](/docs/tasks/agent_todo.md) | Phase 7, 순서 목록 | 070-13 줄과 상태, 070-14 BACKLOG, 070-11/070-12/070-13 순서(사용자 결정) |
| `.vscode/tasks.json` | gcc build-active-file 작업 | **바꾸지 않음**(preset 빌드가 아닌 로컬 편집기 도우미). 놓친 것으로 세지 않도록 적어 둔다 |

## 9. Technical Constraints
- Compiler: MSVC (VS 2026) / Clang 20 + libstdc++ 14 (Linux)
- CMake: 4.0+, Ninja
- C++ Standard: C++23 (C++20 minimum). 모듈은 C++20

## 10. Context & References
- [KI-035](/docs/known_issues.md), [KI-033](/docs/known_issues.md)
- 기존 모듈 파일: [`src/core/alog.cppm`](/src/core/alog.cppm), [`modules/sample_module.cppm`](/modules/sample_module.cppm). [`CMakeLists.txt`](/CMakeLists.txt)(Windows 전용 `FILE_SET CXX_MODULES`, 설치 분기), [`CMakePresets.json`](/CMakePresets.json)
- 공개 core 헤더: [`logger.hpp`](/include/atugcc/core/logger.hpp), [`error.hpp`](/include/atugcc/core/error.hpp), [`log_buffer_config.hpp`](/include/atugcc/core/log_buffer_config.hpp), [`ring_buffer.hpp`](/include/atugcc/core/ring_buffer.hpp), [`timestamp.hpp`](/include/atugcc/core/timestamp.hpp)
- 시험 2026-11-03(WSL, Clang 20.1.2, libstdc++ 14.2, CMake 4.4.5). 저장소 밖의 임시 프로젝트와, 커밋하지 않는 `CMakeUserPresets.json`(`linux-x64-*`를 상속하고 `CMAKE_CXX_COMPILER=clang++-20`만 바꾼 preset)으로:
  - 파티션이 있는 모듈(`export import :text`), 구현 유닛, 클래스 템플릿, 헤더를 감싼 모듈, 그리고 `<print>`/`<string>`을 import보다 먼저 include하는 importer를 만든 임시 프로젝트: Debug와 ASan+UBSan에서 빌드·실행 성공
  - 저장소의 `sample_module.cppm`과 `alog.cppm`(`logger.hpp`, Boost 포함)을 import해 호출: 실행 성공(KI-035의 GCC 13 빌드는 크래시)
  - 저장소 전체를 Clang 20, `-Werror`로: 경고 세 개, 모두 `main.cpp`가 끌어오는 `factory.hpp` / `iterator_concept.hpp`(Assumption 12). 나머지 타깃은 빌드됐고 전체 테스트 통과(21/21)
  - 같은 방법으로 ASan+UBSan(`linux-x64-asan` 상속): 같은 경고 세 개 외에는 빌드, 전체 테스트 통과(21/21)
  - TSan(`linux-x64-tsan` 상속): 경고 세 개와, `log_service.cpp`가 libstdc++ 14.2 `<mutex>`에서 컴파일 오류(Assumption 18). 그래서 `atugcc_core`가 빌드되지 않아 테스트가 돌지 않음. 저장소 밖 임시 worktree에서 Assumption 12의 소멸자 두 개와 Assumption 18의 한 줄을 넣으면 경고·오류 없이 빌드되고 전체 테스트 통과(20/20, `-LE playground`)
  - C++23 시험: Assumption 17

## 11. Implementation Plan
- [ ] Step 1: preset과 `CMakeLists.txt`(툴체인, CMake 4, 스캔, file set, 설치). 옛 모듈 파일 둘과 `main.cpp`의 import 삭제
- [ ] Step 2: `factory.hpp`, `iterator_concept.hpp`의 virtual 소멸자. `log_service.cpp`의 `try_lock_for`(Assumption 18, risky unit)
- [ ] Step 3: `modules/atugcc/core.cppm`
- [ ] Step 4: `tests/modules/test_core_module.cpp`, `test_core_module_mixed.cpp`, `tests/CMakeLists.txt`
- [ ] Step 5: `runner.py` 대체값
- [ ] Step 6: §8 문서, KI 갱신, `docs/cpp_evolution/modules.md`

## 12. Verification Plan
- [ ] `py -3 .agent/scripts/build.py --preset windows-x64-debug --test`와 `--preset linux-x64-debug --test`(경고 없음, 전체 테스트)
- [ ] `--preset linux-x64-asan --test`, `--preset linux-x64-tsan --test`
- [ ] `--preset linux-x64-playground`, `linux-x64-playground-release` 빌드
- [ ] 두 호스트에서 `--gtest-filter "CoreModule*"`
- [ ] 두 호스트에서 `cmake --install out/build/<p>`, 목록을 testrecord에
- [ ] `linux-x64-debug` 전체 빌드 시간: 전(GCC, 스캔 끔)과 후(Clang, 스캔 켬)를 기록(AC 아님)
- [ ] `lint_docs.py`, `lessons.py check` exit 0
- [ ] 모든 AC 행의 증거가 `testrecord.md`에

## History / Amendments
- 2026-11-03: 툴체인 시험 뒤 초안. BACKLOG 줄보다 범위를 좁힘(레슨 → 070-14)
- 2026-11-03: 승인. 사용자 결정으로 Assumption 4(최소 버전 4 이상), 5(모듈을 끄는 옵션 없음, 스캔이 꺼지면 configure 실패)를 보강
