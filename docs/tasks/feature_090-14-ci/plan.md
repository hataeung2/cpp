# Plan 090-14: CI 도입

Spec: [090_14_ci.md](/docs/specs/090_14_ci.md) (approved 2026-11-17). Branch `feature/090-14-ci`.

## Files
- [NEW] `.github/workflows/ci.yml` — job `docs`, `linux-debug` (AC-1, AC-2, AC-3)
- [MODIFY] `.agent/scripts/lint_docs.py` — `.github` in `DOC_DIRS`, `.yml` in `PATH_CHECKED_SUFFIXES` (AC-6)
- [MODIFY] `.agent/scripts/test_agent_scripts.py` — `test_machine_path_in_ci_workflow` (AC-6)
- [MODIFY] docs of spec §8: `config.md`, `test.md`, `linux_build_setup.md`, `README.md`, `known_issues.md`

C++20/23 features: none (no C++ change). Evolution pages: none.

## Design notes
- Spec §2.2 lists `sync_skills.py --check` as its own step in job `docs`. `lint_docs.py` already runs `sync_skills.check` (and `tools/lessons.py check`), so the job has two steps, not three: the same check twice would only be noise. The gate is unchanged.
- Action SHAs (looked up 2026-11-17 from the GitHub API, latest release): `actions/checkout` v7.0.1 `3d3c42e5aac5ba805825da76410c181273ba90b1`, `actions/upload-artifact` v7.0.2 `cf430e030ddbb5b0abf93d22962f4752f3646cd9`.
- AC-4 probe branch: the spec names `ci-probe/090-14`, but the push trigger matches only `main` and `feature/**`, and `workflow_dispatch` needs `gh` or the web page. The probe commits go on `feature/090-14-ci-probe` instead (same purpose, matched by `feature/**`); it is deleted on the remote and locally after the check.

## Units
| Unit | File | Change (what, where, AC) | Check | Risky | Author | Reviewer | Tokens (in / out) | Status |
|---|---|---|---|---|---|---|---|---|
| U1 | `.agent/scripts/lint_docs.py`, `test_agent_scripts.py` | `.github` + `.yml` in the machine-path scan, one test (AC-6) | `test_agent_scripts.py` OK; the new test fails with `.github` removed from `DOC_DIRS`; `lint_docs.py` 0 errors | no | lead (small) | cpp-reviewer | — | done |
| U2 | `.github/workflows/ci.yml` | workflow per spec §2.2 (AC-1, AC-2) | `grep -c "uses: actions/.*@[0-9a-f]\{40\}"` = 3; diff against linux_build_setup.md §1–§3; first GitHub run (AC-3) | no | lead (small) | cpp-reviewer | — | |
| U3 | docs (spec §8) | config.md §6 CI, test.md §4 and §6, linux_build_setup.md, README badge, KIs | `lint_docs.py` 0 errors | no | lead | cpp-reviewer | — | |

`lead (small)`: U1 is two constants and one test; U2's prompt would carry the whole file (the design fixes every line).
