# Test Record: 070-02 로컬 웹 플레이그라운드

- Spec: [/docs/specs/070_02_web_playground.md](/docs/specs/070_02_web_playground.md)
- Plan: [plan.md](/docs/tasks/feature_070-02-web-playground/plan.md)
- Date: 2026-10-28
- Hosts: Windows 11 (MSVC 19.51, Python 3.15, Node 24.19, Edge), WSL Ubuntu 24.04 (GCC 13.3, CMake 3.28, Ninja 1.11, Python 3.12)
- Frontend packages (exact): monaco-editor 0.57.0, mermaid 12.2.0, marked 18.1.2, dompurify 3.4.17; dev: vite 8.3.5, typescript 7.0.2, vitest 5.0.5, jsdom 30.1.3

## Runs

| # | Command | Expected | Actual | Status |
|---|---|---|---|---|
| R1 | `build.py --preset linux-x64-playground --target lesson_lambda_capture` | the new preset configures and builds a lesson | configured `out/build/linux-x64-playground`, `[7/7] Linking … lesson_lambda_capture` | Pass |
| R2 | WSL: `python3 web/server/test_server.py --fixture out/build/linux-x64-debug/bin/playground_fixture` | all pass | first run 30/31: the stream-close test used `conn.sock` (None after `Connection: close`); test fixed (`resp.close()`), then 31 OK | Pass |
| R3 | `py -3 web/server/test_server.py` (Windows, no fixture) | file and guard tests pass, run tests skipped with a note | 31 run, 15 skipped, OK, note printed | Pass |
| R4 | `npm run build` (`tsc --noEmit && vite build`) | exit 0 | first: `process` unknown in `vite.config.ts` → config left out of `tsc` (Vite loads it itself); then built | Pass |
| R5 | WSL: `python3 web/server/capture_diagrams.py` | seed lessons run through the runner; fixture written | `lambda_capture: 0`, `thread_and_log: 0`, `device_state_machine: 2 parts`; showed `DiagramPart::source` is a fenced Markdown block → page unwraps it (`mermaidSource`) | Pass |
| R6 | `npm test` (vitest) | pass | 4 files, 22 tests | Pass |
| R7 | `py -3 tools/playground.py --port 8790` (the command of the VS Code task, without `--open`); `curl /api/health`, `/` | server in WSL reachable from Windows | `atugcc playground: http://127.0.0.1:8790/`; health `{"version":1,"preset":"linux-x64-playground","compiler":"c++ (Ubuntu 13.3.0…)"}`; `/` 200 | Pass |
| R8 | browser scenarios (below), first run | all pass | 2 script timing failures (Ctrl+G → Enter swallowed, so text went on the wrong line) and the intentional 409 counted as a console error; script fixed | Script issue |
| R9 | browser scenarios, second run | all pass | 15/15 PASS | Pass |
| R10 | `build.py --preset linux-x64-debug --test` | 6 tests incl. `PlaygroundServer` | 6/6 | Pass |
| R11 | `build.py --preset windows-x64-debug --test` (`/W4 /WX`, builds `playground_fixture`) | 5/5 (PlaygroundServer is Linux only) | 5/5, no warnings | Pass |
| R12 | `lint_docs.py`, `naming_check.py` | exit 0 | 0 errors / 0 warnings; 0 snake_case function names | Pass |
| R13 | mutation check (scratch script: one change to `runner.py` / `server.py` / `files.py`, run the named tests, restore) | every mutant fails its tests | 12/13: "no output cap" survived — an equivalent mutant (`chunk[:room]` with `room ≤ 0` still drops the data); replaced in Revision 1 | See R17 |

Browser scenarios: a Node script outside the repository drives the installed Edge (`playwright-core`, headless) against the running server: it clicks, types in Monaco, runs lessons, reads the DOM and takes the screenshots in [`screenshots/`](/docs/tasks/feature_070-02-web-playground/screenshots/). It restores every lesson file it edits with `git checkout`.

