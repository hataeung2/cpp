/**
 * @file main.cpp
 * @brief 레슨 class_basics — 클래스와 캡슐화: 불변식, 초기화 순서, explicit, const 멤버 함수
 * @brief Lesson class_basics — classes and encapsulation: invariants, initialization order, explicit, const member functions
 *
 * struct 와 class 의 접근 차이, 불변식을 지키는 멤버 함수, 생성자 초기화 목록, explicit 생성자, const 멤버 함수를 출력으로 확인한다
 * Show the access difference between struct and class, member functions that keep an invariant, constructor initializer lists, explicit constructors, and const member functions through output
 */
#include <iostream>
#include <string>
#include <type_traits>
#include <utility>

#include "atugcc/core/error.hpp"

namespace core = atugcc::core;

namespace {

// 1. struct 는 멤버가 기본 public, class 는 기본 private
// 1. A struct has public members by default, a class has private members by default
struct OpenBox {
    int value_ = 7;
};

class ClosedBox {
    int value_ = 7;

public:
    [[nodiscard]] int get() const {
        return value_;
    }
};

// 밖에서 멤버 value_ 에 접근하는 식이 올바른지 컴파일 시간에 묻는다
// Asks at compile time whether the expression that accesses member value from outside is valid
template <typename T>
concept ValueIsVisible = requires(T& box) { box.value_; };

// 2. 흔한 실수: 모든 멤버가 public 이라 불변식(잔액은 음수가 아니다)을 아무도 지키지 않는다
// 2. A common mistake: every member is public, so nobody keeps the invariant (the balance is never negative)
struct LooseAccount {
    long balance = 0;
};

// 바른 방식: 데이터는 private, 불변식은 멤버 함수가 지킨다
// The right way: the data is private and member functions keep the invariant
class Account {
public:
    explicit Account(long opening) : balance_(opening) {}

    // 잔액보다 많이 빼려는 요청은 상태를 바꾸지 않고 오류를 돌려준다
    // A request to withdraw more than the balance changes nothing and returns an error
    [[nodiscard]] core::Expected<long> withdraw(long amount) {
        if (amount <= 0 || amount > balance_) {
            return std::unexpected(core::CoreError::InvalidArgument);
        }
        balance_ -= amount;
        return balance_;
    }

    // const 멤버 함수: 객체를 바꾸지 않는다고 약속하므로 const 참조로 받은 객체에서도 부를 수 있다
    // A const member function promises not to change the object, so it can be called on an object received by const reference
    [[nodiscard]] long balance() const {
        return balance_;
    }

private:
    long balance_ = 0;
};

// 3. 생성과 소멸을 한 줄씩 보여 주는 작은 멤버 타입
// 3. A small member type that shows its construction one line at a time
class Part {
public:
    Part() : name_("default") {
        std::cout << "  Part() constructed as 'default'\n";
    }

    explicit Part(std::string name) : name_(std::move(name)) {
        std::cout << "  Part(" << name_ << ") constructed\n";
    }

    Part(const Part&) = default;

    Part& operator=(const Part& other) {
        name_ = other.name_;
        std::cout << "  Part assigned from " << name_ << '\n';
        return *this;
    }

private:
    std::string name_;
};

// 초기화 목록: 멤버가 처음부터 원하는 값으로 만들어진다
// Initializer list: each member is created with the wanted value from the start
class ByList {
public:
    ByList(std::string first, std::string second) : first_(std::move(first)), second_(std::move(second)) {}

private:
    Part first_;
    Part second_;
};

// 본문 대입: 멤버가 먼저 기본 값으로 만들어지고, 본문에서 다시 대입된다
// Assignment in the body: members are created with the default first and assigned again in the body
class ByBody {
public:
    ByBody(const std::string& first, const std::string& second) {
        first_ = Part{first};
        second_ = Part{second};
    }

private:
    Part first_;
    Part second_;
};

// 멤버 기본값: 초기화 목록에 없는 멤버는 선언의 기본값을 쓴다
// Member default initializers: a member missing from the initializer list uses the default in its declaration
class Config {
public:
    Config() = default;
    explicit Config(int retries) : retries_(retries) {}

    void print(const char* label) const {
        std::cout << label << " retries=" << retries_ << " host=" << host_ << '\n';
    }

private:
    int retries_ = 3;
    std::string host_ = "localhost";
};

// 4. 한 인자 생성자: explicit 이 없으면 double 이 조용히 Feet 가 된다
// 4. A one-argument constructor: without explicit, a double silently becomes Feet
class Feet {
public:
    Feet(double value) : value_(value) {}

    [[nodiscard]] double value() const {
        return value_;
    }

private:
    double value_ = 0.0;
};

class Meters {
public:
    explicit Meters(double value) : value_(value) {}

    [[nodiscard]] double value() const {
        return value_;
    }

private:
    double value_ = 0.0;
};

void showFeet(const Feet& length) {
    std::cout << "showFeet got " << length.value() << " ft\n";
}

void showMeters(const Meters& length) {
    std::cout << "showMeters got " << length.value() << " m\n";
}

// 5. const 참조로 받은 객체에서는 const 멤버 함수만 부를 수 있다
// 5. Only const member functions can be called on an object received by const reference
void report(const Account& account) {
    std::cout << "report(const Account&): balance = " << account.balance() << '\n';
}

} // namespace

int main() {
    std::cout << std::boolalpha;

    std::cout << "== Step 1: struct and class ==\n";
    // struct 의 value_ 는 밖에서 보이고 class 의 value_ 는 보이지 않는다
    // The value_ of a struct is visible from outside and the value_ of a class is not
    std::cout << "OpenBox::value_ visible from outside: " << ValueIsVisible<OpenBox> << '\n';
    std::cout << "ClosedBox::value_ visible from outside: " << ValueIsVisible<ClosedBox> << '\n';
    std::cout << "ClosedBox::get() = " << ClosedBox{}.get() << '\n';

    std::cout << "== Step 2: an invariant ==\n";
    // 모든 멤버가 public 이면 100 에서 150 을 빼서 -50 이 되는 것을 아무도 막지 않는다
    // With every member public, nobody stops 150 being taken from 100 to give -50
    LooseAccount loose;
    loose.balance = 100;
    loose.balance -= 150;
    std::cout << "LooseAccount after taking 150 from 100: " << loose.balance << " (nothing stopped it)\n";

    Account account{100};
    const auto tooMuch = account.withdraw(150);
    if (!tooMuch) {
        std::cout << "Account::withdraw(150) -> error " << core::to_string(tooMuch.error())
                  << ", balance stays " << account.balance() << '\n';
    }
    const auto enough = account.withdraw(30);
    if (enough) {
        std::cout << "Account::withdraw(30) -> balance " << *enough << '\n';
    }

    std::cout << "== Step 3: initializer list and member defaults ==\n";
    std::cout << "ByList (initializer list):\n";
    const ByList byList{"first", "second"};
    std::cout << "ByBody (assignment in the body):\n";
    const ByBody byBody{"first", "second"};
    Config{}.print("Config()");
    Config{5}.print("Config(5)");

    std::cout << "== Step 4: explicit ==\n";
    // 변환 가능성을 타입 특성으로 확인한다
    // Check convertibility with a type trait
    std::cout << "double -> Feet implicit conversion: " << std::is_convertible_v<double, Feet> << '\n';
    std::cout << "double -> Meters implicit conversion: " << std::is_convertible_v<double, Meters> << '\n';
    showFeet(3.5);
    showMeters(Meters{3.5});

    std::cout << "== Step 5: const member functions ==\n";
    report(account);

    return 0;
}
