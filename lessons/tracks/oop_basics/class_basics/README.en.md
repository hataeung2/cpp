# Lesson: classes and encapsulation — invariants, initialization, `explicit` (`class_basics`)

A class bundles "data and the rules for handling it" into one unit. For someone who knows variables, functions, loops and `struct`, this lesson prints the mistakes people make most often when they first write a class, in five steps: the access difference between `struct` and `class`, the invariant that breaks when every member is `public`, initialization by assignment in the body, the implicit conversion of a one-argument constructor, and `const` member functions. This track does not teach the basics of C++ syntax (variables, control flow, pointers).

## Common mistakes and the right way
| | Common mistake | Right way |
|---|---|---|
| Access | every member `public`, so anyone changes the value | data is `private` and member functions keep the invariant (the balance is never negative) |
| Initialization | assignment in the constructor body, members left uninitialized | the constructor initializer list and member default initializers |
| Conversion | a one-argument constructor silently turns a `double` into the class | `explicit` |
| Queries | `const` forgotten, so they cannot be called on an object taken by `const&` | functions that do not change state are `const` member functions ([const_correctness](/lessons/tracks/essentials/const_correctness/README.en.md)) |

## Run
- Web playground: select it in the lesson tree, then Run
- Local: `cmake --build --preset <preset> --target lesson_class_basics`, then `bin/lessons/lesson_class_basics`, or `ctest --preset <preset> -R lesson.class_basics`

## What to look for
- Step 1: the members of a `struct` are `public` by default and the members of a `class` are `private` by default. The same `value_` is visible from outside in `OpenBox` (`true`) and not in `ClosedBox` (`false`). The default access (the default access of inheritance included) is the only difference between the two keywords.
- Step 2: the members of `LooseAccount` are `public`, so nobody stops 150 being taken from 100 to give `-50`. `Account` hides `balance_` as `private`, and `withdraw` keeps the invariant "you cannot take more than the balance". A request that breaks it changes nothing and comes back as a `core::Expected` error (`InvalidArgument`) ([error_expected](/lessons/tracks/essentials/error_expected/README.en.md)).
- Step 3: an initializer list creates each member with the wanted value from the start (`ByList`: two lines, `Part(first)` and `Part(second)`). Assigning in the body creates the members with the default first and assigns them again, so the work is doubled (`ByBody`). A member missing from the list uses the default of its declaration (`Config()` has `retries=3`). Members are initialized in **declaration order**; the order written in the initializer list does not matter.
- Step 4: `Feet(double)` has no `explicit`, so `showFeet(3.5)` silently converts to `Feet` (`double -> Feet implicit conversion: true`). `Meters` is `explicit`, so you must write `Meters{3.5}` (`false`). Preventing an unintended conversion is the job of `explicit`.
- Step 5: `report(const Account&)` calls only `balance()`. On an object taken by `const&`, only `const` member functions can be called.

```cpp
class Account {
public:
    explicit Account(long opening) : balance_(opening) {}
    [[nodiscard]] core::Expected<long> withdraw(long amount);   // keeps the invariant
    [[nodiscard]] long balance() const { return balance_; }     // only reads
private:
    long balance_ = 0;                                          // outsiders cannot touch it
};
```

## Exercises
The web practice mode (the default) edits a practice copy and leaves the original (`lessons/`) untouched. "Reset" below means ↺ Reset on the web and `py -3 tools/practice.py reset class_basics` locally (local practice: "Practice workspace" in [`lessons/README.md`](/lessons/README.md)).

1. Remove `explicit` from the constructor of `Meters` and look at the step 4 output. How does `double -> Meters implicit conversion` change? Does `showMeters(3.5);` compile now? Reset it.
2. Swap the order in which `first_` and `second_` are written in `ByList`'s initializer list and build. What does the compiler warn about (Clang: `-Wreorder`)? This repository treats warnings as errors, so the Linux build fails. What about MSVC? In which order does initialization actually happen? Reset it.
3. Change `struct` to `class` in `LooseAccount` and build. Read which line the error points at and what it says cannot be accessed. Reset it.
