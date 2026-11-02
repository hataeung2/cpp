# Plan: 090-06 개발 도구 정비 (KI-008, KI-011, KI-012)

- Spec: [/docs/specs/090_06_dev_tools_cleanup.md](/docs/specs/090_06_dev_tools_cleanup.md) (approved 2026-11-02)
- Branch: `feature/090-06-dev-tools-cleanup` (from `main` at `189296f`)
- Order (spec §11): U1 guard (tests first, failing rows confirmed on the current code) → U2 build.py → U3 lesson console (screen-buffer read tried first) → docs.

## Files
- [MODIFY] `.agent/scripts/agent_common.py` — `simple_commands`, `is_adhoc_cmake(command, shell)`, `is_git_commit(command, shell)`
- [MODIFY] `.claude/hooks/guard.py` — dialect from the tool name; `GIT_COMMIT_RE` removed; docstring
- [MODIFY] `.agent/scripts/build.py` — `--gtest-filter` through ctest + `GTEST_FILTER`; filter check
- [MODIFY] `.agent/scripts/test_agent_scripts.py` — AC-1–3 table, build steps / batch / filter tests
- [NEW] `lessons/support/console_utf8.cpp`; [MODIFY] `lessons/CMakeLists.txt` — OBJECT library `atugcc_lesson_console`
- [NEW] `tests/console/console_cp_probe.cpp`, `tests/console/check_console_cp.py`; [MODIFY] `tests/CMakeLists.txt` — `LessonConsoleCodePage` (Windows)
- Docs: spec §8

No C++20/23 feature replaces an older pattern here; no `docs/cpp_evolution/` page (spec §3).

## Design decisions

### D1 `simple_commands(command, shell="bash")` (spec Assumptions 1–4, 6)
Returns a list of simple commands, each a list of unquoted words **starting at the program** (wrappers already stripped), including commands found inside substitutions, shell strings and heredocs fed to a shell. `None` when the text cannot be split.
- Words split on unquoted space / tab. Separators (end a simple command): newline, `;`, `&`, `&&`, `|`, `||`, `|&`, `(`, `)`, and `{` / `}` as whole words. `#` at the start of a word starts a comment to the end of the line (PowerShell also `<# … #>`).
- Redirections are dropped with their target word: `>`, `>>`, `<`, `>&`, `&>`, `<<<` (bash: target is data), an all-digit word or `*` right before `>`/`<` (`2>`, `*>`). `2>&1` is one redirection.
- **bash**: `\x` outside quotes → `x`, `\`+newline = continuation; `'…'` literal; `$'…'` with `\'`; `"…"` with `\` escaping `"` `\` `$` `` ` ``; `$(…)` (nested, quotes inside) and `` `…` `` (outside or inside `"…"`) → the content is split recursively and its commands are added. Heredoc `<<WORD`, `<<-WORD`, `<<'WORD'`, `<<"WORD"`: the body is the lines after the current line up to a line equal to `WORD` (`<<-`: leading tabs stripped first); it is not words. If the command's program is a shell (D2) without a script argument, the body is split recursively (bash rules for sh-family, PowerShell rules for pwsh); otherwise it is data.
- **powershell**: `` `x `` → `x` (outside and inside `"…"`), `` ` ``+newline = continuation; `\` is an ordinary character; `'…'` with `''` → `'`; `"…"` with `""` → `"`; `$(…)` and `@(…)` (outside or inside `"…"`) → recursive; here-strings `@'`⏎…⏎`'@` and `@"`⏎…⏎`"@` are one data word; `&` at the start of a command is the call operator (a wrapper word), elsewhere a separator.
- Unterminated quote, substitution or heredoc, or recursion deeper than 8 → `None`.

