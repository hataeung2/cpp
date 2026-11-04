# Lesson: polymorphism — virtual functions and `std::variant` (`variant_visit`)

The same two shapes (a circle and a rectangle) are written two ways: a base class `Shape` with virtual functions in a `std::vector<std::unique_ptr<Shape>>`, and `Circle` and `Rect` without a base class held in `std::variant<Circle, Rect>` and handled with `std::visit`. After both print the same thing, the lesson compares where you edit to add a new operation (`perimeter`) or a new type, the functions that look inside a variant, and the memory layout. The library's `state.hpp` builds a state machine with the same `overloaded` helper, and the lesson [`device_state_machine`](/lessons/tracks/02_patterns/01_device_state_machine/README.en.md) uses it.

## Virtual functions and `std::variant`
| | Virtual hierarchy | `std::variant` + `std::visit` |
|---|---|---|
| List of types | open: anyone can derive from `Shape` | closed: only the ones written in `variant<Circle, Rect>` |
| Adding an operation | change the base class and **every** derived class | write one new visitor; the types stay as they are |
| Adding a type | write one new derived class | add the type to the `variant`; every visitor that misses it is a **compile error** |
| Storage | one heap allocation per element (`std::make_unique`), a pointer | the value itself, no heap allocation |
| Call | an indirect call through the vtable | a call chosen by the discriminator (`index()`) |

## Run
- Web playground: select it in the lesson tree, then Run
- Local: `cmake --build --preset <preset> --target lesson_variant_visit`, then `bin/lessons/lesson_variant_visit`, or `ctest --preset <preset> -R lesson.variant_visit`

## What to look for
- Steps 1 and 2: both ways print the same lines. In step 2, `area` is visited with one generic lambda (`[](const auto& s) { return s.area(); }`), `name` with `overloaded`, which has one lambda per type. `overloaded` is a three-line helper that inherits from the lambdas and brings in all their `operator()`s.
- Step 3: adding `perimeter` changed not one line of `Circle` or `Rect`. With virtual functions you would add a pure virtual function to `Shape` and change both derived classes.
- Step 4: `index()` is the position of the type it holds now, `holds_alternative` tells whether it holds that type, `get_if` gives a pointer if so and `nullptr` if not. `std::get` with the wrong type throws `std::bad_variant_access`. The exception message differs between standard libraries, so it is not printed.
- Step 5: a `variant` is about the size of its largest type plus a discriminator (the values can differ between platforms). A `unique_ptr` is one pointer, but each element's object is a separate heap allocation.

## Exercises
1. Write `struct Triangle { double base; double height; [[nodiscard]] double area() const { return 0.5 * base * height; } };` and change to `std::variant<Circle, Rect, Triangle>`. The `overloaded` visitors for `name` and `perimeter` stop compiling. Why does the generic lambda for `area` not fail? Is that an advantage or a risk?
2. In the `uses` tab of the lesson [`device_state_machine`](/lessons/tracks/02_patterns/01_device_state_machine/README.en.md), open `state.hpp` and find whether its state transitions are written the same way as steps 2 and 3 here (states in a `std::variant`, `overloaded` visitors).
3. Count how many places you must change to add `perimeter` to the virtual-function side, then add it.
