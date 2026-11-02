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

### D4 build.py (spec Assumptions 7–9)
- A step becomes `(argv, env)` with `env: dict[str, str]` (empty for every step except the filter run). `build_steps(preset, mode, target, test, gtest_filter)` loses `exe_suffix`; `TEST_EXE` stays only in the `--gtest-filter` help text if still used there.
- Filter step: `(["ctest", "--preset", p, "-R", "^AllTests$", "--verbose"], {"GTEST_FILTER": f})`.
- `run()`: `subprocess.run(argv, cwd=root, env={**os.environ, **env} if env else None)`. `batch_script()`: for each `K=V` a line `set "K=V"` before the command line. Printed `+` lines show `GTEST_FILTER=<f> ctest …` (dry run too).
- `bad_filter(f) -> str | None`: reason when `f` has `%`, `"`, `\r` or `\n`. `main()` checks it right after parsing, before picking the preset (so before the WSL hand-off): print `error: …`, return 2.

### D5 Lesson console (spec Assumptions 10–12)
- `lessons/support/console_utf8.cpp` as in spec §2.2. Constructor: `HANDLE out = GetStdHandle(STD_OUTPUT_HANDLE)`; continue only if `out` is valid, `GetFileType(out) == FILE_TYPE_CHAR` and `GetConsoleMode(out, &mode)` succeeds; `UINT cp = GetConsoleOutputCP()`; if `cp != 0 && cp != CP_UTF8 && SetConsoleOutputCP(CP_UTF8)` then `previous_ = cp`. Destructor: `if (previous_ != 0) SetConsoleOutputCP(previous_)`. The comment says why `init_seg(lib)` (order across TUs is unspecified) and that abnormal termination does not restore.
- `lessons/CMakeLists.txt`: `add_library(atugcc_lesson_console OBJECT support/console_utf8.cpp)` before the loop; it needs the project warning flags, so it links `atugcc_headers` (the INTERFACE target that carries `/W4 /utf-8` and warnings-as-errors) — checked against the root `CMakeLists.txt` before writing; every `lesson_<id>` links it.
- Probe `tests/console/console_cp_probe.cpp` (`console_cp_probe <out-file>`): links `atugcc_lesson_console`; a file-scope object in the probe's TU whose destructor appends `dtor=<GetConsoleOutputCP()>`; `main` writes `run=<GetConsoleOutputCP()>` and also prints `한글 × µs ⏱` to stdout.
- Driver `tests/console/check_console_cp.py --probe <exe> --lesson <exe>`: (1) hidden console (`CREATE_NO_WINDOW`), `chcp 949 >nul & <probe> <f> >CON & chcp > <after>`: expect `run=65001`, `dtor=65001`, after `949`; (2) the probe with stdout to a pipe inside the same kind of console: expect `run=949`; (3) `chcp 949 >nul & <lesson> >CON & <python> -I <driver> --read-screen <f>`: the reader (attached to the same console) reads the screen buffer with `ReadConsoleOutputCharacterW` and writes it as UTF-8; expect the line `=== 터미널 추적 결과 (formatTerminal) ===`. The driver prints each observed value and exits 1 on any mismatch. If the hidden console has no screen buffer to read (the step U3a tries first), stop and report (spec AC-9).
- `tests/CMakeLists.txt`: inside `if(WIN32 AND Python3_FOUND)`, `add_executable(console_cp_probe …)` and `add_test(NAME LessonConsoleCodePage COMMAND ${Python3_EXECUTABLE} … --probe $<TARGET_FILE:console_cp_probe> --lesson $<TARGET_FILE:lesson_device_state_machine>)`, when the lesson target exists.

## Units

| Unit | File | Change (what, where, AC) | Check | Risky | Author | Reviewer | Tokens (in / out) | Status |
|---|---|---|---|---|---|---|---|---|
| U1a | `.agent/scripts/test_agent_scripts.py` | AC-1–3 table tests (Bash and PowerShell), before the code | the new rows fail on the current code (7 false positives, 1 miss); old tests pass | no | lead (small) | cpp-reviewer (with U1b) | — | |
| U1b | `.agent/scripts/agent_common.py`, `.claude/hooks/guard.py` | D1–D3 (AC-1–3) | `test_agent_scripts.py` passes; mutants M1, M2 fail it | no | agy flash | cpp-reviewer | | |
| U2 | `.agent/scripts/build.py`, `.agent/scripts/test_agent_scripts.py` | D4 (AC-5–7) | unit tests; `--dry-run` on a Windows and a Linux preset; AC-5, AC-6 runs | no | lead (small) | cpp-reviewer | — | |
| U3a | scratch only | try the screen-buffer read in a hidden console (AC-9 premise) | reader sees text printed by a child | no | lead | — | — | |
| U3b | `lessons/support/console_utf8.cpp`, `lessons/CMakeLists.txt` | D5 object library (AC-8, AC-9) | builds 0 warnings on `windows-x64-debug` and `linux-x64-debug`; lessons link it | yes | agy flash | codex luna (high) | | |
| U3c | `tests/console/console_cp_probe.cpp`, `tests/console/check_console_cp.py`, `tests/CMakeLists.txt` | D5 probe, driver, CTest (AC-8, AC-9) | `ctest -R LessonConsoleCodePage` passes; mutants M3–M5 | no | agy flash | cpp-reviewer | | |
| U4 | spec §8 documents | docs (AC-10) | `lint_docs.py` exit 0 | no | lead | cpp-reviewer | — | |

## Verification (spec §12)
- AC-1–3: `test_agent_scripts.py`; M1 (old regex instead of `simple_commands`), M2 (no recursion into shell strings).
- AC-4: live tool calls in this session after U1b.
- AC-5–7: commands and unit tests; failing-test mutant for AC-5.
- AC-8, AC-9: `LessonConsoleCodePage`; M3 (no restore), M4 (no `init_seg(lib)`), M5 (no set).
- AC-10: `build.py --test` on `windows-x64-debug`, `linux-x64-debug`, `linux-x64-tsan`; `test_agent_scripts.py`; `lint_docs.py`; `naming_check.py`.
