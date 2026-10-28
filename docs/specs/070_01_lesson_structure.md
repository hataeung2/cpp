---
id: 070-01
title: 레슨 구조 — 트랙·레슨·유닛, preset 빌드, 레슨 인덱스
depends_on: []
unblocks: [070-02, 070-03, 070-04]
approved: 2026-10-28
---

# Spec 070-01: 레슨 구조 — 트랙·레슨·유닛, preset 빌드, 레슨 인덱스

## 0. Assumptions (please review)
| # | Decision | Rejected alternative | Why |
|---|---|---|---|
| 1 | 학습 내용은 `lessons/` 아래에 두고 **레슨**(실행 단위)과 **유닛**(재사용 단위)을 분리한다 | 트랙 폴더 안에 코드를 모두 넣기 | 사용자 요구: "폴더별로 나누되 어떤 레슨에서든 개별 유닛을 가져와 볼 수 있게". 유닛은 한 곳에만 있고 여러 레슨이 참조한다 |
| 2 | 라이브러리 헤더(`include/atugcc/...`)도 `lib:` 참조로 유닛처럼 쓴다. 복사하지 않는다 | 레슨용 사본 | 라이브러리를 고치면 레슨에 바로 반영된다. 사본은 금방 낡는다 |
| 3 | 매니페스트는 TOML(`lesson.toml`, `unit.toml`) | YAML / JSON | Python 표준 라이브러리(`tomllib`, 3.11+)로 읽을 수 있다(스크립트는 stdlib만, 090-01 §8). YAML은 외부 패키지가 필요하고 JSON은 손으로 쓰기 불편하다 |
| 4 | 모든 레슨은 CMake 실행 타깃이고 preset으로 빌드된다. 레슨 폴더를 추가하면 자동으로 발견된다(`CONFIGURE_DEPENDS` glob) | 웹 전용 빌드 / 레슨마다 CMake 목록 수정 | 목표는 "직접 컴파일 작업과 웹 작업 반반"이다. 같은 레슨이 VS Code와 Visual Studio(preset 빌드)와 웹(070-02)에서 같은 타깃으로 빌드되어야 결과가 같다. Non-negotiable Rule 2 |
| 5 | 각 레슨은 ctest에 smoke test(종료 코드 0, 10초 제한)로 등록된다 | 테스트 없음 | 레슨이 라이브러리 변경으로 깨지면 바로 보인다. 레슨은 교육용이라 동작 검증보다 "빌드되고 끝까지 돈다"가 기준이다 |
| 6 | 트랙은 두 개로 시작한다: `01_essentials`(core, 문법, 스레드·로그 관리) → `02_patterns`(도메인·상황별 패턴 적용과 변형) | 패턴부터 | 사용자 결정(2026-10-28): 어느 시스템에나 필요한 것을 먼저, 그다음 패턴 |
| 7 | 이 작업은 구조와 도구, 그리고 구조를 증명하는 **시드 레슨 3개와 유닛 2개**만 만든다. 커리큘럼 내용은 070-03(essentials)과 070-04(patterns)로 넘긴다 | 커리큘럼까지 한 작업 | 구조 검증과 내용 작성은 검토 관점이 다르다. 한 브랜치가 너무 커진다 |
| 8 | `main.cpp`의 주석 처리된 샘플과 `src/pattern/example_visualizer.cpp`는 옮기지 않는다 | 이번에 레슨으로 이동 | 기존 타깃(`atugcc_sample`, `atugcc_pattern_example`)과 문서가 참조한다. 070-04에서 레슨으로 옮기며 정리한다 |
| 9 | 레슨 인덱스는 `tools/lessons.py`가 만들고 빌드 산출물(gitignore)로 둔다 | 커밋되는 인덱스 파일 | 매니페스트가 원본이다. 커밋하면 원본과 어긋날 수 있다 |
| 10 | 레슨은 실행 프로필을 선언한다: `quick`(기본, 짧은 예제) / `long`(성능 측정 등 장시간). 이 작업은 스키마와 ctest 처리만 정하고, 웹 실행 제한은 070-02(quick)와 070-06(long)이 정한다 | 모든 레슨에 같은 제한 | 사용자 요구(2026-10-28): 성능 측정 레슨은 10초로 부족하다. 실수로 만든 무한 루프가 짧은 레슨에서 몇 분씩 돌면 안 된다 |

