# Plan: 070-03 essentials 트랙 커리큘럼

- Spec: [/docs/specs/070_03_essentials_curriculum.md](/docs/specs/070_03_essentials_curriculum.md) (approved 2026-11-03)
- Branch: `feature/070-03-essentials-curriculum` (from `main` at `40e37e2`)

## Design

### Files
- [MODIFY] `tools/lessons.py`, `tools/test_lessons.py` — two WARNs (§2.5)
- [MOVE] `lessons/tracks/01_essentials/02_thread_and_log` → `11_thread_and_log`, `03_span_timing` → `14_span_timing` (§2.1)
- [NEW] `lessons/tracks/01_essentials/{02_format_text,04_error_expected,05_source_location,12_log_recovery}/` — `lesson.toml`, `main.cpp`, `README.md`, `README.en.md`
- [MODIFY] the 4 existing `main.cpp`, 2 unit headers — English output, bilingual comments
- [NEW] `README.en.md` for the 4 existing lessons and 2 units
- [MODIFY] `lessons/tags.toml`, `lessons/intro.md`, `lessons/intro.en.md`, `lessons/README.md`, `lessons/units/jthread_worker/README.md`
- [NEW] `docs/cpp_evolution/format.md`; [MODIFY] `error_expected.md`, `source_location.md`, `lock_free_logging.md`
- [MODIFY] `docs/tasks/lesson_candidates.md`, `docs/known_issues.md` (KI-001), `docs/specs/010_08_logger_cleanup.md`, `docs/specs/010_09_logger_thread_buffers.md`, `docs/specs/070_10_lesson_search_i18n.md` (History), `docs/tasks/agent_todo.md`

No new CMake: lessons are found by `lessons/CMakeLists.txt` (glob).

