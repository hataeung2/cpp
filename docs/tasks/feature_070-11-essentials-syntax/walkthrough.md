# Walkthrough: 070-11 essentials 2차 레슨 — 문법

- Spec: [/docs/specs/070_11_essentials_syntax_lessons.md](/docs/specs/070_11_essentials_syntax_lessons.md)
- Evidence: [testrecord.md](/docs/tasks/feature_070-11-essentials-syntax/testrecord.md)
- Branch: `feature/070-11-essentials-syntax`

## Result
Four new essentials lessons fill the syntax slots of the track:
- [`03_const_correctness`](/lessons/tracks/01_essentials/03_const_correctness/README.md): `const` member functions, a `mutable` cache, `const`/non-`const` overloads and one C++23 deducing-this `get`, a table of copies and moves showing that a `const` return value is elided at initialization but copied on assignment and `push_back`, and `const` with pointers.
- [`06_concepts`](/lessons/tracks/01_essentials/06_concepts/README.md): `enable_if` vs a concept, a `Shape` concept from a requires expression, the most constrained overload, `if constexpr (requires { … })`, and `FixedRing<N>` with `requires (std::has_single_bit(N))`.
- [`07_ranges_views`](/lessons/tracks/01_essentials/07_ranges_views/README.md): raw loop vs ranges algorithms with projections, a view pipeline, lazy evaluation with `take(2)`, C++23 views and the call form of `ranges::to`, and `dangling` / `ref_view` / `owning_view`.
- [`08_variant_visit`](/lessons/tracks/01_essentials/08_variant_visit/README.md): the same shapes as a virtual hierarchy and as `std::variant` + `std::visit`, a new operation without touching the types, inspecting a variant, and the memory layout.

All four build without warnings with MSVC and Clang 20, print the same output on both hosts, and have Korean and English READMEs. Tags `const`, `concepts`, `ranges`, `variant` were added; `device_state_machine` got `variant`.

Documents: new [`concepts.md`](/docs/cpp_evolution/concepts.md); [`const_return_type_guide.md`](/docs/learning/const_return_type_guide.md) now says a `const` return value is elided at initialization (C++17) and copied only on assignment and insertion; [lesson_candidates.md](/docs/tasks/lesson_candidates.md) E14, E1, E5, E6 are `레슨 있음`; KI-001 (`concepts.md` written) and KI-033 (`std::forward_like` added to the Linux-missing list) updated.

## Deviations from the spec (recorded in its History)
- The `const` tag has no `mutable` alias: `mutable` already belongs to the `capture` tag. The lesson summary contains the word, so the search still finds it (AC-8).
- §2.2 step 3 example value aligned with the code (`b.get(1) = 21`).

## Follow-ups
- None new. KI-020 (`PlaygroundServer` timing test under host load) showed up once during the run and passed when the machine was idle.
- KI-033 keeps range formatting, the pipe form of `ranges::to` and `std::forward_like` README-only until the Linux toolchain moves to libstdc++ 15.

All code units were written by agy and reviewed (`cpp-reviewer`; codex for the risky `ranges_views`); no `lead (fallback)` units.
