# Test record: 070-11 essentials 2차 레슨 — 문법

- Spec: [/docs/specs/070_11_essentials_syntax_lessons.md](/docs/specs/070_11_essentials_syntax_lessons.md)
- Plan: [plan.md](/docs/tasks/feature_070-11-essentials-syntax/plan.md)
- Hosts: Windows 11, MSVC (VS 2026); WSL Ubuntu 24.04, Clang 20.1.2 + libstdc++ 14.2, CMake 4

## Scripts (lead's scratch area, not committed)
- `comment_pairs.py`: every run of comment lines with Hangul is followed at once by a comment line without Hangul; trailing Korean comments after code are reported. Negative check: the 070-03 base version of `lambda_capture.hpp` (Korean-only comments) gives 3+ problems.
- `readme_pairs.py`: `README.md` and `README.en.md` have the same counts of headings, exercise items, code blocks and tables; English links to READMEs with an English version point at `README.en.md`.
- `hangul_out.py`: no Hangul in captured stdout+stderr.
- `ac8.mjs`: `playwright-core` 1.48.2 driving the installed Edge headless against `py -3 tools/playground.py --port 18781`, English page language set by an init script. It clicks the four new lessons, checks the README panel (`h1` without Hangul, no `.readme-notice`), types six queries and takes two screenshots. It never edits or saves a file.

## Runs
| # | Command | Expected | Actual | Status |
|---|---|---|---|---|
| R1 | `build.py --preset {windows-x64-debug,linux-x64-debug} --target lesson_<id>` ×4 (after U2–U5) | 0 warnings | 0 warnings, 8 builds | Pass |
| R2 | run the 4 lessons on both hosts, `diff --strip-trailing-cr` | same output; §2.2 steps | identical on both hosts; outputs below (AC-2–AC-4) | Pass |
| R3 | `build.py --preset windows-x64-debug --test` (before review fixes) | all pass | 25/25 | Pass |
| R4 | `build.py --preset linux-x64-debug --test` (before review fixes) | all pass | 24/25: `PlaygroundServer` `test_span_flood_keeps_memory_flat` longest pause 0.54 s > 0.5 s while the lead built lesson targets on the same machine. Known flake under host load (KI-020); this task changes no server code | Fail → R6 |
| R5 | `lesson_concepts` without `static_cast<void>(x)` on both presets (U3 review) | 0 warnings | 0 warnings | Pass |
| R6 | final gate, machine otherwise idle: `build.py --preset windows-x64-debug --test`, `linux-x64-debug --test`, `linux-x64-asan --test` | 0 warnings, all pass | 25/25, 25/25 (`PlaygroundServer` passed), 25/25 (ASan + UBSan, U4 lifetime) | Pass |
| R7 | `build.py --preset linux-x64-playground-release`, run `lesson_const_correctness` | same table as Debug | build 0 warnings; output identical to the Debug output | Pass |
| R8 | `comment_pairs.py` on the 4 `main.cpp` (after all fixes) | OK | OK (4 files) | Pass |
| R9 | `readme_pairs.py` on the 4 lesson folders | OK | 4 pairs OK (5 headings, 3 exercises each) | Pass |
| R10 | `hangul_out.py` on 9 captured outputs (4 lessons × 2 hosts + playground-release) | OK | OK | Pass |
| R11 | `py -3 tools/lessons.py check` | ERROR 0, WARN 0 | 0 / 0; 12 lessons | Pass |
| R12 | `py -3 tools/test_lessons.py` | pass | 71 tests OK | Pass |
| R13 | `npm --prefix web/frontend test` | pass | 7 files, 63 tests passed | Pass |
| R14 | `py -3 tools/lessons.py index --out <scratch>` | AC-1 order | see AC-1 | Pass |
| R15 | `node ac8.mjs` (browser, English page) | AC-8 | all OK; screenshots in [`screenshots/`](/docs/tasks/feature_070-11-essentials-syntax/screenshots/) | Pass |
| R16 | `py -3 .agent/scripts/naming_check.py`, `py -3 .agent/scripts/lint_docs.py` | exit 0 | 0 snake_case names; 0 errors, 0 warnings | Pass |

### Lesson output (Linux; Windows identical)
`const_correctness` step 4 (AC-3):
```text
case                       | copy ctor | copy assign | move ctor | move assign
Tracked a = makeValue()    |         0 |           0 |         0 |           0
Tracked a = makeConst()    |         0 |           0 |         0 |           0
t = makeValue()            |         0 |           0 |         0 |           1
t = makeConst()            |         0 |           1 |         0 |           0
v.push_back(makeValue())   |         0 |           0 |         1 |           0
v.push_back(makeConst())   |         1 |           0 |         0 |           0
```
`concepts` step 3: `describe(-3) -> signed_integral`, `describe(3u) -> integral`, `describe(2.5) -> auto`; step 5: `FixedRing<8>: mask = 7, slot(13) = 5`, `FixedRing<16>: mask = 15, slot(13) = 13`.

