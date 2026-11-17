# Lesson: smart pointers and ownership — `unique_ptr`, `shared_ptr`, `weak_ptr` (`smart_pointers`)

A raw pointer such as `Widget*` does not tell you who must delete the object: whether you must delete it, whether you only borrowed it, or whether it is already gone is not in the type. Smart pointers write this **ownership** as a type. With types that print their construction and destruction and count the live objects, this lesson checks five steps: the sole owner `std::unique_ptr` cannot be copied, only moved; a function signature says whether it gives, borrows or takes the ownership; erasing or taking elements out of a `std::vector<std::unique_ptr<Widget>>`; the `use_count` of the shared owner `std::shared_ptr` and the destruction when the last owner lets go; and a cycle between two objects that point at each other, broken with `std::weak_ptr`. Leaks and double frees with raw pointers are never run; they are shown only in text. Previous lessons: [object_lifetime](/lessons/tracks/oop_basics/object_lifetime/README.en.md) (`new`/`delete` in step 5), [copy_and_move](/lessons/tracks/oop_basics/copy_and_move/README.en.md) (moves).

## Common mistakes and the right way
| | Common mistake | Right way |
|---|---|---|
| Owning | create with `new` and pass a `Widget*`: who calls `delete` is not in the type, so it leaks or is freed twice | `std::make_unique` and `std::unique_ptr`: deleted when the scope ends |
| Passing ownership | copying a raw pointer so that two places delete the same object | `unique_ptr` cannot be copied, it is passed only with `std::move` |
| Function signatures | every parameter is a `Widget*` | borrowing: `const Widget&`; taking: `std::unique_ptr<Widget>` by value; creating: return a `std::unique_ptr<Widget>` |
| Polymorphic containers | hold `Widget*` in a `std::vector` and `delete` them one by one at the end | `std::vector<std::unique_ptr<Widget>>`: an element's object is deleted with the element |
| Sharing | `shared_ptr` out of habit when there is one owner | `unique_ptr` by default, `shared_ptr` only when there really are several owners |
| Cycles | two objects point at each other through `shared_ptr` and neither is ever deleted (a leak) | the side that points back is a `std::weak_ptr` |

## Run
- Web playground: select it in the lesson tree, then Run
- Local: `cmake --build --preset <preset> --target lesson_smart_pointers`, then `bin/lessons/lesson_smart_pointers`, or `ctest --preset <preset> -R lesson.smart_pointers`

## What to look for
- Step 1: the object made with `std::make_unique<Widget>("solo")` has one owner, `owner`. A `unique_ptr` cannot be copied (`false`, exercise 1); passing the ownership to `next` with `std::move` still leaves one object (`alive widgets: 1`). The moved-from `owner` is empty: unlike most standard types, whose moved-from value is unspecified, a moved-from `unique_ptr` is defined to be `nullptr` (by the lesson rules, the output prints only the state of the lesson's own types). No `delete` is written, yet `~Widget solo` is printed when the block ends and `alive widgets: 0` follows.
- Step 2: the signature states the ownership. `makeWidget` returns a `std::unique_ptr<Widget>` and gives the ownership to the caller, `show(const Widget&)` only borrows, and `consume(std::unique_ptr<Widget>)` takes it by value and takes the ownership. So `~Widget parcel` is printed when the `consume` call finishes (before that statement ends), before the `back in main` line. Passing it to `consume` needs `std::move(made)`, and `made` is empty afterwards.
- Step 3: put a `Widget` and `Gadget`s into a `std::vector<std::unique_ptr<Widget>>` and one loop tells them apart with the virtual call `kind()` (a `Gadget`'s destruction line is printed by the base `~Widget` too; that a `unique_ptr<Widget>` deletes a `Gadget` correctly because `Widget`'s destructor is virtual is shown through output in step 3 of [inheritance_virtual](/lessons/tracks/oop_basics/inheritance_virtual/README.en.md)). `erase` deletes the object with the element (`~Widget a`), and the object taken out with `std::move(crate.back())` is still held by `taken` after `pop_back` (no destruction line). `clear()` and `reset()` delete the remaining two.
- Step 4: for an object made with `std::make_shared`, every copy of the `shared_ptr` adds an owner: `use_count` 1 → 2 → 1. `~Widget shared` is printed when the last owner, `first`, is gone at the end of the block. `survivor` outside the block holds nothing, so its `use_count` is 0. Give `survivor` a share of the ownership and the lifetime extends past the block (exercise 2).
- Step 5: `Parent` owns its `Child` through a `shared_ptr`, and `Child` only watches its `Parent` through a `std::weak_ptr`. A `weak_ptr` does not count in `use_count`, so it is `parent use_count: 1` (`child` has two owners, the local and the parent, so 2), and when the block ends `~Parent` and `~Child` are printed in turn. `watcher` is a `weak_ptr` too, so it does not keep the object alive, and once it is gone `expired()` is `true`. To use it, get a `shared_ptr` with `lock()` and check that the object is still alive. If `Child` also held a `shared_ptr`, there would be a cycle and neither would be deleted when the block ends (exercise 3). The final `if` block then breaks the remaining cycle by hand with `lock()` and `adopt(nullptr)` so that nothing leaks; in the original, `watcher` is already empty and it does not run (`alive at the end: 0`).

```cpp
[[nodiscard]] std::unique_ptr<Widget> makeWidget(std::string name);   // gives the ownership
void show(const Widget& widget);                                      // borrows
void consume(std::unique_ptr<Widget> widget);                         // takes it: consume(std::move(p))
class Child {
    std::weak_ptr<Parent> parent_;    // the side that points back is a weak_ptr: no cycle
};
```

## Exercises
The web practice mode (the default) edits a practice copy and leaves the original (`lessons/`) untouched. "Reset" below means ↺ Reset on the web and `py -3 tools/practice.py reset smart_pointers` locally (local practice: "Practice workspace" in [`lessons/README.md`](/lessons/README.md)).

1. Add `auto copy = next;` below `auto next = std::move(owner);` in step 1 and build. What error do you get, and why is `unique_ptr` made so that it cannot be copied? Reset it.
2. Add `survivor = first;` above `std::cout << "leaving the block\n";` inside step 4's block and run. When is the `~Widget shared` line printed now? Reset it.
3. Change `Child`'s member `std::weak_ptr<Parent> parent_;` to `std::shared_ptr<Parent> parent_;` and run. How do step 5's `use_count`, the destruction lines, `parent expired` and `alive parents and children` change? Reset it.
