#!/usr/bin/env python3
"""Tests for tools/lessons.py (spec 070-01 AC-3, AC-4). Run: py -3 tools/test_lessons.py

Each broken-tree case starts from a valid temporary tree and breaks one thing, so a finding
can only come from that one change.
"""
from __future__ import annotations

import shutil
import sys
import tempfile
import unicodedata
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
    write(root / "lessons/tags.toml",
          '[alpha_tag]\nko = "알파"\nen = "Alpha"\naliases = ["a_alias"]\n\n'
          '[beta_tag]\nko = "베타"\nen = "Beta"\naliases = ["b_alias"]\n')
    write(root / "lessons/units/alpha/unit.toml",
          'id = "alpha"\ntitle = "Alpha"\ntitle_en = "Alpha EN"\nfiles = ["alpha.hpp"]\nuses = ["unit:beta"]\n')
    write(root / "lessons/units/alpha/alpha.hpp", '#pragma once\n#include "units/beta/beta.hpp"\n')
    write(root / "lessons/units/alpha/README.md", "# alpha\n")
    write(root / "lessons/units/alpha/README.en.md", "# alpha (en)\n")
    write(root / "lessons/units/beta/unit.toml",
          'id = "beta"\ntitle = "Beta"\ntitle_en = "Beta EN"\nfiles = ["beta.hpp"]\nuses = ["lib:atugcc/core/logger.hpp"]\n')
    write(root / "lessons/units/beta/beta.hpp", '#pragma once\n#include "atugcc/core/logger.hpp"\n')
    write(root / "lessons/tracks/01_first/track.toml", 'title = "First"\ntitle_en = "First EN"\n')
    write(root / "lessons/tracks/02_second/track.toml", 'title = "Second"\ntitle_en = "Second EN"\n')
    write(root / "lessons/tracks/01_first/01_one/lesson.toml",
          'id = "one"\ntitle = "One"\ntitle_en = "One EN"\nsources = ["main.cpp"]\nuses = ["unit:alpha"]\ntags = ["alpha_tag"]\n')
    write(root / "lessons/tracks/01_first/01_one/main.cpp",
          '#include "units/alpha/alpha.hpp"\n#include "atugcc/core/logger.hpp"\nint main() {}\n')
    write(root / "lessons/tracks/02_second/01_two/lesson.toml",
          'id = "two"\ntitle = "Two"\ntitle_en = "Two EN"\nsources = ["main.cpp"]\nuses = ["unit:beta"]\n'
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

    def test_index_english_fields_and_readme_en(self) -> None:  # 070-10 AC-3
        def build() -> dict:
            catalog, _ = lessons.load(self.tmp)
            return lessons.index(catalog)

        (self.tmp / "lessons/units/alpha/README.en.md").unlink()  # the valid tree has one since 070-03
        data = build()
        first = data["tracks"][0]
        one = first["lessons"][0]
        alpha = next(u for u in data["units"] if u["id"] == "alpha")
        self.assertEqual((first["titleEn"], one["titleEn"], alpha["titleEn"]), ("First EN", "One EN", "Alpha EN"))
        self.assertEqual((first["title"], one["title"], alpha["title"]), ("First", "One", "Alpha"))
        self.assertEqual((first["summaryEn"], one["summaryEn"], alpha["summaryEn"]), (None, None, None))
        self.assertEqual((one["readmeEn"], alpha["readmeEn"]), (None, None))

        self.replace("lessons/tracks/01_first/01_one/lesson.toml", 'title_en = "One EN"\n',
                     'title_en = ""\nsummary = "Eins"\nsummary_en = "One summary"\n')
        write(self.tmp / "lessons/tracks/01_first/01_one/README.en.md", "# one\n")
        write(self.tmp / "lessons/units/alpha/README.en.md", "# alpha\n")
        data = build()
        one = data["tracks"][0]["lessons"][0]
        alpha = next(u for u in data["units"] if u["id"] == "alpha")
        self.assertIsNone(one["titleEn"])  # "" is null in the index
        self.assertEqual(one["summaryEn"], "One summary")
        self.assertEqual(one["readmeEn"], "lessons/tracks/01_first/01_one/README.en.md")
        self.assertIsNone(one["readme"])
        self.assertEqual(alpha["readmeEn"], "lessons/units/alpha/README.en.md")
        self.assertEqual(alpha["readme"], "lessons/units/alpha/README.md")

    def test_index_tags_vocabulary(self) -> None:  # 070-10 AC-3
        catalog, report = lessons.load(self.tmp)
        lessons.check(catalog, report)
        data = lessons.index(catalog)
        self.assertEqual(data["tags"], {
            "alpha_tag": {"ko": "알파", "en": "Alpha", "aliases": ["a_alias"]},
            "beta_tag": {"ko": "베타", "en": "Beta", "aliases": ["b_alias"]},
        })
        self.assertEqual(list(data["tags"].keys()), ["alpha_tag", "beta_tag"])

        (self.tmp / "lessons/tags.toml").unlink()
        catalog_no_tags, _ = lessons.load(self.tmp)
        data_no_tags = lessons.index(catalog_no_tags)
        self.assertEqual(data_no_tags["tags"], {})

    def test_index_keys(self) -> None:  # 070-10 AC-3: new keys added, existing ones kept
        catalog, _ = lessons.load(self.tmp)
        data = lessons.index(catalog)
        self.assertEqual(list(data), ["version", "tracks", "units", "tags"])
        self.assertEqual(data["version"], 1)
        self.assertEqual(list(data["tracks"][0]),
                         ["id", "title", "titleEn", "summary", "summaryEn", "path", "lessons"])
        self.assertEqual(list(data["tracks"][0]["lessons"][0]),
                         ["id", "title", "titleEn", "summary", "summaryEn", "path", "target", "entry", "sources",
                          "readme", "readmeEn", "uses", "files", "tags", "run"])
        self.assertEqual(list(data["units"][0]),
                         ["id", "title", "titleEn", "summary", "summaryEn", "path", "files", "readme", "readmeEn",
                          "uses", "usedBy"])


class EnglishFieldsTest(LessonsTestCase):
    """070-10 AC-1: English title/summary warning and validation."""

    def test_lesson_without_title_en_warns(self) -> None:  # 070-10 AC-1
        self.replace("lessons/tracks/01_first/01_one/lesson.toml", 'title_en = "One EN"\n', "")
        self.assertFinding("WARN", "01_one/lesson.toml", "title_en")

    def test_unit_with_summary_and_no_summary_en_warns(self) -> None:  # 070-10 AC-1
        self.replace("lessons/units/alpha/unit.toml",
                     'title_en = "Alpha EN"\n',
                     'title_en = "Alpha EN"\nsummary = "Alpha unit summary"\n')
        self.assertFinding("WARN", "alpha/unit.toml", "summary_en")

    def test_track_title_en_not_string_is_error(self) -> None:  # 070-10 AC-1
        self.replace("lessons/tracks/01_first/track.toml",
                     'title_en = "First EN"',
                     "title_en = 3")
        self.assertFinding("ERROR", "01_first/track.toml", "'title_en' must be a string")

    def test_track_without_title_en_warns(self) -> None:  # 070-10 AC-1
        self.replace("lessons/tracks/02_second/track.toml", 'title_en = "Second EN"\n', "")
        self.assertFinding("WARN", "02_second/track.toml", "missing 'title_en'")

    def test_empty_title_en_warns(self) -> None:  # 070-10 AC-1
        self.replace("lessons/units/beta/unit.toml", 'title_en = "Beta EN"', 'title_en = ""')
        self.assertFinding("WARN", "beta/unit.toml", "missing 'title_en'")

    def test_non_string_title_en_gets_no_missing_warning(self) -> None:  # 070-10 AC-1
        self.replace("lessons/tracks/01_first/track.toml", 'title_en = "First EN"', "title_en = 3")
        self.assertFalse(any("missing 'title_en'" in f.message for f in self.findings()))

    def test_multiline_english_field_that_fools_cmake_is_an_error(self) -> None:  # 070-10 AC-1
        # A line inside a multi-line string that looks like `id = ...` is what CMake's regex would read.
        path = self.tmp / "lessons/tracks/01_first/01_one/lesson.toml"
        path.write_text('summary_en = """\nid = "x"\n"""\n' + path.read_text(encoding="utf-8"), encoding="utf-8")
        self.assertFinding("ERROR", "01_one/lesson.toml", "CMake reads id as 'x'")


class TagVocabularyTest(LessonsTestCase):
    """070-10 AC-2: tag vocabulary lessons/tags.toml checks."""

    def test_missing_tags_file_warns_and_skips_tag_checks(self) -> None:  # 070-10 AC-2
        (self.tmp / "lessons/tags.toml").unlink()
        warns = [f for f in self.findings() if f.level == "WARN"]
        self.assertEqual(len(warns), 1)
        self.assertIn("tags.toml", warns[0].path)
        self.assertIn("skipped", warns[0].message)
        self.assertFalse(any("is not in lessons/tags.toml" in f.message for f in self.findings()))

    def test_tags_toml_syntax_error(self) -> None:  # 070-10 AC-2
        self.replace("lessons/tags.toml", "[alpha_tag]", "[alpha_tag")
        self.assertFinding("ERROR", "tags.toml", "TOML syntax error")

    def test_invalid_tag_key(self) -> None:  # 070-10 AC-2
        self.replace("lessons/tags.toml", "[beta_tag]", '["Bad-Key"]')
        self.assertFinding("ERROR", "tags.toml", "must match [a-z0-9_]+")

    def test_tag_missing_en(self) -> None:  # 070-10 AC-2
        self.replace("lessons/tags.toml", 'en = "Alpha"\n', "")
        self.assertFinding("ERROR", "tags.toml", "'en' must be a string")
        self.assertFalse(any("is not in lessons/tags.toml" in f.message for f in self.findings()))

    def test_tag_missing_ko(self) -> None:  # 070-10 AC-2
        self.replace("lessons/tags.toml", 'ko = "베타"\n', "")
        self.assertFinding("ERROR", "tags.toml", "tag 'beta_tag': 'ko' must be a string")

    def test_alias_equal_to_another_tags_key_ignoring_case(self) -> None:  # 070-10 AC-2, §4
        self.replace("lessons/tags.toml", 'aliases = ["b_alias"]', 'aliases = ["ALPHA_TAG"]')
        self.assertFinding("WARN", "tags.toml", "tag 'beta_tag': name 'alpha_tag' is also used by tag 'alpha_tag'")

    def test_aliases_not_a_list_of_strings(self) -> None:  # 070-10 AC-2
        self.replace("lessons/tags.toml", 'aliases = ["a_alias"]', 'aliases = "x"')
        self.assertFinding("ERROR", "tags.toml", "'aliases' must be a list of strings")

    def test_non_table_top_level_value(self) -> None:  # 070-10 AC-2
        tags_file = self.tmp / "lessons/tags.toml"
        tags_file.write_text("stray = 1\n" + tags_file.read_text(encoding="utf-8"), encoding="utf-8")
        self.assertFinding("ERROR", "tags.toml", "must be a table")

    def test_lesson_tag_missing_from_vocabulary(self) -> None:  # 070-10 AC-2
        self.replace("lessons/tracks/01_first/01_one/lesson.toml",
                     'tags = ["alpha_tag"]',
                     'tags = ["unknown_tag"]')
        found = [f for f in self.findings() if "is not in lessons/tags.toml" in f.message]
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].level, "WARN")
        self.assertIn("01_one/lesson.toml", found[0].path)
        manifest_text = (self.tmp / "lessons/tracks/01_first/01_one/lesson.toml").read_text(encoding="utf-8")
        tags_line = lessons.line_of(manifest_text, "tags")
        self.assertIsNotNone(tags_line)
        self.assertEqual(found[0].line, tags_line)

    def test_duplicate_alias_across_tags_warns(self) -> None:  # 070-10 AC-2
        nfd_thread = unicodedata.normalize("NFD", "스레드")
        self.replace("lessons/tags.toml", 'aliases = ["a_alias"]', 'aliases = ["스레드"]')
        self.replace("lessons/tags.toml", 'aliases = ["b_alias"]', f'aliases = ["{nfd_thread}"]')
        self.assertFinding("WARN", "tags.toml", "is also used by tag")

    def test_alias_equal_to_own_tag_key_does_not_warn(self) -> None:  # 070-10 AC-2
        self.replace("lessons/tags.toml", 'aliases = ["a_alias"]', 'aliases = ["alpha_tag"]')
        self.assertFalse(any("is also used by" in f.message for f in self.findings()))


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


