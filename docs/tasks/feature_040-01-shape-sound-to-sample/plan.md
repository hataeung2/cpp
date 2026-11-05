# Plan: 040-01 shape / sound를 sample로

- Spec: [/docs/specs/040_01_shape_sound_to_sample.md](/docs/specs/040_01_shape_sound_to_sample.md) (approved 2026-11-05, 사용자가 스펙 검토 없이 진행하라고 함)
- Branch: `feature/040-01-shape-sound-to-sample` (from `main` at `5e41ee6`)

## Files
- [MOVE] `include/atugcc/libs/{shape,sound}.h`, `src/libs/{shape,sound}.cpp`, `libs/CMakeLists.txt` → `sample/libs/` (`git mv`)
- [NEW] `libs/CMakeLists.txt` (구조 주석만)
- [MODIFY] `CMakeLists.txt` (`add_subdirectory(sample/libs)`를 samples 블록 안에), `main.cpp` (include, 주석 속 예시의 이름)
- [MODIFY] `sample/libs/*` (소스 경로, `namespace sample`, camelCase)
- [MODIFY] 스펙 §8 문서

## Units
| Unit | File | Change (what, where, AC) | Check | Risky | Author | Reviewer | Tokens (in / out) | Status |
|---|---|---|---|---|---|---|---|---|
| U1 | 위 MOVE, `libs/CMakeLists.txt`, 루트 `CMakeLists.txt`, `main.cpp` include | 옮기기 (AC-1, AC-2) | `git status`, AC-2 `git grep` | no | lead (scripted) | lead: 두 preset 빌드 | — | done |
| U2 | `sample/libs/*`, `main.cpp` 주석 | `namespace sample`, camelCase (AC-4) | 확인 실행 두 호스트 | no | lead (small) | lead: 확인 실행 | — | done |
| U3 | 스펙 §8 문서 | 문서 (AC-5) | 문서 게이트 | no | lead | 문서 게이트 | — | done |

`cpp-reviewer`는 부르지 않았다: 위험하지 않은 기계적 이동이고(delegation.md §1의 `lead (scripted)`/`lead (small)`), 바뀐 코드는 예시 클래스 두 개의 이름공간과 이름뿐이며 두 호스트의 실행 결과로 확인했다.
