/**
 * @file main.cpp
 * @brief 레슨 variant_visit — 가상 함수와 std::variant 기반 다형성 비교
 * @brief Lesson variant_visit — compare polymorphism via virtual functions and std::variant
 *
 * 같은 도형을 가상 함수 계층과 std::variant + std::visit 로 구현하여 비교한다
 * The same shapes are implemented via a virtual hierarchy and std::variant + std::visit to compare them
 * 새 연산과 새 타입을 추가할 때의 차이점과 메모리 배치를 확인한다
 * Compare how new operations and types are added, along with their memory layout
 */
#include <algorithm>
#include <format>
#include <iostream>
#include <memory>
#include <numbers>
#include <string_view>
#include <variant>
#include <vector>

namespace {

// 가상 함수 기반의 공통 기본 클래스
// Common base class based on virtual functions
class Shape {
public:
    virtual ~Shape() = default;

    [[nodiscard]] virtual double area() const = 0;
    [[nodiscard]] virtual std::string_view name() const = 0;
};

// 가상 함수 계층의 원 클래스
// Circle class in the virtual function hierarchy
class CircleV final : public Shape {
public:
    explicit CircleV(double radius) : radius_(radius) {}

    [[nodiscard]] double area() const override {
        return std::numbers::pi * radius_ * radius_;
    }

    [[nodiscard]] std::string_view name() const override {
        return "circle";
    }

private:
    double radius_{0.0};
};

// 가상 함수 계층의 직사각형 클래스
// Rectangle class in the virtual function hierarchy
class RectV final : public Shape {
public:
    RectV(double width, double height) : width_(width), height_(height) {}

    [[nodiscard]] double area() const override {
        return width_ * height_;
    }

    [[nodiscard]] std::string_view name() const override {
        return "rect";
    }

private:
    double width_{0.0};
    double height_{0.0};
};

// 기반 클래스가 없는 독립적인 원 구조체
// Standalone circle struct without a base class
struct Circle {
    double radius{0.0};

    [[nodiscard]] double area() const {
        return std::numbers::pi * radius * radius;
    }
};

// 기반 클래스가 없는 독립적인 직사각형 구조체
// Standalone rectangle struct without a base class
struct Rect {
    double width{0.0};
    double height{0.0};

    [[nodiscard]] double area() const {
        return width * height;
    }
};

// state.hpp 의 overloaded 와 같은 세 줄 패턴: 여러 람다를 단일 visitor 로 묶는다
// Three-line pattern, the same as overloaded in state.hpp: combines multiple lambdas into a single visitor
template <typename... Ts>
struct overloaded : Ts... {
    using Ts::operator()...;
};

} // namespace

int main() {
    std::cout << "== 1. virtual functions ==\n";
    // 1. 가상 함수 계층: std::unique_ptr 로 힙에 할당된 다형 객체를 다룬다
    // 1. Virtual function hierarchy: manage polymorphic objects on the heap via std::unique_ptr
    std::vector<std::unique_ptr<Shape>> vShapes;
    vShapes.push_back(std::make_unique<CircleV>(1.0));
    vShapes.push_back(std::make_unique<RectV>(2.0, 3.0));
    for (const auto& shape : vShapes) {
        std::cout << std::format("{}: area {:.2f}\n", shape->name(), shape->area());
    }

    std::cout << "== 2. std::variant and std::visit ==\n";
    // 2. std::variant: 상속 없이 값으로 다형 객체를 보관하고 std::visit 로 처리한다
    // 2. std::variant: store polymorphic objects by value without inheritance and process with std::visit
    std::vector<std::variant<Circle, Rect>> shapes;
    shapes.emplace_back(Circle{1.0});
    shapes.emplace_back(Rect{2.0, 3.0});
    // 이름은 overloaded 로 타입별 분기한다: 타입마다 람다 하나
    // The name branches by type with overloaded: one lambda per type
    const auto nameOf = overloaded{
        [](const Circle&) { return std::string_view{"circle"}; },
        [](const Rect&) { return std::string_view{"rect"}; },
    };
    for (const auto& shape : shapes) {
        const auto name = std::visit(nameOf, shape);
        // 면적은 일반 람다 하나로 두 타입의 같은 이름 멤버 area() 를 부른다
        // The area uses one generic lambda that calls the member area() both types have
        const auto area = std::visit([](const auto& s) { return s.area(); }, shape);
        std::cout << std::format("{}: area {:.2f}\n", name, area);
    }

    std::cout << "== 3. a new operation: perimeter ==\n";
    // 3. 새 연산 추가: 기존 타입을 수정하지 않고 visitor 하나만 추가하면 된다
    // 3. Adding a new operation: add a visitor without modifying existing types
    for (const auto& shape : shapes) {
        const auto name = std::visit(nameOf, shape);
        const auto perimeter = std::visit(overloaded{
            [](const Circle& c) { return 2.0 * std::numbers::pi * c.radius; },
            [](const Rect& r) { return 2.0 * (r.width + r.height); },
        }, shape);
        std::cout << std::format("{}: perimeter {:.2f}\n", name, perimeter);
    }

    std::cout << "== 4. inspecting a variant ==\n";
    // 4. variant 상태 검사: index, holds_alternative, get_if, std::get 예외 처리
    // 4. Inspecting variant state: index, holds_alternative, get_if, and std::get exception handling
    std::variant<Circle, Rect> v = Circle{1.0};
    std::cout << std::format("index() = {}\n", v.index());
    std::cout << std::format("holds_alternative<Circle> = {}\n", std::holds_alternative<Circle>(v));
    std::cout << std::format("get_if<Rect> is null: {}\n", std::get_if<Rect>(&v) == nullptr);

    v = Rect{2.0, 3.0};
    std::cout << std::format("index() = {}\n", v.index());
    if (const auto* rect = std::get_if<Rect>(&v)) {
        std::cout << std::format("get_if<Rect>->width = {:.2f}\n", rect->width);
    }

    try {
        // 잘못된 타입으로 std::get 을 호출하면 std::bad_variant_access 예외가 발생한다
        // Calling std::get with an incorrect type throws std::bad_variant_access
        [[maybe_unused]] const auto& c = std::get<Circle>(v);
    } catch (const std::bad_variant_access&) {
        // 라이브러리마다 예외 메시지가 다르므로 e.what() 은 출력하지 않는다
        // Exception message varies across standard libraries, so do not print e.what()
        std::cout << "bad_variant_access caught\n";
    }

    std::cout << "== 5. memory layout ==\n";
    // 5. 메모리 배치: sizeof 와 힙 할당 여부 비교
    // 5. Memory layout: compare sizeof and heap allocation behavior
    const auto circleSize = sizeof(Circle);
    const auto rectSize = sizeof(Rect);
    const auto variantSize = sizeof(std::variant<Circle, Rect>);
    const auto largestAlternative = std::max(circleSize, rectSize);
    const auto uniquePtrSize = sizeof(std::unique_ptr<Shape>);

    std::cout << std::format("sizeof(Circle) = {}\n", circleSize);
    std::cout << std::format("sizeof(Rect) = {}\n", rectSize);
    std::cout << std::format("sizeof(std::variant<Circle, Rect>) = {}\n", variantSize);
    std::cout << std::format("variant >= largest alternative: {}\n", variantSize >= largestAlternative);
    std::cout << std::format("sizeof(std::unique_ptr<Shape>) = {}\n", uniquePtrSize);
    std::cout << "variant elements: no heap allocation; unique_ptr elements: one allocation each\n";

    return 0;
}
