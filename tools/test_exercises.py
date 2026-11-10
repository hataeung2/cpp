#!/usr/bin/env python3
"""Tests for tools/exercises.py (spec 070-17 AC-1, AC-4, AC-5).

Run: py -3 tools/test_exercises.py
"""
from __future__ import annotations

import contextlib
import io
import json
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import exercises  # noqa: E402
import lessons  # noqa: E402
import test_practice  # noqa: E402


def write(path: Path, data: bytes | str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, str):
        path.write_text(data, encoding="utf-8")
    else:
        path.write_bytes(data)


class ExercisesLoadTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="atugcc_test_ex_load_"))

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_load_good_file_auto_vs_self_and_defaults(self) -> None:
        toml_path = self.tmp / "exercises.toml"
        content = """
[[exercise]]
id = "self_ex"
title = "관찰 과제"
title_en = "Self exercise"
hint = "힌트"
hint_en = "Hint"

[[exercise]]
id = "auto_exit_only"
title = "자동 과제"
title_en = "Auto exercise with exit only"
exit = 0

[[exercise]]
id = "auto_fail_build"
title = "빌드 실패 과제"
title_en = "Auto fail build"
build = "fail"
build_expect = ["compiler error.*"]

[[exercise]]
id = "auto_source_only"
title = "소스 확인 과제"
title_en = "Auto source only"
source = [{ file = "main.cpp", lacks = ["mutable"] }]
"""
        write(toml_path, content)
        files = {"main.cpp": "lessons/tracks/01_t/01_a/main.cpp"}
        ex_list, problems = exercises.load(toml_path, files=files)

        errors = [p for p in problems if p.level == "ERROR"]
        self.assertEqual(errors, [])
        self.assertEqual(len(ex_list), 4)

        # 1. self_ex: no rule keys written
        self.assertEqual(ex_list[0].id, "self_ex")
        self.assertEqual(ex_list[0].kind, "self")
        self.assertEqual(ex_list[0].build, "ok")
        self.assertEqual(ex_list[0].exit, 0)
        self.assertEqual(ex_list[0].source, ())
        self.assertEqual(ex_list[0].expect, ())
        self.assertEqual(ex_list[0].forbid, ())

        # 2. auto_exit_only: only exit written -> auto, defaults
        self.assertEqual(ex_list[1].id, "auto_exit_only")
        self.assertEqual(ex_list[1].kind, "auto")
        self.assertEqual(ex_list[1].build, "ok")
        self.assertEqual(ex_list[1].exit, 0)

        # 3. auto_fail_build: build = "fail"
        self.assertEqual(ex_list[2].id, "auto_fail_build")
        self.assertEqual(ex_list[2].kind, "auto")
        self.assertEqual(ex_list[2].build, "fail")
        self.assertEqual(ex_list[2].build_expect, ("compiler error.*",))

        # 4. auto_source_only
        self.assertEqual(ex_list[3].id, "auto_source_only")
        self.assertEqual(ex_list[3].kind, "auto")
        self.assertEqual(len(ex_list[3].source), 1)
        self.assertEqual(ex_list[3].source[0].file, "main.cpp")
        self.assertEqual(ex_list[3].source[0].lacks, ("mutable",))

    def test_load_error_cases(self) -> None:
        cases = [
            ("toml_syntax", "[[exercise\nid = 1\n", "TOML syntax error"),
            ("unknown_key", '[[exercise]]\nid = "e1"\ntitle = "T"\nunknown_field = 123\n', "unknown key 'unknown_field'"),
            ("missing_id", '[[exercise]]\ntitle = "T"\n', "missing required key 'id'"),
            ("bad_id_hyphen", '[[exercise]]\nid = "bad-id"\ntitle = "T"\n', "must match [a-z0-9_]+"),
            ("bad_id_caps", '[[exercise]]\nid = "BadId"\ntitle = "T"\n', "must match [a-z0-9_]+"),
            ("duplicate_id", '[[exercise]]\nid = "e1"\ntitle = "T"\n[[exercise]]\nid = "e1"\ntitle = "T2"\n', "duplicate exercise id 'e1'"),
            ("build_maybe", '[[exercise]]\nid = "e1"\ntitle = "T"\nbuild = "maybe"\n', "'build' must be 'ok' or 'fail'"),
            ("exit_bool", '[[exercise]]\nid = "e1"\ntitle = "T"\nexit = true\n', "'exit' must be an integer, 'nonzero', or 'any'"),
            ("exit_sometimes", '[[exercise]]\nid = "e1"\ntitle = "T"\nexit = "sometimes"\n', "'exit' must be an integer, 'nonzero', or 'any'"),
            ("bad_regex_expect", '[[exercise]]\nid = "e1"\ntitle = "T"\nexpect = ["["]\n', "invalid regex in 'expect'"),
            ("bad_regex_build_expect", '[[exercise]]\nid = "e1"\ntitle = "T"\nbuild = "fail"\nbuild_expect = ["("]\n', "invalid regex in 'build_expect'"),
            ("bad_regex_source_has", '[[exercise]]\nid = "e1"\ntitle = "T"\nsource = [{ file = "main.cpp", has = ["*"] }]\n', "invalid regex in source 'has'"),
            ("build_fail_with_exit", '[[exercise]]\nid = "e1"\ntitle = "T"\nbuild = "fail"\nexit = 0\n', "'build = \"fail\"' cannot be combined with 'exit'"),
            ("build_fail_with_expect", '[[exercise]]\nid = "e1"\ntitle = "T"\nbuild = "fail"\nexpect = ["out"]\n', "'build = \"fail\"' cannot be combined with 'expect'"),
            ("build_fail_with_forbid", '[[exercise]]\nid = "e1"\ntitle = "T"\nbuild = "fail"\nforbid = ["bad"]\n', "'build = \"fail\"' cannot be combined with 'forbid'"),
            ("build_expect_without_build_fail", '[[exercise]]\nid = "e1"\ntitle = "T"\nbuild_expect = ["err"]\n', "'build_expect' requires 'build = \"fail\"'"),
        ]

        for name, toml_text, err_substr in cases:
            with self.subTest(case=name):
                path = self.tmp / f"{name}.toml"
                write(path, toml_text)
                _, problems = exercises.load(path, files={"main.cpp": "origin/main.cpp"})
                errors = [p.message for p in problems if p.level == "ERROR"]
                self.assertTrue(any(err_substr in msg for msg in errors), f"Expected {err_substr!r} in {errors}")

    def test_load_source_file_validation(self) -> None:
        # source.file not in files
        path1 = self.tmp / "not_in_files.toml"
        write(path1, '[[exercise]]\nid = "e1"\ntitle = "T"\nsource = [{ file = "unknown.cpp" }]\n')
        _, problems = exercises.load(path1, files={"main.cpp": "origin/main.cpp"})
        errors = [p.message for p in problems if p.level == "ERROR"]
        self.assertTrue(any("not a source of the lesson" in msg for msg in errors))

        # source.file mapped to None (ambiguous)
        path2 = self.tmp / "ambiguous.toml"
        write(path2, '[[exercise]]\nid = "e1"\ntitle = "T"\nsource = [{ file = "ambig.cpp" }]\n')
        _, problems = exercises.load(path2, files={"ambig.cpp": None})
        errors = [p.message for p in problems if p.level == "ERROR"]
        self.assertTrue(any("ambiguous" in msg for msg in errors))

    def test_load_warnings(self) -> None:
        # missing title_en
        p_no_title_en = self.tmp / "no_title_en.toml"
        write(p_no_title_en, '[[exercise]]\nid = "e1"\ntitle = "T"\n')
        _, problems = exercises.load(p_no_title_en)
        warns = [p.message for p in problems if p.level == "WARN"]
        self.assertTrue(any("missing 'title_en'" in m for m in warns))

        # hint without hint_en
        p_hint = self.tmp / "hint_no_en.toml"
        write(p_hint, '[[exercise]]\nid = "e1"\ntitle = "T"\ntitle_en = "T"\nhint = "H"\n')
        _, problems = exercises.load(p_hint)
        warns = [p.message for p in problems if p.level == "WARN"]
        self.assertTrue(any("'hint' given without 'hint_en'" in m for m in warns))

        # expect pattern matching empty string
        p_empty_pat = self.tmp / "empty_pat.toml"
        write(p_empty_pat, '[[exercise]]\nid = "e1"\ntitle = "T"\ntitle_en = "T"\nexpect = [".*"]\n')
        _, problems = exercises.load(p_empty_pat)
        warns = [p.message for p in problems if p.level == "WARN"]
        self.assertTrue(any("matches empty string" in m for m in warns))

        # README ## 연습 count mismatch
        p_readme = self.tmp / "readme_mismatch.toml"
        write(p_readme, '[[exercise]]\nid = "e1"\ntitle = "T"\ntitle_en = "T"\n')
        readme_text = "## 연습\n1. First\n2. Second\n"
        _, problems = exercises.load(p_readme, readme=readme_text)
        warns = [p.message for p in problems if p.level == "WARN"]
        self.assertTrue(any("README has 2 exercise item(s), but exercises.toml has 1 group(s)" in m for m in warns))

        # No WARN when README count matches with _a / _b sub-exercises counted once
        p_sub = self.tmp / "sub_ex.toml"
        write(p_sub, """
[[exercise]]
id = "ex1_a"
title = "T1"
title_en = "T1"

[[exercise]]
id = "ex1_b"
title = "T2"
title_en = "T2"
""")
        readme_one = "## 연습\n1. Only one exercise with multiple steps\n"
        _, problems = exercises.load(p_sub, readme=readme_one)
        warns = [p.message for p in problems if p.level == "WARN"]
        self.assertFalse(any("README has" in m for m in warns))

    def test_load_more_warnings(self) -> None:
        """answer / fail_hint without English, empty-matching build_expect and source.has (plan `load`)."""
        base = '[[exercise]]\nid = "e1"\ntitle = "T"\ntitle_en = "T"\n'
        cases = {
            "answer": (base + 'answer = "A"\n', "answer_en"),
            "fail_hint": (base + 'fail_hint = "F"\nexit = 1\n', "fail_hint_en"),
            "build_expect": (base + "build = \"fail\"\nbuild_expect = ['x?']\n", "x?"),
            "has": (base + "source = [{ file = \"main.cpp\", has = ['(a)*'] }]\n", "(a)*"),
        }
        for name, (text, needle) in cases.items():
            with self.subTest(name):
                path = self.tmp / f"warn_{name}.toml"
                write(path, text)
                defs, problems = exercises.load(path, {"main.cpp": "lessons/x/main.cpp"})
                self.assertEqual([p.level for p in problems], ["WARN"], problems)
                self.assertIn(needle, problems[0].message)
                self.assertEqual([d.id for d in defs], ["e1"])  # a WARN keeps the exercise

    def test_load_drops_error_exercise_and_keeps_others(self) -> None:
        path = self.tmp / "mixed.toml"
        content = """
[[exercise]]
id = "broken_ex"
title = "Broken"
title_en = "Broken"
unknown_key = "bad"

[[exercise]]
id = "valid_ex"
title = "Valid"
title_en = "Valid"
exit = 0
"""
        write(path, content)
        ex_list, problems = exercises.load(path)
        self.assertEqual(len(ex_list), 1)
        self.assertEqual(ex_list[0].id, "valid_ex")
        errors = [p.message for p in problems if p.level == "ERROR"]
        self.assertTrue(any("unknown key 'unknown_key'" in m for m in errors))


