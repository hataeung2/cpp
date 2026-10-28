# Walkthrough: 090-01 에이전트 운영 규칙 개선

- Spec: [/docs/specs/090_01_agent_process.md](/docs/specs/090_01_agent_process.md)
- Plan: [plan.md](./plan.md) · Tests and reviews: [testrecord.md](./testrecord.md)
- Branch: `feature/090-01-agent-process` (5 commits, one per step), fast-forwarded into `main` on 2026-10-28 at the user's request (KI-003 closed)

## Result
| Step | Delivered |
|---|---|
| 1 | `CLAUDE.md` / `AGENTS.md` → one boot file ([agent_start_prompt.md](/docs/agent_start_prompt.md)); rule contradictions removed; camelCase confirmed |
| 2 | Spec template with `approved`, Assumptions, `AC-n`, Out of Scope, Documentation Updates; `NNN-SS` ids and 7 states in the todo; [known_issues.md](/docs/known_issues.md) |
| 3 | [delegation.md](/.agent/rules/delegation.md): risk-based authorship, C++ risk list, cross-review; `subagent_run.py` copied from ai_sec; `cpp-reviewer` agent; workflow with unit table and Tester stage |
| 4 | [diagrams.md](/.agent/rules/diagrams.md): generator budget, viewer policy, docs limit; spec 020-04 drafted (awaiting approval) |
| 5 | `lint_docs.py`, `build.py`, guard hook, sanitizer and warnings-as-errors presets, portable `CMakePresets.json` |

Final outcome: all acceptance criteria pass for Linux; the Windows build stops at Boost (KI-007). Details in [testrecord.md](./testrecord.md).

## Cross-checks that changed the result
- agy `flash` reviews of Steps 3 and 4 found 2 workflow gaps and 7 spec issues; all fixed.
- `cpp-reviewer` reviewed the Step 5 scripts twice (26 + 10 findings); all fixed or documented. Round-3 fixes are covered by regression tests, not by a third review (delegation.md §6.3).
- Real builds found what reading could not: a copied `out/` from another checkout, a TSan/ASLR abort, and the VS-bundled vcpkg taking over `VCPKG_ROOT`.

## Back-port list for ai_sec
Spec §11, B-1 to B-14.

## Follow-ups
- KI-003: `main` is behind; fast-forward is the user's decision.
- KI-007: Windows Boost supply (manifest, standalone vcpkg, or system prerequisite) is the user's decision.
- KI-008: the command hook matches text inside quoted strings.
- KI-009: PostgreSQL include path behind the PQXX option.
- KI-001, KI-002, KI-005, KI-006: planned or informational.
- Next tasks: 090-02 (camelCase rename), 020-04 (diagram readability, spec awaiting approval).