class HangulLiteralTest(unittest.TestCase):
    def test_comments_ignored(self) -> None:  # 070-03 AC-6
        text = (
            "// 한글 주석\n"
            "/* 한글 블록\n"
            ' * "따옴표 포함"\n'
            " */\n"
            "int x = 0;\n"
        )
        self.assertEqual(lessons.hangul_literals(text), [])

    def test_plain_string_line_3(self) -> None:  # 070-03 AC-6
        text = (
            "int a = 1;\n"
            "int b = 2;\n"
            'const char* s = "안녕";\n'
        )
        self.assertEqual(lessons.hangul_literals(text), [3])

    def test_ascii_and_hangul_on_different_lines(self) -> None:  # 070-03 AC-6
        text = (
            'const char* a = "hello";\n'
            'const char* b = "세계";\n'
        )
        self.assertEqual(lessons.hangul_literals(text), [2])

    def test_char_literal_quote_then_hangul_comment(self) -> None:  # 070-03 AC-6
        text = 'char c = \'"\'; // 가\n'   # one quote: a scanner that opens a string here reports line 1
        self.assertEqual(lessons.hangul_literals(text), [])
        self.assertEqual(lessons.hangul_literals("char c = '가';\nchar d = u8'나';\n"), [1, 2])

    def test_escaped_quote(self) -> None:  # 070-03 AC-6
        self.assertEqual(lessons.hangul_literals('const char* s = "say \\"안녕\\"";\n'), [1])
        self.assertEqual(lessons.hangul_literals('const char* s = "a\\"b"; // 가\n'), [])

    def test_raw_strings(self) -> None:  # 070-03 AC-6
        self.assertEqual(lessons.hangul_literals('auto s = R"(he said "가")";\n'), [1])
        self.assertEqual(lessons.hangul_literals('auto s = R"x(a )" 가 )x";\n'), [1])
        text_ascii_raw = (
            'auto s = R"(hello "world")";\n'
            '// 한글 주석\n'
        )
        self.assertEqual(lessons.hangul_literals(text_ascii_raw), [])

    def test_raw_string_multiline_hangul(self) -> None:  # 070-03 AC-6
        text = (
            "int x = 0;\n"
            'auto s = R"(\n'
            "ascii line\n"
            '한글 line)";\n'
        )
        self.assertEqual(lessons.hangul_literals(text), [2])

    def test_encoding_prefixes(self) -> None:  # 070-03 AC-6
        self.assertEqual(lessons.hangul_literals('auto s = u8"가";\n'), [1])
        self.assertEqual(lessons.hangul_literals('auto s = L"가";\n'), [1])
        self.assertEqual(lessons.hangul_literals('auto s = u8R"(가)";\n'), [1])
        # the '"' inside the raw string would end an ordinary string early and leave '"; // 가' as a string
        self.assertEqual(lessons.hangul_literals('auto s = u8R"(")"; // 가\n'), [])
        self.assertEqual(lessons.hangul_literals('auto s = R"(")"; // 가\n'), [])

    def test_digit_separator(self) -> None:  # 070-03 AC-6
        self.assertEqual(lessons.hangul_literals("int n = 1'000'000; // 가\n"), [])
        # an odd number of separators: a char literal opened at "'" would run into the comment
        self.assertEqual(lessons.hangul_literals("int n = 1'000; // 가\n"), [])
        self.assertEqual(lessons.hangul_literals("auto h = 0xFF'FF; // 가\n"), [])
        self.assertEqual(lessons.hangul_literals('int n = 1\'000; auto s = "가";\n'), [1])

    def test_identifier_ending_in_r(self) -> None:  # 070-03 AC-6
        self.assertEqual(lessons.hangul_literals('auto s = FOOR"가";\n'), [1])
        # FOOR"(" is an ordinary string ending at its second quote; read as raw, it would run to the ')"' in the comment
        self.assertEqual(lessons.hangul_literals('auto s = FOOR"("; // 가 )"\n'), [])

    def test_unterminated_string_with_hangul(self) -> None:  # 070-03 AC-6
        text = (
            "int x = 1;\n"
            'const char* s = "hello 가'
        )
        self.assertEqual(lessons.hangul_literals(text), [2])

    def test_hangul_jamo(self) -> None:  # 070-03 AC-6
        self.assertEqual(lessons.hangul_literals('const char* s = "ㄱ";\n'), [1])
        self.assertEqual(lessons.hangul_literals('const char* s = "ᄀ";\n'), [1])

    def test_duplicate_literals_on_same_line(self) -> None:  # 070-03 AC-6
        self.assertEqual(lessons.hangul_literals('const char* a = "가", *b = "나";\n'), [1])


