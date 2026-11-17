# Lesson: source location tracking (`source_location`)

A log line is only useful if it says where it came from. This lesson shows the same job in four steps: the `__FILE__`/`__LINE__` macro → a `std::source_location` default argument → a wrapper that receives the location and passes it on → attaching the location to the format string for variadic arguments. At the end, `atugcc::core::Logger` records the calling line the same way. Background: [source_location.en.md](/docs/cpp_evolution/source_location.en.md).

## The old way and C++20
| | Old (macro) | C++20 (`std::source_location`) |
|---|---|---|
| Where the location comes from | the macro expands `__FILE__`, `__LINE__`, `__func__` where it is used | the default argument `std::source_location::current()` is evaluated **at the call site** |
| Namespaces, overloads | a macro knows neither | an ordinary function, so both work |
| Error messages | show the expanded macro | show the function name |
| Variadic arguments | `__VA_ARGS__` | the location cannot be the last parameter → attach it to a type that wraps the format string |

## Run
- Web playground: select it in the lesson tree, then Run
- Local: `cmake --build --preset <preset> --target lesson_source_location`, then `bin/lessons/lesson_source_location`, or `ctest --preset <preset> -R lesson.source_location`

## What to look for
- The lines of steps 1–4 look like `[main.cpp:<line> <function>] ...`. `<line>` is the **calling line** of that step. Compare it with the line numbers in the editor.
- The two lines of step 2 have different line numbers. The one called inside `startEngine()` points into `startEngine`, and its function name differs too (the function name string differs between compilers: MSVC writes `void __cdecl …`).
- `warning: low memory` in step 3 points at the line in `main` that calls `warn`, not at a line inside `warn`, because `warn` passes the `loc` it received on.
- The Logger line of step 5 shows the full path of the file. The Logger does not shorten it.

## Exercises
1. Delete the `loc` parameter of `warn` and make it call only `logHere(std::format("warning: {}", msg))`. See where the line number of step 3 moves, and write down why a wrapper has to receive the location again.
2. Change `Here<std::type_identity_t<Args>...>` in `logFormat` to `Here<Args...>` and compile. Which error do you get, and what does `std::type_identity_t` prevent?
3. Add a call with the wrong number of arguments, like `logFormat("port {}", 8080, 9090);`, and `logFormat("port {:d}", "x");`. Find out which one is a compile error and who does the check (the consteval constructor of `std::format_string`).
