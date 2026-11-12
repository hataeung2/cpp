# Walkthrough: 070-07 단계별 다이어그램 재생

- Spec: [/docs/specs/070_07_diagram_replay.md](/docs/specs/070_07_diagram_replay.md); plan: [plan.md](plan.md); evidence: [testrecord.md](testrecord.md)
- Branch: `feature/070-07-diagram-replay`

## Result
After a run, the Diagrams tab can replay one tracer event by event. The diagram of each step is drawn by the same C++ generator as the final one:
- `viz::diagramPartsOf(messages, transitions, nodes, backend, budget, range)` and `DiagramRange{untilSeq, markLast}`; `Tracer::diagramParts(backend, budget, range)` takes a snapshot and calls it. The old two-argument calls are unchanged. `viz::toJsonLines` now writes the `diagram` lines for both the destructor and the tool, so they are the same code.
- Mermaid marks the last event of the range: a `rect` around the message, `classDef current` on the arrival state, `style <child>` on the child of the last relation.
- Tool `atugcc_diagram_replay` (`tools/diagram_replay/`, built with every lesson): reads 020-05 JSON Lines on stdin, writes the `diagram` lines. A small own JSON reader, tested by round trip.
- Server: keeps up to 5,000 events per tracer, `done.replay`, `GET /api/runs/<id>/diagrams?tracer=&until=`; the build adds the tool as a second target.
- Page: a replay bar (switch, tracer choice, ⏮ ◀ ▶ ⏭, slider, `k / n`, the event), ←/→ in the panel, folded earlier Sequence parts, a cache by `(tracer, seq)`; each step selects the Events row and highlights the editor line; an Events row click moves the replay. `EditorArea.open(..., focus=false)` keeps the keyboard on the diagram.

## Differences from the spec (recorded in the spec's History)
- Structure highlight: `linkStyle` does not work in Mermaid 12.2.0 classDiagram (the parser reads it as a class), so the child of the last relation is styled instead. A name needing quotes gets no highlight in State and Structure.

## Follow-ups
- KI-051: the Exercises panel (`.exercises { display: flex }`, 070-17) is always visible above the active panel. Not fixed here.

## Process notes
- agy `flash` wrote U1, U3–U5, U7–U10, U12–U14 and was reviewed by codex `luna` (U1–U5) or `cpp-reviewer`. The agy service returned 403 ("account disabled") during U14; the finished part was kept after a check. **U15 and U16 (frontend), U2, U6, U11, the review-fix rounds and the docs were written by the lead (`lead (fallback)` for U15/U16)**, reviewed by `cpp-reviewer` (U12–U16).
- Every Clang-only error (`-Werror`) was found by the Linux run, not by MSVC.
