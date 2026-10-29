# Walkthrough: 070-02 로컬 웹 플레이그라운드

- Spec: [/docs/specs/070_02_web_playground.md](/docs/specs/070_02_web_playground.md) (approved 2026-10-28)
- Plan: [plan.md](/docs/tasks/feature_070-02-web-playground/plan.md) · Tests: [testrecord.md](/docs/tasks/feature_070-02-web-playground/testrecord.md)
- Branch: `feature/070-02-web-playground`

## Result
`py -3 tools/playground.py --open` (or the VS Code task **Playground: start**) builds the frontend if needed, starts the server in WSL on `127.0.0.1`, and opens a page where the lessons of `lessons/` can be edited, built and run:
- lesson tree (tracks → lessons, units with the lessons that use them), Monaco tabs for the lesson's files (library headers read-only), saves straight into the repository with sha conflict detection and line endings kept;
- Run builds with the new `linux-x64-playground` preset and streams the build log, stdout/stderr (line by line through `stdbuf`), Tracer events (020-05) and, at the end, the Mermaid diagrams; Stop and a closed page kill the run's process group; quick limits 10 s run, 120 s build, 1 MiB output;
- compile errors become editor markers; clicking an event highlights its source line; diagrams follow diagrams.md §3 (never below 80 %, scroll in their box, full-size view); light/dark.

All 12 acceptance criteria have automated evidence (testrecord: unit tests, CTest `PlaygroundServer` on `linux-x64-debug`, `-asan`, `-tsan`, vitest, and browser scenarios with assertions for the screen ACs); 14/14 mutants of the server code are caught by the tests.

## Decisions made while implementing (spec History)
- AC-5/11/12 fixtures are a test program (`tests/playground/playground_fixture.cpp`), not lessons.
- `done` carries a top-level `stopped`; `build.timedOut` added.
- The server checks `Host`, `Origin` and `Content-Type`, so other web sites cannot start runs or write files.
- `DiagramPart::source` is a fenced Markdown block: the page unwraps it before Mermaid.

## Follow-ups
- KI-015: a lesson process that detaches with `setsid()` is not killed with the run (accepted for local use; isolation belongs to 070-05).
- KI-010: owner updated; the web is not affected.
- KI-013, KI-014 (Logger) remain open; the user chose to fix them after the web work.

No `lead (fallback)` units. The browser scenario script (Edge via `playwright-core`) lives outside the repository; `playwright` is not a dependency of the project.
