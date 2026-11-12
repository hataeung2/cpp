# Walkthrough: 070-19 panel wrap and layout

Spec: [070-19](/docs/specs/070_19_panel_wrap_layout.md). Evidence: [testrecord.md](testrecord.md).

## Result
- The three columns are resizable: bars between sidebar | editor | right panel (mouse, touch, ←/→ 16 px, double click or Enter to reset), minimum widths 160 / 360 / 280 px, stored in `atugcc.layout`, re-fitted when the window changes ([`layout.ts`](/web/frontend/src/layout.ts), arithmetic tested without a DOM).
- The editor wraps lines (`wordWrap`, `wrappingIndent: 'indent'`, `wrappingStrategy: 'advanced'`); `↩` and Alt+Z toggle it. Output wraps by default (`pre-wrap`) and has its own `↩` for the aligned `pre` view. README, exercise, Events and Timings panels wrap text and tables; the tab rows wrap.
- At 1280×800 and 1024×768, also with the right column at its 280 px minimum, none of the right panels or the editor scrolls sideways in four lessons (160 measurements, 0 over). Diagrams keep their 80 % floor and scroll inside their cards.
- Timings hides p50/min/max (below 840 px), then file:line, meter and the comparison (below 600 px) and shows them in the row's ▸ detail.

## Changes to the spec while building
- Assumption 6: the first design (hide three columns below 520 px) still overflowed (554 px at a 280 px panel), so there are two tiers, found by measuring widths from 280 to 1000 px.
- `wrap.ts` added; Enter resets a bar.

## Follow-ups
None registered. Not done by design: the Monaco diff editor opens in a dialog, so its wrap follows the choice at open time only; a lesson README with a very wide code block now wraps instead of scrolling (as the spec says).

## Units written by the lead
All code units are `lead (small)` (plan.md); no `lead (fallback)`.
