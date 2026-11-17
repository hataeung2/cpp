# Walkthrough: 070-26 레슨 순서를 매니페스트로 옮기고 폴더 번호 제거

Spec: [/docs/specs/070_26_lesson_order_manifest.md](/docs/specs/070_26_lesson_order_manifest.md) · Plan: [plan.md](plan.md) · Test record: [testrecord.md](testrecord.md)

## Result
- `lessons/curriculum.toml` holds the order of the tracks and of the lessons in each track. `tools/lessons.py` loads in that order: an unlisted lesson or track comes last with a WARN; a listed lesson without a folder, listed twice or listed under another track is an ERROR; a missing or broken file is an ERROR and the order falls back to folder names.
- Folder names are ids: `lessons/tracks/<track id>/<lesson id>/`. A lesson folder whose name differs from its id, or a numbered track folder, is an ERROR.
- 3 tracks and 21 lessons renamed with `git mv`; links rewritten in living docs and in the link targets of finished specs by the one-off [migrate.py](migrate.py), which also moved the local `practice/` copies and `state.json` entries.
- Order before and after is the same (AC-2), practice status the same (AC-7), both hosts build and test 61 / 61, user checked the playground (AC-8).

## Deviations from the spec
- 21 lessons, not 22 (spec §1, Assumption 10, AC-2 miscounted).
- AC-5's grep also excludes `docs/specs` and `docs/archive`, whose text keeps old paths by Assumption 7; their link targets were checked separately (testrecord R7).

## Follow-ups
None. Next in A3: 070-27 (scaffolding, adds the `curriculum.toml` entry).

## Lead (fallback) units
None.
