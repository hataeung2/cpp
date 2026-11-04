# Plan: 070-14 essentials modules 레슨과 `format_text`의 `std::print` 단계

- Spec: [/docs/specs/070_14_essentials_modules_lesson.md](/docs/specs/070_14_essentials_modules_lesson.md) (approved 2026-11-04)
- Branch: `feature/070-14-essentials-modules-lesson` (from `main` at `2436654`)

## Model assignment (user decision 2026-11-04, this task)
The user asked to spend the agy quota before Claude Code tokens: agy `flash` writes code, test and tool units; agy `opus` writes the doc units (the lead's usual share) and reviews flash's units (cross-family: Gemini author, Claude reviewer); agy `argon` reviews opus's doc units and gives the extra review where one is needed. `cpp-reviewer` and codex are fallbacks only. The lead keeps what [delegation.md](/.agent/rules/delegation.md) §7 never delegates (units, checks, states, commits) and one-line changes (`lead (small)`).

## Design

### Files
- [MODIFY] `lessons/CMakeLists.txt` (`.cppm` → `FILE_SET CXX_MODULES`)
- [NEW] `lessons/tracks/01_essentials/15_modules/` — `lesson.toml`, `main.cpp`, `geometry.cppm`, `geometry_rect.cppm`, `geometry.cpp`, `README.md`, `README.en.md`
- [MODIFY] `lessons/tracks/01_essentials/02_format_text/` — `main.cpp` (step 7), `lesson.toml` (summary), `README.md`, `README.en.md`
- [MODIFY] `tools/lessons.py`, `tools/test_lessons.py`
- [MODIFY] `web/server/files.py`, `web/server/test_server.py`, `web/frontend/src/editor.ts`
- [MODIFY] `lessons/tags.toml`, `lessons/README.md`, `docs/tasks/lesson_candidates.md`, `docs/cpp_evolution/modules.md`, `docs/cpp_evolution/format.md`, `.agent/rules/impl.md`, `web/README.md` (if it lists editable suffixes), `docs/known_issues.md` (KI-033; KI-039 already registered with the spec), `docs/tasks/agent_todo.md`

### Lesson `modules` (spec §2.2)
Common rules as 070-11/070-12: header block, English output, Korean comment line followed by its English line, camelCase functions, `kPascalCase` constants, no `using namespace` at file scope, exact includes, no platform `#ifdef`, exit 0, headings `== N. <name> ==`.
- `geometry_rect.cppm`: `module;` `#include <format>` `#include <string>` `export module modules.geometry:rect;` `export namespace modules::geometry { struct Rect { double width{0.0}; double height{0.0}; }; [[nodiscard]] inline std::string describe(const Rect& r) { return std::format("Rect {} x {}", r.width, r.height); } }`.
- `geometry.cppm`: no global module fragment. `export module modules.geometry;` `export import :rect;` `import atugcc.core;`. `#define GEOMETRY_UNIT_CM 1` with the comment that a module never exports macros. Exported: `[[nodiscard]] double area(const Rect&);` `[[nodiscard]] atugcc::core::Expected<Rect> makeRect(double width, double height);`. Not exported: `namespace modules::geometry::detail { [[nodiscard]] double clampSide(double side); }`.
- `geometry.cpp`: `module;` `#include <expected>` `module modules.geometry;` (the fragment was added at the first Clang build: `std::unexpected` is not visible through `import atugcc.core;`, which exports no standard library names; MSVC had accepted it). `kMaxSide = 1000.0`; `clampSide` returns `side > kMaxSide ? kMaxSide : side`; `area` = width × height; `makeRect`: `width <= 0.0 || height <= 0.0` → `std::unexpected(atugcc::core::CoreError::InvalidArgument)`, else `Rect{clampSide(width), clampSide(height)}`.
- `main.cpp`: `#include <format>` `#include <iostream>` first, then `import modules.geometry;` `import atugcc.core;` (comment: includes before imports, impl.md §2a). Library names are written qualified (`atugcc::core::CoreError`, `atugcc::core::to_string`) so exercise 3's error is certain. Output:
  ```
  == 1. import a module ==
  makeRect(3, 4) -> area = 12 (area is defined in geometry.cpp, an implementation unit)
  == 2. partition re-exported ==
  describe(rect) -> Rect 3 x 4 (describe lives in the partition :rect)
  == 3. macros do not cross import ==
  GEOMETRY_UNIT_CM is not defined in main.cpp
  == 4. import atugcc.core ==
  makeRect(-1, 2) -> error: <atugcc::core::to_string(CoreError::InvalidArgument)>
  main.cpp imports atugcc.core itself: geometry's import is not re-exported
  ```
  Step 1 handles a failed `makeRect(3, 4)` (prints the error, exit 1) rather than dereferencing blindly.

### `format_text` step 7 (spec §2.4)
After step 6: `#include <print>`; `== 7. std::print / std::println (C++23) ==`; `std::println("{}", formatRow(kRows[0]));` then `std::cout << formatRow(kRows[0]) << '\n';` (identical lines); `std::println("println: {:.1}", point);` `std::print(stdout, "print to stdout: {} items\n", kRows.size());`. Comments: `std::print` takes `std::format_string` (compile-time check), order with `std::cout` holds because `std::cout` is synchronized with C stdio by default, Windows console output goes through the Unicode console API (P2093; a pipe gets the bytes).

### Tools (spec §2.3)
`lessons.py`: `CPP_SUFFIXES` + `.cppm`; `MODULE_SUFFIXES_REJECTED = (".ixx", ".mpp", ".cxxm")`; `uses` kind `mod:` resolved under `modules/` (same path rules as `lib:`); `ref_files` → `modules/<name>`; new checks per spec §2.3 (ERROR: entry `.cppm`, unit `.cppm`, rejected suffix, missing `mod:` path; WARN: module name without the `<id>` prefix, `import atugcc.<area>;` without `mod:atugcc/<area>.cppm` in the transitive uses). Regexes: module declaration `^[ \t]*(?:export[ \t]+)?module[ \t]+([A-Za-z_][\w.]*)(?::[A-Za-z_][\w.]*)?[ \t]*;` (`module;` has no name and does not match), import `^[ \t]*(?:export[ \t]+)?import[ \t]+(atugcc\.[\w.]+)[ \t]*;`.

## Units
| Unit | File | Change (what, where, AC) | Check | Risky | Author | Reviewer | Tokens (in / out) | Status |
|---|---|---|---|---|---|---|---|---|
| U1 | `lessons/CMakeLists.txt` | split `.cppm` sources into a `CXX_MODULES` file set (§2.3; AC-3) | configure + build both presets with U2 | no | lead (small) | agy opus (with U2): none | — | done |
| U2 | `15_modules/{lesson.toml,main.cpp,geometry.cppm,geometry_rect.cppm,geometry.cpp}` | lesson code (§2.2; AC-2, AC-3, AC-5) | build both presets 0 warnings; output diff between OSes; `grep -c '#include "atugcc'` = 0 | no | agy flash | first Clang build: `std::unexpected` not visible → `<expected>` fragment, lead (small); agy opus: exercise 3a builds on MSVC → user decision (Clang only, spec History); optional comment → lead (small) | 121k / 27k (review 130k / 24k) | done |
| U3 | `02_format_text/main.cpp`, `lesson.toml` | step 7 (§2.4; AC-8) | build both presets; step 7 lines equal | no | agy flash | codex luna: none (agy opus out of quota) | 91k / 15k | done |
| U4 | `tools/lessons.py` | `.cppm`, `mod:`, checks, index (§2.3; AC-1, AC-6) | `lessons.py check` 0/0; `index` shows `modules/atugcc/core.cppm` | no | agy flash | lead: unit self-coverage key → restored folder name, lead (small); codex luna: none | 147k / 49k (review 227k / 1k with U3, U5) | done |
| U5 | `tools/test_lessons.py` | one test per new rule (AC-6) | `py -3 tools/test_lessons.py` | no | agy flash | codex luna: none | 134k / 30k | done |
| U6 | `web/server/files.py`, `web/server/test_server.py`, `web/frontend/src/editor.ts` | `.cppm` new files and highlighting (§2.3; AC-7) | `PlaygroundServer`, `npm test` | no | lead (small) | agy opus (with U2): none | — | done |
| U7 | `15_modules/README.md`, `README.en.md`, `02_format_text/README.md`, `README.en.md` | lesson text (§2.2, §2.4; AC-8, AC-9) | README pair counts; lint | no | agy argon (agy opus out of quota) | codex luna: none; lead: exercise 2 rebuild list (AC-4) fixed, lead (small) | 260k / 29k | done |
| U8 | `lessons/README.md`, `lesson_candidates.md`, `modules.md`, `format.md`, `impl.md`, `web/README.md`, `known_issues.md` (+ `tags.toml` by lead) | §8 (AC-11) | `lint_docs.py` 0 | no | agy opus | codex luna: none; lead: `README.en.md` links, stale numbering sentence, lead (small) | 106k / 15k | done |
| U9 | `agent_todo.md` | states | lint | no | lead | — | — | |

## Verification (spec §12)
See spec §12; evidence goes to `testrecord.md`.
