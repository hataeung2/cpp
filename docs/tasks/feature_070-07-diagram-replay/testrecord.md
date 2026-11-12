# Test record: 070-07 단계별 다이어그램 재생

- Spec: [/docs/specs/070_07_diagram_replay.md](/docs/specs/070_07_diagram_replay.md)
- Plan: [plan.md](plan.md)
- Hosts: Windows 11 (MSVC 14.51, `windows-x64-debug`), WSL2 Ubuntu 24.04 (Clang 20.1.2, `linux-x64-debug`, the web's `linux-x64-playground`). Browser: Chrome through the Claude-in-Chrome extension.
- Test counts below are from the final runs; the Windows and Linux full runs are after the last code change.

## Runs
| # | What | Expected | Result | Verdict |
|---|---|---|---|---|
| R1 | `build.py --preset windows-x64-debug --test --report` (final) | all pass, 0 warnings | 40/40, 0 warnings (report `out/test-reports/windows-x64-debug/20261112-120415/`) | Pass |
| R2 | `build.py --preset linux-x64-debug --test --report` (final; Clang 20 `-Werror`) | all pass | 40/40 incl. `PlaygroundServer` (139 s, the whole `test_server.py` with the fixture) and 3 scenarios (`out/test-reports/linux-x64-debug/20261112-120755/`) | Pass |
| R3 | first Linux runs | — | caught three Clang-only errors that MSVC accepted: `switch (const char esc = …)` unused (`event_reader.hpp`), designated initializers skipping `EventMeta::location` (`test_diagram_range.cpp`, 20 places, now `metaOf(seq)`), and a test-server fixture whose `python -c` string had a literal `\n` (found by the reviewer, fixed, now a payload argument). All fixed as new units | Fixed |
| R4 | `py -3 web/server/test_server.py` on Windows (API tests; run tests skipped) and in WSL with `--fixture` | pass | 99 tests OK on both; WSL ran the 99 incl. `ReplayRunTest` | Pass |
| R5 | `npm --prefix web/frontend run build`-style typecheck (`tsc --noEmit`) and `vitest run` | pass | 11 files, 131 tests (incl. `replay.test.ts`, `diagramsReplay.test.ts`, the marked-diagram parse cases) | Pass |
| R6 | `py -3 .agent/scripts/lint_docs.py` | 0 / 0 | 0 errors, 0 warnings | Pass |
| R7 | AC-1 per lesson: `py -3 tools/diagram_replay/compare_lessons.py` (Windows) and in WSL `--preset linux-x64-debug` | replay to the last seq = the destructor's `diagram` lines | every lesson built: `device_state_machine` "1 tracer, 2 diagram lines equal" on both; `span_timing` has a Tracer without events (no diagrams); the others write no trace | Pass |
| R8 | Mermaid probe (`mermaid.parse` in vitest, then a local probe page rendered in Chrome with the project's pinned `mermaid@12.2.0`) | which highlight syntax works | see "Findings" | Spec text updated |
| R9 | Browser: playground on `linux-x64-playground`, lesson `device_state_machine`, Practice mode | AC-5 | see "AC-5 browser check" | Pass |

## Findings (spec History 2026-11-12)
- `linkStyle` in a classDiagram: `mermaid.parse` accepts it, but the render shows a class named `linkStyle1stroke` (no link styling). Assumption 6's `linkStyle` therefore does not work in Mermaid 12.2.0. Structure uses `style <child> fill:#fff3b0,stroke:#e0a800,color:#000` on the child of the last relation (rendered yellow in Chrome). A quoted name (`"b c"`) cannot be styled or classed (parse error), so State and Structure skip the highlight for it.
- Lesson: a parse test is not a render test; the highlight is judged by the browser render.

## AC evidence
| AC | Evidence | Verdict |
|---|---|---|
| AC-1 | scenario `scenario.DiagramReplay.ReplayMatchesTheTracerDestructor` (two recording threads, a second tracer in the same file, full range equals the destructor's lines, middle range equals `Tracer::diagramParts(…, range)` with a `rect` and no later action, other tracer not mixed in) on both OS; R7 on the real lesson executables on both OS. File order vs seq order inside a Tracer: seq is taken under the same lock that appends, so recording order = seq order; the tool sorts by seq and the equality holds with threads | Pass |
| AC-2 | `DiagramRange.*` (7 range tests: default = `Tracer::diagramParts`, before first event empty, middle, boundary inclusive, end = no range, Tracer overload, sequence chunks stop at the cursor); the old `DiagramSplitTest` and `TracerTest` suites pass unchanged | Pass |
| AC-3 | `DiagramRange.MarkLast*` (13 tests: rect, until-seq, merged run, split chunk, arrival state, quoted state, child style, kind with the largest seq, tie order, PlantUML/D2 ignored, off changes nothing, duplicate relation, quoted child); `mermaidParse.test.ts` marked sources parse; browser render: Sequence rect and State class in the playground (screenshots below), Structure `style` in the probe page | Pass |
| AC-4 | `EventReader.*` (12 tests) and `ReplayArgs.*` (3): round trip of the three kinds through `toJsonLine`, escapes and UTF-8, surrogate pairs, bad lines and `v` ≠ 1 counted, other tracer / span / diagram ignored uncounted, stable sort by seq (equal seq keeps file order; nodes sorted), CRLF | Pass |
| AC-5 | server: `JobReplayTest`, `ReplayApiTest` (statuses 200/400/404/409/500, UTF-8, cap exactly and cap+1, tool failure / timeout / missing, huge digit strings), `ReplayRunTest` (real run through a fake executable: `done.replay.tracers`); page state: `replay.test.ts`, `diagramsReplay.test.ts` (bar, cursor, hooks, ←/→, tracer choice, the rendered reason for >5,000 and for a truncated Events tab, clear); browser below | Pass |
| AC-6 | R1, R2 (suite + scenarios + `PlaygroundServer`), R5, R6; §8 documents updated (below) | Pass |

## AC-5 browser check (R9)
`device_state_machine`, 6 events (3 messages, 2 transitions, 1 message). Screenshots (saved by the Chrome tool, scratch folder, not committed):
- first: step `1 / 6`, `seq 1 · message · Machine → IO : update_io() · state.hpp:125`, a one-message Sequence with the yellow band; editor line 125 highlighted; Events row 1 selected.
- middle: an Events row click (seq 2, a transition) moved the replay to `2 / 6`; State diagram with `STANDBY` yellow; editor line 153. ArrowRight with the panel focused went to `3 / 6` (editor line 128, Events row 3), the keyboard staying in the panel.
- end: `6 / 6`, `run_cycle() ×2` in a yellow band, editor line 131.
- The `> 5,000 events` case in the page is the rendered reason (jsdom test) plus the server cap tests; no 5,000-event lesson exists to run in the browser.
- Not checked in the browser: dark theme of the highlight; a tracer choice with two tracers (jsdom only).
- During the check the Exercises panel showed above every tab: a bug from 070-17, not this task (KI-051). The screenshots hide it by a style tweak in the page console only.

## Reviews
| Unit | Reviewer | Question | Findings | Resolution |
|---|---|---|---|---|
| U1, U2 | codex `luna` (high) | range cut, `toJsonLines` | none | — |
| U3–U5 (+U4 formatter) | codex `luna` (high) | mark selection, Sequence/State/Structure text, tests | two missing tests: tie priority, only the chunk with the message has `rect` | lead added `MarkLastTieGoesToSequenceThenState`, `MarkLastOnlyTheChunkWithTheMessageHasRect` |
| U7–U10 | `cpp-reviewer` | reader rules, tool, tests | minor: dead `i64`/`bval` fields, unused `fileLines`, stability test weak, `parseArgs` untested, plan wording | removed; test strengthened (equal seq in non-alphabetical file order, nodes); 3 `ReplayArgs` tests; plan aligned |
| U12–U16 | `cpp-reviewer` | server, frontend, tests | `writer_code` test could not pass on POSIX (literal `\n`); stale response put into the cache after `clear()`; bar rebuilt on every step (focus/slider drag lost); `replaySources()` dead; no `DiagramsPanel` test; cap boundary and timeout untested; `int()` of 4300+ digits; lone surrogate encode; Alt+arrows | all fixed (payload argument; generation check before `cache.set`; in-place `updateBar`; removed; `diagramsReplay.test.ts`; boundary, timeout, huge-digit tests; length limits; `errors="replace"`; modifier check) |

## Documents (§8)
`visualizer.hpp` head comment, `.agent/rules/diagrams.md` §3, `web/README.md` (API row, `done.replay`, build line, Page, structure), `docs/cpp_evolution/designated_initializers.md` and `.en.md`, `lessons/README.md`, spec History, `docs/agent_todo.md`. Spec 020-05 untouched.

## Not run
- Dark theme and two-tracer selection in the browser; a run with more than 5,000 events through the page.
