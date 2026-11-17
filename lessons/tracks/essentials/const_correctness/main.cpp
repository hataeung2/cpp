/**
 * @file main.cpp
 * @brief 레슨 const_correctness — const 의 위치: 멤버 함수, mutable, 반환 타입
 * @brief Lesson const_correctness — where const goes: member functions, mutable, return types
 *
 * const 멤버 함수, mutable 캐시, const/비const 오버로드와 deducing this 를 살펴본다
 * Examine const member functions, a mutable cache, const/non-const overloads, and deducing this
 * 값 반환 타입의 const 가 이동 연산을 막고 복사로 이어지는 동작을 확인한다
 * Observe how a const return value blocks move operations and forces copies
 */
#include <concepts>
#include <cstddef>
#include <format>
#include <iostream>
#include <optional>
#include <string>
#include <string_view>
#include <type_traits>
#include <utility>
#include <vector>

namespace {

// 1. const 멤버 함수
// 1. const member functions

// 호출 횟수를 세는 카운터 클래스
// Counter class tracking invocation count
class Counter {
public:
    // 내부 카운터를 1 증가시킨다
    // Increments the internal counter by one
    void increment() {
        ++value_;
    }

    // 현재 카운터 값을 반환한다 (상태를 변경하지 않는 const 멤버 함수)
    // Returns the current counter value (a const member function that does not modify state)
    [[nodiscard]] int value() const {
        return value_;
    }

private:
    int value_ = 0;
};

// const 참조로 전달받은 카운터의 값을 출력한다
// Prints the value of a counter passed by const reference
void report(const Counter& c) {
    // 연습 1: const 참조에서는 상태를 변경하는 비const 멤버 함수를 호출할 수 없다
    // Exercise 1: non-const member functions that modify state cannot be called on a const reference
    // c.increment();
    std::cout << "report(const Counter&): value = " << c.value() << '\n';
}

// 2. mutable 캐시
// 2. mutable cache

// 단어 수를 캐시하는 문서 클래스
// Document class that caches its word count
class Document {
public:
    // 텍스트 내용으로 문서를 생성한다
    // Constructs a document with the given text
    explicit Document(std::string text) : text_(std::move(text)) {}

    // 공백으로 구분된 단어 수를 첫 번째 호출에만 계산하여 캐시에 저장한다
    // Counts space-separated words on the first call only and stores the result in cache
    [[nodiscard]] std::size_t wordCount() const {
        if (!word_count_.has_value()) {
            ++computations_;
            std::size_t count = 0;
            bool inWord = false;
            for (const char ch : text_) {
                if (ch == ' ') {
                    inWord = false;
                } else if (!inWord) {
                    inWord = true;
                    ++count;
                }
            }
            word_count_ = count;
        }
        return *word_count_;
    }

    // 실제 단어 수 계산이 수행된 횟수를 반환한다
    // Returns the number of times the word count was actually computed
    [[nodiscard]] int computations() const {
        return computations_;
    }

private:
    std::string text_;
    mutable std::optional<std::size_t> word_count_;
    mutable int computations_ = 0;
};

// 3. const 및 비const 오버로드와 deducing this
// 3. const and non-const overloads, and deducing this

// 비const/const 오버로드와 C++23 deducing this 를 비교하기 위한 버퍼 클래스
// Buffer class comparing non-const/const overloads and C++23 deducing this
class Buffer {
public:
    // 비const 객체에서 불리는 오버로드: 요소의 참조를 반환한다
    // Overload called on a non-const object: returns a reference to the element
    [[nodiscard]] int& at(std::size_t i) {
        return data_[i];
    }

    // const 객체에서 불리는 오버로드: 요소의 const 참조를 반환한다
    // Overload called on a const object: returns a const reference to the element
    [[nodiscard]] const int& at(std::size_t i) const {
        return data_[i];
    }

    // C++23 deducing this: 단 하나의 멤버 함수로 비const 와 const 호출을 모두 처리한다
    // C++23 deducing this: a single member function handles both non-const and const calls
    [[nodiscard]] auto& get(this auto& self, std::size_t i) {
        return self.data_[i];
    }

private:
    std::vector<int> data_{10, 20, 30};
};

// 4. 값 반환 타입의 const 와 이동 연산
// 4. const return values and moves

// 복사 및 이동 연산 횟수를 기록하는 구조체
// Structure tracking the number of copy and move operations
struct Counts {
    int copyCtor = 0;
    int copyAssign = 0;
    int moveCtor = 0;
    int moveAssign = 0;

    // 모든 카운터를 0으로 초기화한다
    // Resets all counters to zero
    void reset() {
        copyCtor = 0;
        copyAssign = 0;
        moveCtor = 0;
        moveAssign = 0;
    }
};

// 복사 및 이동 연산 횟수를 추적하는 클래스
// Class tracking copy and move operations
class Tracked {
public:
    // Counts 를 가리키는 포인터를 보관하는 객체를 만든다
    // Constructs an object holding a pointer to Counts
    explicit Tracked(Counts& counts) : counts_(&counts) {}

