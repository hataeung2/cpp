# Lesson: filesystem — paths, listing and errors with `std::filesystem` (`filesystem_paths`)

Creating the log and crash-dump folders, building file names, and finding out why the disk said no: `std::filesystem` does it. This lesson prints joining and splitting paths, creating a sandbox folder `fs_sandbox/` under the working directory with three files, listing it (recursively too), the two error styles (exceptions and `std::error_code`) and wrapping one in the library's `core::Expected`, and turning a modification time into a date with `clock_cast`; at the end it deletes the sandbox. The library's [`memory_dump.hpp`](/include/atugcc/core/memory_dump.hpp) (`ensurePrepared`, implemented in [`memory_dump.cpp`](/src/core/memory_dump.cpp)) prepares the dump folder the same way (`create_directories` with an `error_code`, failure as `CoreError::FileIOFailure`). Background: [filesystem.en.md](/docs/cpp_evolution/filesystem.en.md).

## The old ways and C++17/20
| | Platform APIs and strings | `std::filesystem` |
|---|---|---|
| Paths | `std::string` and `"/"` concatenation; the separator differs by OS | `fs::path` and the `/` operator, `filename()`, `stem()`, `extension()`, `parent_path()` |
| Creating folders | `mkdir` / `CreateDirectoryA`: one level at a time | `create_directories`: every missing level |
| Listing | `opendir`, `readdir` / `FindFirstFile`, `FindNextFile` | `directory_iterator`, `recursive_directory_iterator` (`depth()`) |
| Errors | `-1` and `errno` / `FALSE` and `GetLastError()` | exceptions (`filesystem_error`) or the `std::error_code&` overloads |
| Modification time | `stat`'s `st_mtime` / `FILETIME` | `last_write_time` and C++20 `clock_cast<system_clock>` |

## Run
- Web playground: select it in the lesson tree, then Run (the sandbox is `fs_sandbox/` under the lesson folder)
- Local: `cmake --build --preset <preset> --target lesson_filesystem_paths`, then `bin/lessons/lesson_filesystem_paths`, or `ctest --preset <preset> -R lesson.filesystem_paths` (the sandbox is under the build folder)

`fs_sandbox/` is deleted and created again at the start of a run and deleted at the end. A folder left behind by a run that was killed is deleted by the next run. Two runs of the lesson in the same folder at the same time (for example ctest and the web in one folder) can delete each other's sandbox. It is listed in `.gitignore`.

## What to look for
- Step 1: paths are joined with `/` and taken apart. Every line uses `generic_string()` (separator `/`), so both OSes print the same, except the one `preferred_separator` line: `\` on Windows, `/` on Linux.
- Step 2: the files are written in **binary mode**. Windows text mode turns `\n` into `\r\n`, so sizes would differ between OSes. The files are closed at the end of a block before their sizes are read (before closing, buffering can make the size 0).
- Step 3: the standard does not specify the listing order, so the lines are collected and sorted before printing. `recursive_directory_iterator`'s `depth()` is how many levels below the start folder an entry is.
- Step 4: asking for the size of a missing file with the throwing overload gives a `filesystem_error` whose `path1()` is that path. The `error_code` overload does not throw: it fills `ec` and returns `(uintmax_t)-1`. The lesson compares `ec` with `std::errc::no_such_file_or_directory` instead of printing a message (messages differ between OSes, for example `No such file or directory` on Linux and a different sentence in the system language on Windows). `fileSize` turns the `error_code` into a `core::Expected`, so it chains with `and_then` and `or_else` as in the lesson `error_expected`.
- Step 5: the standard leaves `file_clock`'s epoch unspecified, so the time is converted with `clock_cast<system_clock>` before printing the date (a UTC date: it depends on the day you run it). At the end the lesson prints how many entries `remove_all` deleted (3 files, 2 folders, the sandbox itself) and checks that the sandbox is gone.

## Exercises
1. Remove the sorting in step 3 and run several times (better: on both OSes). Is the order always the same? Even if it is, why should you not rely on it?
2. Copy the subfolder with `fs::copy(box / "logs", box / "logs_copy", fs::copy_options::recursive)` and make it show up in step 3's listing. How does the count deleted by `remove_all` change?
3. Print step 5's `ft.time_since_epoch()` as it is and compare it on both hosts. If the numbers differ a lot for files created on the same day, explain why `clock_cast` is needed.
