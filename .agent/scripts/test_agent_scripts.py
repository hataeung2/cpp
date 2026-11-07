#!/usr/bin/env python3
"""Self-tests for the agent scripts in .agent/scripts/ and .claude/hooks/guard.py. Stdlib unittest only.

    py -3 .agent/scripts/test_agent_scripts.py      (Windows)
    python3 .agent/scripts/test_agent_scripts.py    (Linux)
"""
from __future__ import annotations

import contextlib
import importlib
import importlib.util
import io
import json
import os
import re
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
import archive_docs  # noqa: E402
import build  # noqa: E402
import guard_rules  # noqa: E402
import lint_docs  # noqa: E402
import naming_check  # noqa: E402
import subagent_run  # noqa: E402
import sync_skills  # noqa: E402
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

    PREAMBLE = (
        "You are a sub-agent started with this task prompt. "
        "Do not run the repository's boot sequence. "
        "Follow this prompt and the project rules in it."
    )

    def test_build_prompt(self) -> None:
        # 090-12 AC-1: the preamble (spec wording) is the first line, then the file list, then the text.
        self.assertEqual(subagent_run.SUBAGENT_PREAMBLE, self.PREAMBLE)
        prompt_text = "Implement feature X."
        self.assertEqual(
            subagent_run.build_prompt(prompt_text, []), f"{self.PREAMBLE}\n\n{prompt_text}"
        )

        result = subagent_run.build_prompt(prompt_text, ["a.py", "b.py"])
        self.assertEqual(
            result, f"{self.PREAMBLE}\n\nContext files:\n- a.py\n- b.py\n\n{prompt_text}"
        )

    def test_build_prompt_rules_order(self) -> None:
        # 090-12-01 AC-1: preamble, rules block, context file list, then the text.
        self.assertEqual(
            subagent_run.build_prompt("Do X.", ["a.py"], "## Project rules (code)\nR"),
            f"{self.PREAMBLE}\n\n## Project rules (code)\nR\n\nContext files:\n- a.py\n\nDo X.",
        )
        self.assertEqual(
            subagent_run.build_prompt(f"{self.PREAMBLE}\nDo X.", [], "RULES"),
            f"{self.PREAMBLE}\n\nRULES\n\nDo X.",
        )

    def write_rule_tree(self, root: Path) -> None:
        """Small rule files with every section RULE_SECTIONS names, plus distractors."""
        files = {
            ".agent/rules/impl.md": "# Impl\n\n## Core\nCore rule.\n### Core detail\nKept.\n\n## 1. Style\nNot core.\n",
            ".agent/rules/delegation.md": (
                "# D\n## 4. Call\nintro\n\n### Sub-agent limits\n- Limit.\n\n### The lead's prompt\nNot a limit.\n"
                "## 8. Fresh reviewer\ntext\n\n### Review checklist\n- Risk.\n```\n## not a heading\nVERDICT\n```\nAfter fence.\n\n## 9. Recording\nNo.\n"
            ),
            ".agent/rules/test.md": "# T\n## 2. C++ Testing (GoogleTest)\n- Test rule.\n## 3. Build\nNo.\n",
            "lessons/README.md": "# L\n## 레슨 작성 안내\n- 주석은 한국어와 영어.\n## 성능 측정 레슨 작성\nNo.\n",
        }
        for rel, text in files.items():
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")

    def test_rule_bundle_kinds(self) -> None:
        # 090-12-01 AC-1: every kind = Core + Sub-agent limits (+ its own section), exact text.
        common = "## Core\nCore rule.\n### Core detail\nKept.\n\n### Sub-agent limits\n- Limit."
        extra = {
            "code": "",
            "research": "",
            "test": "\n\n## 2. C++ Testing (GoogleTest)\n- Test rule.",
            "lesson": "\n\n## 레슨 작성 안내\n- 주석은 한국어와 영어.",
            "review": "\n\n### Review checklist\n- Risk.\n```\n## not a heading\nVERDICT\n```\nAfter fence.",
        }
        self.assertEqual(set(subagent_run.KINDS), set(extra))
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            self.write_rule_tree(root)
            for kind, tail in extra.items():
                with self.subTest(kind=kind):
                    self.assertEqual(
                        subagent_run.rule_bundle(kind, root),
                        f"## Project rules ({kind})\n\n{common}{tail}",
                    )

    def test_rule_bundle_missing_section(self) -> None:
        # 090-12-01 AC-2: a renamed heading or a missing file is an input error naming file and heading.
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            self.write_rule_tree(root)
            test_md = root / ".agent/rules/test.md"
            test_md.write_text("# T\n## 2. Testing\nrenamed\n", encoding="utf-8")
            with self.assertRaises(subagent_run.InputError) as ctx:
                subagent_run.rule_bundle("test", root)
            self.assertIn(".agent/rules/test.md", str(ctx.exception))
            self.assertIn("## 2. C++ Testing (GoogleTest)", str(ctx.exception))
            subagent_run.rule_bundle("code", root)  # other kinds still build
            (root / "lessons/README.md").unlink()
            with self.assertRaises(subagent_run.InputError) as ctx:
                subagent_run.rule_bundle("lesson", root)
            self.assertIn("rule file not found: lessons/README.md", str(ctx.exception))
            with self.assertRaises(subagent_run.InputError):
                subagent_run.rule_bundle("nope", root)

    def test_real_rule_bundles_build(self) -> None:
        # The repository's own rule files hold every section (the docs gate checks the sizes).
        for kind in subagent_run.KINDS:
            with self.subTest(kind=kind):
                bundle = subagent_run.rule_bundle(kind)
                self.assertTrue(bundle.startswith(f"## Project rules ({kind})\n\n## Core\n"))
                self.assertIn("### Sub-agent limits", bundle)

    @patch("subagent_run.subprocess.run")
    def test_print_rules_calls_no_model(self, mock_run: MagicMock) -> None:
        # 090-12-01 AC-3: --print-rules prints the block and exits 0 without starting a CLI.
        for kind in subagent_run.KINDS:
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                code = subagent_run.run(subagent_run.parse_args(["--print-rules", kind]))
            self.assertEqual(code, subagent_run.EXIT_OK)
            self.assertEqual(buf.getvalue(), subagent_run.rule_bundle(kind) + "\n")
        self.assertFalse(mock_run.called)
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as ctx:
            subagent_run.parse_args(["--print-rules", "nope"])
        self.assertEqual(ctx.exception.code, 2)

    def test_build_prompt_keeps_one_preamble(self) -> None:
        # 090-12 AC-2: a prompt file that already starts with the preamble gets it once.
        body = "Review U1.\n\nLine two."
        for text in (
            f"{self.PREAMBLE}\n{body}",
            f"\n  \n  {self.PREAMBLE}  \n\n\n{body}",
            f"{self.PREAMBLE}\r\n\r\n{body}",
        ):
            with self.subTest(text=text):
                result = subagent_run.build_prompt(text, [])
                self.assertEqual(result.count(self.PREAMBLE), 1)
                self.assertEqual(result, f"{self.PREAMBLE}\n\n{body}")
        # Only the first non-blank line counts: a later quote of the sentence stays.
        quoted = f"Check this line:\n{self.PREAMBLE}\n"
        self.assertEqual(subagent_run.build_prompt(quoted, []).count(self.PREAMBLE), 2)
        self.assertEqual(
            subagent_run.build_prompt(f"{self.PREAMBLE}\n{body}", ["a.py"]),
            f"{self.PREAMBLE}\n\nContext files:\n- a.py\n\n{body}",
        )

    def test_load_prompt_validation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            missing = tmp / "missing.txt"
            with self.assertRaises(subagent_run.InputError):
                subagent_run.load_prompt(str(missing), [], "agy", "code")

            whitespace_file = tmp / "whitespace.txt"
            whitespace_file.write_text("   \n\t  \n", encoding="utf-8")
            with self.assertRaises(subagent_run.InputError):
                subagent_run.load_prompt(str(whitespace_file), [], "agy", "code")

            long_text = "x" * (subagent_run.AGY_PROMPT_LIMIT + 1)
            long_file = tmp / "long.txt"
            long_file.write_text(long_text, encoding="utf-8")
            with self.assertRaises(subagent_run.InputError):
                subagent_run.load_prompt(str(long_file), [], "agy", "code")

            rules = subagent_run.rule_bundle("code")
            codex_prompt = subagent_run.load_prompt(str(long_file), [], "codex", "code")
            self.assertEqual(codex_prompt, f"{self.PREAMBLE}\n\n{rules}\n\n{long_text}")

            # The agy limit counts the preamble and the rules the runner adds.
            room = subagent_run.AGY_PROMPT_LIMIT - len(self.PREAMBLE) - 2 - len(rules) - 2
            fits_file = tmp / "fits.txt"
            fits_file.write_text("x" * room, encoding="utf-8")
            self.assertEqual(
                len(subagent_run.load_prompt(str(fits_file), [], "agy", "code")),
                subagent_run.AGY_PROMPT_LIMIT,
            )
            over_file = tmp / "over.txt"
            over_file.write_text("x" * (room + 1), encoding="utf-8")
            with self.assertRaises(subagent_run.InputError):
                subagent_run.load_prompt(str(over_file), [], "agy", "code")

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
                        ["--model", "flash", "--kind", "code", "--prompt-file", str(prompt_file), "--out", str(out_file)]
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
                        ["--model", "flash", "--kind", "code", "--prompt-file", str(prompt_file), "--out", str(out_file)]
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
                        ["--model", "flash", "--kind", "code", "--prompt-file", str(prompt_file), "--out", str(out_file)]
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
                        ["--model", "flash", "--kind", "code", "--prompt-file", str(prompt_file), "--out", str(out_file)]
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
                        ["--model", "flash", "--kind", "code", "--prompt-file", str(prompt_file), "--out", str(out_file)]
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
                        ["--model", "luna", "--read-only", "--kind", "review", "--prompt-file", str(prompt_file), "--out", str(out_file)]
                    )
                )

            self.assertEqual(exit_code, 0)
            self.assertTrue(mock_run.called)
            call_kwargs = mock_run.call_args[1]
            self.assertEqual(
                call_kwargs.get("input"),
                f"{self.PREAMBLE}\n\n{subagent_run.rule_bundle('review')}\n\n{prompt_text}".encode("utf-8"),
            )

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
                        ["--model", "flash", "--kind", "code", "--prompt-file", str(prompt_file), "--out", str(out_file)]
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
                    ["--model", "flash", "--kind", "code", "--prompt-file", str(prompt_file), "--out", str(out_file)]
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
                ["--model", "nope", "--kind", "code", "--prompt-file", str(prompt_file)],
                ["--model", "luna", "--kind", "review", "--prompt-file", str(prompt_file)],
                ["--model", "flash", "--kind", "code", "--effort", "low", "--prompt-file", str(prompt_file)],
                ["--model", "flash", "--kind", "code", "--prompt-file", str(Path(tmp_dir) / "missing.txt")],
                ["--model", "flash", "--prompt-file", str(prompt_file)],  # 090-12-01 AC-2: no --kind
                ["--kind", "code", "--prompt-file", str(prompt_file)],
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
    return f"---\nid: {task_id}\ntitle: t\napproved: {approved}\n---\n# Spec\nSee KI-001 and [todo](/docs/agent_todo.md).\n"


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
        write(self.root, "docs/agent_todo.md", TODO)
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
        write(self.root, "docs/agent_todo.md", TODO + "- !DONE | 010-02 | dup\n- [ ] old style\n")
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
        write(self.root, "docs/agent_todo.md", todo)
        self.assertTrue(any("has no frontmatter" in e for e in self.errors()))

    def test_review_findings(self) -> None:
        # no separator: the task section is missing
        write(self.root, "docs/agent_todo.md", TODO.replace("\n---\n", "\n"))
        self.assertTrue(any("no '---' line" in e for e in self.errors()))
        # a task-like line without the "- " prefix, a patch without parent, an impossible date
        write(self.root, "docs/agent_todo.md",
              TODO + "* !DEV | 030-01 | X\n- !BACKLOG | 021-07-01 | orphan patch\n")
        errs = self.errors()
        self.assertTrue(any("does not follow" in e for e in errs))
        self.assertTrue(any("must be indented" in e for e in errs))
        self.assertTrue(any("must follow its task 021-07" in e for e in errs))
        write(self.root, "docs/agent_todo.md", TODO + "  - !BACKLOG | 030-02 | indented, not a patch\n")
        self.assertTrue(any("only patches" in e for e in self.errors()))
        write(self.root, "docs/agent_todo.md", TODO)
        write(self.root, "docs/specs/010_02_new.md", spec("010-02", "2026-19-45"))
        self.assertTrue(any("real YYYY-MM-DD" in e for e in self.errors()))

    def test_legacy_needs_marker_and_known_dirs(self) -> None:
        write(self.root, "docs/specs/010_02_new.md", spec("010-02", "2026-10-28"))
        todo = TODO.replace(" — legacy", "")  # DONE spec without frontmatter, not marked legacy
        write(self.root, "docs/agent_todo.md", todo)
        self.assertTrue(any("only DONE tasks marked 'legacy'" in e for e in self.errors()))
        write(self.root, "docs/agent_todo.md", TODO.replace(" — legacy", " — legacy (branch: `feature/old-name`)"))
        write(self.root, "docs/tasks/feature_old-name/walkthrough.md", f"{DRIVE}x\n")
        write(self.root, "docs/tasks/feature_factory/plan.md", "plan\n")
        report = lint_docs.lint(self.root)
        self.assertIn(("INFO", "docs/tasks/feature_old-name/walkthrough.md", 1, f"machine-specific path {DRIVE!r}"), report.findings)
        self.assertTrue(any(f[0] == "ERROR" and "feature_factory" in f[1] for f in report.findings))

    def test_round3_findings(self) -> None:
        # 'legacy' in the title does not seal a spec; only the note after " — " does
        todo = TODO.replace("[Old](/docs/specs/01_old.md) — legacy", "[legacy cleanup](/docs/specs/01_old.md)")
        write(self.root, "docs/agent_todo.md", todo)
        self.assertTrue(any("only DONE tasks marked 'legacy'" in e for e in self.errors()))
        # an undefined KI in an unsealed file is an ERROR even if a sealed file names it first
        write(self.root, "docs/agent_todo.md", TODO)
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

    def test_evolution_pages_come_in_pairs(self) -> None:
        # <x>.md (Korean) + <x>.en.md (English), same headings and code blocks (spec 090-07 AC-2)
        def warnings() -> list[tuple[str, str]]:
            return [
                (f[1], f[3])
                for f in lint_docs.lint(self.root).findings
                if f[0] == "WARN" and f[1].startswith("docs/cpp_evolution")
            ]

        page = "# T\n## Why\ntext\n```cpp\n#include <x>\n## not a heading\n```\n## Now\n"
        write(self.root, "docs/cpp_evolution/a.md", page)
        write(self.root, "docs/cpp_evolution/b.en.md", page)
        write(self.root, "docs/cpp_evolution.md", page)
        self.assertEqual(sorted(warnings()), [
            ("docs/cpp_evolution.md", "no English page cpp_evolution.en.md"),
            ("docs/cpp_evolution/a.md", "no English page a.en.md"),
            ("docs/cpp_evolution/b.en.md", "no Korean page b.md"),
        ])
        write(self.root, "docs/cpp_evolution/a.en.md", page.replace("## Now\n", "### Now\n"))
        write(self.root, "docs/cpp_evolution/b.md", page.replace("```cpp\n#include <x>\n## not a heading\n```\n", ""))
        write(self.root, "docs/cpp_evolution.en.md", page)
        self.assertEqual(sorted(warnings()), [
            ("docs/cpp_evolution/a.md", "headings differ from a.en.md: levels [1, 2, 2] vs [1, 2, 3]"),
            ("docs/cpp_evolution/b.md", "code blocks differ from b.en.md: 0 vs 1"),
        ])
        write(self.root, "docs/cpp_evolution/a.en.md", page)
        write(self.root, "docs/cpp_evolution/b.md", page)
        self.assertEqual(warnings(), [])
        (self.root / "docs/cpp_evolution.md").unlink()
        self.assertEqual(warnings(), [("docs/cpp_evolution.en.md", "no Korean page cpp_evolution.md")])

    def test_archive_ki_reference_across_files(self) -> None:
        # Case 1: KI id defined in KI_CLOSED or KI_DEFERRED is not reported as undefined
        closed_text = archive_docs.KI_CLOSED_INITIAL + (
            "| KI-002 | CLOSED | x | 010-01 | — |\n\n"
            "## KI-002 — closed issue\ntext\n"
        )
        deferred_text = archive_docs.KI_DEFERRED_INITIAL + (
            "| KI-003 | DEFERRED | x | 010-01 | — (when condition) |\n\n"
            "## KI-003 — deferred issue\ntext\n"
        )
        write(self.root, str(archive_docs.KI_CLOSED), closed_text)
        write(self.root, str(archive_docs.KI_DEFERRED), deferred_text)
        write(self.root, "docs/note.md", "See KI-002, KI-003, and KI-099.\n")
        errs = self.errors()
        every = [f[3] for f in lint_docs.lint(self.root).findings]  # no finding at any level
        self.assertFalse(any("KI-002 is not defined" in e for e in every))
        self.assertFalse(any("KI-003 is not defined" in e for e in every))
        self.assertTrue(any("KI-099 is not defined" in e for e in errs))

    def test_archive_group_counts_across_files(self) -> None:
        # Case 2: Group counts combine agent_todo.md and TODO_DONE
        todo_text = (
            "# Tasks\n\n## Grammar\n- Task line: `- !STATE | NNN-SS | Title`\n\n---\n\n"
            "## Phase 1 (2/3 DONE)\n"
            "- !APPROVED | 010-02 | [New](/docs/specs/010_02_new.md)\n"
        )
        write(self.root, "docs/agent_todo.md", todo_text)
        todo_done_text = archive_docs.TODO_DONE_INITIAL + (
            "\n## Phase 1\n"
            "- !DONE | 010-01 | [Old](/docs/specs/01_old.md) — legacy\n"
            "- !DONE | 010-03 | [Three](/docs/specs/010_03_three.md)\n"
        )
        write(self.root, str(archive_docs.TODO_DONE), todo_done_text)
        write(self.root, "docs/specs/010_03_three.md", spec("010-03", "2026-11-01"))
        errs = self.errors()
        self.assertFalse(any("heading says" in e for e in errs))
        write(self.root, "docs/agent_todo.md", todo_text.replace("(2/3 DONE)", "(1/3 DONE)"))
        errs_changed = self.errors()
        self.assertTrue(any("heading says" in e for e in errs_changed))

    def test_archive_sealed_artifact_dir(self) -> None:
        # Case 3: DONE task living only in TODO_DONE keeps its artifact dir sealed (INFO, not ERROR)
        todo_text = (
            "# Tasks\n\n## Grammar\n- Task line: `- !STATE | NNN-SS | Title`\n\n---\n\n"
            "## Phase 1 (2/2 DONE)\n"
            "- !DONE | 010-01 | [Old](/docs/specs/01_old.md) — legacy\n"
        )
        write(self.root, "docs/agent_todo.md", todo_text)
        todo_done_text = archive_docs.TODO_DONE_INITIAL + (
            "\n## Phase 1\n"
            "- !DONE | 010-03 | [Three](/docs/specs/010_03_three.md)\n"
        )
        write(self.root, str(archive_docs.TODO_DONE), todo_done_text)
        write(self.root, "docs/specs/010_03_three.md", spec("010-03", "2026-11-01"))
        write(self.root, "docs/tasks/feature_010-03-x/note.md", "See [broken](/docs/nonexistent.md)\n")
        report = lint_docs.lint(self.root)
        task_findings = [f for f in report.findings if "feature_010-03-x" in f[1]]
        self.assertTrue(task_findings)
        self.assertTrue(all(f[0] == "INFO" for f in task_findings))
        self.assertFalse(any(f[0] == "ERROR" and "feature_010-03-x" in f[1] for f in report.findings))

    def test_archive_todo_done_requires_done_state(self) -> None:
        # Case 4: Non-DONE task line in TODO_DONE is an ERROR mentioning DONE
        todo_done_text = archive_docs.TODO_DONE_INITIAL + (
            "\n## Phase 1\n"
            "- !APPROVED | 010-03 | [Three](/docs/specs/010_03_three.md)\n"
        )
        write(self.root, str(archive_docs.TODO_DONE), todo_done_text)
        write(self.root, "docs/agent_todo.md", TODO.replace("(1/2 DONE)", "(1/3 DONE)"))
        write(self.root, "docs/specs/010_03_three.md", spec("010-03", "2026-11-01"))
        report = lint_docs.lint(self.root)
        self.assertTrue(any(f[0] == "ERROR" and f[1] == archive_docs.TODO_DONE.as_posix() and "010-03" in f[3] and "DONE" in f[3]
                            for f in report.findings))
        self.assertFalse(any("heading says" in f[3] for f in report.findings))

    def test_archive_todo_done_unknown_group_heading(self) -> None:
        # Case 5: TODO_DONE group heading not present in todo is an ERROR
        todo_done_text = archive_docs.TODO_DONE_INITIAL + (
            "\n## Phase 99\n"
            "- !DONE | 099-01 | [Task 99](/docs/specs/099_01.md)\n"
        )
        write(self.root, str(archive_docs.TODO_DONE), todo_done_text)
        write(self.root, "docs/specs/099_01.md", spec("099-01", "2026-11-01"))
        errs = self.errors()
        self.assertTrue(any("Phase 99" in e for e in errs))

    def test_archive_duplicate_task_id_across_files(self) -> None:
        # Case 6: Same task id in todo and TODO_DONE triggers existing 'used 2 times' ERROR
        todo_done_text = archive_docs.TODO_DONE_INITIAL + (
            "\n## Phase 1\n"
            "- !DONE | 010-01 | [Old](/docs/specs/01_old.md) — legacy\n"
        )
        write(self.root, str(archive_docs.TODO_DONE), todo_done_text)
        errs = self.errors()
        self.assertTrue(any("used 2 times" in e for e in errs))

    def test_archive_warn_movable_done_tasks(self) -> None:
        # Case 7: Movable DONE task left in todo warns with archive_docs.py; uncompleted patch suppresses warn
        warns = [f[3] for f in lint_docs.lint(self.root).findings if f[0] == "WARN"]
        self.assertTrue(any("archive_docs.py" in w and "010-01" in w for w in warns))

        write(self.root, "docs/specs/010_01_01.md", spec("010-01-01", "2026-11-01"))
        todo_with_patch = (
            "# Tasks\n\n## Grammar\n- Task line: `- !STATE | NNN-SS | Title`\n\n---\n\n"
            "## Phase 1 (1/3 DONE)\n"
            "- !DONE | 010-01 | [Old](/docs/specs/01_old.md) — legacy\n"
            "  - !DEV | 010-01-01 | [Patch](/docs/specs/010_01_01.md)\n"
            "- !APPROVED | 010-02 | [New](/docs/specs/010_02_new.md)\n"
        )
        write(self.root, "docs/agent_todo.md", todo_with_patch)
        warns_patch = [f[3] for f in lint_docs.lint(self.root).findings if f[0] == "WARN"]
        self.assertFalse(any("archive_docs.py" in w for w in warns_patch))

    def test_archive_ki_status_file_mismatch_warns(self) -> None:
        # Case 8: Misplaced KI status warns with archive_docs.py
        todo_done = archive_docs.TODO_DONE_INITIAL + (
            "\n## Phase 1\n- !DONE | 010-01 | [Old](/docs/specs/01_old.md) — legacy\n"
        )
        write(self.root, str(archive_docs.TODO_DONE), todo_done)
        write(self.root, "docs/agent_todo.md", TODO.replace("- !DONE | 010-01 | [Old](/docs/specs/01_old.md) — legacy\n", ""))

        ki_text = (
            "# Known Issues\n\n"
            "| ID | Status | Area | Found | Owner |\n"
            "|---|---|---|---|---|\n"
            "| KI-001 | OPEN | x | 010-02 | — |\n"
            "| KI-002 | CLOSED | x | 010-02 | — |\n"
            "| KI-003 | DEFERRED | x | 010-02 | — (condition) |\n\n"
            "## KI-001 — first\ntext\n\n"
            "## KI-002 — second\ntext\n\n"
            "## KI-003 — third\ntext\n"
        )
        write(self.root, "docs/known_issues.md", ki_text)
        closed_text = archive_docs.KI_CLOSED_INITIAL + (
            "| KI-004 | OPEN | x | 010-02 | — |\n\n"
            "## KI-004 — fourth\ntext\n"
        )
        write(self.root, str(archive_docs.KI_CLOSED), closed_text)

        warns = [f for f in lint_docs.lint(self.root).findings if f[0] == "WARN" and "archive_docs.py" in f[3]]
        self.assertEqual(len(warns), 3)
        self.assertTrue(any("KI-002" in f[3] for f in warns))
        self.assertTrue(any("KI-003" in f[3] for f in warns))
        self.assertTrue(any("KI-004" in f[3] for f in warns))

    def test_archive_duplicate_ki_id_across_files(self) -> None:
        # Case 9: Same KI id in two KI files is an ERROR
        closed_text = archive_docs.KI_CLOSED_INITIAL + (
            "| KI-001 | CLOSED | x | 010-02 | — |\n\n"
            "## KI-001 — first closed\ntext\n"
        )
        write(self.root, str(archive_docs.KI_CLOSED), closed_text)
        errs = self.errors()
        self.assertTrue(any("KI-001" in e for e in errs))
        write(self.root, str(archive_docs.KI_CLOSED), closed_text.replace("KI-001", "KI-002"))
        self.assertFalse(any("KI-001" in e for e in self.errors()))

    def test_archive_deferred_owner_condition_required(self) -> None:
        # Case 10: DEFERRED with empty or '—' Owner is ERROR; '— (when X)' is valid
        deferred_dash = archive_docs.KI_DEFERRED_INITIAL + (
            "| KI-002 | DEFERRED | Area | 010-02 | — |\n\n"
            "## KI-002 — deferred\ntext\n"
        )
        write(self.root, str(archive_docs.KI_DEFERRED), deferred_dash)
        errs = self.errors()
        self.assertTrue(any("owner" in e.lower() for e in errs))

        deferred_empty = archive_docs.KI_DEFERRED_INITIAL + (
            "| KI-002 | DEFERRED | Area | 010-02 |   |\n\n"
            "## KI-002 — deferred\ntext\n"
        )
        write(self.root, str(archive_docs.KI_DEFERRED), deferred_empty)
        errs = self.errors()
        self.assertTrue(any("owner" in e.lower() for e in errs))

        deferred_valid = archive_docs.KI_DEFERRED_INITIAL + (
            "| KI-002 | DEFERRED | Area | 010-02 | — (when X) |\n\n"
            "## KI-002 — deferred\ntext\n"
        )
        write(self.root, str(archive_docs.KI_DEFERRED), deferred_valid)
        errs = self.errors()
        self.assertFalse(any("owner" in e.lower() for e in errs))

    def test_archive_unknown_ki_status(self) -> None:
        # Case 11: Unknown KI status is an ERROR
        write(self.root, "docs/known_issues.md", KNOWN.replace("| OPEN |", "| MAYBE |"))
        errs = self.errors()
        self.assertTrue(any("MAYBE" in e for e in errs))

    def rule_bundle_fixture(self, runner: bool = True) -> None:
        """The sections subagent_run.RULE_SECTIONS names (090-12-01), small."""
        if runner:
            write(self.root, ".agent/scripts/subagent_run.py", "# marker: the runner lives here\n")
        write(self.root, ".agent/rules/impl.md", "# Impl\n\n## Core\n- Core rule.\n\n## 1. Style\nx\n")
        write(self.root, ".agent/rules/delegation.md",
              "# D\n### Sub-agent limits\n- Limit.\n### Review checklist\n- Risk.\n## 9. Recording\nx\n")
        write(self.root, ".agent/rules/test.md", "# T\n## 2. C++ Testing (GoogleTest)\n- Test rule.\n## 3. Build\nx\n")
        write(self.root, "lessons/README.md", "# L\n## 레슨 작성 안내\n- 안내.\n")

    def bundle_errors(self) -> list[tuple[str, str]]:
        return [(f[1], f[3]) for f in lint_docs.lint(self.root).findings
                if f[0] == "ERROR" and ("RULE_SECTIONS" in f[3] or "limit" in f[3])]

    def test_rule_bundles_gate(self) -> None:
        # 090-12-01 AC-4: missing section, Core over 1.5 KB, a kind's block over 8 KB.
        self.assertEqual((lint_docs.CORE_LIMIT, lint_docs.RULE_BUNDLE_LIMIT), (1536, 8192))
        self.rule_bundle_fixture(runner=False)
        write(self.root, ".agent/rules/test.md", "# T\nno section\n")
        self.assertEqual(self.bundle_errors(), [])  # no runner in the tree: not checked
        self.rule_bundle_fixture()
        self.assertEqual(self.bundle_errors(), [])
        write(self.root, ".agent/rules/test.md", "# T\n## 2. Testing\nrenamed\n")
        self.assertEqual(self.bundle_errors(), [(
            ".agent/rules/test.md",
            "no '## 2. C++ Testing (GoogleTest)' section: subagent_run.py RULE_SECTIONS attaches it to sub-agent prompts (kind test)",
        )])
        self.rule_bundle_fixture()
        (self.root / "lessons/README.md").unlink()
        self.assertEqual([e[0] for e in self.bundle_errors()], ["lessons/README.md"])
        self.assertIn("file not found", self.bundle_errors()[0][1])
        # A common section breaks every kind but is reported once.
        self.rule_bundle_fixture()
        write(self.root, ".agent/rules/impl.md", "# Impl\n## 1. Style\nx\n")
        self.assertEqual(len(self.bundle_errors()), 1)
        # Core: 1536 bytes pass, 1537 fail.
        self.rule_bundle_fixture()
        head = "## Core\n"
        write(self.root, ".agent/rules/impl.md", "# Impl\n" + head + "x" * (1536 - len(head)) + "\n## 1. S\n")
        self.assertEqual(self.bundle_errors(), [])
        write(self.root, ".agent/rules/impl.md", "# Impl\n" + head + "x" * (1537 - len(head)) + "\n## 1. S\n")
        self.assertEqual(self.bundle_errors(), [(".agent/rules/impl.md", "'## Core' is 1537 bytes (limit 1536): every sub-agent prompt carries it")])
        # One kind's block over 8 KB: reported for that kind only.
        self.rule_bundle_fixture()
        write(self.root, ".agent/rules/test.md", "# T\n## 2. C++ Testing (GoogleTest)\n" + "t" * 8200 + "\n")
        errs = self.bundle_errors()
        self.assertEqual(len(errs), 1)
        self.assertEqual(errs[0][0], ".agent/rules/test.md")
        self.assertRegex(errs[0][1], r"^sub-agent rules for kind test are \d+ bytes \(limit 8192\)$")

    def test_boot_prints_core(self) -> None:
        # 090-12-01 AC-5: --boot prints the Core section after the todo header, before the states.
        self.assertNotIn("## Core", lint_docs.boot_text(self.root))  # no impl.md: nothing added
        self.rule_bundle_fixture()
        text = lint_docs.boot_text(self.root)
        self.assertIn("## Core\n- Core rule.\n\nstates:", text)
        self.assertNotIn("## 1. Style", text)
        self.assertLess(text.index("## Grammar"), text.index("## Core"))
        write(self.root, ".agent/rules/impl.md", "# Impl\n## 1. Style\n")
        self.assertIn("NOTE: no '## Core' in .agent/rules/impl.md", lint_docs.boot_text(self.root))

    def boot_ki_fixture(self, open_rows: int, deferred_rows: int = 0) -> None:
        rows = "".join(f"| KI-{i:03d} | OPEN | a | 010-02 | o |\n" for i in range(1, open_rows + 1))
        secs = "\n".join(f"## KI-{i:03d} — t{i}\nbody {i}\n" for i in range(1, open_rows + 1))
        write(self.root, "docs/known_issues.md",
              "# Known Issues\n\n| ID | Status | Area | Found | Owner |\n|---|---|---|---|---|\n" + rows + "\n" + secs)
        if deferred_rows:
            ids = range(500, 500 + deferred_rows)
            write(self.root, str(archive_docs.KI_DEFERRED), archive_docs.KI_DEFERRED_INITIAL
                  + "".join(f"| KI-{i:03d} | DEFERRED | a | 010-02 | — (when {i}) |\n" for i in ids) + "\n"
                  + "\n".join(f"## KI-{i:03d} — d{i}\ndeferred body {i}\n" for i in ids))

    def test_boot_contract_details(self) -> None:
        # Review fixes for U5: defaults and boundaries, item per limit, exact lines, CLI, gate.
        self.assertEqual(lint_docs.BUDGET, {"open_ki": 20, "deferred_ki": 30, "header_bytes": 5120, "boot_bytes": 16384})
        self.boot_ki_fixture(20, 30)
        self.assertEqual(lint_docs.budget_items(self.root), [])
        self.boot_ki_fixture(21, 31)
        self.assertEqual(lint_docs.budget_items(self.root), ["open KI 21/20", "DEFERRED 31/30"])
        text = lint_docs.boot_text(self.root)
        lines = text.splitlines()
        self.assertEqual(lines[0], "BUDGET: open KI 21/20; DEFERRED 31/30: triage before the next task")
        # Order: header -> states -> KI table (both header lines) -> DEFERRED line; no preamble, no group heading.
        order = [text.index(s) for s in ("## Grammar", "states:", "| ID | Status |", "|---|", "| KI-001 |", "DEFERRED: 31 in docs/known_issues_deferred.md (check its Area column for the area you change)")]
        self.assertEqual(order, sorted(order))
        self.assertNotIn("# Known Issues\n", text)
        self.assertNotIn("## Phase 1", text)
        self.assertNotIn("body 1", text)
        # The CLI prints the same text.
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(lint_docs.main(["--root", str(self.root), "--boot"]), 0)
        self.assertEqual(out.getvalue().rstrip("\n"), text.rstrip("\n"))
        # --deferred: table only.
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            lint_docs.main(["--root", str(self.root), "--deferred"])
        self.assertIn("| KI-500 | DEFERRED |", out.getvalue())
        self.assertNotIn("deferred body", out.getvalue())
        self.assertNotIn("Deferred known issues:", out.getvalue())
        # --ki prints the body of each id asked for.
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(lint_docs.main(["--root", str(self.root), "--ki", "KI-001", "KI-500"]), 0)
        self.assertIn("body 1\n", out.getvalue())
        self.assertIn("deferred body 500", out.getvalue())
        # The gate does not change with the limits: baseline within every limit, then each limit broken.
        self.boot_ki_fixture(1, 1)
        self.assertEqual(lint_docs.budget_items(self.root), [])
        clean = sorted(lint_docs.lint(self.root).findings)
        with patch.dict(lint_docs.BUDGET, {"open_ki": 0, "deferred_ki": 0, "header_bytes": 1, "boot_bytes": 1}):
            self.assertEqual([i.split(" ")[0] for i in lint_docs.budget_items(self.root)], ["open", "DEFERRED", "todo", "boot"])
            self.assertEqual(sorted(lint_docs.lint(self.root).findings), clean)
        todo = (self.root / "docs/agent_todo.md").read_text(encoding="utf-8")
        write(self.root, "docs/agent_todo.md", todo.replace("## Grammar\n", "## Grammar\n- ~~010-01 old~~ (DONE 2026-11-01).\n", 1))
        self.assertEqual(lint_docs.budget_items(self.root), ["finished items in the todo header (~~…~~ (DONE …))"])
        without_lines = lambda findings: sorted((f[0], f[1], f[3]) for f in findings)  # the added line shifts line numbers
        self.assertEqual(without_lines(lint_docs.lint(self.root).findings), without_lines(clean))

    def test_boot_header_size_counts_only_the_header(self) -> None:
        header = TODO.split("---", 1)[0]
        write(self.root, "docs/agent_todo.md", TODO + "".join(f"- !BACKLOG | 010-{i:02d} | filler {'x' * 80}\n" for i in range(3, 60)))
        write(self.root, "docs/agent_todo.md", (self.root / "docs/agent_todo.md").read_text(encoding="utf-8").replace("(1/2 DONE)", "(1/59 DONE)"))
        with patch.dict(lint_docs.BUDGET, {"header_bytes": len(header.encode("utf-8"))}):  # exactly at the limit is fine
            self.assertEqual(lint_docs.budget_items(self.root), [])
        with patch.dict(lint_docs.BUDGET, {"header_bytes": len(header.encode("utf-8")) - 1}):
            self.assertEqual([i.split(" ")[1] for i in lint_docs.budget_items(self.root)], ["header"])

    def test_boot_note_without_separator_is_exact(self) -> None:
        write(self.root, "docs/agent_todo.md", "# Tasks\nno separator here\n")
        self.assertEqual(lint_docs.boot_text(self.root).splitlines()[0], "NOTE: no '---' in docs/agent_todo.md; printed the whole file")
        with patch.dict(lint_docs.BUDGET, {"open_ki": 0}):  # the NOTE stays first, BUDGET follows
            lines = lint_docs.boot_text(self.root).splitlines()
            self.assertTrue(lines[0].startswith("NOTE: no '---'") and lines[1].startswith("BUDGET: open KI 1/0"), lines[:2])
        # An indented '---' is the boundary, as for parse_todo.
        write(self.root, "docs/agent_todo.md", TODO.replace("\n---\n", "\n  ---\n"))
        self.assertFalse(lint_docs.boot_text(self.root).startswith("NOTE"))

    def test_boot_views_never_raise_on_a_broken_ki_file(self) -> None:
        write(self.root, str(archive_docs.KI_CLOSED), archive_docs.KI_CLOSED_INITIAL + "| KI-005 | CLOSED | a | x | o |\nstray\n## KI-005 — x\nt\n")
        write(self.root, str(archive_docs.KI_DEFERRED), "# no table\n")
        write(self.root, "docs/known_issues.md", KNOWN.replace("| KI-001 | OPEN |", "| KI-001 | OPNE |"))
        text = lint_docs.boot_text(self.root)
        self.assertIn("| KI-001 | OPNE |", text)  # an unknown status stays visible
        self.assertIn("NOTE: docs/archive/known_issues_closed.md unparsable", text)
        for argv, code in ((["--ki", "KI-001"], 0), (["--deferred"], 1)):
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                self.assertEqual(lint_docs.main(["--root", str(self.root), *argv]), code, argv)
            self.assertIn("unparsable", out.getvalue() + err.getvalue(), argv)

    def test_archive_unreadable_todo_body_is_an_error(self) -> None:
        # A todo archive_docs.py refuses is reported, not silently left without the movable-DONE WARN.
        write(self.root, "docs/agent_todo.md", TODO.replace("- !APPROVED | 010-02", "\n  - !DEV | 010-01-01 | p\n- !APPROVED | 010-02"))
        self.assertTrue(any("archive_docs.py cannot read" in e for e in self.errors()))
        # An archive task before its first heading.
        write(self.root, str(archive_docs.TODO_DONE), archive_docs.TODO_DONE_INITIAL + "\n- !DONE | 010-09 | stray\n")
        self.assertTrue(any("before the first '## ' group heading" in e for e in self.errors()))

    def test_archive_ki_file_checks_own_table_section_pairs(self) -> None:
        # Case 12: Each KI file checks table/section pairs (missing section in KI_CLOSED is ERROR)
        closed_text = archive_docs.KI_CLOSED_INITIAL + (
            "| KI-002 | CLOSED | Area | 010-02 | — |\n"
        )
        write(self.root, str(archive_docs.KI_CLOSED), closed_text)
        # Its section sits in the other file: only a per-file pair check reports it.
        write(self.root, "docs/known_issues.md", KNOWN + "\n## KI-002 — elsewhere\ntext\n")
        errs = self.errors()
        self.assertTrue(any("has no '## KI-002' section" in e for e in errs))

    def test_boot_ac1_header_status_and_open_planned_rows(self) -> None:
        # Case 1 (AC-1): boot_text contains header marker, states:, OPEN and PLANNED rows, table header;
        # does not contain task lines from groups, CLOSED row, or ## KI- sections.
        marker = "MARKER_BOOT_HEADER_LINE_AC1"
        todo_text = (
            f"# Tasks\n\n{marker}\n\n## Grammar\n- Task line: `- !STATE | NNN-SS | Title`\n\n---\n\n"
            "## Phase 1 (1/2 DONE)\n"
            "- !DONE | 010-01 | [Old](/docs/specs/01_old.md) — legacy\n"
            "- !APPROVED | 010-02 | [New](/docs/specs/010_02_new.md)\n"
        )
        write(self.root, "docs/agent_todo.md", todo_text)

        ki_text = (
            "# Known Issues\n\n"
            "| ID | Status | Area | Found | Owner |\n"
            "|---|---|---|---|---|\n"
            "| KI-001 | OPEN | Area1 | 010-02 | — |\n"
            "| KI-002 | PLANNED | Area2 | 010-02 | — |\n"
            "| KI-003 | CLOSED | Area3 | 010-02 | — |\n\n"
            "## KI-001 — first open\nSection 1 open text\n\n"
            "## KI-002 — second planned\nSection 2 planned text\n\n"
            "## KI-003 — third closed\nSection 3 closed text\n"
        )
        write(self.root, "docs/known_issues.md", ki_text)

        boot = lint_docs.boot_text(self.root)

        # Expected inclusions
        self.assertIn(marker, boot)
        self.assertTrue(any(line.startswith("states:") for line in boot.splitlines()))
        self.assertIn("| ID | Status | Area | Found | Owner |", boot)
        self.assertIn("| KI-001 | OPEN | Area1 | 010-02 | — |", boot)
        self.assertIn("| KI-002 | PLANNED | Area2 | 010-02 | — |", boot)

        # Expected exclusions
        self.assertNotIn("- !DONE | 010-01 | [Old](/docs/specs/01_old.md) — legacy", boot)
        self.assertNotIn("- !APPROVED | 010-02 | [New](/docs/specs/010_02_new.md)", boot)
        self.assertNotIn("| KI-003 | CLOSED | Area3 | 010-02 | — |", boot)
        self.assertNotIn("## KI-001", boot)
        self.assertNotIn("## KI-002", boot)
        self.assertNotIn("## KI-003", boot)
        self.assertNotIn("Section 1 open text", boot)
        self.assertNotIn("Section 2 planned text", boot)
        self.assertNotIn("Section 3 closed text", boot)

    def test_boot_ac4a_deferred_summary_and_cli(self) -> None:
        # Case 2 (AC-4a): deferred file holding two DEFERRED rows -> boot_text has no DEFERRED row
        # but a line starting 'DEFERRED: 2 in docs/known_issues_deferred.md'; --deferred prints both rows
        # and table header; without deferred file --deferred prints 'no deferred KIs'.
        deferred_text = archive_docs.KI_DEFERRED_INITIAL + (
            "| KI-010 | DEFERRED | Area A | 010-02 | — (condition A) |\n"
            "| KI-011 | DEFERRED | Area B | 010-02 | — (condition B) |\n\n"
            "## KI-010 — def 1\nDeferred section 10\n\n"
            "## KI-011 — def 2\nDeferred section 11\n"
        )
        write(self.root, str(archive_docs.KI_DEFERRED), deferred_text)

        boot = lint_docs.boot_text(self.root)
        self.assertNotIn("| KI-010 |", boot)
        self.assertNotIn("| KI-011 |", boot)
        self.assertTrue(any(line.startswith("DEFERRED: 2 in docs/known_issues_deferred.md") for line in boot.splitlines()))

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            ret = lint_docs.main(["--root", str(self.root), "--deferred"])
        self.assertEqual(ret, 0)
        out = buf.getvalue()
        self.assertIn("| ID | Status | Area | Found | Owner |", out)
        self.assertIn("| KI-010 | DEFERRED | Area A | 010-02 | — (condition A) |", out)
        self.assertIn("| KI-011 | DEFERRED | Area B | 010-02 | — (condition B) |", out)

        (self.root / archive_docs.KI_DEFERRED).unlink()
        buf_missing = io.StringIO()
        with contextlib.redirect_stdout(buf_missing):
            ret_missing = lint_docs.main(["--root", str(self.root), "--deferred"])
        self.assertEqual(ret_missing, 0)
        self.assertIn("no deferred KIs", buf_missing.getvalue())

    def test_boot_ac2_ki_sections_cli_and_errors(self) -> None:
        # Case 3 (AC-2): --ki KI-001 KI-003 prints both sections and exit 0;
        # duplicate ID prints section once; missing ID prints found sections, missing ID on stderr, exit 1.
        closed_text = archive_docs.KI_CLOSED_INITIAL + (
            "| KI-003 | CLOSED | Area | 010-02 | — |\n\n"
            "## KI-003 — third closed\nClosed body text 3\n"
        )
        write(self.root, str(archive_docs.KI_CLOSED), closed_text)

        # 1. Multiple valid KIs across files
        buf_out = io.StringIO()
        buf_err = io.StringIO()
        with contextlib.redirect_stdout(buf_out), contextlib.redirect_stderr(buf_err):
            ret = lint_docs.main(["--root", str(self.root), "--ki", "KI-001", "KI-003"])
        self.assertEqual(ret, 0)
        self.assertEqual(buf_err.getvalue(), "")
        out = buf_out.getvalue()
        self.assertIn("## KI-001 — first", out)
        self.assertIn("text", out)
        self.assertIn("## KI-003 — third closed", out)
        self.assertIn("Closed body text 3", out)

        # 2. Duplicate argument prints section once
        buf_dup = io.StringIO()
        buf_dup_err = io.StringIO()
        with contextlib.redirect_stdout(buf_dup), contextlib.redirect_stderr(buf_dup_err):
            ret_dup = lint_docs.main(["--root", str(self.root), "--ki", "KI-001", "KI-001"])
        self.assertEqual(ret_dup, 0)
        self.assertEqual(buf_dup_err.getvalue(), "")
        out_dup = buf_dup.getvalue()
        self.assertEqual(out_dup.count("## KI-001 — first"), 1)
        self.assertEqual(out_dup.count("text"), 1)

        # 3. Missing KI exits 1, prints found section on stdout and missing ID on stderr
        buf_missing_out = io.StringIO()
        buf_missing_err = io.StringIO()
        with contextlib.redirect_stdout(buf_missing_out), contextlib.redirect_stderr(buf_missing_err):
            ret_missing = lint_docs.main(["--root", str(self.root), "--ki", "KI-001", "KI-099"])
        self.assertEqual(ret_missing, 1)
        self.assertIn("## KI-001 — first", buf_missing_out.getvalue())
        self.assertIn("text", buf_missing_out.getvalue())
        self.assertIn("KI-099", buf_missing_err.getvalue())

    def test_boot_ac3_no_separator_prints_whole_todo_with_note(self) -> None:
        # Case 4 (AC-3): todo without '---' line: boot_text starts with a line beginning NOTE: and contains whole todo.
        todo_no_sep = "# Tasks\n\nGrammar notes and no separator\n- !DEV | 010-02 | Spec\n"
        write(self.root, "docs/agent_todo.md", todo_no_sep)

        boot = lint_docs.boot_text(self.root)
        first_line = boot.splitlines()[0]
        self.assertTrue(first_line.startswith("NOTE:"))
        self.assertIn(todo_no_sep.strip(), boot)

    def test_boot_ac4_budget_limits_and_clean_state(self) -> None:
        # Case 5 (AC-4 limits): each limit tested separately; first line starts with BUDGET:
        # and ends with 'triage before the next task', budget_items has exactly one item.
        # Within limits: no BUDGET: line, budget_items is [].
        self.assertEqual(lint_docs.budget_items(self.root), [])
        clean_boot = lint_docs.boot_text(self.root)
        self.assertFalse(clean_boot.startswith("BUDGET:"))
        self.assertNotIn("triage before the next task", clean_boot)

        def assert_single_budget_breach(desc: str) -> None:
            items = lint_docs.budget_items(self.root)
            self.assertEqual(len(items), 1, f"Expected 1 item for {desc}, got {items}")
            boot = lint_docs.boot_text(self.root)
            first_line = boot.splitlines()[0]
            self.assertTrue(first_line.startswith("BUDGET:"), f"Expected BUDGET: prefix for {desc}, got: {first_line}")
            self.assertTrue(first_line.endswith("triage before the next task"), f"Expected suffix for {desc}, got: {first_line}")
            self.assertIn(items[0], first_line)

        # 1. open KI over limit
        ki_with_two_open = (
            "# Known Issues\n\n"
            "| ID | Status | Area | Found | Owner |\n"
            "|---|---|---|---|---|\n"
            "| KI-001 | OPEN | x | 010-02 | — |\n"
            "| KI-002 | PLANNED | y | 010-02 | — |\n\n"
            "## KI-001 — first\ntext 1\n\n"
            "## KI-002 — second\ntext 2\n"
        )
        write(self.root, "docs/known_issues.md", ki_with_two_open)
        with patch.dict(lint_docs.BUDGET, {"open_ki": 1}):
            assert_single_budget_breach("open KI over limit")

        # Restore known_issues.md
        write(self.root, "docs/known_issues.md", KNOWN)

        # 2. deferred over limit
        deferred_text = archive_docs.KI_DEFERRED_INITIAL + (
            "| KI-010 | DEFERRED | Area | 010-02 | — (cond) |\n\n"
            "## KI-010 — def\ntext\n"
        )
        write(self.root, str(archive_docs.KI_DEFERRED), deferred_text)
        with patch.dict(lint_docs.BUDGET, {"deferred_ki": 0}):
            assert_single_budget_breach("deferred over limit")

        # Remove deferred file
        (self.root / archive_docs.KI_DEFERRED).unlink()

        # 3. header over header_bytes
        with patch.dict(lint_docs.BUDGET, {"header_bytes": 10}):
            assert_single_budget_breach("header over header_bytes")

        # 4. header line with ~~010-01 x~~ (DONE 2026-11-01)
        todo_with_done_in_header = (
            "# Tasks\n\n"
            "- ~~010-01 x~~ (DONE 2026-11-01)\n\n"
            "## Grammar\n- Task line: `- !STATE | NNN-SS | Title`\n\n---\n\n"
            "## Phase 1 (1/2 DONE)\n"
            "- !DONE | 010-01 | [Old](/docs/specs/01_old.md) — legacy\n"
            "- !APPROVED | 010-02 | [New](/docs/specs/010_02_new.md)\n"
        )
        write(self.root, "docs/agent_todo.md", todo_with_done_in_header)
        assert_single_budget_breach("completed item in progression order")

        # Restore agent_todo.md
        write(self.root, "docs/agent_todo.md", TODO)

        # 5. total over boot_bytes
        with patch.dict(lint_docs.BUDGET, {"boot_bytes": 20}):
            assert_single_budget_breach("total over boot_bytes")

    def test_boot_ac4_gate_budget_limits_not_in_lint_findings(self) -> None:
        # Case 6 (AC-4 gate): with limits exceeded, lint_docs.lint(root) findings
        # contain nothing mentioning BUDGET or the limit.
        todo_with_done_in_header = (
            "# Tasks\n\n"
            "- ~~010-01 x~~ (DONE 2026-11-01)\n\n"
            "## Grammar\n- Task line: `- !STATE | NNN-SS | Title`\n\n---\n\n"
            "## Phase 1 (1/2 DONE)\n"
            "- !DONE | 010-01 | [Old](/docs/specs/01_old.md) — legacy\n"
            "- !APPROVED | 010-02 | [New](/docs/specs/010_02_new.md)\n"
        )
        write(self.root, "docs/agent_todo.md", todo_with_done_in_header)
        deferred_text = archive_docs.KI_DEFERRED_INITIAL + (
            "| KI-010 | DEFERRED | Area | 010-02 | — (condition) |\n\n"
            "## KI-010 — def\ntext\n"
        )
        write(self.root, str(archive_docs.KI_DEFERRED), deferred_text)
        with patch.dict(lint_docs.BUDGET, {"open_ki": 0, "deferred_ki": 0, "header_bytes": 1, "boot_bytes": 1}):
            report = lint_docs.lint(self.root)
        finding_messages = [f[3] for f in report.findings]
        self.assertFalse(any("budget" in m.lower() for m in finding_messages))
        self.assertFalse(any("limit" in m.lower() for m in finding_messages))

    def write_rule(self, name: str, frontmatter: dict[str, str] | None = None, body: str = "") -> Path:
        rel = f".agent/rules/{name}" if name.endswith(".md") else f".agent/rules/{name}.md"
        if frontmatter is None:
            text = body
        else:
            fm_lines = ["---"] + [f"{k}: {v}" for k, v in frontmatter.items()] + ["---"]
            text = "\n".join(fm_lines) + "\n" + body
        return write(self.root, rel, text)

    def rule_findings(self, level: str = "ERROR") -> list[tuple[str, int, str]]:
        return [(f[1], f[2], f[3]) for f in lint_docs.lint(self.root).findings
                if f[0] == level and (f[1].startswith(".agent/rules") or f[1] == "docs/agent_start_prompt.md")]

    def test_rules_review_gaps(self) -> None:
        # Review fixes for U1 (090-09): empty values, no trigger key, bytes not characters,
        # name order, links only (not prose or code), line 1, missing boot prompt message.
        md = {"trigger": "model_decision", "description": "d"}
        self.write_rule("b_rule", md)
        self.write_rule("c_rule", md)
        self.write_boot_prompt(["b_rule", "c_rule"])
        self.assertEqual(self.rule_findings(), [])
        cases = {
            "empty description": ({"trigger": "model_decision", "description": ""}, "requires description"),
            "empty globs": ({"trigger": "glob", "globs": ""}, "requires globs"),
            "no trigger key": ({"description": "d"}, "must be one of"),
        }
        for name, (fm, word) in cases.items():
            with self.subTest(name):
                self.write_rule("a_case", fm)
                hits = [f for f in self.rule_findings() if f[0] == ".agent/rules/a_case.md" and "trigger table" not in f[2]]
                self.assertEqual(len(hits), 1, hits)
                self.assertIn(word, hits[0][2])
                (self.root / ".agent/rules/a_case.md").unlink()
        # 400 Hangul characters = 1200 UTF-8 bytes: over the limit in bytes, under it in characters.
        self.write_rule("x_on", {"trigger": "always_on"}, "가" * 400)
        warns = [f for f in self.rule_findings("WARN") if f[0] == ".agent/rules/x_on.md"]
        self.assertEqual(len(warns), 1)
        self.assertIn("1200 bytes", warns[0][2])
        # Name order decides "the second": written z first, a later; three files.
        (self.root / ".agent/rules/x_on.md").unlink()
        for name in ("z_on", "m_on", "a_on"):
            self.write_rule(name, {"trigger": "always_on"}, "short\n")
        dup = sorted((f[0], f[2]) for f in self.rule_findings() if "only one always_on" in f[2])
        self.assertEqual(dup, [(".agent/rules/m_on.md", "only one always_on rule (first: a_on.md)"),
                               (".agent/rules/z_on.md", "only one always_on rule (first: a_on.md)")])
        for name in ("z_on", "m_on", "a_on"):
            (self.root / f".agent/rules/{name}.md").unlink()
        # A rule named in prose or inside code, but not linked, is not in the table.
        boot = self.root / "docs/agent_start_prompt.md"
        boot.write_text(boot.read_text(encoding="utf-8").replace("[`.agent/rules/c_rule.md`](/.agent/rules/c_rule.md)", "c_rule.md")
                        + "\n```\n[x](/.agent/rules/c_rule.md)\n```\n", encoding="utf-8")
        self.assertEqual(self.rule_findings(), [(".agent/rules/c_rule.md", 1, "not linked from the trigger table in docs/agent_start_prompt.md")])
        # A broken table link: only the existing broken-link ERROR, no new message.
        self.write_boot_prompt(["b_rule", "c_rule", "gone"])
        self.assertEqual([f[2] for f in self.rule_findings()], ["broken link /.agent/rules/gone.md"])
        # No boot prompt, two model_decision rules: exactly one ERROR, the missing-file one.
        boot.unlink()
        self.assertEqual([f[2] for f in self.rule_findings()], ["boot prompt not found: docs/agent_start_prompt.md"])

    def write_boot_prompt(self, rule_names: list[str]) -> Path:
        rows = [
            f"| Trigger {name} | [`.agent/rules/{name if name.endswith('.md') else name + '.md'}`](/.agent/rules/{name if name.endswith('.md') else name + '.md'}) |"
            for name in rule_names
        ]
        table = "\n".join(rows)
        content = (
            "# Agent Boot Sequence\n\n"
            "| Trigger | Rule |\n"
            "|---|---|\n"
            f"{table}\n"
        )
        return write(self.root, "docs/agent_start_prompt.md", content)

    def test_rules_clean_set(self) -> None:
        # Case 1: clean set of rules and boot prompt table
        self.write_rule("boot.md", {"trigger": "always_on"}, "Before anything else, follow docs/agent_start_prompt.md.\n")
        self.write_rule("spec.md", {"trigger": "model_decision", "description": "When writing or amending a spec"}, "Spec rule body.\n")
        self.write_rule("impl.md", {"trigger": "model_decision", "description": "When composing the code"}, "Impl rule body.\n")
        self.write_boot_prompt(["spec.md", "impl.md"])
        report = lint_docs.lint(self.root)
        rule_findings = [
            f for f in report.findings
            if f[0] in ("ERROR", "WARN") and (f[1].startswith(".agent/rules") or f[1].startswith("docs/agent_start_prompt.md"))
        ]
        self.assertEqual(rule_findings, [])

    def test_rules_ac2_frontmatter_validation(self) -> None:
        # Case 2: frontmatter rules and triggers validation
        self.write_rule("bad_trigger.md", {"trigger": "sometimes"}, "Body.\n")
        self.write_rule("no_frontmatter.md", frontmatter=None, body="# Rule without frontmatter\n")
        self.write_rule("no_desc.md", {"trigger": "model_decision"}, "Body.\n")
        self.write_rule("no_globs.md", {"trigger": "glob"}, "Body.\n")
        self.write_rule("valid_glob.md", {"trigger": "glob", "globs": "src/**"}, "Body.\n")
        report = lint_docs.lint(self.root)
        self.assertTrue(any(f[0] == "ERROR" and f[1] == ".agent/rules/bad_trigger.md" and "must be one of" in f[3] for f in report.findings))
        self.assertTrue(any(f[0] == "ERROR" and f[1] == ".agent/rules/no_frontmatter.md" and "no frontmatter" in f[3] for f in report.findings))
        self.assertTrue(any(f[0] == "ERROR" and f[1] == ".agent/rules/no_desc.md" and "description" in f[3] for f in report.findings))
        self.assertTrue(any(f[0] == "ERROR" and f[1] == ".agent/rules/no_globs.md" and "globs" in f[3] for f in report.findings))
        self.assertFalse(any(f[0] == "ERROR" and f[1] == ".agent/rules/valid_glob.md" for f in report.findings))

    def test_rules_ac2_two_always_on(self) -> None:
        # Case 3: multiple always_on rules error on second onwards
        self.write_rule("a_boot.md", {"trigger": "always_on"}, "First always_on rule.\n")
        self.write_rule("z_boot.md", {"trigger": "always_on"}, "Second always_on rule.\n")
        report = lint_docs.lint(self.root)
        dup_errors = [
            f for f in report.findings
            if f[0] == "ERROR" and "only one always_on" in f[3]
        ]
        self.assertEqual(len(dup_errors), 1)
        self.assertEqual(dup_errors[0][1], ".agent/rules/z_boot.md")
        self.assertFalse(any(f[1] == ".agent/rules/a_boot.md" and "only one always_on" in f[3] for f in report.findings))

    def test_rules_ac2_always_on_body_byte_limit(self) -> None:
        # Case 4: always_on body byte limit warning (1025 warns, 1024 does not)
        body_1025 = "a" * 1025
        self.write_rule("boot.md", {"trigger": "always_on"}, body_1025)
        report_over = lint_docs.lint(self.root)
        warns_1025 = [
            f for f in report_over.findings
            if f[0] == "WARN" and f[1] == ".agent/rules/boot.md" and "1024" in f[3]
        ]
        self.assertEqual(len(warns_1025), 1)

        body_1024 = "a" * 1024
        self.write_rule("boot.md", {"trigger": "always_on"}, body_1024)
        report_limit = lint_docs.lint(self.root)
        warns_1024 = [
            f for f in report_limit.findings
            if f[0] == "WARN" and f[1] == ".agent/rules/boot.md" and "1024" in f[3]
        ]
        self.assertEqual(warns_1024, [])

    def test_rules_ac3_trigger_table_missing_rule(self) -> None:
        # Case 5: model_decision rule missing from trigger table is an ERROR
        self.write_rule("rule_a.md", {"trigger": "model_decision", "description": "rule a"}, "Rule A body.\n")
        self.write_rule("rule_b.md", {"trigger": "model_decision", "description": "rule b"}, "Rule B body.\n")
        self.write_rule("boot.md", {"trigger": "always_on"}, "Boot body.\n")
        self.write_boot_prompt(["rule_a.md"])

        report1 = lint_docs.lint(self.root)
        errs_b = [
            f for f in report1.findings
            if f[0] == "ERROR" and f[1] == ".agent/rules/rule_b.md" and "trigger table" in f[3]
        ]
        self.assertEqual(len(errs_b), 1)

        errs_boot = [
            f for f in report1.findings
            if f[0] == "ERROR" and f[1] == ".agent/rules/boot.md" and "trigger table" in f[3]
        ]
        self.assertEqual(errs_boot, [])

        self.write_boot_prompt(["rule_a.md", "rule_b.md"])
        report2 = lint_docs.lint(self.root)
        errs_b_fixed = [
            f for f in report2.findings
            if f[0] == "ERROR" and f[1] == ".agent/rules/rule_b.md" and "trigger table" in f[3]
        ]
        self.assertEqual(errs_b_fixed, [])

    def test_rules_ac3_trigger_table_broken_link(self) -> None:
        # Case 6: table link pointing to non-existent rule gives broken link ERROR
        self.write_boot_prompt(["gone.md"])
        report = lint_docs.lint(self.root)
        broken = [
            f for f in report.findings
            if f[0] == "ERROR" and f[1] == "docs/agent_start_prompt.md" and "broken link" in f[3] and "gone.md" in f[3]
        ]
        self.assertEqual(len(broken), 1)

    def test_rules_ac3_missing_boot_prompt(self) -> None:
        # Case 7: model_decision rule without docs/agent_start_prompt.md is an ERROR
        self.write_rule("spec.md", {"trigger": "model_decision", "description": "When writing a spec"}, "Spec rule body.\n")
        report = lint_docs.lint(self.root)
        errs = [
            f for f in report.findings
            if f[0] == "ERROR" and ("docs/agent_start_prompt.md" in f[1] or "docs/agent_start_prompt.md" in f[3])
        ]
        self.assertEqual(len(errs), 1)


