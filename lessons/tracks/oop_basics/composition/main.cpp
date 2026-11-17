/**
 * @file main.cpp
 * @brief 레슨 composition — 합성과 위임: has-a 대 is-a, LSP
 * @brief Lesson composition — Composition and delegation: has-a versus is-a, LSP
 *
 * 코드를 다시 쓰려고 상속하면 기반 클래스의 인터페이스가 모두 따라오는 것을 출력으로 보고, 멤버로 갖고 일을 맡기는 합성과 위임,
 * Square : Rectangle 이 리스코프 치환 원칙(LSP)을 어기는 것과 그 바른 방식을 확인한다
 * See through the output that inheriting to reuse code brings along the whole interface of the base class, then check composition and
 * delegation (owning a member and handing work to it), how Square : Rectangle breaks the Liskov substitution principle (LSP), and the right way
 */
#include <cstddef>
#include <format>
#include <iostream>
#include <string_view>
#include <type_traits>
#include <vector>

namespace {

// 1. 코드를 다시 쓰려고 상속: std::vector 의 함수가 모두 InheritedStack 의 public 인터페이스가 된다
// 1. Inheriting to reuse code: every function of std::vector becomes part of InheritedStack's public interface
class InheritedStack : public std::vector<int> {
public:
    void push(int value) {
        push_back(value);
    }

    [[nodiscard]] int pop() {
        const int value = back();
        pop_back();
        return value;
    }
};

// 2. 합성: std::vector 를 멤버로 갖고(has-a), 스택이 약속하는 함수만 내놓는다
// 2. Composition: own a std::vector as a member (has-a) and offer only the functions a stack promises
class Stack {
public:
    void push(int value) {
        items_.push_back(value);
    }

    [[nodiscard]] int pop() {
        const int value = items_.back();
        items_.pop_back();
        return value;
    }

    [[nodiscard]] bool empty() const {
        return items_.empty();
    }

    [[nodiscard]] std::size_t size() const {
        return items_.size();
    }

private:
    std::vector<int> items_;
};

// 3. 위임: Car 는 Engine 을 갖고(has-a) start() 를 Engine 에게 맡긴다. 부분은 전체보다 먼저 만들어지고 나중에 사라진다
// 3. Delegation: a Car has an Engine (has-a) and hands start() to it. The part is made before the whole and destroyed after it
class Engine {
public:
    Engine() {
        std::cout << "  Engine built\n";
    }

    Engine(const Engine&) = delete;
    Engine& operator=(const Engine&) = delete;

    ~Engine() {
        std::cout << "  ~Engine\n";
    }

    void start() const {
        std::cout << "  Engine::start\n";
    }
};

class Car {
public:
    Car() {
        std::cout << "  Car built\n";
    }

    Car(const Car&) = delete;
    Car& operator=(const Car&) = delete;

    ~Car() {
        std::cout << "  ~Car\n";
    }

    void start() const {
        std::cout << "  Car::start hands the work to its engine\n";
        engine_.start();
    }

private:
    Engine engine_;
};

// 4. LSP 를 어기는 상속: 정사각형은 수학에서는 직사각형이지만, 너비와 높이를 따로 바꾸는 Rectangle 의 약속은 지킬 수 없다
// 4. Inheritance that breaks the LSP: a square is a rectangle in mathematics, but it cannot keep the promise of a Rectangle
//    whose width and height change separately
namespace broken {

class Rectangle {
public:
    Rectangle(int width, int height) : width_(width), height_(height) {}
    Rectangle(const Rectangle&) = delete;
    Rectangle& operator=(const Rectangle&) = delete;
    virtual ~Rectangle() = default;

    // 약속: 너비를 바꿔도 높이는 그대로, 높이를 바꿔도 너비는 그대로다
    // The promise: changing the width keeps the height, and changing the height keeps the width
    virtual void setWidth(int width) {
        width_ = width;
    }

    virtual void setHeight(int height) {
        height_ = height;
    }

    [[nodiscard]] int width() const {
        return width_;
    }

    [[nodiscard]] int height() const {
        return height_;
    }

    [[nodiscard]] int area() const {
        return width_ * height_;
    }

private:
    int width_ = 0;
    int height_ = 0;
};

// 정사각형의 불변식(네 변이 같다)을 지키려고 두 setter 가 두 변을 함께 바꾼다
// To keep the square's invariant (all sides equal), both setters change both sides
class Square : public Rectangle {
public:
    explicit Square(int side) : Rectangle(side, side) {}

    void setWidth(int width) override {
        Rectangle::setWidth(width);
        Rectangle::setHeight(width);
    }