    // 복사 생성자: 복사 생성 횟수를 1 증가시킨다
    // Copy constructor: increments the copy constructor counter
    Tracked(const Tracked& other) : counts_(other.counts_) {
        if (counts_ != nullptr) {
            ++counts_->copyCtor;
        }
    }

    // 복사 대입 연산자: 복사 대입 횟수를 1 증가시킨다
    // Copy assignment operator: increments the copy assignment counter
    Tracked& operator=(const Tracked& other) {
        if (this != &other) {
            counts_ = other.counts_;
            if (counts_ != nullptr) {
                ++counts_->copyAssign;
            }
        }
        return *this;
    }

    // 이동 생성자: 이동 생성 횟수를 1 증가시킨다
    // Move constructor: increments the move constructor counter
    Tracked(Tracked&& other) noexcept : counts_(other.counts_) {
        if (counts_ != nullptr) {
            ++counts_->moveCtor;
        }
    }

    // 이동 대입 연산자: 이동 대입 횟수를 1 증가시킨다
    // Move assignment operator: increments the move assignment counter
    Tracked& operator=(Tracked&& other) noexcept {
        if (this != &other) {
            counts_ = other.counts_;
            if (counts_ != nullptr) {
                ++counts_->moveAssign;
            }
        }
        return *this;
    }

    ~Tracked() = default;

private:
    Counts* counts_ = nullptr;
};

// 표의 한 행: 연산 이름과 네 횟수
// One table row: the operation and its four counts
void printRow(std::string_view label, const Counts& c) {
    std::cout << std::format("{:<26} | {:>9} | {:>11} | {:>9} | {:>11}\n", label, c.copyCtor, c.copyAssign,
                             c.moveCtor, c.moveAssign);
}

// 비const prvalue 객체를 반환한다 (복사 생략 적용)
// Returns a non-const prvalue object (subject to copy elision)
[[nodiscard]] Tracked makeValue(Counts& counts) {
    return Tracked{counts};
}

// const prvalue 객체를 반환한다: 반환 자체는 복사 생략이고, 호출한 쪽이 대입하거나 넣을 때 이동 대신 복사가 된다
// Returns a const prvalue: the return itself is elided; the caller gets a copy instead of a move when it assigns or inserts it
[[nodiscard]] const Tracked makeConst(Counts& counts) {
    return Tracked{counts};
}

// 연습 2: 주석을 풀고 main 에서 한 번 부르면 Clang 의 -Wignored-qualifiers 경고(오류)가 난다
// Exercise 2: uncomment it and call it once from main; Clang gives -Wignored-qualifiers (an error here)
// const int makeInt() { return 1; }

// 5. const 와 포인터
// 5. const and pointers

// 포인터 타입의 대상과 포인터 자체의 const 여부를 출력한다
// Prints whether the pointee and the pointer itself are const
template <typename T>
void printPointerConstInfo(std::string_view typeName) {
    std::cout << typeName << ": pointee const: "
              << std::is_const_v<std::remove_pointer_t<T>>
              << "  pointer const: "
              << std::is_const_v<T> << '\n';
}

} // namespace