## 1. Objective
atugcc를 학습·연습용으로 쓰기 위한 내용 구조를 만든다. 레슨은 로컬 preset 빌드와 웹 플레이그라운드(070-02)에서 **같은 소스, 같은 타깃**으로 빌드·실행된다. 유닛은 트랙과 레슨을 가로질러 재사용된다. 웹은 `tools/lessons.py`가 만든 인덱스로 목록과 참조 관계를 보여 준다.

## 2. Requirement Details

### 2.1 디렉터리 구조
```text
lessons/
  CMakeLists.txt                  # 레슨 자동 발견, 타깃·테스트 등록
  units/
    <unit_id>/
      unit.toml
      README.md                   # 유닛 설명 (웹에서 렌더링)
      <unit_id>.hpp               # 레슨이 #include "units/<unit_id>/<unit_id>.hpp" 로 가져옴
  tracks/
    01_essentials/
      track.toml                  # title, summary
      01_lambda_capture/
        lesson.toml
        README.md                 # 설명 + 연습 과제
        main.cpp                  # 진입점 (레슨 하나 = 실행 파일 하나)
    02_patterns/
      ...
```

### 2.2 매니페스트 스키마
```toml
# lessons/tracks/02_patterns/01_device_state_machine/lesson.toml
id      = "device_state_machine"        # 저장소 전체에서 유일, [a-z0-9_]
title   = "장비 상태 머신에 State 패턴 적용"
summary = "IDLE/STANDBY/RUN 전이를 Tracer로 보고, 전이 규칙을 바꿔 본다"
sources = ["main.cpp"]                 # 레슨 폴더 기준, 첫 항목이 진입점
uses    = [
  "unit:jthread_worker",               # lessons/units/jthread_worker/
  "lib:atugcc/pattern/state.hpp",      # include/ 기준
  "lib:atugcc/pattern/visualizer.hpp",
]
tags    = ["state", "tracer"]

[run]                                  # 선택. 없으면 profile = "quick"
profile = "quick"                      # "quick" | "long" (Assumption 10)
timeout = 300                          # 초. long에서만 의미, 기본 300, 최대 1800
```
```toml
# lessons/units/jthread_worker/unit.toml
id      = "jthread_worker"
title   = "std::jthread + stop_token 작업 스레드"
files   = ["jthread_worker.hpp"]
uses    = ["lib:atugcc/core/logger.hpp"]  # 유닛도 다른 유닛·라이브러리를 참조할 수 있다
```
- 트랙과 레슨의 순서는 폴더 이름의 숫자 접두사로 정한다.
- `uses`는 웹에서 "관련 파일" 탭으로 열 목록이다. 실제 컴파일 의존성은 `#include`가 정한다. 둘이 어긋나는지는 `lessons.py check`가 경고한다(§2.4).

### 2.3 CMake
- `option(ATUGCC_BUILD_LESSONS "Build lessons" ON)`, 루트 `CMakeLists.txt`에서 `add_subdirectory(lessons)`.
- `lessons/tracks/*/*/lesson.toml`을 `CONFIGURE_DEPENDS`로 glob한다. 레슨마다 타깃 `lesson_<id>`를 만든다(소스 = `sources`). include 경로는 `lessons/`, 링크 대상은 `atugcc_core`.
- 출력 파일은 `${CMAKE_RUNTIME_OUTPUT_DIRECTORY}/lessons/lesson_<id>`.
- `add_test(NAME lesson.<id> ...)`, `LABELS lesson`. quick은 `TIMEOUT 10`, long은 `TIMEOUT <timeout>`과 `LABELS lesson;long`이다. 빠른 확인 때는 `ctest -LE long`으로 제외할 수 있다.
- CMake가 TOML을 파싱할 수는 없다. CMake는 `sources`, `profile`, `timeout`만 정규식으로 읽는다(한 줄 형식으로 제한). 형식 검증은 `lessons.py check`가 맡는다.

