# C++ Evolution: Options Structs and Designated Initializers

## Why
`Tracer::diagramParts()` and `formatDiagram()` take a `DiagramBudget` with five limits. A caller usually wants to change one of them. How the options object is built decides whether the call site says *which* value it changes.

```cpp
struct DiagramBudget {
    std::size_t maxParticipants = 5;
    std::size_t maxMessages     = 15;
    std::size_t maxStates       = 12;
    std::size_t maxNodes        = 12;
    std::size_t labelWrap       = 24;
};
```

## C++14/17 (Legacy)
Either positional aggregate initialization, where every earlier field must be repeated and the reader has to count positions (C++14 or later: in C++11 a struct with default member initializers is not an aggregate, so not even this compiles):

```cpp
DiagramBudget budget{5, 30};             // which one is 30?
tracer.formatDiagram(DiagramBackend::Mermaid, budget);
```

or a builder/setter chain written by hand for every options type:

```cpp
auto budget = DiagramBudget{}.withMaxMessages(30);   // extra code per field
```

## C++20 (Modern)
Designated initializers name the field and keep every other default member initializer:

```cpp
tracer.formatDiagram(DiagramBackend::Mermaid, {.maxMessages = 30});
tracer.diagramParts(DiagramBackend::PlantUML, {.maxParticipants = 4, .labelWrap = 32});
```

Rules worth knowing:
- Designators must follow declaration order (`{.labelWrap = 32, .maxMessages = 30}` does not compile).
- Only aggregates qualify: no user-declared or inherited constructors, no private or protected non-static data members, no virtual functions, no virtual, private or protected base classes. (Private member functions and static members are fine.)
- Fields that are not named keep their default member initializers.

## C++23 (Latest)
Nothing new for designated initializers. The options-struct pattern combines well with C++23 code elsewhere in atugcc, for example a function that returns `core::Expected<Options>` (`std::expected<Options, CoreError>`, [`error.hpp`](/include/atugcc/core/error.hpp)) after validating user input, which the caller then passes on unchanged.

## In atugcc
- [`visualizer.hpp`](/include/atugcc/pattern/visualizer.hpp): `DiagramBudget`, `diagramParts()`, `formatDiagram()`
- [`example_visualizer.cpp`](/src/pattern/example_visualizer.cpp): Demo 4 uses `{.maxParticipants = 4}`
- Spec: [020-04](/docs/specs/020_04_diagram_readability.md)
