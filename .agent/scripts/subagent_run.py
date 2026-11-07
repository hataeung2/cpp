#!/usr/bin/env python3
"""Sub-agent runner: call agy or codex through one CLI script, choosing the model per call.

Every prompt starts with SUBAGENT_PREAMBLE, so the sub-agent skips the repository's boot
sequence (090-12), followed by the project rules for the unit kind (RULE_SECTIONS, 090-12-01).
Rules: .agent/rules/delegation.md.

Usage:
    python .agent/scripts/subagent_run.py --model <alias> --kind <kind> --prompt-file <path> [--read-only] [--effort <level>] [--resume <id>] [--files <path> ...] [--timeout <seconds>] [--out <path>]
    python .agent/scripts/subagent_run.py --print-rules <kind>
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

ALIASES: dict[str, tuple[str, str]] = {
    "flash": ("agy", "gemini-3.8-flash-medium"),
    "argon": ("agy", "gemini-4-argon-high"),
    "sonnet": ("agy", "claude-sonnet-5-5-medium"),
    "opus": ("agy", "claude-opus-5-5-high"),
    "luna": ("codex", "gpt-6-luna"),
    "terra": ("codex", "gpt-5.6-terra"),
}

EFFORTS = ("low", "medium", "high", "xhigh")

AGY_PROMPT_LIMIT = 30_000
RESPONSE_CUT = 8_000

SUBAGENT_PREAMBLE = (
    "You are a sub-agent started with this task prompt. "
    "Do not run the repository's boot sequence. "
    "Follow this prompt and the project rules in it."
)

# Project rules attached to every prompt: (repo-relative file, exact heading line).
COMMON_RULES: tuple[tuple[str, str], ...] = (
    (".agent/rules/impl.md", "## Core"),
    (".agent/rules/delegation.md", "### Sub-agent limits"),
)
# Extra sections per unit kind (--kind).
RULE_SECTIONS: dict[str, tuple[tuple[str, str], ...]] = {
    "code": (),
    "test": ((".agent/rules/test.md", "## 2. C++ Testing (GoogleTest)"),),
    "lesson": (("lessons/README.md", "## 레슨 작성 안내"),),
    "review": ((".agent/rules/delegation.md", "### Review checklist"),),
    "research": (),
}
KINDS = tuple(RULE_SECTIONS)

FENCE_RE = re.compile(r"^\s*(```|~~~)")
HEADING_RE = re.compile(r"^(#{1,6}) ")

QUOTA_RE = re.compile(
    r"quota|rate limit|resource_exhausted|\b429\b|usage limit", re.IGNORECASE
)

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_INPUT = 2
EXIT_QUOTA = 3
EXIT_TIMEOUT = 4


class InputError(Exception):
    """Raised when command-line input or prompt validation fails."""


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sub-agent runner: call agy or codex through one CLI script."
    )
    parser.add_argument("--model", default=None, help="Model alias (required unless --print-rules).")
    parser.add_argument(
        "--kind",
        choices=KINDS,
        default=None,
        help="Unit kind: selects the project rules attached to the prompt (required unless --print-rules).",
    )
    parser.add_argument(
        "--print-rules",
        choices=KINDS,
        default=None,
        metavar="KIND",
        help="Print the project rules attached for KIND and exit; no model is called.",
    )
    parser.add_argument("--prompt-file", default=None, help="Path to prompt file (required unless --print-rules).")
    parser.add_argument("--read-only", action="store_true", help="Run read-only.")
    parser.add_argument(
        "--effort",
        choices=EFFORTS,
        default=None,
        help="Reasoning effort (codex only).",
    )
    parser.add_argument("--resume", default=None, help="Conversation or thread ID to resume.")
    parser.add_argument(
        "--files",
        nargs="+",
        default=[],
        help="Context file paths to prepend to the prompt.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=1200,
        help="Timeout in seconds (default: 1200).",
    )
    parser.add_argument("--out", default=None, help="Path to write the full JSON result.")
    return parser.parse_args(argv)


def resolve(alias: str, effort: str | None, read_only: bool) -> tuple[str, str, str | None]:
    if alias not in ALIASES:
        valid_aliases = ", ".join(ALIASES.keys())
        raise InputError(f"unknown model alias {alias!r}; available aliases: {valid_aliases}")
    cli, model_id = ALIASES[alias]
    if cli == "agy":
        if effort is not None:
            raise InputError(f"--effort cannot be used with agy alias {alias!r}")
        return cli, model_id, None
    if cli == "codex":
        if not read_only:
            raise InputError(f"codex alias {alias!r} requires --read-only")
        resolved_effort = effort if effort is not None else "medium"
        return cli, model_id, resolved_effort
    raise InputError(f"unknown CLI {cli!r} for alias {alias!r}")


def extract_section(text: str, heading: str) -> str | None:
    """The section from the line equal to `heading` up to the next heading of the same or a
    higher level. Lines inside code fences are never headings. None when the heading is absent."""
    level = len(heading) - len(heading.lstrip("#"))
    collected: list[str] | None = None
    in_fence = False
    for line in text.splitlines():
        if FENCE_RE.match(line):
            in_fence = not in_fence
        elif not in_fence:
            if collected is None:
                if line.rstrip() == heading:
                    collected = [line.rstrip()]
                continue
            m = HEADING_RE.match(line)
            if m and len(m.group(1)) <= level:
                break
        if collected is not None:
            collected.append(line)
    if collected is None:
        return None
    return "\n".join(collected).strip()


def rule_sections(kind: str) -> tuple[tuple[str, str], ...]:
    if kind not in RULE_SECTIONS:
        raise InputError(f"unknown kind {kind!r}; kinds: {', '.join(KINDS)}")
    return COMMON_RULES + RULE_SECTIONS[kind]


def rule_bundle(kind: str, root: Path = REPO_ROOT) -> str:
    """The `## Project rules (<kind>)` block: each section of rule_sections(kind), in order."""
    parts = [f"## Project rules ({kind})"]
    for rel, heading in rule_sections(kind):
        path = Path(root) / rel
        if not path.is_file():
            raise InputError(f"rule file not found: {rel} (kind {kind})")
        section = extract_section(path.read_text(encoding="utf-8-sig"), heading)
        if section is None:
            raise InputError(f"rule section not found: {rel} {heading!r} (kind {kind})")
        parts.append(section)
    return "\n\n".join(parts)


def strip_preamble(text: str) -> str:
    """Drop a preamble the prompt file already starts with, and the blank lines around it."""
    lines = text.splitlines(keepends=True)
    start = 0
    while start < len(lines) and not lines[start].strip():
        start += 1
    if start == len(lines) or lines[start].strip() != SUBAGENT_PREAMBLE:
        return text
    start += 1
    while start < len(lines) and not lines[start].strip():
        start += 1
    return "".join(lines[start:])


def build_prompt(text: str, files: list[str], rules: str = "") -> str:
    """Prompt sent to the CLI: SUBAGENT_PREAMBLE, the rules block, the context file list, the text."""
    body = strip_preamble(text)
    if files:
        body = "Context files:\n" + "".join(f"- {f}\n" for f in files) + "\n" + body
    head = SUBAGENT_PREAMBLE + "\n\n"
    if rules:
        head += rules + "\n\n"
    return head + body


def load_prompt(path: str, files: list[str], cli: str, kind: str, root: Path = REPO_ROOT) -> str:
    prompt_path = Path(path)
    if not prompt_path.is_file():
        raise InputError(f"prompt file not found: {path}")
    text = prompt_path.read_text(encoding="utf-8")
    if not text.strip():
        raise InputError(f"prompt file is empty: {path}")
    prompt = build_prompt(text, files, rule_bundle(kind, root))
    if cli == "agy" and len(prompt) > AGY_PROMPT_LIMIT:
        raise InputError(
            f"prompt length ({len(prompt)}) exceeds agy limit of {AGY_PROMPT_LIMIT} characters"
        )
    return prompt


def build_command(
    cli: str,
    exe: str,
    model_id: str,
    effort: str | None,
    prompt: str,
    *,
    read_only: bool,
    resume: str | None,
    timeout: int,
    repo_root: Path,
    last_message_file: str,
) -> tuple[list[str], str | None]:
    if cli == "agy":
        argv = [exe]
        if read_only:
            argv.extend(["--mode", "plan"])
        else:
            argv.append("--dangerously-skip-permissions")
        argv.extend([
            "--add-dir",
            str(repo_root),
            "--model",
            model_id,
            "--output-format",
            "json",
            "--print-timeout",
            f"{timeout}s",
        ])
        if resume:
            argv.extend(["--conversation", resume])
        argv.extend(["-p", prompt])
        return argv, None
    if cli == "codex":
        if resume:
            argv = [
                exe,
                "exec",
                "resume",
                "-m",
                model_id,
                "-c",
                f'model_reasoning_effort="{effort}"',
                "-c",
                'sandbox_mode="read-only"',
                "--json",
                "-o",
                last_message_file,
                resume,
                "-",
            ]
        else:
            argv = [
                exe,
                "exec",
                "-m",
                model_id,
                "-c",
                f'model_reasoning_effort="{effort}"',
                "-s",
                "read-only",
                "-C",
                str(repo_root),
                "--json",
                "-o",
                last_message_file,
                "-",
            ]
        return argv, prompt
    raise ValueError(f"unknown cli: {cli!r}")


def empty_usage() -> dict[str, int]:
    return {
        "input": 0,
        "cached_input": 0,
        "output": 0,
        "reasoning": 0,
        "total": 0,
    }


def parse_agy(stdout: str) -> dict:
    def _to_int(val: object) -> int:
        return val if isinstance(val, int) and not isinstance(val, bool) else 0

    last_obj: dict | None = None
    if isinstance(stdout, str):
        for line in reversed(stdout.splitlines()):
            line = line.strip()
            if not line:
                continue
            try:
                parsed = json.loads(line)
                if isinstance(parsed, dict):
                    last_obj = parsed
                    break
            except Exception:
                continue

    if last_obj is None:
        return {
            "status": "ERROR",
            "response": "",
            "error": "no JSON result in agy output",
            "conversation_id": None,
            "duration_seconds": None,
            "usage": empty_usage(),
            "warnings": [],
        }

    raw_status = last_obj.get("status")
    raw_error = last_obj.get("error")
    if isinstance(raw_status, str):
        status = raw_status
    elif raw_error:
        status = "ERROR"
    else:
        status = "SUCCESS"

    if isinstance(raw_error, str):
        error: str | None = raw_error
    elif raw_error is not None:
        error = str(raw_error)
    else:
        error = None

    raw_response = last_obj.get("response")
    response = raw_response if isinstance(raw_response, str) else ""

    raw_cid = last_obj.get("conversation_id")
    conversation_id = str(raw_cid) if raw_cid is not None else None

    raw_dur = last_obj.get("duration_seconds")
    if isinstance(raw_dur, (int, float)) and not isinstance(raw_dur, bool):
        duration_seconds: float | None = float(raw_dur)
    else:
        duration_seconds = None

    raw_usage = last_obj.get("usage")
    if isinstance(raw_usage, dict):
        usage = {
            "input": _to_int(raw_usage.get("input_tokens")),
            "cached_input": _to_int(raw_usage.get("cache_read_tokens")),
            "output": _to_int(raw_usage.get("output_tokens")),
            "reasoning": _to_int(raw_usage.get("thinking_tokens")),
            "total": _to_int(raw_usage.get("total_tokens")),
        }
    else:
        usage = empty_usage()

    raw_warnings = last_obj.get("warnings")
    if isinstance(raw_warnings, list):
        warnings = [str(w) for w in raw_warnings]
    else:
        warnings = []

    return {
        "status": status,
        "response": response,
        "error": error,
        "conversation_id": conversation_id,
        "duration_seconds": duration_seconds,
        "usage": usage,
        "warnings": warnings,
    }


def parse_codex(stdout: str, last_message: str) -> dict:
    def _to_int(val: object) -> int:
        return val if isinstance(val, int) and not isinstance(val, bool) else 0

    conversation_id: str | None = None
    response = ""
    turn_failed_error: str | None = None
    last_top_level_error: str | None = None
    warnings: list[str] = []
    usage = empty_usage()
    turn_completed_seen = False

    if isinstance(stdout, str):
        for line in stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except Exception:
                continue
            if not isinstance(event, dict):
                continue

            event_type = event.get("type")

            if event_type == "thread.started":
                tid = event.get("thread_id")
                if tid is not None:
                    conversation_id = str(tid)
            elif event_type == "item.completed":
                item = event.get("item")
                if isinstance(item, dict):
                    itype = item.get("type")
                    if itype == "agent_message":
                        txt = item.get("text")
                        response = str(txt) if txt is not None else ""
                    elif itype == "error":
                        msg = item.get("message")
                        if msg is not None:
                            warnings.append(str(msg))
            elif event_type == "error":
                msg = event.get("message")
                if msg is None and isinstance(event.get("error"), dict):
                    msg = event["error"].get("message")
                elif msg is None and isinstance(event.get("error"), str):
                    msg = event["error"]
                if msg is not None:
                    msg_str = str(msg)
                    warnings.append(msg_str)
                    last_top_level_error = msg_str
            elif event_type == "turn.failed":
                err_field = event.get("error")
                if isinstance(err_field, dict):
                    sub_msg = err_field.get("message")
                    turn_failed_error = str(sub_msg) if sub_msg is not None else str(err_field)
                elif err_field is not None:
                    turn_failed_error = str(err_field)
                elif event.get("message") is not None:
                    turn_failed_error = str(event["message"])
                else:
                    turn_failed_error = "turn failed"
            elif event_type == "turn.completed":
                turn_completed_seen = True
                raw_usage = event.get("usage")
                if isinstance(raw_usage, dict):
                    inp = _to_int(raw_usage.get("input_tokens"))
                    cached = _to_int(raw_usage.get("cached_input_tokens"))
                    out = _to_int(raw_usage.get("output_tokens"))
                    reasoning = _to_int(raw_usage.get("reasoning_output_tokens"))
                    usage = {
                        "input": inp,
                        "cached_input": cached,
                        "output": out,
                        "reasoning": reasoning,
                        "total": inp + out,
                    }

    if not response.strip() and isinstance(last_message, str) and last_message.strip():
        response = last_message.strip()

    status = "SUCCESS" if (turn_completed_seen and turn_failed_error is None) else "ERROR"

    if turn_failed_error is not None:
        error: str | None = turn_failed_error
    elif not turn_completed_seen:
        error = last_top_level_error
    else:
        error = None

    return {
        "status": status,
        "response": response,
        "error": error,
        "conversation_id": conversation_id,
        "duration_seconds": None,
        "usage": usage,
        "warnings": warnings,
    }


def classify(returncode: int, result: dict, stderr: str) -> int:
    status = result.get("status") if isinstance(result, dict) else None
    if returncode == 0 and status == "SUCCESS":
        return EXIT_OK

    err_text = ""
    if isinstance(result, dict):
        raw_err = result.get("error")
        if isinstance(raw_err, str):
            err_text = raw_err
        elif raw_err is not None:
            err_text = str(raw_err)

    err_combined = f"{err_text}\n{stderr}" if isinstance(stderr, str) else err_text
    if QUOTA_RE.search(err_combined):
        return EXIT_QUOTA
    return EXIT_FAILED


def run(args: argparse.Namespace) -> int:
    if args.print_rules:
        try:
            print(rule_bundle(args.print_rules))
        except InputError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return EXIT_INPUT
        return EXIT_OK
    try:
        required = (("--model", args.model), ("--kind", args.kind), ("--prompt-file", args.prompt_file))
        missing = [flag for flag, value in required if not value]
        if missing:
            raise InputError(f"missing {', '.join(missing)} (or use --print-rules <kind>)")
        cli, model_id, effort = resolve(args.model, args.effort, args.read_only)
        prompt = load_prompt(args.prompt_file, args.files, cli, args.kind)
    except InputError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_INPUT

    exe = shutil.which(cli)
    if exe is None:
        print(f"{cli} not found on PATH", file=sys.stderr)
        return EXIT_FAILED

    if args.out:
        out_path = args.out
    else:
        fd, out_path = tempfile.mkstemp(prefix="subagent_run_", suffix=".json")
        os.close(fd)

    last_message_file: str = ""
    if cli == "codex":
        fd, last_message_file = tempfile.mkstemp(suffix=".txt")
        os.close(fd)

    try:
        argv, stdin_text = build_command(
            cli,
            exe,
            model_id,
            effort,
            prompt,
            read_only=args.read_only,
            resume=args.resume,
            timeout=args.timeout,
            repo_root=REPO_ROOT,
            last_message_file=last_message_file,
        )

        start_time = time.monotonic()
        timed_out = False
        stdout = ""
        stderr = ""
        returncode = 0
        timeout_val: int | float = args.timeout + 30

        try:
            if stdin_text is not None:
                proc = subprocess.run(
                    argv,
                    cwd=REPO_ROOT,
                    input=stdin_text.encode("utf-8"),
                    capture_output=True,
                    timeout=args.timeout + 30,
                )
            else:
                proc = subprocess.run(
                    argv,
                    cwd=REPO_ROOT,
                    stdin=subprocess.DEVNULL,
                    capture_output=True,
                    timeout=args.timeout + 30,
                )
            duration = time.monotonic() - start_time
            returncode = proc.returncode
            stdout = (
                proc.stdout.decode("utf-8", errors="replace")
                if isinstance(proc.stdout, bytes)
                else str(proc.stdout or "")
            )
            stderr = (
                proc.stderr.decode("utf-8", errors="replace")
                if isinstance(proc.stderr, bytes)
                else str(proc.stderr or "")
            )
        except subprocess.TimeoutExpired as exc:
            duration = time.monotonic() - start_time
            timed_out = True
            if exc.timeout is not None:
                timeout_val = exc.timeout
            stdout = (
                exc.stdout.decode("utf-8", errors="replace")
                if isinstance(exc.stdout, bytes)
                else str(exc.stdout or "")
            )
            stderr = (
                exc.stderr.decode("utf-8", errors="replace")
                if isinstance(exc.stderr, bytes)
                else str(exc.stderr or "")
            )

        last_message = ""
        if cli == "codex" and last_message_file and os.path.isfile(last_message_file):
            try:
                with open(last_message_file, "r", encoding="utf-8", errors="replace") as f:
                    last_message = f.read()
            except OSError:
                last_message = ""

        if timed_out:
            t_sec = (
                int(timeout_val)
                if isinstance(timeout_val, (int, float)) and int(timeout_val) == timeout_val
                else timeout_val
            )
            result = {
                "status": "ERROR",
                "response": "",
                "error": f"timeout after {t_sec} s",
                "conversation_id": None,
                "duration_seconds": round(duration, 1),
                "usage": empty_usage(),
                "warnings": [],
            }
            exit_code = EXIT_TIMEOUT
        else:
            if cli == "agy":
                result = parse_agy(stdout)
            elif cli == "codex":
                result = parse_codex(stdout, last_message)
            else:
                raise ValueError(f"unknown cli: {cli!r}")

            if result.get("duration_seconds") is None:
                result["duration_seconds"] = round(duration, 1)

            exit_code = classify(returncode, result, stderr)

        record = {
            **result,
            "alias": args.model,
            "cli": cli,
            "model": model_id,
            "exit_code": exit_code,
        }

        out_path_obj = Path(out_path)
        out_path_obj.parent.mkdir(parents=True, exist_ok=True)
        out_path_obj.write_text(
            json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        print(format_summary(record, out_path))

        if exit_code == EXIT_OK:
            if not (record.get("response") or "").strip():
                print("empty response: check git status before re-delegating")
        else:
            if record.get("error"):
                print(record["error"])
            if stderr:
                print(stderr[-2000:])

        return exit_code
    finally:
        if last_message_file and os.path.exists(last_message_file):
            try:
                os.remove(last_message_file)
            except OSError as err:
                print(f"warning: could not remove {last_message_file}: {err}", file=sys.stderr)


def format_summary(record: dict, out_path: str) -> str:
    status = record.get("status", "")
    alias = record.get("alias", "")
    model_id = record.get("model", "")
    conv_id = record.get("conversation_id")
    dur = record.get("duration_seconds")
    if dur is not None:
        dur_str = f"{dur} s"
    else:
        dur_str = "0 s"

    first_line = f"{status}, model: {alias} ({model_id}), conversation: {conv_id}, duration: {dur_str}"

    usage = record.get("usage")
    if not isinstance(usage, dict):
        usage = empty_usage()
    inp = usage.get("input", 0)
    cached = usage.get("cached_input", 0)
    out = usage.get("output", 0)
    reasoning = usage.get("reasoning", 0)
    total = usage.get("total", 0)
    tokens_line = f"tokens: input {inp} (cached {cached}), output {out}, reasoning {reasoning}, total {total}"

    out_line = f"out: {out_path}"

    lines = [first_line, tokens_line, out_line]

    warnings = record.get("warnings")
    if isinstance(warnings, list):
        for w in warnings:
            lines.append(f"warning: {w}")

    response = record.get("response", "")
    if not isinstance(response, str):
        response = str(response or "")

    lines.append("")
    if len(response) > RESPONSE_CUT:
        lines.append(
            response[:RESPONSE_CUT]
            + f"\n[cut at {RESPONSE_CUT} characters; full text in {out_path}]"
        )
    elif response:
        lines.append(response)

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    return run(parse_args(argv))


if __name__ == "__main__":
    sys.exit(main())
