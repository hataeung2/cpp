# Walkthrough: 090-14 CI

- Spec: [/docs/specs/090_14_ci.md](/docs/specs/090_14_ci.md) (approved 2026-11-17)
- Plan: [plan.md](plan.md), test record: [testrecord.md](testrecord.md)
- Branch: `feature/090-14-ci`

## Result
Every push to `main` and `feature/**`, every pull request, and a manual run start [`.github/workflows/ci.yml`](/.github/workflows/ci.yml) on GitHub Actions:
- `docs`: `lint_docs.py` (the docs gate with the skill copies and the lesson manifests) and `test_agent_scripts.py`, about 10 s.
- `linux-debug`: the toolchain of [linux_build_setup.md](/docs/guides/linux_build_setup.md) on `ubuntu-24.04`, then `build.py --preset linux-x64-debug --test --report`: all 67 tests (unit, scenario, probe, lesson), about 6–7 min without caches. The report and the build output are uploaded as an artifact.

Two things the first runs showed, now in [config.md](/.agent/rules/config.md) §6:
- The runner image has its own CMake 3.31 in `/usr/local/bin`, ahead of the Kitware CMake 4 on `PATH`. The workflow puts `/usr/bin` first. The reviewer predicted this before the run.
- Run logs and artifacts need a GitHub sign-in, and `gh` is not installed here. So the workflow writes what a reader needs as annotations, which the public REST API returns: the cmake path and version, the report's results by label, and on failure the last 60 lines of the build output.

A probe branch with a broken link and a failing unit test failed both jobs (AC-4) and was deleted.

The docs gate now also checks `.github/` (and `.yml` files) for machine paths.

## Units
U1–U3 `done` (plan.md), all `lead (small)` or lead docs, reviewed by `cpp-reviewer`. No `lead (fallback)` units. No cross-family review: no unit was risky.

## Follow-ups
- KI-024 CLOSED by this task.
- KI-055 (DEFERRED): Windows MSVC job.
- KI-056 (DEFERRED): `asan` / `tsan` jobs.
- KI-057 (DEFERRED): web playground tests in CI.
- Not a KI: the unauthenticated REST API allows 60 requests an hour. Polling for run results used it up once in this task; install `gh` (and sign in) to read logs and artifacts directly.
