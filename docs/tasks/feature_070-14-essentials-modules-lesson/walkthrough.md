# Walkthrough: 070-14 essentials modules 레슨과 `format_text`의 `std::print` 단계

- Spec: [/docs/specs/070_14_essentials_modules_lesson.md](/docs/specs/070_14_essentials_modules_lesson.md)
- Plan: [plan.md](/docs/tasks/feature_070-14-essentials-modules-lesson/plan.md)
- Test record: [testrecord.md](/docs/tasks/feature_070-14-essentials-modules-lesson/testrecord.md) — all AC-1 – AC-11 pass

## Result
- Lessons can list `.cppm` module interface and partition files in `sources`: `lessons/CMakeLists.txt` puts them into the lesson's `CXX_MODULES` file set; implementation units stay ordinary sources; the first source stays a `.cpp`.
- `tools/lessons.py`: `uses` kind `mod:` (→ `modules/`), `.cppm` in the Hangul-literal and include checks, ERROR for a `.cppm` entry point, a `.cppm` in a unit, `.ixx`/`.mpp`/`.cxxm`, a missing `mod:` file; WARN for a module name without the lesson-id prefix and for `import atugcc.<area>;` without `mod:`. 8 new tests.
- Web: new `.cppm` files can be created under `lessons/`; Monaco colours `.cppm` as C++.
- New lesson `15_modules` (`modules`, tag `modules`): primary interface `geometry.cppm`, partition `geometry_rect.cppm` (`:rect`, re-exported), implementation unit `geometry.cpp`, `main.cpp` using `import modules.geometry;` and `import atugcc.core;`. Four output steps, identical on both hosts; three exercises, whose behaviour was checked on both compilers.
- `format_text` step 7: `std::println` / `std::print(stdout, …)`; exercise 3 no longer depends on the toolchain. KI-033 keeps only the libstdc++ 15 items.

## Decisions during DEV
- `geometry.cpp` has a global module fragment with `#include <expected>`: Clang 20 does not give `std::unexpected` through `import atugcc.core;` (correct), MSVC 19.51 accepted it.
- Exercise 3a (remove `import atugcc.core;` from `main.cpp`) fails on Clang but builds on MSVC 19.51, which lets names of a non-exported import reach importers (non-conforming). User decision 2026-11-04: keep the exercise, check it on Clang (spec Assumption 11, AC-5, History).

## Agents
User decision for this task: agy before Claude Code tokens. agy flash wrote U2–U5 and ran the AC-7 browser check; agy opus wrote U8 and reviewed U1/U2/U6, then hit its quota (HTTP 429); agy argon wrote U7; codex luna reviewed U3–U5 and U7/U8. No `lead (fallback)` unit. Lead (small) changes are listed in the plan's unit table.

## Follow-ups
- KI-039 (new with the spec): lesson units cannot hold modules.
- KI-033: range formatting, pipe `ranges::to`, `std::forward_like` wait for libstdc++ 15.
- KI-036 (`import std`), KI-037 (editor support), KI-038 (installed module from a consumer project) unchanged.
