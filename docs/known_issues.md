# Known Issues & Follow-ups

Every follow-up or non-blocking finding gets a `KI-NNN` id here and is referred to by that id from walkthroughs, testrecords and specs.

- **Status**: `OPEN`, `PLANNED` (a task owns it), `CLOSED` (with the closing task or commit).
- New entries go at the bottom with the next free id. Closed entries stay as a record.

| ID | Status | Area | Found | Owner |
|---|---|---|---|---|
| KI-001 | PLANNED | docs/cpp_evolution | 090-01 | Phase 5 (050-xx) |
| KI-002 | OPEN | legacy spec links | 090-01 | — (sealed, informational) |
| KI-003 | OPEN | git / main | 090-01 | user decision |
| KI-004 | PLANNED | CMakePresets.json | 090-01 | 090-01 Step 5 |
| KI-005 | PLANNED | pattern visualizer (all diagram backends) | 090-01 | 020-04 |

## KI-001 — `docs/cpp_evolution` pages referenced but missing
Specs reference six evolution pages that do not exist: `cmake_modernization.md` (spec 01), `concepts.md` (03), `filesystem_format.md` (05), `source_location.md` (06), `trace_console_toggle.md` (08_001), `tracer_benchmarking.md` (08_002). Spec 04 still marks `chrono_format.md` as "(예정)" although the page exists.
**Next**: write them under Phase 5, or in the task that next touches each module; a new spec lists the page under Documentation Updates.

## KI-002 — Stale links in legacy specs
Specs 03, 04 and 05 link `/include/atugcc/core/ring_buffer.h`, the header's name at the time; it is now `ring_buffer.hpp`. Legacy specs are records of their round and are not edited (spec.md §5). The docs lint reports these as information, not errors.

## KI-003 — `main` is behind the integrated work
`main` is 8 commits behind `feature/dedicated-console`. Every feature branch is already merged linearly into that tip, so `main` can be fast-forwarded. Until then, new branches cannot follow the "branch from `main`" rule; 090-01 branched from `feature/dedicated-console` (spec 090-01 Assumption 7).
**Next**: the user decides when to fast-forward and push `main`.

## KI-004 — Machine-specific paths in `CMakePresets.json`
`windows-base` hard-codes `C:/vcpkg/scripts/buildsystems/vcpkg.cmake` and the Visual Studio Ninja path, which breaks Non-negotiable Rule 1 and other machines' builds. `VCPKG_ROOT` is not set on the current Windows machine, so switching to `$env{VCPKG_ROOT}` needs a migration step. The same paths appear in `.agent/rules/CMakePresets.example.json`.
The README records that `$env{VCPKG_ROOT}` was not picked up on Windows (IDE launched without the variable), which is why the absolute path was committed. The README's `ctest --preset windows-x64-debug` also fails: `CMakePresets.json` defines no `testPresets`.
**Next**: 090-01 Step 5: machine paths move to an untracked `CMakeUserPresets.json` (works without env vars in VS, VS Code and CLI), add `testPresets`, verify both presets build.

## KI-005 — Diagram formatters drop repeated messages
The sequence and class-tree outputs of all three backends (`mermaid_formatter.hpp`, `plantuml_formatter.hpp`, `d2_formatter.hpp`) skip any `(from, to, action)` already seen, so a repeated call (e.g., an Observer broadcasting twice) is drawn once and its order is lost. `state_diagram` does the opposite and draws duplicate edges. Neither bounds the diagram's width, so wide traces shrink to unreadable text in a web view.
**Next**: 020-04 (rules: `.agent/rules/diagrams.md`, 090-01 Step 4).
