# Test Record: 070-08 플레이그라운드 소개 페이지

- Spec: [/docs/specs/070_08_playground_intro.md](/docs/specs/070_08_playground_intro.md)
- Plan: [plan.md](/docs/tasks/feature_070-08-playground-intro/plan.md)
- Date: 2026-10-29
- Hosts: Windows 11 (Python 3.15, Node 24.19, Edge) with the playground server in WSL; WSL Ubuntu 24.04 (GCC 13.3) for the Linux suite

Browser checks: a Node script outside the repository drives the installed Edge (`playwright-core`, headless) against a playground started with `py -3 tools/playground.py --port 18780`. It asserts on the DOM and takes the screenshots in [`screenshots/`](/docs/tasks/feature_070-08-playground-intro/screenshots/). It saves no file. The link check is a scratch Python script that resolves each Markdown link of `lessons/intro.md` the way `ReadmePanel` does and requires an existing file.

## Runs

| # | Command | Expected | Actual | Status |
|---|---|---|---|---|
| R1 | `npm --prefix web/frontend run build` (`tsc --noEmit` + Vite), `npm --prefix web/frontend test` | pass | built; 5 files, 37 tests passed | Pass |
| R2 | `py -3 .agent/scripts/build.py --preset linux-x64-debug --test` (before review fixes) | 8/8 | 7/8: `PlaygroundServer` failed `test_span_flood_keeps_memory_flat` (longest pause 1.01 s > 0.5 s) while the host also ran Vite, Edge and a second playground | Fail → R3 |
| R3 | `ctest --preset linux-x64-debug -R PlaygroundServer` (WSL), twice, nothing else running | pass | 52 tests OK both times; AC-7 pauses 0.23 s, 0.21 s. No server code changed in 070-08; recorded as KI-020 | Pass |
| R4 | link check on `lessons/intro.md` | 0 broken | 7 links, 0 broken (3 `include/` headers → editor, 4 `.md` → panel) | Pass |
| R5 | `py -3 tools/lessons.py check`, `lint_docs.py`, `naming_check.py` | exit 0 | 0 errors, 0 warnings (2 tracks, 4 lessons, 2 units); 0 errors, 0 warnings; 0 | Pass |
| R6 | browser script, first version | pass | 10 checks passed | Pass |
| R7 | review fixes, then R1 and R4 again | pass | built; 37 tests passed; 7 links, 0 broken (now `/`-rooted) | Pass |
| R8 | browser script with the review checks (path click opens a writable editor tab; `/api/lessons` forced to 500: first load shows the intro, a failing ↻ keeps the page the user opened) | pass | 14 checks passed | Pass |
| R9 | mutation check (`main.ts` copied to scratch, one change, build, browser script, copy back, `cmp` identical) | each killed | **2/2**: M1 `firstLoad = index === null \|\| !introDecided` (the pre-review rule) → only "failing ↻ keeps the page the user opened" fails; M2 without `else if (firstLoad) showIntro()` → the first AC-2 check times out | Pass |
| R10 | after restoring: build, browser script | pass | 14 checks passed | Pass |

## Acceptance Criteria

| AC | Evidence | Status |
|---|---|---|
| AC-1 | R4 (all links resolve); R8 renders the six sections 여기는 · 두 층: 라이브러리와 레슨 · 여기서 하는 일 · 순서 · 여기서 안 되는 것 · 레슨 만들기; content reviewed by `cpp-reviewer` against the code (claims checked, 3 corrected) | Pass |
| AC-2 | R8: no hash → `lessons/intro.md` in the active README panel, lesson title `레슨을 고르세요` ([ac2-intro-first.png](/docs/tasks/feature_070-08-playground-intro/screenshots/ac2-intro-first.png)); `#no_such_lesson` → intro; `#span_timing` → that lesson's README ([ac2-hash-lesson.png](/docs/tasks/feature_070-08-playground-intro/screenshots/ac2-hash-lesson.png)); M2 fails it | Pass |
| AC-3 | R8: on `#span_timing` with the Output tab open, ⓘ 소개 → README tab with the intro; lesson title, editor tabs (`main.cpp`, `visualizer.hpp`), hash and Run state identical before and after ([ac3-intro-button.png](/docs/tasks/feature_070-08-playground-intro/screenshots/ac3-intro-button.png)); ↻ afterwards keeps the intro | Pass |
| AC-4 | R8: `lessons/README.md` link → panel; `logger.hpp` link → active editor tab `🔒 logger.hpp` (`include/atugcc/core/logger.hpp`). The intro has no external link (0 `target=_blank`); that rule is `ReadmePanel.wire`'s, unchanged | Pass |
| AC-5 | R1, R7 (frontend build and tests); R3 (`PlaygroundServer` 52 OK; R2's one failure is KI-020, not this change); R5 (`lessons.py check`) | Pass |
| AC-6 | §8 documents updated (root README Workflow, Web Playground bullet and preset row; `web/README.md` Page; `lessons/README.md` structure and page section); R5 `lint_docs.py` exit 0 | Pass |

Also checked (spec §4): 420 px wide in dark theme, no horizontal page overflow ([narrow-dark.png](/docs/tasks/feature_070-08-playground-intro/screenshots/narrow-dark.png)); spec Assumption 1 in-page editing, the path above the intro opens `intro.md` in a writable tab ([a1-intro-editor.png](/docs/tasks/feature_070-08-playground-intro/screenshots/a1-intro-editor.png)).

## Revision 1 — 2026-10-29
Review (`cpp-reviewer`, one round) found 7 points, all taken (plan "Changes after review"): ↻ after a failed first load, late failed README reads, in-page editing that the spec promised but the page could not do, wrong `uses` syntax in the README Workflow, the missing release preset, relative links, unchecked `lessons/` links (KI-019). R7–R10 ran after the fixes.

## Reviews
| Unit | Reviewer | Result |
|---|---|---|
| U1–U3 | `cpp-reviewer` | 7 findings, all fixed or registered (KI-019). Not checked by the reviewer: browser behaviour and test runs (done here, R1–R10) |
