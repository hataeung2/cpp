#!/usr/bin/env python3
"""Tests for tools/lessons.py (spec 070-01 AC-3, AC-4). Run: py -3 tools/test_lessons.py

Each broken-tree case starts from a valid temporary tree and breaks one thing, so a finding
can only come from that one change.
"""
from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lessons  # noqa: E402

REPO = Path(__file__).resolve().parent.parent


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def make_valid_tree(root: Path) -> None:
    write(root / "include/atugcc/core/logger.hpp", "#pragma once\n")
    write(root / "lessons/units/alpha/unit.toml",
          'id = "alpha"\ntitle = "Alpha"\nfiles = ["alpha.hpp"]\nuses = ["unit:beta"]\n')
    write(root / "lessons/units/alpha/alpha.hpp", '#pragma once\n#include "units/beta/beta.hpp"\n')
    write(root / "lessons/units/alpha/README.md", "# alpha\n")
    write(root / "lessons/units/beta/unit.toml",
          'id = "beta"\ntitle = "Beta"\nfiles = ["beta.hpp"]\nuses = ["lib:atugcc/core/logger.hpp"]\n')
    write(root / "lessons/units/beta/beta.hpp", '#pragma once\n#include "atugcc/core/logger.hpp"\n')
    write(root / "lessons/tracks/01_first/track.toml", 'title = "First"\n')
    write(root / "lessons/tracks/02_second/track.toml", 'title = "Second"\n')
    write(root / "lessons/tracks/01_first/01_one/lesson.toml",
          'id = "one"\ntitle = "One"\nsources = ["main.cpp"]\nuses = ["unit:alpha"]\n')
    write(root / "lessons/tracks/01_first/01_one/main.cpp",
          '#include "units/alpha/alpha.hpp"\n#include "atugcc/core/logger.hpp"\nint main() {}\n')
    write(root / "lessons/tracks/02_second/01_two/lesson.toml",
          'id = "two"\ntitle = "Two"\nsources = ["main.cpp"]\nuses = ["unit:beta"]\n'
          '[run]\nprofile = "long"\ntimeout = 60\n')
    write(root / "lessons/tracks/02_second/01_two/main.cpp", '#include "units/beta/beta.hpp"\nint main() {}\n')


class LessonsTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="atugcc_lessons_"))
        make_valid_tree(self.tmp)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def findings(self) -> list[lessons.Finding]:
        return lessons.run_check(self.tmp).findings

    def assertFinding(self, level: str, path_part: str, message_part: str) -> None:
        found = self.findings()
        matches = [f for f in found if f.level == level and path_part in f.path and message_part in f.message]
        self.assertTrue(matches, f"no {level} with {path_part!r} / {message_part!r} in {[str(f) for f in found]}")

    def replace(self, relative: str, old: str, new: str) -> None:
        path = self.tmp / relative
        text = path.read_text(encoding="utf-8")
        self.assertIn(old, text)
        path.write_text(text.replace(old, new), encoding="utf-8")


class ValidTreeTest(LessonsTestCase):
    def test_valid_tree_has_no_findings(self) -> None:
        self.assertEqual([str(f) for f in self.findings()], [])

    def test_index_resolves_transitive_files_and_used_by(self) -> None:
        catalog, report = lessons.load(self.tmp)
        lessons.check(catalog, report)
        data = lessons.index(catalog)
        self.assertEqual(data["version"], 1)
        self.assertEqual([t["id"] for t in data["tracks"]], ["01_first", "02_second"])
        one = data["tracks"][0]["lessons"][0]
        self.assertEqual(one["target"], "lesson_one")
        self.assertEqual(one["entry"], "lessons/tracks/01_first/01_one/main.cpp")
        self.assertEqual(one["files"], [
            "lessons/units/alpha/alpha.hpp",
            "lessons/units/alpha/README.md",
            "lessons/units/beta/beta.hpp",
            "include/atugcc/core/logger.hpp",
        ])
        self.assertEqual(one["run"], {"profile": "quick", "timeout": 300, "build": None})
        two = data["tracks"][1]["lessons"][0]
        self.assertEqual(two["run"], {"profile": "long", "timeout": 60, "build": None})
        used_by = {u["id"]: u["usedBy"] for u in data["units"]}
        self.assertEqual(used_by, {"alpha": ["one"], "beta": ["one", "two"]})


