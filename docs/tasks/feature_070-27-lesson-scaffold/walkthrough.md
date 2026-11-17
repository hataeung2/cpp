# Walkthrough 070-27: 레슨·유닛 뼈대 생성

## Result
- `py -3 tools/lessons.py new <track> <id> [--after <id> | --before <id>] [--title …] [--tags …] [--uses …]` makes `lesson.toml`, `README.md`, `README.en.md`, `main.cpp` and `exercises.toml` (one observation exercise) from `tools/lesson_templates/lesson/`, and puts the id into `lessons/curriculum.toml` at the end of the track or at the given place, editing the text so comments and line endings stay. The new lesson builds at once, `lesson.<id>` and `lesson.<id>.exercises_verify` pass on both hosts, and `check` has 0 errors.
- `py -3 tools/lessons.py new-unit <id>` makes `unit.toml`, `<id>.hpp`, `README.md` and `README.en.md`.
- Every condition (spec §2.2, plus the ones the review added: both `--after` and `--before`, one id per line in the array, `*/` or non-UTF-8 text, an id listed without a folder) is checked before writing; a failing write removes the new folder and puts the curriculum's bytes back.
- `check` gives one WARN per file that still has `[scaffold]` (manifest, both READMEs, sources or unit files, `exercises.toml`). The real repository has none.
- `--root` and `--out` still work before the command name (`--out - index`).
- Docs: [lessons/README.md](/lessons/README.md) "새 레슨 추가" (the command first; copying stays for GoogleTest and module lessons) and a "새 유닛" paragraph, the `curriculum.toml` header, the Quick reference in [agent_start_prompt.md](/docs/agent_start_prompt.md).

Evidence: [testrecord.md](testrecord.md).

## Follow-ups
None. A rejected `check --out X` (formerly ignored) has no caller in the repository. The Linux `PlaygroundServer` test pins the real unit list, so a probe unit in the tree makes it fail; that is the test's intent (testrecord R5).

## Fallback units
None.
