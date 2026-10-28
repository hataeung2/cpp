# Walkthrough: 020-04 다이어그램 가독성

- Spec: [/docs/specs/020_04_diagram_readability.md](/docs/specs/020_04_diagram_readability.md) · Plan: [plan.md](./plan.md) · Tests and reviews: [testrecord.md](./testrecord.md)

## Result
- `Tracer::diagramParts(backend, budget)` returns readable parts (title, source, overBudget); `formatDiagram(backend, budget)` joins them, with a title comment only for split kinds. Defaults: 5 participants / 15 messages per sequence part, 12 states, 12 structure nodes, labels wrapped at 24 characters. `DiagramBudget` uses designated initializers (`{.maxMessages = 30}`).
- No fact is dropped: consecutive repeated messages become `label ×N`, identical state edges `trigger ×N`, a repeat after another message is drawn again; every message and relation appears in exactly one part.
- Traces within budget, without repeats and with short labels render byte-identically to before (golden test from a `main` build).
- New example (Demo 4), `docs/cpp_evolution/designated_initializers.md`, KI-005 closed.
- All ten ACs pass on MSVC `/W4 /WX`, GCC `-Werror` and ASan + UBSan.

## How it was built (delegation.md)
Seven units. agy wrote the risky code units (U1–U5) and the tests; the lead fixed the design (plan D1–D3), split the units, ran every per-unit check, removed dead code and renamed agy's snake_case lambdas by script, and added the golden AC-7 test and the AC-5 node-count check. codex reviewed each risky unit and the full diff; `cpp-reviewer` reviewed the tests and the docs.
Machine checks found what reading did not: `wrapLabel` padding (the lead's smoke run), the naming gate catching 7 lambdas, and a review catching a test (AC-8) that could not fail plus a `labelWrap = 0` hang.

## Follow-ups
- KI-010: Mermaid titles outside the fence in string output (web playground decides).
- KI-011: `×` on non-UTF-8 Windows consoles in the example.
