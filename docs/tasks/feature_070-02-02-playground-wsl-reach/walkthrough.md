# Walkthrough: 070-02-02 플레이그라운드가 WSL 서버에 닿지 않을 때 알려 주기

- Spec: [/docs/specs/070_02_02_playground_wsl_reach.md](/docs/specs/070_02_02_playground_wsl_reach.md)
- Plan: [plan.md](/docs/tasks/feature_070-02-02-playground-wsl-reach/plan.md)
- Test record: [testrecord.md](/docs/tasks/feature_070-02-02-playground-wsl-reach/testrecord.md)

## Result
- On Windows `tools/playground.py` checks, after the server reports its address and before Vite starts, that `/api/health` answers from Windows. If it does not within 10 s, it prints `error: Windows cannot reach the API server in WSL at <url> (WSL localhost forwarding is not working). Run "wsl --shutdown", then start the playground again.`, stops the server and exits 1. Both modes; Linux is not checked.
- `web/README.md` names the error and the fix. KI-040 closed.

## Agents
Lead (small) wrote the code, tests and docs; agy argon reviewed twice (3 findings, then none).

## Follow-ups
- KI-018: one launch-test failure after a rewrite of `tools/playground.py`, output not kept.
