/**
 * @file main.cpp
 * @brief 레슨 smart_pointers — 스마트 포인터와 소유권: unique_ptr, shared_ptr, weak_ptr
 * @brief Lesson smart_pointers — Smart pointers and ownership: unique_ptr, shared_ptr, weak_ptr
 *
 * 누가 객체를 지우는지(소유권)를 타입으로 쓰면 언제 지워지는지가 코드에 보인다. 생성·소멸을 찍는 타입으로 unique_ptr 의 단독 소유와 이동,
 * 함수 시그니처가 말하는 소유권, vector<unique_ptr<Base>>, shared_ptr 의 공유 소유, weak_ptr 로 끊는 순환을 출력으로 확인한다
 * Writing who deletes an object (ownership) as a type makes it visible in the code when it is deleted. With types that print their
 * construction and destruction, see unique_ptr's sole ownership and moves, the ownership a function signature states,
 * vector<unique_ptr<Base>>, shared_ptr's shared ownership, and a cycle broken with weak_ptr
 */
#include <iostream>
#include <memory>
#include <string>
#include <string_view>
#include <type_traits>
#include <utility>
#include <vector>

namespace {

// 생성과 소멸을 찍고, 살아 있는 개수를 센다. 자원은 실제 메모리가 아니라 이 출력과 카운터로 본다
// Prints its construction and destruction and counts the live objects. The resource is seen through this output and counter
class Widget {
public:
    explicit Widget(std::string name) : name_(std::move(name)) {
        ++alive_;
        std::cout << "  Widget " << name_ << " built\n";
    }

    Widget(const Widget&) = delete;
    Widget& operator=(const Widget&) = delete;

    virtual ~Widget() {
        --alive_;
        std::cout << "  ~Widget " << name_ << '\n';
    }

    [[nodiscard]] const std::string& name() const {
        return name_;
    }

    [[nodiscard]] virtual std::string_view kind() const {
        return "widget";
    }

    [[nodiscard]] static int alive() {
        return alive_;
    }

private:
    inline static int alive_ = 0;
    std::string name_;
};

// 3단계에서 기반 클래스 포인터로 담는 파생 클래스
// A derived class that step 3 holds through a base-class pointer
class Gadget : public Widget {
public:
    using Widget::Widget;

    [[nodiscard]] std::string_view kind() const override {
        return "gadget";
    }
};

// 2. 함수 시그니처가 소유권을 말한다
// 2. A function signature states the ownership
// unique_ptr 를 돌려주는 함수: 만든 객체의 소유권을 호출한 쪽에 준다
// A function that returns a unique_ptr: it gives the ownership of the new object to the caller
[[nodiscard]] std::unique_ptr<Widget> makeWidget(std::string name) {
    return std::make_unique<Widget>(std::move(name));
}

// const 참조를 받는 함수: 빌려서 쓸 뿐 지우지 않는다
// A function that takes a const reference: it only borrows and never deletes
void show(const Widget& widget) {
    std::cout << "  show borrows " << widget.name() << '\n';
}

// unique_ptr 를 값으로 받는 함수: 소유권을 가져가고, 호출이 끝날 때(다음 문장 전에) 매개변수와 함께 객체가 지워진다
// A function that takes a unique_ptr by value: it takes the ownership, and the object goes with the parameter when the call finishes (before the next statement)
void consume(std::unique_ptr<Widget> widget) {
    std::cout << "  consume owns " << widget->name() << '\n';
}

// 5. 서로를 가리키는 두 객체: 부모는 자식을 소유하고(shared_ptr), 자식은 부모를 소유하지 않고 바라만 본다(weak_ptr)
// 5. Two objects that point at each other: the parent owns the child (shared_ptr); the child only watches the parent (weak_ptr)
class Parent;

class Child {
public:
    Child() {
        ++alive_;
    }

    Child(const Child&) = delete;
    Child& operator=(const Child&) = delete;

    ~Child() {
        --alive_;
        std::cout << "  ~Child\n";
    }

    void setParent(const std::shared_ptr<Parent>& parent) {
        parent_ = parent;
    }

    [[nodiscard]] static int alive() {
        return alive_;
    }

private:
    inline static int alive_ = 0;
    std::weak_ptr<Parent> parent_;
};

class Parent {
public:
    Parent() {
        ++alive_;
    }

