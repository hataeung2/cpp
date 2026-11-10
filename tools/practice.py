#!/usr/bin/env python3
"""Practice workspace: lesson copies that can be edited, built and reset (spec 070-16).

The git-ignored folder `practice/` mirrors the paths under `lessons/`:
    lessons/tracks/<track>/<lesson>/main.cpp -> practice/lessons/tracks/<track>/<lesson>/main.cpp
    lessons/units/<unit>/<unit>.hpp          -> practice/lessons/units/<unit>/<unit>.hpp
A lesson copy holds its lesson.toml and sources; each unit it uses (transitive `uses`) gets a
copy of its unit.toml and files, shared by every lesson that uses the unit. CMake builds a lesson
copy as `practice_<id>` (lessons/CMakeLists.txt).

practice/state.json records, per copy, its origin and the origin's SHA-256 when the copy was made
or reset (baseSha). A copy is modified when its sha differs from baseSha; the origin changed when
the origin's sha differs. An unmodified copy follows a changed origin; manifests always follow.
Reset backs up the copies it overwrites in practice/backup/<YYYYMMDD-HHMMSS>[-n]/ (newest 10 kept).

Usage:
    py -3 tools/practice.py start <lesson>
    py -3 tools/practice.py status [<lesson>]
    py -3 tools/practice.py reset <lesson> | --unit <id> | --file <practice path>
    py -3 tools/practice.py path <lesson>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lessons  # noqa: E402  (the web server has loaded it already: the same module is used)

ROOT = Path(__file__).resolve().parent.parent
PRACTICE_DIR = "practice"
STATE_FILE = "practice/state.json"
BACKUP_DIR = "practice/backup"
KEEP_BACKUPS = 10
MANIFESTS = ("lesson.toml", "unit.toml")


class PracticeError(Exception):
    """Unknown lesson or unit, or a path that is not a recorded practice copy."""


def practice_path(origin: str) -> str:
    """`lessons/...` -> `practice/lessons/...` (repo-relative, '/')."""
    if not origin.startswith("lessons/"):
        raise ValueError(f"not a lessons/ path: {origin!r}")
    return f"{PRACTICE_DIR}/{origin}"


def origin_path(path: str) -> str:
    """`practice/lessons/...` -> `lessons/...`."""
    if not path.startswith(f"{PRACTICE_DIR}/lessons/"):
        raise ValueError(f"not a practice copy path: {path!r}")
    return path[len(PRACTICE_DIR) + 1:]


def is_manifest(path: str) -> bool:
    return path.rsplit("/", 1)[-1] in MANIFESTS


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _stamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def _backup_order(folder: Path) -> tuple[str, int]:
    """`<date>-<time>` sorts before `<date>-<time>-2` before `<date>-<time>-10`."""
    parts = folder.name.split("-")
    return ("-".join(parts[:2]), int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 1)


class _Backup:
    """One backup folder per operation, made when the first file goes into it."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.folder: Path | None = None

    def keep(self, path: str, move: bool = False) -> None:
        if self.folder is None:
            base = self.root / BACKUP_DIR / _stamp()
            # next number after the highest of this second (not the first free one: pruning frees old names)
            taken = [_backup_order(p)[1] for p in base.parent.glob(f"{base.name}*") if _backup_order(p)[0] == base.name]
            self.folder = base.with_name(f"{base.name}-{max(taken) + 1}") if taken else base
            self.folder.mkdir(parents=True)
        target = self.folder / path
        target.parent.mkdir(parents=True, exist_ok=True)
        (shutil.move if move else shutil.copyfile)(self.root / path, target)

    def finish(self) -> str | None:
        """Prune to the newest KEEP_BACKUPS folders; the repo-relative folder of this operation."""
        if self.folder is None:
            return None
        folders = sorted((p for p in (self.root / BACKUP_DIR).iterdir() if p.is_dir()), key=_backup_order)
        for old in folders[:-KEEP_BACKUPS]:
            shutil.rmtree(old)
        return self.folder.relative_to(self.root).as_posix()


