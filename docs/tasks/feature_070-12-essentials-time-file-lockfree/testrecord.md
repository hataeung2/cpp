# Test record: 070-12 essentials 3차 레슨 — 시간·파일·동시성

- Spec: [/docs/specs/070_12_essentials_time_file_lockfree.md](/docs/specs/070_12_essentials_time_file_lockfree.md)
- Plan: [plan.md](/docs/tasks/feature_070-12-essentials-time-file-lockfree/plan.md)
- Hosts: Windows 11, MSVC (VS 2026); WSL Ubuntu 24.04, Clang 20.1.2 + libstdc++ 14.2, CMake 4

## Scripts (lead's scratch area, not committed)
`comment_pairs.py`, `readme_pairs.py`, `hangul_out.py` as in [070-11](/docs/tasks/feature_070-11-essentials-syntax/testrecord.md). `ac9.mjs`: the 070-11 browser script plus a Run step (select the lesson, read the status line, click Run, wait for `all cases verified`, read the table from the Output panel). AC-5's `relaxed` copy: `sed` turns every `memory_order_release` / `memory_order_acquire` of `lock_free_buffer/main.cpp` into `memory_order_relaxed` (6 replacements) in the scratch area, built with `clang++-20 -std=gnu++23 -g -O1 -fsanitize=thread` and run under `setarch -R`.

## Runs
| # | Command | Expected | Actual | Status |
|---|---|---|---|---|
| R1 | `build.py --preset {windows-x64-debug,linux-x64-debug} --target lesson_<id>` ×3 (agy output) | 0 warnings | Clang: 3 builds clean. MSVC: `filesystem_paths` C2039 `to_sys` is not a member of `std::filesystem::_File_time_clock`; `lock_free_buffer` C4324 (structure padded due to alignment specifier) | Fail → R2 |
| R2 | after lead (small) fixes (no `to_sys`; explicit-filler index layout) | 0 warnings | 6 builds clean | Pass |
| R3 | run the 3 lessons on both hosts, `diff --strip-trailing-cr` | AC-3 | `chrono_time`: only `elapsed (rounded) = …ms` and `TimeStamp::str()` differ; `filesystem_paths`: only `preferred_separator`; no `fs_sandbox` left; `lock_free_buffer`: 5 rows `ok` on both | Pass |
| R4 | `relaxed` copy under TSan (AC-5) | data race reported | exit 66, 6 × `WARNING: ThreadSanitizer: data race`, `SUMMARY: … data race relaxed.cpp:133 in SpscRing<Item, 1024, true>::tryPop` (slot read vs the slot write in `tryPush`); repeated after the U4 layout fix with the same result | Pass |
| R5 | after the review fixes: rebuild and rerun the 3 lessons on both hosts | unchanged output | unchanged (same allowed differences); comment pairs OK | Pass |
| R6 | final gate, machine otherwise idle: `build.py --preset windows-x64-debug --test`, `linux-x64-debug --test`, `linux-x64-tsan --test` | 0 warnings, all pass | 28/28, 28/28 (`PlaygroundServer` passed), 28/28; no `ThreadSanitizer` line in the TSan log; `lesson.lock_free_buffer` 1.5 s on each | Pass |
| R7 | `build.py --preset linux-x64-playground-release`, run `lesson_lock_free_buffer` | AC-4 | 0 warnings; 5 rows `ok`, `all cases verified: true` | Pass |
| R8 | `comment_pairs.py` on the 3 `main.cpp`; `hangul_out.py` on the 6 captured outputs + Release run | OK | OK; OK | Pass |
| R9 | `readme_pairs.py` on the 3 lesson folders | OK | 3 pairs OK | Pass |
| R10 | `py -3 tools/lessons.py check`; `py -3 tools/test_lessons.py` | 0/0; pass | 0 errors, 0 warnings (15 lessons); 71 tests OK | Pass |
| R11 | `npm --prefix web/frontend test` | pass | 7 files, 63 tests | Pass |
| R12 | `py -3 tools/lessons.py index --out <scratch>` | AC-1 order | see AC-1 | Pass |
| R13 | `node ac9.mjs` against `tools/playground.py --port 18782` | AC-9 | all OK; screenshots in [`screenshots/`](/docs/tasks/feature_070-12-essentials-time-file-lockfree/screenshots/) | Pass |
| R14 | `naming_check.py`, `lint_docs.py` | exit 0 | 0 snake_case names; 0 errors, 0 warnings | Pass |

### Throughput (not an AC, spec Assumption 13)
| Run | mutex 1:1 | SPSC 1:1 | SPSC false sharing | mutex 4:1 | SPSC per producer 4:1 |
|---|---|---|---|---|---|
| Linux Debug (R5) | 3.1 M/s | 12.8 M/s | 12.1 M/s | 1.7 M/s | 13.2 M/s |
| Linux Release (R7) | 5.2 M/s | 118 M/s | 139 M/s | 2.8 M/s | 30 M/s |
| Web Release (R13) | 4.3 M/s | 54 M/s | 31 M/s | 2.8 M/s | 73 M/s |