    Parent(const Parent&) = delete;
    Parent& operator=(const Parent&) = delete;

    ~Parent() {
        --alive_;
        std::cout << "  ~Parent\n";
    }

    void adopt(std::shared_ptr<Child> child) {
        child_ = std::move(child);
    }

    [[nodiscard]] static int alive() {
        return alive_;
    }

private:
    inline static int alive_ = 0;
    std::shared_ptr<Child> child_;
};

} // namespace

int main() {
    std::cout << std::boolalpha;

    std::cout << "== Step 1: unique_ptr, the sole owner ==\n";
    {
        auto owner = std::make_unique<Widget>("solo");
        std::cout << "owner holds " << owner->name() << '\n';
        std::cout << "unique_ptr can be copied: " << std::is_copy_constructible_v<std::unique_ptr<Widget>> << '\n';
        // 복사는 안 되고 이동만 된다: 소유권이 next 로 넘어가고, 객체는 여전히 하나다
        // It cannot be copied, only moved: the ownership passes to next, and there is still one object
        auto next = std::move(owner);
        std::cout << "after the move, next holds " << next->name() << ", alive widgets: " << Widget::alive() << '\n';
        std::cout << "leaving the block\n";
    }
    std::cout << "alive widgets: " << Widget::alive() << '\n';

    std::cout << "== Step 2: ownership in function signatures ==\n";
    auto made = makeWidget("parcel");
    show(*made);
    consume(std::move(made));
    std::cout << "back in main\n";

    std::cout << "== Step 3: vector<unique_ptr<Widget>> ==\n";
    std::vector<std::unique_ptr<Widget>> crate;
    crate.push_back(std::make_unique<Widget>("a"));
    crate.push_back(std::make_unique<Gadget>("b"));
    crate.push_back(std::make_unique<Gadget>("c"));
    for (const auto& item : crate) {
        std::cout << "  " << item->kind() << ' ' << item->name() << '\n';
    }
    std::cout << "erase the first element:\n";
    crate.erase(crate.begin());
    std::cout << "move the last element out:\n";
    auto taken = std::move(crate.back());
    crate.pop_back();
    std::cout << "  taken holds " << taken->kind() << ' ' << taken->name() << ", crate size " << crate.size() << '\n';
    std::cout << "clear the crate, then reset taken:\n";
    crate.clear();
    taken.reset();
    std::cout << "alive widgets: " << Widget::alive() << '\n';

    std::cout << "== Step 4: shared_ptr, shared ownership ==\n";
    std::shared_ptr<Widget> survivor;
    {
        auto first = std::make_shared<Widget>("shared");
        std::cout << "use_count: " << first.use_count() << '\n';
        {
            const auto second = first;
            std::cout << "with a second owner, use_count: " << first.use_count() << '\n';
        }
        std::cout << "second owner gone, use_count: " << first.use_count() << '\n';
        std::cout << "leaving the block\n";
    }
    std::cout << "after the block, survivor use_count: " << survivor.use_count() << '\n';
    survivor.reset();
    std::cout << "alive widgets: " << Widget::alive() << '\n';

    std::cout << "== Step 5: weak_ptr breaks a cycle ==\n";
    std::weak_ptr<Parent> watcher;
    {
        auto parent = std::make_shared<Parent>();
        auto child = std::make_shared<Child>();
        child->setParent(parent);
        parent->adopt(child);
        watcher = parent;
        std::cout << "parent use_count: " << parent.use_count() << ", child use_count: " << child.use_count() << '\n';
        std::cout << "watcher.lock() gives the parent: " << (watcher.lock() != nullptr) << '\n';
        std::cout << "leaving the block\n";
    }
    std::cout << "parent expired: " << watcher.expired() << '\n';
    std::cout << "alive parents and children: " << Parent::alive() + Child::alive() << '\n';
    // 순환이 남아 있으면 스스로는 풀리지 않으므로 손으로 끊는다. 원본에서는 watcher 가 이미 비어 있어 이 블록이 돌지 않는다
    // A cycle that is left does not undo itself, so break it by hand. In the original, watcher is already empty and this block does not run
    if (const auto parent = watcher.lock()) {
        std::cout << "breaking the cycle by hand\n";
        parent->adopt(nullptr);
    }
    std::cout << "alive at the end: " << Parent::alive() + Child::alive() << '\n';

    return 0;
}
