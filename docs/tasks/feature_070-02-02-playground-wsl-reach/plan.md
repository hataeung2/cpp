# Plan: 070-02-02 플레이그라운드가 WSL 서버에 닿지 않을 때 알려 주기

## Prior Round Reference
- Original spec: [/docs/specs/070_02_web_playground.md](/docs/specs/070_02_web_playground.md)
- Original artifacts: [/docs/tasks/feature_070-02-web-playground/walkthrough.md](/docs/tasks/feature_070-02-web-playground/walkthrough.md)
- Reason for reopen: KI-040. WSL localhost forwarding stopped (`wslrelay.exe` not running) and the launcher still started as if all was well; the user saw only Vite proxy `ECONNREFUSED` lines.

- Spec: [/docs/specs/070_02_02_playground_wsl_reach.md](/docs/specs/070_02_02_playground_wsl_reach.md) (approved 2026-11-04)
- Branch: `feature/070-02-02-playground-wsl-reach` (from `main` at `a5412d9`)

## Design
- `reachable(url, server, wait=10)`: GET `url` without the system proxy; any HTTP response (an error status too) counts. A failed connect is retried every 0.25 s until the deadline; each attempt's timeout and each sleep are clamped to the time left, so no attempt starts after the deadline. A server that ends stops the wait.
- `main`: on Windows only, after `start_server` and before Vite, check `<url>api/health`. Unreachable: the server's exit code if it ended, else the §2.1 error and exit 1; `finally` stops the server.
- Checked before writing: with `wslrelay.exe` missing, a WSL server on `127.0.0.1` (port 37639 from `--port 0`, and a fixed 8799) did not answer from Windows; inside WSL `ss -ltn` showed it listening.

## Units
| # | Unit | Files | Risky | Author | Reviewer | State |
|---|---|---|---|---|---|---|
| U1 | reach check in the launcher | `tools/playground.py` | no | lead (small) | agy argon | done |
| U2 | tests | `tools/test_playground.py` | no | lead (small) | agy argon | done |
| U3 | docs | `web/README.md`, `docs/known_issues.md`, spec 070-02 History, `docs/tasks/agent_todo.md` | no | lead (small) | — | done |

U1 and U2 are one function and its tests (delegation.md §1, small change). Review fixes: `review fixes lead (small)`, checked once more by argon.

## Changes after review
- Attempt timeout and sleep clamped to the time left (a refused connect on Windows loopback takes about 1 s, so `wait=10` could run to about 11 s).
- New tests: late answer after failed attempts, closed port within `wait + 0.5`, system proxy ignored, serve mode checked too.
