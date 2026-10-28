# Test Record: 020-04 다이어그램 가독성

## Acceptance Criteria Evidence
Tests in [`tests/pattern/test_diagram_split.cpp`](/tests/pattern/test_diagram_split.cpp); every AC is checked on PlantUML, Mermaid and D2 where the spec says "세 백엔드".

| AC | Evidence | Result |
|---|---|---|
| AC-1 | `AC1_SequenceBudgetSplitsByMessages`: 40 messages → 3 parts (15/15/10), titles `(1/3)`–`(3/3)`, each label exactly once, order kept | Pass |
| AC-2 | `AC2_SequenceBudgetSplitsByParticipants`: 8-participant ring → exactly 5 parts × 4 messages, ≤ 5 distinct names per part, union = 8 | Pass |
| AC-3 | `AC3_ConsecutiveMessagesMergedWithCount`: `notify() ×3` once; a,b,a → 3 arrows, no `×` | Pass |
| AC-4 | `AC4_StateTransitionsCountAndOverBudget`: non-consecutive identical edges → `go ×2`; 12 states → not over budget; 13 states → 1 part, `overBudget`, `<prefix>over budget: states 13 > 12` | Pass |
| AC-5 | `AC5_StructureTreeSplitsAndOverBudget`: duplicate relation → one edge; 21-node tree → several parts, `Structure (k/n)`, each relation in exactly one part, ≤ 12 names per part [Tester]; 13 children → 1 part, `<prefix>over budget: nodes 14 > 12`, all 13 relations | Pass |
| AC-6 | `AC6_LabelLineBreakAndMermaidEscape`: "alpha beta gamma delta epsilon" → `alpha beta gamma delta` + LB + `epsilon` per backend; Mermaid `a;b` → `a#59;b` | Pass |
| AC-7 | `AC7_OutputUnchangedFromBeforeSplitting` [Tester]: byte-identical to output captured from a build of `main` (a throw-away worktree; 1,126 bytes, all backends and wrappers); existing `PlantUMLFmtTest`, `MermaidFmtTest`, `D2FmtTest` pass unchanged | Pass |
| AC-8 | `AC8_ZeroBudgetClampedToOne`: `{.maxMessages = 0}` with one participant pair → 3 parts of 1 message; `{.labelWrap = 0}` terminates and breaks every character | Pass |
| AC-9 | `windows-x64-debug` (MSVC `/W4 /WX`), `linux-x64-debug` (GCC `-Werror`) and `linux-x64-asan` (ASan + UBSan): build and full suite, `100% tests passed` on all three | Pass |
| AC-10 | `AC10_FormattedDiagramIncludesPartCommentHeaders`: header before each split part; mixed trace: split Sequence parts get headers, the single State part does not, whole string exact | Pass |

## Runs
| Test | Expected | Actual | Status |
|---|---|---|---|
| U1 stand-in-types TU (GCC `-Werror`) + smoke run | split 15/15/10, `notify() ×3`, wrap | first run: `wrapLabel` padded every word to 24 chars → reworked; second run as expected | Pass after rework |
| After U2, U3+U4, U5, lead removals: both presets, existing suite unchanged | pass | pass after each unit | Pass |
| `naming_check.py` after U5 | 0 | 8: `count_if` (std, added to ALLOWED) and 7 named lambdas in agy code → renamed by `--apply` | Pass after fix |
| Golden comparison main vs branch (WSL g++) | identical | `AC-7: identical output (main vs branch)` | Pass |
| Example Demo 4 (Linux, `timeout 20`) | budget split visible | 11 Mermaid parts with `%% Sequence (k/11)` headers, `notify() ×3` | Pass |
| Final gates | all pass | `lint_docs` 0 errors; `naming_check` 0; script self-tests OK; `linux-x64-debug`, `linux-x64-asan`, `windows-x64-debug`: `100% tests passed` | Pass |

## Reviews
| Unit | Reviewer | Question | Findings | Resolution |
|---|---|---|---|---|
| U1 | codex `luna` (high) | D1 conformance | out-of-range runs skipped; `overBudget` forced on fallback parts; `wrapLabel` loop | all fixed by agy (`--resume`); the lead's own run had found the padding bug |
| U2 | codex `luna` | D3 types/declarations only | extras that were requested; `diagram_parts.hpp` include deferred by design | none to fix |
| U3+U4 | codex `luna` (high) | byte-identical part output; labels; note placement | 5 "differences" = the intended behaviour changes (non-consecutive repeats drawn, Mermaid `;` escaped) | none to fix |
| U1–U5 + lead removals (full source diff) | codex `luna` (high) | thread safety, lifetime, termination, format, D1–D3 | only: note wording "nodes" vs plan "children" | plan updated (the wording change was deliberate in U5) |
| U6 tests (Tester stage) | `cpp-reviewer` | does each test check its AC; can it pass trivially | AC-8 could not fail; `labelWrap = 0` would hang `wrapLabel`; AC-6/AC-4/AC-5/AC-2/AC-10 too weak; agy AC-7 mirrored the implementation | agy reworked tests and clamped `wrapLabel` width; the mirror test renamed; [Tester] golden covers AC-7 |
| U7 docs + Demo 4 | `cpp-reviewer` | doc claims vs code; C++ statements; Demo 4; spec §8 complete | KI-005 "byte-identical" too broad; spec 08 History missed "consecutive"; designated_initializers.md: C++11 aggregate rule, incomplete aggregate conditions, nonexistent `ErrorCode`; side notes: Mermaid titles outside the fence, `×` on cp949 consoles. §8 complete, Demo 4 correct | all doc points fixed; side notes registered as KI-010, KI-011 |