class ReadmeItemsTest(unittest.TestCase):
    def test_readme_items(self) -> None:
        # None without ## 연습
        self.assertIsNone(exercises.readme_items("# Title\n\nSome text\n"))

        # Counts only numbered lines under ## 연습
        text = """# Lesson
## 개요
1. Intro item not counted

## 연습
1. Exercise 1
- bullet not counted
2. Exercise 2
   details
3. Exercise 3

## 다음 레슨
1. Next item not counted
"""
        self.assertEqual(exercises.readme_items(text), 3)

        # Empty ## 연습 section
        text_empty = "## 연습\nNo items here\n## Next\n"
        self.assertEqual(exercises.readme_items(text_empty), 0)


class EvaluateTest(unittest.TestCase):
    def test_build_fail_rules(self) -> None:
        ex = exercises.Exercise(
            id="bf",
            title="T",
            build="fail",
            build_expect=("error: cannot convert.*",),
            rules_written=True,
        )

        # 1. Build ok -> build_fail failure
        run_ok = exercises.RunResult(build_ok=True, ran=False)
        res = exercises.evaluate([ex], run_ok, files={}, modified=True)
        self.assertFalse(res[0]["passed"])
        self.assertEqual(res[0]["failures"], [{"rule": "build_fail"}])

        # 2. Build failed and build_expect matches -> pass
        run_matched = exercises.RunResult(
            build_ok=False,
            build_log="some header\nerror: cannot convert int to string\nmore lines",
        )
        res = exercises.evaluate([ex], run_matched, files={}, modified=True)
        self.assertTrue(res[0]["passed"])
        self.assertEqual(res[0]["failures"], [])

        # 3. Build failed and build_expect does not match -> build_expect failure
        run_mismatch = exercises.RunResult(
            build_ok=False,
            build_log="error: unknown identifier foo\n",
        )
        res = exercises.evaluate([ex], run_mismatch, files={}, modified=True)
        self.assertFalse(res[0]["passed"])
        self.assertEqual(
            res[0]["failures"],
            [{"rule": "build_expect", "pattern": "error: cannot convert.*"}],
        )

    def test_build_ok_and_not_run_rules(self) -> None:
        ex = exercises.Exercise(id="bo", title="T", build="ok", exit=0, rules_written=True)

        # Build failed -> build_ok failure
        run_build_fail = exercises.RunResult(build_ok=False, build_log="err")
        res = exercises.evaluate([ex], run_build_fail, files={}, modified=True)
        self.assertFalse(res[0]["passed"])
        self.assertEqual(res[0]["failures"], [{"rule": "build_ok"}])

        # Build ok but ran=False -> not_run failure
        run_not_run = exercises.RunResult(build_ok=True, ran=False)
        res = exercises.evaluate([ex], run_not_run, files={}, modified=True)
        self.assertFalse(res[0]["passed"])
        self.assertEqual(res[0]["failures"], [{"rule": "not_run"}])

    def test_exit_rules(self) -> None:
        # Expected 0, actual 1
        ex0 = exercises.Exercise(id="e0", title="T", exit=0, rules_written=True)
        run1 = exercises.RunResult(build_ok=True, ran=True, exit_code=1)
        res = exercises.evaluate([ex0], run1, files={}, modified=True)
        self.assertFalse(res[0]["passed"])
        self.assertEqual(res[0]["failures"], [{"rule": "exit", "expected": 0, "actual": 1}])

        # Expected 1, actual 2
        ex1 = exercises.Exercise(id="e1", title="T", exit=1, rules_written=True)
        run2 = exercises.RunResult(build_ok=True, ran=True, exit_code=2)
        res = exercises.evaluate([ex1], run2, files={}, modified=True)
        self.assertFalse(res[0]["passed"])
        self.assertEqual(res[0]["failures"], [{"rule": "exit", "expected": 1, "actual": 2}])

        # Integer exit with signal -> fail
        run_sig = exercises.RunResult(build_ok=True, ran=True, exit_code=None, signal="SIGSEGV")
        res = exercises.evaluate([ex0], run_sig, files={}, modified=True)
        self.assertFalse(res[0]["passed"])
        self.assertEqual(res[0]["failures"], [{"rule": "exit", "expected": 0, "actual": "SIGSEGV"}])

        # exit = "nonzero"
        ex_nz = exercises.Exercise(id="enz", title="T", exit="nonzero", rules_written=True)
        # code 3 -> pass
        run_nz3 = exercises.RunResult(build_ok=True, ran=True, exit_code=3)
        self.assertTrue(exercises.evaluate([ex_nz], run_nz3, files={}, modified=True)[0]["passed"])
        # signal SIGABRT -> pass
        run_nz_sig = exercises.RunResult(build_ok=True, ran=True, signal="SIGABRT")
        self.assertTrue(exercises.evaluate([ex_nz], run_nz_sig, files={}, modified=True)[0]["passed"])
        # code 0 -> fail
        run_nz0 = exercises.RunResult(build_ok=True, ran=True, exit_code=0)
        res_nz0 = exercises.evaluate([ex_nz], run_nz0, files={}, modified=True)
        self.assertFalse(res_nz0[0]["passed"])
        self.assertEqual(res_nz0[0]["failures"], [{"rule": "exit", "expected": "nonzero", "actual": 0}])

        # exit = "any"
        ex_any = exercises.Exercise(id="eany", title="T", exit="any", rules_written=True)
        self.assertTrue(exercises.evaluate([ex_any], run1, files={}, modified=True)[0]["passed"])
        self.assertTrue(exercises.evaluate([ex_any], run_sig, files={}, modified=True)[0]["passed"])
        self.assertTrue(exercises.evaluate([ex_any], run_nz0, files={}, modified=True)[0]["passed"])

    def test_expect_and_forbid_rules(self) -> None:
        ex = exercises.Exercise(
            id="ef",
            title="T",
            expect=(r"^result: \d+$",),
            forbid=(r"FAIL",),
            rules_written=True,
        )

        # Match expect on one line of several, no forbid -> pass
        run_pass = exercises.RunResult(
            build_ok=True,
            ran=True,
            exit_code=0,
            stdout="starting...\nresult: 42\ncompleted\n",
        )
        res_pass = exercises.evaluate([ex], run_pass, files={}, modified=True)
        self.assertTrue(res_pass[0]["passed"])

        # No match on expect -> expect failure
        run_no_expect = exercises.RunResult(
            build_ok=True,
            ran=True,
            exit_code=0,
            stdout="starting...\ncompleted\n",
        )
        res_no_expect = exercises.evaluate([ex], run_no_expect, files={}, modified=True)
        self.assertFalse(res_no_expect[0]["passed"])
        self.assertEqual(
            res_no_expect[0]["failures"],
            [{"rule": "expect", "pattern": r"^result: \d+$"}],
        )

        # Match forbid -> forbid failure with line
        run_forbid = exercises.RunResult(
            build_ok=True,
            ran=True,
            exit_code=0,
            stdout="result: 42\n[FAIL] test failed\n",
        )
        res_forbid = exercises.evaluate([ex], run_forbid, files={}, modified=True)
        self.assertFalse(res_forbid[0]["passed"])
        self.assertEqual(
            res_forbid[0]["failures"],
            [{"rule": "forbid", "pattern": "FAIL", "line": "[FAIL] test failed"}],
        )

    def test_source_rules(self) -> None:
        src = exercises.Source(file="main.cpp", has=(r"\band_then\b",), lacks=(r"\bmutable\b",))
        ex = exercises.Exercise(id="src_ex", title="T", source=(src,), rules_written=True)

        run = exercises.RunResult(build_ok=True, ran=True, exit_code=0)

        # Pass: has and_then, lacks mutable
        files_ok = {"main.cpp": "auto x = opt.and_then(f);\nreturn 0;\n"}
        res_ok = exercises.evaluate([ex], run, files=files_ok, modified=True)
        self.assertTrue(res_ok[0]["passed"])

        # Fail has: and_then missing
        files_no_has = {"main.cpp": "return 0;\n"}
        res_no_has = exercises.evaluate([ex], run, files=files_no_has, modified=True)
        self.assertFalse(res_no_has[0]["passed"])
        self.assertEqual(
            res_no_has[0]["failures"],
            [{"rule": "has", "file": "main.cpp", "pattern": r"\band_then\b"}],
        )

        # Fail lacks: mutable present, carries line
        files_lacks = {"main.cpp": "auto f = [x]() mutable { return ++x; };\nauto y = opt.and_then(f);\n"}
        res_lacks = exercises.evaluate([ex], run, files=files_lacks, modified=True)
        self.assertFalse(res_lacks[0]["passed"])
        self.assertEqual(
            res_lacks[0]["failures"],
            [{"rule": "lacks", "file": "main.cpp", "pattern": r"\bmutable\b", "line": "auto f = [x]() mutable { return ++x; };"}],
        )

        # Missing file (mapped to None)
        files_missing = {"main.cpp": None}
        res_missing = exercises.evaluate([ex], run, files=files_missing, modified=True)
        self.assertFalse(res_missing[0]["passed"])
        self.assertEqual(
            res_missing[0]["failures"],
            [{"rule": "missing_file", "file": "main.cpp"}],
        )

    def test_crlf_matching(self) -> None:
        ex = exercises.Exercise(
            id="crlf_ex",
            title="T",
            expect=(r"^exact_line$",),
            source=(exercises.Source(file="main.cpp", has=(r"^int main\(\)$",)),),
            rules_written=True,
        )
        run = exercises.RunResult(build_ok=True, ran=True, exit_code=0, stdout="hello\r\nexact_line\r\nbye\r\n")
        files = {"main.cpp": "int main()\r\n{\r\n    return 0;\r\n}\r\n"}
        res = exercises.evaluate([ex], run, files=files, modified=True)
        self.assertTrue(res[0]["passed"])

    def test_unmodified_copy_never_passes(self) -> None:
        ex = exercises.Exercise(id="e_unmod", title="T", exit=0, rules_written=True)
        run = exercises.RunResult(build_ok=True, ran=True, exit_code=0)
        res = exercises.evaluate([ex], run, files={}, modified=False)
        self.assertFalse(res[0]["passed"])
        self.assertEqual(res[0]["failures"], [{"rule": "unmodified"}])

    def test_stopped_run(self) -> None:
        # stopped=True -> not_finished; no build or exit failures, but source rules still listed
        src = exercises.Source(file="main.cpp", has=(r"TARGET",))
        ex = exercises.Exercise(id="e_stop", title="T", exit=0, source=(src,), rules_written=True)

        run = exercises.RunResult(build_ok=False, ran=False, stopped=True)
        files = {"main.cpp": "no target here\n"}
        res = exercises.evaluate([ex], run, files=files, modified=True)
        self.assertFalse(res[0]["passed"])
        rules = [f["rule"] for f in res[0]["failures"]]
        self.assertIn("not_finished", rules)
        self.assertIn("has", rules)
        self.assertNotIn("build_ok", rules)
        self.assertNotIn("exit", rules)

    def test_truncated_stdout(self) -> None:
        # truncated=True with expect -> checked=False, truncated failure, passed=False
        ex_expect = exercises.Exercise(id="e_trunc", title="T", expect=(r"answer",), rules_written=True)
        run_trunc = exercises.RunResult(build_ok=True, ran=True, exit_code=0, truncated=True, stdout="ans")
        res = exercises.evaluate([ex_expect], run_trunc, files={}, modified=True)
        self.assertFalse(res[0]["checked"])
        self.assertFalse(res[0]["passed"])
        self.assertEqual(res[0]["failures"], [{"rule": "truncated"}])

        # truncated=True without expect or forbid -> normal result (passed=True)
        ex_no_out = exercises.Exercise(id="e_no_out", title="T", exit=0, rules_written=True)
        res_no_out = exercises.evaluate([ex_no_out], run_trunc, files={}, modified=True)
        self.assertTrue(res_no_out[0]["checked"])
        self.assertTrue(res_no_out[0]["passed"])
        self.assertEqual(res_no_out[0]["failures"], [])

    def test_self_exercises_excluded_and_definition_order_preserved(self) -> None:
        ex_self = exercises.Exercise(id="s1", title="Self", rules_written=False)
        ex_auto1 = exercises.Exercise(id="a1", title="Auto 1", exit=0, rules_written=True)
        ex_auto2 = exercises.Exercise(id="a2", title="Auto 2", exit=0, rules_written=True)

        run = exercises.RunResult(build_ok=True, ran=True, exit_code=0)
        res = exercises.evaluate([ex_auto1, ex_self, ex_auto2], run, files={}, modified=True)

        ids = [r["id"] for r in res]
        self.assertEqual(ids, ["a1", "a2"])
        self.assertTrue(all(r["passed"] for r in res))


