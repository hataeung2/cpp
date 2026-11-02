# Walkthrough: 090-06 개발 도구 정비 (KI-008, KI-011, KI-012)

Spec: [/docs/specs/090_06_dev_tools_cleanup.md](/docs/specs/090_06_dev_tools_cleanup.md). Evidence: [testrecord.md](testrecord.md). Units: [plan.md](plan.md).

## Result
- **Guard hook (KI-008)**: commands are judged by what would run. The new [`shell_commands.py`](/.agent/scripts/shell_commands.py) splits a Bash or PowerShell command line into simple commands at the program position, judges shell strings (`bash -c`, `pwsh -Command`, `cmd /c`, `eval`, `iex`), substitutions, heredocs and text fed to a shell, and skips wrappers (`sudo`, `env`, `timeout`, `wsl --exec` …). Text that is only data (quoted arguments, heredoc bodies, here-strings, comments, commit messages) passes. A command it cannot split falls back to the old regex (deny-leaning). The commit-on-main check uses the same splitting. Before: 7 of 13 sample commands wrongly refused and 1 missed; now the table of 98 commands (21 allowed, 61 configure runs, 10 commits, 3 commit messages, 3 unsplittable) passes and the live hook refuses a real configure while allowing a heredoc that mentions one.
- **`build.py --gtest-filter` (KI-012)**: runs through `ctest -R ^AllTests$ --verbose` with `GTEST_FILTER`, so the CMake launcher (`setarch -R`) and `TSAN_OPTIONS` apply. On `linux-x64-tsan` the filtered run now passes instead of exiting 66 without output; a filter with `%`, `"` or a line break is refused.
- **Lesson console (KI-011)**: the KI's premise was wrong (the example already set UTF-8); the lesson executables did not. Every `lesson_<id>` links [`console_utf8.cpp`](/lessons/support/console_utf8.cpp): on a console stdout it switches the output code page to UTF-8 and restores it at normal exit, ordered by `#pragma init_seg(lib)` so later static destructors still print UTF-8. `LessonConsoleCodePage` proves it in a hidden cp949 console, including reading the lesson's Korean line back from the screen.

## Things learned
- `chcp` without arguments does not show the output code page a program changed; the first test driver could not see a missing restore (mutant M3 survived). The test reads `GetConsoleOutputCP()` from a child in the same console instead.
- `>CON` opens the console write-only, so `GetConsoleMode` fails on it; programs in a hidden console get proper handles by inheriting them (no std handles passed to `subprocess.run`).
- `ReadConsoleOutputCharacterW` returns a wide character once for its two cells; rows cut by width drift. The test searches the unsplit buffer.
- The first scanner draft passed its table but regressed compound commands (`for … do cmake …`) against the old regex; reviewing with concrete adversarial strings found it. Three review rounds shaped the final scanner (testrecord Reviews).

## Follow-ups
- KI-031: `enableWindowsAnsi()` (example) changes the console code pages and never restores them.
- KI-032: lessons print ANSI colour codes raw on a console host without VT processing.
- Accepted limits of the guard are listed in spec §6 (names built at run time, `find -exec`/`xargs`/`ssh`, `-EncodedCommand`, a pipe continued on the next line, …); a new KI if one is seen in use.

## Fallbacks
- No `lead (fallback)` unit. Review fixes by the lead (small) in U1b and U3c, and the scanner move (lead, scripted), are recorded in the plan's unit table.
