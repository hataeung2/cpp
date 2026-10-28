# Plan: 090-02 함수 명명 camelCase 통일

- Spec: [/docs/specs/090_02_camelcase_rename.md](/docs/specs/090_02_camelcase_rename.md) (approved 2026-10-28)
- Branch: `feature/090-02-camelcase-rename` (from `main` after 090-03)

## Inventory (U1)
`py -3 .agent/scripts/naming_check.py --map` found 41 project-defined snake_case function names in `include/`, `src/`, `tests/`, `sample/`, `main.cpp` (`libs/` has no sources; `modules/` has none). Not renamed: `out_file` (an `std::ofstream` variable), `get_local_time` (`std::chrono::zoned_time` member), and the std/POSIX/Boost names in `ALLOWED`. Strings such as `"run_cycle()"` in trace output stay as they are (spec §4).

| Area | Renamed |
|---|---|
| `pattern/visualizer.hpp` + definitions in `detail/plantuml_formatter.hpp` | `recordMessage`, `recordTransition`, `pushNode`, `formatTerminal`, `formatDiagram`, `formatPlantuml`, `formatMermaid`, `formatD2`, `snapshotMessages/Transitions/Nodes`, `getGlobalTracer`, concept `onEvent` |
| `pattern/detail/*_formatter.hpp` | `sequenceDiagram`, `stateDiagram`, `classTree`, `messageFlow`, `stateFlow`, `structureTree`, `plantumlId`, `mermaidId`, `d2Id`, `formatTree`, `formatMessages`, `formatTransitions`, `renderNode`, `sectionHeader`, `enableWindowsAnsi` |
| `pattern/observer.hpp` | `registerObserver`, `notifyObservers`, `removeExpired`, `setData`, `collectDisplays`, `onNotify` |
| `pattern/state.hpp` | `stateName`, `currentStateName`, `isTransitionAllowed` |
| `core/memory_dump.hpp` | `safeWrite`, `ignoreResult` |
| examples / samples | `tryTransition`, `conditionVariableUsage1` |

## Units
| Unit | File | Change | Check | Risky | Author | Reviewer | Status |
|---|---|---|---|---|---|---|---|
| U1 | `.agent/scripts/naming_check.py` | inventory, map, `--apply` (code + comments, never literals), clash refusal | 4 self-tests; `--map` reviewed by the lead | no | lead | — (tool; covered by tests) | done |
| U2 | 12 source files | apply the 41-name map | `naming_check.py` = 0; diff +247/−247; both presets build warning-free; suite passes; test list unchanged | yes (public header API) | lead (scripted) | codex `luna` | see testrecord |
| U3 | rules | impl.md naming exceptions + check; test.md naming gate; delegation.md §1 mechanical-change clause | lint exit 0 | no | lead | codex review covers U2 only; rules reviewed with this plan | done |

## Decisions during implementation
- **Scripted instead of agy units.** The spec's plan split the rename into per-header agy units. A rename touches each header *and* all its call sites (e.g. `recordMessage`: 23 sites in 6 files), so the 3-file limit per call would have cut the map into many calls, each able to miss sites, at about 47k input tokens per call. The spec fixes the exact text (the map), so a tested script applies it in one deterministic pass; the risky-unit safeguards stay: codex reviews the diff and both compilers plus the suite verify it. delegation.md §1 now names this case (`lead (scripted)`).
- `naming_check.py` stays as a permanent gate (test.md), so new snake_case functions are caught.
