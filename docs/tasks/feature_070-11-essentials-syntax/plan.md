# Plan: 070-11 essentials 2차 레슨 — 문법

- Spec: [/docs/specs/070_11_essentials_syntax_lessons.md](/docs/specs/070_11_essentials_syntax_lessons.md) (approved 2026-11-04)
- Branch: `feature/070-11-essentials-syntax` (from `main` at `86b5696`)

## Design

### Files
- [NEW] `lessons/tracks/01_essentials/{03_const_correctness,06_concepts,07_ranges_views,08_variant_visit}/` — `lesson.toml`, `main.cpp`, `README.md`, `README.en.md`
- [MODIFY] `lessons/tags.toml` (4 tags), `lessons/tracks/02_patterns/01_device_state_machine/lesson.toml` (`variant`)
- [NEW] `docs/cpp_evolution/concepts.md`; [MODIFY] `docs/learning/const_return_type_guide.md`
- [MODIFY] `docs/tasks/lesson_candidates.md`, `docs/known_issues.md` (KI-001, KI-033), `docs/tasks/agent_todo.md`, spec History (alias change below)

No CMake change: `lessons/CMakeLists.txt` globs the manifests. Lessons link `atugcc_core`, so they get `-Wall -Wextra -Werror` (Clang) and `/W4 /WX` (MSVC).

### Deviation from spec §2.3 (recorded in the spec History)
`mutable` is already an alias of the `capture` tag (`lessons/tags.toml`), and one name belongs to one tag (070-10, `lessons.py check` WARN; AC-7 needs WARN 0). So the `const` tag does not get `mutable`. Search is a substring match over title, summary and tag names (`web/frontend/src/search.ts`), so the `const_correctness` summary contains the word `mutable` and AC-8 (`mutable` finds the lesson) still holds; it finds `lambda_capture` too.

### Common rules for the four `main.cpp`
Same as 070-03: file header doc block (`@file`, `@brief` Korean + English), English program output, every Korean comment line (or paragraph) followed at once by the English one, helpers in an anonymous namespace, camelCase functions, `kPascalCase` constants, `snake_case_` members, `[[nodiscard]]` on value-returning helpers, namespace aliases instead of `using namespace`, includes exactly what is used, no platform `#ifdef`, exit code 0. Each section starts with a heading line `== N. <name> ==`. Values computed by the program are printed from the program (no hard-coded results). Results of a view traversal are collected into a string and printed after the traversal (spec §4).

### `03_const_correctness` (`const_correctness`), `uses = []`, `tags = ["const", "move"]`
1. `== 1. const member functions ==`: `class Counter` (`value_`; `[[nodiscard]] int value() const`, `void increment()`). `void report(const Counter& c)` prints `report(const Counter&): value = 2`. Inside `report`, the commented line `// c.increment();` with a comment pointing at exercise 1.
2. `== 2. mutable cache ==`: `class Document` (`std::string text_`, `mutable std::optional<std::size_t> word_count_`, `mutable int computations_ = 0`; `[[nodiscard]] std::size_t wordCount() const` counts space-separated words on the first call only; `[[nodiscard]] int computations() const`). `const Document doc{"a const function may still fill a cache"}`; three calls print `wordCount() call 1 = 8` … `call 3`; then `computations = 1`. A comment says `mutable` breaks "const means safe to call from several threads at once" (spec §2.2).
3. `== 3. const and non-const overloads, then deducing this ==`: `class Buffer` (`std::vector<int> data_{10, 20, 30}`; `int& at(std::size_t i)`, `const int& at(std::size_t i) const`; `auto& get(this auto& self, std::size_t i) { return self.data_[i]; }`). `Buffer b; const Buffer& cb = b;` Print `b.at(0) returns int&: true`, `cb.at(0) returns const int&: true` (`std::same_as<decltype(...), ...>`), write `b.at(0) = 11`, then `b.get(1) = 21`, print both values, `cb.get(1) returns const int&: true`, and a `static_assert` of the same. A comment: one `get` replaces both overloads; `auto&` keeps the reference (`auto` would copy, exercise 3); the rvalue version needs `std::forward_like`, which the Linux toolchain does not build (KI-033).
4. `== 4. const return values and moves ==`: `struct Counts { int copyCtor = 0; int copyAssign = 0; int moveCtor = 0; int moveAssign = 0; };` (local to `main`, passed by reference; no static counters). `class Tracked` holds `Counts*`; explicit constructor from `Counts&`; the four copy/move members increment their counter; move members `noexcept`. `[[nodiscard]] Tracked makeValue(Counts&)` and `[[nodiscard]] const Tracked makeConst(Counts&)` both `return Tracked{counts};` (prvalue, no NRVO). Table header `case | copy ctor | copy assign | move ctor | move assign` and six rows, counters reset before each operation: `Tracked a = makeValue()`, `Tracked a = makeConst()`, `t = makeValue()`, `t = makeConst()`, `v.push_back(makeValue())`, `v.push_back(makeConst())` (`t` constructed and `v.reserve(2)` before the reset). Expected: init rows 0/0/0/0, `makeValue` rows move, `makeConst` rows copy (AC-3). The commented line `// const int makeInt() { return 1; }` with a comment pointing at exercise 2.
5. `== 5. const and pointers ==`: four rows `int*`, `const int*`, `int* const`, `const int* const`, each `pointee const: <bool>  pointer const: <bool>` computed with `std::is_const_v`. Then `const int* p = &x; p = &y;` prints `*p = 2 after p = &y`, and `int* const q = &x; *q = 5;` prints `x = 5 after *q = 5`.