class Workspace:
    def __init__(self, root: Path = ROOT) -> None:
        self.root = Path(root)

    # --- catalog ---------------------------------------------------------------------------
    def _catalog(self) -> lessons.Catalog:
        return lessons.load(self.root)[0]  # read on every call: manifest edits are seen

    def _lesson(self, catalog: lessons.Catalog, lesson_id: str) -> lessons.Lesson:
        found = next((l for l in catalog.lessons if l.id == lesson_id), None)
        if found is None:
            raise PracticeError(f"unknown lesson: {lesson_id!r}")
        return found

    def _groups(self, catalog: lessons.Catalog, lesson: lessons.Lesson) -> list[tuple[str, str, list[str]]]:
        """(id, practice folder, origin files) of the lesson, then of each unit it uses in `resolve_uses`
        order. A unit missing from the catalog is skipped (`lessons.py check` reports it)."""
        units = {u.id: u for u in catalog.units}
        groups = [(lesson.id, *self._group(lesson.path, "lesson.toml", lesson.sources))]
        for ref in lessons.resolve_uses(catalog, lesson.uses):
            kind, _, name = ref.partition(":")
            if kind == "unit" and name in units:
                groups.append((name, *self._group(units[name].path, "unit.toml", units[name].files)))
        return groups

    def _group(self, folder: Path, manifest: str, names: list[str]) -> tuple[str, list[str]]:
        base = lessons.rel(self.root, folder)
        return practice_path(base), [f"{base}/{n}" for n in [manifest, *names]]

    def lesson_files(self, lesson_id: str) -> list[str]:
        """Origin paths of the lesson's lesson.toml and sources."""
        catalog = self._catalog()
        return self._groups(catalog, self._lesson(catalog, lesson_id))[0][2]

    def unit_ids(self, lesson_id: str) -> list[str]:
        """Units the lesson uses that exist, in `resolve_uses` order."""
        catalog = self._catalog()
        return [g[0] for g in self._groups(catalog, self._lesson(catalog, lesson_id))[1:]]

    # --- state -----------------------------------------------------------------------------
    def _read_state(self) -> dict[str, dict]:
        """{practice path: {"origin", "baseSha"}}; a damaged file is set aside and rebuilt (spec §4)."""
        path = self.root / STATE_FILE
        if not path.is_file():
            return {}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            files = data["files"] if isinstance(data, dict) and data.get("version") == 1 else None
            if isinstance(files, dict) and all(
                    isinstance(e, dict) and isinstance(e.get("origin"), str) and isinstance(e.get("baseSha"), str)
                    for e in files.values()):
                return files
        except (ValueError, KeyError, UnicodeDecodeError):
            pass
        aside, n = path.with_name(f"state.json.broken-{_stamp()}"), 2
        while aside.exists():
            aside, n = aside.with_name(f"state.json.broken-{_stamp()}-{n}"), n + 1
        os.replace(path, aside)
        files = {}
        for copy in sorted((self.root / PRACTICE_DIR / "lessons").rglob("*")):
            rel = copy.relative_to(self.root).as_posix()
            origin = self.root / origin_path(rel)
            if copy.is_file() and origin.is_file():  # program output in a copy folder has no origin
                files[rel] = {"origin": origin_path(rel), "baseSha": _sha(origin.read_bytes())}
        self._write_state(files)
        return files

    def _write_state(self, files: dict[str, dict]) -> None:
        path = self.root / STATE_FILE
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(f"state.json.tmp-{os.getpid()}")
        tmp.write_text(json.dumps({"version": 1, "files": files}, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(tmp, path)

    # --- operations ------------------------------------------------------------------------
    def start(self, lesson_id: str) -> dict:
        """Copy the lesson and its units where no copy exists yet (never overwrites), then status."""
        catalog = self._catalog()
        state = self._read_state()
        for _, _, origins in self._groups(catalog, self._lesson(catalog, lesson_id)):
            for origin in origins:
                src, copy = self.root / origin, self.root / practice_path(origin)
                if not src.is_file():
                    continue
                if not copy.is_file():
                    copy.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(src, copy)
                if practice_path(origin) not in state:  # a copy made by hand is recorded as it is
                    state[practice_path(origin)] = {"origin": origin, "baseSha": _sha(src.read_bytes())}
        self._write_state(state)
        return self.status(lesson_id)

    def status(self, lesson_id: str) -> dict:
        """Follow origin changes, then each copy's state: same, modified, both, missing-origin."""
        catalog = self._catalog()
        groups = self._groups(catalog, self._lesson(catalog, lesson_id))
        state = self._read_state()
        backup = _Backup(self.root)
        changed = False
        for _, folder, origins in groups:
            changed |= self._follow(state, folder, origins, backup)
        if changed:
            self._write_state(state)
        backup.finish()
        listed = [{"id": gid, "dir": folder, "files": [f for f in (self._file(state, o) for o in origins) if f]}
                  for gid, folder, origins in groups]
        return {"lesson": lesson_id, "dir": listed[0]["dir"], "files": listed[0]["files"], "units": listed[1:]}

    def status_all(self) -> dict:
        """Every lesson with a copy; unit copies no listed lesson reaches; copies whose lesson or unit is gone."""
        catalog = self._catalog()
        state = self._read_state()
        out, known = [], set()
        for lesson in catalog.lessons:
            folder = self._groups(catalog, lesson)[0][1]
            if any(p.startswith(folder + "/") for p in state):
                out.append(self.status(lesson.id))
                known |= {f["path"] for r in [out[-1], *out[-1]["units"]] for f in r["files"]}
        state = self._read_state()  # the statuses above may have followed origins
        backup = _Backup(self.root)
        units = []
        for unit in catalog.units:
            gid, folder, origins = unit.id, *self._group(unit.path, "unit.toml", unit.files)
            reached = any(p.startswith(folder + "/") for p in known)  # followed by a lesson's status above
            if not reached and self._follow(state, folder, origins, backup):
                self._write_state(state)
            files = [f for f in (self._file(state, o) for o in origins) if f and f["path"] not in known]
            if files:
                units.append({"id": gid, "dir": folder, "files": files})
            known |= {p for p in state if p.startswith(folder + "/")}
        backup.finish()
        orphans = [{"path": p, "origin": e["origin"], "state": "missing-origin"}
                   for p, e in sorted(state.items()) if p not in known]
        return {"lessons": out, "units": units, "orphans": orphans}

    def reset(self, *, lesson: str | None = None, unit: str | None = None, path: str | None = None) -> dict:
        """Put the origin back into the copies of one lesson (not its units), one unit or one file."""
        if [lesson, unit, path].count(None) != 2:
            raise ValueError("give exactly one of lesson, unit, path")
        catalog = self._catalog()
        state = self._read_state()
        if lesson is not None:
            folder = self._groups(catalog, self._lesson(catalog, lesson))[0][1]
            targets = [p for p in state if p.startswith(folder + "/")]
        elif unit is not None:
            found = next((u for u in catalog.units if u.id == unit), None)
            if found is None:
                raise PracticeError(f"unknown unit: {unit!r}")
            folder = practice_path(lessons.rel(self.root, found.path))
            targets = [p for p in state if p.startswith(folder + "/")]
        else:
            if path not in state:
                raise PracticeError(f"not a recorded practice copy: {path!r}")
            targets = [path]
        backup = _Backup(self.root)
        rewritten = []
        for p in sorted(targets):
            src, copy = self.root / state[p]["origin"], self.root / p
            if not src.is_file():
                continue
            data = src.read_bytes()
            if not copy.is_file() or copy.read_bytes() != data:
                if copy.is_file():
                    backup.keep(p)
                copy.parent.mkdir(parents=True, exist_ok=True)
                copy.write_bytes(data)
                rewritten.append(p)
            state[p]["baseSha"] = _sha(data)  # also when equal: a `both` copy becomes `same`
        self._write_state(state)
        return {"reset": rewritten, "backup": backup.finish()}

    # --- helpers ---------------------------------------------------------------------------
    def _follow(self, state: dict[str, dict], folder: str, origins: list[str], backup: _Backup) -> bool:
        """Bring the copies of one lesson or unit in line with its origin (spec Assumption 7)."""
        recorded = [p for p in state if p.startswith(folder + "/")]
        if not recorded:
            return False  # never started: nothing to follow
        expected = {practice_path(o): o for o in origins}
        changed = False
        for p in recorded:
            if p not in expected and not is_manifest(p):  # dropped from the origin's sources
                if (self.root / p).is_file():
                    backup.keep(p, move=True)
                del state[p]
                changed = True
        for p, origin in expected.items():
            src, copy = self.root / origin, self.root / p
            if not src.is_file():
                continue
            data = src.read_bytes()
            sha = _sha(data)
            if not copy.is_file():  # a new source, or a copy removed by hand: same as a fresh copy
                copy.parent.mkdir(parents=True, exist_ok=True)
                copy.write_bytes(data)
                state[p] = {"origin": origin, "baseSha": sha}
                changed = True
                continue
            entry = state.setdefault(p, {"origin": origin, "baseSha": sha})
            unmodified = _sha(copy.read_bytes()) == entry["baseSha"]
            if sha != entry["baseSha"] and (unmodified or is_manifest(p)):
                copy.write_bytes(data)
                entry["baseSha"] = sha
                changed = True
            elif is_manifest(p) and copy.read_bytes() != data:
                copy.write_bytes(data)
                changed = True
        return changed

    def _file(self, state: dict[str, dict], origin: str) -> dict | None:
        p = practice_path(origin)
        copy, src = self.root / p, self.root / origin
        if not copy.is_file():
            return None
        if not src.is_file():
            return {"path": p, "origin": origin, "state": "missing-origin"}
        origin_sha = _sha(src.read_bytes())
        base = state.get(p, {}).get("baseSha", origin_sha)  # a copy not recorded yet is judged against the origin
        modified = _sha(copy.read_bytes()) != base
        origin_changed = origin_sha != base
        name = ("both" if origin_changed else "modified") if modified else ("origin-changed" if origin_changed else "same")
        return {"path": p, "origin": origin, "state": name}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="practice.py", description="Practice copies of lessons (spec 070-16).")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("start", help="copy a lesson and its units").add_argument("lesson")
    sub.add_parser("status", help="state of the copies").add_argument("lesson", nargs="?")
    reset = sub.add_parser("reset", help="put the origin back (backup first)")
    reset.add_argument("lesson", nargs="?")
    reset.add_argument("--unit")
    reset.add_argument("--file")
    sub.add_parser("path", help="the lesson's practice folder").add_argument("lesson")
    args = parser.parse_args(argv)
    if args.command == "reset" and [args.lesson, args.unit, args.file].count(None) != 2:
        reset.error("give exactly one of <lesson>, --unit, --file")

    ws = Workspace()
    try:
        if args.command == "start":
            print(ws.start(args.lesson)["dir"])
        elif args.command == "path":  # prints only; changes nothing
            catalog = ws._catalog()
            print(ws._groups(catalog, ws._lesson(catalog, args.lesson))[0][1])
        elif args.command == "status":
            every = None if args.lesson is not None else ws.status_all()
            reports = [ws.status(args.lesson)] if every is None else every["lessons"] + every["units"]
            files = [f for r in reports for f in r["files"] + [f for u in r.get("units", []) for f in u["files"]]]
            seen = set()
            for f in files + (every["orphans"] if every else []):
                if f["path"] not in seen:  # a unit shared by two lessons is listed once
                    seen.add(f["path"])
                    print(f"{f['state']:>16} {f['path']}")
        else:
            result = ws.reset(lesson=args.lesson, unit=args.unit, path=args.file)
            for p in result["reset"]:
                print(p)
            if result["backup"]:
                print(f"backup: {result['backup']}")
    except (PracticeError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
