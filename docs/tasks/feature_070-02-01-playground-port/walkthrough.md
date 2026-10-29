# Walkthrough: 070-02-01 플레이그라운드 `--port`를 페이지 포트로

- Spec: [/docs/specs/070_02_01_playground_port.md](/docs/specs/070_02_01_playground_port.md) (amends [070-02](/docs/specs/070_02_web_playground.md))
- Evidence: [testrecord.md](/docs/tasks/feature_070-02-01-playground-port/testrecord.md) (AC-1–AC-4 all Pass)
- Branch: `feature/070-02-01-playground-port`, merged into `main` by fast-forward

## Result
- `py -3 tools/playground.py --dev --open --port 9000` opens the hot-reload page on `127.0.0.1:9000`. `--port` is the page port in both modes (default 8765, with `--dev` 5173); a busy port moves on to the next free one of 20.
- With `--dev` the API server takes any free port; the page reaches it only through the Vite proxy, and the server allows exactly the page's origins.
- The launcher ends when either the server or Vite ends, and stops the other (before, a Vite that failed left the launcher waiting).
- `--port` out of range is a usage error; `--port 0` in serve mode still means "any free port".
- [`tools/test_playground.py`](/tools/test_playground.py): 17 tests, two of them start the real playground (Windows host with the server in WSL, and Linux directly). 12 mutants killed.

## Notes
- On Linux the free-port check sets `SO_REUSEADDR` like Vite's own bind, so a port left in TIME_WAIT by the last run is reused instead of moving the page (review finding).
- `DevLaunchTest` skips on Node < 20 (WSL here has 18.19).

## Follow-ups
- KI-017: closed.
- KI-018 (new): `npm run dev` printed nothing for 30 s in two runs of the launch test; cause not found, diagnostics added to the test.
