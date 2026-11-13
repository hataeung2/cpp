# Walkthrough: 070-21 OOP basics track (`03_oop_basics`)

## Result
A third track `03_oop_basics` ("OOP basics: classes, lifetime, inheritance", under `02_patterns` in the tree) with the first four of its seven lessons. The other three folder numbers (`05_`–`07_`) are free; the curriculum table is in [`docs/lesson_candidates.md`](/docs/lesson_candidates.md) ("OOP 입문 트랙").
- `class_basics`: `struct` versus `class` access, an invariant (`Account::withdraw` returns a `core::Expected`), initializer list versus assignment in the body (the extra default construction is visible), member defaults, `explicit`, `const` member functions.
- `object_lifetime`: scope and reverse destruction, member and base construction order, temporaries and `const&` lifetime extension, an RAII guard that closes on return and on an exception, `new`/`delete` versus `unique_ptr`.
- `copy_and_move`: copy and move counts for value passing, a "shallow copy" shown with an owner counter (`-1`, no double delete is run), Rule of 5 (`IntBox`, `noexcept` and `std::vector` reallocation), Rule of 0 (`Person`), `= delete` and move-only types.
- `inheritance_virtual`: static versus dynamic binding, `override`, a virtual destructor, slicing, an abstract class with `vector<unique_ptr<Shape>>`, `final`.
- Each lesson has a two-language README in the format "common mistakes and the right way", `exercises.toml` (13 exercises: 12 automatic, 1 observation), tags (`class`, `lifetime`, `copy`, `inheritance`, existing `const`, `error`, `move`).
- Docs: `lessons/README.md` (track paragraph), `intro.md` / `intro.en.md` (track list), `lesson_candidates.md` (curriculum table), one link line in the READMEs of `const_correctness` and `variant_visit`.

Evidence: [testrecord.md](testrecord.md).

## Notes
- Draft change: exercise 2 of `inheritance_virtual` ("read `-Wdelete-non-virtual-dtor` as an error") did not work as drafted: on both compilers, removing `virtual` from the base destructor stops at the derived `~FileResource() override`, and without `override` the code builds with no warning at all and would be undefined behaviour when run. The exercise now asks for the `override` error and warns not to run the other version.
- `class_basics` exercise 2 (reorder the initializer list) is an observation exercise: Clang fails with `-Wreorder-ctor` and MSVC builds silently.
- `tags.toml`: the aliases `virtual function` and `가상 함수` moved from tag `variant` to the new tag `inheritance` (one name may belong to one tag). `variant_visit` is still found by those words through its title and summary.
- `cpp-reviewer` found nothing in the code (no UB, leak, unstable output) and six small text issues (two hints printed the solving line, an unanchored `has` regex, "the only difference" between `struct` and `class` ignores the default base access, a move "empties" the original although the standard only guarantees a valid state, and the printed label `base` read as a class name); all fixed in one round.
- 070-20 was merged into `main` first: this task's `exercises.toml` files follow its rules and `lessons/README.md` section.

## Follow-ups
- `composition`, `smart_pointers`, `value_semantics` (candidates O5–O7) are registered as BACKLOG tasks 070-22, 070-23 and 070-24 in `agent_todo.md`, without a place in the order (Assumption 12: that is the user's decision).
