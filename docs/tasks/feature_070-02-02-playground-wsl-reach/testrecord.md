# Test Record: 070-02-02 플레이그라운드가 WSL 서버에 닿지 않을 때 알려 주기

- Spec: [/docs/specs/070_02_02_playground_wsl_reach.md](/docs/specs/070_02_02_playground_wsl_reach.md)
- Plan: [plan.md](/docs/tasks/feature_070-02-02-playground-wsl-reach/plan.md)
- Date: 2026-11-04
- Host: Windows 11 (Python 3.15.1) with the API server in WSL 2.7.11 (NAT networking)

## Runs

| # | Command | Expected | Actual | Status |
|---|---|---|---|---|
| R1 | before the change: `playground.py --dev --port 9000`, then `curl` the API port from Windows; `ss -ltn` in WSL; `tasklist` | find the cause of the user's `ECONNREFUSED` | WSL listened on `127.0.0.1:37639`; Windows got no connection (Vite 502); a WSL server on fixed port 8799 also unreachable after 10 s; no `wslrelay.exe` process | Info |
| R2 | after the change, real run `playground.py --port 19100` | forwarding was back by then (`wslrelay.exe` PID 28044, user session) | check passed, page served, `/api/health` 200 from Windows | Info |
| R3 | `py -3 tools/test_playground.py ReachableTest` | pass | 10 OK in 8.9 s | Pass |
| R4 | mutation check: one change in `tools/playground.py`, run `ReachableTest`, restore (`cmp` against a saved copy) | each killed | **5/5 killed**: no retry; system proxy used; check only with `--dev`; check on every OS; fixed 1 s attempt timeout | Pass |
| R5 | `py -3 tools/test_playground.py` (all, real launches included) | pass | first run: 27 tests, **1 failure**, 47.8 s (see Notes); then 7 runs OK (9–14 s), 2 of them right after rewriting `tools/playground.py` | Pass (see Notes) |
| R6 | `lint_docs.py`, `naming_check.py` | exit 0 | 0 errors, 0 warnings; 0 | Pass |

## AC evidence

| AC | Evidence | Status |
|---|---|---|
| AC-1 | R3: `test_any_response_is_reachable` (200, 403), `test_closed_port_is_unreachable_after_the_wait` (wait 0.3 and 3.0, ends within wait + 0.5), `test_server_end_stops_the_wait`, `test_a_server_that_answers_late_is_reachable`, `test_system_proxy_is_not_used`; R4 | Pass |
| AC-2 | R3: `test_unreachable_on_windows_stops_before_vite` (message, exit 1, server stopped, no Vite), `test_server_that_ended_during_the_check_gives_its_code`, `test_serve_mode_is_checked_too`, `test_no_check_on_linux`; R4 | Pass |
| AC-3 | real WSL with forwarding stopped: not yet run. The forwarding came back before the code was ready (R2). R1 shows the stopped state refuses the connect, which `test_closed_port_is_unreachable_after_the_wait` does with a real socket | **Pending** |
| AC-4 | R5: `DevLaunchTest`, `ServeLaunchTest` pass with the check in place | Pass |

## Reviews
- Round 1, agy argon (read-only, 560 s): 3 findings. (1) No test of the retry path; on Windows a refused loopback connect takes about 1 s, so `wait=0.6` never retried. (2) Attempt timeout and sleep not clamped to the deadline: `wait=10` could run to about 11 s. (3) Proxy bypass and the serve-mode check untested. All fixed by the lead (plan "Changes after review").
- Round 2, agy argon (same conversation, 904 s): no findings.

## Notes
- R5 first run: the failing test's name and output were not kept (only the summary line was read). It was the first full run after the R4 restore rewrote `tools/playground.py`, and it took 47.8 s instead of 9–14 s, the pattern of KI-018 (`npm run dev` silent after a rewrite). Recorded under KI-018. Not reproduced in 7 runs.