class BrokenTreeTest(LessonsTestCase):
    """AC-3: one broken fixture per case, each yields its own finding."""

    def test_duplicate_lesson_id(self) -> None:
        self.replace("lessons/tracks/02_second/01_two/lesson.toml", 'id = "two"', 'id = "one"')
        self.assertFinding("ERROR", "01_two/lesson.toml", "duplicate lesson id 'one'")

    def test_missing_uses_target(self) -> None:
        self.replace("lessons/tracks/01_first/01_one/lesson.toml", '"unit:alpha"', '"unit:alpha", "unit:gamma"')
        self.assertFinding("ERROR", "01_one/lesson.toml", "unit:gamma")
        self.replace("lessons/tracks/01_first/01_one/lesson.toml", '"unit:gamma"', '"lib:atugcc/none.hpp"')
        self.assertFinding("ERROR", "01_one/lesson.toml", "include/atugcc/none.hpp does not exist")

    def test_unit_cycle(self) -> None:
        self.replace("lessons/units/beta/unit.toml", 'uses = ["lib:atugcc/core/logger.hpp"]',
                     'uses = ["lib:atugcc/core/logger.hpp", "unit:alpha"]')
        self.assertFinding("ERROR", "unit.toml", "unit cycle:")
        catalog, _ = lessons.load(self.tmp)
        self.assertEqual(lessons.resolve_uses(catalog, ["unit:alpha"]),
                         ["unit:alpha", "unit:beta", "lib:atugcc/core/logger.hpp"])   # no endless loop

    def test_missing_source(self) -> None:
        self.replace("lessons/tracks/01_first/01_one/lesson.toml", '["main.cpp"]', '["main.cpp", "extra.cpp"]')
        self.assertFinding("ERROR", "01_one/lesson.toml", "'extra.cpp' does not exist")

    def test_toml_syntax_error(self) -> None:
        self.replace("lessons/tracks/01_first/01_one/lesson.toml", 'title = "One"', 'title = "One')
        found = [f for f in self.findings() if "TOML syntax error" in f.message]
        self.assertEqual(len(found), 1, [str(f) for f in self.findings()])
        self.assertEqual(found[0].line, 2)

    def test_include_missing_from_uses(self) -> None:
        self.replace("lessons/tracks/02_second/01_two/main.cpp", "int main", '#include "atugcc/pattern/state.hpp"\nint main')
        self.assertFinding("WARN", "01_two/main.cpp", "lib:atugcc/pattern/state.hpp")
        self.assertFalse(any(f.level == "ERROR" for f in self.findings()))

    def test_bad_profile(self) -> None:
        self.replace("lessons/tracks/02_second/01_two/lesson.toml", 'profile = "long"', 'profile = "slow"')
        self.assertFinding("ERROR", "01_two/lesson.toml", "run.profile 'slow'")

    def test_timeout_out_of_range(self) -> None:
        self.replace("lessons/tracks/02_second/01_two/lesson.toml", "timeout = 60", "timeout = 4000")
        self.assertFinding("ERROR", "01_two/lesson.toml", "run.timeout 4000")

    def test_timeout_on_quick_profile_is_a_warning(self) -> None:
        self.replace("lessons/tracks/02_second/01_two/lesson.toml", 'profile = "long"', 'profile = "quick"')
        self.assertFinding("WARN", "01_two/lesson.toml", "ignored for the quick profile")

    def test_bad_build(self) -> None:  # 070-06 AC-2
        self.replace("lessons/tracks/02_second/01_two/lesson.toml", "timeout = 60", 'timeout = 60\nbuild = "fast"')
        self.assertFinding("ERROR", "01_two/lesson.toml", "run.build 'fast'")

    def test_explicit_build_overrides_the_profile_default(self) -> None:  # 070-06 §2.6
        self.replace("lessons/tracks/02_second/01_two/lesson.toml", "timeout = 60", 'timeout = 60\nbuild = "debug"')
        self.replace("lessons/tracks/01_first/01_one/lesson.toml", 'uses = ["unit:alpha"]',
                     'uses = ["unit:alpha"]\n[run]\nbuild = "release"')
        self.assertEqual([str(f) for f in self.findings()], [])
        catalog, _ = lessons.load(self.tmp)
        by_id = {l.id: l for l in catalog.lessons}
        self.assertEqual((by_id["two"].build, by_id["one"].build), ("debug", "release"))
        runs = {l["id"]: l["run"]["build"] for t in lessons.index(catalog)["tracks"] for l in t["lessons"]}
        self.assertEqual(runs, {"one": "release", "two": "debug"})  # as written
        self.assertEqual(lessons.effective_build("long", None), "release")
        self.assertEqual(lessons.effective_build("quick", None), "debug")

    def test_timeout_zero(self) -> None:
        self.replace("lessons/tracks/02_second/01_two/lesson.toml", "timeout = 60", "timeout = 0")
        self.assertFinding("ERROR", "01_two/lesson.toml", "run.timeout 0")

    def test_bad_id(self) -> None:
        self.replace("lessons/tracks/01_first/01_one/lesson.toml", 'id = "one"', 'id = "One-1"')
        self.assertFinding("ERROR", "01_one/lesson.toml", "must match [a-z0-9_]+")

    def test_duplicate_unit_id(self) -> None:
        write(self.tmp / "lessons/units/gamma/unit.toml", 'id = "alpha"\ntitle = "G"\nfiles = ["g.hpp"]\n')
        write(self.tmp / "lessons/units/gamma/g.hpp", "#pragma once\n")
        self.assertFinding("ERROR", "gamma/unit.toml", "duplicate unit id 'alpha'")
        self.assertFinding("ERROR", "gamma/unit.toml", "must equal its folder name 'gamma'")

    def test_lesson_and_unit_may_share_an_id(self) -> None:
        self.replace("lessons/tracks/01_first/01_one/lesson.toml", 'id = "one"', 'id = "alpha"')
        self.assertEqual([str(f) for f in self.findings()], [])

    def test_unit_include_missing_from_uses(self) -> None:
        self.replace("lessons/tracks/02_second/01_two/main.cpp", "int main", '#include "units/alpha/alpha.hpp"\nint main')
        self.assertFinding("WARN", "01_two/main.cpp", "uses has no unit:alpha")

    def test_include_of_missing_unit(self) -> None:
        self.replace("lessons/tracks/02_second/01_two/main.cpp", "int main", '#include "units/nothing/x.hpp"\nint main')
        self.assertFinding("WARN", "01_two/main.cpp", "no such unit")

    def test_absolute_lib_path(self) -> None:
        self.replace("lessons/tracks/01_first/01_one/lesson.toml", '"unit:alpha"', '"unit:alpha", "lib:/etc/hosts"')
        self.assertFinding("ERROR", "01_one/lesson.toml", "lib:/etc/hosts")


