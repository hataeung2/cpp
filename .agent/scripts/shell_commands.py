#!/usr/bin/env python3
"""Split a Bash or PowerShell command line into the simple commands that would run (spec 090-06, KI-008).

Used by .claude/hooks/guard.py through agent_common.py: a command is judged by its program position, so
text that is only data (quoted arguments, heredoc bodies, here-strings, comments) is not mistaken for a
command, while shell strings (`bash -c`, `pwsh -Command`, `cmd /c`, `eval`, `iex`), substitutions and
text fed to a shell are judged inside. Design: docs/tasks/feature_090-06-dev-tools-cleanup/plan.md D1-D3, D1'.
Stdlib only.
"""
from __future__ import annotations

import re

# Ad-hoc CMake configure (rule 2): `cmake -S`, `cmake -B`, `cmake ..`.
ADHOC_CMAKE_RE = re.compile(
    r"\bcmake(?:\.exe)?\s+(?:[^|;&\n]*\s)?(?:-S|-B)\s*\S|\bcmake(?:\.exe)?\s+\.\.(?:\s|$)"
)

GIT_COMMIT_RE = re.compile(r"\bgit\b[^|;&\n]*\scommit\b")

_POSIX_SHELLS = frozenset({"bash", "sh", "zsh", "dash", "ksh"})

_PS_SHELLS = frozenset({"pwsh", "powershell"})

_RESERVED_SKIP_PROGRAM = frozenset({
    "!", "if", "then", "elif", "else", "while", "until", "do", "coproc",
})

_RESERVED_DISCARD_WORDS = frozenset({
    "fi", "done", "esac", "{", "}",
})

_NON_COMMAND_STARTERS = frozenset({
    "for", "select", "case",
})

_GIT_GLOBAL_TWO_ARG = frozenset({
    "-c", "-C", "--git-dir", "--work-tree",
    "--namespace", "--config-env", "--exec-path", "--super-prefix",
    "--attr-source",
})

_RE_DUP = re.compile(r"(\d*)>&(?:\d+|-)")

_RE_HEREDOC = re.compile(r"<<(-)?")

_RE_HERESTRING = re.compile(r"<<<")

_RE_REDIR = re.compile(r"(\d+|\*)?(&>>|&>|>&|<>|>>|>|<)\s*")

_RE_VAR_ASSIGN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")

_RE_NICE_ADJ = re.compile(r"^-n\d+$")

_RE_TIME_OPT = re.compile(r"^-[A-Za-z]*p[A-Za-z]*$")

_RE_PS_HERE_CLOSE = {
    "'": re.compile(r"(\r?\n)'@"),
    '"': re.compile(r'(\r?\n)"@'),
}

# Shell options that take the next word as their value (so it is not the script).
_SH_VALUE_OPTIONS = frozenset({"-o", "+o", "-O", "+O", "--rcfile", "--init-file"})
# PowerShell takes any unambiguous prefix of a parameter name (`-exec bypass`), so full names are
# matched by prefix (3+ characters) and the short aliases exactly.
_PS_VALUE_OPTIONS = frozenset({
    "-executionpolicy", "-workingdirectory", "-configurationname", "-custompipename", "-settingsfile",
    "-windowstyle", "-outputformat", "-inputformat", "-version", "-psconsolefile",
})
_PS_VALUE_ALIASES = frozenset({
    "-ep", "-ex", "-wd", "-config", "-settings", "-w", "-of", "-o", "-if", "-in", "-v",
})
# Nested `env -S "env -S …"` is split at most this many times (each split copies the rest).
_MAX_ENV_SPLITS = 64
_RE_SH_COMMAND_OPT = re.compile(r"^-[A-Za-z]*c[A-Za-z]*$")
_RE_DURATION = re.compile(r"^\d+(?:\.\d+)?[smhd]?$")
_RE_NICE_NUMBER = re.compile(r"^-\d+$")
_SUDO_VALUE_OPTIONS = frozenset({"-u", "-g", "-C", "-D", "-h", "-p", "-r", "-t", "-U"})
_WSL_VALUE_OPTIONS = frozenset({"-d", "--distribution", "-u", "--user", "--cd", "--shell-type"})


