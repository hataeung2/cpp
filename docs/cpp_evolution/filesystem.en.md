# C++ Evolution: Files and Directories (`std::filesystem`)

## Why
Logs, crash dumps and recovered log maps all need a folder that exists, a file name built from parts, and a clear answer when the disk says no. Before C++17 every one of those steps was a platform call with its own path type and its own error convention. `std::filesystem` (C++17) gives one `path` type, portable directory operations, and two error styles to choose from: exceptions or `std::error_code`. atugcc prepares its dump folder with it and turns the error code into its own `Expected` value.

Lesson: [`filesystem_paths`](/lessons/tracks/01_essentials/10_filesystem_paths/README.en.md) (essentials track).

## C++11/14 (Legacy): strings and platform APIs
```cpp
std::string path = dir + "/" + name;                 // "\\" on Windows? both work, but not everywhere
#ifdef _WIN32
CreateDirectoryA(dir.c_str(), nullptr);              // one level only, BOOL + GetLastError()
WIN32_FIND_DATAA fd; HANDLE h = FindFirstFileA((dir + "\\*").c_str(), &fd);
#else
mkdir(dir.c_str(), 0755);                            // one level only, -1 + errno
DIR* d = opendir(dir.c_str()); while (dirent* e = readdir(d)) { /* ... */ } closedir(d);
#endif
```
- Paths are plain strings: joining, taking the extension or the parent folder is string surgery, and the separator differs.
- Creating `a/b/c` needs a loop; listing a folder needs two APIs and manual cleanup.
- Errors come back as `BOOL`/`-1` plus `GetLastError()`/`errno`, read immediately or lost.

## C++17: `std::filesystem`
```cpp
namespace fs = std::filesystem;
fs::path p = fs::path{"logs"} / "2026" / "app.log";   // p.filename(), p.stem(), p.extension(), p.parent_path()
fs::create_directories(dir);                          // every missing level
for (const auto& entry : fs::recursive_directory_iterator(dir)) { /* entry.path(), entry.file_size() */ }
fs::remove_all(dir);                                  // returns how many entries it removed

std::uintmax_t size = fs::file_size(p);               // throws fs::filesystem_error (path1(), code())
std::error_code ec;
std::uintmax_t size2 = fs::file_size(p, ec);          // no throw: ec set, returns static_cast<std::uintmax_t>(-1)
if (ec == std::errc::no_such_file_or_directory) { /* ... */ }
```
- `path` stores the native form; `generic_string()` always uses `/`, `string()` returns the stored form as it is, and `operator/` joins with `fs::path::preferred_separator` (`\` on Windows).
- Every operation has an exception overload and an `std::error_code&` overload. Code that must not throw for file-system errors (a crash handler's preparation, a `noexcept` function) uses the second; a few of those overloads (`create_directories`, `remove_all`) are still not `noexcept` and can throw `std::bad_alloc`, which is why `memory_dump.cpp` also keeps a `try`.
- Directory iteration order is **unspecified**: sort when the order matters.
- `fs::last_write_time` returns `fs::file_time_type`, whose clock (`file_clock`) has an epoch the standard leaves unspecified.

## C++20: file times as calendar times
```cpp
auto ft = fs::last_write_time(p);
auto sys = std::chrono::clock_cast<std::chrono::system_clock>(ft);   // works with every standard library
std::string day = std::format("{:%F}", sys);
```
- `clock_cast` converts between any two clocks that know how (`file_clock`, `system_clock`, `utc_clock`, …). It is the portable choice for `file_clock`: the standard lets each library give `file_clock` either `to_sys`/`from_sys` (libstdc++) or `to_utc`/`from_utc` (MSVC), and `clock_cast` uses whichever exists. It builds on MSVC and on the Linux toolchain (Clang 20 + libstdc++ 14; GCC 13's libstdc++ had no `clock_cast`).

## C++23 (Current, atugcc)
- [`memory_dump.hpp`](/include/atugcc/core/memory_dump.hpp) / [`memory_dump.cpp`](/src/core/memory_dump.cpp): `MemoryDump::ensurePrepared(dir)` calls `fs::create_directories(dir, ec)` inside a `noexcept` function and turns a failure into `std::unexpected(CoreError::FileIOFailure)` ([`error.hpp`](/include/atugcc/core/error.hpp), [error_expected.en.md](/docs/cpp_evolution/error_expected.en.md)).
- [`log_buffer_config.hpp`](/include/atugcc/core/log_buffer_config.hpp): `configureLogBuffers({.mappedDir = …})` takes a `std::filesystem::path` for the memory-mapped log folder.
