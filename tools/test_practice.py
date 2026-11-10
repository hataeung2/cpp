#!/usr/bin/env python3
"""Tests for tools/practice.py (spec 070-16 AC-1, AC-4, AC-5).

Run: py -3 tools/test_practice.py
"""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import practice  # noqa: E402


def write(path: Path, data: bytes | str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, str):
        path.write_text(data, encoding="utf-8")
    else:
        path.write_bytes(data)


def make_test_tree(root: Path) -> None:
    write(root / "lessons/tags.toml", '[tag]\nko = "태그"\nen = "Tag"\n')
    write(root / "lessons/tracks/01_t/track.toml",
          'title = "Track 1"\ntitle_en = "Track 1 EN"\nsummary = "S"\nsummary_en = "S"\n')
    write(root / "lessons/tracks/01_t/01_a/lesson.toml",
          'id = "a"\ntitle = "A"\ntitle_en = "A"\nsummary = "S"\nsummary_en = "S"\n'
          'sources = ["main.cpp", "util.hpp"]\nuses = ["unit:u"]\n')
    write(root / "lessons/tracks/01_t/01_a/main.cpp", b"#include \"util.hpp\"\r\nint main() {}\r\n")
    write(root / "lessons/tracks/01_t/01_a/util.hpp", b"#pragma once\n// util\n")
    write(root / "lessons/units/u/unit.toml",
          'id = "u"\ntitle = "U"\ntitle_en = "U"\nsummary = "S"\nsummary_en = "S"\nfiles = ["u.hpp"]\n')
    write(root / "lessons/units/u/u.hpp", b"#pragma once\n// u\n")


class PracticeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="atugcc_practice_"))
        make_test_tree(self.tmp)
        self.ws = practice.Workspace(self.tmp)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_01_start_copies_files_and_records_state(self) -> None:
        res = self.ws.start("a")
        expected_files = [
            ("lessons/tracks/01_t/01_a/lesson.toml", "practice/lessons/tracks/01_t/01_a/lesson.toml"),
            ("lessons/tracks/01_t/01_a/main.cpp", "practice/lessons/tracks/01_t/01_a/main.cpp"),
            ("lessons/tracks/01_t/01_a/util.hpp", "practice/lessons/tracks/01_t/01_a/util.hpp"),
            ("lessons/units/u/unit.toml", "practice/lessons/units/u/unit.toml"),
            ("lessons/units/u/u.hpp", "practice/lessons/units/u/u.hpp"),
        ]
        for origin, copy in expected_files:
            self.assertTrue((self.tmp / copy).is_file())
            self.assertEqual((self.tmp / copy).read_bytes(), (self.tmp / origin).read_bytes())

        # Verify CRLF is preserved in copy
        main_bytes = (self.tmp / "practice/lessons/tracks/01_t/01_a/main.cpp").read_bytes()
        self.assertTrue(main_bytes.endswith(b"\r\n"))

        # Verify state.json
        state_path = self.tmp / practice.STATE_FILE
        self.assertTrue(state_path.is_file())
        state = json.loads(state_path.read_text(encoding="utf-8"))
        self.assertEqual(state["version"], 1)

        recorded = state["files"]
        for origin, copy in expected_files:
            self.assertIn(copy, recorded)
            self.assertEqual(recorded[copy]["origin"], origin)
            origin_sha = hashlib.sha256((self.tmp / origin).read_bytes()).hexdigest()
            self.assertEqual(recorded[copy]["baseSha"], origin_sha)

        # Check return value states are all 'same'
        lesson_states = [f["state"] for f in res["files"]]
        self.assertEqual(lesson_states, ["same", "same", "same"])
        unit_states = [f["state"] for f in res["units"][0]["files"]]
        self.assertEqual(unit_states, ["same", "same"])

    def test_02_start_again_after_editing_leaves_edit_and_reports_modified(self) -> None:
        self.ws.start("a")
        copy_main = self.tmp / "practice/lessons/tracks/01_t/01_a/main.cpp"
        write(copy_main, b"// modified by user\r\nint main() {}\r\n")

        res = self.ws.start("a")
        self.assertEqual(copy_main.read_bytes(), b"// modified by user\r\nint main() {}\r\n")

        file_states = {f["path"]: f["state"] for f in res["files"]}
        self.assertEqual(file_states["practice/lessons/tracks/01_t/01_a/main.cpp"], "modified")
        self.assertEqual(file_states["practice/lessons/tracks/01_t/01_a/util.hpp"], "same")

    def test_03_handmade_copy_before_start_kept_and_recorded(self) -> None:
        copy_util = self.tmp / "practice/lessons/tracks/01_t/01_a/util.hpp"
        copy_main = self.tmp / "practice/lessons/tracks/01_t/01_a/main.cpp"
        write(copy_util, (self.tmp / "lessons/tracks/01_t/01_a/util.hpp").read_bytes())
        write(copy_main, b"// handmade modified\n")

        res = self.ws.start("a")
        self.assertEqual(copy_main.read_bytes(), b"// handmade modified\n")

        state = json.loads((self.tmp / practice.STATE_FILE).read_text(encoding="utf-8"))
        self.assertIn("practice/lessons/tracks/01_t/01_a/main.cpp", state["files"])
        self.assertIn("practice/lessons/tracks/01_t/01_a/util.hpp", state["files"])

        file_states = {f["path"]: f["state"] for f in res["files"]}
        self.assertEqual(file_states["practice/lessons/tracks/01_t/01_a/util.hpp"], "same")
        self.assertEqual(file_states["practice/lessons/tracks/01_t/01_a/main.cpp"], "modified")

    def test_04_origin_change_follows_unmodified_and_marks_modified_both(self) -> None:
        self.ws.start("a")
        copy_main = self.tmp / "practice/lessons/tracks/01_t/01_a/main.cpp"
        copy_util = self.tmp / "practice/lessons/tracks/01_t/01_a/util.hpp"
        write(copy_main, b"// user edit\n")

        write(self.tmp / "lessons/tracks/01_t/01_a/util.hpp", b"// new util origin\n")
        write(self.tmp / "lessons/tracks/01_t/01_a/main.cpp", b"// new main origin\n")

        st = self.ws.status("a")
        file_states = {f["path"]: f["state"] for f in st["files"]}

        self.assertEqual(file_states["practice/lessons/tracks/01_t/01_a/util.hpp"], "same")
        self.assertEqual(copy_util.read_bytes(), b"// new util origin\n")

        self.assertEqual(file_states["practice/lessons/tracks/01_t/01_a/main.cpp"], "both")
        self.assertEqual(copy_main.read_bytes(), b"// user edit\n")

    def test_05_manifests_always_follow(self) -> None:
        self.ws.start("a")
        copy_toml = self.tmp / "practice/lessons/tracks/01_t/01_a/lesson.toml"
        write(copy_toml, copy_toml.read_text(encoding="utf-8") + "# hand edit\n")

        origin_toml = self.tmp / "lessons/tracks/01_t/01_a/lesson.toml"
        write(origin_toml, origin_toml.read_text(encoding="utf-8").replace('summary = "S"', 'summary = "New"'))

        self.ws.status("a")
        self.assertEqual(copy_toml.read_bytes(), origin_toml.read_bytes())

    def test_06_origin_manifest_add_and_drop_source(self) -> None:
        self.ws.start("a")
        write(self.tmp / "lessons/tracks/01_t/01_a/extra.cpp", b"// extra\n")
        origin_toml = self.tmp / "lessons/tracks/01_t/01_a/lesson.toml"
        write(origin_toml, origin_toml.read_text(encoding="utf-8").replace(
            'sources = ["main.cpp", "util.hpp"]', 'sources = ["main.cpp", "extra.cpp"]'))

        st = self.ws.status("a")
        file_paths = {f["path"]: f["state"] for f in st["files"]}

        extra_copy = "practice/lessons/tracks/01_t/01_a/extra.cpp"
        self.assertIn(extra_copy, file_paths)
        self.assertEqual(file_paths[extra_copy], "same")
        self.assertEqual((self.tmp / extra_copy).read_bytes(), b"// extra\n")

        util_copy = "practice/lessons/tracks/01_t/01_a/util.hpp"
        self.assertNotIn(util_copy, file_paths)
        self.assertFalse((self.tmp / util_copy).exists())

        state = json.loads((self.tmp / practice.STATE_FILE).read_text(encoding="utf-8"))
        self.assertNotIn(util_copy, state["files"])

        # util.hpp was moved to a backup folder
        backup_files = list((self.tmp / practice.BACKUP_DIR).glob("*/" + util_copy))
        self.assertEqual(len(backup_files), 1)
        self.assertEqual(backup_files[0].read_bytes(), b"#pragma once\n// util\n")

    def test_07_reset_lesson_scope_and_backup(self) -> None:
        self.ws.start("a")
        copy_main = self.tmp / "practice/lessons/tracks/01_t/01_a/main.cpp"
        copy_u = self.tmp / "practice/lessons/units/u/u.hpp"
        write(copy_main, b"// modified main\n")
        write(copy_u, b"// modified unit\n")

        res = self.ws.reset(lesson="a")
        main_rel = "practice/lessons/tracks/01_t/01_a/main.cpp"
        self.assertEqual(res["reset"], [main_rel])
        self.assertIsNotNone(res["backup"])

        backup_file = self.tmp / res["backup"] / main_rel
        self.assertEqual(backup_file.read_bytes(), b"// modified main\n")

        self.assertEqual(copy_main.read_bytes(), (self.tmp / "lessons/tracks/01_t/01_a/main.cpp").read_bytes())
        st = self.ws.status("a")
        file_states = {f["path"]: f["state"] for f in st["files"]}
        self.assertEqual(file_states[main_rel], "same")

        # Unit copy was not reset
        self.assertEqual(copy_u.read_bytes(), b"// modified unit\n")

    def test_08_reset_unit_and_file_scope(self) -> None:
        self.ws.start("a")
        copy_main = self.tmp / "practice/lessons/tracks/01_t/01_a/main.cpp"
        copy_util = self.tmp / "practice/lessons/tracks/01_t/01_a/util.hpp"
        copy_u = self.tmp / "practice/lessons/units/u/u.hpp"
        write(copy_main, b"// edit main\n")
        write(copy_util, b"// edit util\n")
        write(copy_u, b"// edit unit\n")

        res_unit = self.ws.reset(unit="u")
        self.assertEqual(res_unit["reset"], ["practice/lessons/units/u/u.hpp"])
        self.assertEqual(copy_u.read_bytes(), (self.tmp / "lessons/units/u/u.hpp").read_bytes())
        self.assertEqual(copy_main.read_bytes(), b"// edit main\n")
        self.assertEqual(copy_util.read_bytes(), b"// edit util\n")

        res_file = self.ws.reset(path="practice/lessons/tracks/01_t/01_a/main.cpp")
        self.assertEqual(res_file["reset"], ["practice/lessons/tracks/01_t/01_a/main.cpp"])
        self.assertEqual(copy_main.read_bytes(), (self.tmp / "lessons/tracks/01_t/01_a/main.cpp").read_bytes())
        self.assertEqual(copy_util.read_bytes(), b"// edit util\n")

    def test_09_reset_both_copy_equal_to_new_origin(self) -> None:
        self.ws.start("a")
        new_content = b"// matching new content\n"
        copy_main = self.tmp / "practice/lessons/tracks/01_t/01_a/main.cpp"
        origin_main = self.tmp / "lessons/tracks/01_t/01_a/main.cpp"
        write(copy_main, new_content)
        write(origin_main, new_content)

        st_before = self.ws.status("a")
        file_states = {f["path"]: f["state"] for f in st_before["files"]}
        self.assertEqual(file_states["practice/lessons/tracks/01_t/01_a/main.cpp"], "both")

        res = self.ws.reset(lesson="a")
        self.assertEqual(res, {"reset": [], "backup": None})

        st_after = self.ws.status("a")
        file_states_after = {f["path"]: f["state"] for f in st_after["files"]}
        self.assertEqual(file_states_after["practice/lessons/tracks/01_t/01_a/main.cpp"], "same")

    def test_10_reset_restores_deleted_copy(self) -> None:
        self.ws.start("a")
        copy_main = self.tmp / "practice/lessons/tracks/01_t/01_a/main.cpp"
        copy_main.unlink()
        self.assertFalse(copy_main.exists())

        res = self.ws.reset(path="practice/lessons/tracks/01_t/01_a/main.cpp")
        self.assertEqual(res["reset"], ["practice/lessons/tracks/01_t/01_a/main.cpp"])
        self.assertTrue(copy_main.is_file())
        self.assertEqual(copy_main.read_bytes(), (self.tmp / "lessons/tracks/01_t/01_a/main.cpp").read_bytes())

        st = self.ws.status("a")
        file_states = {f["path"]: f["state"] for f in st["files"]}
        self.assertEqual(file_states["practice/lessons/tracks/01_t/01_a/main.cpp"], "same")

    def test_11_backups_pruning_and_order(self) -> None:
        self.ws.start("a")
        copy_main = self.tmp / "practice/lessons/tracks/01_t/01_a/main.cpp"

        # 12 backups in one second: <s>, <s>-2 ... <s>-12. The newest 10 are <s>-3 ... <s>-12; a plain
        # name sort would wrongly treat <s>-10 .. <s>-12 as older than <s>-2 and delete them.
        stamp = "20260101-100000"
        for i in range(12):
            write(copy_main, f"// edit {i}\n".encode("utf-8"))
            with patch("practice._stamp", return_value=stamp):
                res = self.ws.reset(path="practice/lessons/tracks/01_t/01_a/main.cpp")
            self.assertEqual(res["backup"], f"{practice.BACKUP_DIR}/{stamp}" + (f"-{i + 1}" if i else ""))

        backup_dir = self.tmp / practice.BACKUP_DIR
        folders = {p.name for p in backup_dir.iterdir() if p.is_dir()}
        self.assertEqual(folders, {f"{stamp}-{n}" for n in range(3, 13)})

    def test_12_damaged_state_json_recovery(self) -> None:
        cases = [
            ("not_json", "broken json {[["),
            ("version_2", json.dumps({"version": 2, "files": {}})),
            ("missing_base_sha", json.dumps({
                "version": 1,
                "files": {
                    "practice/lessons/tracks/01_t/01_a/main.cpp": {
                        "origin": "lessons/tracks/01_t/01_a/main.cpp"
                    }
                }
            })),
        ]

        for label, corrupt_text in cases:
            with self.subTest(case=label):
                # Fresh start and modify one file
                self.ws.start("a")
                copy_main = self.tmp / "practice/lessons/tracks/01_t/01_a/main.cpp"
                write(copy_main, b"// modified content\n")

                state_path = self.tmp / practice.STATE_FILE
                write(state_path, corrupt_text)

                st = self.ws.status("a")
                # Broken file renamed
                broken_files = list(state_path.parent.glob("state.json.broken-*"))
                self.assertTrue(len(broken_files) >= 1)

                # Copies not deleted and correctly reported
                self.assertTrue(copy_main.is_file())
                file_states = {f["path"]: f["state"] for f in st["files"]}
                self.assertEqual(file_states["practice/lessons/tracks/01_t/01_a/main.cpp"], "modified")
                self.assertEqual(file_states["practice/lessons/tracks/01_t/01_a/util.hpp"], "same")

                # Clean up broken files for next subtest
                for bf in broken_files:
                    bf.unlink()

    def test_13_origin_lesson_removed_orphans_and_error(self) -> None:
        self.ws.start("a")
        shutil.rmtree(self.tmp / "lessons/tracks/01_t/01_a")

        all_st = self.ws.status_all()
        self.assertEqual(all_st["lessons"], [])
        orphan_paths = [o["path"] for o in all_st["orphans"]]
        self.assertIn("practice/lessons/tracks/01_t/01_a/main.cpp", orphan_paths)
        for o in all_st["orphans"]:
            self.assertEqual(o["state"], "missing-origin")

        with self.assertRaises(practice.PracticeError):
            self.ws.status("a")

    def test_14_errors(self) -> None:
        with self.assertRaises(practice.PracticeError):
            self.ws.start("nope")

        with self.assertRaises(practice.PracticeError):
            self.ws.reset(unit="nope")

        with self.assertRaises(practice.PracticeError):
            self.ws.reset(path="practice/lessons/x")

        with self.assertRaises(ValueError):
            self.ws.reset()

        with self.assertRaises(ValueError):
            self.ws.reset(lesson="a", unit="u")

        with self.assertRaises(ValueError):
            practice.practice_path("include/x")

        with self.assertRaises(ValueError):
            practice.origin_path("lessons/x")

    def test_15_cli(self) -> None:
        with patch.object(practice.Workspace.__init__, "__defaults__", (self.tmp,)):
            # start a: exit 0 and prints practice folder
            out = io.StringIO()
            err = io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = practice.main(["start", "a"])
            self.assertEqual(code, 0)
            self.assertEqual(out.getvalue().strip(), "practice/lessons/tracks/01_t/01_a")

            # reset with no target: exits 2
            out = io.StringIO()
            err = io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                with self.assertRaises(SystemExit) as cm:
                    practice.main(["reset"])
                self.assertEqual(cm.exception.code, 2)

            # start nope: exits 1 with 'error:' on stderr
            out = io.StringIO()
            err = io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = practice.main(["start", "nope"])
            self.assertEqual(code, 1)
            self.assertIn("error:", err.getvalue())


if __name__ == "__main__":
    unittest.main()
