# Plan: 070-06 장시간 실행 프로필과 구간 시간(Timings) 화면

- Spec: [/docs/specs/070_06_long_run_timings.md](/docs/specs/070_06_long_run_timings.md) (approved 2026-10-29)
- Branch: `feature/070-06-long-run-timings` (from `main` at `9ad0b6d`)

## Design (fixed by the lead; units implement exactly this)

Decisions not spelled out in the spec:
- A new lesson `span_timing` (essentials track, `profile = "long"`) is added. The manual ACs (AC-3 screenshot, AC-6, AC-8) need a lesson in the page that records spans; the test fixture is not a lesson. It also gives `lessons/README.md` "성능 측정 레슨" a worked example. It runs for a fixed time (15 s), not a fixed amount of work, so Debug and sanitizer smoke tests take the same time.
- `[run] build` in the index is the **effective** value for the manifest's profile; the runner gets the explicit value (or none) so the "길게 실행" toggle on a quick lesson picks Release unless the manifest says `debug` (Assumption 3).
- Output cap (Assumption 8): the long profile caps stdout and stderr **together** at 8 MiB; quick keeps 1 MiB per stream (070-02).
- Stop during the final trace drain ends the drain (070-02 AC-12: done within 1 s after Stop). A time-limit or trace-limit end drains the rest.
- `spans` events carry no SSE `id` (they are not in `job.events`); a reconnecting stream gets a full snapshot.

### D1. `CMakePresets.json`
configure + build preset `linux-x64-playground-release`: inherits `linux-x64-relwithdebinfo`, same cache variables as `linux-x64-playground` (tests and samples off, lessons on), own build directory (`out/build/${presetName}` from the base).

### D2. `tools/lessons.py`, `tools/test_lessons.py`
- `BUILDS = ("release", "debug")`. `Lesson.build: str | None` = the manifest's `[run] build` (None when absent). A value outside `BUILDS` → ERROR, treated as absent.
- `effective_build(profile, build)` → `build` or (`"release"` if profile is long else `"debug"`).
- index `run`: `{profile, timeout, build: effective_build(lesson.profile, lesson.build)}`.
- tests: default per profile, explicit debug on long, explicit release on quick, bad value is an ERROR.

### D3. `web/server/spans.py` (new)
`SpanAggregator(sample_size=1024, bins=20, seed=None)`:
- `add(obj) -> bool`: requires `file` str, `line` int ≥ 0 (not bool), `label` str, `meter` str, `durNs` int ≥ 0 (not bool); else False. Key `(file, line, label, meter)`. Exact count/total/min/max; reservoir (Algorithm R, `random.Random(seed)`).
- `drain() -> list[row]` (keys changed since the last drain), `snapshot() -> list[row]` (all), `lines` (accepted spans).
- row: `{file, line, label, meter, count, totalNs, minNs, maxNs, p50Ns, p95Ns, hist: {loNs, hiNs, bins}}`. Nearest-rank percentiles on the sorted sample. `hist`: sample min..max on a `log(x+1)` scale into `bins` buckets; min == max → `bins: [n]`.

