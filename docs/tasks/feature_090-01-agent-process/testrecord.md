# Test Record: 090-01 에이전트 운영 규칙 개선

## Acceptance Criteria Evidence
| AC | Evidence | Result |
|---|---|---|
| AC-1 | `wc -l`: `CLAUDE.md` 5, `AGENTS.md` 3, `docs/agent_start_prompt.md` 50 (≤ 80). `grep -c docs/agent_start_prompt.md` = 1 in each entry file | Pass |
| AC-2 | `grep -rnE "cmake -S\|-B build\|--build build" .agent docs/specs/00_template.md docs/agent_start_prompt.md`: 3 hits, all inside prohibitions (`config.md:132` "do NOT run", `test.md:32` "Never configure ad hoc", `agent_start_prompt.md:35` "No ad-hoc") | Pass |
| AC-3 | `lint_docs.py`: 0 machine-path ERRORs in rules, entry files, docs and `CMakePresets.json` (19 INFO, all in sealed legacy task records). `CMakePresets.example.json` deleted; KI-004 CLOSED. Remaining: PQXX-only path in `CMakeLists.txt` (KI-009, option off by default) | Pass |
| AC-4 | `grep -c` on `00_template.md`: `approved: null`, Assumptions, Acceptance Criteria, Out of Scope, Documentation Updates = 1 each | Pass |
| AC-5 | `lint_docs.py`: todo grammar, unique ids, `(k/n DONE)` counts, spec links and approval states — 0 ERROR; `--status` lists 49 tasks (BACKLOG 35, SPEC_DRAFT 3, DEV 1, DONE 10) | Pass |
| AC-6 | `delegation.md` §1 (작성자/검토자), §3 (C++ 위험 목록), §4 (프롬프트 규칙); 워크플로 4·5단계가 §1, §6.2, §9를 참조. Step 3 review by agy `flash` (Reviews) | Pass |
| AC-7 | `diagrams.md` §2 (generator budget), §3 (viewer policy), §4 (docs limit); spec 020-04 §2 implements §1–§2 and its AC-1–AC-10 cover them (agy review (b) after fixes); 020-04 is `SPEC_DRAFT`, awaiting user approval | Pass |
| AC-8 | lint exit 0; `linux-x64-debug`, `linux-x64-asan`, `linux-x64-tsan` build with warnings as errors and pass the full suite in WSL; hook refuses ad-hoc configure, commit on `main` (simulated) and machine-path writes, and fired live in this session; 45 script tests pass on Windows (Python 3.15) and WSL (3.12), after two review rounds. Windows build stops at Boost (KI-007) | Pass for Linux; Windows open (KI-007) |
| AC-9 | Spec §11 lists B-1–B-14 | Pass |

## Runs

### 2026-10-28 — Steps 1–2 document checks
- Commands: see the evidence column above (Git Bash).
- No build or test run: Steps 1–2 change documents only.

### 2026-10-28 — Step 3
| Test | Expected | Actual | Status |
|---|---|---|---|
| `py -3 .agent/scripts/test_agent_scripts.py` | 24 copied `SubagentRunTest` cases pass | `Ran 24 tests ... OK` | Pass |
| agy smoke call: `subagent_run.py --model flash --read-only`, "how many static member functions does `MermaidFormatter` declare?" | exit 0, answer 3 (`sequence_diagram`, `state_diagram`, `class_tree`) | exit 0, the same 3 names; 46,807 input / 775 output tokens, 13 s | Pass |

