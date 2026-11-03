#!/usr/bin/env python3
"""Lesson catalog: check the manifests under lessons/ and build the lesson index (spec 070-01, 070-10).

Usage:
    py -3 tools/lessons.py check [--root R]
    py -3 tools/lessons.py index [--root R] [--out out/lessons/index.json | -]

Layout (spec 070-01 §2.1, 070-10):
    lessons/tags.toml                              tag vocabulary (spec 070-10)
    lessons/units/<unit>/unit.toml                 reusable unit (header + README)
    lessons/tracks/<track>/track.toml              track title
    lessons/tracks/<track>/<lesson>/lesson.toml    one lesson = one executable lesson_<id>

`check` exits 1 when any ERROR is found. The web playground (070-02) and lint_docs.py import
this module (load / check / index) instead of running it.
Python 3.11+ standard library only (tomllib).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import tomllib
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

ID_RE = re.compile(r"^[a-z0-9_]+$")
PROFILES = ("quick", "long")
BUILDS = ("release", "debug")  # [run] build (spec 070-06 §2.6)
DEFAULT_TIMEOUT = 300
MAX_TIMEOUT = 1800
# The exact regexes of lessons/CMakeLists.txt (CMake cannot parse TOML). check() reads every
# lesson.toml with them too and compares the result with the TOML values, so a manifest that
# passes check is read the same way by CMake.
CMAKE_ID = re.compile(r'(?:^|\n)id[ \t]*=[ \t]*"([a-z0-9_]+)"')
CMAKE_SOURCES = re.compile(r"(?:^|\n)sources[ \t]*=[ \t]*\[([^\]\n]*)\]")
CMAKE_QUOTED = re.compile(r'"([^"]+)"')
CMAKE_PROFILE = re.compile(r'(?:^|\n)profile[ \t]*=[ \t]*"(quick|long)"')
CMAKE_TIMEOUT = re.compile(r"(?:^|\n)timeout[ \t]*=[ \t]*([0-9]+)")
INCLUDE_RE = re.compile(r'^[ \t]*#[ \t]*include[ \t]*"((?:units|atugcc)/[^"]+)"', re.M)
HANGUL_RE = re.compile(r"[\uac00-\ud7a3\u1100-\u11ff\u3130-\u318f]")
CPP_SUFFIXES = (".cpp", ".hpp", ".h", ".cc", ".cxx", ".hxx")



@dataclass
class Finding:
    level: str          # "ERROR" | "WARN"
    path: str           # repo-relative
    line: int | None
    message: str

    def __str__(self) -> str:
        where = f"{self.path}:{self.line}" if self.line else self.path
        return f"{self.level} {where}: {self.message}"


@dataclass
class Track:
    id: str
    title: str
    summary: str
    path: Path
    title_en: str = ""
    summary_en: str = ""


@dataclass
class Lesson:
    id: str
    title: str
    summary: str
    sources: list[str]
    uses: list[str]
    tags: list[str]
    profile: str
    timeout: int
    path: Path
    track: str
    build: str | None = None    # [run] build as written; None = the profile's default
    title_en: str = ""
    summary_en: str = ""


def effective_build(profile: str, build: str | None) -> str:
    """Build kind of a run: the manifest's `build`, else release for long and debug for quick."""
    return build or ("release" if profile == "long" else "debug")


@dataclass
class Unit:
    id: str
    title: str
    summary: str
    files: list[str]
    uses: list[str]
    path: Path
    title_en: str = ""
    summary_en: str = ""


@dataclass
class Tag:
    id: str
    ko: str
    en: str
    aliases: list[str]
    line: int | None


@dataclass
class Catalog:
    root: Path
    tracks: list[Track] = field(default_factory=list)
    lessons: list[Lesson] = field(default_factory=list)
    units: list[Unit] = field(default_factory=list)
    tags: dict[str, Tag] | None = None


class Report:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.findings: list[Finding] = []

    def add(self, level: str, path: Path, message: str, line: int | None = None) -> None:
        self.findings.append(Finding(level, rel(self.root, path), line, message))

    @property
    def errors(self) -> int:
        return sum(1 for f in self.findings if f.level == "ERROR")


