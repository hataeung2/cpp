/**
 * @file main.cpp
 * @brief 레슨 copy_and_move — 복사와 이동, Rule of 0/5, = delete
 * @brief Lesson copy_and_move — copy and move, Rule of 0/5, = delete
 *
 * 복사와 이동 횟수를 세는 타입으로 값 전달을 보고, 얕은 복사의 문제와 Rule of 5, Rule of 0, 복사 금지를 확인한다
 * Count copies and moves with a small type to watch value passing, then see the shallow-copy problem, the Rule of 5, the Rule of 0 and deleted copies
 */
#include <format>
#include <iostream>
#include <memory>
#include <string>
#include <type_traits>
#include <utility>
#include <vector>

namespace {

// 1. 복사와 이동 횟수를 세는 타입
// 1. A type that counts copies and moves
class Tracked {
public:
    Tracked() = default;

    Tracked(const Tracked&) {
        ++copies_;
    }

    Tracked(Tracked&& other) noexcept {
        ++moves_;
        other.moved_from_ = true;
    }

    Tracked& operator=(const Tracked&) = delete;
    Tracked& operator=(Tracked&&) = delete;
    ~Tracked() = default;

    [[nodiscard]] bool movedFrom() const {
        return moved_from_;
    }

    static void reset() {
        copies_ = 0;
        moves_ = 0;
    }

    [[nodiscard]] static int copies() {
        return copies_;
    }

    [[nodiscard]] static int moves() {
        return moves_;
    }

private:
    bool moved_from_ = false;
    static inline int copies_ = 0;
    static inline int moves_ = 0;
};

void takeByValue(Tracked) {}

void takeByConstRef(const Tracked&) {}

[[nodiscard]] Tracked makeTracked() {
    return Tracked{};
}

void printCounts(const char* label) {
    std::cout << std::format("{:<26} copies {} moves {}\n", label, Tracked::copies(), Tracked::moves());
    Tracked::reset();
}

// 2. 얕은 복사: 기본 복사 생성자는 포인터만 복사해서 소유자가 둘이 된다 (자원은 소유자 수를 세는 카운터로 표현)
// 2. Shallow copy: the default copy constructor copies only the pointer, so there are two owners (the resource is a counter of owners)
struct Resource {
    int owners = 0;
};

class ShallowHandle {
public:
    explicit ShallowHandle(Resource& resource) : resource_(&resource) {
        ++resource_->owners;
    }

    ~ShallowHandle() {
        --resource_->owners;
    }

private:
    Resource* resource_;
};

// 3. Rule of 5: 자원을 직접 관리하는 클래스는 다섯 특수 멤버 함수를 모두 쓴다
// 3. Rule of 5: a class that manages a resource itself writes all five special member functions
class IntBox {
public:
    explicit IntBox(int value) : value_(new int{value}) {}

    IntBox(const IntBox& other) : value_(other.value_ != nullptr ? new int{*other.value_} : nullptr) {
        ++copies_;
    }

    IntBox(IntBox&& other) noexcept : value_(std::exchange(other.value_, nullptr)) {
        ++moves_;
    }

    IntBox& operator=(const IntBox& other) {
        if (this != &other) {
            IntBox copy{other};
            std::swap(value_, copy.value_);
        }
        return *this;
    }

    IntBox& operator=(IntBox&& other) noexcept {
        if (this != &other) {
            delete value_;
            value_ = std::exchange(other.value_, nullptr);
        }
        return *this;
    }

    ~IntBox() {
        delete value_;
    }

    [[nodiscard]] bool empty() const {
        return value_ == nullptr;
    }

    [[nodiscard]] int value() const {
        return value_ != nullptr ? *value_ : 0;
    }

    [[nodiscard]] const int* address() const {
        return value_;
    }

    static void reset() {
        copies_ = 0;
        moves_ = 0;
    }

    [[nodiscard]] static int copies() {
        return copies_;
    }

