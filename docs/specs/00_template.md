---
id: NNN-SS
title: [Task Title]
depends_on: []        # task IDs that must be DONE first, e.g. [010-06]
unblocks: []          # task IDs waiting on this one
approved: null        # YYYY-MM-DD, set only when the user explicitly approves this spec
---

# Spec NNN-SS: [Task Title]

## 0. Assumptions (please review)
Every decision the user did not specify. This is the section the user reviews most closely.

| # | Decision | Rejected alternative | Why |
|---|---|---|---|
| 1 | [...] | [...] | [...] |

## 1. Objective
[What needs to be achieved — module, class, or feature — and why.]

## 2. Requirement Details

### 2.1 Public API Surface
[Headers/classes/functions in `include/atugcc/`. Function names are camelCase.]

### 2.2 Internal Implementation
[Implementation details in `src/` or `detail/`.]

### 2.3 Platform Specifics
[Windows (MSVC 2026) vs Linux (GCC) differences, or `none`.]

## 3. C++ Standard Evolution (if applicable, otherwise `N/A`)
| Approach | Standard | Description |
|----------|----------|-------------|
| Legacy | C++11/14/17 | [Previous approach] |
| Modern | C++20 | [C++20 improvement] |
| Latest | C++23 | [C++23 improvement, if applicable] |

Reference: `/docs/cpp_evolution/<feature>.md` (list it under §8 when the page does not exist yet).

## 4. Edge Cases
Mark each `[x]` with how the design handles it, or `N/A` with a reason.
- [ ] Thread safety / memory ordering
- [ ] Resource lifetime / RAII / dangling views (`std::string_view`, `std::span`, iterators)
- [ ] Platform differences (MSVC vs GCC)
- [ ] Template instantiation / concept constraints
- [ ] ODR (header-only `inline`, static locals)
- [ ] Undefined behaviour (casts, alignment, signed overflow, signal-handler safety)

## 5. Acceptance Criteria
Observable, testable statements. The Tester stage verifies these, not the implementation's own tests.

| ID | Criterion | Verified by |
|---|---|---|
| AC-1 | [...] | [test name / command / manual check] |

## 6. Out of Scope
- [What is deliberately excluded] — picked up by [NNN-SS or KI-NNN]

## 7. Dependencies & Backends
[External libraries and the backend interface that hides them ([impl.md](/.agent/rules/impl.md) §5), or `none`.]

## 8. Documentation Updates
Every document this task changes. A page that no longer matches the code after the task is a defect of the task. Write `none` only when no reader of any document can notice the change.

| Document | Section | Change |
|---|---|---|
| [...] | [...] | [...] |

## 9. Technical Constraints
- Compiler: MSVC (VS 2026) / GCC (latest stable)
- CMake: 3.26+
- C++ Standard: C++23 (C++20 minimum)

## 10. Context & References
[Links to relevant files using project-relative paths, e.g. `[RingBuffer](/include/atugcc/core/ring_buffer.hpp)`.]

## 11. Implementation Plan
- [ ] Step 1: ...
- [ ] Step 2: ...

## 12. Verification Plan
- [ ] Build, zero warnings: `cmake --build --preset windows-x64-debug` and `cmake --build --preset linux-x64-debug`
- [ ] Full suite: `ctest --test-dir out/build/<preset> --output-on-failure` on both presets
- [ ] Every AC row has its evidence in `testrecord.md`

## History / Amendments
- [YYYY-MM-DD: what changed, which sub-spec]
