# Lesson: constraining templates — from SFINAE to concepts (`concepts`)

A template accepts any type and only says "not this type" when compilation fails somewhere deep in its body. C++20 concepts write the requirements in the signature. This lesson writes one constraint with `std::enable_if` (SFINAE) and with a concept, builds a concept from a requires expression, and then prints an abbreviated function template (`const Shape auto&`), the overload with the narrowest constraint winning, `if constexpr (requires { … })`, and a `requires` clause on a class template. For real uses in the library, read [`observer.hpp`](/include/atugcc/pattern/observer.hpp) (`ObserverOf`) and [`ring_buffer.hpp`](/include/atugcc/core/ring_buffer.hpp) (`RingBuffer`'s `requires`) in the `uses` tab. Background: [concepts.en.md](/docs/cpp_evolution/concepts.en.md).

## The old ways and C++20
| | C++11/17 | C++20 |
|---|---|---|
| Writing a constraint | `template <typename T, std::enable_if_t<std::is_integral_v<T>, int> = 0>` | `template <std::integral T>`, a `requires` clause, `std::integral auto` |
| Grouping requirements | only in the docs, or `std::void_t` detection helpers | `concept Shape = requires(const T& s) { … };` |
| Choosing an overload | make the conditions mutually exclusive by hand | subsumption: the narrower constraint wins |
| Does a member exist | the detection idiom | `if constexpr (requires { x.size(); })` |
| Error messages | inside the template body, or "candidate ignored" | at the call, naming the concept and the unmet requirement |

## Run
- Web playground: select it in the lesson tree, then Run
- Local: `cmake --build --preset <preset> --target lesson_concepts`, then `bin/lessons/lesson_concepts`, or `ctest --preset <preset> -R lesson.concepts`

## What to look for
- Step 1: `twiceSfinae` and `twice` give the same value. The difference is where the constraint shows: `enable_if` spends a template parameter and hides the condition in it; the concept is written by name in the type position.
- Step 2: `Shape` means "a type whose `area()` converts to `double` and whose `name()` converts to `std::string_view`". `Circle` and `Square` satisfy it without a common base class. `Shape<int>` is `false`, and the same facts are kept as `static_assert`s.
- Step 3: all three overloads match `-3`, but `std::signed_integral` subsumes `std::integral`, so the narrowest one is chosen. `3u` is not `signed_integral`, so it gets `integral`; `2.5` gets the unconstrained `auto`. This subsumption holds between standard concepts. Two concepts of your own subsume only when they share a concept (one is defined in terms of the other, or both are built on a common one such as `std::integral<T>`); writing the same condition in two separate concepts gives an ambiguity error.
- Step 4: `if constexpr (requires { x.size(); })` turns "does this expression compile" into a `bool`. `std::vector` has `size()`, `int` does not. The false branch is not instantiated, so writing `x.size()` there is no error for `int`.
- Step 5: `FixedRing<N>` accepts only powers of two through `requires (std::has_single_bit(N))`. Only for a power of two is `index & (N - 1)` equal to `index % N`, so the constraint is what makes the mask correct. The library's `RingBuffer` also checks for a power of two in a `requires` clause, but writes it as the pre-C++20 bit expression `BlockCount > 1 && (BlockCount & (BlockCount - 1)) == 0`, which rejects 1 as well (the `requires` line in `ring_buffer.hpp`).

## Exercises
1. Add `printShape(42);` and `twiceSfinae("x");` to `main`, one at a time, and build. Compare the two error messages, and if you can, the messages of MSVC and Clang. Which one tells you more directly what is missing?
2. Read `ObserverOf` in `observer.hpp` and write `concept Printable` (a type with `std::string toString() const`) in the same shape, then give `Circle` a `toString()`. Check with `static_assert(Printable<Circle>)`.
3. Instantiate `FixedRing<6>`. Which constraint does the error say is not satisfied? Check whether `RingBuffer<64, 6>` fails for the same reason.