## Revision 1 — 2026-10-28
Review findings (see Reviews) fixed in one round:
- `files.py`: a symlinked folder under `lessons/` could lead a write outside it, or a read into a hidden folder. Writes now need the resolved path under `lessons/`, and reads reject a resolved hidden component. Saves are serialized with a lock.
- `runner.py`: configure and build share the 120 s limit (configure no longer leaves the build an extra second).
- `test_server.py`: stream-close bound 1.0 s (as Stop); a deadline on the phase wait; the order test now watches both jobs side by side; new symlinked-folder test; fixture launcher passed after `--`.
- `tests/CMakeLists.txt`: `PlaygroundServer` passes `${ATUGCC_TEST_LAUNCHER}` (TSan builds run the fixture under `setarch -R`).
- `tools/playground.py`: children are tracked from the moment they start and stopped with `taskkill /T` on Windows (npm.cmd → node), also when Ctrl+C comes during start-up.
- Frontend: stale focus refresh after a save; a tab closed while loading; conflict on a deleted file; no EventSource retry loop; save errors and stop-before-run no longer leave the buttons stuck; diagram width minus padding; draw() cancelled by a newer draw/clear; 14 px source in the error box; Mermaid config test.

| # | Command | Expected | Actual | Status |
|---|---|---|---|---|
| R14 | WSL `test_server.py --fixture …` | all pass | first run: 5 failures from orphaned `loop` / `sleep 987` processes left by R13's kill-disabling mutants; killed them; then 32 OK | Pass |
| R15 | `npm run build`, `npm test` | pass | built; 4 files, 23 tests | Pass |
| R16 | mutation check, now cleaning orphans after each mutant | all killed | 12/14: the hidden-component and write-scope rules are now enforced twice (path text and resolved path), so removing one layer survives; mutants changed to remove both layers | See R17 |
| R17 | mutation check, final | all killed | **14/14 killed**: no `stdbuf`, no group kill after exit, no output cap, time limit ×3, Stop ignored, disconnect ignored, bind `0.0.0.0`, hidden components, symlink not resolved, write anywhere, symlinked-folder write, no sha check, CRLF lost, no Origin check | Pass |
| R18 | browser scenarios after the fixes | all pass | 15/15 PASS, no console errors | Pass |
| R19 | AC-2 again: apply the web edit (the diff R18 produced) to the file, `build.py --preset linux-x64-debug --target lesson_lambda_capture`, run, `cmp` with the web Output's stdout; restore | identical | `AC-2 stdout identical (5 lines)` | Pass |
| R20 | `build.py --preset linux-x64-tsan --test` | 6/6 | first: `PlaygroundServer` failed, `unrecognized arguments: -R` (the launcher went through argparse); launcher now follows `--`; then 6/6 | Pass |
| R21 | `build.py --test` on `linux-x64-debug` (6/6) and `windows-x64-debug` (5/5) after Revision 1 | pass | 6/6, 5/5 | Pass |
| R22 | killing `wsl.exe` (what VS Code "Terminate Task" does) while the server runs | Linux `server.py` ends too | no `server.py` process left in WSL | Pass |

## Revision 2 — 2026-10-28
Second (last) review round, see Reviews: server-side fixes all confirmed. Two residual frontend races were fixed by the lead exactly as the reviewer described, without a third review (delegation.md §6.3: no ping-pong); the browser check below covers the user-visible one. The reviewer's ASan suspicion was confirmed by running the preset and fixed. The doc review found three statements that said more than the code; corrected.
- `editor.ts`: a tab closed while its file was loading disposes the model it created (the URI could not be opened again); the focus refresh compares the tab object, not the path.
- `runner.py`: `ASAN_OPTIONS` gets `verify_asan_link_order=0` for the run (`stdbuf` uses `LD_PRELOAD`, which an ASan-built program otherwise refuses).
- `web/README.md` and the `runner.py` docstring: process cleanup names the `setsid` exception (KI-015); when configure and `npm ci` run is stated as the code decides it.

