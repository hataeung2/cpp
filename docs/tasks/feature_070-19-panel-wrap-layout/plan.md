# Plan: 070-19 panel wrap and layout

Spec: [070-19](/docs/specs/070_19_panel_wrap_layout.md). Branch `feature/070-19-panel-wrap-layout`. No C++ change; frontend (Vite + TypeScript + Monaco) and docs only.

## Files
- [NEW] `web/frontend/src/layout.ts`: `clampLayout`, `moveSidebar`, `moveRight`, `parseLayout` (DOM-free) and `ColumnLayout` (drag, ←/→, double click, resize, storage `atugcc.layout`).
- [NEW] `web/frontend/src/wrap.ts`: stored wrap choice (`atugcc.wrap.editor`, `atugcc.wrap.output`), default on, blocked storage safe. Not in spec §2.2; added so the two toggles share one reader.
- [NEW] `web/frontend/test/layout.test.ts`.
- [MODIFY] `index.html` (two bars, `.tabbar` with `↩`, Output panel head with `↩`), `theme.css`, `editor.ts`, `output.ts`, `timings.ts`, `main.ts`, `i18n.ts`, `test/timings.test.ts`.
- [MODIFY] docs of spec §8: `diagrams.md` §3, `web/README.md`, `lessons/README.md`, `agent_todo.md`; spec Assumption 6 amended (measurement, see its History).

C++20/23 features: none (frontend task), no `cpp_evolution` page.

## Unit table
Authoring note: the unit sizes are small (one function to one CSS block each) and the prompts would have been longer than the code, so the lead wrote them (`lead (small)`, delegation.md §1) and the fresh reviewer `cpp-reviewer` read the whole diff once at the end. No agy call was made for code.

| Unit | File | Change (what, where, AC) | Check | Risky | Author | Reviewer | Tokens (in / out) | Status |
|---|---|---|---|---|---|---|---|---|
| U1 | `web/frontend/src/layout.ts`, `test/layout.test.ts` | arithmetic, controller, storage (Assumption 8, AC-4) | `vitest layout`: 24 tests | no | lead (small) | cpp-reviewer (whole diff) | n/a | done |
| U2 | `web/frontend/src/wrap.ts`, `editor.ts`, `index.html` | Monaco `wordWrap`, `wrappingIndent: 'indent'`, `wrappingStrategy: 'advanced'`, `↩`, Alt+Z, diff editor (Assumption 3, 12, AC-2) | `grep -c "wrapOptions" editor.ts` = 3; browser AC-2 | no | lead (small) | cpp-reviewer | n/a | done |
| U3 | `output.ts`, `index.html`, `theme.css` | Output wrap toggle, panel head (Assumption 4, AC-3) | browser AC-3 | no | lead (small) | cpp-reviewer | n/a | done |
| U4 | `theme.css` | README, exercise, Events, tab rows, bars, `.layout` variables (Assumptions 5, 6, 8, 9, 10) | `build`, browser AC-1 | no | lead (small) | cpp-reviewer | n/a | done |
| U5 | `timings.ts`, `theme.css`, `test/timings.test.ts` | hide tiers, detail row (Assumption 6 amended, AC-1) | `vitest timings`, width sweep 280–1000 | no | lead (small) | cpp-reviewer | n/a | done |
| U6 | `main.ts`, `i18n.ts` | wiring, titles in two languages | `build` (`tsc --noEmit`), `i18n.test.ts` | no | lead (small) | cpp-reviewer | n/a | done |
| U7 | `diagrams.md`, `web/README.md`, `lessons/README.md`, `agent_todo.md`, spec | §8 documents | `lint_docs.py` | no | lead | cpp-reviewer (diff) | n/a | done |
