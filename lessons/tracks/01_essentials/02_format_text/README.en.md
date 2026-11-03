# Lesson: text formatting — `std::format` (`format_text`)

Every program turns numbers, tables and log lines into text. This lesson prints the features of `std::format` (C++20) in six steps: positional arguments, width/fill/alignment, bases and precision, a `std::formatter` for a user type, appending to a buffer (`std::format_to`), and a format string received at run time (`std::vformat`). `atugcc::core::Logger::log` takes a `std::format_string` too ([`logger.hpp`](/include/atugcc/core/logger.hpp); this lesson does not use the Logger, it only shows where that happens), so the formats you see here work the same in log lines. Background: [format.md](/docs/cpp_evolution/format.md).

## The old ways and C++20/23
| | `printf` | `iostream` | `std::format` (C++20) | `std::print` (C++23) |
|---|---|---|---|---|
| Type checking | none (a mistake is undefined behaviour) | yes | yes, including the format string, **at compile time** | same as `std::format` |
| One table row | short (`%-10s%6d`) | several manipulators, some stay on the stream (`std::fixed`) | short (`{:<10}{:>6}`) | same, printed to the stream directly |
| User types | convert to a string first | `operator<<` | specialize `std::formatter<T>` | same |
| Reordering (translation) | not in ISO C (POSIX has `%1$s`) | not possible | `{1} {0}` | same |

The lesson code does not use `std::print`: GCC 13 in the web playground has no `<print>` (it comes with GCC 14). MSVC has it (exercise 3).

## Run
- Web playground: select it in the lesson tree, then Run
- Local: `cmake --build --preset <preset> --target lesson_format_text`, then `bin/lessons/lesson_format_text`, or `ctest --preset <preset> -R lesson.format_text`

## What to look for
- Step 1: `{0}` is used twice, so the same argument is written again (`idle -> run -> idle`).
- Step 2: the heading, the separator line (`{:-<10}`, fill character `-`) and the three rows line up at the same widths. Numbers are right-aligned, names left-aligned.
- Step 3: `{:#x}` gives `0xff`, `{:#o}` gives `0377`, `{:012b}` gives `000011111111` (width 12, filled with zeros). `{:>12.2f}` is width 12 with two decimals.
- Step 4: `Vec2` with `{:.1}` gives `(1.5, -2.2)`. Why not `-2.3`: 2.25 is exact in binary, and rounding goes to the nearest even digit (round half to even).
- Step 5: `std::format_to` appends three times to the end of the same `std::string`.
- Step 6: a run-time string is formatted with `std::vformat`, and the bad format `"{0} {"` is not a compile error but a `std::format_error` at run time. The message text differs between standard libraries.

## Exercises
1. Delete one argument of `std::format("dec: {}, hex: {:#x}, …", …)` in step 3. Read the compile error and find out who does the check (the consteval constructor of `std::format_string`). What happens if you add one argument **more** instead?
2. Add a `p` presentation to the `Vec2` formatter so that `{:p}` writes polar coordinates `(r, θ)`. Read `p` in `parse` and use `std::hypot`, `std::atan2` in `format`.
3. On the MSVC preset (`windows-x64-debug`), add `#include <print>` and write `std::println("{}", point);`. See which error the Linux preset gives.
