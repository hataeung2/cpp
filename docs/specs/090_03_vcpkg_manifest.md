---
id: 090-03
title: vcpkg manifest로 Boost 자동 공급
depends_on: [090-01]
unblocks: []
approved: 2026-10-28
---

# Spec 090-03: vcpkg manifest로 Boost 자동 공급

## 0. Assumptions (please review)
| # | Decision | Rejected alternative | Why |
|---|---|---|---|
| 1 | `vcpkg.json`(의존성) + `vcpkg-configuration.json`(git 레지스트리 + baseline) | `vcpkg.json`의 `builtin-baseline`만 사용 | VS 번들 vcpkg는 내장 포트 트리가 없어 레지스트리를 명시해야 한다. git 레지스트리는 별도 설치 vcpkg에서도 같은 방식으로 동작한다 |
| 2 | baseline = vcpkg 릴리스 2026.07.29 (`9e593bb18ea69cc5095e012465dcd675a822ed0d`) | 최신 릴리스 2026.10.16 | 이 머신의 번들 vcpkg 도구가 2026-07-27 버전이다. 도구보다 새 레지스트리의 포트는 새 헬퍼 함수를 요구할 수 있다. 올리는 것은 별도 작업으로 한다 |
| 3 | 의존성은 `boost-lockfree` 하나 | `boost` 전체 | 코드가 쓰는 것은 lockfree 큐뿐이다(`log_queue.hpp`). 전체 Boost는 설치 시간이 길다 |
| 4 | vcpkg가 없으면(`ATUGCC_VCPKG_ROOT`, `VCPKG_ROOT` 모두 없음) 지금처럼 시스템 패키지를 쓴다 | vcpkg 필수화 | WSL/Ubuntu는 시스템 Boost로 이미 빌드된다. 같은 preset이 두 경우를 모두 처리한다 |

## 1. Objective
어느 PC에서든 같은 `CMakePresets.json`으로 Boost를 찾게 한다. VS 개발자 환경이 가리키는 번들 vcpkg에서도, 별도로 설치한 vcpkg에서도 manifest가 Boost를 빌드 디렉터리에 자동 설치한다(KI-007).

## 2. Requirement Details
### 2.1 Public API Surface
none

### 2.2 Internal Implementation
- 저장소 루트에 `vcpkg.json`, `vcpkg-configuration.json` 추가.
- `CMakeLists.txt`의 툴체인 탐색은 그대로 둔다(`-DCMAKE_TOOLCHAIN_FILE` → `ATUGCC_VCPKG_ROOT` → `VCPKG_ROOT` → 시스템). 툴체인이 잡히면 vcpkg가 manifest 모드로 동작한다.

### 2.3 Platform Specifics
- Windows: VS 개발자 환경(VsDevCmd, VS, VS Code CMake Tools)이 `VCPKG_ROOT`를 번들 vcpkg로 설정한다 → 추가 설정 없이 동작.
- Linux: `VCPKG_ROOT`가 있으면 manifest, 없으면 시스템 Boost.
- 첫 configure는 네트워크로 레지스트리와 Boost 소스를 받는다(이후 vcpkg binary cache 재사용).

## 3. C++ Standard Evolution
N/A

## 4. Edge Cases
- [x] 오프라인 첫 configure: vcpkg가 실패를 보고한다 → README에 네트워크 필요 명시
- [x] 별도 설치 vcpkg에 이미 classic 모드로 설치된 Boost: manifest가 있으면 manifest가 우선한다 (vcpkg 동작)
- [x] `out/build/<preset>/vcpkg_installed`는 `out/` 아래라 git에 들어가지 않는다

## 5. Acceptance Criteria
| ID | Criterion | Verified by |
|---|---|---|
| AC-1 | 이 머신에서 환경 변수 설정 없이 `build.py --preset windows-x64-debug --test`가 configure, 빌드(경고=오류), 전체 테스트를 통과한다 | 실행 기록 |
| AC-2 | `linux-x64-debug`(WSL, vcpkg 없음)가 시스템 Boost로 계속 통과한다 | 실행 기록 |
| AC-3 | `CMakePresets.json`, `vcpkg*.json`에 머신 경로가 없다 | `lint_docs.py` |
| AC-4 | README, config.md가 manifest 방식을 설명하고 KI-007이 CLOSED다 | 리뷰, lint |

## 6. Out of Scope
- vcpkg baseline 갱신 정책 — 필요할 때 별도 작업
- googletest를 vcpkg로 옮기기 (지금은 FetchContent) — 필요 시 별도 작업

## 7. Dependencies & Adapters
vcpkg (선택), Boost.Lockfree

## 8. Documentation Updates
| Document | Section | Change |
|---|---|---|
| `README.md` | Environment-Specific Configuration | manifest 방식, 네트워크 필요, `ATUGCC_VCPKG_ROOT`는 선택 사항 |
| `.agent/rules/config.md` | §3, §5 | manifest 설명, Boost 오류 대응 |
| `docs/known_issues.md` | KI-007 | CLOSED |

## 9. Technical Constraints
- vcpkg 도구 2026-07-27 이상 (VS 2026 번들)

## 10. Context & References
- [CMakeLists.txt](/CMakeLists.txt)
- [log_queue.hpp](/include/atugcc/core/log_queue.hpp)
- [KI-007](/docs/known_issues.md)

## 11. Implementation Plan
- [ ] U1 `vcpkg.json`, `vcpkg-configuration.json`
- [ ] U2 Windows / Linux 빌드·테스트
- [ ] U3 README, config.md, KI-007

## 12. Verification Plan
- [ ] AC-1–AC-4 증거를 `docs/tasks/feature_090-03-vcpkg-manifest/testrecord.md`에 기록

## History / Amendments
- 2026-10-28: 사용자가 KI-007의 권장안 (a) manifest 방식을 승인 ("어디서나 같은 config").
