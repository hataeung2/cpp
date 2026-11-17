# Lesson: loops and views — from raw loops to `std::ranges` (`ranges_views`)

Over five items (`name`, `price`, `stock`), "find the cheapest item in stock" is written as a raw loop and then with a `std::ranges` algorithm and a projection (`&Item::price`). Then come a view pipeline (`filter | transform | take`), views computing only as much as needed (lazy evaluation), C++23 views (`enumerate`, `zip`, `chunk`, `slide`, `split`, `fold_left`, `ranges::to`), and the lifetime problem of temporary containers, seen through `std::ranges::dangling` and `owning_view`.

## The old ways and C++20/23
| | Old way | `std::ranges` |
|---|---|---|
| Find, sort | a `for` loop, `std::sort(v.begin(), v.end(), [](auto& a, auto& b) { return a.price < b.price; })` | `std::ranges::sort(items, {}, &Item::price)`: one range and a projection |
| Filter and transform | a loop that builds an intermediate vector | `items \| views::filter(…) \| views::transform(…)`: no intermediate vector, computed while iterating |
| The first N | a counter and `break` | `views::take(N)`: computes only what is needed |
| Index, pairs, groups | an index variable | C++23 `views::enumerate`, `zip`, `chunk`, `slide` |
| Collect into a vector | a `push_back` loop | C++23 `std::ranges::to<std::vector>(view)` |
| Iterator into a temporary | compiles, breaks at run time | the result type is `std::ranges::dangling`: dereferencing it is a compile error |

## Run
- Web playground: select it in the lesson tree, then Run
- Local: `cmake --build --preset <preset> --target lesson_ranges_views`, then `bin/lessons/lesson_ranges_views`, or `ctest --preset <preset> -R lesson.ranges_views`

## What to look for
- Step 1: the raw loop and `ranges::min_element` give the same answer (`eggs`). The filtered view passed to `min_element` is a named variable: `filter_view` is not a borrowed range, so calling it on a temporary view would give `dangling` (step 5). After that, `ranges::sort` reorders `items` by price.
- Step 2: read the pipeline left to right: in stock → name → the first three.
- Step 3: `pipeline built, nothing ran yet` appears before any `transform(...)` line. Building a view computes nothing. While iterating, `take(2)` stops after two elements, so the transform lambda runs only for the first two items in stock.
- Step 4: `ranges::to` collects the pipeline into a `std::vector<std::string>`. `enumerate` gives index and element, `zip` pairs two ranges, `chunk(2)` makes groups that do not overlap, `slide(2)` makes overlapping windows. Each part of `split(',')` points into the original `std::string_view`, so it is used only while that string is alive.
- Step 5: `ranges::find` on a temporary vector returns `std::ranges::dangling` instead of an iterator, because the vector is gone at the end of that statement. Attaching a view to a temporary vector (`makeNumbers() | views::transform(…)`) instead moves the vector into an `owning_view`, so iterating is safe. A named vector gets a `ref_view` (a reference).

C++23 also has the pipe form `v | std::ranges::to<std::vector>()` and range formatting `std::format("{}", view)`. Both work with MSVC but do not build on the Linux toolchain (Clang 20 + libstdc++ 14.2), so the lesson code uses the call form of `ranges::to` and formats element by element ([KI-033](/docs/known_issues.md)).

```cpp
auto names = items | views::transform(&Item::name) | std::ranges::to<std::vector>();
std::cout << std::format("{}\n", names);   // ["dates", "eggs", ...]
```

## Exercises
1. Remove `views::take(2)` in step 3 and run. How many times is the transform lambda called? Why is it never called for items out of stock?
2. Below step 5, add `auto it = std::ranges::find(makeNumbers(), 8); std::cout << *it;` and build. Which type does the compile error name? In the days of `std::find(v.begin(), v.end(), 8)`, what stopped the same mistake?
3. If you have MSVC, use the pipe form `| std::ranges::to<std::vector>()` and `std::format("{}", view)` as above. Also check which error the Linux preset gives.