def _clean_program(word: str) -> str:
    """Normalize a program name: basename, lowercase, no .exe."""
    base = word.replace("\\", "/").rstrip("/").split("/")[-1].lower()
    return base[:-4] if base.endswith(".exe") else base


def _shell_script(words: list[str]) -> tuple[str, str | None] | None:
    """For a command that starts a shell: (dialect, script).

    `script` is the `-c` / `-Command` text, or None when the shell reads its script from stdin.
    Returns None when `words` do not start a shell or the shell runs a script file. Option values
    (`bash -o pipefail`, `pwsh -ExecutionPolicy Bypass`) are skipped, so they are not taken for a file.
    """
    if not words:
        return None
    prog = _clean_program(words[0])
    i, n = 1, len(words)
    if prog in _POSIX_SHELLS:
        while i < n:
            word = words[i]
            if not word.startswith(("-", "+")) or word == "--":
                return None  # a script file (after `--` too)
            if word in _SH_VALUE_OPTIONS:
                i += 2
                continue
            if _RE_SH_COMMAND_OPT.match(word):
                return "bash", words[i + 1] if i + 1 < n else ""
            i += 1
        return "bash", None
    if prog in _PS_SHELLS:
        while i < n:
            word = words[i]
            lowered = word.lower()
            if not word.startswith("-"):
                # Windows PowerShell 5.1 takes a positional argument as -Command; pwsh as -File.
                return ("powershell", " ".join(words[i:])) if prog == "powershell" else None
            if len(lowered) > 1 and "-command".startswith(lowered):
                script = " ".join(words[i + 1:])
                return "powershell", None if script == "-" else script
            if len(lowered) > 1 and "-file".startswith(lowered):
                return None
            if lowered in _PS_VALUE_ALIASES or (
                    len(lowered) >= 3 and any(name.startswith(lowered) for name in _PS_VALUE_OPTIONS)):
                i += 2
                continue
            i += 1
        return "powershell", None
    return None


def _skip_options(words: list[str], i: int, value_options: frozenset[str]) -> int:
    """Index after the options at words[i:]; options in `value_options` also take the next word."""
    n = len(words)
    while i < n and words[i].startswith("-"):
        if words[i] == "--":
            return i + 1
        i += 2 if words[i] in value_options else 1
    return i


