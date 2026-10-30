# Walkthrough: 070-08 플레이그라운드 소개 페이지

- Spec: [/docs/specs/070_08_playground_intro.md](/docs/specs/070_08_playground_intro.md)
- Evidence: [testrecord.md](/docs/tasks/feature_070-08-playground-intro/testrecord.md) (AC-1–AC-6 all Pass)
- Branch: `feature/070-08-playground-intro`, merged into `main` by fast-forward

## Result
- [`lessons/intro.md`](/lessons/intro.md): what the page is, library (`include/` + `src/`, reusable core) vs lessons (applying it, plus the C++ syntax underneath), what can be done here (read, change and Run, see Events/Diagrams/Timings), track order, what cannot be done here, where to read about writing lessons.
- Top bar **ⓘ 소개** shows it in the README panel without touching the lesson, the tabs or a run; the page opens on it when the URL hash selects no lesson.
- The path above any README (and the intro) opens that Markdown file in the editor, so the intro and lesson READMEs can be edited in the page.
- Root [`README.md`](/README.md) has a `## Workflow` section: where code goes (library, lesson, scratch), adding a lesson, how a lesson reaches the playground.

## For later edits
- The text is only `lessons/intro.md`: edit it in VS Code or in the page; no frontend build, no index or server change.
- The code is `INTRO_PATH` and `showIntro()` in [`main.ts`](/web/frontend/src/main.ts) plus one button in [`index.html`](/web/frontend/index.html).
- Links are written from the repository root (`/lessons/...`). Renaming a lesson folder means fixing the intro's two lesson links by hand until KI-019.

## Follow-ups
- KI-019 (new): links in `lessons/**/*.md` are not checked; one-line `lint_docs.py` change proposed.
- KI-020 (new): `test_span_flood_keeps_memory_flat` failed once while the host was busy; passed alone twice.
