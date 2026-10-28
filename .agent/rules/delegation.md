---
trigger: model_decision
description: When splitting a task into units, delegating code or investigation to a sub-agent, or asking for a review
---

# Sub-Agent Delegation & Cross-Review Rules (atugcc)

**Principle: the author of a change never verifies it alone.** Every delivered change (code, test, doc) is checked once by an agent that did not write it, and every unit passes a mechanical check (build, test, grep) run by the lead.

The **lead** (the agent the user talks to) designs, splits the work into units, runs every check, moves task states and commits. Sub-agents write drafts and review. Machine checks (both compilers, sanitizers, the full suite) are the strongest verifier in C++; model review covers what they cannot see (spec conformance, design, missing cases).

## 1. Who writes and who reviews

| Unit | Author | First-pass reviewer | Final check |
|---|---|---|---|
| **Ordinary** | lead | `cpp-reviewer` (Claude sub-agent, fresh context, read-only, §8) or agy `flash` | lead's per-unit check |
| **Risky** (§3) | agy, implementer chain §6.1 | codex, reviewer chain §6.2 (different model family from the author) | lead's per-unit check |

- Mark each unit `Risky: yes/no` in the plan's unit table **before** the first call.
- A risky unit the lead had to write itself (`lead (fallback)`) is reviewed by codex, or agy when codex is out.
- No sub-agent available: the lead writes and `cpp-reviewer` reviews; record "no cross-family review" in `testrecord.md` and tell the user.

## 2. Investigation (reading)
- Understanding the cause or structure needs **3 or more files**, or a whole module: ask a read-only sub-agent first (Claude Code's built-in `Explore` agent, or agy `flash --read-only`). The lead fills in only what the answer leaves out.
- **Do not delegate one- or two-function lookups.** An agy call costs about 45k input tokens even for a one-line question (measured 2026-10-28: 46,807 input tokens to count three functions in one header).
- Separate facts from judgment: sub-agents return facts (quotes, call sites, condition lists); the lead draws the conclusion.

## 3. Risky units (C++)
A unit is risky if it touches any of:
- atomics, `memory_order`, locks, condition variables, thread lifetime (`std::jthread`, stop tokens);
- object lifetime and ownership: views that can dangle (`std::string_view`, `std::span`, iterators, references stored in members), `shared_ptr` cycles, moved-from use;
- a public header in `include/atugcc/` whose API or ABI changes;
- header-only `inline` definitions, static locals, templates instantiated in several TUs (ODR);
- platform branches (`#ifdef _WIN32`, Win32 / POSIX calls);
- casts and memory layout (`reinterpret_cast`, `std::bit_cast`, alignment, packed structs);
- signal or crash handlers (async-signal-safety, `memory_dump`);
- two or three files that must change together.

## 4. How to call a sub-agent
- agy / codex: `py -3 .agent/scripts/subagent_run.py --model <alias> --prompt-file <file> [--read-only] [--effort <level>] [--resume <id>] [--files <path> ...]` (Linux: `python3`).
  - The prompt file lives in the lead's scratch directory, outside the repo. Absolute paths appear only in run-time arguments, never in committed files.
  - `--read-only` for research and review; codex always runs read-only (the script refuses otherwise).
  - `--resume <id>` sends review findings or a rejection back to the same implementer conversation.
- `cpp-reviewer`: the Agent tool with `subagent_type: cpp-reviewer` (§8).
- **Every prompt states:**
  - "Not found / cannot confirm" is a valid answer. Do not invent an answer to fill a gap.
  - Edit files directly. Do **not** create helper scripts for bulk replacement.
  - Do not run `git commit`, `checkout`, `switch`, `stash`, `push`, `reset` or create branches. Do not create files in the repo root. Stay within the named files.
- **The prompt carries the design, not the finished code**: file, location, signature, behaviour, constraints, the spec section and AC ids it implements. Code written out in a prompt makes the lead the author.

## 5. Keep units and calls small
- **One unit = one file × one concrete change × one deliverable** (code, test or doc, never mixed). Two or three files only when they cannot pass a check apart (a signature and its only caller).
- **`--files` ≤ 3 per call.** Needing more means the unit is wrong.
- Ask questions answerable with **yes/no or a concrete value**. Open questions invite silent omissions.
- **Order**: code units, then test units for code already checked, then doc units.
- Write the item checklist before the call and tick it against the answer.
- **An empty response is not proof of failure**: check `git status` and `git diff --stat` first, then re-delegate only what is left.
- **Verify with `grep -c`**: count the identifiers that must exist after the change. A report saying "done" is not evidence.

## 6. Model chains
### 6.1 Implementer (risky units)
1. `flash`.
2. `flash` again with `--resume`, carrying the rejection reason or review findings.
3. `argon` in a new conversation.
4. The lead (`lead (fallback)`), noted in the unit table and `walkthrough.md`.

Exit code 3 (quota or rate limit) moves to the next model at once; other failures retry once with a smaller unit.

### 6.2 First-pass reviewer
1. codex `luna` (`--effort high` for concurrency, lifetime and UB units; `medium` otherwise).
2. agy `argon`.
3. `cpp-reviewer`.

The question is narrow: "does the change in `<file>` match spec §N / AC-n? List each mismatch with file:line, or answer `none`." codex runs `git diff -- <file>` itself; agy gets the diff in the prompt file. Findings go back to the implementer as its next attempt (§6.1).
Before each call, tell the user the alias and the reason in one line.

### 6.3 One round only
If the reviewer disagrees, the author reworks once and gets one more review. Still disagreeing: ask the user. Agents do not ping-pong.

## 7. Never delegated
State changes in `agent_todo.md`, spec approval handling, unit splitting and per-unit checks, the Tester verdict, integration, gate runs (build, tests, lint), commits and merges.

## 8. `cpp-reviewer` (Claude sub-agent)
Defined in [`.claude/agents/cpp-reviewer.md`](/.claude/agents/cpp-reviewer.md): fresh context, read-only, checks a diff against the spec and the §3 risk list. It shares the lead's model family, so it is the reviewer for **ordinary** units and the last fallback for risky ones; risky units go to a different family first (§6.2).
Agent definitions load when a Claude Code session starts: a session that creates or edits the file uses agy `flash` instead until it restarts.

## 9. Recording
- `plan.md` unit table:

  | Unit | File | Change (what, where, AC) | Check | Risky | Author | Reviewer | Tokens (in / out) | Status |
  |---|---|---|---|---|---|---|---|---|
  | U1 | `include/atugcc/pattern/visualizer.hpp` | add `setBudget()` to `Tracer` (AC-2) | `grep -c "setBudget"` = 2; build `atugcc_tests`; `--gtest_filter=Tracer*` | yes | agy flash | codex luna: none | 46k / 1k | done |

- `testrecord.md` has a **Reviews** section: unit, reviewer, question, findings, resolution.
- Model aliases appear only here and in `subagent_run.py`.