def _strip_wrappers(words: list[str], shell: str) -> list[str]:
    """The words from the program on: wrapper commands, their options and assignments removed.

    Works on an index (no list copies per word), so long prefixes cost linear time.
    """
    i, n, env_splits = 0, len(words), 0
    while i < n:
        word = words[i]
        if shell == "bash" and _RE_VAR_ASSIGN.match(word):
            i += 1
            continue
        if shell == "powershell" and word in ("&", "."):
            i += 1
            continue
        prog = _clean_program(word)
        if shell == "bash" and prog in _RESERVED_SKIP_PROGRAM:
            i += 1
        elif prog == "time":
            i += 1
            if i < n and _RE_TIME_OPT.match(words[i]):
                i += 1
        elif prog in ("nohup", "exec"):
            i = _skip_options(words, i + 1, frozenset({"-a"}))
        elif prog == "command":
            i += 1
            while i < n and words[i] in ("-p", "-v", "-V"):
                i += 1
        elif prog == "sudo":
            i = _skip_options(words, i + 1, _SUDO_VALUE_OPTIONS)
        elif prog == "nice":
            i += 1
            while i < n and words[i].startswith("-"):
                option = words[i]
                if option == "-n":
                    i += 2
                elif (_RE_NICE_ADJ.match(option) or _RE_NICE_NUMBER.match(option)
                      or option.startswith("--adjustment=")):
                    i += 1
                else:
                    break
        elif prog == "env":
            i += 1
            while i < n:
                option = words[i]
                if option.startswith("-S") and env_splits >= _MAX_ENV_SPLITS:
                    break  # pathological nesting: judge the words as they are
                if option.startswith("-S"):
                    env_splits += 1
                if option == "-S":
                    # the value is the command line itself: split it and continue with its words
                    rest = words[i + 2:] if i + 1 < n else []
                    words = (words[i + 1].split() if i + 1 < n else []) + rest
                    i, n = 0, len(words)
                    break
                if option.startswith("-S") and len(option) > 2:
                    words = option[2:].split() + words[i + 1:]
                    i, n = 0, len(words)
                    break
                if option in ("-u", "-C"):
                    i += 2
                elif option in ("-i", "-0", "-v") or option.startswith(("-u", "-C", "--chdir=", "--unset=")):
                    i += 1
                elif "=" in option and not option.startswith("-"):
                    i += 1
                elif option == "--":
                    i += 1
                    break
                else:
                    break
        elif prog == "timeout":
            i += 1
            while i < n and words[i].startswith("-"):
                option = words[i]
                if option in ("-k", "-s", "--kill-after", "--signal"):
                    i += 2
                else:
                    i += 1  # -v, --foreground, --preserve-status, -k5, --signal=KILL
            if i < n and _RE_DURATION.match(words[i]):
                i += 1
        elif prog == "stdbuf":
            i = _skip_options(words, i + 1, frozenset({"-i", "-o", "-e"}))
        elif prog == "wsl":
            i += 1
            while i < n:
                option = words[i]
                if option in _WSL_VALUE_OPTIONS:
                    i += 2
                elif any(option.startswith(o + "=") for o in _WSL_VALUE_OPTIONS):
                    i += 1
                elif option in ("-e", "--exec", "--"):
                    i += 1
                    break
                else:
                    break
        else:
            break
    return words[i:]


def _recurse_execution(words: list[str], shell: str, depth: int) -> list[list[str]] | None:
    """Commands run by a shell string (`bash -c`, `pwsh -Command`, `cmd /c`) or by `eval`."""
    if not words:
        return []
    prog = _clean_program(words[0])
    script: tuple[str, str] | None = None
    shell_run = _shell_script(words)
    if shell_run is not None and shell_run[1] is not None:
        script = (shell_run[0], shell_run[1])
    elif prog == "cmd":
        for i, word in enumerate(words[1:], 1):
            if word.lower() in ("/c", "/k"):
                script = ("powershell", " ".join(words[i + 1:]))  # cmd: double quotes, no \ escapes
                break
    elif prog == "eval":
        script = (shell, " ".join(words[1:]))
    if script is None:
        return []
    return simple_commands(script[1], script[0], depth + 1)


def _recurse_powershell_runner(words: list[str], depth: int) -> list[list[str]] | None:
    """Find commands executed via PowerShell process or expression runners."""
    if not words:
        return []
    prog = _clean_program(words[0])
    if prog in ("iex", "invoke-expression"):
        script: str | None = None
        for i, w in enumerate(words[1:], 1):
            if w.lower() == "-command" and i + 1 < len(words):
                script = words[i + 1]
                break
            if not w.startswith("-") and script is None:
                script = w
        if script:
            return simple_commands(script, "powershell", depth + 1)
        return []
    if prog in ("start-process", "saps", "start"):
        target: str | None = None
        arg_list_words: list[str] = []
        known_opts = frozenset({
            "-credential", "-workingdirectory", "-loaduserprofile", "-nonewwindow",
            "-passthru", "-redirectstandarderror", "-redirectstandardinput",
            "-redirectstandardoutput", "-usenewenvironment", "-wait", "-windowstyle",
            "-verb",
        })
        i = 1
        while i < len(words):
            w = words[i]
            wl = w.lower()
            if wl in ("-filepath", "-path") and i + 1 < len(words):
                target = words[i + 1]
                i += 2
                continue
            if wl in ("-argumentlist", "-args"):
                i += 1
                while i < len(words):
                    next_wl = words[i].lower()
                    if next_wl in known_opts or next_wl in ("-filepath", "-path"):
                        break
                    arg_list_words.append(words[i])
                    i += 1
                continue
            if not w.startswith("-") and target is None:
                target = w
                i += 1
                continue
            i += 1
        if target:
            clean_args: list[str] = []
            if len(arg_list_words) == 1 and (" " in arg_list_words[0] or "\t" in arg_list_words[0]):
                sub = simple_commands(arg_list_words[0], "powershell", depth + 1)
                if sub and sub[0]:
                    clean_args = sub[0]
            else:
                for a in arg_list_words:
                    for part in a.split(","):
                        part = part.strip()
                        if part:
                            clean_args.append(part)
            return [[target] + clean_args]
        return []
    return []


