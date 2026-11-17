# Lesson: object lifetime — construction, destruction, temporaries, RAII (`object_lifetime`)

In C++ the moment an object is made and the moment it is gone are fixed in the code. This lesson makes those moments visible with a small type (`Noisy`) that prints its construction and destruction one line at a time, and checks the lifetime rules in five steps: the scope decides the lifetime, the construction and destruction order of a base class and members, temporaries and lifetime extension by `const&`, an RAII guard that returns a resource in its destructor (even when an exception is thrown), and a comparison of `new`/`delete` with `std::unique_ptr`. Resources (files, memory) are not really acquired but expressed as lines of output and counters, so this lesson causes no leak or double free.

## Common mistakes and the right way
| | Common mistake | Right way |
|---|---|---|
| Release | pairing `new` and `delete` by hand (a `return` or exception in between leaks) | the scope decides the lifetime: local variables, `std::unique_ptr` |
| Order | thinking members are made in the order written in the initializer list | made in declaration order and destroyed in exactly the reverse order |
| Resources | calling `close()` at the end of a function and missing it on an early `return` or exception | RAII: acquire in the constructor, return in the destructor |
| Temporaries | assuming a temporary lives on after its statement | gone at the end of the statement; bound to a `const&` it lives as long as that reference's scope |

## Run
- Web playground: select it in the lesson tree, then Run
- Local: `cmake --build --preset <preset> --target lesson_object_lifetime`, then `bin/lessons/lesson_object_lifetime`, or `ctest --preset <preset> -R lesson.object_lifetime`

## What to look for
- Step 1: `+ outer`, `+ inner`, then `- inner`, `- outer`. Leaving a scope runs the destructor, and the objects of one scope disappear in the **reverse** of the order they were made. `alive` counts them.
- Step 2: `Derived` inherits `Base` and has two members (`first_`, `second_`). They are made in the order the member of the base class `Base` (`base` in the output) → the body of `Base` → members in declaration order (`first`, `second`) → the body of `Derived`, and destroyed in exactly the reverse order (the `construction order` and `destruction order` lines). What decides the order is the **declaration order**.
- Step 3: a temporary made by `makeNoisy("temporary")` is gone as soon as its statement ends (`alive after the statement: 0`). Bound to a `const&` it lives until the end of the block that holds the reference (`extended`). This extension does not apply when a function returns a reference to a local variable (README text only: this lesson does not run that code).
- Step 4: `ScopedFile` prints `open` in the constructor and `close` in the destructor. `close` is printed once whether the function ends normally like `process(0)` or throws like `process(1)` (`guard summary: opened 2, closed 2`), and an exception runs the destructors of the local objects before it reaches the `catch` (stack unwinding).
- Step 5: an object made with `new` must be deleted by hand with `delete`. A `return` or an exception in between skips the `delete` and leaks; this lesson deletes at once and does not run such a path. `std::unique_ptr` destroys the object by itself when the scope ends, so there is no such path.

```cpp
class ScopedFile {
public:
    explicit ScopedFile(std::string path) { /* acquire the resource */ }
    ~ScopedFile() { /* return it whichever way we leave */ }
    ScopedFile(const ScopedFile&) = delete;             // a copy would return it twice
    ScopedFile& operator=(const ScopedFile&) = delete;
};
```

## Exercises
The web practice mode (the default) edits a practice copy and leaves the original (`lessons/`) untouched. "Reset" below means ↺ Reset on the web and `py -3 tools/practice.py reset object_lifetime` locally (local practice: "Practice workspace" in [`lessons/README.md`](/lessons/README.md)).

1. Swap the **declaration** order of `first_` and `second_` in `Derived` and see how the `construction order` and `destruction order` lines of step 2 change. Reset it.
2. Add `if (stage == 2) { return; }` to `process` after the `ScopedFile` declaration and call `process(2);` once more in step 4. Is `close` still printed on the early `return`? Are the two numbers of `guard summary` equal? Reset it.
3. Change the first statement of step 3, `static_cast<void>(makeNoisy("temporary"));`, to `const Noisy& kept = makeNoisy("temporary");` and print `kept.name()` once (to avoid an unused-variable warning). How does `alive after the statement` change? When does the destruction happen? Reset it.
