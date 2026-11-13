# Test record: 070-20 Exercise definitions for the remaining lessons

- Spec: [/docs/specs/070_20_remaining_exercises.md](/docs/specs/070_20_remaining_exercises.md)
- Plan: [plan.md](plan.md)
- Hosts: Windows 11 (MSVC, `windows-x64-debug`), WSL2 Ubuntu 24.04 (Clang 20, libstdc++ 14: `linux-x64-debug`, `linux-x64-tsan`, the web's `linux-x64-playground`). "Web" means the Clang/libstdc++ build.
- Method for AC-3: a script in the lead's scratch directory (not committed) applies the answer's change to the practice copy, deletes the lesson's progress record, runs `tools/exercises.py check <lesson> --preset <p>`, reads the row of that exercise and resets the copy (`tools/practice.py reset`). The 070-17 rule that the copy must differ from the original is part of the check.

## Runs
| # | What | Expected | Result | Verdict |
|---|---|---|---|---|
| R1 | `py -3 tools/lessons.py check` after the last edit | 0 / 0 | 0 errors, 0 warnings (the 13 new files included: item counts equal) | Pass |
| R2 | solve loop, `windows-x64-debug` | every automatic exercise passes | 28 / 28 pass (table below) | Pass |
| R3 | solve loop, `linux-x64-debug` (WSL) | same | 28 / 28 pass | Pass |
| R4 | `build.py --preset windows-x64-debug --test` (full suite) | all pass, 0 warnings | 53 / 53, 0 warning lines, 17 × `lesson.<id>.exercises_verify` Passed (the 4 earlier lessons + the 13 new ones) | Pass |
| R5 | `build.py --preset linux-x64-debug --test` (WSL) | same | 53 / 53, 0 warning lines, 17 × `exercises_verify` Passed | Pass |
| R6 | `py -3 .agent/scripts/lint_docs.py` | exit 0 | 0 errors, 0 warnings (final run below) | Pass |
| R7 | browser (Claude in Chrome) against `tools/playground.py --port 8790` | AC-7 | see AC-7 | Pass |
| R8 | exercises whose answers state a compiler or tool result, run once on both compilers (`trybuild`: apply, build, run, read the messages) | the statement is true | `const_return_int`: MSVC builds, Clang `-Wignored-qualifiers` fails. `ranges_to_msvc`: MSVC builds both the pipe form and `{}` of a vector; Clang + libstdc++ 14 fails both (`forward_like` error of KI-033; no `formatter<vector<string>>`). `parse_invalid_date`: MSVC `parse ok: true`, value read as 2026-03-02 09:00; libstdc++ `parse ok: false`. `raw_file_time`: Windows `134390815734162577`, Linux `-4643055954753375900`. `copy_recursive`: `remove_all removed 6` → `10`. `import_a`: MSVC builds, Clang `missing '#include'; 'to_string' must be declared before it is used`. `quick_exit`: the first run prints steps 3–5, the second `nothing to recover`. `no_mapped_dir`: steps 3–5 never appear, the second run `nothing to recover`. `relaxed_tsan` (`linux-x64-tsan`): `WARNING: ThreadSanitizer: data race` between `tryPop` (main.cpp:133) and `tryPush` (main.cpp:106) on the ring's heap block, exit code 66, output still `all cases verified: true`. `emergency_state`: with `sleep_for` 250 ms both compilers show `RUN -> EMERGENCY` and `final state: EMERGENCY`; with 120 ms only 3–4 ticks ran on Windows (KI-053). `diagram_backends`: PlantUML `@startuml … @enduml`, D2 `a -> b: label` | Pass; two answers corrected |

## AC-3: automatic exercises solved by their answers
Both columns: `exercises.py check` reported the exercise as passed (`pass (new)`), on the practice copy changed as the answer says.
| Lesson | Exercise | Change made | MSVC | Clang |
|---|---|---|---|---|
| `format_text` | `drop_format_arg` | one `kNumber` removed | pass | pass |
| | `polar_formatter` | `polar` in `parse`/`format`, `<cmath>`, `{:p}` line | pass | pass |
| | `println_a` | three `std::println` | pass | pass |
| | `println_b` | `std::println(bad_pattern, word);` | pass | pass |
| `const_correctness` | `call_increment_on_const` | `c.increment();` uncommented | pass | pass |
| | `get_returns_value` | `auto&` → `auto` | pass | pass |
| `source_location` | `warn_without_loc` | `loc` parameter removed | pass | pass |
| | `type_identity` | `Here<Args...>` | pass | pass |
| | `format_arg_mismatch` | two `logFormat` lines | pass | pass |
| `concepts` | `unconstrained_calls` | `printShape(42)`, `twiceSfinae("x")` | pass | pass |
| | `printable_concept` | concept, `toString`, `static_assert` | pass | pass |
| | `fixed_ring_six` | `FixedRing<6>::kMask` (rerun after the regex fix) | pass | pass |
| `ranges_views` | `drop_take` | `take(2)` removed | pass | pass |
| | `find_on_temporary` | `ranges::find(makeNumbers(), 8)` and `*it` | pass | pass |
| `variant_visit` | `add_triangle` | `Triangle` in the variant | pass | pass |
| `chrono_time` | `seconds_from_ms` | `seconds s = 1500ms;` | pass | pass |
| | `ambiguous_local_time` | the try block for 2026-11-01 01:30 | pass | pass |
| `filesystem_paths` | `copy_recursive` | `fs::copy(…, recursive)` | pass | pass |
| `log_recovery` | `quick_exit` | `std::quick_exit(0)` | pass | pass |
| | `no_mapped_dir` | `.mappedDir` removed | pass | pass |
| `lock_free_buffer` | `small_capacity` | `kCapacity = 8` | pass | pass |
| `span_timing` | `no_reserve` | `// values.reserve(kElements);` | pass | pass |
| | `span_in_hot_loop` | `Tracer&` in `lookUp`, span in the loop (rerun after the regex fix) | pass | pass |
| `modules` | `call_detail` | `detail::clampSide(5.0)` | pass | pass |
| | `import_b` | `export import atugcc.core;`, `main.cpp` import removed | pass | pass |
| `device_state_machine` | `emergency_state` | `tick == 4` branch | pass | pass |
| | `rejected_transition` | `RunState{}` at `tick == 1` | pass | pass |
| | `diagram_backends` | PlantUML and D2 lines | pass | pass |

The 13 observation exercises have no rules: `const_return_int`, `ranges_to_msvc`, `find_state_hpp`, `virtual_perimeter`, `parse_invalid_date`, `unsorted_listing`, `raw_file_time`, `crash_dump_abort`, `relaxed_tsan`, `cached_head`, `debug_build_profile`, `rebuild_scope`, `import_a`. No automatic exercise needs `abort()` (Assumption 9): `crash_dump_abort`, the only one that calls `abort()`, is an observation exercise.

## Reviews
| Unit | Reviewer | Question | Findings | Resolution |
|---|---|---|---|---|
| U1–U4 (13 `exercises.toml`, 4 README edits) | `cpp-reviewer` | `source.has` regexes vs the unchanged source; hint/answer claims vs the source and the other language; KO/EN parity; UB or abort in the text | 10 findings: `span_in_hot_loop` second `has` rule matched 4 original lines; `fixed_ring_six` rule matched a comment; a modules hint offered `[[nodiscard]]` (already present) and a partition remark that was backwards; "build differs" vs the UI label "different build"; `sleep_for(120ms)` written with a literal suffix the lesson does not have; `final state:` is not the last output line; `core::` alias missing in a hint; "same expression" for two different `requires` conditions; a ranges hint question that presupposed the opposite of its answer; `isTransitionAllowed` has a catch-all so "cannot forget a state" is only partly true; hints that printed solving code (Assumption 7) in `polar_formatter`, `printable_concept`, `span_in_hot_loop`, `cached_head`, `emergency_state`, `rejected_transition` | all fixed in one round; the two regexes were rerun on both compilers (pass), the hints were rewritten to say where to look only |

## Acceptance criteria
| AC | Evidence | Verdict |
|---|---|---|
| AC-1 | R1: 13 lessons have `exercises.toml`, `lessons.py check` 0 / 0 (item counts equal, split items counted once) | Pass |
| AC-2 | R4, R5: 17 × `lesson.<id>.exercises_verify` Passed on both presets (13 new); no automatic exercise passes on the unchanged lesson | Pass |
| AC-3 | R2, R3 and the table above: 28 / 28 on both presets; no exercise moved to observation | Pass |
| AC-4 | the solve loop reset the copy after every exercise; `git status` shows only the intended files (the practice copy is git-ignored); the 070-17 tests cover that progress survives a reset | Pass |
| AC-5 | the reviewer's script over all 41 exercises: `title`/`title_en`, `hint`/`hint_en`, `answer`/`answer_en` on every one, `fail_hint`/`fail_hint_en` on exactly the automatic ones; `lessons.py check` has no WARN | Pass |
| AC-6 | `span_timing` exercise 2 and the `device_state_machine` section title changed in both READMEs; the sentence says the practice copy's `lesson.toml` is read-only; section and code-block counts are unchanged | Pass |
| AC-7 | R7: `format_text` (all automatic) and `lambda_capture` (mixed automatic and "스스로 확인") open with the Exercises tab; after the `drop_format_arg` answer was applied to the copy and Run pressed, the row shows `✓ 통과` and the tree changes to `1/4`; the API lists `const_correctness`, `class_basics`, `lock_free_buffer` with `auto` and `self` kinds as defined | Pass |
| AC-8 | R4, R5: 53 / 53 on both presets, 0 warnings; R6 `lint_docs.py` exit 0 | Pass |
