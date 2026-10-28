# Plan: 020-04 다이어그램 가독성

- Spec: [/docs/specs/020_04_diagram_readability.md](/docs/specs/020_04_diagram_readability.md) (approved 2026-10-28)
- Rule: [/.agent/rules/diagrams.md](/.agent/rules/diagrams.md)
- Branch: `feature/020-04-diagram-readability` (from `main` after 090-02)

## Design (fixed by the lead; units implement exactly this)

### D1. `include/atugcc/pattern/detail/diagram_split.hpp` (new, backend-independent)
Namespace `atugcc::pattern::viz::detail`. Included by `visualizer.hpp` after the event types are defined. All functions `inline`; indices refer to the snapshot vectors the caller owns (no pointers, no views kept).
```cpp
struct MessageRun { std::size_t index; std::size_t count; };  // messages[index] repeated `count` times in a row
struct EdgeRun    { std::size_t index; std::size_t count; };  // first transitions[index] of an identical (old,new,trigger) group
struct StructurePart { std::vector<std::size_t> relations; bool overBudget; }; // indices into nodes

[[nodiscard]] inline std::size_t clampBudget(std::size_t value) noexcept;   // 0 -> 1
[[nodiscard]] inline std::vector<MessageRun> mergeConsecutiveMessages(const std::vector<Message>& messages);
// Arrows (runs) in time order; a new part starts when adding the next run would exceed
// maxParticipants distinct names (from/to) or maxMessages runs. Budgets are clamped first.
[[nodiscard]] inline std::vector<std::vector<MessageRun>> splitSequence(
    const std::vector<Message>& messages, const std::vector<MessageRun>& runs,
    std::size_t maxParticipants, std::size_t maxMessages);
// Identical (old_state,new_state,trigger) merged; order of first occurrence.
[[nodiscard]] inline std::vector<EdgeRun> mergeTransitions(const std::vector<Transition>& transitions);
[[nodiscard]] inline std::size_t countStates(const std::vector<Transition>& transitions, const std::vector<EdgeRun>& edges);
// Index of the first occurrence of each distinct (parent,child,relation_type), in order.
[[nodiscard]] inline std::vector<std::size_t> uniqueRelations(const std::vector<Node>& nodes);
// Every relation in exactly one part. All distinct node names <= maxNodes -> one part.
// Otherwise per root (a parent that is never a child, in first-seen order; if none, one part
// with everything): pack(root) = whole subtree if its node count <= maxNodes; else a "star"
// part with root->children relations (overBudget when 1 + children > maxNodes), into which
// whole child subtrees are added greedily while the part stays <= maxNodes nodes; every child
// subtree not added is packed recursively. Cycles: a node already visited is not entered again.
[[nodiscard]] inline std::vector<StructurePart> splitStructure(
    const std::vector<Node>& nodes, const std::vector<std::size_t>& relations, std::size_t maxNodes);
// Word-boundary wrap at `width` characters (bytes); a word longer than width is cut at width.
// Lines are joined with `lineBreak`. Text not longer than width is returned unchanged.
[[nodiscard]] inline std::string wrapLabel(std::string_view label, std::size_t width, std::string_view lineBreak);
[[nodiscard]] inline std::string withCount(std::string label, std::size_t count);   // count > 1 -> label + " ×" + count
[[nodiscard]] inline std::string partTitle(std::string_view kind, std::size_t k, std::size_t n); // n == 1 -> kind, else "kind (k/n)"
```

### D2. Formatters (`plantuml_formatter.hpp`, `mermaid_formatter.hpp`, `d2_formatter.hpp`)
Each formatter class gets three part functions; header/footer lines and edge line formats stay exactly as today, so an unsplit trace without repeats renders the same text as before (AC-7).
```cpp
static std::string sequencePart(const std::vector<Message>&, const std::vector<MessageRun>&, std::size_t labelWrap);
static std::string statePart(const std::vector<Transition>&, const std::vector<EdgeRun>&, std::size_t labelWrap, std::string_view overBudgetNote);
static std::string structurePart(const std::vector<Node>&, const std::vector<std::size_t>& relations, std::size_t labelWrap, std::string_view overBudgetNote);
```
- Label = `withCount(wrapLabel(label, labelWrap, LB), count)`; LB = `\n` (PlantUML, D2), `<br/>` (Mermaid).
- Mermaid labels: `;` -> `#59;` before wrapping.
- `overBudgetNote` non-empty -> one comment line as the first line of the diagram body: `' <note>` (PlantUML, after `@startuml`), `%% <note>` (Mermaid, after the diagram keyword line), `# <note>` (D2, after the section header line).
- The old whole-trace functions (`sequenceDiagram`, `stateDiagram`, `classTree`, `messageFlow`, `stateFlow`, `structureTree`) are removed once nothing calls them (U5); D2's `std::set`-based dedup goes with them.

