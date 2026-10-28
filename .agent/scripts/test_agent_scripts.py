#!/usr/bin/env python3
"""Self-tests for the agent scripts in .agent/scripts/. Stdlib unittest only.

    py -3 .agent/scripts/test_agent_scripts.py      (Windows)
    python3 .agent/scripts/test_agent_scripts.py    (Linux)

SubagentRunTest is copied from the ai_sec project together with subagent_run.py (task 090-01).
"""
from __future__ import annotations

import contextlib
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

import subagent_run  # noqa: E402


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


if __name__ == "__main__":
    unittest.main(verbosity=2)
