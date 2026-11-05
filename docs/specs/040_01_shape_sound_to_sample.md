---
id: 040-01
title: shape / sound를 sample로 옮기고 libs/를 라이브러리별 폴더 구조로
depends_on: []
unblocks: []
approved: 2026-11-05  # 사용자: "040-01까지 이번 세션에서 완료하기로 하자 ... spec까지 필요하지 않다면 바로 진행해도 좋아". 따로 검토받지 않은 기록용 스펙이다
---

# Spec 040-01: shape / sound를 sample로 옮기고 libs/를 라이브러리별 폴더 구조로

## 0. Assumptions (please review)
방향(사용자 결정 2026-11-05, KI-044): `libs/`는 프레임워크의 범용 라이브러리 자리로 남기고, `shape`·`sound`는 STATIC·SHARED 빌드 예시인 sample로 둔다. 후보와 층 나누기는 [lib_candidates.md](/docs/lib_candidates.md). 사용자가 스펙 검토 없이 진행하라고 했으므로, 아래 결정은 구현과 함께 기록한다.

| # | Decision | Rejected alternative | Why |
|---|---|---|---|
| 1 | 옮길 곳은 `sample/libs/` 한 폴더(`CMakeLists.txt`, `shape.h/.cpp`, `sound.h/.cpp`). `main.cpp`는 `#include "sample/libs/shape.h"` | `sample/libs/shape/`, `sample/libs/sound/` 두 폴더 | 파일 다섯 개짜리 예시다. 다른 sample(`sample/cond_var.hpp`)과 같은 include 형식 |
| 2 | `add_subdirectory(sample/libs)`를 `ATUGCC_BUILD_SAMPLES` 안으로. 예시를 쓰는 것은 `atugcc_sample`뿐이다 | 지금처럼 늘 빌드 | samples를 끈 preset(playground)이 쓰지 않는 라이브러리를 빌드하지 않는다 |
| 3 | 타깃 이름 `shape`, `sound`는 그대로 | `atugcc_sample_shape` 등 | 바꿀 소비자가 `atugcc_sample` 하나뿐이고, `libs/`의 새 타깃은 `atugcc_<name>`이라 겹치지 않는다 |
| 4 | 두 클래스를 `namespace sample`에 넣는다 | 전역 그대로 | Windows에서 `<Windows.h>`의 GDI 함수 `Rectangle()`과 이름이 부딪혀 `main.cpp`의 예시 줄을 켜면 C2146으로 빌드되지 않았다(이 작업의 확인 실행에서 발견) |
| 5 | 함수 이름을 camelCase로: `GetSize` → `getSize`, `MakeNoize` → `makeNoise`(오타도) | 그대로 | 명명 규칙(사용자 결정 2026-10-28, impl.md). `naming_check.py`는 snake_case만 보므로 걸리지 않았다 |
| 6 | `main.cpp`의 예시 호출은 주석으로 둔다(이름만 고침) | 주석을 풀어 늘 실행 | `main.cpp`의 sample은 모두 주석이고 하나씩 풀어 쓰는 방식이다. 확인 실행에서만 풀었다(§12) |
| 7 | `libs/CMakeLists.txt`는 폴더 구조를 적은 주석만 두고, 루트의 `add_subdirectory(libs)`는 남긴다 | `libs/`를 지우고 첫 라이브러리 때 만든다 | 라이브러리를 더할 때 `add_subdirectory(<name>)` 한 줄만 더하면 된다 |
| 8 | 내용은 현대화하지 않는다(include guard `__SHAPE__` 등 그대로) | C++23으로 다시 쓰기 | 빌드 방식 예시이고, 옛 040-01의 현대화 목적은 사용자 결정으로 없어졌다 |

## 1. Objective
`include/atugcc/libs/`, `src/libs/`, `libs/`에 흩어진 sample 라이브러리를 `sample/libs/` 한곳에 모은다. `libs/`는 [lib_candidates.md](/docs/lib_candidates.md)의 라이브러리를 `libs/<name>/`으로 받을 빈 자리로 둔다. KI-044를 닫는다.

## 2. Requirement Details

### 2.1 Public API Surface
`include/atugcc/libs/`를 없앤다(설치되는 헤더에서 `shape.h`, `sound.h`가 빠진다). sample API: `sample::Rectangle(int, int)`, `getSize()`; `sample::Sound(int)`, `makeNoise()`.