### 2.4 `tools/lessons.py` (Python 3 stdlib)
| 명령 | 동작 |
|---|---|
| `check` | 스키마, id 유일성, `sources`/`files` 존재, `uses` 대상 존재, 순환 참조, `#include "units/..."` 및 `#include "atugcc/..."` 중 `uses`에 없는 것(WARN). 오류가 있으면 exit 1 |
| `index [--out <path>]` | 트랙 → 레슨 → 해석된 `uses`(저장소 상대 경로 목록, 전이 포함)와 역참조(유닛 → 사용하는 레슨)를 JSON으로 출력. 기본 출력 `out/lessons/index.json` |

- 함수로도 import할 수 있게 쓴다(070-02 서버가 같은 코드를 쓴다).
- `docs` lint(`lint_docs.py`)가 `lessons.py check`를 호출하도록 연결한다.

### 2.5 시드 내용 (구조 증명용)
| 종류 | id | 목적 |
|---|---|---|
| 유닛 | `lambda_capture` | 값·참조·init capture 예시 함수 모음 |
| 유닛 | `jthread_worker` | `std::jthread` + `stop_token` 작업 스레드, Logger 사용 |
| 레슨 (01_essentials) | `lambda_capture` | 유닛 `lambda_capture` 사용 |
| 레슨 (01_essentials) | `thread_and_log` | 유닛 `jthread_worker` + `lib:atugcc/core/logger.hpp` |
| 레슨 (02_patterns) | `device_state_machine` | 유닛 `jthread_worker`(트랙을 가로지르는 재사용) + State 패턴 + Tracer |

### 2.6 Platform Specifics
- 레슨은 Windows(MSVC)와 Linux(GCC) preset 모두에서 빌드돼야 한다. 플랫폼 전용 API(`memory_dump`, 데스크톱 콘솔 sink)를 쓰는 레슨은 만들지 않는다.
- 레슨 소스는 UTF-8이고 `.editorconfig`를 따른다. MSVC는 이미 `/utf-8`을 쓴다.

## 3. C++ Standard Evolution
N/A (구조와 도구 작업. 레슨 내용의 evolution 설명은 각 레슨 README가 맡는다)

## 4. Edge Cases
- [x] 같은 id의 레슨 또는 유닛 → `check` 오류, CMake도 타깃 이름 중복으로 실패한다(이중 방어)
- [x] `uses` 순환(유닛 A ↔ B) → `check` 오류. `index`는 방문 집합으로 무한 루프를 막는다
- [x] 레슨 폴더 추가·삭제 → `CONFIGURE_DEPENDS`가 다음 빌드 때 다시 glob한다
- [x] 매니페스트 문법 오류 → `check`가 파일과 줄을 보고한다(`tomllib.TOMLDecodeError`)
- [x] Thread safety: 시드 레슨 `thread_and_log`, `device_state_machine`는 `linux-x64-tsan` preset smoke test를 통과해야 한다
- N/A ODR / UB / template: 레슨은 각각 독립 실행 파일이다. 유닛 헤더의 함수는 `inline`으로 쓴다(여러 TU에서 쓰일 수 있음)

