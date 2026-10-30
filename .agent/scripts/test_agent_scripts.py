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
        steps = build.build_steps("windows-x64-debug", "stale", "atugcc_tests", True, "Tracer*", ".exe")
        self.assertEqual(steps[0], ["cmake", "--preset", "windows-x64-debug", "--fresh"])
        self.assertEqual(steps[1], ["cmake", "--build", "--preset", "windows-x64-debug", "--target", "atugcc_tests"])
        self.assertEqual(steps[2], ["ctest", "--preset", "windows-x64-debug"])
        self.assertEqual(steps[3][1], "--gtest_filter=Tracer*")
        script = build.batch_script("VsDevCmd.bat", steps)
        self.assertIn("out\\build\\windows-x64-debug\\bin\\atugcc_tests.exe", script)
        self.assertEqual(script.count("if %errorlevel% neq 0 exit /b %errorlevel%"), len(steps) + 1)
        self.assertNotIn("if errorlevel 1", script)  # misses negative crash codes
        self.assertNotIn("|| exit", script)
        self.assertEqual(build.build_steps("p", None, None, False, None, ""), [["cmake", "--build", "--preset", "p"]])

    def test_wsl_forwarding(self) -> None:
        args = build.argparse.Namespace(target=None, test=True, gtest_filter=None, fresh=False, dry_run=False)
        cmd = build.wsl_command(build.forwarded_args(args, "linux-x64-asan"), Path("repo"), "Ubuntu")
        self.assertEqual(cmd[:3], ["wsl.exe", "-d", "Ubuntu"])
        self.assertIn("--exec", cmd)
        self.assertEqual(cmd[-3:], ["--preset", "linux-x64-asan", "--test"])


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
