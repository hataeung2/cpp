# Walkthrough: 090-04 문서 게이트가 `lessons/` Markdown 링크도 검사

- Spec: [/docs/specs/090_04_lessons_doc_links.md](/docs/specs/090_04_lessons_doc_links.md)
- Evidence: [testrecord.md](/docs/tasks/feature_090-04-lessons-doc-links/testrecord.md) (AC-1, AC-2 Pass)
- Branch: `feature/090-04-lessons-doc-links`, merged into `main` by fast-forward

## Result
- `lint_docs.py` checks links, machine paths and KI ids in `lessons/` Markdown (`intro.md`, lesson and unit READMEs) like `docs/`. Renaming a lesson folder now fails the docs gate until the links are fixed.

## Follow-ups
- KI-019: closed.
