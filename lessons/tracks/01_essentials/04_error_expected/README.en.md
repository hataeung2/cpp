# Lesson: error handling — exceptions and `std::expected` (`error_expected`)

The same job, reading the port from a config line `port=8080`, is written two ways: one throws exceptions (`parsePortThrowing`), the other returns `atugcc::core::Expected` (`parsePort`). You see the results for the same four inputs side by side, then chain steps with C++23 `and_then`, `transform` and `or_else`. The whole library uses the same types (`core::Expected<T>`, `core::Result`, `core::CoreError`, [`error.hpp`](/include/atugcc/core/error.hpp)), so after this lesson you can read the return values of library functions directly. Background: [error_expected.md](/docs/cpp_evolution/error_expected.md).

## Exceptions and `std::expected`
| | Exceptions | `std::expected<T, E>` (C++23) |
|---|---|---|
| Where failure shows | not in the function signature; you have to read the docs or the code | in the return type |
| If nobody handles it | it travels up, and `std::terminate` if nobody catches it | you must check before taking the value (together with `[[nodiscard]]`) |
| Chaining steps | several calls in one `try` | `and_then` (the next step can fail too), `transform` (changes the value only), `or_else` (turns a failure into another value or error) |
| Good for | truly exceptional events, constructor failure | **expected** failures such as input checks or opening a file |

## Run
- Web playground: select it in the lesson tree, then Run
- Local: `cmake --build --preset <preset> --target lesson_error_expected`, then `bin/lessons/lesson_error_expected`, or `ctest --preset <preset> -R lesson.error_expected`

## What to look for
- Step 1: for `abc` and the empty string `std::stoi` throws `invalid_argument`; for `70000` the range check throws `out_of_range`. From the signature alone, the caller cannot tell which exception may come.
- Step 2: the same inputs come out as `-> error InvalidArgument`. The reason for the failure comes back as a value and is printed with `core::to_string`.
- Step 3: `port=80` parses but fails in `requireUnprivileged`. `host=example` fails in the first step, `valueOf`, and the later steps are not called. The last line, with `or_else`, uses the default port 8080 instead of failing.

## Exercises
1. Delete the `catch (const std::out_of_range& e)` clause in step 1 and run. See what happens at `70000` (on the web, the exit code is not 0), and explain what "the exception is not visible in the signature" means. Undo it afterwards.
2. Make the `transform` lambda in step 3 return `core::Expected<std::string>` instead of `std::string`. See what the result type becomes, and why `and_then` is the right call in that case.
3. What would you change to print "port out of range" and "not a number" differently? `CoreError` is the library's shared vocabulary, so no value is added to it for one lesson. Give the lesson its own error type (`enum class PortError`) and switch to `std::expected<std::uint16_t, PortError>`.