def _shell_dialect(words: list[str]) -> str | None:
    """'bash' or 'powershell' if `words` start a shell that reads its script from stdin, else None."""
    shell_run = _shell_script(_strip_wrappers(words, "bash"))
    return shell_run[0] if shell_run is not None and shell_run[1] is None else None


def _parse_heredoc_delim(text: str, pos: int) -> tuple[str, bool, int] | None:
    """Return (clean_delim, is_quoted, next_pos) or None on syntax error."""
    n = len(text)
    while pos < n and text[pos] in " \t":
        pos += 1
    if pos >= n:
        return None
    delim_chars: list[str] = []
    is_quoted = False
    while pos < n:
        c = text[pos]
        if c in " \t\r\n;&|()<>":
            break
        if c == "\\":
            is_quoted = True
            pos += 1
            if pos < n:
                delim_chars.append(text[pos])
                pos += 1
        elif c in ("'", '"'):
            is_quoted = True
            q = c
            pos += 1
            while pos < n and text[pos] != q:
                delim_chars.append(text[pos])
                pos += 1
            if pos >= n:
                return None
            pos += 1
        else:
            delim_chars.append(c)
            pos += 1
    if not delim_chars:
        return None
    return "".join(delim_chars), is_quoted, pos


def _scan_expanding_body(body: str, shell: str, depth: int) -> list[list[str]] | None:
    """Extract and scan $(...) and backticks inside expanding heredoc bodies or here-strings."""
    pos, n = 0, len(body)
    sub_cmds: list[list[str]] = []
    while pos < n:
        if body[pos : pos + 2] == "$(" or (shell == "powershell" and body[pos : pos + 2] == "@("):
            sub_scan = _CommandScanner(body, pos + 2, shell, depth, stop_char=")")
            res = sub_scan.scan()
            if res is None:
                return None
            sub_cmds.extend(res[0])
            pos = res[1]
        elif shell == "bash" and body[pos] == "`":
            end = pos + 1
            while end < n:
                if body[end] == "\\":
                    end += 2
                elif body[end] == "`":
                    break
                else:
                    end += 1
            if end >= n:
                return None
            sub = simple_commands(body[pos + 1 : end], "bash", depth)
            if sub is None:
                return None
            sub_cmds.extend(sub)
            pos = end + 1
        elif body[pos] == "\\" and shell == "bash":
            pos += 2
        elif body[pos] == "`" and shell == "powershell":
            pos += 2
        else:
            pos += 1
    return sub_cmds