### D4. `web/server/runner.py`
- `RELEASE_PRESET = "linux-x64-playground-release"`. `Limits` gains `trace_bytes: int` and `combined_output: bool`; `run_sec: float | None` (None = the lesson's `timeout`). `PROFILES`: quick `(120, 10, 1 MiB, 1 GiB, False)`, long `(180, None, 8 MiB, 1 GiB, True)`.
- `LessonInfo(id, path, profile, timeout=300, build=None)`.
- `RunManager(root, preset=PRESET, release_preset=RELEASE_PRESET, …)`; `build_dir(kind)`; `executable(info, build_dir)`; `create(lesson_id, profile_override=None, span_meter=None)` (ValueError for a bad value). `Job` stores `profile_override`, `span_meter`.
- `_execute`: effective profile = override or manifest (unknown → quick); build kind = `lessons.effective_build(profile, info.build)`; `buildType` (`Debug` / `RelWithDebInfo`) in every `phase`; run limit = `limits.run_sec or info.timeout`; env `ATUGCC_TRACE_FLUSH_MS=100`, `ATUGCC_SPAN_METER` when given; `_build` and diagnostics use that kind's preset and build directory.
- `_Collector(cap, combined)`: combined → one budget across stdout and stderr.
- `TraceTail.read(final, limit=4 MiB)`: reads at most `limit` bytes per call; `size()` (stat); `lag()`.
- `_trace`: `span` objects go to the job's `SpanAggregator` (invalid → skipped), with `file` made repo-relative; other kinds as in 070-02. After the lines: `job.publish_spans(aggregator.drain(), aggregator.lines, lag)` when rows changed or lag changed. Returns True when the file is over `trace_bytes`.
- `_stream`: the trace callback's True → `outcome.trace_limit = True`, kill the group (like the time limit). Final flush: read in 4 MiB chunks until the file is drained, ending early when Stop is requested.
- `done.run.traceLimit`.
- `Job`: `span_rows: dict[key, (version, row)]`, `span_info: (version, {spanLines, lagBytes})`, `span_version`. `publish_spans(rows, lines, lag)` bumps the version and notifies. `updates_from(index, seen, timeout) -> (events, done, spans_payload | None, seen')`: payload = rows with version > `seen` (or every row with `full: true` when done), plus `spanLines`, `lagBytes`; None when nothing changed and nothing was ever published.

### D5. `web/server/server.py`
- `POST /api/runs`: optional `profileOverride` ∈ {quick, long}, `spanMeter` ∈ {wall, cpu}; else 400.
- `_stream` uses `updates_from`; writes `event: spans` (no `id`) **before** the batch's regular events (so the final snapshot precedes `done`).
- `/api/health`: adds `releasePreset`.

### D6. `tests/playground/playground_fixture.cpp`
- `sleep25`: sleeps 25 s, prints `slept`, exit 0 (AC-1).
- `span_tick`: 5 × (`timeScope("tick")` around 20 ms, then `recordSpan("io", i ms, here, "perf")`), 1 s apart; then prints each `spanStats()` row as `STATS {json}` on stdout (AC-3, AC-4).
- `span_flood`: `recordSpan("flood", …)` at 100,000 per second (batches of 100 per ms) for 30 s (AC-7, AC-10).

### D7. `web/server/test_server.py`, `tests/CMakeLists.txt`
- `SpanAggregatorTest` (AC-9).
- `RunnerTest`: AC-1 (long 25 s ok; quick override times out at 10 s), AC-2 (buildType per profile/build; preset names exist in `CMakePresets.json`), AC-3, AC-4 (+ `spanMeter: cpu` rows), AC-7 (flood: no span in `job.events`/`trace`, gaps between span updates ≤ 500 ms, RSS growth < 50 MB), AC-10 (small budget → `traceLimit`, temp file removed).
- `StreamTest`: `spans` events over HTTP, final `full` before `done`; 400 for bad `profileOverride`/`spanMeter`.
- `PlaygroundServer` ctest TIMEOUT 180 → 420.

### D8. Frontend (`web/frontend`)
- `api.ts`: `SpanRow`, `SpansData`, `PhaseData.buildType`, `run.traceLimit`, `RunInfo.build`, `startRun(lesson, {profileOverride?, spanMeter?})`, `handlers.spans`.
- `timings.ts` (new): pure functions `formatNs` (020-06 §2.3 rule), `rowKey`, `meanNs`, `compareToPrevious(rows, prev, buildType)`, `inlineByLine(rows)` (count sum, weighted mean per file:line), `loadPrevious`/`savePrevious` (localStorage, try/catch); `TimingsPanel` (sortable table, tabular numerals, click → editor line, expandable SVG histogram, lag and limit notes).
- `editor.ts`: `setInlineTimings(map)` → `after` decorations per model (applied when a model loads), cleared on the next run.
- `output.ts`: optional `maxLines` (long: 5,000; oldest nodes dropped, one note).
- `main.ts`, `index.html`, `theme.css`: "길게 실행" toggle, meter select, remaining time, build type, lag, Timings tab, trace-limit message.
- `test/timings.test.ts` (AC-5 and helpers).

### D9. Lesson `lessons/tracks/01_essentials/03_span_timing/`
`lesson.toml` (`profile = "long"`, `timeout = 120`), `main.cpp` (15 s: vector push_back with/without `reserve`, `std::map` vs `std::unordered_map` lookups, each round in a `timeScope`; prints `formatTimings()`), `README.md` (what it shows, wall vs cpu, exercises).

### D10. Docs (spec §8)
`web/README.md`, `lessons/README.md`, `.agent/rules/config.md`, `docs/specs/070_02_web_playground.md` History, `docs/known_issues.md` KI-016.

## Changes to the design during implementation
- D2: the index carries `[run] build` **as written** (null = default), not the effective value. The page shows the build kind with the runner's rule (`effectiveBuild`, same as `lessons.effective_build`); with the effective value the page could not tell an explicit `build` from a default and showed the wrong kind for a toggled run (review finding).
- D4: a tick that is behind keeps reading 4 MiB pieces for up to `TRACE_TICK_SEC` = 0.25 s, publishing after each piece; the final drain publishes per piece too. `repo_relative()` is cached per file name (it was the per-line bottleneck: the first AC-7 run had a 179 s gap). An unfinished line longer than one piece is dropped and counted as skipped (`TraceTail.oversized`), so memory stays bounded (codex finding).
- D4: the `build` phase event's `limitSec` is the time left after configure (configure and build share `build_sec`).
- D8: inline span times use an editor-owned decorations collection with `afterContentClassName` and one generated CSS rule per line (`::after { content: … }`). Monaco 0.57 did not render `after` injected text of these decorations (model-level or editor-level) in this page; checked in the browser.
- D8: "집계 지연" shows from 1 MiB of lag (below that it is only the unfinished last line); the comparison column is left out when storage is blocked; a selected Timings row stays selected across live updates.

## Units
| Unit | File | Change (what, where, AC) | Check | Risky | Author | Reviewer | Tokens (in / out) | Status |
|---|---|---|---|---|---|---|---|---|
| U1 | `CMakePresets.json` | D1 | WSL `cmake --preset linux-x64-playground-release` + build `lesson_lambda_capture` (RelWithDebInfo) | no | lead | `cpp-reviewer`: none | — | done |
| U2 | `tools/lessons.py`, `tools/test_lessons.py` | D2 (AC-2) | `test_lessons.py` 29 OK; `lessons.py check` | no | lead | `cpp-reviewer`: index build value vs page rule → index carries the written value | — | done |
| U3 | `web/server/spans.py` | D3 (AC-9) | `SpanAggregatorTest` | no | lead | codex luna (with U4, U5): none | (see U4) | done |
| U4 | `web/server/runner.py` | D4 | `test_server.py` RunnerTest, LongRunTest, TraceAndDiagnosticsTest | no (Python; threads and process groups → cross-family review as in 070-02) | lead | codex luna (high): unbounded partial line → fixed; final-flush budget and reader-join delay → not changed (testrecord) | 233k / 4k | done |
| U5 | `web/server/server.py` | D5 | `test_server.py` StreamTest, ServerTest | no | lead | codex luna (with U4): none | (see U4) | done |
| U6 | `tests/playground/playground_fixture.cpp` | D6 | both presets build | no | lead | `cpp-reviewer`: none | — | done |
| U7 | `web/server/test_server.py`, `tests/CMakeLists.txt` | D7 | green; 10/10 mutants killed | no (test) | lead | `cpp-reviewer`: peak RSS not sampled, stream order flaky → fixed | 139k (reviewer, U1–U2, U6–U11) | done |
| U8 | `web/frontend/src/*`, `index.html` | D8 | `npm run build`; browser 17/17 + AC-8 5/5 | no | lead | `cpp-reviewer`: build rule, lag in top bar, storage column, selection, Space → fixed; 5,000+one-chunk cap, fractional ns → testrecord | — | done |
| U9 | `web/frontend/test/timings.test.ts` | D8 tests (AC-5) | `npm test` 37 | no (test) | lead | `cpp-reviewer`: equal counts let totals pass, same-line click → fixed | — | done |
| U10 | `lessons/tracks/01_essentials/03_span_timing/*` | D9 | `lessons.py check`; smoke test on both presets | no | lead | `cpp-reviewer`: exercise 1 shifted lines → comment out instead | — | done |
| U11 | docs | D10 | `lint_docs.py` | no (doc) | lead | `cpp-reviewer`: 4 statements → fixed | — | done |
