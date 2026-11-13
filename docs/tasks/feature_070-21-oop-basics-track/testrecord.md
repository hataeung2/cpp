# Test record: 070-21 OOP basics track (`03_oop_basics`)

- Spec: [/docs/specs/070_21_oop_basics_track.md](/docs/specs/070_21_oop_basics_track.md)
- Plan: [plan.md](plan.md)
- Hosts: Windows 11 (MSVC, `windows-x64-debug`), WSL2 Ubuntu 24.04 (Clang 20, libstdc++ 14: `linux-x64-debug`, `linux-x64-asan`, the web's `linux-x64-playground`).
- AC-5 method: as in 070-20: apply the answer's change to the practice copy, run `tools/exercises.py check <lesson> --preset <p>`, read the row, reset the copy.

## Runs
| # | What | Expected | Result | Verdict |
|---|---|---|---|---|
| R1 | `build.py --preset windows-x64-debug --target lesson_<id>` ×4, then the same on `linux-x64-debug` (WSL) | built with `-Werror` / `/W4`-class warnings as errors, 0 warnings | all built; the only compile error seen was a typo of mine (`movedAlice`) fixed before the first run | Pass |
| R2 | run the four programs on both OSes, compare | equal output, exit 0 | `class_basics`, `object_lifetime`, `copy_and_move`, `inheritance_virtual`: byte-identical (CRLF stripped), exit 0 | Pass |
| R3 | `py -3 tools/lessons.py check` | 0 / 0 | 0 errors, 0 warnings (21 lessons, 3 tracks) | Pass |
| R4 | `lessons.py index` | tracks in order essentials, patterns, oop_basics | `['01_essentials', '02_patterns', '03_oop_basics']` | Pass |
| R5 | solve loop, both presets (13 exercises) | every automatic exercise passes | 12 / 12 pass on MSVC and on Clang (table below) | Pass |
| R6 | `build.py --preset windows-x64-debug --test` | all pass, 0 warnings | 61 / 61, 0 warning lines, 21 × `exercises_verify` Passed | Pass |
| R7 | `build.py --preset linux-x64-debug --test` (WSL) | same | 61 / 61, 0 warning lines, 21 × `exercises_verify` Passed | Pass |
| R8 | `build.py --preset linux-x64-asan --test --label lesson` (WSL) | the four lessons pass under ASan + UBSan | 42 / 42; `lesson.class_basics`, `lesson.object_lifetime`, `lesson.copy_and_move`, `lesson.inheritance_virtual` Passed | Pass |
| R9 | browser (Claude in Chrome) against `tools/playground.py --port 8790` | AC-4 | see AC-4 | Pass |
| R10 | `py -3 .agent/scripts/lint_docs.py` | exit 0 | 0 errors, 0 warnings | Pass |
| R11 | compiler behaviour of the exercises, run on both compilers | the texts are true | `explicit_meters`, `loose_class` (`C2248` / `'balance' is a private member`), `swap_members`, `early_return` (3 / 3), `keep_temp` (`alive after the statement: 1`), `delete_copy` (`C2280` / `call to deleted constructor of 'Tracked'`), `no_noexcept` (`relocation used only moves: false` on both), `override_typo` (`C3668` / `only virtual member functions can be marked 'override'`), `abstract_object` (`C2259` / `variable type 'Shape' is an abstract class`), `final_inherit` (`C3246` / `base 'Square' is marked 'final'`). `init_order`: Clang `field 'second_' will be initialized after field 'first_' [-Werror,-Wreorder-ctor]`, MSVC builds with no message (so it is an observation exercise). `nonvirtual_dtor`: both stop at `~FileResource() override`; with `override` removed too both build **without any warning** and run (undefined behaviour, so the exercise tells the reader not to run it) | Pass; draft exercise 2 of `inheritance_virtual` changed |

## AC-5: automatic exercises solved by their answers
| Lesson | Exercise | MSVC | Clang |
|---|---|---|---|
| `class_basics` | `explicit_meters`, `loose_class` | pass, pass | pass, pass |
| `object_lifetime` | `swap_members`, `early_return`, `keep_temp` | pass ×3 | pass ×3 |
| `copy_and_move` | `delete_copy`, `moved_from` (rerun after the regex was anchored), `no_noexcept` | pass ×3 | pass ×3 |
| `inheritance_virtual` | `override_typo`, `nonvirtual_dtor`, `abstract_object`, `final_inherit` | pass ×4 | pass ×4 |

Observation: `class_basics` `init_order`.

## Reviews
| Unit | Reviewer | Question | Findings | Resolution |
|---|---|---|---|---|
| U2–U5 `main.cpp`, U6–U7 text | `cpp-reviewer` | UB, dangling, leaks, unstable output, naming; README and exercise claims against code and the other language; regexes against the original; hints that print the answer; wrong teaching | code: none. Text: `moved_from` regex unanchored, `moved_from` and `keep_temp` hints printed the solving line, "extension does not apply through a member" was wrong, "the only difference" between `struct` and `class` ignored the default base access (README ×2, answer), a move "empties" the original, `base` read as a class name; the removal of two `variant` aliases from `tags.toml` is not in §8 | fixed in one round (regex anchored and rerun on both compilers; hints reworded; texts corrected); the alias move is intended and recorded in plan.md and the walkthrough |

## Acceptance criteria
| AC | Evidence | Verdict |
|---|---|---|
| AC-1 | R1, R2, R6, R7: builds without warnings on both presets, `lesson.<id>` passes, output has the step headers and the key lines (destruction order, copy and move counts, slicing result) | Pass |
| AC-2 | R8: the four lessons pass on `linux-x64-asan` | Pass |
| AC-3 | R3, R10: `lessons.py check` 0 / 0 (titles, English README, tags, exercise counts), `lint_docs.py` exit 0 | Pass |
| AC-4 | R4, R9: the tree lists `03_oop_basics` after `02_patterns` (Korean and English); the English screen shows the track title, the four lesson titles and the English README (`README.en.md`) with the tags `Class`, `const`, `Error handling`; typing `소멸자` finds `object_lifetime` and `inheritance_virtual`, `virtual` finds `variant_visit` and `inheritance_virtual`, `상속` lists the four lessons of the track, `RAII` finds `object_lifetime` | Pass |
| AC-5 | R5, R6, R7: `exercises.py check` passes the 12 automatic exercises on both compilers; `lesson.<id>.exercises_verify` passes for all 21 lessons (the original passes no automatic exercise) | Pass |
| AC-6 | a script over the four pairs: sections 4 / 4, code blocks 1 / 1, exercises 3 / 3 / 3 / 4 equal; the links match, the English version links the English README (the only shared link is `/lessons/README.md`, which has no English version) | Pass |
| AC-7 | `lesson_candidates.md` has the table (4 × `레슨 있음`, 3 × `후보`); `lessons/README.md` and `intro.md` / `intro.en.md` name the track (the intro page showed the new line in the browser); `lint_docs.py` (links) exit 0 | Pass |
| AC-8 | R6, R7: 61 / 61 on both presets | Pass |