class _CommandScanner:
    """Scan a command line into simple commands, handling quotes, heredocs, and substitutions."""

    def __init__(
        self,
        text: str,
        pos: int = 0,
        shell: str = "bash",
        depth: int = 0,
        stop_char: str | None = None,
    ) -> None:
        self.text = text
        self.pos = pos
        self.shell = "powershell" if shell.lower() == "powershell" else "bash"
        self.depth = depth
        self.stop_char = stop_char
        self.n = len(text)
        self.all_commands: list[list[str]] = []
        self.pipeline_commands: list[list[str]] = []
        self.pipeline_heredocs: list[list[tuple[str, bool, str]]] = []
        self.pipeline_args: list[list[str]] = []
        self.current_words: list[str] = []
        self.pending_heredocs: list[tuple[str, bool, bool, int]] = []
        self.drop_next = False

    def _scan_backtick(self, start: int) -> tuple[str, int] | None:
        i = start
        while i < self.n:
            if self.text[i] == "\\":
                i += 2
            elif self.text[i] == "`":
                return self.text[start:i], i + 1
            else:
                i += 1
        return None

    def _scan_word(self) -> tuple[str, list[list[str]], int] | None:
        pos, n = self.pos, self.n
        text = self.text
        chars: list[str] = []
        sub_cmds: list[list[str]] = []
        esc = "\\" if self.shell == "bash" else "`"

        while pos < n:
            c = text[pos]
            if c in " \t\r\n;&|()<>":
                break
            if c == esc:
                if pos + 1 >= n:
                    chars.append(esc)
                    pos += 1
                    break
                if text[pos + 1] in "\r\n":
                    pos += 3 if text[pos : pos + 3] == esc + "\r\n" else 2
                else:
                    chars.append(text[pos + 1])
                    pos += 2
            elif c == "'" and self.shell == "bash":
                end = text.find("'", pos + 1)
                if end == -1:
                    return None
                chars.append(text[pos + 1 : end])
                pos = end + 1
            elif text[pos : pos + 2] == "$'" and self.shell == "bash":
                pos += 2
                while pos < n and text[pos] != "'":
                    if text[pos] == "\\" and pos + 1 < n:
                        chars.append(text[pos + 1])
                        pos += 2
                    else:
                        chars.append(text[pos])
                        pos += 1
                if pos >= n:
                    return None
                pos += 1
            elif c == "'" and self.shell == "powershell":
                pos += 1
                while pos < n:
                    if text[pos] == "'":
                        if pos + 1 < n and text[pos + 1] == "'":
                            chars.append("'")
                            pos += 2
                        else:
                            pos += 1
                            break
                    else:
                        chars.append(text[pos])
                        pos += 1
                else:
                    return None
            elif c == '"':
                pos += 1
                while pos < n and text[pos] != '"':
                    if text[pos] == esc:
                        if pos + 1 >= n:
                            return None
                        if text[pos + 1] in "\r\n":
                            pos += 3 if text[pos : pos + 3] == esc + "\r\n" else 2
                        elif self.shell == "bash" and text[pos + 1] not in ('"', '\\', '$', '`'):
                            chars.extend(["\\", text[pos + 1]])
                            pos += 2
                        else:
                            chars.append(text[pos + 1])
                            pos += 2
                    elif self.shell == "powershell" and text[pos : pos + 2] == '""':
                        chars.append('"')
                        pos += 2
                    elif text[pos : pos + 2] == "$(" or (
                        self.shell == "powershell" and text[pos : pos + 2] == "@("
                    ):
                        sub_scan = _CommandScanner(
                            text, pos + 2, self.shell, self.depth + 1, stop_char=")"
                        )
                        res = sub_scan.scan()
                        if res is None:
                            return None
                        sub_cmds.extend(res[0])
                        pos = res[1]
                    elif self.shell == "bash" and text[pos] == "`":
                        bt_res = self._scan_backtick(pos + 1)
                        if bt_res is None:
                            return None
                        sub = simple_commands(bt_res[0], "bash", self.depth + 1)
                        if sub is None:
                            return None
                        sub_cmds.extend(sub)
                        pos = bt_res[1]
                    else:
                        chars.append(text[pos])
                        pos += 1
                if pos >= n:
                    return None
                pos += 1
            elif text[pos : pos + 2] == "$(" or (
                self.shell == "powershell" and text[pos : pos + 2] == "@("
            ):
                sub_scan = _CommandScanner(
                    text, pos + 2, self.shell, self.depth + 1, stop_char=")"
                )
                res = sub_scan.scan()
                if res is None:
                    return None
                sub_cmds.extend(res[0])
                pos = res[1]
            elif self.shell == "bash" and c == "`":
                bt_res = self._scan_backtick(pos + 1)
                if bt_res is None:
                    return None
                sub = simple_commands(bt_res[0], "bash", self.depth + 1)
                if sub is None:
                    return None
                sub_cmds.extend(sub)
                pos = bt_res[1]
            else:
                chars.append(c)
                pos += 1

        return "".join(chars), sub_cmds, pos

    def _flush_command(self) -> bool:
        self.drop_next = False
        if not self.current_words:
            return True
        stripped = _strip_wrappers(self.current_words, self.shell)
        if stripped:
            if len(stripped) == 1 and stripped[0] in _RESERVED_DISCARD_WORDS:
                pass
            elif stripped[0] in _NON_COMMAND_STARTERS:
                pass
            else:
                self.pipeline_commands.append(stripped)
                self.pipeline_heredocs.append([])
                self.pipeline_args.append(list(stripped[1:]))
                rec = _recurse_execution(stripped, self.shell, self.depth)
                if rec is None:
                    return False
                self.all_commands.extend(rec)
                if self.shell == "powershell":
                    ps_rec = _recurse_powershell_runner(stripped, self.depth)
                    if ps_rec is None:
                        return False
                    self.all_commands.extend(ps_rec)
        self.current_words = []
        return True

    def _flush_pipeline(self) -> bool:
        if not self.pipeline_commands and not self.pipeline_heredocs:
            return True
        self.all_commands.extend(self.pipeline_commands)
        sh_dialect: str | None = None
        sh_stage_idx = -1
        for k, cmd_words in enumerate(self.pipeline_commands):
            sh = _shell_dialect(cmd_words)
            if sh:
                sh_dialect = sh
                sh_stage_idx = k
                break
        if sh_dialect and sh_stage_idx != -1:
            for j in range(sh_stage_idx):
                if j < len(self.pipeline_heredocs):
                    for delim, is_quoted, body in self.pipeline_heredocs[j]:
                        sub = simple_commands(body, sh_dialect, self.depth + 1)
                        if sub is None:
                            return False
                        self.all_commands.extend(sub)
                if j < len(self.pipeline_args):
                    for arg in self.pipeline_args[j]:
                        sub = simple_commands(arg, sh_dialect, self.depth + 1)
                        if sub is None:
                            return False
                        self.all_commands.extend(sub)
            if sh_stage_idx < len(self.pipeline_heredocs):
                for delim, is_quoted, body in self.pipeline_heredocs[sh_stage_idx]:
                    sub = simple_commands(body, sh_dialect, self.depth + 1)
                    if sub is None:
                        return False
                    self.all_commands.extend(sub)
        else:
            for h_list in self.pipeline_heredocs:
                for delim, is_quoted, body in h_list:
                    if not is_quoted:
                        sub = _scan_expanding_body(body, self.shell, self.depth + 1)
                        if sub is None:
                            return False
                        self.all_commands.extend(sub)
        self.pipeline_commands = []
        self.pipeline_heredocs = []
        self.pipeline_args = []
        return True

    def _read_pending_heredocs(self) -> bool:
        for delim, is_quoted, strip_tabs, stage_idx in self.pending_heredocs:
            body_lines: list[str] = []
            found = False
            while self.pos < self.n:
                nl = self.text.find("\n", self.pos)
                line = self.text[self.pos:] if nl == -1 else self.text[self.pos : nl]
                self.pos = self.n if nl == -1 else nl + 1
                chk = line.rstrip("\r")
                if strip_tabs:
                    chk = chk.lstrip("\t")
                if chk == delim:
                    found = True
                    break
                body_lines.append(line.rstrip("\r"))
            if not found:
                return False
            body = "\n".join(body_lines)
            while len(self.pipeline_heredocs) <= stage_idx:
                self.pipeline_heredocs.append([])
            self.pipeline_heredocs[stage_idx].append((delim, is_quoted, body))
        self.pending_heredocs.clear()
        return True

    def scan(self) -> tuple[list[list[str]], int] | None:
        if self.depth > 8:
            return None
        text, n = self.text, self.n

        while self.pos < n:
            c = text[self.pos]
            if c == "\r":
                if self.pos + 1 < n and text[self.pos + 1] == "\n":
                    self.pos += 1
                c = "\n"
            if c in " \t":
                self.pos += 1
                continue
            if c == "\n":
                if not self._flush_command():
                    return None
                self.pos += 1
                if not self._read_pending_heredocs():
                    return None
                if not self._flush_pipeline():
                    return None
                continue

            esc = "\\" if self.shell == "bash" else "`"
            if text[self.pos : self.pos + 2] in (esc + "\n", esc + "\r"):
                self.pos += 3 if text[self.pos : self.pos + 3] == esc + "\r\n" else 2
                continue
            if self.shell == "powershell" and text[self.pos : self.pos + 2] == "<#":
                close_idx = text.find("#>", self.pos + 2)
                if close_idx == -1:
                    return None
                self.pos = close_idx + 2
                continue
            if c == "#":
                nl = text.find("\n", self.pos)
                self.pos = n if nl == -1 else nl
                continue

            if self.shell == "powershell" and text[self.pos : self.pos + 2] in ("@'", '@"'):
                q = text[self.pos + 1]
                p = self.pos + 2
                if p < n and text[p] == "\r":
                    p += 1
                if p < n and text[p] == "\n":
                    p += 1
                    m = _RE_PS_HERE_CLOSE[q].search(text, p)
                    if not m:
                        return None
                    here_content = text[p : m.start()]
                    self.pos = m.end()
                    if q == '"':
                        sub = _scan_expanding_body(here_content, "powershell", self.depth + 1)
                        if sub is None:
                            return None
                        self.all_commands.extend(sub)
                    if self.drop_next:
                        self.drop_next = False
                    else:
                        self.current_words.append(here_content)
                    continue

            m_dup = _RE_DUP.match(text, self.pos)
            if m_dup:
                if not m_dup.group(1) and self.current_words and self.current_words[-1].isdigit():
                    self.current_words.pop()
                self.pos = m_dup.end()
                continue

            if self.shell == "bash" and _RE_HERESTRING.match(text, self.pos):
                m_hs = _RE_HERESTRING.match(text, self.pos)
                self.pos = m_hs.end()
                while self.pos < n and text[self.pos] in " \t":
                    self.pos += 1
                res = self._scan_word()
                if res is None:
                    return None
                target_word, target_subs, next_pos = res
                self.all_commands.extend(target_subs)
                self.pos = next_pos
                if _shell_dialect(self.current_words) == "bash":
                    sub = simple_commands(target_word, "bash", self.depth + 1)
                    if sub is None:
                        return None
                    self.all_commands.extend(sub)
                continue

            if self.shell == "bash" and _RE_HEREDOC.match(text, self.pos):
                m_hd = _RE_HEREDOC.match(text, self.pos)
                self.pos = m_hd.end()
                strip_tabs = bool(m_hd.group(1))
                delim_res = _parse_heredoc_delim(text, self.pos)
                if delim_res is None:
                    return None
                clean_delim, is_quoted, self.pos = delim_res
                stage_idx = len(self.pipeline_commands)
                self.pending_heredocs.append((clean_delim, is_quoted, strip_tabs, stage_idx))
                continue

            m_red = _RE_REDIR.match(text, self.pos)
            if m_red:
                if (
                    not m_red.group(1)
                    and self.current_words
                    and (self.current_words[-1].isdigit() or self.current_words[-1] == "*")
                ):
                    self.current_words.pop()
                mat = m_red.group(0)
                has_sp = mat.endswith((" ", "\t"))
                self.pos = m_red.end()
                if has_sp:
                    self.drop_next = True
                else:
                    res = self._scan_word()
                    if res is None:
                        return None
                    _, target_subs, self.pos = res
                    self.all_commands.extend(target_subs)
                continue

            if self.stop_char and c == self.stop_char:
                if not self._flush_command():
                    return None
                if not self._flush_pipeline():
                    return None
                self.pos += 1
                return self.all_commands, self.pos

            if text[self.pos : self.pos + 2] == "|&" or c == "|":
                if not self._flush_command():
                    return None
                self.pos += 2 if text[self.pos : self.pos + 2] == "|&" else 1
                continue

            if text[self.pos : self.pos + 2] in (";;", ";&", "&&", "||"):
                if not self._flush_command():
                    return None
                if not self._flush_pipeline():
                    return None
                self.pos += 3 if text[self.pos : self.pos + 3] == ";;&" else 2
                continue

            if c in ";()":
                if not self._flush_command():
                    return None
                if not self._flush_pipeline():
                    return None
                self.pos += 1
                continue

            if c == "&":
                if self.shell == "powershell" and not self.current_words and not self.pipeline_commands:
                    self.current_words.append("&")
                    self.pos += 1
                else:
                    if not self._flush_command():
                        return None
                    if not self._flush_pipeline():
                        return None
                    self.pos += 1
                continue

            if c in "{}" and (self.pos + 1 == n or text[self.pos + 1] in " \t\r\n;&|()"):
                if not self._flush_command():
                    return None
                if not self._flush_pipeline():
                    return None
                self.pos += 1
                continue

            res = self._scan_word()
            if res is None:
                return None
            word, sub_cmds, next_pos = res
            self.all_commands.extend(sub_cmds)
            if next_pos == self.pos:
                self.pos += 1
                continue
            self.pos = next_pos
            if self.drop_next:
                self.drop_next = False
            else:
                self.current_words.append(word)

        if self.pending_heredocs:
            return None
        if self.stop_char:
            return None
        if not self._flush_command():
            return None
        if not self._flush_pipeline():
            return None
        return self.all_commands, self.pos