### 2.2 Internal Implementation
`git mv`로 다섯 파일을 옮기고(이력 유지), `sample/libs/*.cpp`는 같은 폴더의 헤더를 `#include "shape.h"`로 읽는다. `sample/libs/CMakeLists.txt`는 옛 `libs/CMakeLists.txt`에서 소스 경로만 바뀐다.

### 2.3 Platform Specifics
Windows에서 `sound`는 DLL(`SOUND_DECL` = `__declspec(dllexport/dllimport)`), 출력은 `bin/`(루트 `CMAKE_RUNTIME_OUTPUT_DIRECTORY`)이라 `atugcc_sample.exe` 옆에 놓인다. Linux는 `lib/libsound.so`.

## 3. C++ Standard Evolution
N/A

## 4. Edge Cases
- [x] Platform differences: Assumption 4 (`Rectangle` 이름 충돌), §2.3.
- N/A 나머지: 상태·스레드·템플릿 없는 예시 클래스 두 개, 동작은 바뀌지 않는다.

## 5. Acceptance Criteria
| ID | Criterion | Verified by |
|---|---|---|
| AC-1 | `include/atugcc/libs/`, `src/libs/`가 없고, `shape`·`sound`의 소스·헤더·CMake가 `sample/libs/`에 있다. `libs/`에는 `CMakeLists.txt`(주석)만 있다 | `git ls-files` |
| AC-2 | 옛 경로(`atugcc/libs`, `src/libs`)와 옛 이름(`GetSize`, `MakeNoize`)이 봉인되지 않은 파일에 없다 | `git grep` |
| AC-3 | `windows-x64-debug`, `linux-x64-debug` 경고 0으로 빌드, 전체 ctest 통과 | `build.py --test --report` |
| AC-4 | `main.cpp`의 예시 줄을 풀면 두 호스트에서 빌드되고 `rectangle size: 2`, `sound volume: 10`을 찍는다(Linux는 `libsound.so`를 동적 링크) | 확인 실행, `ldd` |
| AC-5 | 문서 게이트 0 error, 0 warning | `lint_docs.py` |

## 6. Out of Scope
- 첫 범용 라이브러리 — [lib_candidates.md](/docs/lib_candidates.md)에서 골라 `040-SS`로.
- 확인 실행에서 본 `lesson.testing` 시간 초과 한 번 — KI-046.

## 7. Dependencies & Backends
none

## 8. Documentation Updates
| Document | Section | Change |
|---|---|---|
| [`README.md`](/README.md) | 폴더 트리 | `include/atugcc/libs/` 줄 삭제, `libs/` 설명, `sample/libs/` |
| [`docs/lib_candidates.md`](/docs/lib_candidates.md) | 머리말 | shape/sound를 옮겼다고 |
| [`docs/guides/project_blueprint.md`](/docs/guides/project_blueprint.md) | Phase 4 | 같은 내용 |
| [`docs/known_issues.md`](/docs/known_issues.md) | KI-044, KI-046 | KI-044 닫음, KI-046 새로 |
| [`docs/agent_todo.md`](/docs/agent_todo.md) | 진행 순서, Phase 4 | 040-01 DONE |

## 9. Technical Constraints
- Compiler: MSVC (VS 2026) / Clang 20 with libstdc++ 14 (Linux)
- CMake: 4.0+ (C++20 modules always on)
- C++ Standard: C++23 (C++20 minimum)

## 10. Context & References
[KI-044](/docs/known_issues.md), [lib_candidates.md](/docs/lib_candidates.md), [main.cpp](/main.cpp), [sample/libs/CMakeLists.txt](/sample/libs/CMakeLists.txt)

## 11. Implementation Plan
- [x] Step 1: `git mv` 다섯 파일, `libs/CMakeLists.txt` 새로(주석), 루트 `CMakeLists.txt`, `main.cpp` include
- [x] Step 2: camelCase, `namespace sample`
- [x] Step 3: §8 문서

## 12. Verification Plan
- [x] Build, zero warnings, full suite: `build.py --preset windows-x64-debug --test --report`, `--preset linux-x64-debug --test --report`
- [x] AC-4 확인 실행: `main.cpp`의 네 줄 주석을 풀고 `--target atugcc_sample`로 빌드·실행한 뒤 되돌림
- [x] Every AC row has its evidence in `testrecord.md`

## History / Amendments
- 2026-11-05: 작성과 구현을 같은 세션에서(사용자 지시). Assumption 4는 확인 실행에서 더했다.
