---
trigger: model_decision
description: When generating diagrams from the Tracer, showing diagrams or trace output in a web page, or drawing a diagram in docs/
---

# Agent Rule: Diagram Readability

A renderer scales a diagram down to its container's width, so a wide diagram ends up with unreadable text. atugcc meets diagrams in three places, and each gets its own guard:

| Where | Size known in advance? | Guard |
|---|---|---|
| Diagrams the Tracer generates at run time (PlantUML, Mermaid, D2) | No, it depends on the user's code | **Generator budget** (§2) |
| Any web page that shows them (the planned playground, published reports) | No | **Viewer policy** (§3) |
| Hand-written diagrams in `docs/` | Yes | **Docs limit** (§4) |

## 1. Keep every fact
Splitting or merging never loses information.
- Every recorded event appears in exactly one part, or is merged into one mark that shows its count (`×N`).
- **Sequence messages keep their order.** Only *consecutive* identical messages (same from, to, action) merge into one arrow labelled `action ×N`; a repeat after another message is drawn again.
- **State transitions**: identical edges (same old, new, trigger) merge into one edge labelled `trigger ×N`.
- **Structure trees**: a relation recorded twice is one edge (structure has no time), so duplicates are dropped without a count.
- A fact that leaves a picture (for example a participant list) goes into a table or text right under it.

## 2. Generator budget (Tracer output)
Defaults; a caller may change them.

| Diagram | Budget per part | When exceeded |
|---|---|---|
| Sequence | ≤ 5 participants, ≤ 15 messages | Split in time order: a part takes messages while it stays within both limits; the next part starts at the next message |
| State | ≤ 12 states | Emit one diagram and a note that it is over budget (the viewer scrolls); no split, because a cut state machine misleads |
| Structure tree | ≤ 12 nodes | Split by the root's direct subtrees, recursively; a node whose children alone exceed the budget stays in one part marked over budget |

- **Labels** wrap at 24 characters with the backend's line break (Mermaid `<br/>`, PlantUML `\n`, D2 `\n`).
- **Part titles**: `Sequence (2/3)`, and the same `(k/n)` on every split kind, so a reader knows a part is not the whole.
- **Structured output**: generators return the parts as data (title, backend, source); string output joins them. A web viewer renders each part as its own block.
- A budget change or a new backend comes with tests that check §1 and §2 on every backend.

## 3. Viewer policy (web pages)
- **Do not shrink below 80 % of the natural size.** A wider diagram scrolls horizontally inside its own container (`overflow-x: auto`); the page itself never scrolls sideways.
- Mermaid: `useMaxWidth: false` for sequence, state, class and flowchart diagrams, then apply the 80 % floor with CSS.
- Diagram text renders at 14 px or more at 100 %.
- Terminal and ASCII-tree output: monospace, `white-space: pre`, no wrapping, horizontal scroll, ANSI colours converted to the page's colour tokens.
- Every diagram has an "open full size" view.
- At phone width the same rules hold: scroll, never shrink below the floor.

## 4. Docs limit (hand-written diagrams in `docs/`)
- Natural size at most **1000 px wide and 1400 px high**; aim for 800 px. A docs column and an A4 page are about 700 px wide, so 1000 px keeps text at 70 % or more and the diagram on one page.
- **Flowcharts**: `TD` by default, about 10 nodes, 4 per row. A list of similar things becomes one node plus a table under the diagram.
- **Sequence diagrams**: at most 5 participants, short messages wrapped with `<br/>`; one diagram per phase when a flow is long. Narrow participant boxes with a frontmatter block when needed:
  ```text
  ---
  config:
    sequence:
      width: 110
      actorMargin: 30
  ---
  sequenceDiagram
  ```
- **One concern per diagram**; a split diagram keeps a `Source:` line under each part.
- Measuring: `docs/` has no Mermaid block yet. With the first one, port the ai_sec measuring script (headless Chrome, recorded sizes checked by the docs lint), KI-006.

## 5. Backend pitfalls
- Mermaid: `;` ends a statement inside a sequence message; escape it as `#59;`. Identifiers with spaces or symbols are quoted (`mermaid_id`).
- A syntax error renders as a wide error picture: a generator change is tested by rendering, not only by string comparison, before the playground ships it.
