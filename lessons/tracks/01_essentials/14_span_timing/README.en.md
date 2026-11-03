# Lesson: span timing

Code ranges that do the same work in two ways are measured in turn with `tracer.timeScope("name")` for 15 seconds, and you compare which is faster, and by how much.
- `push_back` and `reserve + push_back`: filling a vector with 100,000 elements
- `std::map::find` and `std::unordered_map::find`: 10,000 lookups among 100,000 elements

How to use spans and what they cost: the [020-06 spec](../../../../docs/specs/020_06_tracer_span_timing.md) and "성능 측정 레슨 작성" (writing a performance lesson) in [lessons/README.md](../../../README.md) (both in Korean).

## Run
- Web playground: select it in the lesson tree, then Run.
  - This lesson has `profile = "long"`, so the run limit is 120 seconds. It is built optimized (`linux-x64-playground-release`, RelWithDebInfo).
  - The **Timings** tab opens during the run and keeps updating. The time of each range also appears at the end of its `timeScope` line in the editor as `⏱ … avg ×N`.
- Local:
  - `cmake --build --preset <preset> --target lesson_span_timing`, then run `bin/lessons/lesson_span_timing`. The `formatTimings()` table is printed at the end.
  - To run it as a smoke test, use `ctest --preset <preset> -R lesson.span_timing` (label `long`).

## What to look for
- The mean of `reserve + push_back` is smaller than that of `push_back`: the cost of reallocating and moving is gone.
- `std::unordered_map::find` is faster than `std::map::find`: one hash finds the element, without walking down a tree.
- A range whose p95 jumps well above its mean is sometimes slow because of allocation or caches. Click ▸ on the row to see the distribution.
- Switch the meter at the top to `cpu` and run again: the values are almost the same as `wall`, because these ranges only compute and never wait.

## Exercises
1. Comment out the `reserve` line in `fillWithReserve` (`// values.reserve(kElements);`) and press Run. In the "vs previous" column of Timings, check the change of `reserve + push_back`. Deleting the line instead would shift the line numbers of the spans below it, making them different rows that are not compared.
2. Add `build = "debug"` under `[run]` in this lesson's `lesson.toml` and run it. The times grow several-fold, and the "vs previous" column says "different build". Write down why Debug times must not be used to judge performance. Delete the line when you are done.
3. Change `lookUp` so that each turn of its `for` loop is measured as its own span. See how much the number of rounds drops in the same 15 seconds and what the view shows, and explain the advice "measure the range outside a hot loop, not inside it".
