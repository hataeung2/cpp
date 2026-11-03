# Lesson: applying the State pattern to a device state machine (`device_state_machine`)

This lesson combines the `jthread_worker` unit (`PeriodicWorker`), the state machine of `atugcc::pattern::state` and `atugcc::pattern::viz::Tracer`: a background thread drives a device state machine periodically, and the transition history is visualized.

## 1. What the lesson does

The lesson covers:
- The State pattern in modern C++ (C++20/C++23) style: the state machine is built from `std::variant`, `std::visit` and the `overloaded` pattern, without virtual-function inheritance or heap allocation.
- A background `PeriodicWorker` thread calls the state machine's `schedule()` periodically (every 25ms) and makes the transitions `IDLE -> STANDBY -> RUN` in order.
- State transitions and the message call flow are recorded in `viz::Tracer` automatically.
- **Single-thread access**: while the worker thread runs, the `Machine` and the `Tracer` are used only inside the worker thread; the main thread reads the result safely after the worker has stopped and been joined.
- After the worker ends, the lesson prints the terminal ASCII trace (`tracer.formatTerminal()`) and the Mermaid state/sequence diagrams (`tracer.formatDiagram(viz::DiagramBackend::Mermaid)`).

## 2. Key concepts

### A State pattern built on `std::variant`
- The classic GoF State pattern manages concrete classes that inherit an `IState` interface through pointers (`std::shared_ptr` and the like) and dispatches through virtual functions.
- `atugcc::pattern::state::Machine` keeps the state as a value: `std::variant<IdleState, StandbyState, RunState, ...>`.
- `schedule()` and the transition rule check (`isTransitionAllowed`) branch through `std::visit` and the `overloaded` struct. The table of functions to call is built at compile time and picked at run time by the variant's index, so there is no virtual call (vtable) and no heap allocation per state, hence no memory fragmentation.

### How the transition rules work
- `Machine::transition(target)` first checks the transition rule matrix `isTransitionAllowed(current, target)`.
- A nested `std::visit` states explicitly, for each `(current state, target state)` pair, whether the transition is allowed.
- An attempt at a transition that is not allowed (for example `IDLE -> RUN`) leaves the state unchanged and returns a `std::unexpected` holding `core::CoreError::InvalidArgument`.

### Multithreaded synchronization and separate ownership
- To avoid complex lock (mutex) contention, the device state machine and the tracer are accessed by the worker thread alone (exclusive access) while it lives.
- The main thread reads the tracer and the state machine only after `worker.requestStop()` and `worker.join()` confirm that the worker thread has fully ended.

## 3. How to run

### Through ctest (smoke test)
```bash
ctest -R lesson.device_state_machine --output-on-failure
```

### Running the executable directly
```bash
# Windows
bin\lessons\lesson_device_state_machine.exe
# or, with a Debug configuration
bin\Debug\lessons\lesson_device_state_machine.exe

# Linux
bin/lessons/lesson_device_state_machine
```

## 4. Exercises

1. **Extend the transition sequence**: in the worker lambda, after reaching RUN (for example at `tick == 4`), call `machine.transition(state::AbortState{})` or `machine.transition(state::EmergencyState{})` to move to an emergency stop state. See how the new transition shows in the terminal trace and the diagram.
2. **Handle a transition that is not allowed**: at the first transition in the worker lambda (`tick == 1`), try to go from `IDLE` straight to `RunState` (`machine.transition(state::RunState{})`). Check which error (`InvalidArgument`) `res` holds, and log it.
3. **Other diagram backends**: at the end of `main`, call `tracer.formatDiagram(viz::DiagramBackend::PlantUML)` and `tracer.formatDiagram(viz::DiagramBackend::D2)` and compare the diagram formats.