### 2026-10-28 — Step 5
| Test | Expected | Actual | Status |
|---|---|---|---|
| WSL raw run of `linux-x64-debug` / `-asan` / `-tsan` (first attempt) | configure, build, test | debug: copied `_deps/googletest-subbuild` cache from `/mnt/e/cpp` broke `--fresh`; asan: transient `file RENAME ... Permission denied` on `/mnt/c`; tsan: built with `-Werror` cleanly, tests aborted with `ThreadSanitizer: unexpected memory mapping` | Fail → fixed below |
| Fixes | — | `build.py` removes build directories whose caches were recorded elsewhere (all `CMakeCache.txt`, incl. sub-builds) and re-runs interrupted configures; TSan tests run under `setarch x86_64 -R` (`tests/CMakeLists.txt`) | — |
| `py -3 .agent/scripts/build.py --preset linux-x64-tsan --test` (Windows → WSL) | build, 0 warnings, tests pass | `100% tests passed, 0 tests failed out of 1` | Pass |
| `... --preset linux-x64-asan --test` | same | `100% tests passed` | Pass |
| `... --preset linux-x64-debug --test` | stale directory removed, then build and test | "build directory was made at another location ... removing", `100% tests passed` | Pass |
| `... --preset windows-x64-debug --test` | configure with MSVC | MSVC 19.51 found via vswhere/VsDevCmd; `atugcc: vcpkg toolchain from VCPKG_ROOT` (VS bundled vcpkg); `Could not find ... "Boost"`; build.py exit 1 | Blocked: KI-007 |
| `py -3 .agent/scripts/lint_docs.py` | exit 0 | `0 error(s), 0 warning(s), 19 info` | Pass |
| `py -3 .agent/scripts/test_agent_scripts.py` (Windows) and `python3 ...` (WSL) | all pass | `Ran 39 tests ... OK` on both | Pass |
| guard.py pipe tests (11 cases: preset/build allowed, `-S`/`..` denied, commit on feature allowed, machine paths denied, prohibition text, URL, ignored file, outside repo allowed, bad JSON fails open) | as listed | as listed; commit on `main` denied in a simulated run | Pass |
| Live hook | a matching tool call is refused | refused a Bash call whose heredoc contained an ad-hoc configure string (false positive, KI-008) | Pass (fires) |

## Reviews
| Unit | Reviewer | Question | Findings | Resolution |
|---|---|---|---|---|
| Step 3 docs (`delegation.md`, workflow, `test.md`) | agy `flash` (65,773 in / 20,398 out, 164 s). `cpp-reviewer` was planned but is not loadable in the session that created it (agent definitions load at session start) | contradictions / gaps in author-reviewer split, AC source, cross-references, unit-table columns | (a, c) workflow step 4.2 sent every review to `§6.2`, which is the risky-unit chain; (b) none; (d) workflow step 4.4 omitted the Reviewer and Tokens columns | Both fixed in the workflow (4.2 now cites §1 + §6.2 + §6.3; 4.4 lists reviewer, findings, tokens, status) |
| Step 4 docs (`diagrams.md`, spec 020-04) | agy `flash` (38,015 in / 17,363 out, 127 s) | rule–spec contradictions, rule requirements without an AC, AC conflicts, accuracy of the spec's description of `mermaid_formatter.hpp` | (a) `DiagramPart` lacked the backend field the rule names; (b) five rule requirements had no AC: participant union, over-budget note in source, `(k/n)` titles for structure and unsplit titles, `formatDiagram` joining split parts, every-backend coverage for AC-5/AC-6; (c) AC-5 "all relations in one part" read as contradicting the split; (d) none | All fixed: `backend` field; AC-2, AC-4, AC-5, AC-6, AC-7 extended, AC-10 added; AC-5 reworded to "exactly one part"; unsplittable structure node → `overBudget` added to spec §2.2, §4 and rule §2 |
| Step 5 scripts (`agent_common.py`, `lint_docs.py`, `build.py`, `guard.py`) — round 1 | `cpp-reviewer` (first use; 65k tokens, 4.8 min). An earlier agy `flash` call was lost when the session window closed | defects against each script's docstring: rule-breaking input passing, valid input erroring, crash, wrong reuse/deletion of build dirs, lost exit codes, guard bypass | 26 findings, among them: JSON-escaped drive paths not matched; any line with "no"/"not" exempt; DONE spec without frontmatter silently sealed; non-ID artifact dirs sealed; missing `---` parsed zero tasks without error; non-`- ` task lines skipped; patch ids unchecked; impossible dates accepted; quoted non-ASCII paths dropped; BOM hides frontmatter; titles with brackets; percent-encoded links; non-UTF-8 crash; presets changes ignored; junction/subst path deleted as "copied"; case-folding on Linux; unguarded `rmtree`; `if errorlevel 1` misses negative crash codes; Edit result lines unchecked; stdin code page; import failure not fail-open | All reworked; 6 new regression tests (44 total) |
| Same — round 2 (final, delegation.md §6.3) | `cpp-reviewer` (95k tokens) | is each round-1 finding fixed; did the rework add defects | 17 fixed; partly fixed: code-span exemption still allowed `` `VAR=<drive>/x` ``, `legacy` matched in the title, patch placement and indented non-patches, a variable removed from a preset persists; new: KI refs kept only the first occurrence (sealed-first hid an unsealed ERROR), copying an existing offending line passed the guard, `build.py` docstring out of date | All fixed except the removed-variable case, which is documented (`build.py` docstring, config.md §5: use `--fresh`). Round-3 fixes were not reviewed again (§6.3: one round); each is covered by a regression test (45 tests pass on Windows and WSL) |
