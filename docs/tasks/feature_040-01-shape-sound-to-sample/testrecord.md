# Test Record: 040-01 shape / sound를 sample로

- Spec: [/docs/specs/040_01_shape_sound_to_sample.md](/docs/specs/040_01_shape_sound_to_sample.md)
- Host: Windows 11 (MSVC, `windows-x64-debug`), WSL Linux (Clang 20, `linux-x64-debug`), `py -3 .agent/scripts/build.py`

## Runs — 2026-11-05
| Command | Result |
|---|---|
| `build.py --preset windows-x64-debug --test --report` (첫 실행, `namespace` 전) | 경고 0; 34/35, `lesson.testing` `***Timeout 13.07 sec` (KI-046) |
| `build.py --preset windows-x64-debug --label lesson` ×2 | 17/17 두 번, `lesson.testing` 0.05 s, 0.04 s |
| `build.py --preset windows-x64-debug --label lesson --report out/test-reports/windows-x64-debug/040-01-lesson-rerun` | 17/17 |
| `build.py --preset linux-x64-debug --test --report` (첫 실행) | 경고 0; 35/35 |
| 확인 실행 1 (Windows, 예시 줄 주석 풀고 `--target atugcc_sample`) | C2146 `missing ';' before identifier 'r'` (`main.cpp:155`): `<Windows.h>`의 `Rectangle()` 함수. Assumption 4 |
| 확인 실행 2 (Windows, `namespace sample` 뒤) | 경고 0, `rectangle size: 2`, `sound volume: 10` (`bin/sound.dll`) |
| 확인 실행 3 (Linux, 같은 줄) | 경고 0, `rectangle size: 2`, `sound volume: 10`; `ldd`: `libsound.so => .../out/build/linux-x64-debug/lib/libsound.so` |
| `build.py --preset windows-x64-debug --test --report out/test-reports/windows-x64-debug/040-01-final` (최종, 예시 줄은 다시 주석) | 경고 0; 35/35 |
| `build.py --preset linux-x64-debug --test --report out/test-reports/linux-x64-debug/040-01-final` (최종) | 경고 0; 35/35 |
| `py -3 .agent/scripts/naming_check.py` | 0 |
| `py -3 .agent/scripts/lint_docs.py` | 0 error, 0 warning |

## AC evidence
| AC | Evidence | Result |
|---|---|---|
| AC-1 | `git ls-files include/atugcc/libs src/libs`: 0개; `git ls-files sample/libs`: `CMakeLists.txt`, `shape.{h,cpp}`, `sound.{h,cpp}`; `git ls-files libs`: `libs/CMakeLists.txt` (주석 3줄) | pass |
| AC-2 | `git grep "atugcc/libs\|src/libs\|GetSize\|MakeNoize"` (봉인된 기록, 스펙, KI 기록 제외): 0건 | pass |
| AC-3 | 최종 두 실행: 경고 0, 35/35 | pass |
| AC-4 | 확인 실행 2, 3 | pass |
| AC-5 | 문서 게이트 0 error, 0 warning | pass |