class CMakeAgreementTest(LessonsTestCase):
    """check() reads lesson.toml the way lessons/CMakeLists.txt does; any difference is an ERROR."""

    LESSON = "lessons/tracks/02_second/01_two/lesson.toml"

    def test_multiline_sources(self) -> None:
        self.replace("lessons/tracks/01_first/01_one/lesson.toml", 'sources = ["main.cpp"]', 'sources = [\n  "main.cpp",\n]')
        self.assertFinding("ERROR", "01_one/lesson.toml", "CMake reads sources as []")

    def test_single_quoted_sources(self) -> None:
        self.replace("lessons/tracks/01_first/01_one/lesson.toml", 'sources = ["main.cpp"]', "sources = ['main.cpp']")
        self.assertFinding("ERROR", "01_one/lesson.toml", "CMake reads sources as []")

    def test_indented_or_single_quoted_id(self) -> None:
        self.replace("lessons/tracks/01_first/01_one/lesson.toml", 'id = "one"', "id = 'one'")
        self.assertFinding("ERROR", "01_one/lesson.toml", "CMake reads id as None")

    def test_inline_run_table(self) -> None:
        self.replace(self.LESSON, '[run]\nprofile = "long"\ntimeout = 60\n', "")
        self.replace(self.LESSON, 'id = "two"', 'id = "two"\nrun = { profile = "long", timeout = 60 }')
        self.assertFinding("ERROR", "01_two/lesson.toml", "CMake reads profile as 'quick', TOML says 'long'")

    def test_profile_outside_run_table(self) -> None:
        self.replace(self.LESSON, '[run]\nprofile = "long"\ntimeout = 60\n', "")
        self.replace(self.LESSON, 'id = "two"', 'id = "two"\nprofile = "long"')
        self.assertFinding("ERROR", "01_two/lesson.toml", "CMake reads profile as 'long', TOML says 'quick'")


class CommandLineTest(LessonsTestCase):
    def test_check_exit_code(self) -> None:
        self.assertEqual(lessons.main(["check", "--root", str(self.tmp)]), 0)
        self.replace("lessons/tracks/01_first/01_one/lesson.toml", '["main.cpp"]', '["gone.cpp"]')
        self.assertEqual(lessons.main(["check", "--root", str(self.tmp)]), 1)

    def test_index_to_file(self) -> None:
        out = self.tmp / "out/lessons/index.json"
        self.assertEqual(lessons.main(["index", "--root", str(self.tmp)]), 0)
        self.assertIn('"target": "lesson_one"', out.read_text(encoding="utf-8"))


class RepositoryTest(unittest.TestCase):
    """The real lessons/ tree (AC-3 seed passes, AC-4 cross-track reuse)."""

    def test_repository_check_has_no_errors(self) -> None:
        report = lessons.run_check(REPO)
        self.assertEqual([str(f) for f in report.findings if f.level == "ERROR"], [])

    def test_jthread_worker_is_used_by_lessons_in_two_tracks(self) -> None:
        catalog, report = lessons.load(REPO)
        lessons.check(catalog, report)
        data = lessons.index(catalog)
        unit = next(u for u in data["units"] if u["id"] == "jthread_worker")
        self.assertEqual(sorted(unit["usedBy"]), ["device_state_machine", "thread_and_log"])
        tracks_of = {l["id"]: t["id"] for t in data["tracks"] for l in t["lessons"]}
        self.assertEqual({tracks_of[l] for l in unit["usedBy"]}, {"01_essentials", "02_patterns"})


if __name__ == "__main__":
    unittest.main()
