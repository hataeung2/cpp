# Lesson: lambda capture

Run four capture modes and see in the output what the closure copies and what it refers to. The explanation table is in the [unit README](../../../units/lambda_capture/README.en.md).

## Run
- Local: `cmake --build --preset <preset> --target lesson_lambda_capture`, then run `bin/lessons/lesson_lambda_capture`, or `ctest --preset <preset> -R lesson.lambda_capture`
- Web playground (070-02): select it in the lesson tree, then Run

## What to look for
- The counter copied with `second = first` counts on its own, apart from `first` (output `11, 12 / 11`).
- `add`, captured by reference, changes `total` in `main`.
- A closure that holds a `unique_ptr` does not fit in a `std::function`, but fits in a `std::move_only_function`.

## Exercises
1. Delete `mutable` in `makeCounterByValue` and read the compile error. Why can `count` not be changed?
2. Write a function that **returns** a lambda capturing a local variable by reference, call it, and explain what dangles. Build with the `linux-x64-asan` preset and **run** it with `ASAN_OPTIONS=detect_stack_use_after_return=1`: ASan reports `stack-use-after-return` (building alone does not show it).
3. Change the type of `holder` to `std::function<int()>`, see which error you get, and write down why.