### `06_concepts` (`concepts`), `uses = ["lib:atugcc/pattern/observer.hpp", "lib:atugcc/core/ring_buffer.hpp"]`, `tags = ["concepts"]`
1. `== 1. enable_if vs a concept ==`: `template <typename T, std::enable_if_t<std::is_integral_v<T>, int> = 0> [[nodiscard]] T twiceSfinae(T x)` and `template <std::integral T> [[nodiscard]] T twice(T x)`; print `twiceSfinae(21) = 42`, `twice(21) = 42`.
2. `== 2. a concept from a requires expression ==`: `concept Shape` (`s.area()` → `std::convertible_to<double>`, `s.name()` → `std::convertible_to<std::string_view>`); `struct Circle { double radius; … }`, `struct Square { double side; … }`; `void printShape(const Shape auto& s)` prints `circle: area 3.14`; print `Shape<Circle> = true`, `Shape<Square> = true`, `Shape<int> = false`; `static_assert` the same three.
3. `== 3. the most constrained overload wins ==`: `describe(auto)`, `describe(std::integral auto)`, `describe(std::signed_integral auto)` returning `std::string_view`; print `describe(-3) -> signed_integral`, `describe(3u) -> integral`, `describe(2.5) -> auto` (AC-4).
4. `== 4. if constexpr with a requires expression ==`: `template <typename T> [[nodiscard]] std::string sizeInfo(const T& x)`: `if constexpr (requires { x.size(); })` → `size() = N`, else `no size()`. Print for `std::vector<int>{1, 2, 3}` and `42`.
5. `== 5. requires clause on a class template ==`: `template <std::size_t N> requires (std::has_single_bit(N)) struct FixedRing { static constexpr std::size_t kMask = N - 1; [[nodiscard]] static constexpr std::size_t slot(std::size_t index) { return index & kMask; } };` Print `FixedRing<8>: mask = 7, slot(13) = 5` and `FixedRing<16>: mask = 15, slot(13) = 13`. A comment points at `RingBuffer`'s `requires (BlockCount > 1 && (BlockCount & (BlockCount - 1)) == 0) && (BlockSize >= 4)` in `ring_buffer.hpp` (a power-of-two check written as a pre-C++20 bit expression, which also rejects 1) and at exercise 3 (`FixedRing<6>`).

