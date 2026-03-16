# Spec: [Task Title]

## Objective
[What needs to be achieved — module, class, or feature.]

## Requirement Details

### Public API Surface
[Headers/classes/functions in `include/atugcc/`]

### Internal Implementation  
[Implementation details in `src/`]

### Platform Specifics
[Windows (MSVC 2026) vs Linux (GCC) differences, if any]

## C++ Standard Evolution (if applicable)
| Approach | Standard | Description |
|----------|----------|-------------|
| Legacy | C++11/14/17 | [Previous approach] |
| Modern | C++20 | [C++20 improvement] |
| Latest | C++23 | [C++23 improvement, if applicable] |

Reference: `/docs/cpp_evolution/<feature>.md`

## Edge Cases
- [ ] Thread safety
- [ ] Resource lifetime / RAII
- [ ] Platform differences (MSVC vs GCC)
- [ ] Template instantiation
- [ ] ODR violations

## Dependencies & Adapters
[External libraries and adapter interface design]

## Technical Constraints
- Compiler: MSVC (VS 2026) / GCC (latest stable)
- CMake: 3.26+
- C++ Standard: C++23 (C++20 minimum)

## Context & References
[Links to relevant files using project-relative paths]

## Implementation Plan
- [ ] Step 1: ...
- [ ] Step 2: ...

## Verification Plan
- [ ] CMake build: `cmake --build build --config Debug`
- [ ] Tests: `ctest --output-on-failure -C Debug`
- [ ] Zero warnings at `/W3` (MSVC) or `-Wall` (GCC)