### D2 Wrappers and execution strings
- Program = basename of the first word after wrappers, lower-cased, directory (`/` or `\`) and `.exe` removed.
- Stripped from the front, repeatedly: `NAME=value` (bash), `sudo`, `env` (with `-i`, `-u X`, `--`, and assignments after it), `time`, `nice` (`-n X`), `nohup`, `exec`, `command`, `&` (PowerShell), `wsl`/`wsl.exe` with `-d X`, `--distribution X`, `-u X`, `--user X`, `--cd X`, `--shell-type X`, `-e`, `--exec`, `--`.
- Recursed into (their commands are added to the result; the shell command itself is kept too):
  - `bash`, `sh`, `zsh`, `dash`, `ksh` with a word matching `-[A-Za-z]*c[A-Za-z]*` (`-c`, `-lc`, `-ec`): the next word, bash rules;
  - `pwsh`, `powershell` with a word `w` where `w.lower()` starts with `-c` and `"-command".startswith(w.lower())`: the remaining words joined by spaces, PowerShell rules;
  - `cmd` with `/c` or `/k` (any case, after other `/x` switches): the remaining words joined by spaces, PowerShell rules (no `\` escapes, double quotes);
  - `eval`: the remaining words joined by spaces, same rules.

### D3 Predicates
- `is_adhoc_cmake(command, shell="bash")`: `simple_commands` is `None` → `ADHOC_CMAKE_RE.search(command)` (spec Assumption 3). Otherwise true when a command's program is `cmake` and one of its arguments is `-S`, `-B`, starts with `-S`/`-B` (attached value), or is `..`.
- `is_git_commit(command, shell="bash")`: `None` → the old `GIT_COMMIT_RE` (moved from `guard.py`). Otherwise true when the program is `git` and the first argument that is not a global option is `commit`. Global options: words starting with `-`; `-c`, `-C`, `--git-dir`, `--work-tree`, `--namespace`, `--config-env`, `--exec-path`, `--super-prefix` without `=` also take the next word.
- `guard.decide`: `shell = "powershell" if tool == "PowerShell" else "bash"`; `check_command(command, shell)`.

### D1' Revision after the U1b review (cpp-reviewer, 2026-11-02)
The first U1b draft passed the table but missed compound commands (a regression against the old regex), mishandled several redirection and substitution forms, and denied the usual `git commit -m "$(cat <<'EOF' … EOF)"` idiom. The second round implements:
- **R1 One scanner.** The end of `$(…)` / `@(…)` is found by running the same command scanner on the text after `(` until the matching unquoted `)` (so quotes, comments and heredocs inside a substitution are handled exactly as outside). No separate paren counter. Backticks likewise end at the first unescaped `` ` `` and their content is scanned.
- **R2 Reserved words (bash).** At the program position, skip `!`, `if`, `then`, `elif`, `else`, `while`, `until`, `do`, `coproc`, `time` (with `-p`), and drop the words `fi`, `done`, `esac`, `{`, `}` when they stand alone. A simple command whose program is `for`, `select` or `case` is not a command (its words are names and values, `for x in a b`); `case` patterns end at `)`, which is already a separator.
- **R3 Redirections.** Match `&>`, `&>>`, `>&`, `<>` before `&`, `>` and `<`; compiled regexes used with `.match(text, pos)` (no `text[i:]` copies). The target word is scanned like any word: substitutions in it are judged; only its text is dropped. The word after `<<<` too.
- **R4 Expanding bodies.** An unquoted-delimiter heredoc body (bash) and an `@"…"@` here-string (PowerShell) are data, but `$(…)` and backticks (bash) / `$(…)` (PowerShell) inside them are scanned and judged. A quoted delimiter (`<<'X'`, `<<"X"`, `<<\X`, `<<X"Y"`: any quoting in the delimiter word) and `@'…'@` are not expanded. The delimiter is the delimiter word with quotes removed.
- **R5 Text fed to a shell.** A heredoc or `<<<` word whose command is a shell without a script argument (only options before it; `bash -s` counts) is scanned as a script. In a pipeline, when a later stage is such a shell, the heredoc bodies and the string arguments of the earlier stages are scanned as scripts of that shell.
- **R6 Shell script argument.** For `bash`/`sh`/… only options before the first non-option word count: `bash tool.sh -c "…"` runs `tool.sh`, the `-c` is its argument.
- **R7 Wrappers with options.** `sudo` (options; `-u -g -C -D -h -p -r -t -U` take a value), `time -p`, `nice` (`-N`, `-n N`, `--adjustment=N`), `env` (`-i -0 -v`, `-u X`, `-C X`, `--chdir=X`, `-S X`, assignments), `timeout` (options, `-k X`, `-s X`, then the duration), `stdbuf` (`-i/-o/-e` with attached or separate value), `nohup`, `exec` (`-a X`, `-c`, `-l`), `command` (`-p`). PowerShell: `.` (dot-source) like `&`.
- **R8 PowerShell string and process runners.** `iex` / `Invoke-Expression` (`-Command X` or the first argument): scanned as PowerShell. `Start-Process` / `saps` / `start`: the program is `-FilePath X` or the first positional argument; `-ArgumentList` values (one string split by PowerShell rules, or a comma list) are its arguments.
- **R9 git.** `--attr-source` takes a value, like `-c`, `-C`, `--git-dir` …
- **R10 Style.** One statement per line, as in the rest of `agent_common.py`; no line over 110 characters; shell-name sets as module constants (`_POSIX_SHELLS`, `_PS_SHELLS`); the scanner as a small private class with named methods instead of one 120-line function with a closure; helper names that say what they return. Restore the `machine_paths` docstring that the first draft shortened.
- Accepted, not handled (spec §6 gets them): names built at run time (`x=cmake; $x -B o`, `$(echo cmake) -B o`); `{` as a later word (`echo { cmake -B o }`) is treated as a separator.

### D4 build.py (spec Assumptions 7–9)
- A step becomes `(argv, env)` with `env: dict[str, str]` (empty for every step except the filter run). `build_steps(preset, mode, target, test, gtest_filter)` loses `exe_suffix`; `TEST_EXE` stays only in the `--gtest-filter` help text if still used there.
- Filter step: `(["ctest", "--preset", p, "-R", "^AllTests$", "--verbose"], {"GTEST_FILTER": f})`.
- `run()`: `subprocess.run(argv, cwd=root, env={**os.environ, **env} if env else None)`. `batch_script()`: for each `K=V` a line `set "K=V"` before the command line. Printed `+` lines show `GTEST_FILTER=<f> ctest …` (dry run too).
- `bad_filter(f) -> str | None`: reason when `f` has `%`, `"`, `\r` or `\n`. `main()` checks it right after parsing, before picking the preset (so before the WSL hand-off): print `error: …`, return 2.

### D5 Lesson console (spec Assumptions 10–12)
- `lessons/support/console_utf8.cpp` as in spec §2.2. Constructor: `HANDLE out = GetStdHandle(STD_OUTPUT_HANDLE)`; continue only if `out` is valid, `GetFileType(out) == FILE_TYPE_CHAR` and `GetConsoleMode(out, &mode)` succeeds; `UINT cp = GetConsoleOutputCP()`; if `cp != 0 && cp != CP_UTF8 && SetConsoleOutputCP(CP_UTF8)` then `previous_ = cp`. Destructor: `if (previous_ != 0) SetConsoleOutputCP(previous_)`. The comment says why `init_seg(lib)` (order across TUs is unspecified) and that abnormal termination does not restore.
- `lessons/CMakeLists.txt`: `add_library(atugcc_lesson_console OBJECT support/console_utf8.cpp)` before the loop; it needs the project warning flags, so it links `atugcc_headers` (the INTERFACE target that carries `/W4 /utf-8` and warnings-as-errors) — checked against the root `CMakeLists.txt` before writing; every `lesson_<id>` links it.
- Probe `tests/console/console_cp_probe.cpp` (`console_cp_probe <out-file>`): links `atugcc_lesson_console`; a file-scope object in the probe's TU whose destructor appends `dtor=<GetConsoleOutputCP()>`; `main` writes `run=<GetConsoleOutputCP()>` and also prints `한글 × µs ⏱` to stdout.
- Driver `tests/console/check_console_cp.py --probe <exe> --lesson <exe>`: (1) hidden console (`CREATE_NO_WINDOW`), `chcp 949 >nul & <probe> <f> & <python> -I <driver> --report-cp <after>`: expect `run=65001`, `dtor=65001`, after `949`; (2) the probe with stdout to a pipe inside the same kind of console: expect `run=949` and after `949`; (3) `chcp 949 >nul & <lesson> & <python> -I <driver> --read-screen <f> & … --report-cp <after>`: the reader (attached to the same console) reads the screen buffer with `ReadConsoleOutputCharacterW` and writes it as UTF-8; expect the line `=== 터미널 추적 결과 (formatTerminal) ===`. The driver prints each observed value and exits 1 on any mismatch. If the hidden console has no screen buffer to read (the step U3a tries first), stop and report (spec AC-9).
- `tests/CMakeLists.txt`: inside `if(WIN32 AND ATUGCC_BUILD_LESSONS AND Python3_Interpreter_FOUND)`, `add_executable(console_cp_probe …)` linking `atugcc_lesson_console`, and `add_test(NAME LessonConsoleCodePage COMMAND ${Python3_EXECUTABLE} … --probe $<TARGET_FILE:console_cp_probe> --lesson $<TARGET_FILE:lesson_device_state_machine>)`. The root adds `tests/` before `lessons/`, so `if(TARGET …)` cannot be used there; link items and `$<TARGET_FILE:…>` resolve at generate time, after both directories.
- Changed while implementing (U3c): no `>CON` (it opens the console write-only, so `GetConsoleMode` fails and the lesson does not switch) — the programs inherit the hidden console's handles because no std handles are passed; the after-exit value comes from a child calling `GetConsoleOutputCP()` (`chcp` without arguments did not reveal mutant M3); the screen is searched unsplit (a wide character fills two cells but is read back once, so rows cut by width drift).
- U3a result (2026-11-02, scratch): a reader attached to a hidden cp949 console reads the screen buffer (120×9001) with `ReadConsoleOutputCharacterW` on `CONOUT$`; UTF-8 bytes printed at 949 read back as `=== ?곕???異붿쟻 寃곌낵 횞 쨉s ??===`, at 65001 as `=== 터미널 추적 결과 × µs ⏱ ===`. Cells after the text can hold `\x00`: strip them.

## Units

| Unit | File | Change (what, where, AC) | Check | Risky | Author | Reviewer | Tokens (in / out) | Status |
|---|---|---|---|---|---|---|---|---|
| U1a | `.agent/scripts/test_agent_scripts.py` | AC-1–3 table tests (Bash and PowerShell), before the code; review cases added before round 2 | the new rows fail on the current code | no | lead (small) | cpp-reviewer (with U1b) | — | done: 17 guard-level failures on the old code; 46 review rows failing on round 1 |
| U1b | `.agent/scripts/agent_common.py`, `.agent/scripts/shell_commands.py` (new), `.claude/hooks/guard.py` | D1–D3, D1' (AC-1–3) | `test_agent_scripts.py` passes; mutants M1, M2 fail it | no | agy flash (2 rounds); move to `shell_commands.py` lead (scripted); review fixes lead (small) | cpp-reviewer: round 1 13 classes → D1'; re-review 5 → lead fixed; lead-diff check 2 → lead fixed (testrecord Reviews) | round 1 338k / 141k; round 2 592k / 256k | done: 58/58, M1 33, M2 16 failing subtests |
| U2 | `.agent/scripts/build.py`, `.agent/scripts/test_agent_scripts.py` | D4 (AC-5–7) | unit tests; `--dry-run` on a Windows and a Linux preset; AC-5, AC-6 runs | no | lead (small); review fixes lead (small) | cpp-reviewer (with U4): batch `^` lost, help text → fixed | — | done (testrecord R14–R19, R27, R28, R30) |
| U3a | scratch only | try the screen-buffer read in a hidden console (AC-9 premise) | reader sees text printed by a child | no | lead | — | — | done: readable at 65001, mojibake at 949 |
| U3b | `lessons/support/console_utf8.cpp`, `lessons/CMakeLists.txt` | D5 object library (AC-8, AC-9) | builds 0 warnings on `windows-x64-debug` and `linux-x64-debug`; lessons link it | yes | agy flash | codex luna (high): none | agy 110k / 13k; codex 240k / 6k | done |
| U3c | `tests/console/console_cp_probe.cpp`, `tests/console/check_console_cp.py`, `tests/CMakeLists.txt` | D5 probe, driver, CTest (AC-8, AC-9) | `ctest -R LessonConsoleCodePage` passes; mutants M3–M5 | no | agy flash; review fixes lead (small) | cpp-reviewer: robustness, doc drift, names → lead fixed; re-review: Python 3.10 gate → fixed | agy 449k / 125k | done: M3 survived the first driver (`chcp`), killed after the change; M4, M5 killed |
| U4 | spec §8 documents | docs (AC-10) | `lint_docs.py` exit 0 | no | lead | cpp-reviewer (with U2): 8 statements → fixed | — | done |

## Verification (spec §12)
- AC-1–3: `test_agent_scripts.py`; M1 (old regex instead of `simple_commands`), M2 (no recursion into shell strings).
- AC-4: live tool calls in this session after U1b.
- AC-5–7: commands and unit tests; failing-test mutant for AC-5.
- AC-8, AC-9: `LessonConsoleCodePage`; M3 (no restore), M4 (no `init_seg(lib)`), M5 (no set).
- AC-10: `build.py --test` on `windows-x64-debug`, `linux-x64-debug`, `linux-x64-tsan`; `test_agent_scripts.py`; `lint_docs.py`; `naming_check.py`.
