# C++ Evolution: Constraining Templates (SFINAE → Concepts)

## Why
A template accepts any type until something inside it fails to compile. The error then points deep into the template body, and the template's requirements live only in its documentation. C++20 concepts put the requirements in the signature: the compiler checks them at the call, reports the unmet requirement by name, and picks between overloads by how constrained they are. atugcc uses a concept for its observer requirements and a `requires` clause for the power-of-two rule of `RingBuffer`.

Lesson: [`concepts`](/lessons/tracks/01_essentials/06_concepts/README.en.md) (essentials track).

## C++11/17 (Legacy): SFINAE with `std::enable_if`
```cpp
template <typename T, std::enable_if_t<std::is_integral_v<T>, int> = 0>
T twiceSfinae(T x) { return x * 2; }

twiceSfinae(21);    // 42
twiceSfinae("x");   // error: no matching function ... candidate template ignored:
                    //        requirement 'std::is_integral_v<const char *>' was not satisfied (Clang 20)
```
- "Substitution failure is not an error": an invalid type in the signature removes the overload instead of failing. `std::enable_if_t<cond, int> = 0` turns a condition into such a failure.
- The condition is hidden in a template parameter. Two overloads with opposite conditions must be written so that exactly one survives; there is no "more specific" ordering.
- Testing for a member (`x.size()`) needs `std::void_t` or detection-idiom helpers.

## C++20: concepts and `requires`
```cpp
template <std::integral T>
T twice(T x) { return x * 2; }

template <typename T>
concept Shape = requires(const T& s) {
    { s.area() } -> std::convertible_to<double>;
    { s.name() } -> std::convertible_to<std::string_view>;
};

void printShape(const Shape auto& s);           // abbreviated function template

std::string_view describe(auto);                 // least constrained
std::string_view describe(std::integral auto);
std::string_view describe(std::signed_integral auto);   // chosen for -3: it subsumes std::integral

if constexpr (requires { x.size(); }) { /* x has size() */ }

template <std::size_t N>
    requires (std::has_single_bit(N))
struct FixedRing { static constexpr std::size_t kMask = N - 1; };
```
- A **concept** is a named compile-time predicate on types. A **requires expression** lists the expressions that must be valid and, with `-> concept`, what their results must satisfy.
- **Constraint placement**: `template <std::integral T>`, a `requires` clause after the template head or the declarator, or `Concept auto` in a parameter (abbreviated template).
- **Subsumption**: when two overloads both match, the one whose constraints imply the other's wins. This works through the standard concepts (`std::signed_integral` is defined as `std::integral<T> && std::is_signed_v<T>`). Two atomic constraints count as the same only when they come from the same written expression, so subsumption needs a shared concept: `B` is defined in terms of `A` (`concept B = A<T> && ...`), or both are built on a common one (`std::integral<T>` in both). Writing the same condition twice in two separate concepts gives an ambiguity error instead.
- **`if constexpr (requires { ... })`** replaces detection idioms for a one-off check inside a function.
- Errors name the concept and the failed requirement at the call site.

## C++23 (Current, atugcc)
- [`observer.hpp`](/include/atugcc/pattern/observer.hpp): `ObserverOf<T>` requires `onNotify(const Subject&)` and `display()`; `subscribe` takes `template <ObserverOf T>`, so an observer without them fails at the `subscribe` call with the missing member named.
- [`ring_buffer.hpp`](/include/atugcc/core/ring_buffer.hpp): `RingBuffer` has `requires (BlockCount > 1 && (BlockCount & (BlockCount - 1)) == 0) && (BlockSize >= 4)`. The bit trick `(n & (n - 1)) == 0` is the pre-C++20 spelling of "power of two" (it is also true for 0; `> 1` excludes 0 and 1, while `has_single_bit` excludes only 0); C++20 `std::has_single_bit(n)` (`<bit>`) says it by name, and the lesson's `FixedRing` uses it.
- New code prefers `concept`/`requires` over `enable_if` ([impl.md](/.agent/rules/impl.md) §1).