### `07_ranges_views` (`ranges_views`), `uses = []`, `tags = ["ranges", "lambda"]`
Data: `struct Item { std::string name; int price; int stock; };` `std::vector<Item> items{{"apple", 300, 4}, {"bread", 250, 0}, {"cheese", 900, 2}, {"dates", 120, 0}, {"eggs", 200, 6}};` `inStock` is a lambda `stock > 0`.
1. `== 1. raw loop vs ranges algorithms ==`: raw loop over `items` → `raw loop: cheapest in stock = eggs (200)`. Same with `auto inStockItems = items | views::filter(inStock);` and `std::ranges::min_element(inStockItems, {}, &Item::price)` (the view is a named variable: `filter_view` is not a borrowed range, a temporary would give `dangling`) → `ranges::min_element: cheapest in stock = eggs (200)`. Then `std::ranges::sort(items, {}, &Item::price)` → `sorted by price: dates, eggs, bread, apple, cheese`. `inStockItems` is not used after the sort (a `filter_view` caches its begin).
2. `== 2. a view pipeline ==`: `items | views::filter(inStock) | views::transform(&Item::name) | views::take(3)` → `in stock, cheapest first: eggs, apple, cheese`.
3. `== 3. lazy evaluation ==`: a transform lambda `noisy` prints `  transform(<name>)` directly (this section is about when it is called) and returns the name; the result line is built during the loop and printed after it. Print `pipeline built, nothing ran yet` right after building `items | views::filter(inStock) | views::transform(noisy) | views::take(2)`, then loop, then `result: eggs, apple`. Expected transform lines: `eggs`, `apple` only (AC-4).
4. `== 4. C++23 views ==`: `const auto names = std::ranges::to<std::vector>(items | views::filter(inStock) | views::transform(&Item::name));` → `ranges::to: 3 names in a std::vector<std::string>`; same for prices (`&Item::price`). `enumerate: 0 eggs, 1 apple, 2 cheese`; `zip: eggs=200, apple=300, cheese=900`; with `std::vector<int> numbers{1, 2, 3, 4, 5, 6, 7}`: `chunk(2): [1 2] [3 4] [5 6] [7]`, `slide(2): [1 2] [2 3] [3 4] [4 5] [5 6] [6 7]`; `std::string_view csv = "a,b,c"` → `split(','): a | b | c` (each part as `std::string_view(part)` while `csv` is alive); `fold_left(numbers, 0, std::plus{}) = 28`. A comment: the pipe form `| std::ranges::to<std::vector>()` and `std::format("{}", view)` are README-only (KI-033).
5. `== 5. dangling and owning_view ==`: `[[nodiscard]] std::vector<int> makeNumbers()` returns `{5, 3, 8}`. `using FindOnTemporary = decltype(std::ranges::find(makeNumbers(), 8));` (unevaluated: no iterator to a dead vector exists), `static_assert(std::same_as<FindOnTemporary, std::ranges::dangling>)` and print `find on a temporary vector returns std::ranges::dangling: true`. Print `views::all(lvalue vector) is ref_view: true` and `views::all(temporary vector) is owning_view: true` (`std::same_as` on `std::views::all_t<std::vector<int>&>` / `<std::vector<int>>`). Then `auto doubled = makeNumbers() | views::transform(…x * 2…);` and print `doubled (the view owns the vector): 10 6 16`. The lesson never dereferences a `dangling` (exercise 2 does).

### `08_variant_visit` (`variant_visit`), `uses = ["lib:atugcc/pattern/state.hpp"]`, `tags = ["variant", "state"]`
1. `== 1. virtual functions ==`: `class Shape` (virtual destructor, pure `area()`, `name()`), `class CircleV final`, `class RectV final`; `std::vector<std::unique_ptr<Shape>>` with a circle (radius 1) and a rect (2 × 3); print `circle: area 3.14`, `rect: area 6.00`.
2. `== 2. std::variant and std::visit ==`: `struct Circle { double radius; [[nodiscard]] double area() const; };`, `struct Rect { double width; double height; [[nodiscard]] double area() const; };` (no base class). `template <typename... Ts> struct overloaded : Ts... { using Ts::operator()...; };` (three lines, comment: same as `state.hpp`). `std::vector<std::variant<Circle, Rect>>` with the same two shapes; `area` through a generic lambda `[](const auto& s) { return s.area(); }`, `name` through `overloaded{…}`; same two output lines as step 1.
3. `== 3. a new operation: perimeter ==`: one `overloaded` visitor (`std::numbers::pi`) → `circle: perimeter 6.28`, `rect: perimeter 10.00`. Types unchanged (comment).
4. `== 4. inspecting a variant ==`: `std::variant<Circle, Rect> v = Circle{1.0};` → `index() = 0`, `holds_alternative<Circle> = true`, `get_if<Rect> is null: true`; `v = Rect{2.0, 3.0};` → `index() = 1`, `get_if<Rect>->width = 2.00`; `std::get<Circle>(v)` inside `try`, catch `const std::bad_variant_access&` → `bad_variant_access caught` (no `what()`).
5. `== 5. memory layout ==`: `sizeof(Circle) = …`, `sizeof(Rect) = …`, `sizeof(std::variant<Circle, Rect>) = …`, `variant >= largest alternative: true` (computed with `std::max`), `sizeof(std::unique_ptr<Shape>) = …`, and the line `variant elements: no heap allocation; unique_ptr elements: one allocation each`.

### Tags (spec §2.3, minus `mutable`)
Four tables appended to `lessons/tags.toml`; `device_state_machine` gets `tags = ["state", "tracer", "variant"]`. Check: `lessons.py check` has no tag WARN.

