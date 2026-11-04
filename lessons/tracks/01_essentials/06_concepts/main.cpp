/**
 * @file main.cpp
 * @brief 레슨 concepts — 템플릿 제약: SFINAE에서 concepts로
 * @brief Lesson concepts — constraining templates: from SFINAE to concepts
 *
 * std::enable_if 와 std::integral concept 로 같은 제약을 작성하여 비교한다
 * Write the same constraint with std::enable_if and with std::integral to compare them
 * requires 식, 축약 함수 템플릿, 가장 좁은 제약의 오버로드, 클래스 템플릿 제약을 다룬다
 * Cover requires expressions, abbreviated function templates, subsumption overload selection, and class template constraints
 */
#include <bit>
#include <concepts>
#include <cstddef>
#include <format>
#include <iostream>
#include <numbers>
#include <string>
#include <string_view>
#include <type_traits>
#include <vector>

namespace {

// SFINAE 방식: std::enable_if_t로 정수 타입만 허용한다
// SFINAE approach: allow only integral types via std::enable_if_t
template <typename T, std::enable_if_t<std::is_integral_v<T>, int> = 0>
[[nodiscard]] T twiceSfinae(T x) {
    return static_cast<T>(x * 2);
}

// C++20 concept 방식: 템플릿 매개변수 자리에 concept를 직접 쓴다
// C++20 concept approach: use the concept directly in place of typename
template <std::integral T>
[[nodiscard]] T twice(T x) {
    return static_cast<T>(x * 2);
}

// requires 식으로 정의한 Shape concept: area()와 name() 멤버 함수를 요구한다
// Shape concept defined with a requires expression: requires area() and name() member functions
template <typename T>
concept Shape = requires(const T& s) {
    { s.area() } -> std::convertible_to<double>;
    { s.name() } -> std::convertible_to<std::string_view>;
};

// Shape concept를 만족하는 Circle 구조체
// Circle struct that satisfies the Shape concept
struct Circle {
    double radius{0.0};

    [[nodiscard]] double area() const {
        return std::numbers::pi * radius * radius;
    }

    [[nodiscard]] std::string_view name() const {
        return "circle";
    }
};

// Shape concept를 만족하는 Square 구조체
// Square struct that satisfies the Shape concept
struct Square {
    double side{0.0};

    [[nodiscard]] double area() const {
        return side * side;
    }

    [[nodiscard]] std::string_view name() const {
        return "square";
    }
};

// 축약 함수 템플릿 (const Shape auto&): Shape 제약을 만족하는 모든 타입을 받는다
// Abbreviated function template (const Shape auto&): accepts any type satisfying Shape
void printShape(const Shape auto& s) {
    std::cout << std::format("{}: area {:.2f}\n", s.name(), s.area());
}

// 가장 덜 제약된 오버로드: 모든 타입을 받는다
// Least constrained overload: accepts any type
[[nodiscard]] constexpr std::string_view describe(auto) {
    return "auto";
}

// std::integral로 제약된 오버로드: 정수 타입을 받는다
// Overload constrained by std::integral: accepts integral types
[[nodiscard]] constexpr std::string_view describe(std::integral auto) {
    return "integral";
}

// std::signed_integral로 제약된 오버로드: 부호 있는 정수 타입을 받는다
// Overload constrained by std::signed_integral: accepts signed integral types
[[nodiscard]] constexpr std::string_view describe(std::signed_integral auto) {
    return "signed_integral";
}

// requires 식을 사용한 if constexpr: size() 멤버 함수가 있는지 컴파일 타임에 검사한다
// if constexpr with a requires expression: checks at compile time whether size() exists
template <typename T>
[[nodiscard]] std::string sizeInfo(const T& x) {
    if constexpr (requires { x.size(); }) {
        return std::format("size() = {}", x.size());
    } else {
        return "no size()";
    }
}

// 클래스 템플릿의 requires 절: N이 2의 거듭제곱(단일 비트)인지 검사한다
// requires clause on a class template: verifies that N is a power of two (single bit)
template <std::size_t N>
    requires (std::has_single_bit(N))
struct FixedRing {
    static constexpr std::size_t kMask = N - 1;

