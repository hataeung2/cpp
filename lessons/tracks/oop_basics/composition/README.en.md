# Lesson: composition and delegation — has-a versus is-a, LSP (`composition`)

Inheritance is the promise "a derived class is a kind of base class (is-a)", not a tool for reusing code. When you want to reuse code, the right tool is usually composition: **own the class as a member (has-a) and hand work to it (delegation)**. This lesson checks it in five steps: a stack that inherits `std::vector<int>` gets `insert` along with it, so a value can be slipped in under the stack; a stack that owns a `std::vector<int>` as a member offers only the stack's functions; when a `Car` has an `Engine` and hands `start()` to it, the part is made before the whole and destroyed after it; writing "a square is a rectangle", true in mathematics, as inheritance breaks the Liskov substitution principle (LSP); and the right way. Deleting a class without a virtual destructor, such as `std::vector`, through a base-class pointer (undefined behaviour) is never run; it is shown only with a trait. Previous lesson: [inheritance_virtual](/lessons/tracks/oop_basics/inheritance_virtual/README.en.md).

## Common mistakes and the right way
| | Common mistake | Right way |
|---|---|---|
| Code reuse | `public` inheritance to use a few functions: the whole interface of the base class comes along and opens a way to break the invariant | composition: own it as a member, offer only the functions you need and hand the work to the member inside them (delegation) |
| Inheriting a standard container | `class Stack : public std::vector<int>`: no virtual destructor, so deleting through a `std::vector<int>*` is undefined behaviour | a `std::vector<int>` member |
| Judging is-a | writing a real-world classification ("a square is a rectangle") straight as inheritance | inherit only when the derived class keeps every promise that code using the base class trusts (LSP) |
| Two types with different promises | in `Square : Rectangle` the setters change both sides and break `Rectangle`'s promise | no inheritance between them; share only the promise both can keep (area, name) as an interface |

## Run
- Web playground: select it in the lesson tree, then Run
- Local: `cmake --build --preset <preset> --target lesson_composition`, then `bin/lessons/lesson_composition`, or `ctest --preset <preset> -R lesson.composition`

## What to look for
- Step 1: `InheritedStack` inherits `std::vector<int>` publicly just to implement `push` and `pop` with it. So `std::vector`'s `insert` is a function of `InheritedStack` too, and after pushing 1 2 3, `insert(begin(), 99)` slips 99 in at the bottom. The pop order is `3 2 1 99`: 99 went in last and comes out last. Outside code can break the stack's promise ("the last value in comes out first"). `std::vector<int>` has no virtual destructor (`false`), so deleting an `InheritedStack` through a `std::vector<int>*` is undefined behaviour (step 3 of [inheritance_virtual](/lessons/tracks/oop_basics/inheritance_virtual/README.en.md)).
- Step 2: `Stack` owns a `std::vector<int>` as the member `items_` and offers only `push`, `pop`, `empty` and `size`. Each function hands the work to `items_` (delegation). The pop order is `3 2 1`, and there is no way to call `insert` (exercise 1). `std::is_base_of_v` shows that `InheritedStack` is a kind of `std::vector<int>` (`true`) and `Stack` is not (`false`).
- Step 3: `Car` owns an `Engine` as a member and hands `start()` to `engine_.start()`. The output order `Engine built`, `Car built`, …, `~Car`, `~Engine`: a member (the part) is made before the body of the whole's constructor and destroyed after the body of the whole's destructor. has-a by a member (composition) ties the part's lifetime to the whole. A `Car` is not a kind of `Engine`, so there is no reason to inherit.
- Step 4: `broken::Square` inherits `broken::Rectangle`, and to keep its invariant (all sides equal) both `setWidth` and `setHeight` change both sides. `stretch(Rectangle&)` trusts only `Rectangle`'s promise (changing the width keeps the height) and sets width 5, height 4, so it expects area 20. The rectangle is `5 x 4, area 20`, but the square is `4 x 4, area 16`: putting a `Square` into code that takes a `Rectangle&` broke the promise that code trusts. That is a violation of the **Liskov substitution principle (LSP)**: code that uses a base class must still be right when you put a derived class into it. It is defined behaviour and the compiler does not warn: a design bug. Fixing it the other way round (exercise 3) makes it stop being a square.
- Step 5: `fixed::Rectangle` and `fixed::Square` do not inherit from each other; they share only the promise both can keep (`area`, `name`) in the abstract class `Shape`. `Square` has only `setSide`, which changes its one side, so no function that could break the invariant exists, and `fixed::Square` is not a kind of `fixed::Rectangle` (`false`). So passing a `fixed::Square` to a function that takes a `fixed::Rectangle&` (like step 4's `stretch`) is a compile error, and `Shape` has no width or height setters to misuse.

```cpp
class Stack {                                  // no inheritance
public:
    void push(int value) { items_.push_back(value); }   // offer only what you need and hand it to the member
private:
    std::vector<int> items_;                   // has-a
};
class Shape {                                  // only the promise both can keep
public:
    virtual ~Shape() = default;
    [[nodiscard]] virtual int area() const = 0;
};
class Rectangle final : public Shape { /* setWidth, setHeight */ };
class Square final : public Shape { /* setSide */ };
```

## Exercises
The web practice mode (the default) edits a practice copy and leaves the original (`lessons/`) untouched. "Reset" below means ↺ Reset on the web and `py -3 tools/practice.py reset composition` locally (local practice: "Practice workspace" in [`lessons/README.md`](/lessons/README.md)).

1. Add `stack.insert(stack.begin(), 99);` below `stack.push(3);` in step 2 and build. Step 1's `leaky.insert(…)` builds, so why is this line an error? Reset it.
2. Change `public` to `private` in `class InheritedStack : public std::vector<int>` and build. Which lines give errors, and which of the functions blocked along with `insert` does a stack need too? Reset it.
3. Remove `broken::Square`'s `setHeight` override and run. How do step 4's `square:` line and `still a square` line change, and what broke this time? Reset it.
