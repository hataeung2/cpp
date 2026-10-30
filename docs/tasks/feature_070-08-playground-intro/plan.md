# Plan: 070-08 플레이그라운드 소개 페이지

- Spec: [/docs/specs/070_08_playground_intro.md](/docs/specs/070_08_playground_intro.md) (approved 2026-10-29)
- Branch: `feature/070-08-playground-intro` (from `main` at `1fd15b6`), carrying the uncommitted root README `## Workflow` section (spec Assumption 6)

## Design
The user will rewrite the intro to taste after this task, so the text and the code are kept apart and the code stays small:
- **Text is data.** Everything the reader sees is in `lessons/intro.md`. Changing it needs no frontend build, no server change and no index change; it can be edited in VS Code or in the page itself (it is under `lessons/`).
- **One place in code.** `INTRO_PATH` and `showIntro()` in `main.ts`, plus one button in `index.html`. Moving the file or adding more guide pages later changes this constant or turns it into a list; nothing else depends on it.
- **No new schema.** The intro is not a lesson: `tools/lessons.py`, `/api/lessons` and the tree stay as they are, so 070-03/070-04 curriculum work does not have to carry an intro field.
- **Few links that can break.** The intro links stable entry points (root README, `lessons/README.md`, three library headers) and one lesson README per track, all from the repository root (`/…`), so moving the intro keeps them. Lesson folders may be renamed in 070-03/070-04; checking `lessons/` links automatically is KI-019.
- First load: when the hash selects no lesson (no hash, unknown id, or the index request failed), the README panel shows the intro. ↻ never replaces the panel.

## Units
| # | Unit | Files | Risky | Author | Reviewer | State |
|---|---|---|---|---|---|---|
| U1 | intro text | `lessons/intro.md` [NEW] | no | lead | `cpp-reviewer` | done |
| U2 | intro button, first-load intro | `web/frontend/index.html`, `web/frontend/src/main.ts`, `readme.ts`, `theme.css` [MODIFY] | no | lead | `cpp-reviewer` | done |
| U3 | docs | `README.md`, `web/README.md`, `lessons/README.md` [MODIFY] | no | lead | `cpp-reviewer` | done |

Check per unit: `git diff --stat` shows only the unit's files; U1 link check (every relative link resolves to a file); U2 `npm run build` and `npm test`; U3 `lint_docs.py` exit 0.

## Changes after review
`cpp-reviewer`, one round, 7 findings; all taken:
- `main.ts`: `introDecided` set on the first call, not on the first successful index load. Before, a ↻ that failed again after a failed first load replaced the panel.
- `readme.ts`: a failed read that arrives after another document was asked for is dropped, like a successful one (spec §4 Resource lifetime).
- `readme.ts`, `theme.css`: the path above a README or the intro opens that file in the editor. Spec Assumption 1 promised in-page editing of the intro, but no tab could open it (`.md` links go to the panel, README files are left out of lesson tabs).
- `README.md` Workflow step 2: `uses` syntax is `unit:<unit>` / `lib:atugcc/...`; the quoted paths are the `#include` form.
- `intro.md`, `README.md`: the long profile's `linux-x64-playground-release` preset is named.
- `intro.md`: links from the repository root.
- Unchecked links under `lessons/`: KI-019 (one-line `lint_docs.py` change, outside this spec).
