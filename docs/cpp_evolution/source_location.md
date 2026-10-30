# C++ Evolution: Caller Location and Whole-Line Output

## Why
A log line is only useful if it says where it came from. `atugcc::core::Logger` recorded the location inside its own header (`logger.hpp:41`) for every call, because `std::source_location::current()` was called in the logger's body instead of at the call site (KI-013). When several threads wrote to one stream, their lines could also mix. Task 010-08 fixes both without a macro.

## C++11/17 (Legacy): macros
```cpp
#define LOG_INFO(...) \
  ::logLine(Level::Info, __FILE__, __LINE__, __func__, fmt::format(__VA_ARGS__))

void logLine(Level lv, const char* file, int line, const char* func, const std::string& msg) {
  std::lock_guard lock(g_cout_mutex);  // every writer must know this mutex
  std::cout << '[' << name(lv) << "] [" << file << ':' << line << ' ' << func << "] " << msg << '\n';
}
```
- The macro is the only way to capture the caller's `__FILE__` / `__LINE__`.
- It ignores namespaces, cannot be overloaded, and shows up in error messages as its expansion.
- Whole lines need a mutex that every writer of `std::cout` shares by convention.

## C++20: `std::source_location` as a default argument
A default argument is evaluated **at the call site**, so `std::source_location::current()` there records the caller:
```cpp
void log(std::string_view msg, std::source_location loc = std::source_location::current());
log("hello");  // loc is this line
```
With variadic format arguments the location cannot be the last parameter (it would be swallowed by `Args&&...`), and it cannot come first without the caller writing it. The usual answer is to attach it to the **format string**: a small wrapper whose constructor takes the string and the location.
```cpp
template <typename... Args>
struct FormatWithLocation {
  std::format_string<Args...> fmt;
  std::source_location loc;

  template <typename S>
    requires std::convertible_to<const S&, std::string_view>
  consteval FormatWithLocation(const S& s, std::source_location l = std::source_location::current())
      : fmt(s), loc(l) {}
};

template <typename... Args>
void log(Level lv, FormatWithLocation<std::type_identity_t<Args>...> f, Args&&... args);

logger.log(Level::Info, "user {} logged in", id);  // unchanged call site, caller's file and line
```
- `consteval` keeps the compile-time check of the format string: `std::format_string`'s constructor is `consteval`, and passing it the wrapper's parameter `s` (not a constant by itself) is allowed only inside another immediate function. A `consteval` wrapper constructor is that function; the literal at the call site is the constant.
- `std::type_identity_t` keeps the wrapper out of template argument deduction: `Args` come from the arguments only, and the string literal converts to the wrapper.
- The `requires` clause keeps `log(Level::Info, ...)` from trying to turn `Level` into a format string.

## C++20: `std::osyncstream` for whole lines
```cpp
std::osyncstream(*out) << line << '\n' << std::flush;
```
The synchronized stream collects the line in its own buffer and writes it to the wrapped stream in one step when it is destroyed, under a lock that belongs to the wrapped stream buffer. Two `Logger`s that share `std::cout` (or a file) no longer interleave characters, and neither needs to know the other's mutex. `std::flush` here asks for the flush to happen inside that same step, so no thread flushes the shared stream outside the lock.

## C++23 (Current, atugcc)
- [`logger.hpp`](/include/atugcc/core/logger.hpp): `FormatWithLocation`, the two convenience `log` overloads, and the explicit `log(std::source_location, Level, std::format_string, ...)` for code that forwards a location it received.
- Failures of the crash-dump preparation are reported as `std::expected` (`atugcc::core::Result`), see [error_expected.md](/docs/cpp_evolution/error_expected.md).
- Related: `std::print` (C++23) writes formatted text to a stream or `FILE*` directly, but it does not by itself keep two writers' lines apart; `std::osyncstream` does.
