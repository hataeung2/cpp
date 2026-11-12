# Plan: 070-07 단계별 다이어그램 재생

- Spec: [/docs/specs/070_07_diagram_replay.md](/docs/specs/070_07_diagram_replay.md) (approved 2026-11-10)
- Branch: `feature/070-07-diagram-replay` (from `main` at `014b8fb`)

## Model assignment
Default split ([delegation.md](/.agent/rules/delegation.md) §1): agy `flash` writes ordinary code, test and tool units; the fresh reviewer (`cpp-reviewer`) reviews them. Risky units (public header, ODR, two files that change together) are reviewed by codex `luna`. The lead writes doc units and `lead (small)` changes.

## Findings from the Mermaid probe (Step 0 and the browser check)
| Syntax | Result |
|---|---|
| `sequenceDiagram` with `rect rgba(…)` … `end` around a message | parses and renders the yellow band (browser) |
| `stateDiagram-v2` with `classDef current …` + `class C current` | parses and renders the state yellow (browser) |
| same with a quoted state id (`class "b c" current`, `"b c":::current`) | **parse error** |
| `classDiagram` with `linkStyle 1 stroke:#e0a800` | `mermaid.parse` passes, but the browser render shows a class named `linkStyle1stroke`: **no link styling** (Assumption 6's `linkStyle` does not work in Mermaid 12.2.0) |
| `classDiagram` with `style B fill:#fff3b0,stroke:#e0a800,color:#000` | parses and renders the class yellow (browser) |
| `classDiagram` with `style "b c" …` | **parse error** |

Parse success is not proof (the `linkStyle` case); highlights are confirmed by rendering in a real browser. Consequences (recorded in the spec's History):
1. Structure highlight is `style <child> fill:#fff3b0,stroke:#e0a800,color:#000` on the child of the last relation, not `linkStyle`.
2. A name that `mermaidId` would quote (not `[A-Za-z0-9_]+`) gets no highlight in State and Structure (the diagram stays valid); documented in `visualizer.hpp` and `diagrams.md` §3. Sequence has no such limit.

## Design

### C++ (spec §2.1, Assumptions 4, 5, 6)
- `visualizer.hpp`: `struct DiagramRange { uint64 untilSeq = max; bool markLast = false; }`, free function `diagramPartsOf(span<const Message>, span<const Transition>, span<const Node>, backend = PlantUML, budget = {}, range = {})`, and the `Tracer::diagramParts(backend, budget, range)` overload. The old two-argument `diagramParts` stays. Includes `<limits>` `<span>`.
- `detail/diagram_parts.hpp`: the body of `Tracer::diagramParts` moves into `diagramPartsOf`. Precondition (documented): each list is in ascending `meta.seq` order (the Tracer's recording order; the tool sorts). The range cut uses `std::ranges::partition_point` on `seq <= untilSeq`. The three cut lists are copied into vectors (the formatters take `const std::vector<…>&`). `Tracer::diagramParts` takes the snapshot under `shared_lock` and calls it. Seq order = recording order inside one Tracer (seq is taken under the same `unique_lock` that appends), so the tool's seq sort gives the destructor's order; AC-1 shows it.
- Marking: `range.markLast` and backend Mermaid only. The last event of the range = the one with the largest `seq` among the last elements of the three cut lists. Its kind gets a mark (an index into the cut list) passed to the formatter as a last parameter `std::optional<std::size_t> mark = std::nullopt`. PlantUML and D2 formatters are not touched.
  - `MermaidFormatter::sequencePart(…, mark)`: the run with `run.index <= mark < run.index + run.count` is written as `    rect rgba(255, 235, 59, 0.35)\n<line>    end\n`. A chunk that does not hold the message has no `rect`.
  - `statePart(…, mark)`: after the edges, `    classDef current fill:#fff3b0,stroke:#e0a800,color:#000\n    class <new_state> current\n`, unless `mermaidId(new_state)` needs quotes.
  - `structurePart(…, mark)`: if the part holds a relation equal (parent, child, relation_type) to node `mark`, after the relation lines write `    style <child> fill:#fff3b0,stroke:#e0a800,color:#000` (unless `mermaidId(child)` needs quotes).
- `detail/event_stream.hpp`: new public `toJsonLines(std::uint32_t tracerId, const std::vector<DiagramPart>&) -> std::vector<std::string>` holds the part-index logic that `onDiagramParts` has now (index per kind); `onDiagramParts` writes those lines. The tool and the destructor therefore share one code path (AC-1).

### Tool `tools/diagram_replay/` (Assumption 7, 8)
- `event_reader.hpp` (namespace `atugcc::tools::replay`): `struct EventSet { vector<viz::Message> messages; vector<viz::Transition> transitions; vector<viz::Node> nodes; size_t skipped = 0; }`, `[[nodiscard]] EventSet readEvents(std::istream&, std::uint32_t tracer)`. One line = one flat JSON object of strings, integers, booleans (strings: `\" \\ \/ \b \f \n \r \t \uXXXX` incl. surrogate pairs → UTF-8). Unknown keys skipped. Kind `message|transition|node` of the wanted tracer are collected (`meta.seq`, `meta.tracerId` set; `file/line/func/tUs` ignored); `span` and `diagram` lines are ignored without counting; another tracer's events are ignored; a line that is not a flat object, has no integer `seq`/`tracer`, has `v` ≠ 1, an unknown kind, or a missing string field counts in `skipped`. A trailing `\r` is ignored. After reading, each list is stably sorted by `seq`.
- `replay.hpp`: `int replay(std::istream& in, std::ostream& out, std::ostream& err, std::uint32_t tracer, std::uint64_t until, bool markLast)` — reads, calls `diagramPartsOf(…, Mermaid, {}, {until, markLast})`, writes `toJsonLines(tracer, parts)` one per line, then writes `skipped: N` as the last line of `err`. Returns 0.
- `main.cpp`: arguments `--tracer <id> --until <seq> [--mark-last]` (`--until` optional = max); wrong arguments → usage on stderr, exit 2; calls `replay(std::cin, std::cout, std::cerr, …)`.
- `CMakeLists.txt`: target `atugcc_diagram_replay` (links `atugcc_headers atugcc_core`, include dir of the tool for tests), `RUNTIME_OUTPUT_DIRECTORY` `${CMAKE_BINARY_DIR}/bin/tools`; the root `CMakeLists.txt` adds the directory inside `if (ATUGCC_BUILD_LESSONS)`.
- stdout on Windows is text mode (CRLF); the tool is used on Linux by the server, and tests compare lines without `\r`. No `_setmode`/`#ifdef`.

### Server (Assumptions 3, 9, 12)
- `runner.py`: `Job.replay: dict[int, list[dict]]` keeps `message|transition|node` events per tracer from `_trace_lines` (cap `REPLAY_MAX_EVENTS = 5000` per tracer; over it the tracer's list is dropped and `Job.replay_counts` keeps counting). The `done` payload gets `replay: {"max": 5000, "tracers": {"<tracer>": count}}`. The build runs `--target lesson_<id> atugcc_diagram_replay` (one `--target`, two names). `RunManager.replay_tool(build_dir)` → `[build_dir/bin/tools/atugcc_diagram_replay]`, injectable (`replay_tool=` like `executable=`); `RunManager.replay(job, tracer, until, mark)` runs it.
- `server.py`: `GET /api/runs/<id>/diagrams?tracer=<t>&until=<seq>[&mark=0|1]` → 404 no run, 409 not done, 400 bad numbers or a tracer over the cap, 404 unknown tracer, 500 `{error}` when the tool fails or is missing; 200 `{tracer, until, parts: [DiagramLine…]}`. The tool is started with the tracer's events as JSON lines (`ensure_ascii=False`, UTF-8) on stdin, 10 s timeout, stdout parsed line by line.

### Page (Assumptions 9–11)
- `web/frontend/src/replay.ts` (new, no DOM except the bar class): pure state `ReplayState` — `replayTracers`, `setStep`, `next/prev/first/last`, `goToSeq`, cache key `(tracer, seq)`; `DiagramsPanel` hosts the bar: tracer select (only when ≥2 replayable tracers), ⏮ ◀ ▶ ⏭, range slider, `k / n` + `describe(event)`, keys ←/→ with focus in the panel, toggle to switch off. Moving a step: debounce 150 ms, fetch `/api/runs/<id>/diagrams`, draw (last Sequence part expanded, earlier ones folded `<details>`), select the Events row, open the editor line. Clicking an Events row calls back into replay. `main.ts` keeps `runId` of the finished run in `lastRunId`. Off with a reason when: the tracer has more than `replayMax` events, the Events panel does not hold all events of the tracer, or the run is not `done`/build failed.
- `api.ts`: `api.replayParts(runId, tracer, until)`; `DoneData.replay` (`ReplayInfo {max, tracers}`).
- `i18n.ts` (ko/en pair), `theme.css`: bar styles, `.replay-fold`.

### Docs (§8)
`visualizer.hpp` head comment, `diagrams.md` §3, `web/README.md`, both `designated_initializers` notes, `lessons/README.md`, `agent_todo.md`, the spec's History (Findings above).

## Files
- [MODIFY] `include/atugcc/pattern/visualizer.hpp`, `detail/diagram_parts.hpp`, `detail/mermaid_formatter.hpp`, `detail/event_stream.hpp`
- [NEW] `tools/diagram_replay/{CMakeLists.txt,event_reader.hpp,replay.hpp,main.cpp}`, `tools/diagram_replay/compare_lessons.py`
- [MODIFY] `CMakeLists.txt`, `tests/CMakeLists.txt`
- [NEW] `tests/pattern/test_diagram_range.cpp`, `tests/pattern/test_event_reader.cpp`, `tests/scenario/scenario_diagram_replay.cpp`
- [MODIFY] `web/server/runner.py`, `server.py`, `test_server.py`
- [NEW] `web/frontend/src/replay.ts`, `web/frontend/test/replay.test.ts`; [MODIFY] `diagrams.ts`, `events.ts`, `main.ts`, `api.ts`, `i18n.ts`, `theme.css`, `web/frontend/test/mermaidParse.test.ts` (marked-diagram cases)
- [MODIFY] docs listed above

## C++20/23 features applied
`std::span<const T>` params, designated initializers for `DiagramRange`, `std::ranges::partition_point`, `std::optional` mark. Evolution note: one line in `docs/cpp_evolution/designated_initializers.md` + `.en.md`.

## Unit table
| Unit | File | Change (what, where, AC) | Check | Risky | Author | Reviewer | Tokens (in / out) | Status |
|---|---|---|---|---|---|---|---|---|
| U1 | `visualizer.hpp`, `detail/diagram_parts.hpp` | `DiagramRange`, `diagramPartsOf` (cut only, no marks yet), `Tracer::diagramParts` overload (AC-2) | `grep -c diagramPartsOf` ≥ 3; build `atugcc_tests`; existing `Tracer*`/`DiagramSplit*` tests | yes | agy flash | | | |
| U2 | `detail/event_stream.hpp` | `toJsonLines`, `onDiagramParts` uses it (AC-1) | `grep -c toJsonLines`; `--gtest_filter=EventStream*` | yes | lead (small) | | | |
| U3 | `tests/pattern/test_diagram_range.cpp`, `tests/CMakeLists.txt` | range cases first/middle/last/out, default = old result (AC-2) | `--gtest_filter=DiagramRange*` | no | agy flash | | | |
| U4 | `detail/mermaid_formatter.hpp`, `detail/diagram_parts.hpp` | `mark` parameter, mark selection by largest seq, three highlights (AC-3) | build; U3 tests still pass | yes | agy flash | | | |
| U5 | `tests/pattern/test_diagram_range.cpp` | mark tests: three kinds, no mark for PlantUML/D2, quoted-id skip, folded run (AC-3) | `--gtest_filter=DiagramRange*` | no | agy flash | | | |
| U6 | `web/frontend/test/mermaidParse.test.ts` | marked sequence/state/structure sources parse, a broken marked one fails (AC-3) | `npm --prefix web/frontend test` | no | lead (small) | | | |
| U7 | `tools/diagram_replay/event_reader.hpp` | reader (AC-4) | build `atugcc_tests` after U8 | no | agy flash | | | |
| U8 | `tests/pattern/test_event_reader.cpp`, `tests/CMakeLists.txt` | round trip for message/transition/node, escapes, broken/`v` lines, other tracer, span/diagram ignored, sort (AC-4) | `--gtest_filter=EventReader*` | no | agy flash | | | |
| U9 | `tools/diagram_replay/{replay.hpp,main.cpp,CMakeLists.txt}`, root `CMakeLists.txt` | tool and target (Assumption 8) | build target `atugcc_diagram_replay`; run by hand | no | agy flash | | | |
| U10 | `tests/scenario/scenario_diagram_replay.cpp`, `tests/CMakeLists.txt` | events recorded by a Tracer → file → `replay()` → lines equal the destructor's lines; middle `until` (AC-1) | `--label scenario` | no | agy flash | | | |
| U11 | `tools/diagram_replay/compare_lessons.py` | every Tracer lesson: run, run the tool to the last seq, compare to the `diagram` lines (AC-1) | run on linux preset | no | agy flash | | | |
| U12 | `web/server/runner.py` | keep replay events (cap), `done.replay`, build target, tool command (AC-5) | `test_server.py` | no | agy flash | | | |
| U13 | `web/server/server.py` | `/api/runs/<id>/diagrams` (AC-5) | `test_server.py` | no | agy flash | | | |
| U14 | `web/server/test_server.py` | endpoint statuses, cap, fake tool, real tool when built (AC-5) | `test_server.py` | no | agy flash | | | |
| U15 | `web/frontend/src/replay.ts`, `test/replay.test.ts` | pure step state + tests (AC-5) | `npm test` | no | agy flash | | | |
| U16 | `api.ts`, `diagrams.ts`, `events.ts`, `main.ts`, `i18n.ts`, `theme.css` | bar, cache, folding, links to Events and editor (AC-5) | `npm run build`, `npm test`, screenshots | no | agy flash | | | |
| U17 | docs (§8) | `visualizer.hpp` comment, `diagrams.md`, `web/README.md`, `designated_initializers` pair, `lessons/README.md`, spec History, `agent_todo.md` | `lint_docs.py` | no | lead | | | |

## Result of the unit table
All units `done`. Authors: agy `flash` for U1, U3, U4, U5, U7, U8, U9, U10, U12/U13, U14; `lead (small)` for U2, U6, U11 and every review-fix round; `lead (fallback)` for U15 and U16 (agy answered 403 during U14). Reviewers and findings: [testrecord.md](testrecord.md) "Reviews". The server plan deviations of the review are aligned above (`replay_tool`, `api.replayParts`, `done.replay = {max, tracers}`).