### Comment style (spec Assumption 12)
A Korean comment line is followed at once by the English line with the same meaning, same indentation and comment kind:
```cpp
// 값 캡처: 두 counter 는 서로의 count 를 모른다
// By-value capture: the two counters do not know each other's count
```
A comment of several lines (block or `//` run) may instead be a Korean paragraph followed by its English paragraph; the marker `[학습]` becomes `[Learn]` in the English one. Trailing comments (`code;  // 설명`) become a two-line comment above the code line. Check (AC-5): every run of comment lines with Hangul is directly followed by a comment line without Hangul (`comment_pairs.py` in the lead's scratch area; the testrecord keeps its output).

### `lessons.py` (spec §2.5)
- `hangul_literals(text: str) -> list[int]`: 1-based line numbers (sorted, unique) of string or character literals that contain a Hangul syllable (U+AC00–U+D7A3), Jamo (U+1100–U+11FF) or compatibility Jamo (U+3130–U+318F). One forward scan with states: code, `//` comment (to end of line), `/* */` comment, `"…"` (backslash escapes the next character), `'…'` (same), raw string `R"delim(` … `)delim"` (no escapes; `delim` up to 16 characters). An encoding prefix (`u8`, `u`, `U`, `L`) before `"` or `R"` needs no special case (it is code before the quote). A digit separator `1'000` must not open a character literal: `'` right after an alphanumeric character that is part of a number literal (previous char is a hex digit and the token started with a digit) is code. An unterminated literal at the end of the file: the literal's start line is reported if the rest of the file has Hangul. A literal that spans lines (raw string) reports its start line.
- In `check()`: for every lesson `sources` file and unit `files` file that exists (`.cpp`, `.hpp`, `.h`), WARN per reported line: `string literal with Hangul: program output is English (spec 070-10 Assumption 14)`, path = that file, line = the reported line.
- In `check()`: lesson folder or unit folder with `README.md` and no `README.en.md` → WARN at the manifest, line 0: `no README.en.md (English README, spec 070-03)`.
- Python naming follows the file (snake_case).

### New lessons (spec §2.2)
All: `profile` quick (default), no `[run]`, exit 0, English output, comments per the style above, `namespace` aliases at function scope or file scope as in the existing lessons (no `using namespace std`), `[[nodiscard]]` on value-returning helpers, camelCase functions, `kPascalCase` constants. Includes are exactly what is used.

**`02_format_text`** (`format_text`), `uses = ["lib:atugcc/core/logger.hpp"]`, `tags = ["format"]`. Does not include the logger (the `uses` entry shows where the library takes `std::format_string`); README says so.
- `struct Vec2 { double x; double y; };` and `template <> struct std::formatter<Vec2>`: `parse` accepts an optional precision `.N` (one digit) and `}`; anything else throws `std::format_error`. `format` writes `(x, y)` with that precision (default: shortest `{}`).
- `main` prints six numbered sections, each with a heading line `== N. <name> ==`:
  1. positional arguments: `std::format("{0} -> {1} -> {0}", "idle", "run")`
  2. width, fill, alignment: a 3-row table of `name | count | share` with `{:<10}`, `{:>6}`, `{:>7.1%}`-style percent computed as `{:>6.1f}%`
  3. integers and floating point: `255` as `{}`, `{:#x}`, `{:#o}`, `{:012b}`; `3.14159265` as `{:.3f}`, `{:e}`, `{:>12.2f}`
  4. user type: `Vec2{1.5, -2.25}` with `{}` and `{:.1}` (precision through the formatter)
  5. `std::format_to(std::back_inserter(buffer), …)` three times in a loop into one `std::string`, then print the buffer and its size
  6. runtime format string: `std::vformat(pattern, std::make_format_args(...))` with a good pattern, then a bad one (`"{0} {"`) inside `try`, catching `std::format_error` and printing `format_error: <what()>`
- A comment at section 6 says why the compile-time checked `std::format` cannot take a runtime string (`std::format_string` is checked in a consteval constructor).

**`04_error_expected`** (`error_expected`), `uses = ["lib:atugcc/core/error.hpp"]`, `tags = ["error"]`.
- `[[nodiscard]] std::uint16_t parsePortThrowing(std::string_view text)`: `std::stoi(std::string(text), &pos)` (throws `std::invalid_argument` / `std::out_of_range`), then `throw std::out_of_range` when `pos != text.size()` or the value is outside 1..65535.
- `[[nodiscard]] core::Expected<std::uint16_t> parsePort(std::string_view text)`: `std::from_chars` into `int`; `ec != std::errc{}`, leftover characters, empty text, or value outside 1..65535 → `std::unexpected(core::CoreError::InvalidArgument)`.
- `[[nodiscard]] core::Expected<std::string_view> valueOf(std::string_view line, std::string_view key)`: `key=value` → value; another key or no `=` → `InvalidArgument`. The returned view points into `line` (comment: the caller keeps `line` alive).
- `[[nodiscard]] core::Expected<std::uint16_t> requireUnprivileged(std::uint16_t port)`: `< 1024` → `InvalidArgument`.
- `main`:
  1. `== 1. exceptions ==`: for inputs `"8080"`, `"abc"`, `"70000"`, `""`: `try { … } catch (const std::exception& e)` printing `parsePortThrowing("abc") threw: <type> (<what>)` where `<type>` is `invalid_argument` or `out_of_range` (two catch clauses, no `typeid`).
  2. `== 2. std::expected ==`: same inputs through `parsePort`, printing `parsePort("abc") -> error InvalidArgument` (with `core::to_string`) or `-> 8080`. Uses `has_value()` / `*result` / `result.error()`.
  3. `== 3. and_then / transform / or_else ==`: lines `"port=8080"`, `"port=80"`, `"host=example"`, `"port=x"`: `valueOf(line, "port").and_then(parsePort).and_then(requireUnprivileged).transform([](std::uint16_t p) { return std::format("listen on :{}", p); })` printed with `value_or`-free code: `if (r) … else …`. Then one chain with `.or_else([](core::CoreError) -> core::Expected<std::uint16_t> { return 8080; })` showing the default port for `"port=x"`.
- `parsePort` passed to `and_then` by name works because it takes `std::string_view` and returns `Expected<…>`; `requireUnprivileged` likewise.

**`05_source_location`** (`source_location`), `uses = ["lib:atugcc/core/logger.hpp"]`, `tags = ["source_location", "log"]`.
- `[[nodiscard]] std::string shortName(const char* file)`: `std::filesystem::path(file).filename().string()`.
- Section 1 `== 1. macro ==`: `#define LOG_HERE(msg) logAt(__FILE__, __LINE__, __func__, msg)` with `// MACRO:` justification comment (it is the legacy example); `void logAt(const char* file, int line, const char* func, std::string_view msg)` prints `[<short file>:<line> <func>] <msg>`.
- Section 2 `== 2. std::source_location default argument ==`: `void logHere(std::string_view msg, std::source_location loc = std::source_location::current())` prints the same shape (`loc.line()`, `loc.function_name()`). Called from `main` and from a helper `void startEngine()`; the printed line is each call's line.
- Section 3 `== 3. wrapper that forwards the location ==`: `void warn(std::string_view msg, std::source_location loc = std::source_location::current()) { logHere(std::format("warning: {}", msg), loc); }` — the forwarded location is the caller of `warn`. A comment explains: without the parameter, every warning would show the line inside `warn`.
- Section 4 `== 4. variadic: attach the location to the format string ==`: a local copy `template <typename... Args> struct Here { std::format_string<Args...> fmt; std::source_location loc; template <typename S> requires std::convertible_to<const S&, std::string_view> consteval Here(const S& s, std::source_location l = std::source_location::current()) : fmt(s), loc(l) {} };` and `template <typename... Args> void logFormat(Here<std::type_identity_t<Args>...> here, Args&&... args)` printing the location and `std::format(here.fmt, std::forward<Args>(args)...)`. A comment explains why `loc` cannot be the last parameter after `Args&&...` and what `std::type_identity_t` does (keeps `Args` deduced from the arguments only).
- Section 5 `== 5. atugcc::core::Logger does the same ==`: `core::Logger logger{core::Logger::Config{.liveOutput = &std::cout, .enableCrashDump = false}}; logger.log(core::Level::Info, "port {} ready", 8080); logger.flush();` A comment points at `FormatWithLocation` in `logger.hpp`. The Logger prints the full path (README says so).
- Line numbers in output are not hard-coded anywhere (README says "the line of the call").

**`12_log_recovery`** (`log_recovery`), `uses = ["lib:atugcc/core/logger.hpp", "lib:atugcc/core/log_buffer_config.hpp"]`, `tags = ["recovery", "log"]`. Design proven by a throwaway probe on both OSes (2026-11-03, deleted).
- `constexpr std::string_view kMapDir = "log/map";`
- 1 `== 1. map the log buffers (recovers the previous run) ==`: `const auto configured = core::configureLogBuffers({.drainInterval = std::chrono::milliseconds{1000}, .mappedDir = std::filesystem::path{kMapDir}});` On error print `configureLogBuffers failed: <to_string>; continuing without the map` and skip step 2. (The library prints its own `[atugcc] recovered …` line on stderr during this call; README says so.)
- 2 `== 2. lines recovered from the previous run ==`: collect `recovered_*.log` in `kMapDir` (`std::filesystem::directory_iterator` with `std::error_code`; sort by name). None → `nothing to recover (first run?)`. Each: print `file: <filename>`, then up to 20 lines prefixed `  | `, then `(… N more lines)` when cut; close the stream, then `std::filesystem::remove(path, ec)`; on `ec` print `cannot remove <filename>: <ec.message()>`.
- 3 `== 3. this run ==`: `core::Logger logger{core::Logger::Config{.liveOutput = &std::cout, .enableCrashDump = false}};` `step 1 (flushed)`, `step 2 (flushed)` at Info, `logger.flush()`, then `step 3 (not flushed)`, `step 4 (not flushed)`, `step 5 (not flushed)`.
- 4: print `ending with std::_Exit(0): no destructors, no flush, no exit handlers` and `run the lesson again to see steps 3-5 recovered`, `std::cout.flush()`, `std::_Exit(0)`.
- A comment at step 4 explains: `std::quick_exit` and returning from `main` are clean exits for the Logger (it delivers every line and deletes the map file), `_Exit` behaves like SIGKILL for the map.
- No platform `#ifdef`. `<cstdlib>` for `_Exit`.

### Existing lessons (spec §2.3)
- `thread_and_log`: `=== thread_and_log lesson start ===`, `[WorkerFast] tick {}`, `[WorkerSlow] tick {}`, `=== worker result: WorkerFast = {} ticks, WorkerSlow = {} ticks ===`.
- `device_state_machine`: `=== device_state_machine lesson start ===`, `STANDBY transition failed`, `RUN transition failed`, `device state machine finished. final state: {}`, `=== Terminal trace (formatTerminal) ===`, `=== Mermaid diagram (formatDiagram) ===`.
- Every comment in the 4 `main.cpp` and 2 unit headers gets its English line.

### Tags (spec §2.4)
Four tables appended to `lessons/tags.toml` with the aliases of the spec table. Check before writing: no alias of the new tags equals a name of an existing tag (`logger`, `로그` belong to `log`; `복구` is new).

## Units
Order: tool → tool test → move → existing code → tags → new lessons → READMEs → docs.

| Unit | File | Change (what, where, AC) | Check | Risky | Author | Reviewer | Tokens (in / out) | Status |
|---|---|---|---|---|---|---|---|---|
| U1 | `tools/lessons.py` | `hangul_literals()`, two WARNs in `check()` (§2.5; AC-6) | `lessons.py check` on the repo: exactly the 6 README and 10 Hangul-literal WARNs expected | no | agy flash | cpp-reviewer (with U2): code correct; duplicate WARN when one file is listed twice (same as the existing `#include` WARN, not fixed, testrecord) | not recorded | done |
| U2 | `tools/test_lessons.py` | valid tree gets `README.en.md`; AC-6 cases | `test_lessons.py` 71 OK | no | agy flash | cpp-reviewer: 4 tests passed with their rule removed (mutation); review fixes lead (small); re-check: 5/6 fail under mutation, last one replaced with the reviewer's counterexample, checked by the lead's mutant | 151k / 41k | done |
| U3 | `git mv` 2 folders; `lessons/README.md`, specs 010-08, 010-09 | moves, link paths, History lines (Assumption 4; AC-1, AC-10) | `lint_docs.py` 0 errors; index order | no | lead (scripted) | — (lint) | — | done |
| U4 | 4 lesson `main.cpp` | English output, bilingual comments (AC-5) | comment-pair script OK; Hangul literal WARN 0; build both presets | no | lead (small) | cpp-reviewer (with U5): no code change; found `LessonConsoleCodePage` relied on the Korean heading → `check_console_cp.py` expected line changed (spec §2.3 amended); paragraph form vs AC-5 wording → spec/plan amended; one English wording fixed | — | done |
| U5 | `lessons/units/*/*.hpp` | bilingual comments, comment-only (AC-5) | comment-pair script with code comparison against HEAD: OK | no | lead (small) | cpp-reviewer (with U4): none | — | done |
| U6 | `lessons/tags.toml` | 4 tags (§2.4) | `lessons.py check` no tag WARN | no | lead | AC-8 browser search | — | done |
| U7 | `02_format_text/` | lesson (§2.2; AC-2) | build both presets 0 warnings; output | no | agy flash | cpp-reviewer: P2905 wording, parse comment, `{:08b}` fill not visible, spec `{:.1f}` vs plan; lead (small) fixed `make_format_args(42)` (rvalue, P2905) before review and the findings after; re-check resolved | 107k / 36k | done |
| U8 | `04_error_expected/` | lesson (§2.2; AC-2) | same | no | agy flash | cpp-reviewer: trailing characters threw `out_of_range`, 2 English comments, unreachable else, spec `readLine` name; review fixes lead (small); re-check resolved | 133k / 30k | done |
| U9 | `05_source_location/` | lesson (§2.2; AC-2) | same; printed lines = call lines (105, 113, 50, 121, 128, 138) | no | agy flash | cpp-reviewer: false comment "default argument forbidden after a pack" (real reason: a pack that is not last is not deduced), 2 loose comments, `logf` clashes with `::logf`; review fixes lead (small) incl. rename `logFormat`; re-check resolved | 124k / 24k | done |
| U10 | `12_log_recovery/` | lesson (§2.2, §2.6; AC-2, AC-3) | build both presets; three runs on both OSes | yes | agy flash | codex luna (high): flush-triggered drain could take steps 3–5, unread file deleted on open failure; review fixes lead (small) (100 ms wait after flush, open/bad checks, manifest `uses` + `error.hpp`); re-check: file fix resolved, timing narrowed but not synchronization → stated in both READMEs; "Korean and English on one line" not reproduced (lines 82, 149 are Korean-only, English on the next line) | 156k / 35k (review 506k / 11k, re-check 678k / 15k) | done |
| U11 | new lessons' READMEs (8 files) | §2.2 content (AC-4) | `readme_pairs.py` OK; lint | no | lead | cpp-reviewer (with U12): see testrecord | — | done |
| U12 | 6 `README.en.md`, `jthread_worker/README.md` fix, `intro.en.md` links | §2.3, Assumptions 10–11 (AC-4) | same | no | lead | cpp-reviewer (with U11): see testrecord | — | done |
| U13 | `format.md` [NEW], 3 evolution pages, `lesson_candidates.md`, `known_issues.md`, `lessons/README.md`, 070-10 and 090-06 History, `agent_todo.md` | spec §8 (AC-10) | `lint_docs.py` exit 0 | no | lead | cpp-reviewer (with U11) | — | done |

## Verification (spec §12)
- `py -3 tools/test_lessons.py`, `py -3 tools/lessons.py check` (ERROR 0, WARN 0)
- `py -3 .agent/scripts/build.py --preset windows-x64-debug --test`, `--preset linux-x64-debug --test`
- AC-5: run every lesson on both presets, scan output for Hangul; comment-pair script over the 8 `main.cpp` and 2 headers
- AC-3: `log_recovery` three runs in an empty folder, both OSes
- `npm --prefix web/frontend run build`, `npm --prefix web/frontend test`
- Browser (AC-8): screenshots in `screenshots/`
- `py -3 .agent/scripts/lint_docs.py`
