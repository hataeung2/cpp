#!/usr/bin/env python3
"""One-time move of spec 070-26: numbered lesson folders -> lesson ids, links rewritten, practice copies moved.

Usage (repository root, nothing else running on the lesson folders):
    py -3 docs/tasks/feature_070-26-lesson-order-manifest/migrate.py --dry-run   # print the plan only
    py -3 docs/tasks/feature_070-26-lesson-order-manifest/migrate.py             # do it

Kept as the task's record (spec 070-26 Assumption 8); it is not a tool and is not run again.
1. Map: lessons/tracks/<NN_track>/ -> <track>, lessons/tracks/<track>/<NN_lesson>/ -> <lesson id>.
   Every new name is checked (lesson id = folder target, no clash) before anything moves.
2. `git mv` every folder (history kept).
3. Rewrite each old folder name as a whole token in tracked text files, except docs/tasks/ (sealed task
   records). In docs/specs/ and docs/archive/ only inside Markdown link targets `](...)` (Assumption 7).
4. Move practice/lessons/tracks/... copies and rewrite the paths in practice/state.json.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path.cwd()
TRACKS = ROOT / "lessons/tracks"
ID_RE = re.compile(r'(?:^|\n)id[ \t]*=[ \t]*"([a-z0-9_]+)"')
NUMBERED = re.compile(r"^[0-9]{2}_([a-z0-9_]+)$")
LINK_TARGET = re.compile(r"\]\(([^)\s]*)\)")
LINKS_ONLY = ("docs/specs/", "docs/archive/")
SEALED = ("docs/tasks/",)


def build_map() -> tuple[dict[str, str], list[tuple[Path, Path]]]:
    """({old folder name: new name}, [(old path, new path)] in move order: tracks first, then lessons)."""
    names: dict[str, str] = {}
    moves: list[tuple[Path, Path]] = []
    lesson_moves: list[tuple[Path, Path]] = []
    for track in sorted(p for p in TRACKS.iterdir() if p.is_dir()):
        m = NUMBERED.match(track.name)
        new_track = m.group(1) if m else track.name
        if m:
            names[track.name] = new_track
            moves.append((track, TRACKS / new_track))
        for lesson in sorted(p for p in track.iterdir() if (p / "lesson.toml").is_file()):
            found = ID_RE.search((lesson / "lesson.toml").read_text(encoding="utf-8"))
            if not found:
                sys.exit(f"no id in {lesson / 'lesson.toml'}")
            lesson_id = found.group(1)
            if lesson.name != lesson_id:
                if lesson.name in names and names[lesson.name] != lesson_id:
                    sys.exit(f"folder name {lesson.name} is used twice with different ids")
                names[lesson.name] = lesson_id
                if (track / lesson_id).exists():  # the lesson target, checked before any track moves
                    sys.exit(f"target exists: {track / lesson_id}")
                lesson_moves.append((TRACKS / new_track / lesson.name, TRACKS / new_track / lesson_id))
    targets = [new for _, new in moves + lesson_moves]
    if len(set(targets)) != len(targets):
        sys.exit("two folders would get the same name")
    for _, new in moves:
        if new.exists():
            sys.exit(f"target exists: {new}")
    return names, moves + lesson_moves


def token_re(names: dict[str, str]) -> re.Pattern[str]:
    alternatives = "|".join(re.escape(n) for n in sorted(names, key=len, reverse=True))
    return re.compile(rf"(?<![A-Za-z0-9_])({alternatives})(?![A-Za-z0-9_])")


def rewrite(text: str, pattern: re.Pattern[str], names: dict[str, str], links_only: bool) -> str:
    swap = lambda m: names[m.group(1)]  # noqa: E731
    if not links_only:
        return pattern.sub(swap, text)
    return LINK_TARGET.sub(lambda m: "](" + pattern.sub(swap, m.group(1)) + ")", text)


def tracked_text_files() -> list[str]:
    out = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, check=True, capture_output=True, text=True).stdout
    return [p for p in out.split("\0") if p and not p.startswith(SEALED)]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    names, moves = build_map()
    pattern = token_re(names)
    print(f"{len(names)} folder names:")
    for old, new in names.items():
        print(f"  {old} -> {new}")

    edits: dict[Path, str] = {}
    count = 0
    for rel in tracked_text_files():
        path = ROOT / rel
        try:
            text = path.read_bytes().decode("utf-8")
        except (UnicodeDecodeError, FileNotFoundError):
            continue
        new = rewrite(text, pattern, names, rel.startswith(LINKS_ONLY))
        if new != text:
            n = sum(1 for _ in pattern.finditer(text)) if not rel.startswith(LINKS_ONLY) else \
                sum(len(pattern.findall(m.group(1))) for m in LINK_TARGET.finditer(text))
            count += n
            edits[path] = new
            print(f"  edit {rel} ({n})")
    print(f"{len(edits)} files, {count} replacements")

    state_path = ROOT / "practice/state.json"
    practice_tracks = ROOT / "practice/lessons/tracks"
    if args.dry_run:
        print("dry run: nothing changed")
        return 0

    # 1. text first (paths of edited files are the old ones), then the folders
    for path, text in edits.items():
        path.write_bytes(text.encode("utf-8"))
    for old, new in moves:
        subprocess.run(["git", "mv", str(old.relative_to(ROOT)), str(new.relative_to(ROOT))], cwd=ROOT, check=True)

    # 2. practice copies (git-ignored): same folder moves, then the state file's keys and origins
    if practice_tracks.is_dir():
        for old, new in moves:
            p_old = ROOT / "practice" / old.relative_to(ROOT)
            p_new = ROOT / "practice" / new.relative_to(ROOT)
            if p_old.is_dir():
                p_new.parent.mkdir(parents=True, exist_ok=True)
                p_old.rename(p_new)
                print(f"  practice {p_old.relative_to(ROOT)} -> {p_new.relative_to(ROOT)}")
    if state_path.is_file():
        state = json.loads(state_path.read_text(encoding="utf-8"))
        swap = lambda s: pattern.sub(lambda m: names[m.group(1)], s)  # noqa: E731
        state["files"] = {swap(k): {**v, "origin": swap(v["origin"])} for k, v in state.get("files", {}).items()}
        state_path.write_text(json.dumps(state, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"  practice/state.json: {len(state['files'])} entries")
    return 0


if __name__ == "__main__":
    sys.exit(main())
