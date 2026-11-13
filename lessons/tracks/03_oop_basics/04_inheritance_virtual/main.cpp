/**
 * @file main.cpp
 * @brief 레슨 inheritance_virtual — 상속, 가상 함수, 가상 소멸자, 슬라이싱, 추상 클래스, final
 * @brief Lesson inheritance_virtual — inheritance, virtual functions, virtual destructors, slicing, abstract classes, final
 *
 * 같은 호출이 정적 결합과 동적 결합에서 어떻게 달라지는지 출력으로 보고, 가상 소멸자와 슬라이싱, 추상 클래스, final 을 확인한다
 * See how the same call differs under static and dynamic binding, then check virtual destructors, slicing, abstract classes and final
 */
#include <format>
#include <iostream>
#include <memory>
#include <numbers>
#include <string>
#include <string_view>
#include <type_traits>
#include <vector>

namespace {

// 1. 비가상 함수: 호출은 변수의 선언된 타입으로 정해진다 (정적 결합)
// 1. A non-virtual function: the call is decided by the declared type of the variable (static binding)
class PlainBase {
public:
    [[nodiscard]] std::string name() const {
        return "PlainBase::name";
    }
};

class PlainDerived : public PlainBase {
public:
    [[nodiscard]] std::string name() const {
        return "PlainDerived::name";
    }
};

// 2. 가상 함수: 호출은 실제 객체의 타입으로 정해진다 (동적 결합)
// 2. A virtual function: the call is decided by the actual type of the object (dynamic binding)
class Animal {
public:
    Animal() = default;
    Animal(const Animal&) = default;
    Animal& operator=(const Animal&) = default;
    virtual ~Animal() = default;

    [[nodiscard]] virtual std::string sound() const {
        return "...";
    }
};

class Dog : public Animal {
public:
    [[nodiscard]] std::string sound() const override {
        return "woof";
    }
};

// 3. 가상 소멸자가 있으면 기반 클래스 포인터로 지워도 파생 클래스의 소멸자까지 불린다
// 3. With a virtual destructor, deleting through a base pointer also runs the derived destructor
class Resource {
public:
    Resource() = default;
    Resource(const Resource&) = delete;
    Resource& operator=(const Resource&) = delete;

    virtual ~Resource() {
        std::cout << "  ~Resource\n";
    }
};

class FileResource : public Resource {
public:
    ~FileResource() override {
        std::cout << "  ~FileResource\n";
    }
};

// 소멸자가 가상이 아닌 기반 클래스: 이 레슨은 이 타입으로 delete 하지 않고 특성으로만 확인한다
// A base class whose destructor is not virtual: the lesson never deletes through it and only checks the trait
class NonVirtualBase {
public:
    ~NonVirtualBase() = default;
    virtual void run() {}
};

// 4. 값으로 받으면 파생 부분이 잘려 나간다 (슬라이싱): 정의된 동작이지만 대개 의도가 아니다
// 4. Taking by value cuts off the derived part (slicing): defined behaviour, but usually not what you wanted
void describeByValue(Animal animal) {
    std::cout << "  by value: " << animal.sound() << '\n';
}

void describeByReference(const Animal& animal) {
    std::cout << "  by reference: " << animal.sound() << '\n';
}

// 5. 추상 클래스: 순수 가상 함수가 하나라도 있으면 객체를 만들 수 없다
// 5. An abstract class: with any pure virtual function, no object can be made
class Shape {
public:
    Shape() = default;
    Shape(const Shape&) = delete;
    Shape& operator=(const Shape&) = delete;
    virtual ~Shape() = default;

    [[nodiscard]] virtual double area() const = 0;
    [[nodiscard]] virtual std::string_view name() const = 0;
};

class Circle : public Shape {
public:
    explicit Circle(double radius) : radius_(radius) {}

    [[nodiscard]] double area() const override {
        return std::numbers::pi * radius_ * radius_;
    }

    [[nodiscard]] std::string_view name() const override {
        return "circle";
    }

private:
    double radius_ = 0.0;
};

// 6. final: 더 이상 상속할 수 없는 클래스
// 6. final: a class that can no longer be inherited from
class Square final : public Shape {
public:
    explicit Square(double side) : side_(side) {}

    [[nodiscard]] double area() const override {
        return side_ * side_;
    }

    [[nodiscard]] std::string_view name() const override {
        return "square";
    }

private:
    double side_ = 0.0;
};

} // namespace

int main() {
    std::cout << std::boolalpha;

    std::cout << "== Step 1: a non-virtual function ==\n";
    const PlainDerived plain;
    const PlainBase& plainRef = plain;
    std::cout << "PlainDerived object: " << plain.name() << '\n';
    std::cout << "through a PlainBase reference: " << plainRef.name() << '\n';

    std::cout << "== Step 2: a virtual function ==\n";
    const Dog dog;
    const Animal& animalRef = dog;
    std::cout << "Dog object: " << dog.sound() << '\n';
    std::cout << "through an Animal reference: " << animalRef.sound() << '\n';

    std::cout << "== Step 3: a virtual destructor ==\n";
    std::cout << "deleting a FileResource through unique_ptr<Resource>:\n";
    {
        const std::unique_ptr<Resource> resource = std::make_unique<FileResource>();
    }
    std::cout << "Resource has a virtual destructor: " << std::has_virtual_destructor_v<Resource> << '\n';
    std::cout << "NonVirtualBase has a virtual destructor: " << std::has_virtual_destructor_v<NonVirtualBase> << '\n';

    std::cout << "== Step 4: slicing ==\n";
    describeByValue(dog);
    describeByReference(dog);

    std::cout << "== Step 5: an abstract class ==\n";
    std::cout << "Shape is abstract: " << std::is_abstract_v<Shape> << '\n';
    std::vector<std::unique_ptr<Shape>> shapes;
    shapes.push_back(std::make_unique<Circle>(1.0));
    shapes.push_back(std::make_unique<Square>(2.0));
    for (const auto& shape : shapes) {
        std::cout << std::format("  {}: area {:.2f}\n", shape->name(), shape->area());
    }

    std::cout << "== Step 6: final ==\n";
    std::cout << "Square is final: " << std::is_final_v<Square> << '\n';
    std::cout << "Circle is final: " << std::is_final_v<Circle> << '\n';

    return 0;
}
