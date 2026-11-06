# Skills (source)

Each folder here is one skill in the [Agent Skills](https://agentskills.io) format: `<name>/SKILL.md` with frontmatter `name` and `description`, plus optional files. This folder is the only source (spec [090-10](/docs/specs/090_10_portable_skills.md)).

| Tool | Reads | Kept by |
|---|---|---|
| Antigravity | `.agent/skills/` (this folder) | — |
| Claude Code | `.claude/skills/` | `sync_skills.py` (generated copies) |
| Codex | `.agents/skills/` | `sync_skills.py` (generated copies) |

## Rules
- Frontmatter: only `name` (lower-case letters, digits and `-`, at most 64 characters, the folder name) and `description` (at most 1024 characters: what the skill does and when to use it). Tool-specific keys are refused: every tool must read the same skill.
- The body is a short guide that points to the rules in `.agent/rules/`, `.agent/workflows/` and the scripts; it does not copy them. A body above 4 KiB is a warning.
- Never edit `.claude/skills/` or `.agents/skills/`: they are generated, and a copy that differs from its source fails the docs gate.

## New or changed skill
1. Edit or add `.agent/skills/<name>/SKILL.md`.
2. `py -3 .agent/scripts/sync_skills.py` writes the copies (and removes copies whose source is gone).
3. `py -3 .agent/scripts/lint_docs.py` exits 0 (it runs `sync_skills.py --check`).
4. Commit the source and the copies together.
