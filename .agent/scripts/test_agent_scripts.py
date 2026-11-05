#!/usr/bin/env python3
"""Self-tests for the agent scripts in .agent/scripts/ and .claude/hooks/guard.py. Stdlib unittest only.

    py -3 .agent/scripts/test_agent_scripts.py      (Windows)
    python3 .agent/scripts/test_agent_scripts.py    (Linux)

SubagentRunTest is copied from the ai_sec project together with subagent_run.py (task 090-01).
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

import agent_common  # noqa: E402
import build  # noqa: E402
import lint_docs  # noqa: E402
import naming_check  # noqa: E402
import subagent_run  # noqa: E402
import test_report  # noqa: E402

sys.path.insert(0, str(SCRIPTS.parents[1] / ".claude" / "hooks"))
import guard  # noqa: E402

# Machine paths are assembled so this file itself passes the rule it tests.
DRIVE = "C" + ":/"
HOME = "/" + "home/dev/"


class SubagentRunTest(unittest.TestCase):
    def assert_flag_value(self, argv: list[str], flag: str, value: str) -> None:
        self.assertIn(flag, argv)
        idx = argv.index(flag)
        self.assertEqual(argv[idx + 1], value)

    def test_resolve_spec_aliases(self) -> None:
        spec_table: dict[str, tuple[str, str]] = {
            "flash": ("agy", "gemini-3.8-flash-medium"),
            "argon": ("agy", "gemini-4-argon-high"),
            "sonnet": ("agy", "claude-sonnet-5-5-medium"),
            "opus": ("agy", "claude-opus-5-5-high"),
            "luna": ("codex", "gpt-6-luna"),
            "terra": ("codex", "gpt-5.6-terra"),
        }
        for alias, (expected_cli, expected_id) in spec_table.items():
            if expected_cli == "agy":
                cli, model_id, effort = subagent_run.resolve(alias, effort=None, read_only=False)
                self.assertEqual(cli, expected_cli)
                self.assertEqual(model_id, expected_id)
                self.assertIsNone(effort)
            else:
                cli, model_id, effort = subagent_run.resolve(alias, effort=None, read_only=True)
                self.assertEqual(cli, expected_cli)
                self.assertEqual(model_id, expected_id)
                self.assertEqual(effort, "medium")
                cli_exp, model_id_exp, effort_exp = subagent_run.resolve(alias, effort="high", read_only=True)
                self.assertEqual(cli_exp, expected_cli)
                self.assertEqual(model_id_exp, expected_id)
                self.assertEqual(effort_exp, "high")

    def test_resolve_input_errors(self) -> None:
        with self.assertRaises(subagent_run.InputError):
            subagent_run.resolve("unknown_alias", effort=None, read_only=False)
        with self.assertRaises(subagent_run.InputError):
            subagent_run.resolve("flash", effort="high", read_only=False)
        with self.assertRaises(subagent_run.InputError):
            subagent_run.resolve("luna", effort=None, read_only=False)

    def test_build_prompt(self) -> None:
        prompt_text = "Implement feature X."
        self.assertEqual(subagent_run.build_prompt(prompt_text, []), prompt_text)

        result = subagent_run.build_prompt(prompt_text, ["a.py", "b.py"])
        self.assertTrue(result.startswith("Context files:\n- a.py\n- b.py\n\n"))
        self.assertEqual(result, f"Context files:\n- a.py\n- b.py\n\n{prompt_text}")

    def test_load_prompt_validation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            missing = tmp / "missing.txt"
            with self.assertRaises(subagent_run.InputError):
                subagent_run.load_prompt(str(missing), [], "agy")

            whitespace_file = tmp / "whitespace.txt"
            whitespace_file.write_text("   \n\t  \n", encoding="utf-8")
            with self.assertRaises(subagent_run.InputError):
                subagent_run.load_prompt(str(whitespace_file), [], "agy")

            long_text = "x" * (subagent_run.AGY_PROMPT_LIMIT + 1)
            long_file = tmp / "long.txt"
            long_file.write_text(long_text, encoding="utf-8")
            with self.assertRaises(subagent_run.InputError):
                subagent_run.load_prompt(str(long_file), [], "agy")

            codex_prompt = subagent_run.load_prompt(str(long_file), [], "codex")
            self.assertEqual(codex_prompt, long_text)

    def test_build_command_agy_edit(self) -> None:
        repo_root = Path("repo")
        exe = "agy"
        model_id = "gemini-3.8-flash-medium"
        prompt = "Write code"
        argv, stdin = subagent_run.build_command(
            "agy",
            exe,
            model_id,
            None,
            prompt,
            read_only=False,
            resume=None,
            timeout=600,
            repo_root=repo_root,
            last_message_file="",
        )
        self.assertEqual(argv[0], exe)
        self.assertIn("--dangerously-skip-permissions", argv)
        self.assertNotIn("--mode", argv)
        self.assert_flag_value(argv, "--model", model_id)
        self.assert_flag_value(argv, "--output-format", "json")
        self.assert_flag_value(argv, "--print-timeout", "600s")
        self.assert_flag_value(argv, "--add-dir", str(repo_root))
        self.assertEqual(argv[-2:], ["-p", prompt])
        self.assertIsNone(stdin)

    def test_build_command_agy_read_only(self) -> None:
        repo_root = Path("repo")
        exe = "agy"
        model_id = "gemini-3.8-flash-medium"
        prompt = "Review code"
        conv_id = "conv-12345"
        argv, stdin = subagent_run.build_command(
            "agy",
            exe,
            model_id,
            None,
            prompt,
            read_only=True,
            resume=conv_id,
            timeout=600,
            repo_root=repo_root,
            last_message_file="",
        )
        self.assert_flag_value(argv, "--mode", "plan")
        self.assertNotIn("--dangerously-skip-permissions", argv)
        self.assert_flag_value(argv, "--conversation", conv_id)
        self.assertIsNone(stdin)

    def test_build_command_codex_new(self) -> None:
        repo_root = Path("repo")
        exe = "codex"
        model_id = "gpt-6-luna"
        prompt = "Check diff"
        effort = "high"
        last_msg = "last_msg.txt"
        argv, stdin = subagent_run.build_command(
            "codex",
            exe,
            model_id,
            effort,
            prompt,
            read_only=True,
            resume=None,
            timeout=600,
            repo_root=repo_root,
            last_message_file=last_msg,
        )
        self.assertEqual(argv[1], "exec")
        self.assert_flag_value(argv, "-m", model_id)
        self.assert_flag_value(argv, "-c", f'model_reasoning_effort="{effort}"')
        self.assert_flag_value(argv, "-s", "read-only")
        self.assert_flag_value(argv, "-C", str(repo_root))
        self.assertIn("--json", argv)
        self.assert_flag_value(argv, "-o", last_msg)
        self.assertEqual(argv[-1], "-")
        self.assertEqual(stdin, prompt)

    def test_build_command_codex_resume(self) -> None:
        repo_root = Path("repo")
        exe = "codex"
        model_id = "gpt-6-luna"
        prompt = "Follow up check"
        effort = "medium"
        last_msg = "last_msg.txt"
        resume_id = "thread-xyz"
        argv, stdin = subagent_run.build_command(
            "codex",
            exe,
            model_id,
            effort,
            prompt,
            read_only=True,
            resume=resume_id,
            timeout=600,
            repo_root=repo_root,
            last_message_file=last_msg,
        )
        self.assertEqual(argv[1:3], ["exec", "resume"])
        self.assertIn('sandbox_mode="read-only"', argv)
        self.assertEqual(argv[argv.index('sandbox_mode="read-only"') - 1], "-c")
        self.assertNotIn("-s", argv)
        self.assertNotIn("-C", argv)
        self.assertEqual(argv[-2], resume_id)
        self.assertEqual(argv[-1], "-")
        self.assertEqual(stdin, prompt)

    def test_parse_agy_success(self) -> None:
        stdout = (
            "plain text info line before json\n"
            + json.dumps({
                "status": "SUCCESS",
                "response": "agy done",
                "conversation_id": "conv-1234",
                "usage": {
                    "input_tokens": 100,
                    "cache_read_tokens": 40,
                    "output_tokens": 50,
                    "thinking_tokens": 20,
                    "total_tokens": 210,
                },
            })
            + "\n"
        )
        res = subagent_run.parse_agy(stdout)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["response"], "agy done")
        self.assertEqual(res["conversation_id"], "conv-1234")
        self.assertEqual(
            res["usage"],
            {
                "input": 100,
                "cached_input": 40,
                "output": 50,
                "reasoning": 20,
                "total": 210,
            },
        )

    def test_parse_agy_no_json(self) -> None:
        stdout = "just some logs\nand another line\n"
        res = subagent_run.parse_agy(stdout)
        self.assertEqual(res["status"], "ERROR")
        self.assertEqual(res["error"], "no JSON result in agy output")

    def test_parse_codex_success(self) -> None:
        lines = [
            json.dumps({"type": "thread.started", "thread_id": "thread-123"}),
            json.dumps({"type": "item.completed", "item": {"type": "error", "message": "warning message"}}),
            json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": "codex response"}}),
            json.dumps({
                "type": "turn.completed",
                "usage": {
                    "input_tokens": 50,
                    "cached_input_tokens": 10,
                    "output_tokens": 25,
                    "reasoning_output_tokens": 5,
                },
            }),
        ]
        res = subagent_run.parse_codex("\n".join(lines), last_message="")
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["conversation_id"], "thread-123")
        self.assertEqual(res["response"], "codex response")
        self.assertEqual(res["warnings"], ["warning message"])
        self.assertEqual(
            res["usage"],
            {
                "input": 50,
                "cached_input": 10,
                "output": 25,
                "reasoning": 5,
                "total": 75,
            },
        )

    def test_parse_codex_transient_error(self) -> None:
        lines = [
            json.dumps({"type": "error", "message": "Reconnecting... 2/5"}),
            json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": "all good"}}),
            json.dumps({
                "type": "turn.completed",
                "usage": {"input_tokens": 10, "output_tokens": 5},
            }),
        ]
        res = subagent_run.parse_codex("\n".join(lines), last_message="")
        self.assertEqual(res["status"], "SUCCESS")
        self.assertIsNone(res["error"])
        self.assertIn("Reconnecting... 2/5", res["warnings"])

    def test_parse_codex_errors(self) -> None:
        lines_failed = [
            json.dumps({"type": "turn.failed", "error": {"message": "turn failed detail"}}),
        ]
        res1 = subagent_run.parse_codex("\n".join(lines_failed), last_message="")
        self.assertEqual(res1["status"], "ERROR")
        self.assertEqual(res1["error"], "turn failed detail")

        lines_top_error = [
            json.dumps({"type": "error", "message": "top level error message"}),
        ]
        res2 = subagent_run.parse_codex("\n".join(lines_top_error), last_message="")
        self.assertEqual(res2["status"], "ERROR")
        self.assertEqual(res2["error"], "top level error message")

    def test_parse_codex_fallback_and_malformed(self) -> None:
        lines = [
            "non-json line",
            "{broken json",
            "12345",
            json.dumps({"type": "turn.completed"}),
        ]
        res = subagent_run.parse_codex("\n".join(lines), last_message="  fallback message  \n")
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["response"], "fallback message")

    def test_classify(self) -> None:
        self.assertEqual(subagent_run.classify(0, {"status": "SUCCESS"}, ""), 0)
        self.assertEqual(subagent_run.classify(1, {"status": "ERROR", "error": "hit usage limit"}, ""), 3)
        self.assertEqual(subagent_run.classify(1, {"status": "ERROR", "error": "error 429 too many requests"}, ""), 3)
        self.assertEqual(subagent_run.classify(1, {"status": "ERROR"}, "RESOURCE_EXHAUSTED"), 3)
        self.assertEqual(subagent_run.classify(1, {"status": "SUCCESS"}, ""), 1)
        self.assertEqual(subagent_run.classify(1, {"status": "ERROR", "error": "general failure"}, ""), 1)

    @patch("subagent_run.shutil.which", return_value="fake-agy")
    @patch("subagent_run.subprocess.run")
    def test_run_agy_success(self, mock_run: MagicMock, mock_which: MagicMock) -> None:
        stdout_bytes = json.dumps({
            "status": "SUCCESS",
            "response": "Agy completed successfully",
            "conversation_id": "conv-99",
            "usage": {
                "input_tokens": 10,
                "cache_read_tokens": 0,
                "output_tokens": 5,
                "thinking_tokens": 0,
                "total_tokens": 15,
            },
        }).encode("utf-8")
        mock_run.return_value = subprocess.CompletedProcess(
            args=["fake-agy"], returncode=0, stdout=stdout_bytes, stderr=b""
        )
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            prompt_file = tmp / "prompt.txt"
            prompt_file.write_text("Hello prompt", encoding="utf-8")
            out_file = tmp / "out.json"

            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                exit_code = subagent_run.run(
                    subagent_run.parse_args(
                        ["--model", "flash", "--prompt-file", str(prompt_file), "--out", str(out_file)]
                    )
                )

            self.assertEqual(exit_code, 0)
            self.assertTrue(out_file.is_file())
            data = json.loads(out_file.read_text(encoding="utf-8"))
            for key in ("status", "response", "usage", "alias", "cli", "model", "exit_code"):
                self.assertIn(key, data)
            self.assertEqual(data["status"], "SUCCESS")
            self.assertEqual(data["response"], "Agy completed successfully")
            self.assertEqual(data["alias"], "flash")
            self.assertEqual(data["cli"], "agy")
            self.assertEqual(data["model"], "gemini-3.8-flash-medium")
            self.assertEqual(data["exit_code"], 0)

            printed = buf.getvalue()
            self.assertIn("tokens:", printed)
            self.assertIn("Agy completed successfully", printed)

    @patch("subagent_run.shutil.which", return_value="fake-agy")
    @patch("subagent_run.subprocess.run")
    def test_run_agy_empty_response(self, mock_run: MagicMock, mock_which: MagicMock) -> None:
        stdout_bytes = json.dumps({
            "status": "SUCCESS",
            "response": "",
            "conversation_id": "conv-empty",
        }).encode("utf-8")
        mock_run.return_value = subprocess.CompletedProcess(
            args=["fake-agy"], returncode=0, stdout=stdout_bytes, stderr=b""
        )
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            prompt_file = tmp / "prompt.txt"
            prompt_file.write_text("Hello prompt", encoding="utf-8")
            out_file = tmp / "out.json"

            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                exit_code = subagent_run.run(
                    subagent_run.parse_args(
                        ["--model", "flash", "--prompt-file", str(prompt_file), "--out", str(out_file)]
                    )
                )

            self.assertEqual(exit_code, 0)
            printed = buf.getvalue()
            self.assertIn("empty response: check git status before re-delegating", printed)

    @patch("subagent_run.shutil.which", return_value="fake-agy")
    @patch("subagent_run.subprocess.run")
    def test_run_agy_quota_error(self, mock_run: MagicMock, mock_which: MagicMock) -> None:
        stdout_bytes = json.dumps({
            "status": "ERROR",
            "error": "RESOURCE_EXHAUSTED: quota limit exceeded",
        }).encode("utf-8")
        mock_run.return_value = subprocess.CompletedProcess(
            args=["fake-agy"], returncode=1, stdout=stdout_bytes, stderr=b""
        )
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            prompt_file = tmp / "prompt.txt"
            prompt_file.write_text("Hello prompt", encoding="utf-8")
            out_file = tmp / "out.json"

            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                exit_code = subagent_run.run(
                    subagent_run.parse_args(
                        ["--model", "flash", "--prompt-file", str(prompt_file), "--out", str(out_file)]
                    )
                )

            self.assertEqual(exit_code, 3)

    @patch("subagent_run.shutil.which", return_value="fake-agy")
    @patch("subagent_run.subprocess.run")
    def test_run_timeout(self, mock_run: MagicMock, mock_which: MagicMock) -> None:
        mock_run.side_effect = subprocess.TimeoutExpired(cmd=["fake-agy"], timeout=630)
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            prompt_file = tmp / "prompt.txt"
            prompt_file.write_text("Hello prompt", encoding="utf-8")
            out_file = tmp / "out.json"

            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                exit_code = subagent_run.run(
                    subagent_run.parse_args(
                        ["--model", "flash", "--prompt-file", str(prompt_file), "--out", str(out_file)]
                    )
                )

            self.assertEqual(exit_code, 4)
            self.assertTrue(out_file.is_file())
            data = json.loads(out_file.read_text(encoding="utf-8"))
            self.assertEqual(data["status"], "ERROR")
            self.assertTrue(data["error"].startswith("timeout after"))

    @patch("subagent_run.shutil.which", return_value=None)
    def test_run_cli_not_on_path(self, mock_which: MagicMock) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            prompt_file = tmp / "prompt.txt"
            prompt_file.write_text("Hello prompt", encoding="utf-8")
            out_file = tmp / "out.json"

            buf_err = io.StringIO()
            with contextlib.redirect_stderr(buf_err):
                exit_code = subagent_run.run(
                    subagent_run.parse_args(
                        ["--model", "flash", "--prompt-file", str(prompt_file), "--out", str(out_file)]
                    )
                )
            self.assertEqual(exit_code, 1)

    @patch("subagent_run.shutil.which", return_value="fake-codex")
    @patch("subagent_run.subprocess.run")
    def test_run_codex(self, mock_run: MagicMock, mock_which: MagicMock) -> None:
        prompt_text = "Review this PR diff"
        codex_stdout = "\n".join([
            json.dumps({"type": "thread.started", "thread_id": "thread-123"}),
            json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": "codex response"}}),
            json.dumps({
                "type": "turn.completed",
                "usage": {"input_tokens": 50, "output_tokens": 15},
            }),
        ]).encode("utf-8")

        mock_run.return_value = subprocess.CompletedProcess(
            args=["fake-codex"], returncode=0, stdout=codex_stdout, stderr=b""
        )
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            prompt_file = tmp / "prompt.txt"
            prompt_file.write_text(prompt_text, encoding="utf-8")
            out_file = tmp / "out.json"

            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                exit_code = subagent_run.run(
                    subagent_run.parse_args(
                        ["--model", "luna", "--read-only", "--prompt-file", str(prompt_file), "--out", str(out_file)]
                    )
                )

            self.assertEqual(exit_code, 0)
            self.assertTrue(mock_run.called)
            call_kwargs = mock_run.call_args[1]
            self.assertEqual(call_kwargs.get("input"), prompt_text.encode("utf-8"))

            self.assertTrue(out_file.is_file())
            data = json.loads(out_file.read_text(encoding="utf-8"))
            self.assertEqual(data["cli"], "codex")
            self.assertEqual(data["status"], "SUCCESS")
            self.assertEqual(data["response"], "codex response")

    @patch("subagent_run.shutil.which", return_value="fake-agy")
    @patch("subagent_run.subprocess.run")
    def test_run_long_response_cut(self, mock_run: MagicMock, mock_which: MagicMock) -> None:
        long_response = "X" * (subagent_run.RESPONSE_CUT + 500)
        stdout_bytes = json.dumps({
            "status": "SUCCESS",
            "response": long_response,
            "conversation_id": "conv-long",
        }).encode("utf-8")
        mock_run.return_value = subprocess.CompletedProcess(
            args=["fake-agy"], returncode=0, stdout=stdout_bytes, stderr=b""
        )
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            prompt_file = tmp / "prompt.txt"
            prompt_file.write_text("Hello prompt", encoding="utf-8")
            out_file = tmp / "out.json"

            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                exit_code = subagent_run.run(
                    subagent_run.parse_args(
                        ["--model", "flash", "--prompt-file", str(prompt_file), "--out", str(out_file)]
                    )
                )

            self.assertEqual(exit_code, 0)
            printed = buf.getvalue()
            self.assertNotIn(long_response, printed)
            cut_notice = f"[cut at {subagent_run.RESPONSE_CUT} characters; full text in {str(out_file)}]"
            self.assertIn(cut_notice, printed)
            self.assertIn(str(out_file), printed)

    # Tester-added (032-06 Tester stage): spec §2 Feature A Output, exit 1 and exit 2 at run level.
    @patch("subagent_run.shutil.which", return_value="fake-agy")
    @patch("subagent_run.subprocess.run")
    def test_run_agy_plain_error_exits_1(self, mock_run: MagicMock, mock_which: MagicMock) -> None:
        stdout_bytes = json.dumps({"status": "ERROR", "error": "invalid model selection"}).encode("utf-8")
        mock_run.return_value = subprocess.CompletedProcess(
            args=["fake-agy"], returncode=1, stdout=stdout_bytes, stderr=b""
        )
        with tempfile.TemporaryDirectory() as tmp_dir:
            prompt_file = Path(tmp_dir) / "prompt.txt"
            prompt_file.write_text("Hello prompt", encoding="utf-8")
            out_file = Path(tmp_dir) / "out.json"
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                exit_code = subagent_run.run(subagent_run.parse_args(
                    ["--model", "flash", "--prompt-file", str(prompt_file), "--out", str(out_file)]
                ))
            self.assertEqual(exit_code, subagent_run.EXIT_FAILED)
            self.assertIn("invalid model selection", buf.getvalue())
            self.assertEqual(json.loads(out_file.read_text(encoding="utf-8"))["exit_code"], 1)

    @patch("subagent_run.shutil.which", return_value="fake-codex")
    @patch("subagent_run.subprocess.run")
    def test_run_refusal_starts_no_cli(self, mock_run: MagicMock, mock_which: MagicMock) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            prompt_file = Path(tmp_dir) / "prompt.txt"
            prompt_file.write_text("Hello prompt", encoding="utf-8")
            for argv in (
                ["--model", "nope", "--prompt-file", str(prompt_file)],
                ["--model", "luna", "--prompt-file", str(prompt_file)],
                ["--model", "flash", "--effort", "low", "--prompt-file", str(prompt_file)],
                ["--model", "flash", "--prompt-file", str(Path(tmp_dir) / "missing.txt")],
            ):
                with self.subTest(argv=argv), contextlib.redirect_stderr(io.StringIO()):
                    self.assertEqual(subagent_run.run(subagent_run.parse_args(argv)), subagent_run.EXIT_INPUT)


def write(root: Path, rel: str, text: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text), encoding="utf-8")
    return path


TODO = """\
# Tasks

