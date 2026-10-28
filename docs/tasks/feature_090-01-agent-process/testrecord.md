# Test Record: 090-01 에이전트 운영 규칙 개선

## Acceptance Criteria Evidence
| AC | Evidence | Result |
|---|---|---|
| AC-1 | `wc -l`: `CLAUDE.md` 5, `AGENTS.md` 3, `docs/agent_start_prompt.md` 50 (≤ 80). `grep -c docs/agent_start_prompt.md` = 1 in each entry file | Pass |
| AC-2 | `grep -rnE "cmake -S\|-B build\|--build build" .agent docs/specs/00_template.md docs/agent_start_prompt.md`: 3 hits, all inside prohibitions (`config.md:132` "do NOT run", `test.md:32` "Never configure ad hoc", `agent_start_prompt.md:35` "No ad-hoc") | Pass |
| AC-3 | Rules and entry files: 2 hits, both prohibitions (`impl.md:57`, `agent_start_prompt.md:34`). `CMakePresets.json` and `CMakePresets.example.json` still hold machine paths (KI-004) | Partial — Step 5 |
| AC-4 | `grep -c` on `00_template.md`: `approved: null`, Assumptions, Acceptance Criteria, Out of Scope, Documentation Updates = 1 each | Pass |
| AC-5 | 49 task lines; 0 lines outside the grammar regex `^\s*- !(BACKLOG\|SPEC_DRAFT\|APPROVED\|DEV\|TEST\|DONE\|BLOCKED) \| NNN-SS(-PP)? \| `; 0 duplicate IDs | Pass (lint script in Step 5) |
| AC-6 | — | Step 3 |
| AC-7 | — | Step 4 |
| AC-8 | — | Step 5 |
| AC-9 | Spec §11 lists B-1–B-4 | Pass (extended per step) |

## Runs

### 2026-10-28 — Steps 1–2 document checks
- Commands: see the evidence column above (Git Bash).
- No build or test run: Steps 1–2 change documents only.