The false-sharing row is sometimes faster than the padded row: this ring reads the other side's index on every push and pop, so that line moves between cores either way. Both READMEs now say so and point at exercise 2 (a cached copy of the other index).

## AC evidence
| AC | Criterion | Evidence | Result |
|---|---|---|---|
| AC-1 | essentials order with the 3 new lessons in their slots | R12: `…, variant_visit, chrono_time, filesystem_paths, thread_and_log, log_recovery, lock_free_buffer, span_timing` | Pass |
| AC-2 | 0 warnings on both presets, smoke tests pass (`lock_free_buffer` labelled `long`), every §2.2 step in the output | R2, R6 (lesson tests 15/15 on both), R3 (5 sections for `chrono_time` and `filesystem_paths`, the 5-row table) | Pass |
| AC-3 | `chrono_time` same on both OSes except the two "now" lines and the ms value; `filesystem_paths` same except `preferred_separator`, sandbox gone | R3, R5 | Pass |
| AC-4 | 5 rows, all `ok`, on both Debug presets and `linux-x64-playground-release` | R3, R7 | Pass |
| AC-5 | no TSan report on `linux-x64-tsan`; the `relaxed` copy reports a data race | R6 (`lesson.lock_free_buffer` passed, no report), R4 | Pass |
| AC-6 | `README.en.md` for all three, same structure, English links; one translation review | R9; cpp-reviewer doc review: translation none | Pass |
| AC-7 | no Hangul in output; Korean comment line → English line | R8 | Pass |
| AC-8 | `lessons.py check` 0/0 | R10 | Pass |
| AC-9 | searches `zoned_time`, `directory_iterator`, `memory_order`, `시간대`, `링 버퍼` find the new lessons; web Run of `lock_free_buffer` is a Release build with the table; English READMEs | R13: each query → its lesson (`Lessons 1`); status before Run `long · run 120s · Release(RelWithDebInfo) build`, 5 rows `ok`, `all cases verified: true`; 3 English `h1`, no notice; screenshots `ac9-search.png`, `ac9-english-chrono_time.png`, `ac9-run-lock_free_buffer.png` | Pass |
| AC-10 | full suite on both presets; frontend; `test_lessons.py` | R6, R11, R10 | Pass |
| AC-11 | §8 documents updated, `lint_docs.py` exit 0 | R14; walkthrough | Pass |

## Reviews
| Unit | Reviewer | Question | Findings | Resolution |
|---|---|---|---|---|
| U2 `chrono_time` | cpp-reviewer | no `%Z`/`operator<<`, catch order, parse only a valid string, KO/EN comments, includes | 4 comment slips (`choose::earliest` described as resolving an ambiguity; parse "in reverse"; hh_mm_ss "nanoseconds"; header line dropped "fixed instant"); advisories: `round` ties go to even, `<string>` missing | lead (small), README step 1 too; re-check: resolved |
| U3 `filesystem_paths` | cpp-reviewer | binary mode and close, generic paths, sorting, no messages, Expected chain, cleanup, comments | none; notes: unchecked writes, comment placement | lead (small): writes checked; re-check: `good()` before the close misses close-time failures → `close()` then `fail()`, failure path uses the `error_code` `remove_all` (the reviewer's fix) |
| U4 `lock_free_buffer` (risky) | codex luna (high) | memory ordering, full/empty, shared data and lifetimes, stop order, per-producer rings, cache-line layout | `PlainIndex` not guaranteed to share one cache line (object only 8-byte aligned) | lead (small): `Indices<Padded>` explicit 64-byte layouts; re-check (resume): resolved |
| U5–U7 docs | cpp-reviewer | translation (AC-6), README claims vs code, `filesystem.md`, other diffs | translation none; README quote `t + 1` vs code `tail + 1`; `ensurePrepared` body is in `memory_dump.cpp`; "implementation-defined" epoch is "unspecified"; `filesystem.md`: `string()` does not convert separators, not all `error_code` overloads are `noexcept`; `lock_free_logging.md` wording | lead (small): all fixed |

## Notes
- Two compiler facts found while building, now in the spec History and `filesystem.md`: MSVC's `file_clock` has `to_utc` but no `to_sys` (the standard allows either pair; `clock_cast` works with both), and MSVC `/W4` warns C4324 when `alignas` makes the compiler pad a struct (the lesson fills the spare bytes itself).
- `locate_zone` failing for a missing time zone database was not exercised (both hosts have one); the handler is reviewed code only.
