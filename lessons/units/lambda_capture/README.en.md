# Unit: lambda_capture

A lambda is an object of an unnamed class whose members are what it captured. The capture mode decides whether such a member is a **copy** or a **reference to the original**.

| Function | Capture | What the closure holds | Watch out |
|---|---|---|---|
| `makeCounterByValue(start)` | `[count = start]` + `mutable` | a member `count` copied from `start` | Only its own value changes, whatever happens to the original variable |
| `makeAdderByReference(total)` | `[&total]` | a reference to `total` | If the lambda lives longer than `total`, the reference dangles |
| `makeGreeter(name)` | `[name = std::move(name)]` | the name string (moved in) | Take the argument by value and move it into the closure |
| `makeOwner(value)` | `[value = std::move(value)]` | a `unique_ptr` | The closure becomes move-only. `std::function` cannot hold it; `std::move_only_function` (C++23) can |

Used by the lesson `lambda_capture` (essentials track).
