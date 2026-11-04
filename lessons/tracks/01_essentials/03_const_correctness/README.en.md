# Lesson: where `const` goes — member functions, `mutable`, return types (`const_correctness`)

`const` means different things depending on where it is written. A `const` after a member function promises "this function does not change the object"; a `const` in front of a return-by-value type mostly does nothing, or blocks moves. This lesson prints the difference in five steps: `const` member functions, a `mutable` cache, `const`/non-`const` overloads and the C++23 deducing this that merges them, a return-type `const` seen through a type that counts its copies and moves, and `const` with pointers. Background: [const_return_type_guide.md](/docs/learning/const_return_type_guide.md) (Korean).

## The old ways and C++23
| | Old way | This lesson's way |
|---|---|---|
| Query functions | `const` forgotten, so they cannot be called on an object taken by `const&` | every function that does not change state is `const` |
| Caches | drop `const`, or `const_cast` | a `mutable` member (needs a lock or an atomic when shared between threads) |
| `const`/non-`const` pair | the same body twice, or one delegating to the other with `const_cast` | C++23 deducing this: one `auto& get(this auto& self, std::size_t i)` |
| Return by value | `const std::string name()` ("so the caller cannot change it") | `std::string name()`: the `const` blocks moves in assignment and `push_back` |

## Run
- Web playground: select it in the lesson tree, then Run
- Local: `cmake --build --preset <preset> --target lesson_const_correctness`, then `bin/lessons/lesson_const_correctness`, or `ctest --preset <preset> -R lesson.const_correctness`

## What to look for
- Step 1: `report(const Counter&)` calls only `value()`. On an object taken by `const&`, only `const` member functions can be called.
- Step 2: `wordCount()` is `const`, but it stores its result in a `mutable` member on the first call, so after three calls `computations = 1`. In exchange, `mutable` breaks the expectation that "a `const` function may be called from several threads at once". If threads share this object, the cache needs a lock or a `std::atomic`.
- Step 3: the same `at(0)` returns `int&` on a non-`const` object and `const int&` through `const&`. The compiler picks the overload by the object's `const`. Below it, `get` is a single function written with C++23 deducing this: `self` is deduced as `Buffer&` or `const Buffer&`, and the return type `auto&` follows that `const`.
- Step 4: read the table. Initialization (`Tracked a = makeConst();`) is 0 even with `const`, because of C++17 guaranteed copy elision. In assignment and `push_back`, `makeValue` moves and `makeConst` **copies**: a `const` temporary does not bind to `Tracked&&`, so the move operations cannot be chosen.
- Step 5: in `const int*` the pointed-to value is `const`; in `int* const` the pointer itself is. Read right to left ("`p` is a pointer to `const int`").

Deducing this for rvalue objects too (`this Self&& self` with `std::forward_like<Self>(self.data_[i])`) builds with MSVC, but on the Linux toolchain (Clang 20 + libstdc++ 14.2) `forward_like` is a compile error, so it is not in the lesson code ([KI-033](/docs/known_issues.md)).

```cpp
template <typename Self>
auto&& get(this Self&& self, std::size_t i) {
    return std::forward_like<Self>(self.data_[i]);   // int&& for a Buffer&&
}
```

## Exercises
1. Uncomment `// c.increment();` inside `report` in step 1 and build. Read in the compile error what is `const`, then revert.
2. Uncomment `// const int makeInt() { return 1; }` in step 4 and call it once from `main` (without a call, an unused-function error appears as well). Clang warns `-Wignored-qualifiers`, and this repository treats warnings as errors, so the Linux build fails. What does MSVC do? Why is there no warning for the class type `const Tracked`?
3. Change the return type of `get` from `auto&` to `auto`. Why does `b.get(1) = 21;` stop compiling? If you have MSVC, write the rvalue version with `std::forward_like` as above and check the type of `std::move(b).get(1)`.
