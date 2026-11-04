# C++ Evolution: Text Formatting

## Why
Every program prints numbers, tables and log lines. Before C++20 the choice was between `printf`, which is short but not type-safe, and `iostream`, which is type-safe but verbose and keeps formatting state in the stream. `std::format` (C++20) gives `printf`'s compact format strings with type checking at compile time, and `std::print` (C++23) writes the result to a stream or `FILE*` in one call. atugcc's `Logger` takes `std::format_string`, so log calls get the same compile-time check.

Lesson: [`format_text`](/lessons/tracks/01_essentials/02_format_text/README.en.md) (essentials track).

## C++11/17 (Legacy): `printf` and `iostream`
```cpp
std::printf("%-10s|%6d|%6.1f%%\n", name.c_str(), count, share);   // %d with a long: undefined behaviour
std::printf("%s\n", count);                                        // compiles (warning at best); undefined behaviour, typically a crash

std::cout << std::left << std::setw(10) << name << '|'
          << std::right << std::setw(6) << count << '|'
          << std::fixed << std::setprecision(1) << std::setw(6) << share << "%\n";
// std::fixed and setprecision stay on std::cout for every later output
```
- `printf` trusts the format string: a wrong conversion is undefined behaviour, not a compile error. A user type needs a `to_string` helper first.
- `iostream` is type-safe, but one table row takes many manipulators, some of them sticky, and translating a sentence means reordering `<<` chains.
- The `{fmt}` library introduced the `{}` syntax that became `std::format`.

## C++20: `std::format`
```cpp
std::string row = std::format("{:<10}|{:>6}|{:>6.1f}%", name, count, share);
std::string order = std::format("{0} -> {1} -> {0}", "idle", "run");   // positional arguments, reused
std::format("{}", count, extra);   // fine: extra arguments are ignored
std::format("{:d}", name);         // compile error: std::format_string checks the string against the types
```
- The format string is a `std::format_string<Args...>` whose constructor is `consteval`: a bad specifier or a missing argument is a **compile error**.
- A string known only at run time goes through `std::vformat(text, std::make_format_args(args...))`, which throws `std::format_error` instead.
- `std::format_to(std::back_inserter(buffer), ...)` appends to an existing buffer; `std::formatted_size` tells the length first.
- User types plug in by specializing `std::formatter<T>` (`parse` reads the specifier, `format` writes the value), and then work in every `{}` context, the Logger included.

## C++23: `std::print`
```cpp
std::print("{:<10}|{:>6}\n", name, count);   // to stdout in one call
std::println(stderr, "error: {}", message);  // with a newline, to a FILE* or std::ostream
```
- When the program is compiled as UTF-8 (MSVC `/utf-8`), `std::print` to a Windows console writes Unicode through the console API, whatever the console code page is.
- Every toolchain of this project has it now: MSVC, and on Linux libstdc++ 14 with Clang 20 (spec 070-13; GCC 13, the earlier Linux toolchain, had no `<print>`). The `format_text` lesson has a `std::print` / `std::println` step (step 7, task 070-14): the same table row through `std::println` and through `std::cout`, its `Vec2` formatter in `std::println`, and `std::print(stdout, …)`.
- For log lines from many threads use the `Logger`: it formats on the calling thread and writes whole lines from one log thread (see [lock_free_logging.md](/docs/cpp_evolution/lock_free_logging.md)).

## C++23 (Current, atugcc)
- [`logger.hpp`](/include/atugcc/core/logger.hpp): `Logger::log` takes a `std::format_string` wrapped with the call location (`FormatWithLocation`, see [source_location.md](/docs/cpp_evolution/source_location.md)), so a wrong log format is a compile error.
- New code uses `std::format`, not `{fmt}` ([impl.md](/.agent/rules/impl.md) §2).
