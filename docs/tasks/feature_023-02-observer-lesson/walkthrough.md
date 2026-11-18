# Walkthrough: 023-02 Observer

- Spec: [/docs/specs/023_02_observer_lesson.md](/docs/specs/023_02_observer_lesson.md) (approved 2026-11-18)
- Plan: [plan.md](plan.md), test record: [testrecord.md](testrecord.md)
- Branch: `feature/023-02-observer-lesson`

## Result
- **Header fix** ([`observer.hpp`](/include/atugcc/pattern/observer.hpp)): `notifyObservers()` walks a copy of the subscriber list. A callback that subscribes (vector reallocation) or calls `setData` again (`erase_if`) no longer invalidates the loop; before the fix ASan reported heap-use-after-free. Contract: a subscriber added during a notification gets the next one; one that expires during a notification is skipped at its turn. Comments state that the Subject is not thread safe, that nested `setData` recursion is the caller's responsibility, and that a callback must not destroy the Subject or its Tracer. Public API unchanged.
- **Tests**: `ObserverTest.SubscribeDuringNotifyStartsNextTime`, `ObserverTest.NestedSetDataIsSafe` (both fail on an index-loop implementation, R3); scenario `scenario.TracedObserver.SubscribeNotifyExpireDiagram` (subscribe → notify → one receiver gone → notify → Mermaid).
- **Lesson** [`patterns/sensor_observers`](/lessons/tracks/patterns/sensor_observers/README.md), after `device_state_machine`: a virtual `IObserver` with attach/detach next to concept + `weak_ptr` subscriptions; a receiver leaving its scope drops out with no `detach`; the Tracer's terminal trace and sequence diagram. Three automatic exercises (a third receiver type, reading the `ObserverOf` error, keeping a receiver alive). New tag `observer`.
- Links: `intro.md`/`intro.en.md`, `lesson_candidates.md` (E1 row), the essentials `concepts` README (both languages).

70/70 tests on `windows-x64-debug` and `linux-x64-debug`, no warnings (testrecord R9, R10).

## Units
U1–U8 `done` (plan.md). Code and tests by agy flash, small review fixes by the lead (`review fixes lead (small)` in U1, U2, U3, U5, U7). No `lead (fallback)` units. U2 (risky) reviewed by codex luna.

## Deviations
See testrecord "Deviations from the spec": the nested test is not the ASan-failing one; no `profile` line; concepts link placed in the intro sentence; `keep_panel` assumes a reset after exercise 1.

## Follow-ups
- KI-058 (DEFERRED): generalize `observer::Subject` (payload type, unsubscribe token, recursion and threading policy) in an engine task that needs an event system, with one more lesson (user decision 2026-11-18).
- KI-023 unchanged: `main.cpp`'s dead `observer::observerSample()` call is 070-04's.
- KI-057 unchanged: this task did not touch `web/`.