    [[nodiscard]] static int moves() {
        return moves_;
    }

private:
    int* value_ = nullptr;
    static inline int copies_ = 0;
    static inline int moves_ = 0;
};

// 4. Rule of 0: 자원을 관리하는 멤버(std::string, std::vector)에게 맡기면 특수 멤버 함수를 하나도 쓰지 않아도 된다
// 4. Rule of 0: leave the resources to members that manage them (std::string, std::vector) and you write no special member function
class Person {
public:
    Person(std::string name, std::vector<int> scores) : name_(std::move(name)), scores_(std::move(scores)) {}

    [[nodiscard]] const std::string& name() const {
        return name_;
    }

    [[nodiscard]] std::size_t scoreCount() const {
        return scores_.size();
    }

private:
    std::string name_;
    std::vector<int> scores_;
};

// 5. 복사 금지: 복사 생성자를 = delete 하거나, 복사할 수 없는 멤버(unique_ptr)를 두면 저절로 그렇게 된다
// 5. No copies: delete the copy constructor or hold a member that cannot be copied (unique_ptr) and it follows by itself
class Ticket {
public:
    Ticket() = default;
    Ticket(const Ticket&) = delete;
    Ticket& operator=(const Ticket&) = delete;
    Ticket(Ticket&&) = default;
    Ticket& operator=(Ticket&&) = default;
    ~Ticket() = default;
};

class Owner {
public:
    Owner() : data_(std::make_unique<int>(1)) {}

private:
    std::unique_ptr<int> data_;
};

} // namespace

int main() {
    std::cout << std::boolalpha;

    std::cout << "== Step 1: copies and moves ==\n";
    Tracked a;
    Tracked::reset();
    takeByValue(a);
    printCounts("takeByValue(a)");
    takeByValue(std::move(a));
    printCounts("takeByValue(std::move(a))");
    takeByValue(makeTracked());
    printCounts("takeByValue(makeTracked())");
    takeByConstRef(a);
    printCounts("takeByConstRef(a)");

    std::cout << "== Step 2: a shallow copy ==\n";
    Resource resource;
    {
        const ShallowHandle first{resource};
        const ShallowHandle second{first};
        std::cout << "  handles alive: 2, owners counted: " << resource.owners << '\n';
    }
    std::cout << "  after both are destroyed, owners counted: " << resource.owners << " (released twice)\n";

    std::cout << "== Step 3: Rule of 5 ==\n";
    const IntBox original{42};
    const IntBox copy{original};
    std::cout << "copy has the same value: " << (copy.value() == original.value()) << '\n';
    std::cout << "copy has its own storage: " << (copy.address() != original.address()) << '\n';
    IntBox source{7};
    const IntBox target{std::move(source)};
    std::cout << "moved-from IntBox is empty: " << source.empty() << ", target value: " << target.value() << '\n';

    IntBox::reset();
    std::vector<IntBox> boxes;
    for (int i = 0; i < 8; ++i) {
        boxes.push_back(IntBox{i});
    }
    std::cout << "relocation used only moves: " << (IntBox::copies() == 0) << '\n';

    std::cout << "== Step 4: Rule of 0 ==\n";
    const Person alice{"alice", {90, 85, 70}};
    const Person copyOfAlice{alice};
    Person bob{"bob", {60}};
    const Person movedBob{std::move(bob)};
    std::cout << "copy: " << copyOfAlice.name() << " has " << copyOfAlice.scoreCount() << " scores\n";
    std::cout << "moved: " << movedBob.name() << " has " << movedBob.scoreCount() << " scores\n";
    std::cout << "Person is nothrow move constructible: " << std::is_nothrow_move_constructible_v<Person> << '\n';

    std::cout << "== Step 5: no copies ==\n";
    std::cout << "Ticket copyable: " << std::is_copy_constructible_v<Ticket>
              << ", movable: " << std::is_move_constructible_v<Ticket> << '\n';
    std::cout << "Owner (unique_ptr member) copyable: " << std::is_copy_constructible_v<Owner>
              << ", movable: " << std::is_move_constructible_v<Owner> << '\n';

    return 0;
}
