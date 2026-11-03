/**
 * @file main.cpp
 * @brief 레슨 lambda_capture — 캡처 방식별 동작을 출력으로 확인한다
 * @brief Lesson lambda_capture — see what each capture mode does through the output
 *
 * 유닛: lessons/units/lambda_capture/lambda_capture.hpp
 * Unit: lessons/units/lambda_capture/lambda_capture.hpp
 */
#include <functional>
#include <iostream>
#include <memory>
#include <utility>

#include "units/lambda_capture/lambda_capture.hpp"

namespace lc = atugcc::lessons::lambda_capture;

int main() {
    // 1. 값 캡처: 두 counter 는 서로의 count 를 모른다
    // 1. By-value capture: the two counters do not know each other's count
    auto first = lc::makeCounterByValue(10);
    // closure 복사 → count 도 복사
    // Copying the closure copies count too
    auto second = first;
    std::cout << "[value]     first: " << first() << ", " << first()
              << " / second: " << second() << '\n';   // 11, 12 / 11

    // 2. 참조 캡처: 람다가 바꾼 것은 원본 total 이다
    // 2. By-reference capture: what the lambda changes is the original total
    int total = 0;
    auto add = lc::makeAdderByReference(total);
    add(3);
    add(4);
    std::cout << "[reference] total = " << total << '\n';   // 7

    // 3. init capture (move): 인자로 넘긴 문자열은 closure 안으로 옮겨진다
    // 3. Init capture (move): the string passed as the argument is moved into the closure
    auto greet = lc::makeGreeter("atugcc");
    std::cout << "[init]      " << greet("Hello") << '\n';

    // 4. move-only closure: 복사는 안 되고 move 만 된다
    // 4. Move-only closure: it cannot be copied, only moved
    auto owner = lc::makeOwner(std::make_unique<int>(42));
    auto moved = std::move(owner);
    std::move_only_function<int()> holder = std::move(moved);   // C++23
    std::cout << "[move-only] value = " << holder() << '\n';

    return 0;
}
