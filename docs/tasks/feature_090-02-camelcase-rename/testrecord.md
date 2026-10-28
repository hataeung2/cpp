# Test Record: 090-02 함수 명명 camelCase 통일

## Acceptance Criteria Evidence
| AC | Evidence | Result |
|---|---|---|
| AC-1 | `py -3 .agent/scripts/naming_check.py` after the rename: `0 snake_case function name(s)`, exit 0 (before: 41) | Pass |
| AC-2 | `build.py --preset windows-x64-debug --test` (MSVC `/W4 /WX`) and `--preset linux-x64-debug --test` (GCC `-Wall -Wextra -Werror`): both exit 0, `100% tests passed` | Pass |
| AC-3 | `atugcc_tests --gtest_list_tests` before and after: identical (75 lines) | Pass |
| AC-4 | `visualizer.hpp` header example uses `formatTerminal()` / `formatDiagram()`; no old name in README, `include/`, `src/`, `tests/`, `sample/`, `main.cpp` except string literals in trace output (`"on_notify()"`) and the variable `on_notify_fn` | Pass |

## Runs
| Test | Expected | Actual | Status |
|---|---|---|---|
| `naming_check.py --apply` | 41 names, only identifiers in code and comments | `renamed 41 names in 12 files`; `git diff --stat` +247 / −247 lines (pure substitutions) | Pass |
| Script self-tests | all pass | `Ran 49 tests ... OK` (4 new `NamingCheckTest`) | Pass |
| Windows debug build + suite | 0 warnings, pass | exit 0, `100% tests passed` | Pass |
| Linux debug build + suite (WSL) | 0 warnings, pass | exit 0, `100% tests passed` | Pass |
| Test list comparison | identical | `test list identical` | Pass |
| `lint_docs.py` | exit 0 | `0 error(s), 0 warning(s), 19 info` | Pass |

## Reviews
| Unit | Reviewer | Question | Findings | Resolution |
|---|---|---|---|---|
| U2 (12 files, 41 renames) | codex `luna`, effort medium (258,754 in incl. 228,224 cached / 1,465 out, 35 s) | (a) pure renames from the map only; (b) literals or non-function identifiers touched; (c) concept requirements/implementers and out-of-class definitions consistent; (d) std/POSIX/Boost exceptions renamed | none on all four items | — |
