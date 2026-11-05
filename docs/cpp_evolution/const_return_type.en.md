# `const` on a C++ Return Type vs `const` on a Member Function

In C++, where the `const` keyword goes in a function signature changes its meaning and behaviour completely. In particular, putting `const` on the return type (`virtual const bool hasNext()`) and putting it after a member function (`virtual bool hasNext() const`) lead to entirely different results.

## 1. `const` in front of the return type (e.g. `const bool`)

```cpp
virtual const bool hasNext() = 0;  // ❌ pattern to avoid
```

Putting `const` on a returned primitive type (`bool`, `int`, …) like this **means nothing** in C++.

### Why?
When a primitive value is returned by value, the returned value reaches the caller as a one-off temporary (an rvalue) anyway. Whether the caller copies it into an ordinary variable or into a `const` one is entirely the caller's choice.

```cpp
bool a = iter->hasNext();        // the value is copied into my variable a anyway
const bool b = iter->hasNext();  // if I want it const, I declare it const myself
```

So forcing `const` onto the return type itself is pointless, and strict compilers (`-Wall -Wextra` on Clang and GCC) warn with `[-Wignored-qualifiers]`. This repository treats warnings as errors, so the build fails.

### On class types it blocks moves
For `bool`, the warning is the whole problem. Putting `const` on a class return type such as `std::string` or `std::vector`, however, causes a performance problem without any warning. You need to know exactly **where** it happens.

```cpp
const std::string makeName();

std::string a = makeName();   // neither a copy nor a move (C++17 guaranteed copy elision)
a = makeName();               // copy assignment instead of move assignment
names.push_back(makeName());  // copy construction instead of move construction
```

- **Initialization** (`std::string a = makeName();`): since C++17, returning a prvalue such as `return std::string{...};` makes the returned value `a` itself (guaranteed copy elision). Even with `const`, there is neither a copy nor a move.
- **Assignment and inserting into a container**: putting the value into an object that already exists has to take it from the returned temporary. Because that temporary is `const`, the move operation (which takes `std::string&&`) cannot be chosen, and the copy operation (`const std::string&`) is called. For a string or a vector that is a **deep copy**.

Step 4 of the lesson [`const_correctness`](/lessons/tracks/01_essentials/03_const_correctness/README.en.md) prints this comparison as a table, using a type that counts its copies and moves.

**Conclusion:** do not put `const` on a return-by-value type. On primitive types it means nothing; on class types it blocks moves in assignment and container insertion.

---

## 2. `const` after the function signature (e.g. `hasNext() const`)

```cpp
virtual bool hasNext() const = 0;  // ✅ correct pattern (the function is safe)
```

If you want to say "this function is safe and does not change the object's internal state", put `const` **at the very end of the function declaration**, not in front of the return type.

### Why?
A `const` after the parentheses `()` is a promise, to the compiler and to fellow developers reading the code, that **"calling this member function never changes the object's member data"**.

If the function body then changes a member variable by mistake, the compiler stops with an error and prevents the bug before it happens.

- Functions that change state (setters, buffer updates, …): declared without `const`.
- Functions that only query state (getters, `hasNext()`, `isAvailable()`, …): always declared with `const` at the end.

`const` member functions, a `mutable` cache, and `const`/non-`const` overloads (merged into one with C++23 deducing this) are steps 1–3 of the same lesson.
