# Test Record: 090-01 에이전트 운영 규칙 개선

## Acceptance Criteria Evidence
| AC | Evidence | Result |
|---|---|---|
| AC-1 | `wc -l`: `CLAUDE.md` 5, `AGENTS.md` 3, `docs/agent_start_prompt.md` 50 (≤ 80). `grep -c docs/agent_start_prompt.md` = 1 in each entry file | Pass |
| AC-2 | `grep -rnE "cmake -S\|-B build\|--build build" .agent docs/specs/00_template.md docs/agent_start_prompt.md`: 3 hits, all inside prohibitions (`config.md:132` "do NOT run", `test.md:32` "Never configure ad hoc", `agent_start_prompt.md:35` "No ad-hoc") | Pass |
| AC-3 | Rules and entry files: 2 hits, both prohibitions (`impl.md:57`, `agent_start_prompt.md:34`). `CMakePresets.json` and `CMakePresets.example.json` still hold machine paths (KI-004) | Partial — Step 5 |
| AC-4 | `grep -c` on `00_template.md`: `approved: null`, Assumptions, Acceptance Criteria, Out of Scope, Documentation Updates = 1 each | Pass |
| AC-5 | 49 task lines; 0 lines outside the grammar regex `^\s*- !(BACKLOG\|SPEC_DRAFT\|APPROVED\|DEV\|TEST\|DONE\|BLOCKED) \| NNN-SS(-PP)? \| `; 0 duplicate IDs | Pass (lint script in Step 5) |
| AC-6 | `delegation.md` §1 (작성자/검토자), §3 (C++ 위험 목록), §4 (프롬프트 규칙); 워크플로 4·5단계가 §1, §6.2, §9를 참조 (`grep -c "delegation.md" start-develop-one-task.md` = 3). `cpp-reviewer` 리뷰 결과는 Reviews 참조 | Pass |
| AC-7 | `diagrams.md` §2 (generator budget), §3 (viewer policy), §4 (docs limit); spec 020-04 §2 implements §1–§2 and its AC-1–AC-10 cover them (agy review (b) after fixes); 020-04 is `SPEC_DRAFT`, awaiting user approval | Pass |
| AC-8 | — | Step 5 |
| AC-9 | Spec §11 lists B-1–B-4 | Pass (extended per step) |

## Runs

### 2026-10-28 — Steps 1–2 document checks
- Commands: see the evidence column above (Git Bash).
- No build or test run: Steps 1–2 change documents only.

### 2026-10-28 — Step 3
| Test | Expected | Actual | Status |
|---|---|---|---|
| `py -3 .agent/scripts/test_agent_scripts.py` | 24 copied `SubagentRunTest` cases pass | `Ran 24 tests ... OK` | Pass |
| agy smoke call: `subagent_run.py --model flash --read-only`, "how many static member functions does `MermaidFormatter` declare?" | exit 0, answer 3 (`sequence_diagram`, `state_diagram`, `class_tree`) | exit 0, the same 3 names; 46,807 input / 775 output tokens, 13 s | Pass |

## Reviews
| Unit | Reviewer | Question | Findings | Resolution |
|---|---|---|---|---|
| Step 3 docs (`delegation.md`, workflow, `test.md`) | agy `flash` (65,773 in / 20,398 out, 164 s). `cpp-reviewer` was planned but is not loadable in the session that created it (agent definitions load at session start) | contradictions / gaps in author-reviewer split, AC source, cross-references, unit-table columns | (a, c) workflow step 4.2 sent every review to `§6.2`, which is the risky-unit chain; (b) none; (d) workflow step 4.4 omitted the Reviewer and Tokens columns | Both fixed in the workflow (4.2 now cites §1 + §6.2 + §6.3; 4.4 lists reviewer, findings, tokens, status) |
| Step 4 docs (`diagrams.md`, spec 020-04) | agy `flash` (38,015 in / 17,363 out, 127 s) | rule–spec contradictions, rule requirements without an AC, AC conflicts, accuracy of the spec's description of `mermaid_formatter.hpp` | (a) `DiagramPart` lacked the backend field the rule names; (b) five rule requirements had no AC: participant union, over-budget note in source, `(k/n)` titles for structure and unsplit titles, `formatDiagram` joining split parts, every-backend coverage for AC-5/AC-6; (c) AC-5 "all relations in one part" read as contradicting the split; (d) none | All fixed: `backend` field; AC-2, AC-4, AC-5, AC-6, AC-7 extended, AC-10 added; AC-5 reworded to "exactly one part"; unsplittable structure node → `overBudget` added to spec §2.2, §4 and rule §2 |
