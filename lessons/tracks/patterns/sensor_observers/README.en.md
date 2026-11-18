# Lesson: The Observer pattern: tell several receivers when a sensor value changes (`sensor_observers`)

When a device's sensor value changes, several receivers (a panel display, an alarm log) need to know. The Observer pattern lets the side that holds the value (the Subject) tell them without knowing each one. This lesson writes the same notification two ways: a virtual-function interface with a list of raw pointers (the old way), and concept plus `std::weak_ptr` subscriptions (the library's [`observer.hpp`](/include/atugcc/pattern/observer.hpp)). The `Tracer`'s record and diagram show how notifications change after one receiver goes away. The essentials lesson [`concepts`](/lessons/tracks/essentials/concepts/README.en.md) and the oop_basics lesson [`smart_pointers`](/lessons/tracks/oop_basics/smart_pointers/README.en.md) are good to read first. Background on concepts: [concepts.en.md](/docs/cpp_evolution/concepts.en.md).

## The old way and C++20

| | The old way (Step 1) | C++20 (Steps 2–3) |
|---|---|---|
| Shape of a receiver | Inherits `IObserver` and `override`s `update` | Any type with `onNotify` and `display`, no base class. The `ObserverOf` concept checks it at compile time |
| What the Subject holds | `std::vector<IObserver*>` (raw pointers) | Per subscription, a `std::weak_ptr` handle and the functions to call |
| When a receiver goes away | The receiver must `detach` first. Forgetting it leaves a dangling pointer in the list, and the next notification is undefined behaviour | Nothing to do. When the next notification starts, `expired()` filters it out (`std::erase_if`). A receiver that goes away during a notification is skipped at its turn because its `lock()` fails |
| A wrong receiver | Missing a pure virtual function gives an abstract-class error | A missing member function gives an error that it does not satisfy `ObserverOf` |

The lesson does not run the old way's danger (a forgotten `detach`): its result is not defined, so Step 1 is the safe version that does not forget `detach`.

This lesson uses `Subject::setData(d1, d2)` as (sensor name, value string). The library's `Subject` is a teaching implementation with two pieces of data (`data1()`, `data2()`); a receiver reads them when it is notified. `data1()` and `data2()` return `const` references to the Subject's members. Their value changes at the next `setData`, and a `std::string_view` into them may become invalid, so receivers keep a copy of the strings.

The Subject does not know the subscribers' concrete types. Per subscription it holds a handle that only watches the lifetime, `std::weak_ptr<void>`, and two functions to call (`std::function`); the concrete type (`std::weak_ptr<PanelDisplay>` and so on) lives only inside the lambdas `subscribe` makes (type erasure). So the Subject does not own a receiver; it only checks whether the receiver is still alive.

## Run
- Web playground: select it in the lesson tree, then Run
- Local: `cmake --build --preset <preset> --target lesson_sensor_observers`, then `bin/lessons/lesson_sensor_observers`, or `ctest --preset <preset> -R lesson.sensor_observers`

## What to look for
- **Step 1**: `legacy panel: temperature = 21.5`. The notification goes through a virtual call. In the code, notice that `detach` is separate from the receiver's lifetime.
- **Step 2**: the `display()` lines after both receivers got two values, and `receivers: 2`. `PanelDisplay` and `AlarmLog` have no base class; `subscribe` checks them with `ObserverOf`.
- **Step 3**: the panel went away when it left the Step 2 block. The third value reaches only the alarm: `alarm: 3 notification(s)`, `receivers: 1`, and `messages sent: 5` (2 + 2 + 1) so far. Nobody called `detach`.
- **Step 4**: the five notifications the `Tracer` recorded and a Mermaid sequence diagram. Consecutive notifications to the same receiver merge into one line, like `×2`. On the web, the step replay of the Diagrams tab shows one notification at a time.
- The library's `notifyObservers()` walks a **copy** of the subscriber list taken when the notification starts. So a receiver may add a new subscriber or call `setData` again while it is being notified; the new subscriber receives the next notification.

## Exercises
The web practice mode (the default) edits a practice copy and leaves the original (`lessons/`) untouched. "Reset" below means ↺ Reset on the web and `py -3 tools/practice.py reset sensor_observers` locally (local practice: "Practice workspace" in [`lessons/README.md`](/lessons/README.md)).

1. **A third receiver**: write one more receiver type with `onNotify` and `display` and no base class (for example a `FanControl` that switches on whenever the value changes), and subscribe it in Step 2. Done when `receivers: 3` appears. Reset it.
2. **Read a concept error**: delete the `display()` function of `PanelDisplay` and build. Which line fails, and why? Reset it.
3. **Change a receiver's lifetime**: keep the panel alive outside the Step 2 block (copy the block's `shared_ptr` into a variable outside the block). Done when Step 3's output shows `panel: temperature = 30.0`. Reset it.
