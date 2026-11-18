# Lesson: value semantics and operators — `operator<=>`, operator overloading (`value_semantics`)

Copies of an `int` are independent, and you compare its values with `==` and `<`. A type you write yourself can also be handled **like a value** (value semantics), and that takes copying, comparison and the operators it needs. This lesson checks it in five steps: copies of a value type are independent and equality is decided by value (`== = default`), unlike reference semantics where two `shared_ptr`s share one object; writing the six comparison operators by hand, where one mistake makes the six disagree; getting all six at once with `operator<=>` as `= default`, and sorting; writing `<=>` and `==` yourself for a fraction, where memberwise comparison is not the meaning; and when and how to overload operators such as `+=`, `+` and `<<`. Previous lessons: [copy_and_move](/lessons/tracks/oop_basics/copy_and_move/README.en.md) (copy and move), [smart_pointers](/lessons/tracks/oop_basics/smart_pointers/README.en.md) (`shared_ptr`).

## Common mistakes and the right way
| | Common mistake | Right way |
|---|---|---|
| Equality | a hand-written `==` comparing the members one by one (a new member gets forgotten) | `bool operator==(const T&) const = default;` |
| Ordering | writing `==`, `!=`, `<`, `<=`, `>` and `>=` by hand, so that one mistake makes them disagree | `auto operator<=>(const T&) const = default;`: all six, in the members' declaration order |
| Comparison with another meaning | the default comparison for a type whose value has several forms (1/2, 2/4) | write `<=>` and `==` yourself with the same rule; `std::weak_ordering` when equivalent is not equal |
| Writing `<=>` yourself | writing only `<=>` and expecting `==` to appear | write `==` too (`!=` comes on its own) |
| Arithmetic operators | `+` and `+=` implemented separately, so the rule lives in two places | `+=` as a member, `+` as a non-member that uses `+=` |
| Output | a member function such as `print()` | `std::ostream& operator<<(std::ostream&, const T&)` |

## Run
- Web playground: select it in the lesson tree, then Run
- Local: `cmake --build --preset <preset> --target lesson_value_semantics`, then `bin/lessons/lesson_value_semantics`, or `ctest --preset <preset> -R lesson.value_semantics`

## What to look for
- Step 1: `Point b = a;` makes a new `Point`, so `b.x = 10` does not change `a` (`a: (1, 2)`). `Point`'s `==` is `= default`, so it compares all members, and after `b = a` it is `true`: equality is decided by value, not by address. In contrast, the two `std::shared_ptr<Point>`s `p` and `q` **share one object**, so `q->x = 10` shows through `*p` too (reference semantics, exercise 1).
- Step 2: `OldDate` writes the six comparison operators by hand, and `operator<` forgets `day`. For 2026-11-17 and 2026-11-18, `!=` is `true` but both `<` and `>` are `false`, and both `<=` and `>=` are `true`: `<`, `<=`, `>` and `>=` say "the same" while `==` and `!=` say "different", so they disagree. It is defined behaviour and the compiler does not warn. `std::sort` and `std::map` use only `<`, so they treat different days of the same month as equivalent: with 11-17 in a `std::map`, 11-18 looks like the same key and is not added (this lesson does not run that).
- Step 3: `Date` gets all six operators from the single line `auto operator<=>(const Date&) const = default;`. It compares the members **in declaration order** (`year`, `month`, `day`), so for the two dates from step 2 `<` is `true` and `>` is `false`, in agreement, and `std::ranges::sort` sorts in date order. A defaulted `<=>` also declares a defaulted `==`.
- Step 4: for `Fraction`, 1/2 and 2/4 are the same value but have different members. So `<=>` is written by hand and compares `a/b` with `c/d` as `a*d` against `c*b`, and its result type is `std::weak_ordering`: "equal" in `std::strong_ordering` means interchangeable anywhere, but 1/2 and 2/4 print differently with `<<`, so they are only **equivalent** (`is equivalent: true`). What this lesson's `==` asks is "the same value?", and that is equivalence. A hand-written `<=>` does not give `==`, so `==` is written with the same rule (exercise 3). Switching to the default comparison gives wrong results (exercise 2).
- Step 5: overload arithmetic operators only when they mean what they mean for `int`. `+=` is a member that changes its own value, and `+` is a non-member (`friend`) that takes the left operand by value and uses `+=`, so the rule for addition lives in one place. 1/2 + 1/4 is `6/8` (not reduced), and thanks to step 4's `==`, `6/8 == 3/4` is `true`. `operator<<` is for output, as in `std::cout << half`. An operator with a surprising meaning (say, `+` of two dates) is not overloaded; make it a named function instead.

```cpp
struct Date {
    int year = 0;
    int month = 0;
    int day = 0;
    [[nodiscard]] auto operator<=>(const Date&) const = default;   // six comparisons, in member order
};
class Fraction {
public:
    [[nodiscard]] std::weak_ordering operator<=>(const Fraction& other) const;   // by hand when the meaning differs
    [[nodiscard]] bool operator==(const Fraction& other) const;                  // == by hand too
    Fraction& operator+=(const Fraction& other);
    friend Fraction operator+(Fraction left, const Fraction& right);             // built on +=
};
```

## Exercises
The web practice mode (the default) edits a practice copy and leaves the original (`lessons/`) untouched. "Reset" below means ↺ Reset on the web and `py -3 tools/practice.py reset value_semantics` locally (local practice: "Practice workspace" in [`lessons/README.md`](/lessons/README.md)).

1. Change `Point b = a;` in step 1 to `Point& b = a;` and run. What does `b.x = 10` change now, and what happens to the `a == b` line? Reset it.
2. Delete `Fraction`'s `operator<=>` and `operator==` and replace them with the single line `[[nodiscard]] auto operator<=>(const Fraction&) const = default;`, then run. Which values in steps 4 and 5 change, and why are they wrong? Reset it.
3. Delete only `Fraction`'s `operator==` and build. The `<` lines build, so why is the `==` line an error? Reset it.
