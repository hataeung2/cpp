/**
 * @file lambda_capture.hpp
 * @brief 유닛 lambda_capture — 캡처 방식별로 람다가 무엇을 가지고 다니는지
 *
 * [학습] 람다는 캡처한 값을 멤버로 가진 이름 없는 클래스(closure type)의 객체다.
 *   [count = start]        → 멤버 count 를 복사로 초기화 (값 캡처, init capture)
 *   [&total]               → 멤버가 total 을 가리키는 참조 (참조 캡처: 원본보다 오래 살면 dangling)
 *   [name = std::move(n)]  → 멤버를 move 로 초기화 (C++14 init capture)
 *   unique_ptr 캡처        → closure 도 move-only 가 된다 (std::function 에는 못 담고 std::move_only_function 에는 담는다)
 */
#pragma once

#include <format>
#include <memory>
#include <string>
#include <string_view>
#include <utility>

namespace atugcc::lessons::lambda_capture {

/// 호출할 때마다 1씩 늘어난 값을 돌려준다. count 는 closure 안의 사본이다.
[[nodiscard]] inline auto makeCounterByValue(int start) {
    // [학습] mutable 이 없으면 operator() 가 const 라서 count 를 바꿀 수 없다.
    return [count = start]() mutable { return ++count; };
}

/// 받은 값을 total 에 더한다. total 은 호출자의 변수 그 자체다.
[[nodiscard]] inline auto makeAdderByReference(int& total) {
    // [학습] 이 람다를 total 보다 오래 보관하면 dangling reference 가 된다.
    return [&total](int value) { total += value; };
}

/// name 을 closure 안으로 옮겨(move) 두고 인사말을 만든다.
[[nodiscard]] inline auto makeGreeter(std::string name) {
    return [name = std::move(name)](std::string_view greeting) {
        return std::format("{}, {}!", greeting, name);
    };
}

/// unique_ptr 을 소유하는 move-only 람다. 복사하려 하면 컴파일 오류가 난다.
[[nodiscard]] inline auto makeOwner(std::unique_ptr<int> value) {
    return [value = std::move(value)]() { return *value; };
}

} // namespace atugcc::lessons::lambda_capture