    void setHeight(int height) override {
        Rectangle::setWidth(height);
        Rectangle::setHeight(height);
    }
};

// Rectangle 의 약속만 믿는 코드: 너비 5, 높이 4 로 바꾸면 넓이는 20 이어야 한다
// Code that trusts only Rectangle's promise: after width 5 and height 4, the area must be 20
void stretch(Rectangle& rectangle) {
    rectangle.setWidth(5);
    rectangle.setHeight(4);
}

void describe(std::string_view name, const Rectangle& rectangle) {
    std::cout << std::format("  {}: {} x {}, area {} (stretch expects 20)\n", name, rectangle.width(), rectangle.height(), rectangle.area());
}

} // namespace broken

// 5. 바른 방식: Square 와 Rectangle 은 서로 상속하지 않고, 둘 다 지킬 수 있는 약속(넓이와 이름)만 Shape 로 나눈다
// 5. The right way: Square and Rectangle do not inherit from each other; they share only the promise both can keep (area and name) in Shape
namespace fixed {

class Shape {
public:
    Shape() = default;
    Shape(const Shape&) = delete;
    Shape& operator=(const Shape&) = delete;
    virtual ~Shape() = default;

    [[nodiscard]] virtual int area() const = 0;
    [[nodiscard]] virtual std::string_view name() const = 0;
};

class Rectangle final : public Shape {
public:
    Rectangle(int width, int height) : width_(width), height_(height) {}

    void setWidth(int width) {
        width_ = width;
    }

    void setHeight(int height) {
        height_ = height;
    }

    [[nodiscard]] int area() const override {
        return width_ * height_;
    }

    [[nodiscard]] std::string_view name() const override {
        return "rectangle";
    }

private:
    int width_ = 0;
    int height_ = 0;
};

// 정사각형은 변 하나만 바꾼다: 불변식을 깨는 함수가 처음부터 없다
// A square changes its one side only: no function that could break the invariant exists
class Square final : public Shape {
public:
    explicit Square(int side) : side_(side) {}

    void setSide(int side) {
        side_ = side;
    }

    [[nodiscard]] int area() const override {
        return side_ * side_;
    }

    [[nodiscard]] std::string_view name() const override {
        return "square";
    }

private:
    int side_ = 0;
};

void describe(const Shape& shape) {
    std::cout << std::format("  {}: area {}\n", shape.name(), shape.area());
}

} // namespace fixed

} // namespace

int main() {
    std::cout << std::boolalpha;

    std::cout << "== Step 1: inheriting to reuse code ==\n";
    InheritedStack leaky;
    leaky.push(1);
    leaky.push(2);
    leaky.push(3);
    // std::vector 의 insert 도 InheritedStack 의 함수라서, 스택 밑에 값을 끼워 넣을 수 있다
    // std::vector's insert is a function of InheritedStack too, so a value can be slipped in under the stack
    leaky.insert(leaky.begin(), 99);
    std::cout << "pushed 1 2 3, then called insert(begin(), 99)\n";
    std::cout << "pop order:";
    while (!leaky.empty()) {
        std::cout << ' ' << leaky.pop();
    }
    std::cout << '\n';
    std::cout << "std::vector<int> has a virtual destructor: " << std::has_virtual_destructor_v<std::vector<int>> << '\n';

    std::cout << "== Step 2: composition ==\n";
    Stack stack;
    stack.push(1);
    stack.push(2);
    stack.push(3);
    std::cout << "pushed 1 2 3, size " << stack.size() << '\n';
    std::cout << "pop order:";
    while (!stack.empty()) {
        std::cout << ' ' << stack.pop();
    }
    std::cout << '\n';
    std::cout << "InheritedStack is a std::vector<int>: " << std::is_base_of_v<std::vector<int>, InheritedStack> << '\n';
    std::cout << "Stack is a std::vector<int>: " << std::is_base_of_v<std::vector<int>, Stack> << '\n';

    std::cout << "== Step 3: delegation ==\n";
    {
        const Car car;
        car.start();
    }

    std::cout << "== Step 4: a Square that is a Rectangle breaks the LSP ==\n";
    broken::Rectangle rectangle{2, 3};
    broken::stretch(rectangle);
    broken::describe("rectangle", rectangle);
    broken::Square square{2};
    broken::stretch(square);
    broken::describe("square", square);
    std::cout << "  still a square: " << (square.width() == square.height()) << '\n';

    std::cout << "== Step 5: separate types behind a promise both can keep ==\n";
    fixed::Rectangle fixedRectangle{2, 3};
    fixedRectangle.setWidth(5);
    fixedRectangle.setHeight(4);
    fixed::Square fixedSquare{2};
    fixedSquare.setSide(4);
    fixed::describe(fixedRectangle);
    fixed::describe(fixedSquare);
    std::cout << "fixed::Square is a fixed::Rectangle: " << std::is_base_of_v<fixed::Rectangle, fixed::Square> << '\n';

    return 0;
}