class MessageTest(unittest.TestCase):
    def test_all_messages_produce_non_empty_sentence(self) -> None:
        params_map = {
            "unmodified": {},
            "not_finished": {},
            "build_fail": {},
            "build_expect": {"pattern": r"error: .*"},
            "build_ok": {},
            "not_run": {},
            "exit": {"expected": 0, "actual": 1},
            "expect": {"pattern": r"result: \d+"},
            "forbid": {"pattern": "FAIL", "line": "FAIL: test failed"},
            "truncated": {},
            "missing_file": {"file": "main.cpp"},
            "has": {"file": "main.cpp", "pattern": "and_then"},
            "lacks": {"file": "main.cpp", "pattern": "mutable", "line": "mutable int x;"},
        }

        for rule in exercises.MESSAGES:
            with self.subTest(rule=rule):
                params = {"rule": rule, **params_map.get(rule, {})}
                msg = exercises.message(params)
                self.assertTrue(len(msg) > 0)
                # Ensure no unfilled {brace} remains
                self.assertIsNone(re.search(r"\{[a-z_]+\}", msg))


class ProgressTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="atugcc_test_prog_"))
        self.prog = exercises.Progress(self.tmp)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_record_new_ids_and_keeps_timestamp(self) -> None:
        new1 = self.prog.record("lesson1", ["e1", "e2"], how="auto")
        self.assertEqual(new1, ["e1", "e2"])

        l1 = self.prog.lesson("lesson1")
        self.assertIn("e1", l1)
        self.assertIn("e2", l1)
        time_e1 = l1["e1"]["passed"]

        # Second record with overlapping ids
        new2 = self.prog.record("lesson1", ["e1", "e2", "e3"], how="auto")
        self.assertEqual(new2, ["e3"])

        l1_after = self.prog.lesson("lesson1")
        self.assertEqual(l1_after["e1"]["passed"], time_e1)
        self.assertIn("e3", l1_after)

    def test_set_self(self) -> None:
        # set_self True
        self.prog.set_self("lesson1", "self1", done=True)
        l1 = self.prog.lesson("lesson1")
        self.assertEqual(l1["self1"]["how"], "self")

        # set_self False removes self
        self.prog.set_self("lesson1", "self1", done=False)
        self.assertNotIn("self1", self.prog.lesson("lesson1"))

        # set_self False on auto pass does NOT remove it
        self.prog.record("lesson1", ["auto1"], how="auto")
        self.prog.set_self("lesson1", "auto1", done=False)
        self.assertIn("auto1", self.prog.lesson("lesson1"))
        self.assertEqual(self.prog.lesson("lesson1")["auto1"]["how"], "auto")

    def test_clear_removes_one_lesson_only(self) -> None:
        self.prog.record("l1", ["e1"])
        self.prog.record("l2", ["e2"])

        self.prog.clear("l1")
        self.assertEqual(self.prog.lesson("l1"), {})
        self.assertIn("e2", self.prog.lesson("l2"))

    def test_damaged_file_handling(self) -> None:
        bad_contents = [
            "{ bad json",
            json.dumps({"version": 2, "lessons": {}}),
            json.dumps({"version": 1, "lessons": {"l1": {"e1": {"passed": "2026-01-01", "how": "wrong"}}}}),
        ]

        prog_file = self.tmp / exercises.PROGRESS_FILE

        for bad in bad_contents:
            write(prog_file, bad)
            res = self.prog.lesson("l1")
            self.assertEqual(res, {})

            # Broken file was preserved
            broken_files = list(prog_file.parent.glob("progress.json.broken-*"))
            self.assertTrue(len(broken_files) > 0)

            # New valid empty progress file was started
            data = json.loads(prog_file.read_text(encoding="utf-8"))
            self.assertEqual(data["version"], 1)
            self.assertEqual(data["lessons"], {})

    def test_passed_counts_only_current_ids(self) -> None:
        self.prog.record("l1", ["e1", "deprecated_ex"])
        self.prog.record("l2", ["e2"])

        defs_by_lesson = {
            "l1": ["e1", "e3"],  # deprecated_ex is not in current defs
            "l2": ["e2"],
            "l3": ["e4"],
        }
        counts = self.prog.passed_counts(defs_by_lesson)
        self.assertEqual(counts, {"l1": 1, "l2": 1, "l3": 0})


class CheckPracticeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="atugcc_test_chk_prac_"))
        test_practice.make_test_tree(self.tmp)
        self.lesson_dir = self.tmp / "lessons/tracks/01_t/01_a"
        self.files_map = {"main.cpp": "lessons/tracks/01_t/01_a/main.cpp"}

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_check_practice_lifecycle(self) -> None:
        # 1. Write exercises.toml in lesson
        toml_content = """
[[exercise]]
id = "ex1"
title = "T"
title_en = "T"
expect = ["hello"]
"""
        write(self.lesson_dir / "exercises.toml", toml_content)

        # 2. Unchanged copy
        practice_main = self.tmp / "practice/lessons/tracks/01_t/01_a/main.cpp"
        origin_main = self.tmp / "lessons/tracks/01_t/01_a/main.cpp"
        write(practice_main, origin_main.read_bytes())

        run_hello = exercises.RunResult(build_ok=True, ran=True, exit_code=0, stdout="hello\n")
        out1 = exercises.check_practice(self.tmp, "a", self.lesson_dir, self.files_map, run_hello)
        self.assertEqual(len(out1["exercises"]), 1)
        self.assertFalse(out1["exercises"][0]["passed"])
        self.assertEqual(out1["exercises"][0]["failures"], [{"rule": "unmodified"}])
        # Nothing recorded in progress
        prog = exercises.Progress(self.tmp)
        self.assertEqual(prog.lesson("a"), {})

        # 3. Changed copy that satisfies rules
        write(practice_main, b"// modified\nint main() {}\n")
        out2 = exercises.check_practice(self.tmp, "a", self.lesson_dir, self.files_map, run_hello)
        self.assertEqual(len(out2["exercises"]), 1)
        self.assertTrue(out2["exercises"][0]["passed"])
        self.assertTrue(out2["exercises"][0]["new"])
        self.assertIn("ex1", prog.lesson("a"))

        # 4. Second call with same changed copy -> new is False
        out3 = exercises.check_practice(self.tmp, "a", self.lesson_dir, self.files_map, run_hello)
        self.assertTrue(out3["exercises"][0]["passed"])
        self.assertFalse(out3["exercises"][0]["new"])

        # 5. Reset copy to origin: result not passed, but progress record remains (AC-4)
        write(practice_main, origin_main.read_bytes())
        out4 = exercises.check_practice(self.tmp, "a", self.lesson_dir, self.files_map, run_hello)
        self.assertFalse(out4["exercises"][0]["passed"])
        self.assertIn("ex1", prog.lesson("a"))

    def test_check_practice_no_exercises_toml(self) -> None:
        out = exercises.check_practice(
            self.tmp, "a", self.lesson_dir, self.files_map, exercises.RunResult(build_ok=True)
        )
        self.assertEqual(out, {})

    def test_check_practice_broken_exercises_toml(self) -> None:
        write(self.lesson_dir / "exercises.toml", "[[exercise]]\nid = 'bad-id'\ntitle = 'T'\n")
        out = exercises.check_practice(
            self.tmp, "a", self.lesson_dir, self.files_map, exercises.RunResult(build_ok=True)
        )
        self.assertIn("exercisesError", out)
        self.assertIn("must match [a-z0-9_]+", out["exercisesError"])

    def test_check_practice_any_changed_copy_counts(self) -> None:
        """A change to the second file only (util.hpp) still makes the copy modified (Assumption 5)."""
        write(self.lesson_dir / "exercises.toml", '[[exercise]]\nid = "ex1"\ntitle = "T"\ntitle_en = "T"\nexit = 0\n')
        files = {"main.cpp": "lessons/tracks/01_t/01_a/main.cpp", "util.hpp": "lessons/tracks/01_t/01_a/util.hpp"}
        for name, origin in files.items():
            write(self.tmp / "practice" / origin, (self.tmp / origin).read_bytes())
        run = exercises.RunResult(build_ok=True, ran=True, exit_code=0)
        self.assertFalse(exercises.check_practice(self.tmp, "a", self.lesson_dir, files, run)["exercises"][0]["passed"])
        write(self.tmp / "practice" / files["util.hpp"], b"#pragma once\n// changed\n")
        self.assertTrue(exercises.check_practice(self.tmp, "a", self.lesson_dir, files, run)["exercises"][0]["passed"])

    def test_check_practice_unreadable_copy_is_reported(self) -> None:
        write(self.lesson_dir / "exercises.toml", '[[exercise]]\nid = "ex1"\ntitle = "T"\ntitle_en = "T"\nexit = 0\n')
        write(self.tmp / "practice" / self.files_map["main.cpp"], b"changed\n")
        with patch.object(Path, "read_bytes", side_effect=PermissionError("denied")):
            out = exercises.check_practice(self.tmp, "a", self.lesson_dir, self.files_map,
                                           exercises.RunResult(build_ok=True, ran=True, exit_code=0))
        self.assertIn("denied", out["exercisesError"])


