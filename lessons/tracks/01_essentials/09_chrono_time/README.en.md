# Lesson: working with time — `std::chrono` durations, clocks, calendar, time zones (`chrono_time`)

Log timestamps, timing a piece of code, "the same day next month", "what time is it in Seoul": `std::chrono` does all of it. In five steps this lesson prints duration conversions, timing with `steady_clock`, calendar dates and repairing an invalid one, converting a **fixed instant** between time zones (including a time that does not exist because of daylight saving), and chrono formatting with its inverse, `parse`. The library's [`TimeStamp`](/include/atugcc/core/timestamp.hpp) builds log timestamps with the same `zoned_time` and `std::format`. Background: [chrono_format.md](/docs/cpp_evolution/chrono_format.md).

## The old ways and C++20
| | C time functions | `std::chrono` (C++20) |
|---|---|---|
| Units | `time_t` (seconds) and integers; the unit lives only in the variable name | the unit is in the type, like `std::chrono::milliseconds`; lossy conversions are explicit with `duration_cast`, `round`, `floor` |
| Elapsed time | `time()` or `clock()`: wrong when the wall clock changes | `steady_clock`: never goes backwards |
| Dates | `struct tm`, months from 0, `mktime` silently "fixes" invalid dates | `year_month_day` with `ok()`, `February/last` |
| Time zones | `localtime_r` / `_localtime64_s`: only this machine's zone, a different function per platform | `zoned_time{"Asia/Seoul", t}`: any zone by name, with its daylight-saving rules |
| Text | `strftime(buf, sizeof buf, "%F %T", &tm)` | `std::format("{:%F %T}", t)`, reading back with `std::chrono::parse` |

The old-style code is in [chrono_format.md](/docs/cpp_evolution/chrono_format.md). `std::localtime` gives warning C4996 on MSVC, and this repository treats warnings as errors, so it is not in the lesson code.

## Run
- Web playground: select it in the lesson tree, then Run
- Local: `cmake --build --preset <preset> --target lesson_chrono_time`, then `bin/lessons/lesson_chrono_time`, or `ctest --preset <preset> -R lesson.chrono_time`

## What to look for
- Step 1: there are three ways to turn `1500ms` into seconds. `duration_cast` truncates toward zero (`1s`, `-1s`), `round` goes to the nearest value (`2s`; an exact tie goes to the even one, so `2500ms` is also `2s`), `floor` rounds down (`-2s`). Adding durations of different units gives the finer unit (`90min`).
- Step 2: `sleep_for(20ms)` sleeps **at least** 20 ms. The rounded ms value differs from run to run. `steady_clock` has `is_steady` true; the wall clock `system_clock` can move back when the time is synchronized, so it is false.
- Step 3: 29 February exists in 2024 and not in 2023. Adding one month to 31 January gives `2026-02-31`, and `ok()` is false. `year/month/last` moves it to the last day of that month.
- Step 4: the same instant `2026-11-03 09:00 UTC` is 18:00 in Seoul (`+0900`), 04:00 in New York (`-0500`) and 10:00 in Berlin (`+0100`). Because the instant is fixed, both OSes print the same lines. On 8 March 2026 New York jumps from 02:00 to 03:00, so 02:30 does not exist, and `choose::earliest` picks 03:00 (`-0400`). Time zone abbreviations (`%Z`) are not used: the same Seoul zone prints as `KST` on Linux (libstdc++) and `GMT+9` on Windows (MSVC). Where there is no time zone database (some containers), the lesson prints `time zone database unavailable: …` and carries on.
- Step 5: `%A` is the weekday, `%j` the day of the year, and `hh_mm_ss` shows a duration as hours:minutes:seconds. `parse` is the inverse of formatting: it reads the string back into a time, equal to the instant of step 4. The last two lines (`current_zone`, `TimeStamp::str()`) are **now** and this machine's time zone, so they differ between runs and machines. The web playground uses the time zone of WSL.

## Exercises
1. Add `std::chrono::seconds s = 1500ms;` and build. Why is it a compile error? Why does `std::chrono::milliseconds m = 2s;` compile?
2. Add another city to step 4 (for example `Australia/Sydney`), and build a time that exists **twice**, such as 01:30 on 1 November 2026 in New York when daylight saving ends, catching `ambiguous_local_time`. How do `choose::earliest` and `choose::latest` differ?
3. Give step 5's `parse` the date that does not exist, `"2026-02-30 09:00"`, and compare the stream's `fail()` on both hosts. libstdc++ reports a failure and MSVC accepts it (checked 2026-11-04). That is why the lesson reads only a valid string. With untrusted input, format the parsed value back with the same format and compare it with the original string (and look at what MSVC produced).