def simple_commands(command: str, shell: str = "bash", _depth: int = 0) -> list[list[str]] | None:
    """Split command into simple commands starting at programs with wrappers stripped."""
    if _depth > 8:
        return None
    try:
        scanner = _CommandScanner(command, 0, shell, _depth, stop_char=None)
        res = scanner.scan()
        if res is None:
            return None
        return res[0]
    except Exception:  # a scanner bug must not let a command through: the caller falls back to the regex
        return None


def is_adhoc_cmake(command: str, shell: str = "bash") -> bool:
    """True if command runs an ad-hoc cmake configure (-S, -B, ..)."""
    cmds = simple_commands(command, shell)
    if cmds is None:
        return bool(ADHOC_CMAKE_RE.search(command))
    for w in cmds:
        if w and _clean_program(w[0]) == "cmake":
            for a in w[1:]:
                if a in ("-S", "-B", "..") or a.startswith(("-S", "-B")):
                    return True
    return False


def is_git_commit(command: str, shell: str = "bash") -> bool:
    """True if command runs git commit (not just mentioning it in text)."""
    cmds = simple_commands(command, shell)
    if cmds is None:
        return bool(GIT_COMMIT_RE.search(command))
    for w in cmds:
        if w and _clean_program(w[0]) == "git":
            i = 1
            while i < len(w):
                if w[i] in _GIT_GLOBAL_TWO_ARG:
                    i += 2
                elif w[i].startswith("-"):
                    i += 1
                elif w[i] == "commit":
                    return True
                else:
                    break
    return False