def rel(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def read_toml(path: Path, report: Report) -> tuple[dict | None, str]:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as error:
        report.add("ERROR", path, f"not UTF-8: {error}")
        return None, ""
    try:
        return tomllib.loads(text), text
    except tomllib.TOMLDecodeError as error:
        line = getattr(error, "lineno", None)
        if line is None:
            match = re.search(r"line (\d+)", str(error))
            line = int(match.group(1)) if match else None
        report.add("ERROR", path, f"TOML syntax error: {error}", line)
        return None, text


def line_of(text: str, key: str) -> int | None:
    match = re.search(rf"^[ \t]*{re.escape(key)}[ \t]*=", text, re.M)
    return text.count("\n", 0, match.start()) + 1 if match else None


def header_line(text: str, key: str) -> int | None:
    match = re.search(rf"^[ \t]*\[[ \t]*{re.escape(key)}[ \t]*\]", text, re.M)
    return text.count("\n", 0, match.start()) + 1 if match else None


def str_field(data: dict, key: str, path: Path, text: str, report: Report, required: bool) -> str:
    value = data.get(key)
    if value is None:
        if required:
            report.add("ERROR", path, f"missing required key '{key}'")
        return ""
    if not isinstance(value, str):
        report.add("ERROR", path, f"'{key}' must be a string", line_of(text, key))
        return ""
    return value


def list_field(data: dict, key: str, path: Path, text: str, report: Report, required: bool) -> list[str]:
    value = data.get(key)
    if value is None:
        if required:
            report.add("ERROR", path, f"missing required key '{key}'")
        return []
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        report.add("ERROR", path, f"'{key}' must be a list of strings", line_of(text, key))
        return []
    if required and not value:
        report.add("ERROR", path, f"'{key}' must not be empty", line_of(text, key))
    return value


def check_id(value: str, path: Path, text: str, report: Report) -> None:
    if value and not ID_RE.fullmatch(value):
        report.add("ERROR", path, f"id {value!r} must match [a-z0-9_]+", line_of(text, "id"))


def check_local_files(names: list[str], key: str, folder: Path, manifest: Path, text: str, report: Report) -> None:
    for name in names:
        candidate = Path(name)
        if candidate.is_absolute() or ".." in candidate.parts:
            report.add("ERROR", manifest, f"'{key}' entry {name!r} must be a path inside the folder", line_of(text, key))
        elif not (folder / candidate).is_file():
            report.add("ERROR", manifest, f"'{key}' entry {name!r} does not exist", line_of(text, key))


def check_english(data: dict, title: str, summary: str, path: Path, text: str, report: Report) -> None:
    """Warn when the English title or summary is missing (spec 070-10 §2.2). A value that is not a
    string already has its ERROR from str_field, so it gets no WARN on top."""
    for key, korean, message in (("title_en", title, "English title, shown when the page is in English"),
                                 ("summary_en", summary, "English summary")):
        if korean and data.get(key) in (None, ""):
            report.add("WARN", path, f"missing '{key}' ({message})", line_of(text, key.removesuffix("_en")))


def normalize_name(s: str) -> str:
    """Normalize a name for duplicate checking (spec 070-10 §2.2)."""
    return " ".join(unicodedata.normalize("NFC", s).casefold().split())


def hangul_literals(text: str) -> list[int]:
    """Return sorted line numbers of C++ string or character literals containing Hangul (spec 070-03 §2.5)."""
    lines: set[int] = set()
    n = len(text)
    i = 0
    while i < n:
        if text[i:i + 2] == "//":
            nl = text.find("\n", i + 2)
            if nl == -1:
                break
            i = nl + 1
            continue

        if text[i:i + 2] == "/*":
            end = text.find("*/", i + 2)
            if end == -1:
                break
            i = end + 2
            continue

        if text[i] == '"':
            k = i - 1
            while k >= 0 and (text[k].isalnum() or text[k] == "_"):
                k -= 1
            token_before = text[k + 1 : i]
            is_raw = token_before in ("R", "u8R", "uR", "UR", "LR")

            start_line = text.count("\n", 0, i) + 1
            start_pos = i

            if is_raw:
                paren_pos = text.find("(", i + 1)
                valid_raw = False
                if paren_pos != -1 and (paren_pos - (i + 1)) <= 16:
                    delim = text[i + 1 : paren_pos]
                    if not any(c in " ()\\\r\n\t\v\f" for c in delim):
                        valid_raw = True

                if valid_raw:
                    closing = f"){delim}\""
                    close_pos = text.find(closing, paren_pos + 1)
                    if close_pos != -1:
                        if HANGUL_RE.search(text[start_pos : close_pos + len(closing)]):
                            lines.add(start_line)
                        i = close_pos + len(closing)
                        continue
                    else:
                        if HANGUL_RE.search(text[start_pos:]):
                            lines.add(start_line)
                        break
                else:
                    if HANGUL_RE.search(text[start_pos:]):
                        lines.add(start_line)
                    break
            else:
                i += 1
                found_close = False
                while i < n:
                    if text[i] == "\\":
                        i += 2
                    elif text[i] == '"':
                        if HANGUL_RE.search(text[start_pos : i + 1]):
                            lines.add(start_line)
                        i += 1
                        found_close = True
                        break
                    else:
                        i += 1
                if not found_close:
                    if HANGUL_RE.search(text[start_pos:]):
                        lines.add(start_line)
                continue

        if text[i] == "'":
            if i > 0 and text[i - 1].isalnum():
                k = i - 1
                while k >= 0 and (text[k].isalnum() or text[k] in "_'"):
                    k -= 1
                if text[k + 1].isdigit():
                    i += 1
                    continue

            start_line = text.count("\n", 0, i) + 1
            start_pos = i
            i += 1
            found_close = False
            while i < n:
                if text[i] == "\\":
                    i += 2
                elif text[i] == "'":
                    if HANGUL_RE.search(text[start_pos : i + 1]):
                        lines.add(start_line)
                    i += 1
                    found_close = True
                    break
                else:
                    i += 1
            if not found_close:
                if HANGUL_RE.search(text[start_pos:]):
                    lines.add(start_line)
            continue

        i += 1

    return sorted(lines)


def load_tags(lessons_dir: Path, report: Report) -> dict[str, Tag] | None:
    """Read the tag vocabulary lessons/tags.toml (spec 070-10 §2.2)."""
    tags_path = lessons_dir / "tags.toml"
    if not tags_path.is_file():
        report.add("WARN", tags_path, "no lessons/tags.toml: tag checks skipped")
        return None

    data, text = read_toml(tags_path, report)
    if data is None:
        return None

    tags: dict[str, Tag] = {}
    for key, value in data.items():
        line = header_line(text, key)
        if not isinstance(value, dict):
            report.add("ERROR", tags_path, f"'{key}' must be a table", line)
            continue
        if not ID_RE.fullmatch(key):
            report.add("ERROR", tags_path, f"tag {key!r} must match [a-z0-9_]+", line)

        ko = value.get("ko")
        if not isinstance(ko, str):
            report.add("ERROR", tags_path, f"tag '{key}': 'ko' must be a string", line)
            ko = ""

        en = value.get("en")
        if not isinstance(en, str):
            report.add("ERROR", tags_path, f"tag '{key}': 'en' must be a string", line)
            en = ""

        aliases_val = value.get("aliases")
        if aliases_val is None:
            aliases: list[str] = []
        elif not isinstance(aliases_val, list) or not all(isinstance(a, str) for a in aliases_val):
            report.add("ERROR", tags_path, f"tag '{key}': 'aliases' must be a list of strings", line)
            aliases = []
        else:
            aliases = list(aliases_val)

        tags[key] = Tag(id=key, ko=ko, en=en, aliases=aliases, line=line)

    owned_names: dict[str, str] = {}
    for key, tag in tags.items():
        names: list[str] = []
        for raw in (key, tag.ko, tag.en, *tag.aliases):
            norm = normalize_name(raw)
            if norm and norm not in names:
                names.append(norm)

        for name in names:
            if name in owned_names:
                other = owned_names[name]
                report.add("WARN", tags_path, f"tag '{key}': name {name!r} is also used by tag '{other}'", tag.line)
            else:
                owned_names[name] = key

    return tags


def check_cmake_view(text: str, lesson: "Lesson", manifest: Path, report: Report) -> None:
    """Read the manifest the way lessons/CMakeLists.txt does and compare with the TOML values."""
    hint = "lessons/CMakeLists.txt reads it with a line regex"

    def mismatch(key: str, cmake_value: object, toml_value: object, form: str) -> None:
        report.add("ERROR", manifest,
                   f"CMake reads {key} as {cmake_value!r}, TOML says {toml_value!r}: write {form} "
                   f"at the start of its own line ({hint})", line_of(text, key))

    match = CMAKE_ID.search(text)
    if lesson.id and (match.group(1) if match else None) != lesson.id:
        mismatch("id", match.group(1) if match else None, lesson.id, 'id = "<id>" (double quotes)')
    match = CMAKE_SOURCES.search(text)
    cmake_sources = CMAKE_QUOTED.findall(match.group(1)) if match else []
    if lesson.sources and cmake_sources != lesson.sources:
        mismatch("sources", cmake_sources, lesson.sources, 'sources = ["a.cpp", ...] (one line, double quotes)')
    match = CMAKE_PROFILE.search(text)
    cmake_profile = match.group(1) if match else "quick"
    if cmake_profile != lesson.profile:
        mismatch("profile", cmake_profile, lesson.profile, 'profile = "..." under [run]')
    if lesson.profile == "long":
        match = CMAKE_TIMEOUT.search(text)
        cmake_timeout = int(match.group(1)) if match else DEFAULT_TIMEOUT
        if cmake_timeout != lesson.timeout:
            mismatch("timeout", cmake_timeout, lesson.timeout, "timeout = N under [run]")


def load(root: Path = ROOT) -> tuple[Catalog, Report]:
    """Read every manifest under <root>/lessons. Schema problems go to the report."""
    report = Report(root)
    catalog = Catalog(root=root)
    lessons_dir = root / "lessons"
    catalog.tags = load_tags(lessons_dir, report)

    for manifest in sorted((lessons_dir / "units").glob("*/unit.toml")):
        data, text = read_toml(manifest, report)
        if data is None:
            continue
        unit = Unit(
            id=str_field(data, "id", manifest, text, report, True),
            title=str_field(data, "title", manifest, text, report, True),
            summary=str_field(data, "summary", manifest, text, report, False),
            files=list_field(data, "files", manifest, text, report, True),
            uses=list_field(data, "uses", manifest, text, report, False),
            path=manifest.parent,
            title_en=str_field(data, "title_en", manifest, text, report, False),
            summary_en=str_field(data, "summary_en", manifest, text, report, False),
        )
        check_id(unit.id, manifest, text, report)
        if unit.id and unit.id != unit.path.name:
            # lessons include units as "units/<id>/...", so the folder name is the id
            report.add("ERROR", manifest, f"unit id {unit.id!r} must equal its folder name {unit.path.name!r}",
                       line_of(text, "id"))
        check_local_files(unit.files, "files", unit.path, manifest, text, report)
        check_english(data, unit.title, unit.summary, manifest, text, report)
        catalog.units.append(unit)

    for track_dir in sorted(p for p in (lessons_dir / "tracks").glob("*") if p.is_dir()):
        track_manifest = track_dir / "track.toml"
        title, summary = track_dir.name, ""
        title_en, summary_en = "", ""
        if track_manifest.is_file():
            data, text = read_toml(track_manifest, report)
            if data is not None:
                title = str_field(data, "title", track_manifest, text, report, True) or track_dir.name
                summary = str_field(data, "summary", track_manifest, text, report, False)
                title_en = str_field(data, "title_en", track_manifest, text, report, False)
                summary_en = str_field(data, "summary_en", track_manifest, text, report, False)
                check_english(data, title, summary, track_manifest, text, report)
        else:
            report.add("ERROR", track_dir, "track folder has no track.toml")
        catalog.tracks.append(Track(id=track_dir.name, title=title, summary=summary, path=track_dir,
                                    title_en=title_en, summary_en=summary_en))

        for manifest in sorted(track_dir.glob("*/lesson.toml")):
            data, text = read_toml(manifest, report)
            if data is None:
                continue
            run = data.get("run", {})
            if not isinstance(run, dict):
                report.add("ERROR", manifest, "'run' must be a table", line_of(text, "run"))
                run = {}
            profile = run.get("profile", "quick")
            if profile not in PROFILES:
                report.add("ERROR", manifest, f"run.profile {profile!r} must be one of {', '.join(PROFILES)}",
                           line_of(text, "profile"))
                profile = "quick"
            timeout = run.get("timeout", DEFAULT_TIMEOUT)
            if not isinstance(timeout, int) or isinstance(timeout, bool) or not 1 <= timeout <= MAX_TIMEOUT:
                report.add("ERROR", manifest, f"run.timeout {timeout!r} must be an integer 1..{MAX_TIMEOUT}",
                           line_of(text, "timeout"))
                timeout = DEFAULT_TIMEOUT
            elif "timeout" in run and profile == "quick":
                report.add("WARN", manifest, "run.timeout is ignored for the quick profile", line_of(text, "timeout"))
            build = run.get("build")
            if build is not None and build not in BUILDS:
                report.add("ERROR", manifest, f"run.build {build!r} must be one of {', '.join(BUILDS)}",
                           line_of(text, "build"))
                build = None
            lesson = Lesson(
                id=str_field(data, "id", manifest, text, report, True),
                title=str_field(data, "title", manifest, text, report, True),
                summary=str_field(data, "summary", manifest, text, report, False),
                sources=list_field(data, "sources", manifest, text, report, True),
                uses=list_field(data, "uses", manifest, text, report, False),
                tags=list_field(data, "tags", manifest, text, report, False),
                profile=profile,
                timeout=timeout,
                path=manifest.parent,
                track=track_dir.name,
                build=build,
                title_en=str_field(data, "title_en", manifest, text, report, False),
                summary_en=str_field(data, "summary_en", manifest, text, report, False),
            )
            check_id(lesson.id, manifest, text, report)
            check_local_files(lesson.sources, "sources", lesson.path, manifest, text, report)
            check_cmake_view(text, lesson, manifest, report)
            check_english(data, lesson.title, lesson.summary, manifest, text, report)
            if catalog.tags is not None:
                for tag in lesson.tags:
                    if tag not in catalog.tags:
                        report.add("WARN", manifest, f"tag {tag!r} is not in lessons/tags.toml", line_of(text, "tags"))
            catalog.lessons.append(lesson)

    return catalog, report


def resolve_uses(catalog: Catalog, uses: list[str], seen: set[str] | None = None) -> list[str]:
    """Transitive closure of `uses` in first-seen order (cycles are cut, check() reports them)."""
    units = {u.id: u for u in catalog.units}
    seen = set() if seen is None else seen
    order: list[str] = []
    for ref in uses:
        if ref in seen:
            continue
        seen.add(ref)
        order.append(ref)
        kind, _, name = ref.partition(":")
        if kind == "unit" and name in units:
            order += resolve_uses(catalog, units[name].uses, seen)
    return order


def ref_files(catalog: Catalog, ref: str) -> list[str]:
    kind, _, name = ref.partition(":")
    if kind == "lib":
        return [f"include/{name}"]
    unit = next((u for u in catalog.units if u.id == name), None)
    if unit is None:
        return []
    base = rel(catalog.root, unit.path)
    files = [f"{base}/{f}" for f in unit.files]
    if (unit.path / "README.md").is_file():
        files.append(f"{base}/README.md")
    return files


def check(catalog: Catalog, report: Report) -> Report:
    """Cross-manifest checks: unique ids, `uses` targets, unit cycles, #include vs `uses`, README.en.md, Hangul literals."""
    root = catalog.root
    for kind, items in (("lesson", catalog.lessons), ("unit", catalog.units)):
        first: dict[str, Path] = {}
        for item in items:
            manifest_path = item.path / f"{kind}.toml"
            if (item.path / "README.md").is_file() and not (item.path / "README.en.md").is_file():
                report.add("WARN", manifest_path, "no README.en.md (English README, spec 070-03)")
            if not item.id:
                continue
            if item.id in first:
                report.add("ERROR", manifest_path,
                           f"duplicate {kind} id {item.id!r} (also {rel(root, first[item.id])})")
            else:
                first[item.id] = item.path

    unit_ids = {u.id for u in catalog.units}
    owners: list[tuple[Path, list[str], list[str]]] = (
        [(u.path / "unit.toml", u.uses, u.files) for u in catalog.units]
        + [(l.path / "lesson.toml", l.uses, l.sources) for l in catalog.lessons])
    for manifest, uses, _ in owners:
        for ref in uses:
            kind, _, name = ref.partition(":")
            if kind == "unit":
                if name not in unit_ids:
                    report.add("ERROR", manifest, f"uses {ref!r}: no unit with that id")
            elif kind == "lib":
                lib = Path(name)
                if lib.is_absolute() or lib.anchor or ".." in lib.parts or not (root / "include" / lib).is_file():
                    report.add("ERROR", manifest, f"uses {ref!r}: include/{name} does not exist")
            else:
                report.add("ERROR", manifest, f"uses {ref!r}: must start with 'unit:' or 'lib:'")

    # unit cycles
    graph = {u.id: [r.partition(":")[2] for r in u.uses if r.startswith("unit:")] for u in catalog.units}
    state: dict[str, int] = {}
    reported: set[frozenset[str]] = set()

    def visit(node: str, stack: list[str]) -> None:
        state[node] = 1
        for nxt in graph.get(node, []):
            if state.get(nxt) == 1:
                cycle = stack[stack.index(nxt):] + [nxt]
                key = frozenset(cycle)
                if key not in reported:
                    reported.add(key)
                    unit = next(u for u in catalog.units if u.id == nxt)
                    report.add("ERROR", unit.path / "unit.toml", "unit cycle: " + " -> ".join(cycle))
            elif nxt in graph and state.get(nxt) is None:
                visit(nxt, stack + [nxt])
        state[node] = 2

    for unit_id in graph:
        if state.get(unit_id) is None:
            visit(unit_id, [unit_id])

    # #include "units/..." and "atugcc/..." must be covered by the owner's transitive uses
    for manifest, uses, names in owners:
        closure = resolve_uses(catalog, uses)
        covered_units = {r.partition(":")[2] for r in closure if r.startswith("unit:")}
        covered_libs = {r.partition(":")[2] for r in closure if r.startswith("lib:")}
        if manifest.name == "unit.toml":
            covered_units.add(manifest.parent.name)
        for name in names:
            source = manifest.parent / name
            if not source.is_file():
                continue
            text = source.read_text(encoding="utf-8", errors="replace")
            if source.suffix in CPP_SUFFIXES:
                for line in hangul_literals(text):
                    report.add("WARN", source,
                               "string literal with Hangul: program output is English (spec 070-10 Assumption 14)",
                               line)
            for match in INCLUDE_RE.finditer(text):
                target = match.group(1)
                line = text.count("\n", 0, match.start()) + 1
                if target.startswith("units/"):
                    unit_dir = target.split("/")[1]
                    if unit_dir not in unit_ids and not (root / "lessons" / target).is_file():
                        report.add("WARN", source, f'#include "{target}": no such unit', line)
                    elif unit_dir not in covered_units:
                        report.add("WARN", source, f'#include "{target}" but uses has no unit:{unit_dir}', line)
                elif target.partition("/")[2] and target not in covered_libs:
                    report.add("WARN", source, f'#include "{target}" but uses has no lib:{target}', line)
    return report


def index(catalog: Catalog) -> dict:
    """Lesson index for the web playground (spec 070-01 §2.4, 070-10 §2.3). Paths are repo-relative."""
    root = catalog.root

    def readme(folder: Path, name: str = "README.md") -> str | None:
        return f"{rel(root, folder)}/{name}" if (folder / name).is_file() else None

    def files_of(uses: list[str]) -> list[str]:
        out: list[str] = []
        for ref in resolve_uses(catalog, uses):
            for path in ref_files(catalog, ref):
                if path not in out:
                    out.append(path)
        return out

    closures = {l.id: set(resolve_uses(catalog, l.uses)) for l in catalog.lessons}
    tracks = []
    for track in catalog.tracks:
        lessons = []
        for lesson in (l for l in catalog.lessons if l.track == track.id):
            base = rel(root, lesson.path)
            lessons.append({
                "id": lesson.id,
                "title": lesson.title,
                "titleEn": lesson.title_en or None,
                "summary": lesson.summary,
                "summaryEn": lesson.summary_en or None,
                "path": base,
                "target": f"lesson_{lesson.id}",
                "entry": f"{base}/{lesson.sources[0]}" if lesson.sources else None,
                "sources": [f"{base}/{s}" for s in lesson.sources],
                "readme": readme(lesson.path),
                "readmeEn": readme(lesson.path, "README.en.md"),
                "uses": lesson.uses,
                "files": files_of(lesson.uses),
                "tags": lesson.tags,
                # build: as written (null = the run profile's default, see effective_build)
                "run": {"profile": lesson.profile, "timeout": lesson.timeout, "build": lesson.build},
            })
        tracks.append({
            "id": track.id,
            "title": track.title,
            "titleEn": track.title_en or None,
            "summary": track.summary,
            "summaryEn": track.summary_en or None,
            "path": rel(root, track.path),
            "lessons": lessons,
        })
    units = []
    for unit in catalog.units:
        base = rel(root, unit.path)
        units.append({
            "id": unit.id,
            "title": unit.title,
            "titleEn": unit.title_en or None,
            "summary": unit.summary,
            "summaryEn": unit.summary_en or None,
            "path": base,
            "files": [f"{base}/{f}" for f in unit.files],
            "readme": readme(unit.path),
            "readmeEn": readme(unit.path, "README.en.md"),
            "uses": unit.uses,
            "usedBy": [l.id for l in catalog.lessons if f"unit:{unit.id}" in closures[l.id]],
        })
    tags = {t.id: {"ko": t.ko, "en": t.en, "aliases": list(t.aliases)} for t in (catalog.tags or {}).values()}
    return {"version": 1, "tracks": tracks, "units": units, "tags": tags}


def run_check(root: Path = ROOT) -> Report:
    catalog, report = load(root)
    return check(catalog, report)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=["check", "index"])
    parser.add_argument("--root", type=Path, default=ROOT, help="repository root (default: this checkout)")
    parser.add_argument("--out", default=None, help="index output file, '-' for stdout (default: out/lessons/index.json)")
    args = parser.parse_args(argv)
    root = args.root.resolve()

    if args.command == "check":
        report = run_check(root)
        for finding in report.findings:
            print(finding)
        catalog, _ = load(root)
        print(f"lessons: {report.errors} error(s), {len(report.findings) - report.errors} warning(s); "
              f"{len(catalog.tracks)} track(s), {len(catalog.lessons)} lesson(s), {len(catalog.units)} unit(s)")
        return 1 if report.errors else 0

    catalog, report = load(root)
    check(catalog, report)
    if report.errors:
        for finding in report.findings:
            print(finding, file=sys.stderr)
        return 1
    text = json.dumps(index(catalog), ensure_ascii=False, indent=2) + "\n"
    if args.out == "-":
        sys.stdout.write(text)
    else:
        out = Path(args.out) if args.out else root / "out" / "lessons" / "index.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
        print(f"lessons: index written to {rel(root, out)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
