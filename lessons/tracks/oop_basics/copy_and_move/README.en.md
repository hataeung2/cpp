# Lesson: copy and move — Rule of 0/5, `= delete` (`copy_and_move`)

When you pass an object to a function or put it in another variable, C++ copies or moves it. A copy makes a new object with the same value; a move hands the contents of the original to the new object and leaves the original in a valid but unspecified state (often empty). This lesson prints the difference with a type that counts copies and moves (`Tracked`) and checks it in five steps: the counts for copy / `std::move` / a temporary in value passing, the problem that a default copy of a class holding a resource makes two owners (nothing is really released; it is shown with an owner counter), writing it by hand with the Rule of 5, leaving it to members with the Rule of 0, and forbidding copies. An object that has been moved from is in a "valid but unspecified state", so this lesson prints the state after a move only for types the lesson defines itself, and never the moved-from value of a standard type such as `std::string`. Previous lesson: [object_lifetime](/lessons/tracks/oop_basics/object_lifetime/README.en.md).

## Common mistakes and the right way
| | Common mistake | Right way |
|---|---|---|
| A class holding a resource | a default (shallow) copy makes two owners of the same resource | write copy and move by hand (Rule of 5) or leave the resource to a member (Rule of 0) |
| Special member functions | writing only the destructor and forgetting copy and move | decide all five (destructor, copy construct/assign, move construct/assign) together or write none |
| Move | the move constructor has no `noexcept`, so `std::vector` copies when it reallocates | move operations are `noexcept` |
| Forbidding copies | telling people in documentation that a class must not be copied | `= delete` makes the compiler stop it; a `std::unique_ptr` member does it by itself |

## Run
- Web playground: select it in the lesson tree, then Run
- Local: `cmake --build --preset <preset> --target lesson_copy_and_move`, then `bin/lessons/lesson_copy_and_move`, or `ctest --preset <preset> -R lesson.copy_and_move`

## What to look for
- Step 1: `takeByValue(a)` is one copy, `takeByValue(std::move(a))` is one move, `takeByValue(makeTracked())` is zero (C++17 guaranteed copy elision) and `takeByConstRef(a)` is zero. Giving an lvalue to a function that takes its argument by value is a copy.
- Step 2: `ShallowHandle` is a class that holds just a pointer. The default copy constructor copies the pointer and does not raise the "owner count", so there are two handles but the counter says 1. When both are gone the counter is `-1`: the same resource was given back twice. With a real resource that would be a double free (undefined behaviour), so this lesson shows it only with a counter.
- Step 3: `IntBox` holds an `int` made with `new`, so it writes all five special member functions. A copy makes **separate storage** (`copy has its own storage: true`) and a move hands over the pointer and empties the original (`moved-from IntBox is empty: true`). Because the move constructor is `noexcept`, `std::vector<IntBox>` moves its elements instead of copying them when it reallocates (`relocation used only moves: true`).
- Step 4: `Person` leaves its resources to the members `std::string` and `std::vector<int>`, so it writes no special member function (Rule of 0). Copy and move both work by themselves, and the move construction is `noexcept`.
- Step 5: `Ticket` has its copy `= delete`d (`copyable: false`), and `Owner`, which has a `unique_ptr` member, writes nothing and still cannot be copied but can be moved.

```cpp
class Person {                       // Rule of 0: no special member functions
    std::string name_;
    std::vector<int> scores_;
};
class Ticket {                       // no copies, move only
public:
    Ticket(const Ticket&) = delete;
    Ticket(Ticket&&) = default;
};
```

## Exercises
The web practice mode (the default) edits a practice copy and leaves the original (`lessons/`) untouched. "Reset" below means ↺ Reset on the web and `py -3 tools/practice.py reset copy_and_move` locally (local practice: "Practice workspace" in [`lessons/README.md`](/lessons/README.md)).

1. Change the copy constructor of `Tracked` to `Tracked(const Tracked&) = delete;`, build, and read which line gives the error. Reset it.
2. Right below `takeByValue(std::move(a));` in step 1, print `a.movedFrom()`. In what state is `a` after the move? Why does this lesson not print the moved-from value of a `std::string`? Reset it.
3. Remove `noexcept` from the move constructor of `IntBox` and look at `relocation used only moves` in step 3. How does it change? Why does `std::vector` choose copying when it reallocates? Reset it.
