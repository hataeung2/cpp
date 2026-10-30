# Plan: 090-04 문서 게이트가 `lessons/` Markdown 링크도 검사

- Spec: [/docs/specs/090_04_lessons_doc_links.md](/docs/specs/090_04_lessons_doc_links.md) (approved 2026-10-29)
- Branch: `feature/090-04-lessons-doc-links` (from `main` at `9262d5e`)

## Design
`DOC_DIRS` gains `"lessons"`; `checked_files()` then hands every `.md`/`.json` under `lessons/` to the existing `check_file()` (broken links, machine paths, KI ids). A dry run with the change found nothing to fix in the 8 Markdown files there.

## Units
| # | Unit | Files | Risky | Author | Reviewer | State |
|---|---|---|---|---|---|---|
| U1 | `lessons` in `DOC_DIRS` | `.agent/scripts/lint_docs.py` | no | lead | lead (one-line change; the mutant check is the review) | done |
| U2 | test | `.agent/scripts/test_agent_scripts.py` | no | lead | lead | done |
| U3 | docs | `.agent/rules/test.md`, `lessons/README.md`, `docs/known_issues.md` | no | lead | lead | done |