## Grammar
- Task line: `- !STATE | NNN-SS | Title`

---

## Phase 1 (1/2 DONE)
- !DONE | 010-01 | [Old](/docs/specs/01_old.md) — legacy
- !APPROVED | 010-02 | [New](/docs/specs/010_02_new.md)
"""

KNOWN = """\
# Known Issues

| ID | Status | Area | Found | Owner |
|---|---|---|---|---|
| KI-001 | OPEN | x | 010-02 | — |

## KI-001 — first
text
"""

ADHOC = "cmake " + "-S . -B build"


def spec(task_id: str, approved: str) -> str:
    return f"---\nid: {task_id}\ntitle: t\napproved: {approved}\n---\n# Spec\nSee KI-001 and [todo](/docs/tasks/agent_todo.md).\n"


class AgentCommonTest(unittest.TestCase):
    def test_machine_paths(self) -> None:
        self.assertEqual(agent_common.machine_paths(f"use {DRIVE}vcpkg"), [DRIVE])
        self.assertEqual(agent_common.machine_paths(f"export X={HOME}vcpkg"), [HOME])
        self.assertEqual(agent_common.machine_paths("see https://example.com/a and http://x/y"), [])
        self.assertEqual(agent_common.machine_paths(f"NEVER use `{DRIVE}`"), [])
        self.assertEqual(agent_common.machine_paths("file:" + "///tmp/x"), ["file:" + "///"])
        json_escaped = '"VCPKG_ROOT": "C' + ':' + '\\\\vcpkg"'
        self.assertEqual(len(agent_common.machine_paths(json_escaped)), 1)
        self.assertEqual(len(agent_common.machine_paths(f"Set root to {DRIVE}vcpkg (not needed on Linux)")), 1)
        self.assertEqual(len(agent_common.machine_paths(f"| VCPKG | {DRIVE}dev | no |")), 1)
        self.assertEqual(len(agent_common.machine_paths(f"Set `VCPKG_ROOT={DRIVE}vcpkg` if vcpkg is not on PATH")), 1)
        self.assertEqual(agent_common.machine_paths(f"never use `{DRIVE}` or `Z:/`"), [])
        self.assertEqual(agent_common.read_frontmatter("﻿---\nid: 1\n---\n"), {"id": "1"})
        self.assertEqual(agent_common.LINK_RE.findall("[Foo [bar]](/docs/x.md)"), [("Foo [bar]", "/docs/x.md")])

    def test_adhoc_cmake(self) -> None:
        for cmd in (ADHOC, "cmake " + "-B out", "cd b && cmake " + "..", "cmake.exe -G Ninja " + "-S src"):
            with self.subTest(cmd=cmd):
                self.assertTrue(agent_common.is_adhoc_cmake(cmd))
        for cmd in ("cmake --preset x", "cmake --build --preset x", "cmake --install out/build/x", "ctest --preset x"):
            with self.subTest(cmd=cmd):
                self.assertFalse(agent_common.is_adhoc_cmake(cmd))

    def test_frontmatter_and_strip_code(self) -> None:
        self.assertEqual(agent_common.read_frontmatter("---\nid: 1  # c\napproved: null\n---\nx"), {"id": "1", "approved": "null"})
        self.assertIsNone(agent_common.read_frontmatter("# no"))
        stripped = agent_common.strip_code("a `[x](/no)` b\n```\n[y](/no)\n```\n[z](/yes)")
        self.assertNotIn("/no", stripped)
        self.assertIn("/yes", stripped)


class LintDocsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        write(self.root, "docs/tasks/agent_todo.md", TODO)
        write(self.root, "docs/known_issues.md", KNOWN)
        write(self.root, "docs/specs/01_old.md", "# Legacy\n[gone](/include/gone.h)\n")
        write(self.root, "docs/specs/010_02_new.md", spec("010-02", "2026-10-28"))

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def errors(self) -> list[str]:
        return [f[3] for f in lint_docs.lint(self.root).findings if f[0] == "ERROR"]

    def test_clean_tree(self) -> None:
        report = lint_docs.lint(self.root)
        self.assertEqual([f for f in report.findings if f[0] == "ERROR"], [])
        self.assertIn(("INFO", "docs/specs/01_old.md", 2, "broken link /include/gone.h"), report.findings)

    def test_approved_state_needs_approved_spec(self) -> None:
        write(self.root, "docs/specs/010_02_new.md", spec("010-02", "null"))
        self.assertTrue(any("approved: null" in e for e in self.errors()))

    def test_bad_task_line_duplicate_id_and_count(self) -> None:
        write(self.root, "docs/tasks/agent_todo.md", TODO + "- !DONE | 010-02 | dup\n- [ ] old style\n")
        errs = self.errors()
        self.assertTrue(any("does not follow" in e for e in errs))
        self.assertTrue(any("used 2 times" in e for e in errs))
        self.assertTrue(any("heading says" in e for e in errs))

    def test_machine_path_and_unknown_ki(self) -> None:
        write(self.root, "docs/note.md", f"Install to {DRIVE}tools. See KI-009.\n")
        errs = self.errors()
        self.assertTrue(any("machine-specific path" in e for e in errs))
        self.assertTrue(any("KI-009 is not defined" in e for e in errs))

    def test_open_task_with_legacy_spec(self) -> None:
        todo = TODO.replace("!DONE | 010-01", "!DEV | 010-01").replace("(1/2 DONE)", "(0/2 DONE)")
        write(self.root, "docs/tasks/agent_todo.md", todo)
        self.assertTrue(any("has no frontmatter" in e for e in self.errors()))

    def test_review_findings(self) -> None:
        # no separator: the task section is missing
        write(self.root, "docs/tasks/agent_todo.md", TODO.replace("\n---\n", "\n"))
        self.assertTrue(any("no '---' line" in e for e in self.errors()))
        # a task-like line without the "- " prefix, a patch without parent, an impossible date
        write(self.root, "docs/tasks/agent_todo.md",
              TODO + "* !DEV | 030-01 | X\n- !BACKLOG | 021-07-01 | orphan patch\n")
        errs = self.errors()
        self.assertTrue(any("does not follow" in e for e in errs))
        self.assertTrue(any("must be indented" in e for e in errs))
        self.assertTrue(any("must follow its task 021-07" in e for e in errs))
        write(self.root, "docs/tasks/agent_todo.md", TODO + "  - !BACKLOG | 030-02 | indented, not a patch\n")
        self.assertTrue(any("only patches" in e for e in self.errors()))
        write(self.root, "docs/tasks/agent_todo.md", TODO)
        write(self.root, "docs/specs/010_02_new.md", spec("010-02", "2026-19-45"))
        self.assertTrue(any("real YYYY-MM-DD" in e for e in self.errors()))

    def test_legacy_needs_marker_and_known_dirs(self) -> None:
        write(self.root, "docs/specs/010_02_new.md", spec("010-02", "2026-10-28"))
        todo = TODO.replace(" — legacy", "")  # DONE spec without frontmatter, not marked legacy
        write(self.root, "docs/tasks/agent_todo.md", todo)
        self.assertTrue(any("only DONE tasks marked 'legacy'" in e for e in self.errors()))
        write(self.root, "docs/tasks/agent_todo.md", TODO.replace(" — legacy", " — legacy (branch: `feature/old-name`)"))
        write(self.root, "docs/tasks/feature_old-name/walkthrough.md", f"{DRIVE}x\n")
        write(self.root, "docs/tasks/feature_factory/plan.md", "plan\n")
        report = lint_docs.lint(self.root)
        self.assertIn(("INFO", "docs/tasks/feature_old-name/walkthrough.md", 1, f"machine-specific path {DRIVE!r}"), report.findings)
        self.assertTrue(any(f[0] == "ERROR" and "feature_factory" in f[1] for f in report.findings))

    def test_round3_findings(self) -> None:
        # 'legacy' in the title does not seal a spec; only the note after " — " does
        todo = TODO.replace("[Old](/docs/specs/01_old.md) — legacy", "[legacy cleanup](/docs/specs/01_old.md)")
        write(self.root, "docs/tasks/agent_todo.md", todo)
        self.assertTrue(any("only DONE tasks marked 'legacy'" in e for e in self.errors()))
        # an undefined KI in an unsealed file is an ERROR even if a sealed file names it first
        write(self.root, "docs/tasks/agent_todo.md", TODO)
        write(self.root, "docs/specs/01_old.md", "# Legacy\nSee KI-099.\n")
        write(self.root, "docs/zz_note.md", "See KI-099.\n")
        report = lint_docs.lint(self.root)
        self.assertIn(("ERROR", "docs/zz_note.md", 1, "KI-099 is not defined in docs/known_issues.md"), report.findings)
        self.assertIn(("INFO", "docs/specs/01_old.md", 2, "KI-099 is not defined in docs/known_issues.md"), report.findings)

    def test_encoding_links_and_sealed_ki(self) -> None:
        (self.root / "docs/specs/010_02_new.md").write_text("﻿" + spec("010-02", "2026-10-28"), encoding="utf-8")
        write(self.root, "docs/a b.md", "x\n")
        write(self.root, "docs/note.md", "[ok](/docs/a%20b.md)\n")
        write(self.root, "docs/specs/01_old.md", "# Legacy\nSee KI-077.\n")
        (self.root / "docs/cp949.md").write_bytes("한글".encode("cp949"))
        report = lint_docs.lint(self.root)
        errs = [f for f in report.findings if f[0] == "ERROR"]
        self.assertEqual([f for f in errs if "cp949" not in f[1]], [])
        self.assertTrue(any("not UTF-8" in f[3] for f in errs))
        self.assertIn(("INFO", "docs/specs/01_old.md", 2, "KI-077 is not defined in docs/known_issues.md"), report.findings)

    def test_lessons_are_checked(self) -> None:
        # lint runs tools/lessons.py check when the tree has lessons/ (spec 070-01 AC-6)
        (self.root / "tools").mkdir()
        shutil.copy(Path(__file__).resolve().parents[2] / "tools" / "lessons.py", self.root / "tools" / "lessons.py")
        write(self.root, "lessons/tracks/01_t/track.toml", 'title = "T"\n')
        write(self.root, "lessons/tracks/01_t/01_l/lesson.toml", 'id = "l"\ntitle = "L"\nsources = ["main.cpp"]\n')
        self.assertIn("lessons: 'sources' entry 'main.cpp' does not exist", self.errors())
        write(self.root, "lessons/tracks/01_t/01_l/main.cpp", "int main() {}\n")
        self.assertEqual(self.errors(), [])

    def test_lesson_markdown_links_are_checked(self) -> None:
        # links in lessons/ Markdown (intro.md, READMEs) are checked like docs/ (spec 090-04, KI-019)
        write(self.root, "lessons/intro.md", "[a](/lessons/tracks/01_t/01_l/README.md) [b](README.md)\n")
        errs = self.errors()
        self.assertIn("broken link /lessons/tracks/01_t/01_l/README.md", errs)
        self.assertIn("broken link README.md", errs)
        write(self.root, "lessons/README.md", "x\n")
        write(self.root, "lessons/tracks/01_t/01_l/README.md", "[up](../../../intro.md)\n")
        self.assertEqual(self.errors(), [])

class BuildScriptTest(unittest.TestCase):
    def test_pick_preset(self) -> None:
        names = ["windows-x64-debug", "linux-x64-debug"]
        self.assertEqual(build.pick_preset("auto", "Windows", names), "windows-x64-debug")
        self.assertEqual(build.pick_preset("auto", "Linux", names), "linux-x64-debug")
        with self.assertRaises(ValueError):
            build.pick_preset("linux-x64-asan", "Linux", names)

    def test_configure_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bdir = Path(tmp) / "b"
            self.assertEqual(build.configure_mode(bdir, "/src", False), "plain")
            write(bdir, "CMakeCache.txt", f"CMAKE_HOME_DIRECTORY:INTERNAL=/src\nCMAKE_CACHEFILE_DIR:INTERNAL={bdir.as_posix()}\n")
            self.assertEqual(build.configure_mode(bdir, "/src", False), "fresh")  # interrupted configure
            write(bdir, "build.ninja", "")
            write(bdir, "CMakeFiles/rules.ninja", "")
            self.assertIsNone(build.configure_mode(bdir, "/src/", False))
            self.assertEqual(build.configure_mode(bdir, "/SRC", False), "stale")  # Linux paths keep case
            self.assertEqual(build.configure_mode(bdir, "/src", True), "fresh")
            self.assertEqual(build.configure_mode(bdir, "/other", False), "stale")
            write(bdir, "_deps/g-subbuild/CMakeCache.txt", "CMAKE_CACHEFILE_DIR:INTERNAL=/elsewhere/g-subbuild\n")
            self.assertEqual(build.configure_mode(bdir, "/src", False), "stale")

    def test_preset_change_and_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bdir = Path(tmp) / "b"
            write(bdir, "CMakeCache.txt", f"CMAKE_HOME_DIRECTORY:INTERNAL=/src\nCMAKE_CACHEFILE_DIR:INTERNAL={bdir.as_posix()}\n")
            write(bdir, "build.ninja", "")
            write(bdir, "CMakeFiles/rules.ninja", "")
            presets = write(Path(tmp), "CMakePresets.json", "{}")
            old = (bdir / "CMakeCache.txt").stat().st_mtime - 10
            os.utime(presets, (old, old))
            self.assertIsNone(build.configure_mode(bdir, "/src", False, (presets,)))
            os.utime(presets, None)
            os.utime(bdir / "CMakeCache.txt", (old, old))
            self.assertEqual(build.configure_mode(bdir, "/src", False, (presets,)), "plain")
        self.assertTrue(build.same_dir("C" + ":/_dev/cpp", "c" + ":\\_dev\\cpp\\"))
        self.assertFalse(build.same_dir("/home/a/Repo", "/home/a/repo"))
        with tempfile.TemporaryDirectory() as tmp:
            self.assertTrue(build.same_dir(tmp, str(Path(tmp) / "." )))

    def test_steps_and_batch(self) -> None:
        steps = build.build_steps("windows-x64-debug", "stale", "atugcc_tests", True, "Tracer*:-Tracer.Slow")
        self.assertEqual(steps[0], (["cmake", "--preset", "windows-x64-debug", "--fresh"], {}))
        self.assertEqual(steps[1], (["cmake", "--build", "--preset", "windows-x64-debug", "--target", "atugcc_tests"], {}))
        self.assertEqual(steps[2], (["ctest", "--preset", "windows-x64-debug"], {}))
        # spec 090-06 AC-5/AC-6: the filter runs through ctest, so AllTests' launcher and environment apply
        self.assertEqual(steps[3], (["ctest", "--preset", "windows-x64-debug", "-R", "^AllTests$", "--verbose"],
                                    {"GTEST_FILTER": "Tracer*:-Tracer.Slow"}))
        self.assertEqual(build.show(steps[3]),
                         "GTEST_FILTER=Tracer*:-Tracer.Slow ctest --preset windows-x64-debug -R ^AllTests$ --verbose")
        script = build.batch_script("VsDevCmd.bat", steps)
        lines = script.split("\r\n")
        at = lines.index('set "GTEST_FILTER=Tracer*:-Tracer.Slow"')
        self.assertEqual(lines[at + 1], 'ctest --preset windows-x64-debug -R "^AllTests$" --verbose')
        self.assertNotIn("atugcc_tests.exe", script)
        self.assertEqual(script.count("if %errorlevel% neq 0 exit /b %errorlevel%"), len(steps) + 1)
        self.assertNotIn("if errorlevel 1", script)  # misses negative crash codes
        self.assertNotIn("|| exit", script)
        self.assertEqual(build.build_steps("p", None, None, False, None), [(["cmake", "--build", "--preset", "p"], {})])

    @unittest.skipUnless(os.name == "nt", "runs cmd.exe")
    def test_batch_arguments_reach_the_program_unchanged(self) -> None:
        # cmd drops an unquoted ^ in a batch file (U2 review): run a real batch, not a string comparison.
        args = ["^AllTests$", "a b", "x&y", "Tracer*:-Tracer.Slow", "plain"]
        with tempfile.TemporaryDirectory() as tmp:
            bat, out = Path(tmp) / "t.bat", Path(tmp) / "args.txt"
            script = (f'"{sys.executable}" -I -c "import sys; open(sys.argv[1], \'w\').write(chr(10).join(sys.argv[2:]))" '
                      + " ".join(build.batch_arg(a) for a in [str(out), *args]))
            bat.write_text("@echo off\r\n" + script + "\r\n", encoding="utf-8")
            subprocess.run(["cmd.exe", "/d", "/c", str(bat)], check=True)
            self.assertEqual(out.read_text().split("\n"), args)

    def test_bad_filter(self) -> None:  # spec 090-06 AC-7
        self.assertIsNone(build.bad_filter("Logger*.Shared*:-*Slow?"))
        for bad in ("A%PATH%", 'A"B', "A\nB", "A\rB"):
            with self.subTest(bad=bad):
                self.assertIsNotNone(build.bad_filter(bad))
                for preset in ("windows-x64-debug", "linux-x64-tsan"):
                    err = io.StringIO()
                    with patch.object(build.subprocess, "run") as ran, contextlib.redirect_stderr(err):
                        self.assertEqual(build.main(["--preset", preset, "--gtest-filter", bad, "--dry-run"]), 2)
                    ran.assert_not_called()  # refused before any step or WSL hand-off
                    self.assertIn("--gtest-filter must not contain", err.getvalue())

    def test_run_passes_step_environment(self) -> None:
        with patch.object(build.subprocess, "run", return_value=MagicMock(returncode=0)) as ran, \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(build.run([(["a"], {}), (["b"], {"GTEST_FILTER": "X*"})], Path(".")), 0)
        self.assertIsNone(ran.call_args_list[0].kwargs["env"])
        env = ran.call_args_list[1].kwargs["env"]
        self.assertEqual(env["GTEST_FILTER"], "X*")
        self.assertIn("PATH", {k.upper() for k in env})  # the rest of the environment is kept

    def test_wsl_forwarding(self) -> None:
        args = build.argparse.Namespace(target=None, test=True, gtest_filter=None, fresh=False, dry_run=False)
        cmd = build.wsl_command(build.forwarded_args(args, "linux-x64-asan"), Path("repo"), "Ubuntu")
        self.assertEqual(cmd[:3], ["wsl.exe", "-d", "Ubuntu"])
        self.assertIn("--exec", cmd)
        self.assertEqual(cmd[-3:], ["--preset", "linux-x64-asan", "--test"])
        args.gtest_filter = "Logger*:-*Slow"
        self.assertEqual(build.forwarded_args(args, "linux-x64-tsan")[-2:], ["--gtest-filter", "Logger*:-*Slow"])

    def test_label(self) -> None:  # spec 040-02 AC-8
        steps = build.build_steps("windows-x64-debug", None, None, True, None, label="scenario")
        self.assertIn((["ctest", "--preset", "windows-x64-debug", "-L", "scenario", "--no-tests=error"], {}), steps)
        self.assertNotIn((["ctest", "--preset", "windows-x64-debug"], {}), steps)
        reason = build.bad_filter("a%b", "--label")
        self.assertIsNotNone(reason)
        self.assertIn("--label", reason)
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(build.main(["--label", 'x"y', "--dry-run"]), 2)
        args = build.argparse.Namespace(target=None, test=False, label="scenario", gtest_filter=None, fresh=False, dry_run=False, report=None)
        self.assertEqual(build.forwarded_args(args, "linux-x64-asan")[-2:], ["--label", "scenario"])

    def test_report_build_steps(self) -> None:  # spec 040-02 AC-13
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            steps = build.build_steps("windows-x64-debug", None, None, False, "Tracer*", label="scenario", report=tmp_path)
            self.assertEqual(steps[1], (["ctest", "--preset", "windows-x64-debug", "--show-only=json-v1"], {}, tmp_path / "tests.json"))
            self.assertEqual(steps[2][0][-2:], ["--output-junit", (tmp_path / "ctest-1.junit.xml").as_posix()])
            self.assertEqual(steps[3][0][-2:], ["--output-junit", (tmp_path / "ctest-2.junit.xml").as_posix()])
            self.assertEqual(steps[2][1]["GTEST_OUTPUT"], f"json:{tmp_path.as_posix()}/gtest/")
            self.assertEqual(steps[3][1]["GTEST_OUTPUT"], f"json:{tmp_path.as_posix()}/gtest/")
            self.assertEqual(steps[3][1]["GTEST_FILTER"], "Tracer*")
            steps_no_report = build.build_steps("windows-x64-debug", None, None, False, "Tracer*", label="scenario")
            for s in steps_no_report:
                self.assertEqual(len(s), 2)

    def test_report_show_and_batch(self) -> None:  # spec 040-02 AC-13
        with tempfile.TemporaryDirectory() as tmp:
            out_file = Path(tmp) / "tests.json"
            step = (["ctest", "--preset", "p", "--show-only=json-v1"], {}, out_file)
            self.assertTrue(build.show(step).endswith(f"> {out_file.as_posix()}"))
            codes_file = Path(tmp) / "step_codes.txt"
            script = build.batch_script("VsDevCmd.bat", [step], step_codes_file=codes_file)
            self.assertIn(f'>>"{codes_file.as_posix()}" echo 0 %errorlevel%', script)
            self.assertIn(f'> "{out_file.as_posix()}"', script)

    @unittest.skipUnless(os.name == "nt", "runs cmd.exe")
    def test_batch_exit_codes(self) -> None:  # spec 040-02 AC-13
        with tempfile.TemporaryDirectory() as tmp:
            t = Path(tmp)
            fake_vs = t / "fake_vs.bat"
            fake_vs.write_text("@exit /b 0\r\n", encoding="utf-8")
            step_codes = t / "step_codes.txt"
            steps = [
                ([sys.executable, "-c", "exit(0)"], {}),
                ([sys.executable, "-c", "exit(3)"], {}),
            ]
            script = build.batch_script(str(fake_vs), steps, step_codes_file=step_codes)
            bat = t / "run.bat"
            bat.write_text(script, encoding="utf-8")
            res = subprocess.run(["cmd.exe", "/d", "/c", str(bat)])
            self.assertEqual(res.returncode, 3)
            self.assertEqual(step_codes.read_text(encoding="utf-8").splitlines(), ["0 0", "1 3"])

    def test_report_main_argument_errors(self) -> None:  # spec 040-02 AC-13
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(build.main(["--report"]), 2)
            self.assertEqual(build.main(["--report", "out/test-reports/t"]), 2)
            self.assertEqual(build.main(["--report", DRIVE + "x", "--test"]), 2)
            self.assertEqual(build.main(["--report", "/x", "--test"]), 2)
        target = build.REPO_ROOT / "out" / "test-reports" / "t"
        self.assertFalse(target.exists())
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = build.main(["--report", "out/test-reports/t", "--dry-run", "--label", "scenario"])
        self.assertEqual(code, 0)
        self.assertIn("(dry run: not written)", buf.getvalue())
        self.assertFalse(target.exists())

    def test_report_dir_problem(self) -> None:  # spec 040-02 AC-13
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertIsNotNone(build.report_dir_problem(".", root))
            self.assertIsNotNone(build.report_dir_problem("..", root))
            self.assertIsNotNone(build.report_dir_problem("a/../..", root))
            non_empty = root / "non_empty"
            non_empty.mkdir()
            (non_empty / "other.txt").write_text("x", encoding="utf-8")
            self.assertIsNotNone(build.report_dir_problem("non_empty", root))
            file_path = root / "file.txt"
            file_path.write_text("x", encoding="utf-8")
            self.assertIsNotNone(build.report_dir_problem("file.txt", root))
            empty_dir = root / "empty"
            empty_dir.mkdir()
            self.assertIsNone(build.report_dir_problem("empty", root))
            with_run = root / "with_run"
            with_run.mkdir()
            (with_run / "run.json").write_text("{}", encoding="utf-8")
            (with_run / "extra.txt").write_text("x", encoding="utf-8")
            self.assertIsNone(build.report_dir_problem("with_run", root))
            self.assertIsNone(build.report_dir_problem("missing", root))

    def test_forwarded_args_report(self) -> None:  # spec 040-02 AC-13
        args = build.argparse.Namespace(target=None, test=False, label=None, gtest_filter=None, fresh=False, dry_run=False, report="out/test-reports/p/t")
        self.assertEqual(build.forwarded_args(args, "linux-x64-asan")[-2:], ["--report", "out/test-reports/p/t"])

    def test_finish_report_no_test_step(self) -> None:  # spec 040-02 AC-12
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report_dir = root / "rep"
            report_dir.mkdir()
            run_data = {
                "preset": "linux-x64-debug",
                "steps": [
                    {"argv": ["cmake", "--build", "--preset", "linux-x64-debug"], "code": 1},
                    {"argv": ["ctest", "--output-junit", "x.xml"], "code": None},
                ],
            }
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                build.finish_report(report_dir, "rep", run_data, root)
            self.assertIn("no test report", buf.getvalue())
            self.assertTrue((report_dir / "run.json").is_file())
            self.assertFalse((report_dir / "report.md").exists())


class TestReportTest(unittest.TestCase):
    def test_write_report(self) -> None:  # spec 040-02 AC-13
        with tempfile.TemporaryDirectory() as tmp_str:
            rep = Path(tmp_str)
            (rep / "gtest").mkdir()
            (rep / "run.json").write_text(json.dumps({
                "preset": "linux-x64-debug",
                "command": "py -3 .agent/scripts/build.py --label unit|scenario",
                "build_dir": "out/build/linux-x64-debug",
                "started": "2026-11-04 12:00:00",
                "steps": [
                    {"argv": ["cmake", "--build", "--preset", "linux-x64-debug"], "code": 0},
                    {"argv": ["ctest", "--preset", "linux-x64-debug", "--show-only=json-v1"], "code": 0},
                    {"argv": ["ctest", "--preset", "linux-x64-debug", "-L", "scenario", "--output-junit", "ctest-1.junit.xml"], "code": 8},
                ],
            }), encoding="utf-8")
            (rep / "tests.json").write_text(json.dumps({
                "tests": [
                    {"name": "AllTests", "properties": [{"name": "LABELS", "value": ["unit"]}], "command": ["bin/atugcc_tests"]},
                    {"name": "scenario.A.B", "properties": [{"name": "LABELS", "value": ["scenario"]}], "command": ["bin/atugcc_scenarios"]},
                    {"name": "CrashDump", "properties": [{"name": "LABELS", "value": ["probe"]}], "command": ["bin/crash_probe"]},
                ],
            }), encoding="utf-8")
            crash_lines = [f"line {i}" for i in range(1, 41)]
            crash_lines[24] = f"{rep.as_posix()}/out/build/linux-x64-debug/bin/crash_probe"
            crash_out = "\n".join(crash_lines)
            xml_content = (
                '<testsuite>'
                '<testcase name="AllTests" time="2.0" status="run"/>'
                '<testcase name="scenario.A.B" time="1.0" status="fail">'
                '<failure message="Failed"/>'
                '<system-out>scenario output</system-out>'
                '</testcase>'
                '<testcase name="CrashDump" time="0.5" status="fail">'
                '<failure message="Failed"/>'
                f'<system-out>{crash_out}</system-out>'
                '</testcase>'
                '</testsuite>'
            )
            (rep / "ctest-1.junit.xml").write_text(xml_content, encoding="utf-8")
            (rep / "gtest" / "atugcc_scenarios.json").write_text(json.dumps({
                "tests": 1, "failures": 1, "disabled": 0,
                "testsuites": [{
                    "name": "A", "tests": 1, "failures": 1, "disabled": 0,
                    "testsuite": [{
                        "name": "B", "status": "RUN", "result": "COMPLETED",
                        "failures": [{"failure": "x.cpp:3\nFailed\nGoogle Test trace:\nscenario.hpp:73: step 2: check\n"}],
                    }],
                }],
            }), encoding="utf-8")
            (rep / "gtest" / "broken.json").write_text("{", encoding="utf-8")
            out_path = test_report.write_report(rep, repo_root=rep)
            text = out_path.read_text(encoding="utf-8")

            headings = [
                "# Test report: linux-x64-debug",
                "## Steps",
                "## Results by label",
                "## Failures",
                "## Slowest tests",
                "## GoogleTest cases",
                "## Inputs",
            ]
            pos = 0
            for h in headings:
                idx = text.find(h, pos)
                self.assertNotEqual(idx, -1, f"heading {h!r} not found in order")
                pos = idx + len(h)

            self.assertIn("| unit | 1 | 1 | 0 | 0 |", text)
            self.assertIn("| scenario | 1 | 0 | 1 | 0 |", text)
            self.assertIn("| probe | 1 | 0 | 1 | 0 |", text)
            self.assertIn("| **All** | 3 | 1 | 2 | 0 |", text)

            self.assertIn("### scenario.A.B", text)
            self.assertIn("`A.B`", text)
            self.assertIn("step 2: check", text)

            self.assertIn("### CrashDump", text)
            self.assertIn("line 40", text)
            self.assertIn("line 11", text)
            self.assertNotIn("line 10", text)

            self.assertIn("could not read: gtest/broken.json", text)
            self.assertIn("unit\\|scenario", text)
            self.assertNotIn(rep.as_posix(), text)
            self.assertNotIn(str(rep), text)
            self.assertIn("| 8 |", text)

    def test_fallback_cmake_labels(self) -> None:  # spec 040-02 AC-13
        with tempfile.TemporaryDirectory() as tmp_str:
            rep = Path(tmp_str)
            (rep / "run.json").write_text(json.dumps({
                "preset": "linux-x64-debug",
                "command": "py -3 .agent/scripts/build.py",
                "build_dir": "out/build/linux-x64-debug",
                "steps": [],
            }), encoding="utf-8")
            xml_content = (
                '<testsuite>'
                '<testcase name="AllTests" time="2.0" status="run">'
                '<properties><property name="cmake_labels" value="unit"/></properties>'
                '</testcase>'
                '</testsuite>'
            )
            (rep / "ctest-1.junit.xml").write_text(xml_content, encoding="utf-8")
            out_path = test_report.write_report(rep, repo_root=rep)
            text = out_path.read_text(encoding="utf-8")
            self.assertIn("| unit | 1 | 1 | 0 | 0 |", text)

    def test_main(self) -> None:  # spec 040-02 AC-13
        with tempfile.TemporaryDirectory() as tmp:
            t = Path(tmp)
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(test_report.main([str(t / "missing")]), 2)
                self.assertEqual(test_report.main([str(t)]), 2)  # no ctest-*.junit.xml
            # run.json is optional (a run made without build.py, tests/README.md 4.4)
            (t / "ctest-1.junit.xml").write_text(
                '<testsuite><testcase name="AllTests" time="1" status="run"/></testsuite>', encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(test_report.main([str(t)]), 0)
            report = (t / "report.md").read_text(encoding="utf-8")
            self.assertIn("# Test report: unknown", report)
            self.assertIn("| **All** | 1 | 1 | 0 | 0 |", report)


class GuardHookTest(unittest.TestCase):
    def test_commands(self) -> None:
        self.assertIsNotNone(guard.decide({"tool_name": "Bash", "tool_input": {"command": ADHOC}}))
        self.assertIsNotNone(guard.decide({"tool_name": "PowerShell", "tool_input": {"command": "cmake " + ".."}}))
        self.assertIsNone(guard.decide({"tool_name": "Bash", "tool_input": {"command": "cmake --preset linux-x64-debug"}}))

    def test_commit_on_main(self) -> None:
        event = {"tool_name": "Bash", "tool_input": {"command": "git commit -m x"}}
        with patch.object(guard.ac, "git", return_value=MagicMock(stdout="main\n")):
            self.assertIsNotNone(guard.decide(event))
        with patch.object(guard.ac, "git", return_value=MagicMock(stdout="feature/090-01-x\n")):
            self.assertIsNone(guard.decide(event))

    def test_edit_result_and_stdin(self) -> None:
        with tempfile.TemporaryDirectory(dir=guard.ROOT / "out" if (guard.ROOT / "out").is_dir() else None) as tmp:
            target = Path(tmp) / "x.json"
            target.write_text('"root": "C_X/vcpkg"\n', encoding="utf-8")
            event = {"tool_name": "Edit", "tool_input": {"file_path": str(target), "old_string": "_X", "new_string": ":"}}
            with patch.object(guard, "inside_repo", return_value=True), patch.object(guard.ac, "is_ignored", return_value=False):
                self.assertIsNotNone(guard.decide(event))  # path assembled across the edit boundary
                target.write_text(f'"a": "{DRIVE}x"\nend\n', encoding="utf-8")
                copy = {"tool_name": "Edit", "tool_input": {"file_path": str(target), "old_string": "end",
                                                            "new_string": f'"a": "{DRIVE}x"\nend'}}
                self.assertIsNotNone(guard.decide(copy))  # copying an existing offending line
        payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": "echo 한글 && " + ADHOC}}, ensure_ascii=False).encode("utf-8")
        fake_stdin = MagicMock()
        fake_stdin.buffer.read.return_value = payload
        out = io.StringIO()
        with patch.object(guard.sys, "stdin", fake_stdin), patch.object(guard.sys, "stdout", out):
            self.assertEqual(guard.main(), 0)
        self.assertIn('"permissionDecision": "deny"', out.getvalue())

    def test_writes(self) -> None:
        inside = str(guard.ROOT / "docs" / "x.md")
        with patch.object(guard.ac, "is_ignored", return_value=False):
            self.assertIsNotNone(guard.decide({"tool_name": "Edit", "tool_input": {"file_path": inside, "new_string": f"{DRIVE}vcpkg"}}))
            self.assertIsNotNone(guard.decide({"tool_name": "MultiEdit", "tool_input": {"file_path": inside, "edits": [{"new_string": f"{HOME}x"}]}}))
            self.assertIsNone(guard.decide({"tool_name": "Write", "tool_input": {"file_path": inside, "content": f"never use `{DRIVE}`"}}))
            self.assertIsNotNone(guard.decide({"tool_name": "Write", "tool_input": {"file_path": inside, "content": f"root {DRIVE}vcpkg (not on CI)"}}))
        with patch.object(guard.ac, "is_ignored", return_value=True):
            self.assertIsNone(guard.decide({"tool_name": "Write", "tool_input": {"file_path": inside, "content": f"{DRIVE}vcpkg"}}))
        outside = str(guard.ROOT.parent / "elsewhere.md")
        self.assertIsNone(guard.decide({"tool_name": "Write", "tool_input": {"file_path": outside, "content": f"{DRIVE}x"}}))


CM = "cm" + "ake"
COMMIT = "git " + "commit"


class CommandPositionTest(unittest.TestCase):
    """Spec 090-06 AC-1–3: a command is judged by what runs, not by text it mentions (KI-008)."""

    ALLOWED = (  # (shell, command); allowed on a feature branch and, being no commit, on main
        ("bash", f"cat > t.txt <<'EOF'\n{CM} -S . -B build\nEOF"),
        ("bash", f"cat > t.py <<EOF\nG = '{COMMIT}'\nEOF\necho done"),
        ("bash", f'grep -n "{CM} -B" docs/x.md'),
        ("bash", f"grep -n {CM} -B 3 CMakeLists.txt"),
        ("bash", f'echo "{COMMIT}"'),
        ("bash", "git log --grep " + "commit"),
        ("bash", f"echo '{CM} -S x' | wc -l"),
        ("powershell", f"@'\n{CM} -S . -B build\n'@ | Set-Content t.txt"),
        ("powershell", f'Select-String -Pattern "{CM} -B" -Path docs\\x.md'),
        ("powershell", f"Write-Output '{COMMIT}'"),
        ("bash", f"{CM} --preset p"),
        ("bash", f"{CM} --build --preset p --target atugcc_tests"),
        ("bash", "ctest --preset p"),
        ("powershell", f"& {CM} --build --preset p"),
        ("bash", f"echo $(echo hi # don't\n) {CM} -B o"),
        ("bash", f"cat <<\\EOF\n{CM} -B o\nEOF"),
        ("bash", f"cat <<E\"OF\"\n{CM} -B o\nEOF"),
        ("bash", f"bash tool.sh -c \"{CM} -B o\""),
        ("bash", f"cat <<'EOF'\n$({CM} -B o)\nEOF"),  # quoted delimiter: the body is not expanded
        ("powershell", f"$s = @'\n$({CM} -B o)\n'@"),  # single-quoted here-string: not expanded
        ("bash", f"for {CM} in a b; do echo $x; done"),
    )
    ADHOC_RUNS = (
        ("bash", f"{CM} -S . -B build"),
        ("bash", f"cd x && {CM} .."),
        ("bash", f"a; {CM} -Bout"),
        ("bash", f'bash -c "{CM} -S . -B b"'),
        ("bash", f"sh -c '{CM} -B o'"),
        ("bash", f'bash -lc "cd x; {CM} -B o"'),
        ("bash", f'pwsh -Command "{CM} -B o"'),
        ("bash", f'cmd /c "{CM} -B o"'),
        ("bash", f"wsl.exe --cd . --exec {CM} -B o"),
        ("bash", f"sudo env X=1 {CM} .."),
        ("bash", f'echo "$({CM} -B o)"'),
        ("bash", f"echo `{CM} -B o`"),
        ("bash", f"bash <<EOF\n{CM} -B o\nEOF"),
        ("bash", f"eval {CM} -B o"),
        ("powershell", f'& "tools\\{CM}.exe" "-S" "." "-B" "out"'),
        ("powershell", f"{CM}.exe -G Ninja -S src"),
        ("powershell", f'powershell -c "{CM} -B o"'),
        ("powershell", f'cmd.exe /d /s /c "{CM} -B o"'),
        ("powershell", f'Write-Output "$({CM} -B o)"'),
        # U1b review: compound commands (the old regex caught these)
        ("bash", f"for p in a; do {CM} -B $p; done"),
        ("bash", f"if true; then {CM} -B o; fi"),
        ("bash", f"if false; then :; else {CM} ..; fi"),
        ("bash", f"until {CM} -B o; do :; done"),
        ("bash", f"while true; do {CM} -B o; done"),
        ("bash", f"! {CM} -B o"),
        ("bash", f"coproc {CM} -B o"),
        ("bash", f"case x in a) {CM} -B o;; esac"),
        # redirections, substitutions in odd places
        ("bash", f"{CM} &>log -S . -B out"),
        ("bash", f"{CM} >&log -S . -B out"),
        ("bash", f"echo x >$({CM} -B o)"),
        ("bash", f'cat <<< "$({CM} -B o)"'),
        ("bash", f"cat <<< `{CM} -B o`"),
        ("bash", f"cat <<EOF\n$({CM} -B o)\nEOF"),
        ("powershell", f"Write-Output x >$({CM} -B o)"),
        ("powershell", f'$s = @"\n$({CM} -B o)\n"@'),
        # text fed to a shell
        ("bash", f"cat <<EOF | bash\n{CM} -B o\nEOF"),
        ("bash", f'echo "{CM} -B o" | bash'),
        ("bash", f'bash <<< "{CM} -B o"'),
        ("bash", f"bash -s <<'EOF'\n{CM} -B o\nEOF"),
        # wrappers with options
        ("bash", f"sudo -E {CM} -B o"),
        ("bash", f"time -p {CM} -B o"),
        ("bash", f"nice -10 {CM} -B o"),
        ("bash", f"env -C x {CM} -B o"),
        ("bash", f"timeout 600 {CM} -B o"),
        ("bash", f"timeout -k 5 600 {CM} -B o"),
        ("bash", f"stdbuf -oL {CM} -B o"),
        # PowerShell ways to run a string or a program
        ("powershell", f'iex "{CM} -B o"'),
        ("powershell", f"Invoke-Expression '{CM} -B o'"),
        ("powershell", f". {CM} -B o"),
        ("powershell", f'Start-Process {CM} -ArgumentList "-B o"'),
        ("powershell", f'Start-Process -FilePath {CM} -ArgumentList "-S", ".", "-B", "o"'),
        # U1b re-review: option values before the script argument, more wrapper forms
        ("bash", f'bash -o pipefail -c "{CM} -B o"'),
        ("bash", f'bash --rcfile x -c "{CM} -B o"'),
        ("bash", f'pwsh -ExecutionPolicy Bypass -Command "{CM} -B o"'),
        ("powershell", f'powershell -ExecutionPolicy Bypass -Command "{CM} -B o"'),
        ("powershell", f'pwsh -NoProfile -WorkingDirectory x -c "{CM} -B o"'),
        ("bash", f'env -S "{CM} -B o"'),
        ("bash", f"timeout --signal=KILL 60 {CM} -B o"),
        ("powershell", f'powershell -exec bypass -Command "{CM} -B o"'),
        ("bash", f'pwsh -exec bypass -c "{CM} -B o"'),
        ("powershell", f'powershell -win hidden -Command "{CM} -B o"'),
    )
    COMMITS = (
        ("bash", f"{COMMIT} -m x"),
        ("bash", "git -C . " + "commit -m x"),
        ("bash", "git -c user.name=x " + "commit -m x"),
        ("bash", f'{COMMIT} -q -F - <<\'EOF\'\nmsg\nEOF'),
        ("bash", f"git add . && {COMMIT} -m x"),
        ("powershell", f"{COMMIT} -m x"),
        ("bash", "! " + f"{COMMIT} -m x"),
        ("bash", "sudo -u me " + f"{COMMIT} -m x"),
        ("bash", "git --attr-source HEAD " + "commit -m x"),
        ("bash", f"if true; then {COMMIT} -m x; fi"),
    )

    @staticmethod
    def decide(shell: str, command: str, branch: str) -> str | None:
        tool = "PowerShell" if shell == "powershell" else "Bash"
        with patch.object(guard.ac, "git", return_value=MagicMock(stdout=f"{branch}\n")):
            return guard.decide({"tool_name": tool, "tool_input": {"command": command}})

    def test_mentions_are_allowed(self) -> None:  # AC-1
        for shell, cmd in self.ALLOWED:
            for branch in ("main", "feature/090-06-x"):
                with self.subTest(shell=shell, cmd=cmd, branch=branch):
                    self.assertIsNone(self.decide(shell, cmd, branch))
        # commits whose message mentions an ad-hoc configure: allowed on a feature branch, still a commit on main
        for message in (f'{COMMIT} -m "docs: never run {CM} -S"',
                        f"{COMMIT} -m \"$(cat <<'EOF'\ndocs: do not run {CM} -S; it's banned\nEOF\n)\"",
                        f"{COMMIT} -q -F - <<'EOF'\n1) never run {CM} -S . -B b\nEOF"):
            with self.subTest(message=message):
                self.assertIsNone(self.decide("bash", message, "feature/090-06-x"))
                self.assertIsNotNone(self.decide("bash", message, "main"))

    def test_runs_are_denied(self) -> None:  # AC-2
        for shell, cmd in self.ADHOC_RUNS:
            with self.subTest(shell=shell, cmd=cmd):
                self.assertTrue(agent_common.is_adhoc_cmake(cmd, shell))
                self.assertIsNotNone(self.decide(shell, cmd, "feature/090-06-x"))
        for shell, cmd in self.COMMITS:
            with self.subTest(shell=shell, cmd=cmd):
                self.assertTrue(agent_common.is_git_commit(cmd, shell))
                self.assertIsNotNone(self.decide(shell, cmd, "main"))
                self.assertIsNone(self.decide(shell, cmd, "feature/090-06-x"))

    def test_unsplittable_falls_back_to_regex(self) -> None:  # AC-3
        for shell, cmd in (("bash", f"echo 'unclosed {CM} -S . -B b"), ("bash", f"cat <<EOF\n{CM} -B o"),
                           ("powershell", f'Write-Output "unclosed {CM} -B o')):
            with self.subTest(shell=shell, cmd=cmd):
                self.assertIsNone(agent_common.simple_commands(cmd, shell))
                self.assertIsNotNone(self.decide(shell, cmd, "feature/090-06-x"))

    def test_long_commands_split_in_linear_time(self) -> None:
        # A hook call has a 15 s budget; a quadratic step made 40,000 prefix words take seconds (U1b re-review).
        for cmd in ("A=1 " * 40000 + "ls", "sudo " + "-E " * 40000 + "ls", ("echo " + "x " * 1000 + "; ") * 160,
                    'env -S "' + "env -S " * 20000 + 'x"'):
            start = time.perf_counter()
            self.assertIsNotNone(agent_common.simple_commands(cmd, "bash"))
            self.assertLess(time.perf_counter() - start, 2.0, cmd[:20])

    def test_simple_commands_shape(self) -> None:
        self.assertEqual(agent_common.simple_commands('FOO=1 sudo git -C "a b" status; echo hi', "bash"),
                         [["git", "-C", "a b", "status"], ["echo", "hi"]])
        self.assertEqual(agent_common.simple_commands("cat <<'X'\nbody; rm\nX\nls 2>&1 >/dev/null", "bash"),
                         [["cat"], ["ls"]])
        self.assertEqual(agent_common.simple_commands("Get-Item 'it''s' | Out-Null", "powershell"),
                         [["Get-Item", "it's"], ["Out-Null"]])
        self.assertEqual(agent_common.simple_commands('dir "C\\x\\" ; ls', "powershell"),
                         [["dir", "C\\x\\"], ["ls"]])


class NamingCheckTest(unittest.TestCase):
    def test_camel(self) -> None:
        self.assertEqual(naming_check.camel("record_message"), "recordMessage")
        self.assertEqual(naming_check.camel("format_d2"), "formatD2")
        self.assertEqual(naming_check.camel("condition_variable_usage1"), "conditionVariableUsage1")

    def test_rename_keeps_strings(self) -> None:
        text = ('t.record_message("record_message()"); // see record_message\n'
                'auto r = R"x(record_message)x"; char c = \'_\'; /* push_node */ push_node(1);\n')
        out = naming_check.rename_text(text, {"record_message": "recordMessage", "push_node": "pushNode"})
        self.assertIn('t.recordMessage("record_message()");', out)
        self.assertIn("// see recordMessage", out)
        self.assertIn('R"x(record_message)x"', out)
        self.assertIn("/* pushNode */ pushNode(1);", out)

    def test_candidates_and_apply(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, "include/a.hpp",
                  "void do_work();\nstd::string s = std::to_string(1); std::ofstream out_file(p);\n"
                  'void f() { do_work(); log("do_work()"); }\n')
            found = naming_check.candidates(root)
            self.assertEqual(sorted(found), ["do_work"])
            self.assertEqual(len(found["do_work"]), 2)  # declaration + call, not the string
            self.assertEqual(naming_check.main(["--root", str(root), "--apply"]), 0)
            self.assertIn("void doWork();", (root / "include/a.hpp").read_text(encoding="utf-8"))
            self.assertIn('log("do_work()")', (root / "include/a.hpp").read_text(encoding="utf-8"))
            self.assertEqual(naming_check.main(["--root", str(root)]), 0)

    def test_apply_refuses_clash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, "src/b.cpp", "void do_work(); void doWork();\n")
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(naming_check.main(["--root", str(root), "--apply"]), 2)
            self.assertIn("void do_work();", (root / "src/b.cpp").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
