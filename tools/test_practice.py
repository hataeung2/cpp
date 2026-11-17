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
    write(root / "lessons/tracks/t/track.toml",
          'title = "Track 1"\ntitle_en = "Track 1 EN"\nsummary = "S"\nsummary_en = "S"\n')
    write(root / "lessons/tracks/t/a/lesson.toml",
          'id = "a"\ntitle = "A"\ntitle_en = "A"\nsummary = "S"\nsummary_en = "S"\n'
          'sources = ["main.cpp", "util.hpp"]\nuses = ["unit:u"]\n')
    write(root / "lessons/tracks/t/a/main.cpp", b"#include \"util.hpp\"\r\nint main() {}\r\n")
    write(root / "lessons/tracks/t/a/util.hpp", b"#pragma once\n// util\n")
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
            ("lessons/tracks/t/a/lesson.toml", "practice/lessons/tracks/t/a/lesson.toml"),
            ("lessons/tracks/t/a/main.cpp", "practice/lessons/tracks/t/a/main.cpp"),
            ("lessons/tracks/t/a/util.hpp", "practice/lessons/tracks/t/a/util.hpp"),
            ("lessons/units/u/unit.toml", "practice/lessons/units/u/unit.toml"),
            ("lessons/units/u/u.hpp", "practice/lessons/units/u/u.hpp"),
        ]
        for origin, copy in expected_files:
            self.assertTrue((self.tmp / copy).is_file())
            self.assertEqual((self.tmp / copy).read_bytes(), (self.tmp / origin).read_bytes())

        # Verify CRLF is preserved in copy
        main_bytes = (self.tmp / "practice/lessons/tracks/t/a/main.cpp").read_bytes()
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
        copy_main = self.tmp / "practice/lessons/tracks/t/a/main.cpp"
        write(copy_main, b"// modified by user\r\nint main() {}\r\n")

        res = self.ws.start("a")
        self.assertEqual(copy_main.read_bytes(), b"// modified by user\r\nint main() {}\r\n")

        file_states = {f["path"]: f["state"] for f in res["files"]}
        self.assertEqual(file_states["practice/lessons/tracks/t/a/main.cpp"], "modified")
        self.assertEqual(file_states["practice/lessons/tracks/t/a/util.hpp"], "same")

    def test_03_handmade_copy_before_start_kept_and_recorded(self) -> None:
        copy_util = self.tmp / "practice/lessons/tracks/t/a/util.hpp"
        copy_main = self.tmp / "practice/lessons/tracks/t/a/main.cpp"
        write(copy_util, (self.tmp / "lessons/tracks/t/a/util.hpp").read_bytes())
        write(copy_main, b"// handmade modified\n")

        res = self.ws.start("a")
        self.assertEqual(copy_main.read_bytes(), b"// handmade modified\n")

        state = json.loads((self.tmp / practice.STATE_FILE).read_text(encoding="utf-8"))
        self.assertIn("practice/lessons/tracks/t/a/main.cpp", state["files"])
        self.assertIn("practice/lessons/tracks/t/a/util.hpp", state["files"])

        file_states = {f["path"]: f["state"] for f in res["files"]}
        self.assertEqual(file_states["practice/lessons/tracks/t/a/util.hpp"], "same")
        self.assertEqual(file_states["practice/lessons/tracks/t/a/main.cpp"], "modified")

    def test_04_origin_change_follows_unmodified_and_marks_modified_both(self) -> None:
        self.ws.start("a")
        copy_main = self.tmp / "practice/lessons/tracks/t/a/main.cpp"
        copy_util = self.tmp / "practice/lessons/tracks/t/a/util.hpp"
        write(copy_main, b"// user edit\n")

        write(self.tmp / "lessons/tracks/t/a/util.hpp", b"// new util origin\n")
        write(self.tmp / "lessons/tracks/t/a/main.cpp", b"// new main origin\n")

        st = self.ws.status("a")
        file_states = {f["path"]: f["state"] for f in st["files"]}

        self.assertEqual(file_states["practice/lessons/tracks/t/a/util.hpp"], "same")
        self.assertEqual(copy_util.read_bytes(), b"// new util origin\n")

        self.assertEqual(file_states["practice/lessons/tracks/t/a/main.cpp"], "both")
        self.assertEqual(copy_main.read_bytes(), b"// user edit\n")

    def test_05_manifests_always_follow(self) -> None:
        self.ws.start("a")
        copy_toml = self.tmp / "practice/lessons/tracks/t/a/lesson.toml"
        write(copy_toml, copy_toml.read_text(encoding="utf-8") + "# hand edit\n")

        origin_toml = self.tmp / "lessons/tracks/t/a/lesson.toml"
        write(origin_toml, origin_toml.read_text(encoding="utf-8").replace('summary = "S"', 'summary = "New"'))

        self.ws.status("a")
        self.assertEqual(copy_toml.read_bytes(), origin_toml.read_bytes())

    def test_06_origin_manifest_add_and_drop_source(self) -> None:
        self.ws.start("a")
        write(self.tmp / "lessons/tracks/t/a/extra.cpp", b"// extra\n")
        origin_toml = self.tmp / "lessons/tracks/t/a/lesson.toml"
        write(origin_toml, origin_toml.read_text(encoding="utf-8").replace(
            'sources = ["main.cpp", "util.hpp"]', 'sources = ["main.cpp", "extra.cpp"]'))

        st = self.ws.status("a")
        file_paths = {f["path"]: f["state"] for f in st["files"]}

        extra_copy = "practice/lessons/tracks/t/a/extra.cpp"
        self.assertIn(extra_copy, file_paths)
        self.assertEqual(file_paths[extra_copy], "same")
        self.assertEqual((self.tmp / extra_copy).read_bytes(), b"// extra\n")

        util_copy = "practice/lessons/tracks/t/a/util.hpp"
        self.assertNotIn(util_copy, file_paths)
        self.assertFalse((self.tmp / util_copy).exists())

        state = json.loads((self.tmp / practice.STATE_FILE).read_text(encoding="utf-8"))
        self.assertNotIn(util_copy, state["files"])

        # util.hpp was moved into the lesson's backup folder (spec 070-16-01)
        backup_files = list((self.tmp / practice.BACKUP_DIR / "lessons" / "a").glob("util.*.hpp"))
        self.assertEqual(len(backup_files), 1)
        self.assertEqual(backup_files[0].read_bytes(), b"#pragma once\n// util\n")

    def test_07_reset_lesson_scope_and_backup(self) -> None:
        """AC-1: the backups of one lesson reset are in lessons/<id>/ as <name>.<stamp><ext>, one stamp."""
        self.ws.start("a")
        copy_main = self.tmp / "practice/lessons/tracks/t/a/main.cpp"
        copy_util = self.tmp / "practice/lessons/tracks/t/a/util.hpp"
        copy_u = self.tmp / "practice/lessons/units/u/u.hpp"
        write(copy_main, b"// modified main\n")
        write(copy_util, b"// modified util\n")
        write(copy_u, b"// modified unit\n")

        # a stamp per call would show here: one operation takes the stamp once
        with patch("practice._stamp", side_effect=["20261112-103015", "20261112-103016", "20261112-103017"]):
            res = self.ws.reset(lesson="a")
        main_rel = "practice/lessons/tracks/t/a/main.cpp"
        util_rel = "practice/lessons/tracks/t/a/util.hpp"
        self.assertEqual(res["reset"], [main_rel, util_rel])
        self.assertEqual(res["backup"], "practice/backup/lessons/a")

        folder = self.tmp / res["backup"]
        self.assertEqual(sorted(p.name for p in folder.iterdir()),
                         ["main.20261112-103015.cpp", "util.20261112-103015.hpp"])
        self.assertEqual((folder / "main.20261112-103015.cpp").read_bytes(), b"// modified main\n")
        self.assertEqual((folder / "util.20261112-103015.hpp").read_bytes(), b"// modified util\n")

        self.assertEqual(copy_main.read_bytes(), (self.tmp / "lessons/tracks/t/a/main.cpp").read_bytes())
        st = self.ws.status("a")
        file_states = {f["path"]: f["state"] for f in st["files"]}
        self.assertEqual(file_states[main_rel], "same")

        # AC-2: the unit copy was not reset and the lesson reset made no unit backup folder
        self.assertEqual(copy_u.read_bytes(), b"// modified unit\n")
        self.assertFalse((self.tmp / practice.BACKUP_DIR / "units").exists())

    def test_08_reset_unit_and_file_scope(self) -> None:
        self.ws.start("a")
        copy_main = self.tmp / "practice/lessons/tracks/t/a/main.cpp"
        copy_util = self.tmp / "practice/lessons/tracks/t/a/util.hpp"
        copy_u = self.tmp / "practice/lessons/units/u/u.hpp"
        write(copy_main, b"// edit main\n")
        write(copy_util, b"// edit util\n")
        write(copy_u, b"// edit unit\n")

        res_unit = self.ws.reset(unit="u")
        self.assertEqual(res_unit["reset"], ["practice/lessons/units/u/u.hpp"])
        self.assertEqual(copy_u.read_bytes(), (self.tmp / "lessons/units/u/u.hpp").read_bytes())
        self.assertEqual(copy_main.read_bytes(), b"// edit main\n")
        self.assertEqual(copy_util.read_bytes(), b"// edit util\n")

        res_file = self.ws.reset(path="practice/lessons/tracks/t/a/main.cpp")
        self.assertEqual(res_file["reset"], ["practice/lessons/tracks/t/a/main.cpp"])
        self.assertEqual(copy_main.read_bytes(), (self.tmp / "lessons/tracks/t/a/main.cpp").read_bytes())
        self.assertEqual(copy_util.read_bytes(), b"// edit util\n")

    def test_09_reset_both_copy_equal_to_new_origin(self) -> None:
        self.ws.start("a")
        new_content = b"// matching new content\n"
        copy_main = self.tmp / "practice/lessons/tracks/t/a/main.cpp"
        origin_main = self.tmp / "lessons/tracks/t/a/main.cpp"
        write(copy_main, new_content)
        write(origin_main, new_content)

        st_before = self.ws.status("a")
        file_states = {f["path"]: f["state"] for f in st_before["files"]}
        self.assertEqual(file_states["practice/lessons/tracks/t/a/main.cpp"], "both")

        res = self.ws.reset(lesson="a")
        self.assertEqual(res, {"reset": [], "backup": None})

        st_after = self.ws.status("a")
        file_states_after = {f["path"]: f["state"] for f in st_after["files"]}
        self.assertEqual(file_states_after["practice/lessons/tracks/t/a/main.cpp"], "same")

    def test_10_reset_restores_deleted_copy(self) -> None:
        self.ws.start("a")
        copy_main = self.tmp / "practice/lessons/tracks/t/a/main.cpp"
        copy_main.unlink()
        self.assertFalse(copy_main.exists())

        res = self.ws.reset(path="practice/lessons/tracks/t/a/main.cpp")
        self.assertEqual(res["reset"], ["practice/lessons/tracks/t/a/main.cpp"])
        self.assertTrue(copy_main.is_file())
        self.assertEqual(copy_main.read_bytes(), (self.tmp / "lessons/tracks/t/a/main.cpp").read_bytes())

        st = self.ws.status("a")
        file_states = {f["path"]: f["state"] for f in st["files"]}
        self.assertEqual(file_states["practice/lessons/tracks/t/a/main.cpp"], "same")

    def test_11_backups_pruned_per_file(self) -> None:
        """AC-3: the newest 10 backups of each file stay; another file's backup is not pushed out."""
        self.ws.start("a")
        copy_main = self.tmp / "practice/lessons/tracks/t/a/main.cpp"
        copy_util = self.tmp / "practice/lessons/tracks/t/a/util.hpp"
        write(copy_util, b"// edited util\n")
        with patch("practice._stamp", return_value="20260101-090000"):
            self.ws.reset(path="practice/lessons/tracks/t/a/util.hpp")

        # 12 backups of main.cpp in one second: <s>, <s>-2 ... <s>-12. The newest 10 are <s>-3 ... <s>-12; a plain
        # name sort would wrongly treat <s>-10 .. <s>-12 as older than <s>-2 and delete them.
        stamp = "20260101-100000"
        for i in range(12):
            write(copy_main, f"// edit {i}\n".encode("utf-8"))
            with patch("practice._stamp", return_value=stamp):
                res = self.ws.reset(path="practice/lessons/tracks/t/a/main.cpp")
            self.assertEqual(res["backup"], "practice/backup/lessons/a")

        names = sorted(p.name for p in (self.tmp / "practice/backup/lessons/a").iterdir())
        expected_main = [f"main.{stamp}-{n}.cpp" for n in range(3, 13)]
        self.assertEqual([n for n in names if n.startswith("main.")], sorted(expected_main))
        self.assertEqual([n for n in names if n.startswith("util.")], ["util.20260101-090000.hpp"])
        newest = self.tmp / "practice/backup/lessons/a" / f"main.{stamp}-12.cpp"
        self.assertEqual(newest.read_bytes(), b"// edit 11\n")

    def test_16_unit_reset_goes_to_unit_folder(self) -> None:
        """AC-2: a unit reset backs up into units/<id>/."""
        self.ws.start("a")
        write(self.tmp / "practice/lessons/units/u/u.hpp", b"// modified unit\n")
        with patch("practice._stamp", return_value="20261112-110500"):
            res = self.ws.reset(unit="u")
        self.assertEqual(res["backup"], "practice/backup/units/u")
        backup = self.tmp / res["backup"] / "u.20261112-110500.hpp"
        self.assertEqual(backup.read_bytes(), b"// modified unit\n")
        self.assertFalse((self.tmp / practice.BACKUP_DIR / "lessons").exists())

    def test_17_same_id_for_lesson_and_unit_stays_apart(self) -> None:
        """AC-2: through the catalog, a lesson and a unit with the same id back up into separate folders
        (the lesson folder is `xl` and the unit folder `xx`: the backup folder is named by id, not by the folder
        name; `lessons.py check` rejects a lesson folder that is not its id (070-26), practice.py does not rely on it)."""
        write(self.tmp / "lessons/tracks/t/xl/lesson.toml",
              'id = "x"\ntitle = "X"\ntitle_en = "X"\nsummary = "S"\nsummary_en = "S"\n'
              'sources = ["a.cpp"]\nuses = ["unit:x"]\n')
        write(self.tmp / "lessons/tracks/t/xl/a.cpp", b"// lesson\n")
        write(self.tmp / "lessons/units/xx/unit.toml",
              'id = "x"\ntitle = "X"\ntitle_en = "X"\nsummary = "S"\nsummary_en = "S"\nfiles = ["a.hpp"]\n')
        write(self.tmp / "lessons/units/xx/a.hpp", b"// unit\n")
        self.ws.start("x")
        write(self.tmp / "practice/lessons/tracks/t/xl/a.cpp", b"// edited lesson\n")
        write(self.tmp / "practice/lessons/units/xx/a.hpp", b"// edited unit\n")
        with patch("practice._stamp", return_value="20261112-120000"):
            self.assertEqual(self.ws.reset(lesson="x")["backup"], "practice/backup/lessons/x")
        with patch("practice._stamp", return_value="20261112-120001"):
            self.assertEqual(self.ws.reset(unit="x")["backup"], "practice/backup/units/x")
        base = self.tmp / practice.BACKUP_DIR
        self.assertEqual(sorted(p.name for p in (base / "lessons/x").iterdir()), ["a.20261112-120000.cpp"])
        self.assertEqual(sorted(p.name for p in (base / "units/x").iterdir()), ["a.20261112-120001.hpp"])
        self.assertEqual((base / "lessons/x/a.20261112-120000.cpp").read_bytes(), b"// edited lesson\n")
        self.assertEqual((base / "units/x/a.20261112-120001.hpp").read_bytes(), b"// edited unit\n")

    def test_18_names_with_dots_no_extension_and_subfolders(self) -> None:
        """AC-4: files are grouped by folder + name + extension; each group keeps its newest KEEP_BACKUPS."""
        folder = "practice/lessons/tracks/t/x"
        owners = {folder: ("lessons", "x")}
        names = ["foo.bar.cpp", "foo.cpp", "foo.hpp", "Makefile", "sub/foo.cpp", "v.20250101-000000.cpp"]
        for name in names:
            write(self.tmp / folder / name, b"x")
        rounds = practice.KEEP_BACKUPS + 2
        for i in range(rounds):
            with patch("practice._stamp", return_value=f"20261112-1200{i:02d}"):
                backup = practice._Backup(self.tmp, owners)
                for name in names:
                    backup.keep(f"{folder}/{name}")
        base = self.tmp / practice.BACKUP_DIR / "lessons/x"
        newest = [f"20261112-1200{i:02d}" for i in range(rounds - practice.KEEP_BACKUPS, rounds)]
        for name in names:
            directory, _, short = name.rpartition("/")
            parsed = [r for r in map(practice.parse_backup_name, (q.name for q in (base / directory).iterdir())) if r]
            self.assertEqual(sorted(stamp for original, stamp, _ in parsed if original == short), newest, name)
        self.assertEqual(practice.parse_backup_name("foo.bar.20261112-120000.cpp"), ("foo.bar.cpp", "20261112-120000", 1))
        self.assertEqual(practice.parse_backup_name("Makefile.20261112-120000-3"), ("Makefile", "20261112-120000", 3))
        self.assertEqual(practice.parse_backup_name("v.20250101-000000.20261112-120000.cpp"),
                         ("v.20250101-000000.cpp", "20261112-120000", 1))
        self.assertIsNone(practice.parse_backup_name("main.cpp"))

    def test_20_owner_not_in_the_catalog(self) -> None:
        """Assumption 6: a copy whose lesson or unit is gone is backed up under its folder name."""
        write(self.tmp / "practice/lessons/tracks/t/gone/a.cpp", b"// a\n")
        write(self.tmp / "practice/lessons/units/gone/b.hpp", b"// b\n")
        write(self.tmp / "practice/lessons/odd.txt", b"odd\n")
        backup = practice._Backup(self.tmp, {})
        backup.keep("practice/lessons/tracks/t/gone/a.cpp")
        backup.keep("practice/lessons/units/gone/b.hpp")
        base = self.tmp / practice.BACKUP_DIR
        self.assertEqual([p.name for p in (base / "lessons/gone").iterdir()], [practice.backup_name("a.cpp", backup.stamp)])
        self.assertEqual([p.name for p in (base / "units/gone").iterdir()], [practice.backup_name("b.hpp", backup.stamp)])
        with self.assertRaises(practice.PracticeError):
            backup.keep("practice/lessons/odd.txt")

    def test_21_backup_just_made_survives_a_clock_set_back(self) -> None:
        """Pruning orders by stamp; a backup with an older stamp than 10 existing ones is still kept."""
        folder = "practice/lessons/tracks/t/x"
        write(self.tmp / folder / "main.cpp", b"// now\n")
        owner_dir = self.tmp / practice.BACKUP_DIR / "lessons/x"
        for i in range(practice.KEEP_BACKUPS):
            write(owner_dir / practice.backup_name("main.cpp", f"20271212-0000{i:02d}"), b"later")
        with patch("practice._stamp", return_value="20260101-000000"):
            practice._Backup(self.tmp, {folder: ("lessons", "x")}).keep(f"{folder}/main.cpp")
        names = sorted(p.name for p in owner_dir.iterdir())
        self.assertEqual(len(names), practice.KEEP_BACKUPS)
        self.assertIn("main.20260101-000000.cpp", names)
        self.assertNotIn("main.20271212-000000.cpp", names)  # the oldest of the later ones went

    def test_22_finish_reports_the_first_owner_and_move_takes_the_file(self) -> None:
        lesson_folder, unit_folder = "practice/lessons/tracks/t/x", "practice/lessons/units/y"
        write(self.tmp / lesson_folder / "a.cpp", b"// a\n")
        write(self.tmp / unit_folder / "b.hpp", b"// b\n")
        backup = practice._Backup(self.tmp, {lesson_folder: ("lessons", "x"), unit_folder: ("units", "y")})
        self.assertIsNone(backup.finish())
        backup.keep(f"{unit_folder}/b.hpp", move=True)
        backup.keep(f"{lesson_folder}/a.cpp")
        self.assertEqual(backup.finish(), "practice/backup/units/y")
        self.assertFalse((self.tmp / unit_folder / "b.hpp").exists())
        self.assertTrue((self.tmp / lesson_folder / "a.cpp").exists())

    def test_23_subfolder_source_through_reset(self) -> None:
        """AC-4: a lesson source in a subfolder is backed up under the same relative path."""
        lesson_toml = self.tmp / "lessons/tracks/t/a/lesson.toml"
        write(lesson_toml, lesson_toml.read_text(encoding="utf-8").replace(
            'sources = ["main.cpp", "util.hpp"]', 'sources = ["main.cpp", "sub/h.cpp"]'))
        write(self.tmp / "lessons/tracks/t/a/sub/h.cpp", b"// h\n")
        self.ws.start("a")
        write(self.tmp / "practice/lessons/tracks/t/a/sub/h.cpp", b"// edited h\n")
        with patch("practice._stamp", return_value="20261112-130000"):
            res = self.ws.reset(lesson="a")
        backup = self.tmp / res["backup"] / "sub/h.20261112-130000.cpp"
        self.assertEqual(backup.read_bytes(), b"// edited h\n")

    def test_19_old_format_folders_are_left_alone(self) -> None:
        """AC-5: a practice/backup/<stamp>/ folder of the 070-16 layout is neither read nor pruned."""
        olds = [self.tmp / practice.BACKUP_DIR / f"202601{i:02d}-000000/practice/lessons/tracks/t/a/main.cpp"
                for i in range(1, practice.KEEP_BACKUPS + 2)]  # more than the old layout kept
        for old in olds:
            write(old, b"// old backup\n")
        self.ws.start("a")
        copy_main = self.tmp / "practice/lessons/tracks/t/a/main.cpp"
        for i in range(practice.KEEP_BACKUPS + 2):
            write(copy_main, f"// edit {i}\n".encode("utf-8"))
            with patch("practice._stamp", return_value=f"20261112-1000{i:02d}"):
                self.ws.reset(path="practice/lessons/tracks/t/a/main.cpp")
        for old in olds:
            self.assertEqual(old.read_bytes(), b"// old backup\n")

    def test_12_damaged_state_json_recovery(self) -> None:
        cases = [
            ("not_json", "broken json {[["),
            ("version_2", json.dumps({"version": 2, "files": {}})),
            ("missing_base_sha", json.dumps({
                "version": 1,
                "files": {
                    "practice/lessons/tracks/t/a/main.cpp": {
                        "origin": "lessons/tracks/t/a/main.cpp"
                    }
                }
            })),
        ]

        for label, corrupt_text in cases:
            with self.subTest(case=label):
                # Fresh start and modify one file
                self.ws.start("a")
                copy_main = self.tmp / "practice/lessons/tracks/t/a/main.cpp"
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
                self.assertEqual(file_states["practice/lessons/tracks/t/a/main.cpp"], "modified")
                self.assertEqual(file_states["practice/lessons/tracks/t/a/util.hpp"], "same")

                # Clean up broken files for next subtest
                for bf in broken_files:
                    bf.unlink()

    def test_13_origin_lesson_removed_orphans_and_error(self) -> None:
        self.ws.start("a")
        shutil.rmtree(self.tmp / "lessons/tracks/t/a")

        all_st = self.ws.status_all()
        self.assertEqual(all_st["lessons"], [])
        orphan_paths = [o["path"] for o in all_st["orphans"]]
        self.assertIn("practice/lessons/tracks/t/a/main.cpp", orphan_paths)
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
            self.assertEqual(out.getvalue().strip(), "practice/lessons/tracks/t/a")

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
