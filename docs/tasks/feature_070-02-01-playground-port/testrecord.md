# Test Record: 070-02-01 플레이그라운드 `--port`를 페이지 포트로

- Spec: [/docs/specs/070_02_01_playground_port.md](/docs/specs/070_02_01_playground_port.md)
- Plan: [plan.md](/docs/tasks/feature_070-02-01-playground-port/plan.md)
- Date: 2026-10-29
- Hosts: Windows 11 (Python 3.15, Node 24.19, Vite 8.3.5) with the API server in WSL; WSL Ubuntu 24.04 (Python 3.12, Node 18.19) for the Linux run

## Runs

| # | Command | Expected | Actual | Status |
|---|---|---|---|---|
| R1 | WSL `python3 web/server/server.py --port 0`, then `/api/health` from Windows | answers | bound 34789, health answered through WSL localhost forwarding | Pass |
| R2 | `py -3 tools/test_playground.py` | pass | 10 OK in 3.7 s (both real launches ran) | Pass |
| R3 | mutation check: one change in `tools/playground.py`, run the tests, restore (scratch; `cmp` against a saved copy after each) | each killed | **4/4 killed**: M1 Vite not given the port; M2 origins on 5173; M3 dev server on the page port; M4 no busy check | Pass |
| R4 | M3 by hand (`--dev --port 19300`, through `timeout 60 … \| grep \| tail`) | launcher ends when Vite cannot keep its port | Vite reported ready (the WSL forward of 19300 was not up yet), then stopped; `error: the Vite dev server stopped` printed, but the pipeline ran into the 60 s timeout | Info |
| R5 | M3 again, output to a file, no pipe | launcher ends | Vite: `Port 19310 is already in use`; launcher printed the error and exited 1 after 2 s | Pass |
| R6 | real code: `--dev --port 19320`, `/api/health` through Vite, then kill Vite's `node.exe` | launcher ends at once, no WSL server left | health 200; launcher ended within 1 s with `error: the Vite dev server stopped`; `pgrep` in WSL found no `server.py` | Pass |
| R7 | `test_lessons.py`, `lessons.py check`, `naming_check.py`, `test_agent_scripts.py`, `lint_docs.py` | exit 0 | 29 OK; 0 errors; 0; OK; 0 errors, 0 warnings | Pass |

R4 note: the hang came with the shell pipeline and the mutant together; R5 (same mutant, no pipe) and R6 (real code) end at once. Not reproduced further.

## Revision 1 — 2026-10-29
Review (`cpp-reviewer`, one round) found four points; all fixed:
1. On Linux the probe without `SO_REUSEADDR` called a TIME_WAIT port busy while Vite (libuv) and `server.py` reuse it, so a quick restart moved the page to N+1. Fixed: `SO_REUSEADDR` on non-Windows; new test `test_time_wait_counts_as_free`.
2. No test checked that `main` hands the origins and port 0 to the real server. Fixed: `DevLaunchTest` sends `Origin` headers through Vite (page origins 200, another 403) and checks the server's command line.
3. `wait_any` and the `finally` cleanup were untested. Fixed: `WaitAnyTest` with fake processes, including `main` stopping both children when Vite ends.
4. `--port 0` in serve mode had become 8765, and out-of-range ports gave a traceback. Fixed: `None` means unset; range check with `parser.error` (serve 0..65535, dev 1..65535); `free_port` stops at 65535.

Also: `DevLaunchTest` skips with its reason on Node < 20 (WSL has 18.19; spec 070-02 needs 20+); the launch test prints the launcher's output on failure and fails at once when the launcher has ended.

| # | Command | Expected | Actual | Status |
|---|---|---|---|---|
| R8 | `py -3 tools/test_playground.py` after the fixes, first runs | pass | 4 runs in a row: `DevLaunchTest` failed after 30 s (page port refused) | Fail → KI-018 |
| R9 | the same, repeated (6, 10, 15, 3 runs) | pass | all pass, 3–4 s each | Pass |
| R10 | mutation check on the new tests | each killed by the intended test | first pass: `DevLaunchTest` failed in every run again (R8's stall, the launcher output now showed `npm run dev` printed nothing for 30 s); M8 (no range check) hung because the test reached a real launch; M9 was only "killed" by the stall. Tests fixed: range test stops at `launch_plan`, overflow test raises `OverflowError` above 65535 like the real `bind`, origin checks before the command-line check | Fail → fixed |
| R11 | mutation check again | each killed by the intended test | **8/8**: M5 origins dropped → `403 != 200`; M6 `server.wait()` → `WaitAnyTest`; M7 `port or 8765` → port-0 test; M8 → `went past the check`; M9 → `OverflowError`; M10 dev server on 8765 → 3 tests; M11 (WSL) no `SO_REUSEADDR` → `test_time_wait_counts_as_free`; M1–M4 rerun on the new tests: still killed (R16) | Pass |
| R12 | `py -3 tools/test_playground.py` (Windows) | pass | 17 OK, 3.7 s | Pass |
| R13 | WSL `python3 tools/test_playground.py` (Linux) | pass | 17 run, 1 skipped (`DevLaunchTest`: Node 18.19); `ServeLaunchTest` ran the server directly on Linux | Pass |
| R14 | `npm run dev` alone, 12 starts (scratch probe) | — | first line 0.38–0.53 s, ready 0.71–0.92 s, no stall | Info (KI-018) |
| R15 | checks of R7 again | exit 0 | 29 OK; 0 errors; 0; OK; lint 0 errors, 0 warnings | Pass |
| R16 | final `py -3 tools/test_playground.py` after M1–M4 were rerun on the new tests (all still killed) | pass | first run: `DevLaunchTest` stall again (34.9 s, third KI-018 occurrence; its output was not kept); next run 17 OK, then `DevLaunchTest` 3/3 OK right after an M1 run | Pass (KI-018 open) |

## Acceptance Criteria

| AC | Evidence | Status |
|---|---|---|
| AC-1 | R12 `DevLaunchTest`: `dev page:` is `http://127.0.0.1:<N>/`, Vite serves `/src/main.ts` there, `/api/health` through it returns the server's preset; M1, M3 fail it | Pass |
| AC-2 | R12 `LaunchPlanTest`, `WaitAnyTest` (port 0, Vite command), `DevLaunchTest` (real server: page origins 200, other 403, `--port 0`); M2, M5, M7, M10 fail them | Pass |
| AC-3 | R12/R13 `LaunchPlanTest` (busy page port moves, all busy → exit 1), `FreePortTest` (incl. TIME_WAIT on Linux), `WaitAnyTest` (Vite ends → launcher ends, both children stopped); R6 with the real Vite; M4, M6, M9, M11 fail them | Pass |
| AC-4 | R12/R13 `ServeLaunchTest`: page and `/api/health` on the given port (Windows via WSL, Linux directly) | Pass |

## Reviews
| Unit | Reviewer | Result |
|---|---|---|
| U1–U3 | `cpp-reviewer` | 4 findings, all fixed (Revision 1). No cross-family review: an ordinary unit (delegation.md §1) |
