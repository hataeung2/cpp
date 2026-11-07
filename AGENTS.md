# atugcc — Agent Entry Point (Codex and other AGENTS.md-aware tools)

A sub-agent started with a task prompt stops here: skip the boot sequence, follow the prompt and the project rules it carries.

Otherwise, follow the boot sequence in [`docs/agent_start_prompt.md`](/docs/agent_start_prompt.md). It is shared with `CLAUDE.md` (Claude Code) and `.agent/` (Antigravity), so every tool reads the same rules in the same order.