    [[nodiscard]] static constexpr std::size_t slot(std::size_t index) {
        return index & kMask;
    }
};

} // namespace

int main() {
    std::cout << "== 1. enable_if vs a concept ==\n";
    // 1. SFINAE 방식과 concept 방식 모두 같은 정수 연산을 수행한다
    // 1. Both the SFINAE approach and the concept approach perform the same integer operation
    std::cout << std::format("twiceSfinae(21) = {}\n", twiceSfinae(21));
    std::cout << std::format("twice(21) = {}\n", twice(21));

    std::cout << "== 2. a concept from a requires expression ==\n";
    // 2. Circle과 Square는 Shape concept를 만족하므로 printShape로 전달할 수 있다
    // 2. Circle and Square satisfy the Shape concept, so they can be passed to printShape
    printShape(Circle{1.0});
    printShape(Square{2.0});
    // concept를 불리언 조건으로 평가하여 타입 만족 여부를 확인한다
    // Evaluate the concept as a boolean condition to inspect type satisfaction
    std::cout << std::boolalpha;
    std::cout << "Shape<Circle> = " << Shape<Circle> << '\n';
    std::cout << "Shape<Square> = " << Shape<Square> << '\n';
    std::cout << "Shape<int> = " << Shape<int> << '\n';
    static_assert(Shape<Circle>);
    static_assert(Shape<Square>);
    static_assert(!Shape<int>);

    std::cout << "== 3. the most constrained overload wins ==\n";
    // 3. 컴파일러는 인자를 만족하는 오버로드 중 가장 좁은(더 제약된) 것을 고른다
    // 3. The compiler selects the most constrained overload among those satisfied by the argument
    std::cout << std::format("describe(-3) -> {}\n", describe(-3));
    std::cout << std::format("describe(3u) -> {}\n", describe(3u));
    std::cout << std::format("describe(2.5) -> {}\n", describe(2.5));

    std::cout << "== 4. if constexpr with a requires expression ==\n";
    // 4. if constexpr와 requires 식을 결합하면 concept 정의 없이도 멤버 유무를 분기할 수 있다
    // 4. Combining if constexpr with a requires expression branches on member presence without defining a concept
    const std::vector<int> numbers{1, 2, 3};
    std::cout << std::format("std::vector<int>{{1, 2, 3}}: {}\n", sizeInfo(numbers));
    std::cout << std::format("42: {}\n", sizeInfo(42));

    std::cout << "== 5. requires clause on a class template ==\n";
    // 5. 크기가 2의 거듭제곱이면 index & (N - 1) 이 index % N 과 같다: 제약이 마스크 계산의 정확성을 보장한다
    // 5. With a power-of-two size, index & (N - 1) equals index % N: the constraint makes the mask correct
    std::cout << std::format("FixedRing<8>: mask = {}, slot(13) = {}\n",
                             FixedRing<8>::kMask,
                             FixedRing<8>::slot(13));
    std::cout << std::format("FixedRing<16>: mask = {}, slot(13) = {}\n",
                             FixedRing<16>::kMask,
                             FixedRing<16>::slot(13));
    // include/atugcc/core/ring_buffer.hpp의 RingBuffer도 requires 절로 2의 거듭제곱을 검사하고, 1도 거부한다
    // RingBuffer in include/atugcc/core/ring_buffer.hpp also checks for a power of two in a requires clause, and rejects 1 too
    // 그 검사는 C++20 이전 방식의 비트 식이다: BlockCount > 1 && (BlockCount & (BlockCount - 1)) == 0 (BlockSize 조건도 있음)
    // The check is the pre-C++20 bit expression: BlockCount > 1 && (BlockCount & (BlockCount - 1)) == 0 (plus a BlockSize condition)
    // 연습 3: FixedRing<6>처럼 2의 거듭제곱이 아닌 크기로 인스턴스화하면 컴파일 오류가 난다
    // Exercise 3: instantiating with a non-power-of-two size like FixedRing<6> causes a compile error

    return 0;
}