class ReadmeEnTest(LessonsTestCase):
    def test_lesson_missing_readme_en(self) -> None:  # 070-03 AC-6
        write(self.tmp / "lessons/tracks/01_first/01_one/README.md", "# One\n")
        self.assertFinding("WARN", "01_one/lesson.toml", "no README.en.md")

    def test_unit_missing_readme_en(self) -> None:  # 070-03 AC-6
        write(self.tmp / "lessons/units/beta/README.md", "# Beta\n")
        self.assertFinding("WARN", "units/beta/unit.toml", "no README.en.md")

    def test_folder_neither_readme_no_warning(self) -> None:  # 070-03 AC-6
        readme_warns = [f for f in self.findings() if "README.en.md" in f.message]
        self.assertEqual(readme_warns, [])

    def test_folder_both_readmes_no_warning(self) -> None:  # 070-03 AC-6
        write(self.tmp / "lessons/tracks/01_first/01_one/README.md", "# One\n")
        write(self.tmp / "lessons/tracks/01_first/01_one/README.en.md", "# One EN\n")
        readme_warns = [f for f in self.findings() if "README.en.md" in f.message]
        self.assertEqual(readme_warns, [])


class HangulLiteralCheckTest(LessonsTestCase):
    def test_lesson_source_hangul_literal(self) -> None:  # 070-03 AC-6
        self.replace("lessons/tracks/01_first/01_one/main.cpp", "int main() {}", 'int main() { std::cout << "안녕"; }')
        self.assertFinding("WARN", "01_one/main.cpp", "Hangul")
        match = next(f for f in self.findings() if f.level == "WARN" and "01_one/main.cpp" in f.path and "Hangul" in f.message)
        self.assertEqual(match.line, 3)

    def test_unit_header_hangul_literal(self) -> None:  # 070-03 AC-6
        self.replace("lessons/units/alpha/alpha.hpp",
                     '#include "units/beta/beta.hpp"\n',
                     '#include "units/beta/beta.hpp"\ninline const char* msg = "안녕";\n')
        warns = [f for f in self.findings() if "Hangul" in f.message]
        self.assertEqual([(f.level, f.path, f.line) for f in warns], [("WARN", "lessons/units/alpha/alpha.hpp", 3)])

    def test_lesson_source_hangul_only_in_comments(self) -> None:  # 070-03 AC-6
        self.replace("lessons/tracks/01_first/01_one/main.cpp",
                     "int main() {}",
                     '// 한글 주석\n/* 블록 한글 주석 "따옴표" */\nint main() {}\n')
        hangul_warns = [f for f in self.findings() if "Hangul" in f.message]
        self.assertEqual(hangul_warns, [])

    def test_non_cpp_source_not_scanned(self) -> None:  # 070-03 AC-6
        write(self.tmp / "lessons/tracks/01_first/01_one/data.txt", 'const char* s = "안녕";\n')
        self.replace("lessons/tracks/01_first/01_one/lesson.toml",
                     'sources = ["main.cpp"]',
                     'sources = ["main.cpp", "data.txt"]')
        hangul_warns = [f for f in self.findings() if "Hangul" in f.message]
        self.assertEqual(hangul_warns, [])