### Verification scripts (lead's scratch area, not committed)
- `comment_pairs.py`: every run of comment lines with Hangul is followed at once by a comment line without Hangul (070-03 AC-5 rule).
- `readme_pairs.py`: `README.md` / `README.en.md` have the same number of headings, exercise items and code blocks; English links to READMEs with an English version point at `README.en.md`.
- `hangul_out.py`: no Hangul in a captured stdout+stderr file.
- `ac8.mjs`: headless Edge with `playwright-core` against `tools/playground.py` (as 070-03).

## Units
Order: tags → four lessons (code) → READMEs → docs.

| Unit | File | Change (what, where, AC) | Check | Risky | Author | Reviewer | Tokens (in / out) | Status |
|---|---|---|---|---|---|---|---|---|
| U1 | `lessons/tags.toml`, `device_state_machine/lesson.toml`, 4 new `lesson.toml` | 4 tags, `variant` on `device_state_machine`, manifests (§2.1, §2.3; AC-1, AC-7) | `lessons.py check` no tag WARN | no | lead | AC-8 search | — | done (`mutable` alias dropped, spec History) |
| U2 | `03_const_correctness/main.cpp` | lesson (§2.2; AC-2, AC-3) | build both presets 0 warnings; output; AC-3 table | no | agy flash | cpp-reviewer: wrong `makeConst` comment (copy is at the caller), 3 KO/EN mismatches, spec `get(0) = 5` vs plan, exercise 2 also gives `-Wunused-function` if not called; review fixes lead (small) (+ before review: `printRow` helper, no blank lines); re-check: resolved except README wording of exercise 2, fixed | 185k / 42k | done |
| U3 | `06_concepts/main.cpp` | lesson (§2.2; AC-2, AC-4) | same | no | agy flash | cpp-reviewer: RingBuffer comment said "same constraint" (it also rejects 1, and `requires` is not old syntax), "fast" mask claim; `static_cast<void>(x)` unconfirmed → removed, 0 warnings both; review fixes lead (small) incl. README and `concepts.md`; re-check: resolved, README.en comma splice and `concepts.md` wording fixed | 162k / 34k | done |
| U4 | `07_ranges_views/main.cpp` | lesson (§2.2; AC-2, AC-4) | same; `linux-x64-asan` lesson run | yes (views that can dangle) | agy flash | codex luna (high): none | 100k / 35k (review 222k / 3k) | done |
| U5 | `08_variant_visit/main.cpp` | lesson (§2.2; AC-2, AC-4) | same | no | agy flash | cpp-reviewer: area comment above the wrong line, "pattern matching" wording, README Triangle `area()` only declared; review fixes lead (small) (+ before review: one shared `nameOf` visitor); re-check: resolved | 88k / 21k | done |
| U6 | 8 READMEs | §2.2 content (AC-5) | `readme_pairs.py` OK; lint | no | lead | cpp-reviewer (per lesson with U2–U5, then one doc review U6–U9): translation none; subsumption sentence too strong (also a shared base concept) → fixed lead (small) | — | done |
| U7 | `const_return_type_guide.md` | copy elision fix, lesson link (Assumption 8) | lint | no | lead | cpp-reviewer (doc review): correct; two wording notes → fixed | — | done |
| U8 | `docs/cpp_evolution/concepts.md` [NEW] | evolution page (Assumption 13) | lint | no | lead | cpp-reviewer (U3 re-check, doc review): subsumption sentence, "concepts for RingBuffer" (a requires clause), Clang message text checked on Clang 20 → fixed | — | done |
| U9 | `lesson_candidates.md`, `known_issues.md`, `agent_todo.md`, spec History | §8 (AC-10) | `lint_docs.py` exit 0 | no | lead | cpp-reviewer (doc review): `ranges_views` row read as if 023-05 already links it → "링크할 예정" | — | done |

## Verification (spec §12)
- `py -3 tools/test_lessons.py`, `py -3 tools/lessons.py check` (ERROR 0, WARN 0)
- `py -3 .agent/scripts/build.py --preset windows-x64-debug --test`, `--preset linux-x64-debug --test`
- `const_correctness` on `linux-x64-playground-release` (AC-3)
- `linux-x64-asan --test` (U4 risky: lifetime)
- Output Hangul scan, comment pairs (AC-6)
- `npm --prefix web/frontend test`
- Browser (AC-8): screenshots in `screenshots/`
- `py -3 .agent/scripts/lint_docs.py`