| # | Command | Expected | Actual | Status |
|---|---|---|---|---|
| R23 | `build.py --preset linux-x64-asan --test` before the ASan fix | 6/6 | `PlaygroundServer` failed: 10 run tests, `ASan runtime does not come first in initial library list` | Fail → fixed |
| R24 | `build.py --test` on `linux-x64-asan`, `linux-x64-debug`, `linux-x64-tsan` after the fix | 6/6 each | 6/6, 6/6, 6/6 (`PlaygroundServer` ≈ 30 s) | Pass |
| R25 | browser scenarios + "lesson A, B before A loaded, A again" | all pass | 16/16 PASS; entry file reopens, no console errors | Pass |
| R26 | final gates: `npm run build`, `npm test` (23), `py -3 web/server/test_server.py` (Windows, 16 skipped), `lint_docs.py`, `naming_check.py`, `tools/test_lessons.py` (27) | exit 0 | all exit 0 | Pass |

## Acceptance Criteria Evidence

| AC | Criterion (short) | Evidence | Result |
|---|---|---|---|
| AC-1 | one task starts the server; tree shows the 3 seed lessons and 2 units | R7 (task command), browser "AC-1" checks in R9/R18, [ac1-tree.png](/docs/tasks/feature_070-02-web-playground/screenshots/ac1-tree.png); `LessonsApiTest` | Pass |
| AC-2 | a web edit + Run changes the repo file (git diff) and its stdout equals the `linux-x64-debug` build's | browser "AC-2" checks (diff line `+    std::cout << "[web] edited in the playground\n";`), R19 `cmp` identical, [ac2-run.png](/docs/tasks/feature_070-02-web-playground/screenshots/ac2-run.png) | Pass |
| AC-3 | path escapes and forbidden writes rejected | `FilesTest.test_escapes_are_rejected` (10 forms), `test_symlink_out_of_the_repository_is_rejected`, `test_symlinked_folder_cannot_lead_writes_out_of_lessons`, `test_writes_outside_lessons_are_forbidden`, `ServerTest.test_encoded_and_plain_escapes_over_http` (`%2e%2e`, `%2F`, `%00`, `.git`, static path); mutants R17 | Pass |
| AC-4 | stale `baseSha` → 409 with current content; CRLF stays CRLF | `test_stale_base_sha_is_a_conflict_with_the_disk_content`, `test_crlf_file_stays_crlf`, `ServerTest.test_file_round_trip_and_conflict`; browser conflict dialog ([conflict-dialog.png](/docs/tasks/feature_070-02-web-playground/screenshots/conflict-dialog.png)) | Pass |
| AC-5 | endless lesson ends at ~10 s with `timedOut`, nothing left; 2 MiB → `truncated` | `RunnerTest.test_endless_lesson_ends_at_the_time_limit_without_leftovers` (10.0–12.0 s, SIGKILL, no process), `test_large_output_is_cut_at_one_mebibyte` (exactly 1 MiB), `test_background_children_do_not_survive` | Pass |
| AC-6 | compile error → marker on that file and line | browser "AC-6" (status `빌드 실패 · 오류 1개`, one `squiggly-error` on line 41), [ac6-marker.png](/docs/tasks/feature_070-02-web-playground/screenshots/ac6-marker.png); `diagnostics.test.ts`; `test_gcc_diagnostics_become_repo_relative` | Pass |
| AC-7 | `device_state_machine` events in seq order; click highlights the source line | browser "AC-7" (6 events, seq 1…6; click → tab `include/atugcc/pattern/state.hpp`, highlighted line 128 = event line), [ac7-events.png](/docs/tasks/feature_070-02-web-playground/screenshots/ac7-events.png) | Pass |
| AC-8 | all seed Mermaid parts parse; never below 80 %; wide parts scroll in their box | `mermaidParse.test.ts` (fixture from a real run, R5); browser "AC-8" (scales 0.8 / 1.0, 14 px text at 100 %, wide part scrolls, page does not, at 1600 px and 420 px), [ac8-diagrams.png](/docs/tasks/feature_070-02-web-playground/screenshots/ac8-diagrams.png), [ac8-narrow.png](/docs/tasks/feature_070-02-web-playground/screenshots/ac8-narrow.png) | Pass |
| AC-9 | server binds 127.0.0.1 only | `ServerTest.test_binds_loopback_only` (connect via the WSL eth0 address refused); mutant "bind 0.0.0.0" killed | Pass |
| AC-10 | `npm run build`, `npm test`, `test_server.py`, `lint_docs.py` exit 0 | R26 (and CTest `PlaygroundServer` in R24) | Pass |
| AC-11 | 1 line/s fixture: ≥ 4 `stdout` events at different times before `done` | `StreamTest.test_lines_arrive_while_the_lesson_runs` (SSE client), `RunnerTest.test_output_streams_line_by_line`; mutant "no stdbuf" fails both | Pass |
| AC-12 | Stop → `done{stopped:true}` within 1 s, nothing left; same for a closed stream | `RunnerTest.test_stop_ends_the_run_within_a_second`, `StreamTest.test_stop_over_http`, `StreamTest.test_closing_the_stream_stops_the_run` (1.0 s), `test_stop_while_queued_ends_the_job_without_running` | Pass |

