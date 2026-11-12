# Test record: 070-19 panel wrap and layout

- Spec: [/docs/specs/070_19_panel_wrap_layout.md](/docs/specs/070_19_panel_wrap_layout.md)
- Plan: [plan.md](plan.md)
- Host: Windows 11; the page is served by `tools/playground.py --port 18790 --no-frontend-build` (the server runs in WSL2 Ubuntu 24.04, Clang 20). No C++ changed, so no MSVC build was needed.
- Browser checks: Node scripts outside the repository (scratch folder) drive the installed Edge headless through `playwright-core` 1.55.0. `ac1.mjs` (AC-1), `ac2.mjs` (AC-2 to AC-6), `sweep.mjs` (Timings widths), `dpr.mjs` (display scaling). They save no lesson file; lessons are only run. Screenshots: [screenshots/](screenshots/).

## Runs
| # | What | Expected | Result | Verdict |
|---|---|---|---|---|
| R1 | `npm --prefix web/frontend test` (final) | all pass | 13 files, 164 tests | Pass |
| R2 | `npm --prefix web/frontend run build` (`tsc --noEmit` + `vite build`) | no error, no warning | built; no `warn`/`error` line | Pass |
| R3 | `build.py --preset linux-x64-debug --label probe --report` (WSL) | `PlaygroundServer` and the other probes pass | 12/12, `PlaygroundServer` 147.6 s (report `out/test-reports/linux-x64-debug/20261112-143244/`, local) | Pass |
| R4 | `ac1.mjs`, 4 lessons × (1280×800, 1024×768) × (default widths, right column dragged to 280 px) | `scrollWidth ≤ clientWidth` for README, 연습, Output, Diagrams, Events, Timings, tab bar, panel tab row, page; no Monaco line past the editor's right edge | 160 measurements, 0 over (final run after the last code change) | Pass |
| R5 | `sweep.mjs`: Timings of `span_timing` with the right column at 280, 320, 400, 480, 540, 600, 700, 760, 800, 900, 1000 px of a 1600 px window | no overflow | first design (hide p50/min/max below 520 px) overflowed at 760–800 px and at 280 px (554 px wide); after the two tiers (840 px / 600 px) 0 over | Fail → fixed → Pass |
| R6 | `ac2.mjs` (AC-2 to AC-6, below) | all pass | ALL PASS (final run) | Pass |
| R7 | `dpr.mjs`: drag the right bar by 100 px at display scaling 1.25 and 1.5 | width changes by exactly 100 | 538 → 638 at both | Pass |
| R8 | `py -3 .agent/scripts/lint_docs.py` | exit 0 | 0 error(s), 0 warning(s) (after archiving) | Pass |

## Acceptance criteria
| ID | Evidence | Result |
|---|---|---|
| AC-1 | R4. Lessons `format_text`, `span_timing`, `testing` (연습 tab present), `device_state_machine`. The diff editor of 070-16 opens in a dialog, not in the panels; its `diffWordWrap` follows the editor choice (code review, no measurement) | Pass |
| AC-2 | `ac2.mjs`: wrap on by default and no text past the editor edge; `↩` off makes lines run past the edge and stores `off`; after a reload the choice stays; Alt+Z turns it on. Wrapped continuation lines are indented: [ac2_editor_wrap_on_1024.png](screenshots/ac2_editor_wrap_on_1024.png). Unit: `layout.test.ts` "wrap choice" (default on, off/on, unknown value, blocked storage) | Pass |
| AC-3 | `ac2.mjs` on `span_timing`: `white-space: pre-wrap` and no sideways scroll by default; off gives `pre` with `scrollWidth` 782 > 537; stored `atugcc.wrap.output=off`. Screenshots [ac3_output_wrap_on.png](screenshots/ac3_output_wrap_on.png), [ac3_output_wrap_off.png](screenshots/ac3_output_wrap_off.png) (the `formatTimings` table) | Pass |
| AC-4 | `layout.test.ts` (`clampLayout`, `moveSidebar`, `moveRight`, `parseLayout` with 9 broken inputs, `loadLayout`/`saveLayout` with blocked storage). `ac2.mjs`: default 260 / 42 %; → twice = +32 px; ← stops at 160; double click resets; right bar to the far right = 280, to the far left = editor 360; 800 px survives a reload; a 1000 px window keeps minimums and the sum; the chosen width returns at 1600 px; blocked `localStorage` gives defaults and the bar still moves; bars hidden at 880 px. R7 for display scaling | Pass |
| AC-5 | `ac2.mjs` while wrapped: Timings line-end decorations exist (4) and a Timings row click highlights a line: [ac5_inline_timing_wrapped.png](screenshots/ac5_inline_timing_wrapped.png), [ac5_timings_jump_wrapped.png](screenshots/ac5_timings_jump_wrapped.png). Diagnostics and the GoogleTest failure marks are Monaco markers on logical lines and were not changed by this task; not re-measured with a failing build | Pass for decorations and jump; markers by design (see Reviews) |
| AC-6 | `ac2.mjs` on `device_state_machine`: panel does not scroll, `.diagram-scroll` is `overflow-x: auto`, no diagram below 80 % of its natural width (680 of 850 px) | Pass |
| AC-7 | R1, R2, R3, R8 | Pass |

## Reviews
| Unit | Reviewer | Question | Findings | Resolution |
|---|---|---|---|---|
| whole diff | `cpp-reviewer` (fresh, Claude family like the lead; no agy call, see plan.md) | matches Assumptions 3–10 and §4? | (1) double press reset is `dblclick` only; (2) blocked storage of `layout.ts` untested; (3) `LAYOUT_KEY` assertion mirrors the constant, `atugcc.wrap.output` not asserted; (4) comment-only `catch` blocks (same style as `practice.ts`) | (1) Enter on a focused bar now resets too (title, README); (2) `loadLayout`/`saveLayout` exported and tested with blocked storage; (3) replaced by a store/read-back test and an Output-key test; (4) kept: storage errors are an expected, documented case, same as `practice.ts` and the spec's "저장소가 막히면 기본값" |

No other-family reviewer: the code is frontend only, not risky (delegation.md §3), and the fresh reviewer is the one the table names for ordinary units. The code units were written by the lead (`lead (small)`), so the review was not cross-family; the browser measurements are the stronger evidence here.

## Deviations
- Spec Assumption 6 changed after R5 (History of the spec): two hide tiers instead of one, thresholds 840 px and 600 px of the table's container width.
- New file `wrap.ts` (not in spec §2.2).
- Enter on a bar resets the width (the keyboard counterpart of the double click).