int main() {
    std::cout << std::boolalpha;

    std::cout << "== 1. const member functions ==\n";
    // 1. const 멤버 함수: 상태를 변경하지 않는 읽기 전용 연산이다
    // 1. const member functions: read-only operations that do not modify state
    Counter counter;
    counter.increment();
    counter.increment();
    report(counter);

    std::cout << "== 2. mutable cache ==\n";
    // 2. mutable 캐시: const 멤버 함수 안에서도 mutable 필드는 수정할 수 있다
    // 2. mutable cache: mutable fields can be modified even inside a const member function
    // mutable 은 "const 함수는 여러 스레드에서 동시에 호출해도 안전하다"는 기대를 깨뜨린다
    // mutable breaks the expectation that const member functions are safe to call concurrently
    // 여러 스레드가 공유하는 환경에서는 뮤텍스나 std::atomic 같은 동기화가 필요하다
    // In multi-threaded shared environments, synchronization via mutex or std::atomic is required
    const Document doc{"a const function may still fill a cache"};
    std::cout << "wordCount() call 1 = " << doc.wordCount() << '\n';
    std::cout << "wordCount() call 2 = " << doc.wordCount() << '\n';
    std::cout << "wordCount() call 3 = " << doc.wordCount() << '\n';
    std::cout << "computations = " << doc.computations() << '\n';

    std::cout << "== 3. const and non-const overloads, then deducing this ==\n";
    // 3. const/비const 오버로드와 C++23 deducing this
    // 3. const/non-const overloads and C++23 deducing this
    Buffer b;
    const Buffer& cb = b;

    std::cout << "b.at(0) returns int&: "
              << std::same_as<decltype(b.at(0)), int&> << '\n';
    std::cout << "cb.at(0) returns const int&: "
              << std::same_as<decltype(cb.at(0)), const int&> << '\n';

    b.at(0) = 11;
    b.get(1) = 21;
    std::cout << "b.at(0) = " << b.at(0) << ", b.get(1) = " << b.get(1) << '\n';

    static_assert(std::same_as<decltype(cb.get(1)), const int&>);
    std::cout << "cb.get(1) returns const int&: "
              << std::same_as<decltype(cb.get(1)), const int&> << '\n';

    // 단 하나의 get 함수가 const 와 비const 오버로드 두 벌을 모두 대체한다
    // The single get function replaces both const and non-const overloads
    // auto& 반환 타입을 사용하여 복사를 방지하고 참조를 유지한다 (auto 로 쓰면 값 복사가 됨, 연습 3)
    // auto& return type preserves the reference without copying (using auto would copy, exercise 3)
    // rvalue 객체까지 다루려면 std::forward_like 가 필요하지만 Linux 툴체인에서 빌드되지 않는다 (KI-033)
    // Handling rvalue objects requires std::forward_like, which does not build on the Linux toolchain (KI-033)

    std::cout << "== 4. const return values and moves ==\n";
    // 4. 값 반환 타입의 const: 반환값에 붙은 const 가 이동 연산을 가로막고 복사를 강제한다
    // 4. const on value return types: const on return values blocks moves and forces copies
    Counts counts;
    std::cout << std::format("{:<26} | {:>9} | {:>11} | {:>9} | {:>11}\n", "case", "copy ctor", "copy assign",
                             "move ctor", "move assign");

    // 1) makeValue() 로 초기화 (C++17 보장된 복사 생략으로 생성자/대입 호출 없음)
    // 1) Initialization with makeValue() (no ctor/assign calls due to C++17 guaranteed copy elision)
    counts.reset();
    {
        [[maybe_unused]] Tracked a = makeValue(counts);
    }
    printRow("Tracked a = makeValue()", counts);

    // 2) makeConst() 로 초기화 (const prvalue 역시 C++17 복사 생략이 적용됨)
    // 2) Initialization with makeConst() (const prvalue also undergoes C++17 copy elision)
    counts.reset();
    {
        [[maybe_unused]] Tracked a = makeConst(counts);
    }
    printRow("Tracked a = makeConst()", counts);

    // 3) makeValue() 대입 (비const rvalue 는 이동 대입 연산자를 호출)
    // 3) Assignment with makeValue() (non-const rvalue calls move assignment operator)
    Tracked t{counts};
    counts.reset();
    t = makeValue(counts);
    printRow("t = makeValue()", counts);

    // 4) makeConst() 대입 (const rvalue 는 T&& 에 묶이지 않아 이동 대입 대신 복사 대입)
    // 4) Assignment with makeConst() (const rvalue cannot bind to T&&, falls back to copy assignment)
    counts.reset();
    t = makeConst(counts);
    printRow("t = makeConst()", counts);

    // 5) v.push_back(makeValue()) (비const rvalue 는 이동 생성자를 호출)
    // 5) v.push_back(makeValue()) (non-const rvalue calls move constructor)
    std::vector<Tracked> v;
    v.reserve(2);
    counts.reset();
    v.push_back(makeValue(counts));
    printRow("v.push_back(makeValue())", counts);

    // 6) v.push_back(makeConst()) (const rvalue 는 이동할 수 없어 복사 생성자를 호출)
    // 6) v.push_back(makeConst()) (const rvalue cannot be moved, falls back to copy constructor)
    counts.reset();
    v.push_back(makeConst(counts));
    printRow("v.push_back(makeConst())", counts);

    std::cout << "== 5. const and pointers ==\n";
    // 5. const 와 포인터: 가리키는 대상의 const 와 포인터 변수 자체의 const
    // 5. const and pointers: const on pointee versus const on pointer variable
    printPointerConstInfo<int*>("int*");
    printPointerConstInfo<const int*>("const int*");
    printPointerConstInfo<int* const>("int* const");
    printPointerConstInfo<const int* const>("const int* const");

    // const int*: 가리키는 값은 수정할 수 없지만 포인터 변수 자체는 다른 주소를 가리킬 수 있다
    // const int*: the pointed-to value cannot be modified, but the pointer variable can point elsewhere
    int x = 1;
    int y = 2;
    const int* p = &x;
    p = &y;
    std::cout << "*p = " << *p << " after p = &y\n";

    // int* const: 포인터 변수 자체는 주소를 바꿀 수 없지만 가리키는 값은 수정할 수 있다
    // int* const: the pointer itself cannot change its target address, but the pointed-to value can be modified
    int* const q = &x;
    *q = 5;
    std::cout << "x = " << x << " after *q = 5\n";

    return 0;
}
