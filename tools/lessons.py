#!/usr/bin/env python3
"""Lesson catalog: check the manifests under lessons/ and build the lesson index (spec 070-01).

Usage:
    py -3 tools/lessons.py check [--root R]
    py -3 tools/lessons.py index [--root R] [--out out/lessons/index.json | -]

Layout (spec 070-01 §2.1):
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


@dataclass
class Catalog:
    root: Path
    tracks: list[Track] = field(default_factory=list)
    lessons: list[Lesson] = field(default_factory=list)
    units: list[Unit] = field(default_factory=list)


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
        )
        check_id(unit.id, manifest, text, report)
        if unit.id and unit.id != unit.path.name:
            # lessons include units as "units/<id>/...", so the folder name is the id
            report.add("ERROR", manifest, f"unit id {unit.id!r} must equal its folder name {unit.path.name!r}",
                       line_of(text, "id"))
        check_local_files(unit.files, "files", unit.path, manifest, text, report)
        catalog.units.append(unit)

    for track_dir in sorted(p for p in (lessons_dir / "tracks").glob("*") if p.is_dir()):
        track_manifest = track_dir / "track.toml"
        title, summary = track_dir.name, ""
        if track_manifest.is_file():
            data, text = read_toml(track_manifest, report)
            if data is not None:
                title = str_field(data, "title", track_manifest, text, report, True) or track_dir.name
                summary = str_field(data, "summary", track_manifest, text, report, False)
        else:
            report.add("ERROR", track_dir, "track folder has no track.toml")
        catalog.tracks.append(Track(id=track_dir.name, title=title, summary=summary, path=track_dir))

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
            )
            check_id(lesson.id, manifest, text, report)
            check_local_files(lesson.sources, "sources", lesson.path, manifest, text, report)
            check_cmake_view(text, lesson, manifest, report)
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
    """Cross-manifest checks: unique ids, `uses` targets, unit cycles, #include vs `uses`."""
    root = catalog.root
    for kind, items in (("lesson", catalog.lessons), ("unit", catalog.units)):
        first: dict[str, Path] = {}
        for item in items:
            if not item.id:
                continue
            if item.id in first:
                report.add("ERROR", item.path / f"{kind}.toml",
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
    """Lesson index for the web playground (spec 070-01 §2.4). Paths are repo-relative."""
    root = catalog.root

    def readme(folder: Path) -> str | None:
        return f"{rel(root, folder)}/README.md" if (folder / "README.md").is_file() else None

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
                "summary": lesson.summary,
                "path": base,
                "target": f"lesson_{lesson.id}",
                "entry": f"{base}/{lesson.sources[0]}" if lesson.sources else None,
                "sources": [f"{base}/{s}" for s in lesson.sources],
                "readme": readme(lesson.path),
                "uses": lesson.uses,
                "files": files_of(lesson.uses),
                "tags": lesson.tags,
                # build: as written (null = the run profile's default, see effective_build)
                "run": {"profile": lesson.profile, "timeout": lesson.timeout, "build": lesson.build},
            })
        tracks.append({"id": track.id, "title": track.title, "summary": track.summary,
                       "path": rel(root, track.path), "lessons": lessons})
    units = []
    for unit in catalog.units:
        base = rel(root, unit.path)
        units.append({
            "id": unit.id,
            "title": unit.title,
            "summary": unit.summary,
            "path": base,
            "files": [f"{base}/{f}" for f in unit.files],
            "readme": readme(unit.path),
            "uses": unit.uses,
            "usedBy": [l.id for l in catalog.lessons if f"unit:{unit.id}" in closures[l.id]],
        })
    return {"version": 1, "tracks": tracks, "units": units}


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
