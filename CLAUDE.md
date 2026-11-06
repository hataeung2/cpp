# atugcc — Claude Code Context

A sub-agent started with a task prompt stops here: skip the boot sequence and follow the prompt only.

Otherwise, follow the boot sequence in [`docs/agent_start_prompt.md`](/docs/agent_start_prompt.md) before doing anything else. It is shared with `AGENTS.md` (Codex and other tools) and `.agent/` (Antigravity), so the reading order and the non-negotiable rules live in exactly one place.

- Function and method names are `camelCase` (user decision 2026-10-28; see [`.agent/rules/impl.md`](/.agent/rules/impl.md)).
