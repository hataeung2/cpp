/**
 * @file main.cpp
 * @brief 레슨 object_lifetime — 객체의 수명: 스코프, 생성·소멸 순서, 임시 객체, RAII
 * @brief Lesson object_lifetime — object lifetime: scope, construction and destruction order, temporaries, RAII
 *
 * 생성과 소멸을 출력하는 작은 타입으로 객체가 언제 만들어지고 사라지는지 보고, 소멸자로 자원을 돌려주는 RAII 가드를 확인한다
 * A small type that prints its construction and destruction shows when objects are made and gone, and an RAII guard returns a resource in its destructor
 */
#include <iostream>
#include <memory>
#include <stdexcept>
#include <string>
#include <utility>

namespace {

// 생성과 소멸 순서를 한 줄에 모아 보여 주는 기록
// A record that gathers the construction and destruction order into one line each
struct Trace {
    std::string built;
    std::string gone;

    void clear() {
        built.clear();
        gone.clear();
    }

    static void append(std::string& list, const std::string& name) {
        if (!list.empty()) {
            list += ", ";
        }
        list += name;
    }
};

[[nodiscard]] Trace& trace() {
    static Trace instance;
    return instance;
}

// 생성과 소멸을 출력하는 작은 타입 (복사는 막아 두어 출력이 생성·소멸 한 쌍으로만 나온다)
// A small type that prints construction and destruction (copying is blocked so output is only one construct/destroy pair)
class Noisy {
public:
    explicit Noisy(std::string name) : name_(std::move(name)) {
        std::cout << "  + " << name_ << '\n';
        Trace::append(trace().built, name_);
        ++alive_;
    }

    Noisy(const Noisy&) = delete;
    Noisy& operator=(const Noisy&) = delete;

    ~Noisy() {
        std::cout << "  - " << name_ << '\n';
        Trace::append(trace().gone, name_);
        --alive_;
    }

    [[nodiscard]] const std::string& name() const {
        return name_;
    }

    [[nodiscard]] static int alive() {
        return alive_;
    }

private:
    std::string name_;
    static inline int alive_ = 0;
};

// 2. 기반 클래스와 멤버의 생성·소멸 순서
// 2. Construction and destruction order of a base class and members
class Base {
public:
    Base() {
        std::cout << "  Base body\n";
    }

private:
    Noisy base_part_{"base"};
};

class Derived : public Base {
public:
    Derived() {
        std::cout << "  Derived body\n";
    }

private:
    Noisy first_{"first"};
    Noisy second_{"second"};
};

// 3. 임시 객체를 만들어 돌려주는 함수 (보장된 복사 생략으로 한 번만 만들어진다)
// 3. A function that makes and returns a temporary (guaranteed copy elision makes it just once)
[[nodiscard]] Noisy makeNoisy(std::string name) {
    return Noisy{std::move(name)};
}

// 4. RAII 가드: 생성자에서 자원을 얻고 소멸자에서 돌려준다 (자원은 출력 줄로 표현)
// 4. RAII guard: acquire the resource in the constructor and return it in the destructor (the resource is a line of output)
class ScopedFile {
public:
    explicit ScopedFile(std::string path) : path_(std::move(path)) {
        std::cout << "  open " << path_ << '\n';
        ++opened_;
    }

    ScopedFile(const ScopedFile&) = delete;
    ScopedFile& operator=(const ScopedFile&) = delete;

    ~ScopedFile() {
        std::cout << "  close " << path_ << '\n';
        ++closed_;
    }

    [[nodiscard]] static int opened() {
        return opened_;
    }

    [[nodiscard]] static int closed() {
        return closed_;
    }

private:
    std::string path_;
    static inline int opened_ = 0;
    static inline int closed_ = 0;
};

// 단계 번호에 따라 정상 종료하거나 예외를 던지는 함수: 어느 경로로 나가도 가드의 소멸자가 불린다
// A function that ends normally or throws depending on the stage number: the guard's destructor runs whichever way it leaves
void process(int stage) {
    const ScopedFile file{"data.txt"};
    if (stage == 1) {
        throw std::runtime_error("stage 1 failed");
    }
    std::cout << "  processed stage " << stage << '\n';
}

} // namespace

int main() {
    std::cout << "== Step 1: scope decides the lifetime ==\n";
    {
        const Noisy outer{"outer"};
        std::cout << "  inside the scope, alive: " << Noisy::alive() << '\n';
        {
            const Noisy inner{"inner"};
            std::cout << "  inside the inner scope, alive: " << Noisy::alive() << '\n';
        }
        std::cout << "  back in the outer scope: " << outer.name() << '\n';
    }
    std::cout << "after the scopes, alive: " << Noisy::alive() << '\n';

    std::cout << "== Step 2: members and base classes ==\n";
    trace().clear();
    {
        const Derived derived;
        std::cout << "  derived is complete\n";
    }
    std::cout << "construction order: " << trace().built << '\n';
    std::cout << "destruction order: " << trace().gone << '\n';

    std::cout << "== Step 3: temporaries ==\n";
    // 임시 객체는 그것을 만든 문장이 끝나면 사라진다
    // A temporary is gone when the statement that made it ends
    static_cast<void>(makeNoisy("temporary"));
    std::cout << "alive after the statement: " << Noisy::alive() << '\n';
    {
        // const 참조에 묶인 임시 객체는 그 참조의 스코프가 끝날 때까지 산다
        // A temporary bound to a const reference lives until that reference's scope ends
        const Noisy& extended = makeNoisy("extended");
        std::cout << "  bound to a reference: " << extended.name() << ", alive: " << Noisy::alive() << '\n';
    }
    std::cout << "alive after the block: " << Noisy::alive() << '\n';

    std::cout << "== Step 4: RAII guard ==\n";
    process(0);
    try {
        process(1);
    } catch (const std::runtime_error& error) {
        std::cout << "  caught: " << error.what() << '\n';
    }
    std::cout << "guard summary: opened " << ScopedFile::opened() << ", closed " << ScopedFile::closed() << '\n';

    std::cout << "== Step 5: new and delete versus unique_ptr ==\n";
    // new 로 만든 객체는 delete 를 직접 짝지어야 한다 (사이에 return 이나 예외가 있으면 누수가 된다: 여기서는 바로 해제한다)
    // An object made with new needs a matching delete by hand (a return or exception in between would leak it: here it is freed at once)
    auto* raw = new Noisy{"raw"};
    std::cout << "  raw pointer alive: " << Noisy::alive() << '\n';
    delete raw;
    {
        // unique_ptr 는 스코프가 끝나면 알아서 소멸시킨다
        // unique_ptr destroys it by itself when the scope ends
        const auto owned = std::make_unique<Noisy>("owned");
        std::cout << "  unique_ptr alive: " << Noisy::alive() << '\n';
    }
    std::cout << "alive at the end: " << Noisy::alive() << '\n';

    return 0;
}
