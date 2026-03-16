---
trigger: model_decision
description: When making a specification
---

# Agent Rule: Task Specification Writing Guide (atugcc)

## 1. When to Write a Spec
When picking a task from `/docs/tasks/agent_todo.md`, if the linked Spec file is missing (e.g., `- [ ] Task Name`), you MUST draft a Spec file before writing any code.

## 2. Drafting the Spec
Create a new file `/docs/specs/XX_taskname.md` (where XX is the next available sequence number) using the template `/docs/specs/00_template.md`.

Guidelines for each section:
- **Objective**: Clearly state what needs to be achieved — the module, class, or feature being added or refactored.
- **Requirement Details**: Break down into logical components:
  - **Public API Surface**: What headers/classes/functions will be exposed in `include/atugcc/`.
  - **Internal Implementation**: What goes in `src/`.
  - **Platform Specifics**: Any Windows (MSVC) vs Linux (GCC) differences.
- **C++ Standard Evolution** (if applicable):
  - Document the pre-C++20 approach and how C++20/23 improves it.
  - Reference which C++20/23 features are being utilized.
- **Edge Cases (CRITICAL)**: Proactively anticipate:
  - Thread safety concerns
  - Resource lifetime / RAII guarantees
  - Platform-specific behavior differences
  - Template instantiation issues
  - ODR (One Definition Rule) violations
- **Dependencies & Adapters**: If external libraries are involved, specify the adapter interface design.
- **Technical Constraints**: Compiler requirements (MSVC 2026 / GCC latest), CMake minimum version, target platforms.
- **Context & References**: Link relevant files using **project-relative paths** (e.g., `[RingBuffer](/include/atugcc/core/ring_buffer.hpp)`). **DO NOT** use absolute paths.
- **Implementation & Verification Plan**: 
  - Step-by-step implementation checklist.
  - CMake build verification commands.
  - GoogleTest test cases to write.

> 💡 **Self-Correction & Proactivity**: Do not leave sections blank if the user omitted details. Propose the optimal C++ design, document assumptions, and ask the user to review.

## 3. Post-Draft Actions (Mandatory)
Once the Spec is drafted, strictly follow these steps:

1. **Link Spec**: Update `/docs/tasks/agent_todo.md` to link to the new Spec file.
   - Before: `- [ ] Task Name`
   - After: `- [ ] [Task Name](/docs/specs/XX_taskname.md)`
2. **Report**: Notify the user that the Spec (Proposal) is ready for review.
3. **STOP & WAIT**: **DO NOT start code implementation** at this stage. Leave the task status as `[ ]` and wait for the user's approval.