`ranges_views` step 3:
```text
pipeline built, nothing ran yet
  transform(eggs)
  transform(apple)
result: eggs, apple
```
Step 4: `ranges::to: 3 names …`, `enumerate: 0 eggs, 1 apple, 2 cheese`, `zip: eggs=200, apple=300, cheese=900`, `chunk(2): [1 2] [3 4] [5 6] [7]`, `slide(2): [1 2] … [6 7]`, `split(','): a | b | c`, `fold_left(…) = 28`; step 5: `dangling: true`, `ref_view: true`, `owning_view: true`, `doubled …: 10 6 16`.

`variant_visit` steps 1–3 print `circle: area 3.14`, `rect: area 6.00` (both ways), perimeters `6.28` / `10.00`; step 4 `index() = 0`, `holds_alternative<Circle> = true`, `get_if<Rect> is null: true`, `index() = 1`, `get_if<Rect>->width = 2.00`, `bad_variant_access caught`; step 5 `sizeof(Circle) = 8`, `sizeof(Rect) = 16`, `sizeof(std::variant<Circle, Rect>) = 24`, `variant >= largest alternative: true`, `sizeof(std::unique_ptr<Shape>) = 8`.

## AC evidence
| AC | Criterion | Evidence | Result |
|---|---|---|---|
| AC-1 | essentials order with the 4 new lessons in their folder slots | R14: `lambda_capture, format_text, const_correctness, error_expected, source_location, concepts, ranges_views, variant_visit, thread_and_log, log_recovery, span_timing` | Pass |
| AC-2 | 0 warnings on both presets, smoke tests pass, every §2.2 step in the output | R1, R6 (`lesson.*` 12/12 on both), R2 (five `== N. … ==` sections each) | Pass |
| AC-3 | `const_correctness` step 4 table as expected on both Debug presets and `linux-x64-playground-release` | R2, R7, table above | Pass |
| AC-4 | `describe` choices; `take(2)` transforms only the first two in stock; `sizeof(variant) >=` largest | R2 output above (24 ≥ 16) | Pass |
| AC-5 | `README.en.md` for all four, same structure, English links; one translation review | R9; `cpp-reviewer` doc review: translation `none` (Reviews) | Pass |
| AC-6 | no Hangul in output; Korean comment line → English line | R10, R8 | Pass |
| AC-7 | `lessons.py check` ERROR 0, WARN 0 | R11 (`mutable` alias moved to the summary, spec History) | Pass |
| AC-8 | searches `std::visit`, `requires`, `views`, `mutable`, `컨셉` find the new lesson; `std::variant` finds `variant_visit` and `device_state_machine`; English READMEs without notice | R15: `std::visit` → variant_visit, device_state_machine; `requires` → concepts; `views` → ranges_views; `mutable` → lambda_capture, const_correctness; `컨셉` → concepts; `std::variant` → variant_visit, device_state_machine; 4 English `h1`, no notice; screenshots `ac8-search-variant.png`, `ac8-english-variant_visit.png` | Pass |
| AC-9 | full suite on both presets; frontend tests; `test_lessons.py` | R6, R13, R12 | Pass |
| AC-10 | §8 documents updated, `lint_docs.py` exit 0 | R16; documents in the walkthrough | Pass |

## Reviews
| Unit | Reviewer | Question | Findings | Resolution |
|---|---|---|---|---|
| U2 `const_correctness` | cpp-reviewer | spec/plan match, step 4 really shows the claim, deducing this, exercise lines, KO/EN comments | `makeConst` comment put the copy inside the function; 3 KO/EN mismatches; spec `get(0) = 5` vs plan `get(1) = 21`; exercise 2 also gives `-Wunused-function` if `makeInt` is not called | lead (small): comments fixed, spec text aligned (History), exercise 2 says "call it once"; re-check: resolved, README reason wording fixed |
| U3 `concepts` | cpp-reviewer | spec/plan match, comment correctness, includes | RingBuffer comment said "same constraint" (it also rejects 1; the `requires` clause is C++20 too); "fast" mask claim; `static_cast<void>(x)` need unconfirmed | lead (small): comments, README, `concepts.md`, plan fixed; cast removed (R5); re-check: resolved, README.en comma splice and `concepts.md` 0/1 wording fixed |
| U4 `ranges_views` (risky) | codex luna (high) | lifetime bugs, dangling use, is AC-4's `take(2)` guaranteed by the code | none | — |
| U5 `variant_visit` | cpp-reviewer | spec/plan match, no `what()`, README exercise 1 claim, KO/EN | area comment above the wrong line; "pattern matching" wording; README `Triangle::area()` only declared | lead (small); re-check: resolved |
| U6–U9 docs | cpp-reviewer | translation (AC-5), README claims vs code, guide, `concepts.md`, KI and candidate rows | translation none; subsumption sentence too strong (a shared base concept also subsumes) in README and `concepts.md`; `concepts.md` called RingBuffer's rule a concept; two guide wording notes; `ranges_views` candidate row read as if 023-05 already links it | lead (small): all fixed; Clang message in `concepts.md` checked on Clang 20 |

## Notes
- KI-020 (`test_span_flood_keeps_memory_flat` under host load) reproduced once in R4 (0.54 s); passed in R6 with the machine idle. No change to KI-020.
- Before review the lead also replaced six copy-pasted table prints in `const_correctness` with `printRow` (column widths with `std::format`) and removed blank lines between sections (other lessons have none), and merged the duplicated name visitor of `variant_visit` into one `nameOf`.