## 5. Acceptance Criteria
| ID | Criterion | Verified by |
|---|---|---|
| AC-1 | 시드 레슨 3개가 `windows-x64-debug`, `linux-x64-debug`, `linux-x64-tsan` preset에서 경고 없이 빌드되고 smoke test가 통과한다 | `build.py --preset <p> --test` |
| AC-2 | 새 레슨 폴더(매니페스트 + main.cpp)를 복사해 추가하면 CMake 파일을 고치지 않아도 다음 빌드에서 타깃과 테스트가 생긴다 | 임시 레슨으로 수동 확인, testrecord에 기록 |
| AC-3 | `lessons.py check`가 시드에서 exit 0이고, 의도적으로 깨뜨린 fixture 7종(id 중복, 없는 uses, 순환, 없는 source, TOML 문법 오류, uses 누락 include, 잘못된 `profile`/범위 밖 `timeout`)에서 각각 해당 오류나 경고를 낸다 | `tools/test_lessons.py` (unittest) |
| AC-4 | `lessons.py index`의 JSON에서 `jthread_worker` 유닛의 역참조가 두 트랙의 레슨 2개를 가리킨다 | 같은 unittest |
| AC-5 | `ATUGCC_BUILD_LESSONS=OFF`이면 레슨 타깃이 생기지 않고 나머지 빌드·테스트는 그대로다 | 수동 configure 확인(preset에 cache 변수 덮어쓰기) |
| AC-6 | `lint_docs.py`가 `lessons.py check`를 실행하고 exit 0이다 | 실행 기록 |

## 6. Out of Scope
- essentials 트랙 커리큘럼(core, lambda, concurrency, 스레드 관리, 로그 관리) — 070-03
- patterns 트랙 커리큘럼, `main.cpp` 샘플·`example_visualizer.cpp`를 레슨으로 이전 — 070-04
- 웹 화면과 서버 — 070-02
- 공개 배포 — 070-05 (사용자 결정 대기)

## 7. Dependencies & Adapters
없음. `tomllib`(Python 3.11+ 표준). WSL Ubuntu 24.04의 Python 3.12와 Windows Python 3.15 모두 해당.

## 8. Documentation Updates
| Document | Section | Change |
|---|---|---|
| `README.md` | Project Structure, How to Build | `lessons/` 설명, `ATUGCC_BUILD_LESSONS`, 레슨 실행 방법 |
| `lessons/README.md` (신규) | 전체 | 레슨·유닛 작성법, 매니페스트 스키마, 새 레슨 추가 절차 |
| `docs/agent_start_prompt.md` | Quick reference | `tools/lessons.py check` 한 줄 |
| `.gitignore` | — | `out/lessons/` (out/이 이미 무시되면 변경 없음) |

## 9. Technical Constraints
- Compiler: MSVC (VS 2026) / GCC 13+
- CMake: 3.26+
- C++ Standard: C++23 (C++20 minimum)
- 스크립트: Python 3.11+ 표준 라이브러리만

## 10. Context & References
- [루트 CMakeLists](/CMakeLists.txt)
- [CMakePresets](/CMakePresets.json)
- [build.py](/.agent/scripts/build.py)
- [lint_docs.py](/.agent/scripts/lint_docs.py)
- [웹 플레이그라운드 스펙](/docs/specs/070_02_web_playground.md)

## 11. Implementation Plan
- [ ] Step 1: `tools/lessons.py` (check, index) + `tools/test_lessons.py` + fixture
- [ ] Step 2: `lessons/CMakeLists.txt`, 루트 연결, 옵션
- [ ] Step 3: 시드 유닛 2개, 레슨 3개
- [ ] Step 4: `lint_docs.py` 연결, 문서 갱신

## 12. Verification Plan
- [ ] `py -3 .agent/scripts/build.py --preset windows-x64-debug --test`
- [ ] `py -3 .agent/scripts/build.py --preset linux-x64-debug --test`, `linux-x64-tsan`
- [ ] `py -3 tools/test_lessons.py`, `py -3 .agent/scripts/lint_docs.py`
- [ ] Every AC row has its evidence in `testrecord.md`

## History / Amendments
- 2026-10-28: 초안. 사용자 결정 반영: 로컬 전용, 트랙 순서(essentials → patterns), 유닛 재사용.
- 2026-10-28: 검토 반영: `[run]` 실행 프로필(quick/long)과 ctest 처리 추가(Assumption 10).
- 2026-10-28: 사용자 승인.
