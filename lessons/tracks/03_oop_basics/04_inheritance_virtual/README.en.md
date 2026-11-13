# Lesson: inheritance and virtual functions — virtual destructors, slicing, abstract classes, `final` (`inheritance_virtual`)

Inheritance writes "a derived class is a kind of base class" in code, and a virtual function makes **the real object's function** run even when it is called through a reference or pointer to the base class. This lesson checks it in six steps: a non-virtual call is decided by the declared type of the variable (static binding), `virtual` and `override` make the function of the real type run (dynamic binding), the destruction order with a virtual destructor, slicing that cuts off the derived part when you take an object by value, polymorphic use through an abstract class and `std::vector<std::unique_ptr<Shape>>`, and `final`. Deleting through a base-class pointer when the destructor is not virtual (undefined behaviour) is never run by this lesson; it is shown only with a trait (`std::has_virtual_destructor_v`) and in text. The comparison with value-type polymorphism (`std::variant`) is in [variant_visit](/lessons/tracks/01_essentials/08_variant_visit/README.en.md). Previous lesson: [copy_and_move](/lessons/tracks/03_oop_basics/03_copy_and_move/README.en.md).

## Common mistakes and the right way
| | Common mistake | Right way |
|---|---|---|
| Destructor | the base destructor is not virtual, so deleting through a base pointer does not run the derived destructor (undefined behaviour) | `virtual ~Base()` in the base class |
| Overriding | the signature is slightly off, so it is a **new function**, not an override | `override`: a mistake is a compile error |
| Passing by value | taking the base class by value cuts off the derived part (slicing) | take it by reference or pointer |
| Interface | an empty function as a default that means nothing | a pure virtual function `= 0`: an abstract class cannot be instantiated |
| No further inheritance | someone inherits and changes the override | `final` |

## Run
- Web playground: select it in the lesson tree, then Run
- Local: `cmake --build --preset <preset> --target lesson_inheritance_virtual`, then `bin/lessons/lesson_inheritance_virtual`, or `ctest --preset <preset> -R lesson.inheritance_virtual`

## What to look for
- Step 1: `name()` on a `PlainDerived` object is `PlainDerived::name`, but called through a `PlainBase&` it is `PlainBase::name`. A non-virtual function is decided by the declared type of the variable.
- Step 2: with `sound()` declared `virtual` and overridden in `Dog`, calling it through an `Animal&` still gives `woof`. Write `override` on an override: if the base class has no virtual function with the same signature, the compiler tells you.
- Step 3: `Resource` has a virtual destructor, so when `std::unique_ptr<Resource>` deletes a `FileResource`, `~FileResource` and `~Resource` run in turn (derived → base). Without a virtual destructor the derived destructor does not run, which is undefined behaviour. This lesson does not run that; it shows with `std::has_virtual_destructor_v` that `Resource` is `true` and `NonVirtualBase` is `false`. With `override`, the compiler checks that the derived destructor overrides the virtual one (exercise 2). A class with no `virtual` function at all can fall into the same danger without a warning, so make `virtual ~Base()` a habit for a base class.
- Step 4: `describeByValue(Animal)` takes a `Dog` by value and copies only the `Animal` part, so it prints `...` (slicing, defined behaviour). `describeByReference(const Animal&)` prints `woof`.
- Step 5: `Shape` has a pure virtual function, so `std::is_abstract_v<Shape>` is `true` and `Shape s;` does not compile. With the concrete types `Circle` and `Square` in a `std::vector<std::unique_ptr<Shape>>`, one loop handles different types.
- Step 6: `Square` is `final`, so it cannot be inherited from (`true`); `Circle` can be (`false`).

```cpp
class Shape {
public:
    virtual ~Shape() = default;                         // virtual destructor
    [[nodiscard]] virtual double area() const = 0;      // pure virtual function
};
class Circle : public Shape {
public:
    [[nodiscard]] double area() const override;         // override on an override
};
class Square final : public Shape { /* … */ };          // no further inheritance
```

## Exercises
The web practice mode (the default) edits a practice copy and leaves the original (`lessons/`) untouched. "Reset" below means ↺ Reset on the web and `py -3 tools/practice.py reset inheritance_virtual` locally (local practice: "Practice workspace" in [`lessons/README.md`](/lessons/README.md)).

1. Misspell `Dog`'s `sound()` as `soundd()` and build. What error does `override` give? What happens if you remove `override` (it builds, but how does the step 2 output change)? Reset it.
2. Remove `virtual` from `virtual ~Resource()` in `Resource` and build. Which line gives the error, and why is `~FileResource() override` an error? (If you remove `override` too it builds, but deleting a `FileResource` through a `std::unique_ptr<Resource>` is undefined behaviour, so **do not run it**.) Reset it.
3. In step 5 try to create a `Shape` object directly (`Shape base;`). What error do you get and which function does it name as pure virtual? Reset it.
4. Write a class that inherits from `Square` (`class BigSquare : public Square {};`). What error do you get? Reset it.
