# Plan: 070-21 OOP basics track (`03_oop_basics`, curriculum, first four lessons)

- Spec: [/docs/specs/070_21_oop_basics_track.md](/docs/specs/070_21_oop_basics_track.md) (approved 2026-11-12)
- Branch: `feature/070-21-oop-basics-track` (from `main` after 070-20 was merged)

## Model assignment
Lesson code and text are written by the lead ([delegation.md](/.agent/rules/delegation.md) §1: the C++ here is lesson code of a few dozen lines per class, written together with the README it illustrates, and a sub-agent prompt would be longer than the code: `lead (small)`). The four `main.cpp` units are not risky in the §3 sense (no atomics, threads, views, signal handlers; lifetime is shown with objects of the lesson's own type, no dangling reference is formed). Reviewer: `cpp-reviewer` (fresh context, Agent tool). Machine checks: MSVC and Clang 20 builds with warnings as errors, outputs compared, `linux-x64-asan` smoke tests, and the solve-and-check loop of every automatic exercise on both compilers.

## Design (spec §2.1, §2.2)
- Track `03_oop_basics` (`track.toml`, two languages), four lessons, folder numbers `01_`–`04_`; `05_`–`07_` stay empty (postponed lessons).
- Each lesson is one `main.cpp` with an anonymous namespace, English output with `== Step N: … ==` headers, Korean line + English line comments, README in two languages in the format "common mistakes and the right way" (`흔한 실수와 바른 방식`), and an `exercises.toml`.
- Output stability: no addresses, times or hashes. The only pointer compare prints a boolean. A moved-from state is printed only for types the lesson defines (`Tracked::movedFrom()`, `IntBox::empty()`).
- UB is never executed (Assumption 6): the shallow copy of step 2 in `copy_and_move` is a counter of owners (`-1`), not a double delete; the missing virtual destructor is shown with `std::has_virtual_destructor_v` and text only; `new` is paired with `delete` at once.
- Exercise classification (Assumption 8, 070-20 Assumption 2) from running both compilers:
  - observation: `class_basics` `init_order` (Clang `-Wreorder-ctor` fails the build, MSVC builds silently);
  - automatic: the other 12 (`explicit_meters`, `loose_class`; `swap_members`, `early_return`, `keep_temp`; `delete_copy`, `moved_from`, `no_noexcept`; `override_typo`, `nonvirtual_dtor`, `abstract_object`, `final_inherit`).
  - Draft change: the draft exercise 2 of `inheritance_virtual` read "`-Wdelete-non-virtual-dtor` as an error". Running it showed that on both compilers removing `virtual` from `~Resource()` stops at `~FileResource() override` (error on both), and with `override` also removed it builds and runs without any warning (the class has no other virtual function). The exercise now asks for the `override` error and tells the reader not to run the version that builds.

## Files
- [NEW] `lessons/tracks/03_oop_basics/track.toml`
- [NEW] `lessons/tracks/03_oop_basics/{01_class_basics,02_object_lifetime,03_copy_and_move,04_inheritance_virtual}/{lesson.toml,main.cpp,README.md,README.en.md,exercises.toml}`
- [MODIFY] `lessons/tags.toml` (tags `class`, `lifetime`, `copy`, `inheritance`; the aliases `virtual function` and `가상 함수` moved from tag `variant` to `inheritance`, because one name may belong to one tag only)
- [MODIFY] `lessons/README.md`, `lessons/intro.md`, `lessons/intro.en.md`, `docs/lesson_candidates.md`
- [MODIFY] `lessons/tracks/01_essentials/03_const_correctness/README.md`, `README.en.md`, `08_variant_visit/README.md`, `README.en.md` (one link line each, spec §8)
- [MODIFY] `docs/agent_todo.md`

## Unit table
| Unit | File | Change (what, where, AC) | Check | Risky | Author | Reviewer | Tokens | Status |
|---|---|---|---|---|---|---|---|---|
| U1 | `03_oop_basics/track.toml`, `lessons/tags.toml` | track and four tags (AC-3, AC-4) | `lessons.py check` 0/0; `lessons.py index` order | no | lead | cpp-reviewer | — | done |
| U2 | `01_class_basics/{lesson.toml,main.cpp}` | Steps 1–5 (AC-1) | both builds, 0 warnings; outputs equal | no | lead (small) | cpp-reviewer | — | done |
| U3 | `02_object_lifetime/{lesson.toml,main.cpp}` | Steps 1–5 (AC-1) | same | no | lead (small) | cpp-reviewer | — | done |
| U4 | `03_copy_and_move/{lesson.toml,main.cpp}` | Steps 1–5 (AC-1) | same | no | lead (small) | cpp-reviewer | — | done |
| U5 | `04_inheritance_virtual/{lesson.toml,main.cpp}` | Steps 1–6 (AC-1) | same | no | lead (small) | cpp-reviewer | — | done |
| U6 | the four `README.md` / `README.en.md` pairs | AC-6 | section and block counts equal | no | lead | cpp-reviewer | — | done |
| U7 | the four `exercises.toml` | AC-5 | `exercises.py check` on both presets | no | lead | cpp-reviewer | — | done |
| U8 | `lessons/README.md`, `intro.md`, `intro.en.md`, `lesson_candidates.md`, link lines in `const_correctness` and `variant_visit` | AC-7 | `lint_docs.py` | no | lead | cpp-reviewer | — | done |
