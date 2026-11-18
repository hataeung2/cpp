# Test record 090-14: CI 도입

Spec: [090_14_ci.md](/docs/specs/090_14_ci.md). Plan: [plan.md](plan.md).

## Runs
| # | Where | Commit | Result | Notes |
|---|---|---|---|---|
| L1 | local `linux-x64-debug --test --report out/test-reports/local-090-14` (WSL, Clang 20.1.2) | working tree with U1 (the report header says `3c87d45`, HEAD when it was written) | exit 0, 67/67 | baseline for AC-3: unit 4, scenario 3, probe 12, lesson 48 (long 4, playground 1 are extra labels on the same tests); 257.8 s of tests |
| L2 | local `test_agent_scripts.py`, `lint_docs.py` | branch | OK; 0 errors | new test fails with `.github` removed from `DOC_DIRS` (mutation check) |
| G1 | GitHub run 44205965419 | `96fed89` | failure | `docs` success; `linux-debug` failed in the build step. Logs need a sign-in (REST `jobs/<id>/logs` 403); led to the annotation steps |
| G2 | GitHub run 44206287239 | `3c87d45` | failure | annotation: `/usr/local/bin/cmake cmake version 3.31.6`, `"cmakeMinimumRequired" major version 4 must be less than 3` (reviewer's finding confirmed) |
| G3 | GitHub run 44206913413 | `ea48da3` | **success** | `/usr/bin/cmake cmake version 4.5.0`; `linux-debug` 5 min 48 s, `docs` 6 s |
| G4 | GitHub run 44207818256 | `b09dd24` | **success** | `linux-debug` 6 min 57 s (00:26:27–00:33:24), `docs` 10 s; label table (notice annotation): unit 4/4, scenario 3/3, probe 12/12, lesson 48/48, long 4/4, playground 1/1, all 67/67, 257.7 s of tests |
| G5 | GitHub run 44207878893, branch `feature/090-14-ci-probe` | `5af52de` (broken link + `CiProbe.MustFail`) | **failure** (intended) | `docs` failure; `linux-debug` failure, exit 8, `AllTests (Failed)`, unit 4 / 3 passed / 1 failed, all other labels pass, 67 tests; artifact `test-report-linux-x64-debug` 42,827 bytes. Branch deleted on the remote and locally |

## Acceptance criteria
| AC | Criterion | Evidence | Result |
|---|---|---|---|
| AC-1 | workflow file, two jobs, triggers, `contents: read`, SHA-pinned GitHub actions only | [`ci.yml`](/.github/workflows/ci.yml) review (cpp-reviewer U2: triggers, permissions, concurrency, pins match); `grep -c "uses: actions/.*@[0-9a-f]\{40\} # v"` = 3 = all `uses:` lines | pass |
| AC-2 | install steps = linux_build_setup.md §1–§3 | cpp-reviewer U2: packages and Kitware key/repository character-identical (§1 and §3 in one apt line). Plus one CI-only `PATH` step, documented in config.md §6 and the guide | pass |
| AC-3 | both jobs succeed on the task branch; every label runs | G3, G4 success; G4 table equals L1 per label (unit 4, scenario 3, probe 12, lesson 48; 67 in all), none not run. Job time about 6–7 min without caches (Assumption 7: no KI needed) | pass |
| AC-4 | (a) docs gate error fails `docs`; (b) failing unit test fails `linux-debug`, report uploaded | G5: `docs` failure in step `lint_docs` (self-tests skipped after it), `linux-debug` failure with `AllTests (Failed)` in the build-output annotation, report annotation present; artifact `test-report-linux-x64-debug` uploaded (42,827 bytes) | pass |
| AC-5 | CI succeeds on `main` after the merge | checked after the merge on the run of `main`'s push; recorded in Revision 1 below | see Revision 1 |
| AC-6 | `.github/` machine path is an ERROR | `LintDocsTest.test_machine_path_in_ci_workflow` (L2), fails without the change | pass |
| AC-7 | `lint_docs.py` exit 0; KI-024 CLOSED; follow-ups registered | KI-024 CLOSED (090-14); KI-055 (MSVC), KI-056 (sanitizers), KI-057 (web tests) DEFERRED, moved by `archive_docs.py`; `lint_docs.py`: 0 errors, 0 warnings, exit 0 | pass |

## Deviations from the spec
- Job `docs` has no separate `sync_skills.py --check` step (§2.2): `lint_docs.py` already runs `sync_skills.check`.
- CI-only steps not in §2.2: `/usr/bin` first on `PATH`, three annotations, `out/ci-build.log` in the artifact (plan Design notes, config.md §6).
- AC-4 used one commit with both breakages on `feature/090-14-ci-probe`, not two commits on `ci-probe/090-14`: the push trigger matches `feature/**`, and the two jobs run in parallel, so one run checks (a) and (b).

## Reviews
| Unit | Reviewer | Question | Findings | Resolution |
|---|---|---|---|---|
| U1 | cpp-reviewer | can the test pass trivially; false `.yml` errors? | none | — |
| U2 | cpp-reviewer | does `ci.yml` match §2.2, AC-1, AC-2; what fails on a clean runner? | (1) image's CMake 3.x in `/usr/local/bin` shadows CMake 4; (2) no `sync_skills` step; (3) two comment lines | (1) confirmed by G2, fixed (`GITHUB_PATH`); (2) kept, the gate is the same; (3) kept, cosmetic |
| U3 | cpp-reviewer | do the docs say what `ci.yml` does; §8 rows; KI form | (1) config.md §6 missed annotations and `ci-build.log`; (2) guide said "unchanged"; (3) KIs not archived yet | (1), (2) fixed; (3) `archive_docs.py` at the end |

Cross-family review: none. All reviews are `cpp-reviewer` (Claude, the lead's family); no unit was risky (delegation.md §1).

## Revision 1 — 2026-11-17 (after the merge)
| AC | Evidence | Result |
|---|---|---|
| AC-5 | GitHub run 44213135152 on `main` (`0ff591c`, the merge commit): `docs` success (14 s), `linux-debug` success (6 min 42 s) | pass |