class CliBuildTest(unittest.TestCase):
    def test_other_platform_preset_is_refused_before_building(self) -> None:
        class FakeBuild:
            @staticmethod
            def preset_platform(preset: str) -> str:
                return "Linux" if preset.startswith("linux-") else "Windows"

            @staticmethod
            def host_system() -> str:
                return "Windows"

        with patch.object(exercises.subprocess, "run") as run:
            with self.assertRaises(exercises._CliError) as caught:
                exercises._build(FakeBuild, "linux-x64-debug", "practice_a")
        run.assert_not_called()
        self.assertIn("WSL", str(caught.exception))


class CliVerifyTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="atugcc_test_cli_ver_"))
        test_practice.make_test_tree(self.tmp)
        self.lesson_dir = self.tmp / "lessons/tracks/01_t/01_a"
        # Pre-import tools module dependencies before patching ROOT
        exercises._tools()

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_cli_verify_exits_1_when_exercise_passes_on_original(self) -> None:
        # Exercise expects "hello", which the --exe command prints, and has no failing rule on origin
        toml_content = """
[[exercise]]
id = "ex_passes_on_origin"
title = "Passes on origin"
expect = ["hello"]
"""
        write(self.lesson_dir / "exercises.toml", toml_content)

        buf_out = io.StringIO()
        buf_err = io.StringIO()
        with patch.object(exercises, "ROOT", self.tmp), contextlib.redirect_stdout(buf_out), contextlib.redirect_stderr(buf_err):
            code = exercises.main(["verify", "a", "--exe", sys.executable, "-c", "print('hello')"])
            self.assertEqual(code, 1)
        self.assertIn("passes on the unchanged lesson", buf_err.getvalue())

    def test_cli_verify_exits_0_when_no_exercise_passes_on_original(self) -> None:
        # Exercise expects "solved_output", which the unchanged lesson run does not produce
        toml_content = """
[[exercise]]
id = "ex_requires_change"
title = "Requires change"
expect = ["solved_output"]
"""
        write(self.lesson_dir / "exercises.toml", toml_content)

        buf_out = io.StringIO()
        buf_err = io.StringIO()
        with patch.object(exercises, "ROOT", self.tmp), contextlib.redirect_stdout(buf_out), contextlib.redirect_stderr(buf_err):
            code = exercises.main(["verify", "a", "--exe", sys.executable, "-c", "print('hello')"])
            self.assertEqual(code, 0)
        self.assertIn("no automatic exercise passes on the unchanged lesson", buf_out.getvalue())

    def test_cli_verify_exits_0_when_no_exercises_toml(self) -> None:
        buf_out = io.StringIO()
        buf_err = io.StringIO()
        with patch.object(exercises, "ROOT", self.tmp), contextlib.redirect_stdout(buf_out), contextlib.redirect_stderr(buf_err):
            code = exercises.main(["verify", "a", "--exe", sys.executable, "-c", "print('hello')"])
            self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