class ModuleRulesTest(LessonsTestCase):
    """070-14 AC-6: tests for C++20 module rules in tools/lessons.py."""

    def test_entry_source_cannot_be_cppm(self) -> None:  # 070-14 AC-6
        write(self.tmp / "lessons/tracks/01_first/01_one/main.cppm", "int main() {}\n")
        self.replace("lessons/tracks/01_first/01_one/lesson.toml",
                     'sources = ["main.cpp"]',
                     'sources = ["main.cppm"]')
        errors = [f for f in self.findings() if f.level == "ERROR"]
        self.assertEqual(len(errors), 1, [str(f) for f in self.findings()])
        self.assertIn("entry", errors[0].message)
        self.assertIn(".cppm", errors[0].message)
        self.assertIn("01_one/lesson.toml", errors[0].path)

    def test_unit_files_cannot_contain_cppm(self) -> None:  # 070-14 AC-6
        write(self.tmp / "lessons/units/alpha/alpha.cppm", "export module alpha;\n")
        self.replace("lessons/units/alpha/unit.toml",
                     'files = ["alpha.hpp"]',
                     'files = ["alpha.hpp", "alpha.cppm"]')
        errors = [f for f in self.findings() if f.level == "ERROR" and "KI-039" in f.message]
        self.assertEqual(len(errors), 1, [str(f) for f in self.findings()])
        self.assertIn("units", errors[0].message)
        self.assertIn("alpha/unit.toml", errors[0].path)

    def test_lesson_sources_rejected_module_extension(self) -> None:  # 070-14 AC-6
        write(self.tmp / "lessons/tracks/01_first/01_one/extra.ixx", "export module one.extra;\n")
        self.replace("lessons/tracks/01_first/01_one/lesson.toml",
                     'sources = ["main.cpp"]',
                     'sources = ["main.cpp", "extra.ixx"]')
        errors = [f for f in self.findings() if f.level == "ERROR"]
        self.assertEqual(len(errors), 1, [str(f) for f in self.findings()])
        self.assertIn("unsupported module extension", errors[0].message)
        self.assertIn(".ixx", errors[0].message)
        self.assertIn("01_one/lesson.toml", errors[0].path)

    def test_uses_mod_path_validation(self) -> None:  # 070-14 AC-6
        self.replace("lessons/tracks/01_first/01_one/lesson.toml",
                     'uses = ["unit:alpha"]',
                     'uses = ["unit:alpha", "mod:atugcc/none.cppm"]')
        self.assertFinding("ERROR", "01_one/lesson.toml", "modules/atugcc/none.cppm does not exist")
        write(self.tmp / "modules/atugcc/core.cppm", "export module atugcc.core;\n")
        self.replace("lessons/tracks/01_first/01_one/lesson.toml",
                     '"mod:atugcc/none.cppm"',
                     '"mod:atugcc/core.cppm"')
        self.assertEqual([str(f) for f in self.findings()], [])

    def test_module_name_prefix(self) -> None:  # 070-14 AC-6
        self.replace("lessons/tracks/01_first/01_one/lesson.toml",
                     'sources = ["main.cpp"]',
                     'sources = ["main.cpp", "shapes.cppm"]')
        shapes = self.tmp / "lessons/tracks/01_first/01_one/shapes.cppm"
        write(shapes, "// preamble\n\nexport module other.shapes;\n")
        warns = [f for f in self.findings() if f.level == "WARN" and "shapes.cppm" in f.path]
        self.assertEqual(len(warns), 1, [str(f) for f in self.findings()])
        self.assertEqual(warns[0].line, 3)
        self.assertIn("name should be 'one' or start with 'one.'", warns[0].message)

        for decl in (
            "export module one.shapes;\n",
            "export module one.shapes:part;\n",
            "module one.shapes;\n",
            "module;\n",
            "module;\nexport module one.shapes;\n",
        ):
            write(shapes, decl)
            self.assertEqual([str(f) for f in self.findings()], [], f"failed for {decl!r}")

    def test_import_atugcc_requires_mod_in_uses(self) -> None:  # 070-14 AC-6
        write(self.tmp / "modules/atugcc/core.cppm", "export module atugcc.core;\n")
        self.replace("lessons/tracks/01_first/01_one/main.cpp",
                     "int main() {}",
                     "import atugcc.core;\nint main() {}")
        warns = [f for f in self.findings() if f.level == "WARN" and "import atugcc.core" in f.message]
        self.assertEqual(len(warns), 1, [str(f) for f in self.findings()])
        self.assertEqual(warns[0].line, 3)
        self.assertIn("uses has no mod:atugcc/core.cppm", warns[0].message)

        # with the mod: in uses -> no WARN
        self.replace("lessons/tracks/01_first/01_one/lesson.toml",
                     'uses = ["unit:alpha"]',
                     'uses = ["unit:alpha", "mod:atugcc/core.cppm"]')
        self.assertEqual([str(f) for f in self.findings()], [])

        # with the mod: only in a unit that the lesson uses (transitive) -> no WARN
        self.replace("lessons/tracks/01_first/01_one/lesson.toml",
                     'uses = ["unit:alpha", "mod:atugcc/core.cppm"]',
                     'uses = ["unit:alpha"]')
        self.replace("lessons/units/beta/unit.toml",
                     'uses = ["lib:atugcc/core/logger.hpp"]',
                     'uses = ["lib:atugcc/core/logger.hpp", "mod:atugcc/core.cppm"]')
        self.assertEqual([str(f) for f in self.findings()], [])

    def test_cppm_source_hangul_literal_warns(self) -> None:  # 070-14 AC-6
        self.replace("lessons/tracks/01_first/01_one/lesson.toml",
                     'sources = ["main.cpp"]',
                     'sources = ["main.cpp", "shapes.cppm"]')
        write(self.tmp / "lessons/tracks/01_first/01_one/shapes.cppm",
              'export module one.shapes;\n'
              'inline const char* msg = "안녕";\n')
        warns = [f for f in self.findings() if f.level == "WARN" and "Hangul" in f.message]
        self.assertEqual(len(warns), 1, [str(f) for f in self.findings()])
        self.assertIn("shapes.cppm", warns[0].path)
        self.assertEqual(warns[0].line, 2)

    def test_index_includes_mod_files_and_cppm_sources(self) -> None:  # 070-14 AC-1
        write(self.tmp / "modules/atugcc/core.cppm", "export module atugcc.core;\n")
        write(self.tmp / "lessons/tracks/01_first/01_one/shapes.cppm", "export module one.shapes;\n")
        self.replace("lessons/tracks/01_first/01_one/lesson.toml",
                     'sources = ["main.cpp"]',
                     'sources = ["main.cpp", "shapes.cppm"]')
        self.replace("lessons/tracks/01_first/01_one/lesson.toml",
                     'uses = ["unit:alpha"]',
                     'uses = ["unit:alpha", "mod:atugcc/core.cppm"]')
        catalog, report = lessons.load(self.tmp)
        lessons.check(catalog, report)
        self.assertEqual([str(f) for f in report.findings if f.level == "ERROR"], [])
        data = lessons.index(catalog)
        one = data["tracks"][0]["lessons"][0]
        self.assertIn("modules/atugcc/core.cppm", one["files"])
        self.assertIn("lessons/tracks/01_first/01_one/shapes.cppm", one["sources"])


if __name__ == "__main__":
    unittest.main()