### D3. Tracer (`visualizer.hpp` declarations; definitions in new `detail/diagram_parts.hpp`)
```cpp
struct DiagramBudget { std::size_t maxParticipants = 5, maxMessages = 15, maxStates = 12, maxNodes = 12, labelWrap = 24; };
enum class DiagramKind { Sequence, State, Structure };
struct DiagramPart { DiagramKind kind; DiagramBackend backend; std::string title; std::string source; bool overBudget; };
[[nodiscard]] std::vector<DiagramPart> diagramParts(DiagramBackend backend = DiagramBackend::PlantUML, const DiagramBudget& budget = {}) const;
[[nodiscard]] std::string formatDiagram(DiagramBackend backend = DiagramBackend::PlantUML, const DiagramBudget& budget = {}) const;
// formatPlantuml() / formatMermaid() / formatD2() stay as wrappers: formatDiagram(<backend>)
```
- `diagramParts`: copy the three deques under `shared_lock` (as today), then build parts outside the lock in the order Sequence, State, Structure.
- State: one part, `overBudget = countStates > maxStates`, note `over budget: states <count> > <limit>`. Structure part that cannot meet the budget: note `over budget: nodes <distinct names in the part> > <limit>` (changed from "children" in the U5 prompt so one wording covers the star and the fallback parts; codex final review flagged the old text here).
- `formatDiagram`: for each kind, if that kind has more than one part, write a title comment line (`' `, `%% `, `# `) before each of its parts; then the part source; then `\n` (as today). **Interpretation**: the spec's "조각이 2개 이상일 때" is read per kind, so an unsplit trace that has both messages and transitions keeps today's output (AC-7).
- The current definitions of `formatPlantuml/Mermaid/D2/Diagram` move from `plantuml_formatter.hpp` to `diagram_parts.hpp`.

## Units
All code units touch the public pattern API or several files that must change together → `Risky: yes` (delegation.md §3): author agy (`flash`, chain §6.1), first-pass review codex `luna`, then the lead's check.

| Unit | Files | Change | Check | Risky | Author | Reviewer | Tokens | Status |
|---|---|---|---|---|---|---|---|---|
| U1 | `detail/diagram_split.hpp` (new) | D1 | stand-in-types TU with GCC `-Werror` + smoke run; then real build after U2 | yes | agy flash (2 attempts: `wrapLabel` padded, fixed via `--resume`; width-0 clamp added in U6 rework) | codex luna: 3 findings (out-of-range skip, `overBudget` on fallback parts, `wrapLabel` loop) → fixed | 108k / 41k + rework | done |
| U2 | `visualizer.hpp`, `detail/plantuml_formatter.hpp` (signature only) | D3 types + declarations; include `diagram_split.hpp` (`diagram_parts.hpp` include moves to U5, where the file is created) | both presets build and pass | yes | agy flash | codex luna: none (extras were requested) | 244k / 20k | done |
| U3+U4 | `detail/plantuml_formatter.hpp`, `detail/mermaid_formatter.hpp`, `detail/d2_formatter.hpp` | D2 part functions (keep old ones); one call because all three implement the same interface | both presets build | yes | agy flash | codex luna: only the intended behaviour changes | 190k / 26k | done |
| U5 | `detail/diagram_parts.hpp` (new), `detail/plantuml_formatter.hpp`, `visualizer.hpp` include | D3 definitions; move Tracer::format* here; remove PlantUML's old functions | Mermaid/D2 files untouched (`cmp`); existing suite passes unchanged | yes | agy flash | codex luna (full diff, after U5b): wording only | 167k / 33k | done |
| U5b | `detail/mermaid_formatter.hpp`, `detail/d2_formatter.hpp` | remove the old whole-trace functions (unused after U5), unused includes, D2 header comment | build, suite, `naming_check` | yes | lead (scripted) | codex luna (full diff) | — | done |
| U5c | `detail/diagram_split.hpp`, `detail/diagram_parts.hpp` | 7 named lambdas → camelCase (naming gate) | `naming_check` = 0 | no | lead (scripted, `naming_check --apply`) | codex luna (full diff) | — | done |
| U6 | `tests/pattern/test_diagram_split.cpp` (new), `tests/CMakeLists.txt` | tests for AC-1–AC-10, all three backends | suite passes; Tester reads each test against its AC; `cpp-reviewer` on the tests | no (test) | agy flash (2 attempts) + lead [Tester] golden AC-7 and AC-5 node count | `cpp-reviewer` | 131k / 31k + 386k / 55k | done |
| U7 | `visualizer.hpp` header comment, `src/pattern/example_visualizer.cpp` (Demo 4), `docs/cpp_evolution/designated_initializers.md`, spec 08 History, KI-005 | docs and one example | lint, build, Demo 4 run | no | lead | covered by the final gates (docs only) | — | done |
