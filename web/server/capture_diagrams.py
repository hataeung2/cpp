#!/usr/bin/env python3
"""Run every seed lesson through the playground runner and save their Mermaid parts.

    python3 web/server/capture_diagrams.py [--out web/frontend/test/fixtures/seed_diagrams.json]

The file is the fixture of web/frontend/test/mermaidParse.test.ts (spec 070-02 AC-8): every
part the lessons produce must pass mermaid.parse. Run it again after changing a lesson or the
diagram generator (020-04), then `npm test` in web/frontend. Linux / WSL only (runner).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import runner  # noqa: E402

DEFAULT_OUT = runner.ROOT / "web" / "frontend" / "test" / "fixtures" / "seed_diagrams.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)

    catalog, _ = runner.lessons.load(runner.ROOT)
    runs = runner.RunManager(runner.ROOT)
    parts = []
    for lesson in catalog.lessons:
        job = runs.create(lesson.id)
        index, done = 0, False
        while not done:
            events, done = job.events_from(index, 1.0)
            index += len(events)
        name, data = job.events[-1]
        if not data["build"]["ok"] or data["run"]["exitCode"] != 0:
            print(f"error: lesson {lesson.id} did not finish cleanly: {data['build']} {data['run']}", file=sys.stderr)
            return 1
        for part in data["diagrams"]:
            parts.append({"lesson": lesson.id, **{k: part[k] for k in ("tracer", "part", "parts", "diagram", "title", "source")}})
        print(f"{lesson.id}: {len(data['diagrams'])} parts")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({"version": 1, "parts": parts}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {len(parts)} parts to {args.out.relative_to(runner.ROOT) if args.out.is_relative_to(runner.ROOT) else args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