Manual ACs (1, 2, 6, 7, 8) were run by the browser script with assertions, not by eye; the screenshots are the record.

## Reviews

| Unit | Reviewer | Question | Findings | Resolution |
|---|---|---|---|---|
| U3, U5 (`runner.py`, `server.py`) | codex luna (high) | races on `done`/stop, process lifetime, limits, SSE, request guard | `setsid()` descendants escape the group (and can block a reader); configure could leave the build +1 s; UTF-8 replacement may exceed the cap by a few bytes; exit just after the limit reported as normal exit | build limit fixed; `setsid` → KI-015 (local trust model, 070-05); the other two accepted (bytes cap is on raw bytes; a program that exited on its own did exit) |
| U2, U4, U6, U7, U1 | `cpp-reviewer` | path safety, test strength per AC, fixture build, launcher, rules | symlinked folder under `lessons/` → write outside; sha check vs replace race; stream-close bound 1.5 s; order test could not fail; phase wait without deadline; TSan launcher missing; `--dev` leaves node; Ctrl+C during start-up | all fixed in Revision 1 (wsl.exe termination verified: R22) |
| U8–U10 (frontend) | `cpp-reviewer` | data loss, XSS, stream/buttons, AC-8 policy, test strength | stale focus refresh after save; tab closed while loading; deleted-file conflict; EventSource retry loop; save exception locks Run; `run:null` crash; Stop before runId; padding in fit; overlapping draws; error-box font; fixture set too strict | all fixed in Revision 1; 11.2 px at the 80 % floor kept (diagrams.md §3 sets 14 px at 100 %) |
| Revision 1 (server) | same `cpp-reviewer` (second and last round) | is each finding fixed, anything new | all 5 fixed; suspected ASan failure through `stdbuf`'s `LD_PRELOAD` (unconfirmed) | ASan confirmed by R23, fixed (R24) |
| Revision 1 (frontend) | same `cpp-reviewer` (second and last round) | is each finding fixed, anything new | 5 of 7 fixed; focus refresh compared the path not the tab; a tab closed while loading left its model (URI blocked) | fixed by the lead as described (Revision 2), R25 |
| U11 docs | `cpp-reviewer` | does each document state only what the code does | `web/README.md`: "nothing outlives the run" (contradicts KI-015); configure and `npm ci` conditions incomplete | corrected (Revision 2) |

Cross-family review: `runner.py` and `server.py` (threads, process groups) were reviewed by codex although no unit is risky by delegation.md §3 (no C++ risk); the other units by `cpp-reviewer`.
