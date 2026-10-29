# Plan: 070-02-01 플레이그라운드 `--port`를 페이지 포트로

## Prior Round Reference
- Original spec: [/docs/specs/070_02_web_playground.md](/docs/specs/070_02_web_playground.md)
- Original artifacts: [/docs/tasks/feature_070-02-web-playground/walkthrough.md](/docs/tasks/feature_070-02-web-playground/walkthrough.md)
- Reason for reopen: KI-017. `--dev --port 9000` moved only the API server; the page stayed on 5173.

- Spec: [/docs/specs/070_02_01_playground_port.md](/docs/specs/070_02_01_playground_port.md) (approved 2026-10-29)
- Branch: `feature/070-02-01-playground-port` (from `main` at `7f4537c`)

## Design
- `launch_plan(port, dev)` returns (server port, extra server arguments, Vite port). Serve mode: `(port or 8765, [], None)`. Dev mode: `(0, --allow-origin for 127.0.0.1 and localhost on the page port, page port)`, page port = `free_port(port or 5173)`.
- `free_port(first, tries=20)` binds `127.0.0.1` on the host (where Vite runs) to find the first free port.
- Vite gets the port on its command line (`npm run dev -- --port N`); `strictPort` stays, so a port taken after the check makes Vite fail instead of moving silently.
- `wait_any(procs)`: the launcher ends when the server or Vite ends (before, a failed Vite left the launcher waiting on the server).
- Checked before writing: an API server started in WSL with `--port 0` answers from Windows (`/api/health` on port 34789).

## Units
| # | Unit | Files | Risky | Author | Reviewer | State |
|---|---|---|---|---|---|---|
| U1 | port plan, Vite port, wait for either child | `tools/playground.py` | no | lead | `cpp-reviewer` | done |
| U2 | tests (unit + real launch) | `tools/test_playground.py` | no | lead | `cpp-reviewer` | done |
| U3 | docs | `web/README.md`, `.vscode/tasks.json`, `web/frontend/vite.config.ts`, `docs/known_issues.md`, spec 070-02 History | no | lead | `cpp-reviewer` | done |

## Changes after review
- `free_port` sets `SO_REUSEADDR` on Linux (as libuv does) and stops at 65535.
- `--port` range check with `parser.error`; `None` (not 0) means "not given", so serve-mode `--port 0` still reaches the server.
- Tests: `WaitAnyTest` (fake processes), Origin checks through Vite, TIME_WAIT test, Node 20+ skip, launcher output on failure.