ARCH_KI_PREAMBLE = """\
# Known Issues & Follow-ups

| ID | Status | Area | Found | Owner |
|---|---|---|---|---|
"""

ARCH_TODO = """\
# Tasks

## Grammar
- Task line: `- !STATE | NNN-SS | Title`

---

## Phase 1 (1/2 DONE)
- !DONE | 010-01 | Old task
- !DEV | 010-02 | New task
"""


class ArchiveDocsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_ki_closed_and_deferred_move_to_respective_files(self) -> None:
        ki_text = ARCH_KI_PREAMBLE + (
            "| KI-001 | OPEN | Area | 010-01 | Owner |\n"
            "| KI-002 | CLOSED | Area | 010-01 | Owner |\n"
            "| KI-003 | DEFERRED | Area | 010-01 | Owner |\n"
            "| KI-004 | CLOSED | Area | 010-01 | Owner |\n"
            "| KI-005 | DEFERRED | Area | 010-01 | Owner |\n"
            "| KI-006 | OPEN | Area | 010-01 | Owner |\n\n"
            "## KI-001 — issue 1\nSection 1 text\n\n"
            "## KI-002 — issue 2\nSection 2 text\n\n"
            "## KI-003 — issue 3\nSection 3 text\n\n"
            "## KI-004 — issue 4\nSection 4 text\n\n"
            "## KI-005 — issue 5\nSection 5 text\n\n"
            "## KI-006 — issue 6\nSection 6 text\n"
        )
        write(self.root, str(archive_docs.KNOWN_ISSUES), ki_text)
        write(self.root, str(archive_docs.TODO), ARCH_TODO)

        moves = archive_docs.apply(self.root)
        self.assertEqual(sorted(m for m in moves if m[0].startswith("KI-")), [
            ("KI-002", archive_docs.KNOWN_ISSUES, archive_docs.KI_CLOSED),
            ("KI-003", archive_docs.KNOWN_ISSUES, archive_docs.KI_DEFERRED),
            ("KI-004", archive_docs.KNOWN_ISSUES, archive_docs.KI_CLOSED),
            ("KI-005", archive_docs.KNOWN_ISSUES, archive_docs.KI_DEFERRED),
        ])

        closed_path = self.root / archive_docs.KI_CLOSED
        deferred_path = self.root / archive_docs.KI_DEFERRED
        known_path = self.root / archive_docs.KNOWN_ISSUES

        self.assertTrue(closed_path.is_file())
        self.assertTrue(deferred_path.is_file())

        known_txt = known_path.read_text(encoding="utf-8")
        closed_txt = closed_path.read_text(encoding="utf-8")
        def_txt = deferred_path.read_text(encoding="utf-8")

        # OPEN ones stay
        self.assertIn("| KI-001 |", known_txt)
        self.assertIn("## KI-001 — issue 1", known_txt)
        self.assertIn("| KI-006 |", known_txt)
        self.assertIn("## KI-006 — issue 6", known_txt)
        for ki_id in ("KI-002", "KI-003", "KI-004", "KI-005"):
            self.assertNotIn(f"| {ki_id} |", known_txt)
            self.assertNotIn(f"## {ki_id} ", known_txt)

        # CLOSED ones moved
        self.assertIn("| KI-002 |", closed_txt)
        self.assertIn("## KI-002 — issue 2", closed_txt)
        self.assertIn("| KI-004 |", closed_txt)
        self.assertIn("## KI-004 — issue 4", closed_txt)
        for ki_id in ("KI-001", "KI-003", "KI-005", "KI-006"):
            self.assertNotIn(f"| {ki_id} |", closed_txt)
            self.assertNotIn(f"## {ki_id} ", closed_txt)

        # DEFERRED ones moved
        self.assertIn("| KI-003 |", def_txt)
        self.assertIn("## KI-003 — issue 3", def_txt)
        self.assertIn("| KI-005 |", def_txt)
        self.assertIn("## KI-005 — issue 5", def_txt)
        for ki_id in ("KI-001", "KI-002", "KI-004", "KI-006"):
            self.assertNotIn(f"| {ki_id} |", def_txt)
            self.assertNotIn(f"## {ki_id} ", def_txt)

        # Each moved section text appears exactly once across all files
        all_text = known_txt + closed_txt + def_txt
        for i in range(1, 7):
            self.assertEqual(all_text.count(f"Section {i} text"), 1)
            self.assertEqual(all_text.count(f"| KI-00{i} |"), 1)
        # New files start with their preamble and the table header.
        self.assertTrue(closed_txt.startswith(archive_docs.KI_CLOSED_INITIAL))
        self.assertTrue(def_txt.startswith(archive_docs.KI_DEFERRED_INITIAL))

        # IDs inside each file are in ascending order
        self.assertLess(known_txt.index("| KI-001 |"), known_txt.index("| KI-006 |"))
        self.assertLess(known_txt.index("## KI-001"), known_txt.index("## KI-006"))
        self.assertLess(closed_txt.index("| KI-002 |"), closed_txt.index("| KI-004 |"))
        self.assertLess(closed_txt.index("## KI-002"), closed_txt.index("## KI-004"))
        self.assertLess(def_txt.index("| KI-003 |"), def_txt.index("| KI-005 |"))
        self.assertLess(def_txt.index("## KI-003"), def_txt.index("## KI-005"))

    def test_ki_deferred_edited_to_open_moves_back_to_known_issues(self) -> None:
        known_text = ARCH_KI_PREAMBLE + (
            "| KI-001 | OPEN | Area | 010-01 | Owner |\n"
            "| KI-003 | OPEN | Area | 010-01 | Owner |\n\n"
            "## KI-001 — issue 1\nSection 1 text\n\n"
            "## KI-003 — issue 3\nSection 3 text\n"
        )
        deferred_text = ARCH_KI_PREAMBLE + (
            "| KI-002 | OPEN | Area | 010-01 | Owner |\n\n"
            "## KI-002 — issue 2\nSection 2 text\n"
        )
        write(self.root, str(archive_docs.KNOWN_ISSUES), known_text)
        write(self.root, str(archive_docs.KI_DEFERRED), deferred_text)
        write(self.root, str(archive_docs.TODO), ARCH_TODO)

        moves = archive_docs.apply(self.root)
        self.assertIn(("KI-002", archive_docs.KI_DEFERRED, archive_docs.KNOWN_ISSUES), moves)

        known_txt = (self.root / archive_docs.KNOWN_ISSUES).read_text(encoding="utf-8")
        def_path = self.root / archive_docs.KI_DEFERRED
        self.assertNotIn("KI-002", def_path.read_text(encoding="utf-8"))

        self.assertIn("| KI-002 |", known_txt)
        self.assertIn("## KI-002 — issue 2", known_txt)

        # Rows in id order between existing rows
        idx_r1 = known_txt.index("| KI-001 |")
        idx_r2 = known_txt.index("| KI-002 |")
        idx_r3 = known_txt.index("| KI-003 |")
        self.assertLess(idx_r1, idx_r2)
        self.assertLess(idx_r2, idx_r3)

        # Sections in id order
        idx_s1 = known_txt.index("## KI-001")
        idx_s2 = known_txt.index("## KI-002")
        idx_s3 = known_txt.index("## KI-003")
        self.assertLess(idx_s1, idx_s2)
        self.assertLess(idx_s2, idx_s3)

    def test_todo_done_moves_to_archive_while_heading_and_partial_patches_stay(self) -> None:
        todo_text = """\
        # Tasks

        ## Grammar
        - Task line: `- !STATE | NNN-SS | Title`

        ---

        ## Phase 1 (1/2 DONE)
        - !DONE | 010-01 | First finished task
        - !DONE | 010-02 | Second task with pending patch
          - !DEV | 010-02-01 | Incomplete patch

        ## Phase 2 (1/1 DONE)
        - !DONE | 020-01 | Phase 2 finished task
        """
        write(self.root, str(archive_docs.TODO), todo_text)
        write(self.root, str(archive_docs.KNOWN_ISSUES), ARCH_KI_PREAMBLE + "| KI-001 | OPEN | Area | 010-01 | Owner |\n\n## KI-001 — issue 1\nDetails 1\n")

        moves = archive_docs.apply(self.root)
        self.assertIn(("010-01", archive_docs.TODO, archive_docs.TODO_DONE), moves)
        self.assertIn(("020-01", archive_docs.TODO, archive_docs.TODO_DONE), moves)
        moved_ids = [m[0] for m in moves]
        self.assertNotIn("010-02", moved_ids)
        self.assertNotIn("010-02-01", moved_ids)

        todo_txt = (self.root / archive_docs.TODO).read_text(encoding="utf-8")
        done_path = self.root / archive_docs.TODO_DONE
        self.assertTrue(done_path.is_file())
        done_txt = done_path.read_text(encoding="utf-8")

        # 010-01 moved to TODO_DONE under ## Phase 1 (no count)
        self.assertIn("## Phase 1\n", done_txt)
        self.assertNotIn("## Phase 1 (", done_txt)
        self.assertIn("- !DONE | 010-01 | First finished task", done_txt)

        # 010-02 and its patch stay in todo
        self.assertIn("- !DONE | 010-02 | Second task with pending patch", todo_txt)
        self.assertIn("  - !DEV | 010-02-01 | Incomplete patch", todo_txt)
        self.assertNotIn("010-01", todo_txt)
        self.assertNotIn("010-02", done_txt)
        self.assertNotIn("010-02-01", done_txt)

        # Todo heading ## Phase 1 (... DONE) is unchanged
        self.assertIn("## Phase 1 (1/2 DONE)", todo_txt)

        # Todo still has heading even when the group becomes empty
        self.assertIn("## Phase 2 (1/1 DONE)", todo_txt)
        self.assertNotIn("020-01", todo_txt)
        self.assertIn("## Phase 2\n", done_txt)
        self.assertNotIn("## Phase 2 (", done_txt)
        self.assertIn("- !DONE | 020-01 | Phase 2 finished task", done_txt)

    def test_apply_is_idempotent_and_does_not_touch_files_on_second_run(self) -> None:
        ki_text = ARCH_KI_PREAMBLE + (
            "| KI-001 | OPEN | Area | 010-01 | Owner |\n"
            "| KI-002 | CLOSED | Area | 010-01 | Owner |\n\n"
            "## KI-001 — issue 1\nDetails 1\n\n"
            "## KI-002 — issue 2\nDetails 2\n"
        )
        write(self.root, str(archive_docs.KNOWN_ISSUES), ki_text)
        write(self.root, str(archive_docs.TODO), ARCH_TODO)

        first_moves = archive_docs.apply(self.root)
        self.assertTrue(len(first_moves) > 0)

        before_state = {
            p: (p.read_bytes(), p.stat().st_mtime_ns)
            for p in self.root.rglob("*")
            if p.is_file()
        }
        time.sleep(0.02)

        second_moves = archive_docs.apply(self.root)
        self.assertEqual(second_moves, [])

        after_state = {
            p: (p.read_bytes(), p.stat().st_mtime_ns)
            for p in self.root.rglob("*")
            if p.is_file()
        }
        self.assertEqual(set(before_state.keys()), set(after_state.keys()))
        for p, (b_bytes, b_mtime) in before_state.items():
            a_bytes, a_mtime = after_state[p]
            self.assertEqual(b_bytes, a_bytes)
            self.assertEqual(b_mtime, a_mtime)

    def test_apply_with_nothing_to_move_returns_empty_and_creates_no_files(self) -> None:
        ki_text = ARCH_KI_PREAMBLE + (
            "| KI-001 | OPEN | Area | 010-01 | Owner |\n"
            "| KI-002 | PLANNED | Area | 010-01 | Owner |\n\n"
            "## KI-001 — issue 1\nDetails 1\n\n"
            "## KI-002 — issue 2\nDetails 2\n"
        )
        todo_text = """\
        # Tasks

        ---

        ## Phase 1 (0/2 DONE)
        - !DEV | 010-01 | Dev task
        - !APPROVED | 010-02 | Approved task
        """
        write(self.root, str(archive_docs.KNOWN_ISSUES), ki_text)
        write(self.root, str(archive_docs.TODO), todo_text)

        moves = archive_docs.apply(self.root)
        self.assertEqual(moves, [])

        self.assertFalse((self.root / archive_docs.KI_CLOSED).exists())
        self.assertFalse((self.root / archive_docs.KI_DEFERRED).exists())
        self.assertFalse((self.root / archive_docs.TODO_DONE).exists())

    def test_plan_moves_and_dry_run_cli_write_nothing_and_print_moves(self) -> None:
        ki_text = ARCH_KI_PREAMBLE + (
            "| KI-001 | OPEN | Area | 010-01 | Owner |\n"
            "| KI-002 | CLOSED | Area | 010-01 | Owner |\n\n"
            "## KI-001 — issue 1\nDetails 1\n\n"
            "## KI-002 — issue 2\nDetails 2\n"
        )
        write(self.root, str(archive_docs.KNOWN_ISSUES), ki_text)
        write(self.root, str(archive_docs.TODO), ARCH_TODO)

        before_files = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}

        planned = archive_docs.plan_moves(self.root)
        self.assertEqual(sorted(planned), [
            ("010-01", archive_docs.TODO, archive_docs.TODO_DONE),
            ("KI-002", archive_docs.KNOWN_ISSUES, archive_docs.KI_CLOSED),
        ])
        after_plan_files = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        self.assertEqual(before_files, after_plan_files)

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = archive_docs.main(["--root", str(self.root), "--dry-run"])

        self.assertEqual(code, 0)
        after_cli_files = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        self.assertEqual(before_files, after_cli_files)

        stdout_text = buf.getvalue()
        for item_id, _src, dst in planned:
            self.assertIn(f"moved {item_id} -> {dst.as_posix()}", stdout_text)
        archive_docs.apply(self.root)  # the planned moves are the ones performed
        self.assertIn("| KI-002 |", (self.root / archive_docs.KI_CLOSED).read_text(encoding="utf-8"))
        self.assertNotIn("| KI-002 |", (self.root / archive_docs.KNOWN_ISSUES).read_text(encoding="utf-8"))
        self.assertIn("| 010-01 |", (self.root / archive_docs.TODO_DONE).read_text(encoding="utf-8"))
        self.assertNotIn("| 010-01 |", (self.root / archive_docs.TODO).read_text(encoding="utf-8"))

    def test_parse_error_returns_exit_1_and_writes_nothing(self) -> None:
        bad_ki = ARCH_KI_PREAMBLE + (
            "| KI-001 | CLOSED | Area | 010-01 | Owner |\n"
            "invalid non-blank line between table and sections\n"
            "## KI-001 — issue 1\nDetails 1\n"
        )
        write(self.root, str(archive_docs.KNOWN_ISSUES), bad_ki)
        write(self.root, str(archive_docs.TODO), ARCH_TODO)

        before_files = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}

        buf_out = io.StringIO()
        buf_err = io.StringIO()
        with contextlib.redirect_stdout(buf_out), contextlib.redirect_stderr(buf_err):
            code = archive_docs.main(["--root", str(self.root)])

        self.assertEqual(code, 1)
        self.assertIn("archive_docs:", buf_err.getvalue())
        after_files = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        self.assertEqual(before_files, after_files)

    def test_cli_moves_then_reports_nothing_to_move(self) -> None:
        write(self.root, str(archive_docs.KNOWN_ISSUES), ARCH_KI_PREAMBLE + "| KI-001 | CLOSED | a | 010-01 | o |\n\n## KI-001 — x\nt\n")
        write(self.root, str(archive_docs.TODO), ARCH_TODO)
        for expected in ("moved KI-001 -> docs/archive/known_issues_closed.md", "nothing to move"):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                self.assertEqual(archive_docs.main(["--root", str(self.root)]), 0)
            self.assertIn(expected, buf.getvalue())

    def test_nothing_to_move_keeps_non_canonical_files(self) -> None:
        # Two blank lines between sections: a rewrite would normalise them.
        ki = ARCH_KI_PREAMBLE + "| KI-001 | OPEN | a | 010-01 | o |\n\n\n## KI-001 — x\nt\n\n\n## KI-002 — y\nu\n"
        ki = ki.replace("| KI-001 | OPEN | a | 010-01 | o |\n", "| KI-001 | OPEN | a | 010-01 | o |\n| KI-002 | PLANNED | a | 010-01 | o |\n")
        todo = ARCH_TODO.replace("!DONE | 010-01", "!DEV | 010-01") + "\n\n"
        paths = [write(self.root, str(archive_docs.KNOWN_ISSUES), ki), write(self.root, str(archive_docs.TODO), todo)]
        before = [(p.read_bytes(), p.stat().st_mtime_ns) for p in paths]
        self.assertEqual(archive_docs.apply(self.root), [])
        self.assertEqual([(p.read_bytes(), p.stat().st_mtime_ns) for p in paths], before)

    def test_moves_sort_into_existing_files_and_back_home(self) -> None:
        write(self.root, str(archive_docs.KNOWN_ISSUES), ARCH_KI_PREAMBLE
              + "| KI-002 | CLOSED | a | 010-01 | closed by 010-01 |\n| KI-004 | CLOSED | a | 010-01 | o |\n"
              + "| KI-005 | OPEN | closed by x | 010-01 | closed by 020-01 |\n\n"
              + "## KI-002 — b\nt2\n\n## KI-004 — d\nt4\n\n## KI-005 — e\nt5\n")
        write(self.root, str(archive_docs.KI_CLOSED), archive_docs.KI_CLOSED_INITIAL
              + "| KI-001 | PLANNED | a | 010-01 | 030-01 |\n| KI-003 | CLOSED | a | 010-01 | o |\n\n"
              + "## KI-001 — a\nt1\n\n## KI-003 — c\nt3\n")
        write(self.root, str(archive_docs.KI_DEFERRED), archive_docs.KI_DEFERRED_INITIAL
              + "| KI-006 | PLANNED | a | 010-01 | 030-02 |\n\n## KI-006 — f\nt6\n")
        write(self.root, str(archive_docs.TODO), ARCH_TODO)
        moves = archive_docs.apply(self.root)
        self.assertIn(("KI-001", archive_docs.KI_CLOSED, archive_docs.KNOWN_ISSUES), moves)
        self.assertIn(("KI-006", archive_docs.KI_DEFERRED, archive_docs.KNOWN_ISSUES), moves)
        self.assertNotIn("KI-005", [m[0] for m in moves])  # status is read per cell, "closed by" elsewhere is ignored
        closed = (self.root / archive_docs.KI_CLOSED).read_text(encoding="utf-8")
        rows = [line.split(" | ")[0] for line in closed.splitlines() if line.startswith("| KI-")]
        self.assertEqual(rows, ["| KI-002", "| KI-003", "| KI-004"])
        heads = [line.split(" — ")[0] for line in closed.splitlines() if line.startswith("## KI-")]
        self.assertEqual(heads, ["## KI-002", "## KI-003", "## KI-004"])
        known = (self.root / archive_docs.KNOWN_ISSUES).read_text(encoding="utf-8")
        rows = [line.split(" | ")[0] for line in known.splitlines() if line.startswith("| KI-")]
        self.assertEqual(rows, ["| KI-001", "| KI-005", "| KI-006"])
        heads = [line.split(" — ")[0] for line in known.splitlines() if line.startswith("## KI-")]
        self.assertEqual(heads, ["## KI-001", "## KI-005", "## KI-006"])
        self.assertNotIn("KI-006", (self.root / archive_docs.KI_DEFERRED).read_text(encoding="utf-8"))
        self.assertNotIn("KI-001", closed)

    def assert_refused(self, files: dict[str, str], reason: str) -> None:
        """archive_docs refuses for `reason` (exit 1, stderr), in both modes, and writes nothing."""
        for rel, text in files.items():
            write(self.root, rel, text)
        before = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        for argv in (["--root", str(self.root), "--dry-run"], ["--root", str(self.root)]):
            err = io.StringIO()
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
                self.assertEqual(archive_docs.main(argv), 1, argv)
            self.assertIn("archive_docs:", err.getvalue())
            self.assertIn(reason, err.getvalue())
        self.assertEqual({p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}, before)

    def test_refuses_instead_of_losing_text(self) -> None:
        closing = ARCH_KI_PREAMBLE + "| KI-001 | CLOSED | a | 010-01 | o |\n\n## KI-001 — x\nt\n"
        ki = str(archive_docs.KNOWN_ISSUES)
        todo = str(archive_docs.TODO)
        cases = {
            "free text in the todo archive": ("unexpected line", {
                ki: closing, todo: ARCH_TODO,
                str(archive_docs.TODO_DONE): archive_docs.TODO_DONE_INITIAL + "\n## Phase 0\na note\n- !DONE | 000-01 | z\n"}),
            "todo archive without ---": ("missing '---'", {
                ki: closing, todo: ARCH_TODO,
                str(archive_docs.TODO_DONE): "# Archive\n\n## Phase 0\n- !DONE | 000-01 | z\n"}),
            "duplicate row in one file": ("duplicate KI id KI-001 in table rows", {
                ki: closing.replace("| KI-001 | CLOSED | a | 010-01 | o |\n", "| KI-001 | CLOSED | a | 010-01 | o |\n| KI-001 | CLOSED | b | 010-01 | o |\n"),
                todo: ARCH_TODO}),
            "duplicate section in one file": ("duplicate KI id KI-001 in sections", {
                ki: closing + "\n## KI-001 — again\nu\n", todo: ARCH_TODO}),
            "row without a section": ("KI section for KI-001 missing", {
                ki: ARCH_KI_PREAMBLE + "| KI-001 | CLOSED | a | 010-01 | o |\n", todo: ARCH_TODO}),
            "same KI in two files": ("present in multiple files", {
                ki: closing, todo: ARCH_TODO,
                str(archive_docs.KI_CLOSED): archive_docs.KI_CLOSED_INITIAL + "| KI-001 | CLOSED | old | 010-01 | o |\n\n## KI-001 — old\nkeep me\n"}),
            "task already archived": ("already in", {
                ki: closing, todo: ARCH_TODO,
                str(archive_docs.TODO_DONE): archive_docs.TODO_DONE_INITIAL + "\n## Phase 1\n- !DONE | 010-01 | Old task\n"}),
            "same task twice in the todo": ("appears twice", {
                ki: closing, todo: ARCH_TODO + "- !DONE | 010-01 | Old task again\n"}),
            "task before the first heading": ("before first '## ' heading", {
                ki: closing, todo: ARCH_TODO.replace("---\n\n## Phase 1", "---\n- !DONE | 000-09 | stray\n\n## Phase 1")}),
            "patch after a blank line": ("not directly under a task", {
                ki: closing, todo: ARCH_TODO.replace("- !DONE | 010-01 | Old task\n", "- !DONE | 010-01 | Old task\n\n  - !DEV | 010-01-01 | patch\n")}),
            "note line in the todo body": ("unexpected line", {
                ki: closing, todo: ARCH_TODO.replace("- !DONE | 010-01 | Old task\n", "- !DONE | 010-01 | Old task\n  a note\n")}),
        }
        for name, (reason, files) in cases.items():
            with self.subTest(name):
                for p in sorted(self.root.rglob("*"), reverse=True):
                    p.unlink() if p.is_file() else p.rmdir()
                self.assert_refused(files, reason)

    def test_untouched_ki_file_is_not_rewritten(self) -> None:
        write(self.root, str(archive_docs.KNOWN_ISSUES), ARCH_KI_PREAMBLE + "| KI-001 | CLOSED | a | 010-01 | o |\n\n## KI-001 — x\nt\n")
        deferred = write(self.root, str(archive_docs.KI_DEFERRED), archive_docs.KI_DEFERRED_INITIAL
                         + "| KI-002 | DEFERRED | a | 010-01 | — (when x) |\n\n\n## KI-002 — y\nu\n\n\n")
        write(self.root, str(archive_docs.TODO), ARCH_TODO)
        before = (deferred.read_bytes(), deferred.stat().st_mtime_ns)
        self.assertIn(("KI-001", archive_docs.KNOWN_ISSUES, archive_docs.KI_CLOSED), archive_docs.apply(self.root))
        self.assertEqual((deferred.read_bytes(), deferred.stat().st_mtime_ns), before)

    def test_todo_blocks_groups_and_existing_archive(self) -> None:
        todo = """\
        # Tasks

        ---

        ## Phase 1 (3/3 DONE)
        - !DONE | 010-03 | c
          - !DONE | 010-03-01 | c patch
        - !DONE | 010-01 | a

        ## Phase 2 (1/1 DONE)
        - !DONE | 020-01 | x
        """
        write(self.root, str(archive_docs.TODO), todo)
        write(self.root, str(archive_docs.TODO_DONE), archive_docs.TODO_DONE_INITIAL
              + "\n## Phase 0\n- !DONE | 000-01 | zero\n\n## Phase 2\n- !DONE | 020-00 | earlier\n\n## Phase 1\n- !DONE | 010-02 | b\n")
        write(self.root, str(archive_docs.KNOWN_ISSUES), ARCH_KI_PREAMBLE + "| KI-001 | OPEN | a | 010-01 | o |\n\n## KI-001 — x\nt\n")
        archive_docs.apply(self.root)
        done = (self.root / archive_docs.TODO_DONE).read_text(encoding="utf-8")
        body = [line.strip() for line in done.split("\n---\n", 1)[1].splitlines() if line.strip()]
        self.assertEqual(body, [
            "## Phase 1", "- !DONE | 010-01 | a", "- !DONE | 010-02 | b", "- !DONE | 010-03 | c", "- !DONE | 010-03-01 | c patch",
            "## Phase 2", "- !DONE | 020-00 | earlier", "- !DONE | 020-01 | x",
            "## Phase 0", "- !DONE | 000-01 | zero",
        ])
        self.assertIn("  - !DONE | 010-03-01 | c patch", done)  # the patch keeps its indent under its task
        todo_after = (self.root / archive_docs.TODO).read_text(encoding="utf-8")
        self.assertNotIn("010-03", todo_after)
        self.assertIn("## Phase 1 (3/3 DONE)", todo_after)

    def test_todo_without_task_section_moves_nothing(self) -> None:
        self.assertEqual(archive_docs.movable_task_ids("# Tasks\n- !DONE | 010-01 | a\n"), [])
        self.assertEqual(archive_docs.archive_heading("## Phase 1: x (2/3 DONE)"), "## Phase 1: x")


class SyncSkillsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_case1_ac1_sync_valid_skills_and_idempotent(self) -> None:
        alpha_src = (
            "---\n"
            "name: alpha\n"
            "description: Alpha skill description\n"
            "---\n"
            "# Alpha\n"
            "Body of alpha skill.\n"
        )
        alpha_ref = "# Notes\nReference documentation.\n"
        beta_src = (
            "---\n"
            "name: beta\n"
            "description: Beta skill description\n"
            "---\n"
            "# Beta\n"
            "Body of beta skill.\n"
        )
        p_alpha = write(self.root, str(sync_skills.SOURCE / "alpha" / "SKILL.md"), alpha_src)
        p_alpha.write_bytes(alpha_src.encode("utf-8"))
        p_ref = write(self.root, str(sync_skills.SOURCE / "alpha" / "notes" / "ref.md"), alpha_ref)
        p_ref.write_bytes(alpha_ref.encode("utf-8"))
        p_beta = write(self.root, str(sync_skills.SOURCE / "beta" / "SKILL.md"), beta_src)
        p_beta.write_bytes(beta_src.encode("utf-8"))

        res = sync_skills.sync(self.root)
        self.assertIsInstance(res, list)

        for target in sync_skills.TARGETS:
            alpha_dest = self.root / target / "alpha" / "SKILL.md"
            self.assertTrue(alpha_dest.is_file())
            expected_alpha_skill = (
                "---\n"
                "name: alpha\n"
                "description: Alpha skill description\n"
                "---\n"
                f"{sync_skills.MARKER.format(name='alpha')}\n"
                "# Alpha\n"
                "Body of alpha skill.\n"
            )
            self.assertEqual(alpha_dest.read_text(encoding="utf-8").replace("\r\n", "\n"), expected_alpha_skill)

            alpha_ref_dest = self.root / target / "alpha" / "notes" / "ref.md"
            self.assertTrue(alpha_ref_dest.is_file())
            self.assertEqual(alpha_ref_dest.read_text(encoding="utf-8").replace("\r\n", "\n"), alpha_ref)

            beta_dest = self.root / target / "beta" / "SKILL.md"
            self.assertTrue(beta_dest.is_file())
            expected_beta_skill = (
                "---\n"
                "name: beta\n"
                "description: Beta skill description\n"
                "---\n"
                f"{sync_skills.MARKER.format(name='beta')}\n"
                "# Beta\n"
                "Body of beta skill.\n"
            )
            self.assertEqual(beta_dest.read_text(encoding="utf-8").replace("\r\n", "\n"), expected_beta_skill)

        self.assertEqual(sync_skills.check(self.root), [])

        target_files: list[Path] = []
        for target in sync_skills.TARGETS:
            for p in (self.root / target).rglob("*"):
                if p.is_file():
                    target_files.append(p)
        stats_before = {p: (p.stat().st_mtime_ns, p.read_bytes()) for p in target_files}

        res2 = sync_skills.sync(self.root)
        self.assertEqual(res2, [])
        for p in target_files:
            st = p.stat()
            self.assertEqual(st.st_mtime_ns, stats_before[p][0])
            self.assertEqual(p.read_bytes(), stats_before[p][1])

    def test_case2_ac2_edited_copy_detected_by_check_and_main(self) -> None:
        src = (
            "---\n"
            "name: alpha\n"
            "description: Alpha skill description\n"
            "---\n"
            "# Alpha\n"
        )
        p = write(self.root, str(sync_skills.SOURCE / "alpha" / "SKILL.md"), src)
        p.write_bytes(src.encode("utf-8"))
        sync_skills.sync(self.root)

        copy_path = self.root / sync_skills.TARGETS[0] / "alpha" / "SKILL.md"
        copy_path.write_text("edited copy\n", encoding="utf-8")
        copy_rel = (sync_skills.TARGETS[0] / "alpha" / "SKILL.md").as_posix()
        src_rel = (sync_skills.SOURCE / "alpha" / "SKILL.md").as_posix()

        findings = sync_skills.check(self.root)
        errors = [f for f in findings if f.level == "ERROR" and f.path == copy_rel]
        self.assertTrue(len(errors) >= 1)
        self.assertTrue(any("out of date" in f.message and src_rel in f.message for f in errors))

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            code = sync_skills.main(["--root", str(self.root), "--check"])
        self.assertEqual(code, 1)
        out = buf.getvalue()
        self.assertIn("out of date", out)
        self.assertIn(copy_rel, out)

    def test_case3_ac2_deleted_source_detected_and_cleaned(self) -> None:
        alpha_src = (
            "---\n"
            "name: alpha\n"
            "description: Alpha skill description\n"
            "---\n"
            "# Alpha\n"
        )
        beta_src = (
            "---\n"
            "name: beta\n"
            "description: Beta skill description\n"
            "---\n"
            "# Beta\n"
        )
        p_alpha = write(self.root, str(sync_skills.SOURCE / "alpha" / "SKILL.md"), alpha_src)
        p_alpha.write_bytes(alpha_src.encode("utf-8"))
        p_beta = write(self.root, str(sync_skills.SOURCE / "beta" / "SKILL.md"), beta_src)
        p_beta.write_bytes(beta_src.encode("utf-8"))
        sync_skills.sync(self.root)

        shutil.rmtree(self.root / sync_skills.SOURCE / "beta")

        findings = sync_skills.check(self.root)
        for target in sync_skills.TARGETS:
            leftover_rel = (target / "beta" / "SKILL.md").as_posix()
            errors = [f for f in findings if f.level == "ERROR" and f.path == leftover_rel]
            self.assertTrue(len(errors) >= 1)
            self.assertTrue(any("no source" in f.message for f in errors))

        sync_skills.sync(self.root)
        for target in sync_skills.TARGETS:
            self.assertFalse((self.root / target / "beta").exists())
        self.assertEqual(sync_skills.check(self.root), [])

    def test_case4_ac2_missing_skill_md_errors_and_refuses_sync(self) -> None:
        folder = self.root / sync_skills.SOURCE / "empty-skill"
        folder.mkdir(parents=True, exist_ok=True)
        other = folder / "other.txt"
        other.write_bytes(b"content\n")

        findings = sync_skills.check(self.root)
        expected_folder = (sync_skills.SOURCE / "empty-skill").as_posix()
        expected_skill = (sync_skills.SOURCE / "empty-skill" / "SKILL.md").as_posix()
        errors = [f for f in findings if f.level == "ERROR" and f.path in (expected_folder, expected_skill)]
        self.assertTrue(len(errors) >= 1)

        with self.assertRaises(ValueError):
            sync_skills.sync(self.root)

        for target in sync_skills.TARGETS:
            target_path = self.root / target
            if target_path.exists():
                self.assertEqual(list(target_path.iterdir()), [])

    def test_case5_ac3_frontmatter_errors_and_limits(self) -> None:
        src_skill_rel = (sync_skills.SOURCE / "alpha" / "SKILL.md").as_posix()
        skill_file = self.root / sync_skills.SOURCE / "alpha" / "SKILL.md"

        # 1. extra key allowed-tools
        bad_extra_key = (
            "---\n"
            "name: alpha\n"
            "description: Alpha skill\n"
            "allowed-tools: read_file\n"
            "---\n"
            "# Alpha\n"
        )
        write(self.root, str(sync_skills.SOURCE / "alpha" / "SKILL.md"), bad_extra_key)
        skill_file.write_bytes(bad_extra_key.encode("utf-8"))
        findings = sync_skills.check(self.root)
        errors = [f for f in findings if f.level == "ERROR" and f.path == src_skill_rel]
        self.assertTrue(len(errors) >= 1)
        self.assertTrue(any("allowed-tools" in f.message for f in errors))

        # 2. name different from the folder
        bad_name_diff = (
            "---\n"
            "name: different\n"
            "description: Alpha skill\n"
            "---\n"
            "# Alpha\n"
        )
        skill_file.write_bytes(bad_name_diff.encode("utf-8"))
        findings = sync_skills.check(self.root)
        errors = [f for f in findings if f.level == "ERROR" and f.path == src_skill_rel]
        self.assertTrue(len(errors) >= 1)
        self.assertTrue(any(("folder" in f.message.lower() or "alpha" in f.message)
                            and ("name" in f.message.lower() or "different" in f.message) for f in errors))

        # 3. name with an upper-case letter (folder and name both UpperSkill so only case is invalid)
        upper_skill_file = self.root / sync_skills.SOURCE / "UpperSkill" / "SKILL.md"
        upper_src_rel = (sync_skills.SOURCE / "UpperSkill" / "SKILL.md").as_posix()
        bad_name_upper = (
            "---\n"
            "name: UpperSkill\n"
            "description: Alpha skill\n"
            "---\n"
            "# UpperSkill\n"
        )
        write(self.root, str(sync_skills.SOURCE / "UpperSkill" / "SKILL.md"), bad_name_upper)
        upper_skill_file.write_bytes(bad_name_upper.encode("utf-8"))
        shutil.rmtree(self.root / sync_skills.SOURCE / "alpha")
        findings = sync_skills.check(self.root)
        errors = [f for f in findings if f.level == "ERROR" and f.path == upper_src_rel]
        self.assertTrue(len(errors) >= 1)
        self.assertTrue(any("upper" in f.message.lower() or "case" in f.message.lower()
                            or "name" in f.message.lower() or "pattern" in f.message.lower()
                            for f in errors))
        shutil.rmtree(self.root / sync_skills.SOURCE / "UpperSkill")

        # 4. description of 1025 characters
        desc_1025 = "d" * 1025
        bad_desc_len = (
            "---\n"
            "name: alpha\n"
            f"description: {desc_1025}\n"
            "---\n"
            "# Alpha\n"
        )
        write(self.root, str(sync_skills.SOURCE / "alpha" / "SKILL.md"), bad_desc_len)
        skill_file.write_bytes(bad_desc_len.encode("utf-8"))
        findings = sync_skills.check(self.root)
        errors = [f for f in findings if f.level == "ERROR" and f.path == src_skill_rel]
        self.assertTrue(len(errors) >= 1)
        self.assertTrue(any("description" in f.message.lower()
                            and ("1024" in f.message or "1025" in f.message or "long" in f.message.lower() or "limit" in f.message.lower())
                            for f in errors))

        # 5. empty description
        bad_desc_empty = (
            "---\n"
            "name: alpha\n"
            "description:\n"
            "---\n"
            "# Alpha\n"
        )
        skill_file.write_bytes(bad_desc_empty.encode("utf-8"))
        findings = sync_skills.check(self.root)
        errors = [f for f in findings if f.level == "ERROR" and f.path == src_skill_rel]
        self.assertTrue(len(errors) >= 1)
        self.assertTrue(any("description" in f.message.lower() and "empty" in f.message.lower() for f in errors))

        # 6. description of exactly 1024 characters is fine
        desc_1024 = "d" * 1024
        good_desc_len = (
            "---\n"
            "name: alpha\n"
            f"description: {desc_1024}\n"
            "---\n"
            "# Alpha\n"
        )
        skill_file.write_bytes(good_desc_len.encode("utf-8"))
        findings = sync_skills.check(self.root)
        # Only the source is judged here: the copies were never synced, so they are reported missing.
        self.assertEqual([f for f in findings if f.level == "ERROR" and f.path == src_skill_rel], [])

    def test_case6_ac3_body_utf8_byte_limit_warning(self) -> None:
        src_skill_rel = (sync_skills.SOURCE / "alpha" / "SKILL.md").as_posix()
        skill_file = self.root / sync_skills.SOURCE / "alpha" / "SKILL.md"

        head = (
            "---\n"
            "name: alpha\n"
            "description: Valid description\n"
            "---\n"
        )
        # Korean multi-byte text: '한' is 3 bytes in UTF-8
        # 1365 * 3 = 4095 bytes
        body_4096 = ("한" * 1365) + "a"
        self.assertEqual(len(body_4096.encode("utf-8")), 4096)
        self.assertNotEqual(len(body_4096), len(body_4096.encode("utf-8")))

        write(self.root, str(sync_skills.SOURCE / "alpha" / "SKILL.md"), head + body_4096)
        skill_file.write_bytes((head + body_4096).encode("utf-8"))
        findings_4096 = sync_skills.check(self.root)
        self.assertEqual([f for f in findings_4096 if f.level == "WARN" and f.path == src_skill_rel], [])

        body_4097 = ("한" * 1365) + "ab"
        self.assertEqual(len(body_4097.encode("utf-8")), 4097)
        self.assertNotEqual(len(body_4097), len(body_4097.encode("utf-8")))

        skill_file.write_bytes((head + body_4097).encode("utf-8"))
        findings_4097 = sync_skills.check(self.root)
        warns = [f for f in findings_4097 if f.level == "WARN" and f.path == src_skill_rel]
        self.assertEqual(len(warns), 1)
        self.assertTrue(any("4096" in warns[0].message or "byte" in warns[0].message.lower()
                            or "limit" in warns[0].message.lower() or "size" in warns[0].message.lower()
                            for _ in [None]))

    def test_case7_crlf_line_endings_ignored_by_check(self) -> None:
        src = (
            "---\n"
            "name: alpha\n"
            "description: Alpha skill description\n"
            "---\n"
            "# Alpha\n"
            "Body of alpha.\n"
        )
        p = write(self.root, str(sync_skills.SOURCE / "alpha" / "SKILL.md"), src)
        p.write_bytes(src.encode("utf-8"))
        sync_skills.sync(self.root)
        self.assertEqual(sync_skills.check(self.root), [])

        copy_path = self.root / sync_skills.TARGETS[0] / "alpha" / "SKILL.md"
        copy_rel = (sync_skills.TARGETS[0] / "alpha" / "SKILL.md").as_posix()
        text = copy_path.read_text(encoding="utf-8")
        crlf_bytes = text.replace("\r\n", "\n").replace("\n", "\r\n").encode("utf-8")
        copy_path.write_bytes(crlf_bytes)

        findings = sync_skills.check(self.root)
        self.assertEqual([f for f in findings if f.path == copy_rel], [])

    def test_case8_ac4_lint_docs_integration(self) -> None:
        write(self.root, "docs/agent_todo.md", TODO)
        write(self.root, "docs/known_issues.md", KNOWN)
        write(self.root, "docs/specs/01_old.md", "# Legacy\n[gone](/include/gone.h)\n")
        write(self.root, "docs/specs/010_02_new.md", spec("010-02", "2026-10-28"))

        alpha_src = (
            "---\n"
            "name: alpha\n"
            "description: Alpha skill description\n"
            "---\n"
            "# Alpha\n"
        )
        p = write(self.root, str(sync_skills.SOURCE / "alpha" / "SKILL.md"), alpha_src)
        p.write_bytes(alpha_src.encode("utf-8"))
        sync_skills.sync(self.root)

        copy_path = self.root / sync_skills.TARGETS[0] / "alpha" / "SKILL.md"
        copy_rel = (sync_skills.TARGETS[0] / "alpha" / "SKILL.md").as_posix()
        copy_path.write_text("edited copy\n", encoding="utf-8")

        report = lint_docs.lint(self.root)
        errors = [f for f in report.findings if f[0] == "ERROR" and f[1] == copy_rel]
        self.assertTrue(len(errors) >= 1)
        self.assertTrue(any(f[3].startswith("skills:") for f in errors))

        sync_skills.sync(self.root)
        report_after = lint_docs.lint(self.root)
        self.assertEqual([f for f in report_after.findings if f[3].startswith("skills:")], [])

    def test_case9_empty_tree_check_returns_empty(self) -> None:
        self.assertEqual(sync_skills.check(self.root), [])

    # --- Review fixes for U1 (090-10) -------------------------------------------------

    def put_skill(self, name: str, frontmatter: str | None = None, body: str = "# Body\n", eol: str = "\n") -> Path:
        fm = frontmatter if frontmatter is not None else f"name: {name}\ndescription: does {name}\n"
        text = f"---\n{fm}---\n{body}".replace("\n", eol)
        path = self.root / sync_skills.SOURCE / name / "SKILL.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.encode("utf-8"))
        return path

    def run_main(self, *argv: str) -> tuple[int, str]:
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            code = sync_skills.main(["--root", str(self.root), *argv])
        return code, out.getvalue()

    def test_review_written_bytes_are_lf_and_no_rewrite(self) -> None:
        self.put_skill("alpha", body="# Alpha\nline two\n")
        sync_skills.sync(self.root)
        copy = self.root / sync_skills.TARGETS[0] / "alpha" / "SKILL.md"
        marker = sync_skills.MARKER.format(name="alpha")
        self.assertEqual(copy.read_bytes(), f"---\nname: alpha\ndescription: does alpha\n---\n{marker}\n# Alpha\nline two\n".encode("utf-8"))
        old = 1_000_000_000
        for target in sync_skills.TARGETS:
            os.utime(self.root / target / "alpha" / "SKILL.md", ns=(old, old))
        self.assertEqual(sync_skills.sync(self.root), [])
        for target in sync_skills.TARGETS:
            self.assertEqual((self.root / target / "alpha" / "SKILL.md").stat().st_mtime_ns, old)

    def test_review_crlf_source_matches_lf_copy(self) -> None:
        # Under core.autocrlf the source is CRLF in the working tree: the copy is still LF and up to date.
        self.put_skill("alpha", eol="\r\n")
        sync_skills.sync(self.root)
        copy = (self.root / sync_skills.TARGETS[1] / "alpha" / "SKILL.md").read_bytes()
        self.assertNotIn(b"\r", copy)
        self.assertIn(("\n---\n" + sync_skills.MARKER.format(name="alpha") + "\n").encode("utf-8"), copy)
        self.assertEqual(sync_skills.check(self.root), [])

    def test_review_check_never_writes_and_reports_every_case(self) -> None:
        self.put_skill("alpha")
        self.put_skill("beta")
        sync_skills.sync(self.root)
        edited = self.root / sync_skills.TARGETS[0] / "alpha" / "SKILL.md"
        edited.write_bytes(b"edited copy\n")
        leftover = self.root / sync_skills.TARGETS[1] / "gone" / "SKILL.md"
        leftover.parent.mkdir(parents=True)
        leftover.write_bytes(b"x\n")
        (self.root / sync_skills.SOURCE / "nofile").mkdir()
        before = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        code, out = self.run_main("--check")
        self.assertEqual(code, 1)
        self.assertIn(".claude/skills/alpha/SKILL.md", out)
        self.assertIn("out of date", out)
        self.assertIn(".agents/skills/gone/SKILL.md", out)
        self.assertIn("no source", out)
        self.assertIn(".agent/skills/nofile/SKILL.md", out)
        self.assertIn("missing SKILL.md", out)
        self.assertEqual({p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}, before)  # --check wrote nothing

    def test_review_sync_refuses_before_writing_valid_skills(self) -> None:
        self.put_skill("alpha")
        (self.root / sync_skills.SOURCE / "broken").mkdir()
        with self.assertRaises(ValueError) as ctx:
            sync_skills.sync(self.root)
        self.assertIn(".agent/skills/broken/SKILL.md", str(ctx.exception))
        self.assertIn("missing SKILL.md", str(ctx.exception))
        for target in sync_skills.TARGETS:
            self.assertFalse((self.root / target).exists())
        code, out = self.run_main()
        self.assertEqual(code, 1)
        self.assertIn("sync_skills:", out)

    def test_review_validate_rules_tied_to_cause(self) -> None:
        cases = {
            "upper-case name": ("name: Alpha\ndescription: d\n", "does not match pattern"),
            "no frontmatter": (None, "frontmatter"),
            "missing name": ("description: d\n", "missing 'name'"),
            "missing description": ("name: alpha\n", "missing 'description'"),
            "name over 64": (f"name: {'a' * 65}\ndescription: d\n", "exceeds 64"),
        }
        for label, (fm, word) in cases.items():
            with self.subTest(label):
                shutil.rmtree(self.root / sync_skills.SOURCE, ignore_errors=True)
                path = self.root / sync_skills.SOURCE / "alpha" / "SKILL.md"
                path.parent.mkdir(parents=True)
                path.write_bytes(b"# no frontmatter\n" if fm is None else f"---\n{fm}---\n# B\n".encode("utf-8"))
                errors = [f.message for f in sync_skills.validate(self.root) if f.level == "ERROR"]
                self.assertTrue(any(word in m for m in errors), (word, errors))
        # The upper-case name is caught by the pattern even when it equals the folder name.
        shutil.rmtree(self.root / sync_skills.SOURCE)
        self.put_skill("Alpha", "name: Alpha\ndescription: d\n")
        self.assertEqual([m for m in (f.message for f in sync_skills.validate(self.root)) if "folder" in m], [])
        self.assertTrue(any("does not match pattern" in f.message for f in sync_skills.validate(self.root)))
        # A file that is not UTF-8 is an ERROR, not an exception.
        shutil.rmtree(self.root / sync_skills.SOURCE)
        self.put_skill("alpha")
        (self.root / sync_skills.SOURCE / "alpha" / "bad.md").write_bytes(b"\xff\xfe\x00bad")
        self.assertTrue(any("UTF-8" in f.message and f.path.endswith("alpha/bad.md") for f in sync_skills.check(self.root)))

    def test_review_missing_copies_bom_hash_and_missing_source(self) -> None:
        self.put_skill("alpha")
        # Never synced, and no target folder at all: each missing copy is an ERROR.
        missing = sorted(f.path for f in sync_skills.check(self.root) if "out of date" in f.message)
        self.assertEqual(missing, [".agents/skills/alpha/SKILL.md", ".claude/skills/alpha/SKILL.md"])
        sync_skills.sync(self.root)
        (self.root / ".claude/skills/alpha/SKILL.md").unlink()
        self.assertEqual([f.path for f in sync_skills.check(self.root)], [".claude/skills/alpha/SKILL.md"])
        # A BOM in the source: the copy still starts with the frontmatter, marker after the closing ---.
        src = self.root / sync_skills.SOURCE / "alpha" / "SKILL.md"
        src.write_bytes(b"\xef\xbb\xbf" + src.read_bytes())
        sync_skills.sync(self.root)
        copy = (self.root / ".agents/skills/alpha/SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(copy.startswith("---\nname: alpha\n"), copy[:40])
        self.assertIn("---\n" + sync_skills.MARKER.format(name="alpha") + "\n# Body", copy)
        # A '#' in the description is counted, not cut as a comment.
        self.put_skill("alpha", f"name: alpha\ndescription: C# {'d' * 1022}\n")
        self.assertTrue(any("description length" in f.message for f in sync_skills.validate(self.root)))
        # A comment-only value is empty.
        self.put_skill("alpha", "name: alpha\ndescription: # note\n")
        self.assertTrue(any("description is empty" in f.message for f in sync_skills.validate(self.root)))
        # No source folder but generated copies exist: sync refuses and removes nothing.
        shutil.rmtree(self.root / sync_skills.SOURCE)
        with self.assertRaises(ValueError):
            sync_skills.sync(self.root)
        self.assertTrue((self.root / ".agents/skills/alpha/SKILL.md").is_file())

    def test_review_top_level_files_are_not_skills(self) -> None:
        (self.root / sync_skills.SOURCE).mkdir(parents=True)
        (self.root / sync_skills.SOURCE / "README.md").write_bytes(b"# Skills\n")
        self.assertEqual(sync_skills.check(self.root), [])
        self.assertEqual(sync_skills.sync(self.root), [])
        for target in sync_skills.TARGETS:
            self.assertFalse((self.root / target / "README.md").exists())


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


class CodexGuardHookTest(unittest.TestCase):
    def load_adapter(self):
        adapter_path = SCRIPTS.parents[1] / ".codex" / "hooks" / "guard.py"
        if not adapter_path.is_file():
            self.fail(f"codex adapter not found: {adapter_path}")
        spec = importlib.util.spec_from_file_location("codex_guard", adapter_path)
        if spec is None or spec.loader is None:
            self.fail(f"could not create module spec from {adapter_path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def make_event(
        self,
        tool_name: str,
        tool_input: dict,
        cwd: str | None = None,
    ) -> dict:
        return {
            "hook_event_name": "PreToolUse",
            "tool_name": tool_name,
            "tool_input": tool_input,
            "cwd": cwd if cwd is not None else str(SCRIPTS.parents[1]),
            "session_id": "s",
            "turn_id": "t",
            "tool_use_id": "u",
        }

    @contextlib.contextmanager
    def patch_branch(self, adapter, branch: str):
        mock = MagicMock(stdout=f"{branch}\n")
        with patch.object(agent_common, "git", return_value=mock):
            if hasattr(adapter, "ac") and hasattr(adapter.ac, "git"):
                with patch.object(adapter.ac, "git", return_value=mock):
                    yield
            else:
                yield

    def test_codex_case1_bash_adhoc_rule2(self) -> None:
        adapter = self.load_adapter()
        event_adhoc = self.make_event("Bash", {"command": ADHOC})
        reason_adhoc = adapter.decide(event_adhoc)
        self.assertIsNotNone(reason_adhoc)
        self.assertIn("rule 2", reason_adhoc)

        event_preset = self.make_event("Bash", {"command": "cmake --preset x"})
        reason_preset = adapter.decide(event_preset)
        self.assertIsNone(reason_preset)

    def test_codex_case2_bash_commit_protected_branch_rule4(self) -> None:
        adapter = self.load_adapter()
        event_commit = self.make_event("Bash", {"command": "git commit -m x"})

        with self.patch_branch(adapter, "main"):
            reason_main = adapter.decide(event_commit)
            self.assertIsNotNone(reason_main)
            self.assertIn("rule 4", reason_main)

        with self.patch_branch(adapter, "feature/x"):
            reason_feature = adapter.decide(event_commit)
            self.assertIsNone(reason_feature)

        event_log = self.make_event("Bash", {"command": "git log --grep commit"})
        with self.patch_branch(adapter, "main"):
            reason_log = adapter.decide(event_log)
            self.assertIsNone(reason_log)

    def test_codex_case3_apply_patch_add_file_rule1(self) -> None:
        adapter = self.load_adapter()
        patch_machine = textwrap.dedent(f"""\
        *** Begin Patch
        *** Add File: docs/x.md
        +{DRIVE}vcpkg/installed
        *** End Patch
        """)
        event_machine = self.make_event("apply_patch", {"command": patch_machine})
        reason_machine = adapter.decide(event_machine)
        self.assertIsNotNone(reason_machine)
        self.assertIn("rule 1", reason_machine)

        patch_clean = textwrap.dedent("""\
        *** Begin Patch
        *** Add File: docs/x.md
        +docs/relative/path.md
        *** End Patch
        """)
        event_clean = self.make_event("apply_patch", {"command": patch_clean})
        reason_clean = adapter.decide(event_clean)
        self.assertIsNone(reason_clean)

    def test_codex_case4_apply_patch_update_file(self) -> None:
        adapter = self.load_adapter()
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo = Path(tmp_dir)
            subprocess.run(["git", "init", "-q", str(repo)], check=True)
            (repo / ".gitignore").write_text("out/\n", encoding="utf-8")

            patch_root = patch.object(adapter, "ROOT", repo) if hasattr(adapter, "ROOT") else contextlib.nullcontext()
            with patch_root, patch.object(agent_common, "REPO_ROOT", repo):
                # Context line and '-' line contain machine path -> None
                patch_minus_context = textwrap.dedent(f"""\
                *** Begin Patch
                *** Update File: docs/x.md
                 {HOME}context/line
                -{DRIVE}old/machine/path
                +clean replacement line
                *** End Patch
                """)
                event_minus = self.make_event("apply_patch", {"command": patch_minus_context}, cwd=str(repo))
                self.assertIsNone(adapter.decide(event_minus))

                # '+' line contains machine path -> reason naming rule 1
                patch_plus = textwrap.dedent(f"""\
                *** Begin Patch
                *** Update File: docs/x.md
                 context line
                -{DRIVE}old/machine/path
                +{DRIVE}new/machine/path
                *** End Patch
                """)
                event_plus = self.make_event("apply_patch", {"command": patch_plus}, cwd=str(repo))
                reason_plus = adapter.decide(event_plus)
                self.assertIsNotNone(reason_plus)
                self.assertIn("rule 1", reason_plus)

                # '*** Move to:' makes the new path judged; ignored target out/x.md -> None
                patch_move = textwrap.dedent(f"""\
                *** Begin Patch
                *** Update File: docs/x.md
                *** Move to: out/x.md
                +{DRIVE}new/machine/path
                *** End Patch
                """)
                event_move = self.make_event("apply_patch", {"command": patch_move}, cwd=str(repo))
                self.assertIsNone(adapter.decide(event_move))

    def test_codex_case5_patch_outside_repo(self) -> None:
        adapter = self.load_adapter()
        patch_outside_add = textwrap.dedent(f"""\
        *** Begin Patch
        *** Add File: ../outside.md
        +{DRIVE}some/machine/path
        *** End Patch
        """)
        event_outside_add = self.make_event("apply_patch", {"command": patch_outside_add})
        self.assertIsNone(adapter.decide(event_outside_add))

        patch_outside_update = textwrap.dedent(f"""\
        *** Begin Patch
        *** Update File: ../outside.md
        +{DRIVE}some/machine/path
        *** End Patch
        """)
        event_outside_update = self.make_event("apply_patch", {"command": patch_outside_update})
        self.assertIsNone(adapter.decide(event_outside_update))

    def test_codex_case6_other_tools_and_command_list(self) -> None:
        adapter = self.load_adapter()
        # Other tools -> None
        self.assertIsNone(adapter.decide(self.make_event("update_plan", {"command": ADHOC})))
        self.assertIsNone(adapter.decide(self.make_event("mcp__server__tool", {"command": ADHOC})))

        # tool_input.command given as list of strings for Bash is joined and judged
        event_list_adhoc = self.make_event("Bash", {"command": ["cmake", "-S", ".", "-B", "build"]})
        reason_list_adhoc = adapter.decide(event_list_adhoc)
        self.assertIsNotNone(reason_list_adhoc)
        self.assertIn("rule 2", reason_list_adhoc)

        event_list_clean = self.make_event("Bash", {"command": ["cmake", "--preset", "linux-x64-debug"]})
        self.assertIsNone(adapter.decide(event_list_clean))

    def test_codex_case7_main_stdin_stdout_fail_open(self) -> None:
        adapter = self.load_adapter()

        def run_main(payload_bytes: bytes, payload_str: str) -> tuple[int, str, str]:
            fake_stdin = MagicMock()
            fake_stdin.buffer.read.return_value = payload_bytes
            fake_stdin.read.return_value = payload_str
            out = io.StringIO()
            err = io.StringIO()
            patchers = [
                patch("sys.stdin", fake_stdin),
                contextlib.redirect_stdout(out),
                contextlib.redirect_stderr(err),
            ]
            if hasattr(adapter, "sys"):
                patchers.append(patch.object(adapter.sys, "stdin", fake_stdin))
                patchers.append(patch.object(adapter.sys, "stdout", out))
                patchers.append(patch.object(adapter.sys, "stderr", err))
            with contextlib.ExitStack() as stack:
                for p in patchers:
                    stack.enter_context(p)
                code = adapter.main()
            return code, out.getvalue(), err.getvalue()

        # Denying event: prints exactly one JSON object with PreToolUse deny, exit 0
        deny_event = self.make_event("Bash", {"command": ADHOC})
        deny_str = json.dumps(deny_event)
        code, stdout, stderr = run_main(deny_str.encode("utf-8"), deny_str)
        self.assertEqual(code, 0)
        self.assertEqual(stderr, "")
        deny_data = json.loads(stdout)
        hook_output = deny_data.get("hookSpecificOutput", {})
        self.assertEqual(hook_output.get("hookEventName"), "PreToolUse")
        self.assertEqual(hook_output.get("permissionDecision"), "deny")
        self.assertIn("rule 2", hook_output.get("permissionDecisionReason", ""))

        # Passing event: prints nothing, exit 0
        pass_event = self.make_event("Bash", {"command": "cmake --preset x"})
        pass_str = json.dumps(pass_event)
        code, stdout, stderr = run_main(pass_str.encode("utf-8"), pass_str)
        self.assertEqual(code, 0)
        self.assertEqual(stdout, "")
        self.assertEqual(stderr, "")

        # Non-JSON stdin: prints nothing to stdout, something to stderr, exit 0 (fail open)
        raw = "not a valid json payload"
        code, stdout, stderr = run_main(raw.encode("utf-8"), raw)
        self.assertEqual(code, 0)
        self.assertEqual(stdout, "")
        self.assertNotEqual(stderr, "")

    def test_codex_case8_hooks_json(self) -> None:
        hooks_json_path = SCRIPTS.parents[1] / ".codex" / "hooks.json"
        self.assertTrue(hooks_json_path.is_file(), f".codex/hooks.json not found: {hooks_json_path}")
        data = json.loads(hooks_json_path.read_text(encoding="utf-8"))
        pre_tool_use = data.get("hooks", {}).get("PreToolUse")
        if pre_tool_use is None:
            pre_tool_use = data.get("PreToolUse")
        self.assertIsInstance(pre_tool_use, list, "PreToolUse must be a list of hook entries")
        self.assertGreater(len(pre_tool_use), 0, "PreToolUse list must not be empty")

        matching_entry = None
        for entry in pre_tool_use:
            matcher = entry.get("matcher", "")
            if re.search(matcher, "Bash") and re.search(matcher, "apply_patch"):
                matching_entry = entry
                break
        self.assertIsNotNone(matching_entry, "No PreToolUse entry matching both Bash and apply_patch")
        matcher = matching_entry.get("matcher", "")
        self.assertIsNone(re.search(matcher, "update_plan"), "matcher must not match update_plan")

        inner_hooks = matching_entry.get("hooks", [])
        commands = [h.get("command", "") for h in inner_hooks if isinstance(h, dict)]
        if "command" in matching_entry:
            commands.append(matching_entry["command"])
        self.assertTrue(
            any(".codex/hooks/guard.py" in cmd for cmd in commands),
            f"PreToolUse command must mention .codex/hooks/guard.py, found: {commands}"
        )

    def test_codex_review_u4_lists_blocks_and_patch_start(self) -> None:
        # U4 review fixes (090-11): list commands keep argument boundaries, every file block of a
        # patch is judged, absolute paths, Delete blocks never judged, leading whitespace or BOM.
        adapter = self.load_adapter()
        with patch.object(agent_common, "git", return_value=MagicMock(stdout="main\n")):
            self.assertEqual(adapter.decide(self.make_event("Bash", {"command": ["bash", "-lc", "git commit -m x"]})),
                             guard_rules.protected_branch_reason("main"))
        self.assertEqual(adapter.decide(self.make_event("Bash", {"command": ["bash", "-lc", ADHOC]})),
                         guard_rules.check_command(ADHOC, "bash"))
        bad = f"see {DRIVE}tools"
        expected = guard_rules.machine_path_reason([bad])
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo = Path(tmp_dir)
            subprocess.run(["git", "init", "-q", str(repo)], check=True)

            def judge(body: str, prefix: str = "") -> str | None:
                return adapter.decide(self.make_event(
                    "apply_patch", {"command": f"{prefix}*** Begin Patch\n{body}*** End Patch\n"}, cwd=str(repo)))

            with patch.object(adapter, "ROOT", repo):
                # The bad block is not the first one, then not the last one.
                self.assertEqual(judge(f"*** Add File: a.md\n+ok\n*** Add File: b.md\n+{bad}\n"), expected)
                self.assertEqual(judge(f"*** Add File: b.md\n+{bad}\n*** Add File: c.md\n+ok\n"), expected)
                # An absolute path inside the repo is judged; one outside is not.
                self.assertEqual(judge(f"*** Add File: {(repo / 'd.md').as_posix()}\n+{bad}\n"), expected)
                self.assertIsNone(judge(f"*** Add File: {(repo.parent / 'outside.md').as_posix()}\n+{bad}\n"))
                # A Delete block's lines (even '+' ones) are never judged; the next block still is.
                self.assertIsNone(judge(f"*** Delete File: e.md\n+{bad}\n"))
                self.assertEqual(judge(f"*** Delete File: e.md\n*** Add File: f.md\n+{bad}\n"), expected)
                # A BOM right before `*** Begin Patch` on the same line, and blank lines before it.
                self.assertEqual(judge(f"*** Add File: g.md\n+{bad}\n", prefix="\n﻿"), expected)
                # Headers start in column 0: an indented "header" or " *** End Patch" is a context
                # line of the Update block and does not end or redirect it.
                self.assertEqual(judge(f"*** Update File: h.md\n@@\n *** End Patch\n *** Add File: out/i.md\n+{bad}\n"), expected)
                # A '+' line is not cut at a form feed (str.splitlines would cut it).
                self.assertEqual(judge(f"*** Add File: j.md\n+x\x0c{bad}\n"), guard_rules.machine_path_reason([f"x\x0c{bad}"]))

    # --- Review fixes for U3 (090-11) -------------------------------------------------

    def test_codex_review_exact_reasons_cwd_move_and_config(self) -> None:
        adapter = self.load_adapter()
        # Exact reasons: the adapter writes none of its own.
        self.assertEqual(adapter.decide(self.make_event("Bash", {"command": ADHOC})), guard_rules.check_command(ADHOC, "bash"))
        with patch.object(agent_common, "git", return_value=MagicMock(stdout="main\n")):
            self.assertEqual(adapter.decide(self.make_event("Bash", {"command": "git commit -m x"})), guard_rules.protected_branch_reason("main"))
        bad = f"see {DRIVE}tools"
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo = Path(tmp_dir)
            subprocess.run(["git", "init", "-q", str(repo)], check=True)
            (repo / ".gitignore").write_text("out/\n", encoding="utf-8")
            (repo / "docs").mkdir()

            def patch_event(body: str, cwd: Path | None) -> dict:
                event = self.make_event("apply_patch", {"command": f"*** Begin Patch\n{body}*** End Patch\n"})
                if cwd is None:
                    event.pop("cwd")
                else:
                    event["cwd"] = str(cwd)
                return event

            with patch.object(adapter, "ROOT", repo):
                expected = guard_rules.machine_path_reason([bad])
                # Paths are relative to cwd: "x.md" from docs/ is docs/x.md (checked); from the root it is x.md.
                self.assertEqual(adapter.decide(patch_event(f"*** Add File: x.md\n+{bad}\n", repo / "docs")), expected)
                # cwd decides: from out/ the same relative path is ignored, so it passes.
                (repo / "out").mkdir()
                self.assertIsNone(adapter.decide(patch_event(f"*** Add File: x.md\n+{bad}\n", repo / "out")))
                # No cwd: the repo root is the base (out/x.md ignored, docs/x.md checked).
                self.assertIsNone(adapter.decide(patch_event(f"*** Add File: out/x.md\n+{bad}\n", None)))
                self.assertEqual(adapter.decide(patch_event(f"*** Add File: docs/x.md\n+{bad}\n", None)), expected)
                # Move to decides: an ignored source moved to a checked path is judged as the new path.
                self.assertEqual(adapter.decide(patch_event(f"*** Update File: out/x.md\n*** Move to: docs/x.md\n@@\n+{bad}\n", repo)), expected)
                # Delete File is not judged.
                self.assertIsNone(adapter.decide(patch_event(f"*** Delete File: docs/x.md\n", repo)))
        # The config has exactly the documented shape; the command finds the repo root itself.
        cfg = json.loads((SCRIPTS.parents[1] / ".codex" / "hooks.json").read_text(encoding="utf-8"))
        self.assertEqual(list(cfg), ["hooks"])
        entries = cfg["hooks"]["PreToolUse"]
        self.assertEqual(len(entries), 1)
        handler = entries[0]["hooks"][0]
        self.assertEqual(handler["type"], "command")
        self.assertIn("$(git rev-parse --show-toplevel)/.codex/hooks/guard.py", handler["command"])
        self.assertNotIn("command", entries[0])


class GitPrecommitAndSetupHooksTest(unittest.TestCase):
    def load_git_precommit(self):
        try:
            return importlib.import_module("git_precommit")
        except ModuleNotFoundError as exc:
            self.fail(f"git_precommit module not found: {exc}")

    def load_setup_hooks(self):
        try:
            return importlib.import_module("setup_hooks")
        except ModuleNotFoundError as exc:
            self.fail(f"setup_hooks module not found: {exc}")

    def init_repo(self, path: Path, default_branch: str = "main") -> Path:
        subprocess.run(["git", "init", "-q", "-b", default_branch, str(path)], check=True)
        subprocess.run(["git", "-C", str(path), "config", "user.name", "Test User"], check=True)
        subprocess.run(["git", "-C", str(path), "config", "user.email", "test@example.com"], check=True)
        return path

    def commit_file(self, repo: Path, rel: str, content: str, msg: str = "commit") -> Path:
        p = write(repo, rel, content)
        subprocess.run(["git", "-C", str(repo), "add", rel], check=True)
        subprocess.run(["git", "-C", str(repo), "commit", "--no-verify", "-m", msg], check=True)
        return p

    def run_main(self, mod, argv: list[str]) -> tuple[int, str, str]:
        out = io.StringIO()
        err = io.StringIO()
        patchers = [
            contextlib.redirect_stdout(out),
            contextlib.redirect_stderr(err),
        ]
        if hasattr(mod, "sys"):
            patchers.append(patch.object(mod.sys, "stdout", out))
            patchers.append(patch.object(mod.sys, "stderr", err))
        with contextlib.ExitStack() as stack:
            for p in patchers:
                stack.enter_context(p)
            code = mod.main(argv)
        return code, out.getvalue(), err.getvalue()

    def test_precommit_case1_main_protected_branch(self) -> None:
        mod = self.load_git_precommit()
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo = Path(tmp_dir) / "repo"
            self.init_repo(repo, default_branch="main")
            self.commit_file(repo, "init.txt", "initial\n", "initial commit")

            write(repo, "docs/clean.md", "clean content\n")
            subprocess.run(["git", "-C", str(repo), "add", "docs/clean.md"], check=True)

            expected_reason = guard_rules.protected_branch_reason("main")
            self.assertIsNotNone(expected_reason)
            self.assertEqual(mod.check(repo), [expected_reason])

            code, out, err = self.run_main(mod, ["--root", str(repo)])
            self.assertEqual(code, 1)
            self.assertIn(expected_reason, err)
            self.assertIn("--no-verify", err)

    def test_precommit_case2_feature_machine_path_and_clean(self) -> None:
        mod = self.load_git_precommit()
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo = Path(tmp_dir) / "repo"
            self.init_repo(repo, default_branch="main")
            self.commit_file(repo, "init.txt", "initial\n", "initial commit")
            subprocess.run(["git", "-C", str(repo), "checkout", "-b", "feature/x"], check=True)

            bad_line = f"Install to {DRIVE}tools"
            write(repo, "docs/a.md", bad_line + "\n")
            subprocess.run(["git", "-C", str(repo), "add", "docs/a.md"], check=True)

            expected_reason = guard_rules.machine_path_reason([bad_line])
            self.assertIsNotNone(expected_reason)
            self.assertEqual(mod.check(repo), [expected_reason])

            code_bad, _, err_bad = self.run_main(mod, ["--root", str(repo)])
            self.assertEqual(code_bad, 1)
            self.assertIn(expected_reason, err_bad)
            self.assertIn("--no-verify", err_bad)

            subprocess.run(["git", "-C", str(repo), "rm", "-f", "docs/a.md"], check=True)
            write(repo, "docs/clean.md", "clean content\n")
            subprocess.run(["git", "-C", str(repo), "add", "docs/clean.md"], check=True)

            self.assertEqual(mod.check(repo), [])
            code_clean, out_clean, err_clean = self.run_main(mod, ["--root", str(repo)])
            self.assertEqual(code_clean, 0)
            self.assertEqual(err_clean, "")

    def test_precommit_case3_only_added_lines_count(self) -> None:
        mod = self.load_git_precommit()
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo = Path(tmp_dir) / "repo"
            self.init_repo(repo, default_branch="main")
            self.commit_file(repo, "init.txt", "initial\n", "initial commit")
            subprocess.run(["git", "-C", str(repo), "checkout", "-b", "feature/x"], check=True)

            # 1. Committed file containing a machine path, then a staged change that adds a clean line to it -> []
            file1 = "docs/file1.md"
            self.commit_file(repo, file1, f"existing bad path: {DRIVE}tools\n", "commit bad file")
            write(repo, file1, f"existing bad path: {DRIVE}tools\nclean added line\n")
            subprocess.run(["git", "-C", str(repo), "add", file1], check=True)

            self.assertEqual(mod.check(repo), [])
            code1, _, err1 = self.run_main(mod, ["--root", str(repo)])
            self.assertEqual(code1, 0)
            self.assertEqual(err1, "")

            # 2. A staged deletion of a file that contains a machine path -> []
            file2 = "docs/file2.md"
            self.commit_file(repo, file2, f"to delete: {HOME}secret\n", "commit second bad file")
            subprocess.run(["git", "-C", str(repo), "rm", file2], check=True)

            self.assertEqual(mod.check(repo), [])
            code2, _, err2 = self.run_main(mod, ["--root", str(repo)])
            self.assertEqual(code2, 0)
            self.assertEqual(err2, "")

    def test_precommit_case4_force_added_ignored_file_is_committed_so_checked(self) -> None:
        # Lead correction (090-11 U5 review): a file under an ignored folder that is staged with
        # `git add -f` is committed, so rule 1 (no machine paths in committed files) applies to it.
        # git check-ignore does not report tracked/staged files as ignored, which gives exactly that.
        mod = self.load_git_precommit()
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo = Path(tmp_dir) / "repo"
            self.init_repo(repo, default_branch="main")
            self.commit_file(repo, "init.txt", "initial\n", "initial commit")
            subprocess.run(["git", "-C", str(repo), "checkout", "-q", "-b", "feature/x"], check=True)

            self.commit_file(repo, ".gitignore", "out/\n", "add gitignore")
            line = f"cache at {DRIVE}temp"
            write(repo, "out/x.md", line + "\n")
            subprocess.run(["git", "-C", str(repo), "add", "-f", "out/x.md"], check=True)

            self.assertEqual(mod.check(repo), [guard_rules.machine_path_reason([line])])
            code, out, err = self.run_main(mod, ["--root", str(repo)])
            self.assertEqual(code, 1)

    def test_precommit_case5_detached_head_and_unborn_branch(self) -> None:
        mod = self.load_git_precommit()
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Detached HEAD (git checkout --detach): current_branch returns "", clean staged change -> []
            repo1 = Path(tmp_dir) / "repo1"
            self.init_repo(repo1, default_branch="main")
            self.commit_file(repo1, "init.txt", "initial\n", "initial commit")
            subprocess.run(["git", "-C", str(repo1), "checkout", "--detach"], check=True)

            self.assertEqual(mod.current_branch(repo1), "")
            write(repo1, "docs/clean.md", "clean content\n")
            subprocess.run(["git", "-C", str(repo1), "add", "docs/clean.md"], check=True)
            self.assertEqual(mod.check(repo1), [])
            code, out, err = self.run_main(mod, ["--root", str(repo1)])
            self.assertEqual(code, 0)
            self.assertEqual(err, "")

            # An unborn branch (fresh repo on main before the first commit): current_branch returns "main" and first commit refused
            repo2 = Path(tmp_dir) / "repo2"
            self.init_repo(repo2, default_branch="main")

            self.assertEqual(mod.current_branch(repo2), "main")
            write(repo2, "docs/first.md", "first commit content\n")
            subprocess.run(["git", "-C", str(repo2), "add", "docs/first.md"], check=True)

            expected_reason = guard_rules.protected_branch_reason("main")
            self.assertIsNotNone(expected_reason)
            self.assertEqual(mod.check(repo2), [expected_reason])
            code_unborn, _, err_unborn = self.run_main(mod, ["--root", str(repo2)])
            self.assertEqual(code_unborn, 1)
            self.assertIn(expected_reason, err_unborn)

    def test_precommit_case6_fail_closed_on_error(self) -> None:
        mod = self.load_git_precommit()
        with tempfile.TemporaryDirectory() as tmp_dir:
            not_git = Path(tmp_dir) / "not_git"
            not_git.mkdir()
            # Non-repo root causes git failure -> main returns 1 and stderr contains "guard failed"
            code, out, err = self.run_main(mod, ["--root", str(not_git)])
            self.assertEqual(code, 1)
            self.assertIn("guard failed", err)

            # Exception during check -> main returns 1 and stderr contains "guard failed"
            repo = Path(tmp_dir) / "repo"
            self.init_repo(repo)
            with patch.object(mod, "check", side_effect=RuntimeError("simulated error")):
                code_err, out_err, err_err = self.run_main(mod, ["--root", str(repo)])
                self.assertEqual(code_err, 1)
                self.assertIn("guard failed", err_err)

    def test_precommit_case7_binary_and_non_ascii_paths(self) -> None:
        mod = self.load_git_precommit()
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo = Path(tmp_dir) / "repo"
            self.init_repo(repo, default_branch="main")
            self.commit_file(repo, "init.txt", "initial\n", "initial commit")
            subprocess.run(["git", "-C", str(repo), "checkout", "-b", "feature/x"], check=True)

            # Staged binary file (bytes with NUL) -> no crash, [] for it
            bin_path = repo / "data.bin"
            bin_path.write_bytes(b"data\x00with\x00nulls\xff\xfe")
            subprocess.run(["git", "-C", str(repo), "add", "data.bin"], check=True)
            self.assertEqual(mod.check(repo), [])
            self.assertEqual(mod.staged_added_lines(repo).get("data.bin", []), [])
            code_bin, _, err_bin = self.run_main(mod, ["--root", str(repo)])
            self.assertEqual(code_bin, 0)
            self.assertEqual(err_bin, "")

            # Path with non-ASCII characters (Korean file name) with a machine path -> one reason (paths read with core.quotepath=off)
            korean_file = "docs/문서.md"
            bad_line = f"설치: {DRIVE}tools\n"
            write(repo, korean_file, bad_line)
            subprocess.run(["git", "-C", str(repo), "add", korean_file], check=True)

            expected_reason = guard_rules.machine_path_reason([bad_line])
            self.assertIsNotNone(expected_reason)
            self.assertEqual(mod.check(repo), [expected_reason])
            self.assertIn(korean_file, mod.staged_added_lines(repo))
            code_korean, _, err_korean = self.run_main(mod, ["--root", str(repo)])
            self.assertEqual(code_korean, 1)
            self.assertIn(expected_reason, err_korean)

    def test_setup_hooks_case8_install_idempotent_and_conflict(self) -> None:
        mod = self.load_setup_hooks()
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo = Path(tmp_dir) / "repo"
            self.init_repo(repo)

            # In a temp repo, hooks_installed is False
            self.assertIs(mod.hooks_installed(repo), False)

            # setup_hooks.main([...]) returns 0 and git config --local --get core.hooksPath is .githooks
            code, out, err = self.run_main(mod, ["--root", str(repo)])
            self.assertEqual(code, 0)
            res = subprocess.run(
                ["git", "-C", str(repo), "config", "--local", "--get", "core.hooksPath"],
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertEqual(res.stdout.strip(), ".githooks")
            self.assertIs(mod.hooks_installed(repo), True)

            # Running it again returns 0 and changes nothing
            code2, out2, err2 = self.run_main(mod, ["--root", str(repo)])
            self.assertEqual(code2, 0)
            res2 = subprocess.run(
                ["git", "-C", str(repo), "config", "--local", "--get", "core.hooksPath"],
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertEqual(res2.stdout.strip(), ".githooks")
            self.assertIs(mod.hooks_installed(repo), True)

            # With a different existing value (other) it returns 1 and leaves other
            subprocess.run(
                ["git", "-C", str(repo), "config", "--local", "core.hooksPath", "other"],
                check=True,
            )
            self.assertIs(mod.hooks_installed(repo), False)
            code3, out3, err3 = self.run_main(mod, ["--root", str(repo)])
            self.assertEqual(code3, 1)
            res3 = subprocess.run(
                ["git", "-C", str(repo), "config", "--local", "--get", "core.hooksPath"],
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertEqual(res3.stdout.strip(), "other")

            # In a temp dir that is not a git repo, hooks_installed is None
            not_git = Path(tmp_dir) / "not_git"
            not_git.mkdir()
            self.assertIsNone(mod.hooks_installed(not_git))

    def test_setup_hooks_case9_lint_docs_status_and_boot(self) -> None:
        expected = "git hooks: not installed (py -3 .agent/scripts/setup_hooks.py; the user decides per clone)"
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo = Path(tmp_dir) / "repo"
            self.init_repo(repo)
            write(repo, "docs/agent_todo.md", TODO)
            write(repo, "docs/known_issues.md", KNOWN)

            status = lint_docs.status_lines(repo)
            self.assertIn(expected, status)
            boot = lint_docs.boot_text(repo)
            self.assertIn(expected, boot)

            mod = self.load_setup_hooks()
            code, out, err = self.run_main(mod, ["--root", str(repo)])
            self.assertEqual(code, 0)

            status_after = lint_docs.status_lines(repo)
            self.assertNotIn(expected, status_after)
            boot_after = lint_docs.boot_text(repo)
            self.assertNotIn(expected, boot_after)

            non_git = Path(tmp_dir) / "non_git"
            non_git.mkdir()
            write(non_git, "docs/agent_todo.md", TODO)
            write(non_git, "docs/known_issues.md", KNOWN)
            self.assertNotIn(expected, lint_docs.status_lines(non_git))
            self.assertNotIn(expected, lint_docs.boot_text(non_git))

    def test_precommit_case10_hook_file_contract(self) -> None:
        hook_path = SCRIPTS.parents[1] / ".githooks" / "pre-commit"
        self.assertTrue(hook_path.is_file(), f".githooks/pre-commit not found: {hook_path}")
        raw = hook_path.read_bytes()
        self.assertNotIn(b"\r", raw, "pre-commit hook must not contain CR bytes (LF line endings only)")
        content = raw.decode("utf-8")
        self.assertTrue(content.startswith("#!/bin/sh"), "pre-commit hook must start with #!/bin/sh")
        self.assertIn(".agent/scripts/git_precommit.py", content, "pre-commit hook must refer to .agent/scripts/git_precommit.py")

    # --- Review fixes for U5 (090-11) -------------------------------------------------

    def test_precommit_review_gaps(self) -> None:
        mod = self.load_git_precommit()
        setup = self.load_setup_hooks()
        line = f"see {DRIVE}tools"
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo = Path(tmp_dir) / "repo"
            self.init_repo(repo, default_branch="main")
            self.commit_file(repo, "init.txt", "initial\n", "initial commit")
            # Exact stderr lines on a refusal.
            write(repo, "docs/a.md", "clean\n")
            subprocess.run(["git", "-C", str(repo), "add", "docs/a.md"], check=True)
            code, out, err = self.run_main(mod, ["--root", str(repo)])
            self.assertEqual(code, 1)
            self.assertEqual(out, "")
            self.assertEqual(err.splitlines(), [
                f"pre-commit: {guard_rules.protected_branch_reason('main')}",
                "pre-commit: commit refused (a person may bypass with git commit --no-verify; agents never do)",
            ])
            # Detached HEAD: the branch passes, the path check still runs.
            subprocess.run(["git", "-C", str(repo), "reset", "-q"], check=True)
            subprocess.run(["git", "-C", str(repo), "checkout", "-q", "--detach"], check=True)
            write(repo, "docs/b.md", line + "\n")
            subprocess.run(["git", "-C", str(repo), "add", "docs/b.md"], check=True)
            self.assertEqual(mod.check(repo), [guard_rules.machine_path_reason([line])])
            # A binary file that contains a machine path is not read as text.
            subprocess.run(["git", "-C", str(repo), "reset", "-q"], check=True)
            (repo / "blob.bin").write_bytes(b"\x00\x01" + line.encode("utf-8") + b"\x00\xff")
            subprocess.run(["git", "-C", str(repo), "add", "blob.bin"], check=True)
            self.assertEqual(mod.check(repo), [])
            # A clean commit prints nothing at all.
            code, out, err = self.run_main(mod, ["--root", str(repo)])
            self.assertEqual((code, out, err), (0, "", ""))
            # setup_hooks messages; the foreign value is named.
            code, out, err = self.run_main(setup, ["--root", str(repo)])
            self.assertEqual((code, out.strip()), (0, "installed: core.hooksPath=.githooks"))
            code, out, err = self.run_main(setup, ["--root", str(repo)])
            self.assertEqual((code, out.strip()), (0, "already installed"))
            subprocess.run(["git", "-C", str(repo), "config", "--local", "core.hooksPath", "other"], check=True)
            code, out, err = self.run_main(setup, ["--root", str(repo)])
            self.assertEqual(code, 1)
            self.assertIn("'other'", err)
        # The hook file's first line is exactly the shebang.
        hook = SCRIPTS.parents[1] / ".githooks" / "pre-commit"
        self.assertEqual(hook.read_bytes().split(b"\n", 1)[0], b"#!/bin/sh")

    def test_precommit_review_diff_parsing_cannot_be_fooled(self) -> None:
        # Final review fixes (090-11): every staged machine path is found whatever the diff looks like.
        mod = self.load_git_precommit()
        bad = f"see {DRIVE}tools"
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo = Path(tmp_dir) / "repo"
            self.init_repo(repo, default_branch="main")
            self.commit_file(repo, "init.txt", "initial\n", "initial commit")
            subprocess.run(["git", "-C", str(repo), "checkout", "-q", "-b", "feature/x"], check=True)
            # A user's diff config that changes the prefixes must not hide anything.
            subprocess.run(["git", "-C", str(repo), "config", "--local", "diff.mnemonicPrefix", "true"], check=True)
            subprocess.run(["git", "-C", str(repo), "config", "--local", "diff.noprefix", "true"], check=True)
            files = {
                "a.md": f"++ b/elsewhere\n{bad}\n",            # an added line that looks like a '+++' header
                "with space.md": f"{bad}\n",                   # a TAB follows such names on the '+++' line
                "폴더/한글.md": f"{bad}\n",
                "ff.md": f"x\x0c{bad}\n",                      # str.splitlines would cut at the form feed
            }
            if os.name != "nt":  # Windows refuses '"' in file names; git quotes such names even with quotepath=off
                files['quote"name.md'] = f"{bad}\n"
            for rel, text in files.items():
                path = repo / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(text.encode("utf-8"))
            subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
            added = mod.staged_added_lines(repo)
            self.assertEqual(sorted(added), sorted(files))
            self.assertEqual(added["a.md"], ["++ b/elsewhere", bad])
            self.assertEqual(added["ff.md"], [f"x\x0c{bad}"])
            for rel in files:  # each file is judged at its own path and refused
                self.assertIsNotNone(guard_rules.check_added_lines(repo / rel, added[rel], root=repo), rel)
            self.assertEqual(mod.check(repo), [guard_rules.machine_path_reason([bad]), guard_rules.machine_path_reason([f"x\x0c{bad}"])]
                             if guard_rules.machine_path_reason([bad]) != guard_rules.machine_path_reason([f"x\x0c{bad}"])
                             else [guard_rules.machine_path_reason([bad])])
            # symbolic-ref failing for another reason than a detached HEAD fails closed.
            with patch.object(agent_common, "git", side_effect=[MagicMock(returncode=0), MagicMock(returncode=128, stderr="boom", stdout="")]):
                with self.assertRaises(RuntimeError):
                    mod.current_branch(repo)

    def test_precommit_review_real_hook_through_git_commit(self) -> None:
        # End to end: the real .githooks/pre-commit runs through `git commit` in a temp repo.
        real = SCRIPTS.parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo = Path(tmp_dir) / "repo"
            self.init_repo(repo, default_branch="main")
            for rel in (".githooks/pre-commit", ".agent/scripts/git_precommit.py", ".agent/scripts/guard_rules.py",
                        ".agent/scripts/agent_common.py", ".agent/scripts/shell_commands.py"):
                (repo / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(real / rel, repo / rel)
            (repo / ".githooks/pre-commit").chmod(0o755)
            subprocess.run(["git", "-C", str(repo), "config", "--local", "core.hooksPath", ".githooks"], check=True)
            subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)

            def commit() -> subprocess.CompletedProcess[str]:
                return subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "x"], capture_output=True, text=True)

            refused = commit()  # first commit on main
            self.assertNotEqual(refused.returncode, 0)
            self.assertIn("non-negotiable rule 4", refused.stderr)
            subprocess.run(["git", "-C", str(repo), "checkout", "-q", "-b", "feature/x"], check=True)
            self.assertEqual(commit().returncode, 0, "a clean commit on a feature branch passes")
            write(repo, "docs/b.md", f"see {DRIVE}tools\n")
            subprocess.run(["git", "-C", str(repo), "add", "docs/b.md"], check=True)
            refused = commit()
            self.assertNotEqual(refused.returncode, 0)
            self.assertIn("non-negotiable rule 1", refused.stderr)
        # Once tracked, the hook is executable in the index (Linux skips a hook without the bit).
        listed = subprocess.run(["git", "-C", str(real), "ls-files", "-s", ".githooks/pre-commit"], capture_output=True, text=True).stdout
        if listed:
            self.assertTrue(listed.startswith("100755 "), listed)


if __name__ == "__main__":
    unittest.main(verbosity=2)
