/**
 * @file observer.hpp
 * @brief atugcc::pattern::observer — Concept 기반 Observer 패턴
 *
 * 기존 `observer::` namespace 및 가상 함수 기반 구현을 C++20 Concepts 스타일로 재작성.
 *
 * ==========================================================================
 * 학습 포인트
 * --------------------------------------------------------------------------
 * [1] Concept (C++20)
 *     - ObserverOf<T, Subject>: T 가 Observer 로 동작하는지 컴파일 타임에 검증.
 *     - 가상 함수 대신 concept 로 인터페이스를 표현하면
 *       vtable 없이 타입 안전성을 보장할 수 있다.
 *
 * [2] std::vector + std::erase_if (C++20)
 *     - 만료된 약참조(weak_ptr) 구독자를 한 줄로 제거.
 *
 * [3] std::weak_ptr
 *     - Subject 가 Observer 의 수명을 소유하지 않도록 약참조 사용.
 *     - notify 시 lock() 으로 아직 살아있는지 확인한다.
 *
 * [4] std::string_view 반환 vs std::string 반환 차이
 *     - getData1/2 는 내부 std::string 참조를 반환 — 수명이 Subject 에 묶인다.
 *
 * [5] Tracer 연동
 *     - notify_observers() 시 Subject→Observer 메시지를 record_message() 로 기록.
 *     - Observer 의 pull() 에서도 Observer→Subject 방향 기록.
 * ==========================================================================
 */
#pragma once

#include <algorithm>
#include <concepts>
#include <functional>
#include <memory>
#include <string>
#include <string_view>
#include <vector>

#include "atugcc/pattern/visualizer.hpp"

namespace atugcc::pattern::observer {

// ============================================================================
// 전방 선언
// ============================================================================
class Subject;

// ============================================================================
// [학습] Concept 정의
//
// ObserverOf<T> 는 T 가 아래 두 멤버 함수를 갖는지 컴파일 타임에 확인한다:
//   void T::on_notify(const Subject&)   — Subject 가 변경됐을 때 호출
//   std::string T::display()            — 현재 보유 데이터를 문자열로 반환
//
// 기존 코드에서 순수 가상 함수(pull, display)가 하던 역할을 concept 로 대체.
// 클래스 계층 없이도 다형성을 표현할 수 있다는 점이 핵심. 
//  => 상속이(vtable 참조 오버헤드가) 사라지고 컴파일러가 인라인 최적화를 더 효율적으로 가능하게 함
// ============================================================================
template <typename T>
concept ObserverOf = requires(T& obs, const Subject& subj) {
    { obs.on_notify(subj) } -> std::same_as<void>;
    { obs.display()       } -> std::convertible_to<std::string>;
};

// ============================================================================
// Subject
// ============================================================================
class Subject {
public:
    explicit Subject(viz::Tracer& tracer = viz::get_global_tracer())
        : data1_("data1"), data2_("data2")
        , tracer_(tracer)
    {}

    // ------------------------------------------------------------------
    // 구독자 등록 / 해제
    // [학습] std::weak_ptr 을 저장해 Subject 가 수명을 관리하지 않게 한다.
    // ------------------------------------------------------------------
    void register_observer(std::weak_ptr<void> obs_handle,
                           std::function<void(const Subject&)> on_notify_fn,
                           std::function<std::string()>        display_fn,
                           std::string_view name)
    {
        entries_.push_back(Entry{
            .handle    = std::move(obs_handle),
            .on_notify = std::move(on_notify_fn),
            .display   = std::move(display_fn),
            .name      = std::string(name),
        });
    }

    void remove_expired() {
        // [학습] std::erase_if (C++20): predicate 가 true 인 원소 제거
        std::erase_if(entries_, [](const Entry& e) {
            return e.handle.expired();
        });
    }

    // ------------------------------------------------------------------
    // 데이터 변경 + 알림
    // ------------------------------------------------------------------
    void set_data(std::string_view d1, std::string_view d2) {
        data1_ = d1;
        data2_ = d2;
        notify_observers();
    }

    [[nodiscard]] const std::string& data1() const noexcept { return data1_; }
    [[nodiscard]] const std::string& data2() const noexcept { return data2_; }

    void notify_observers() {
        remove_expired();
        for (auto& e : entries_) {
            // 구독자가 아직 살아있는지 확인하고, 살아있다면 알림과 메시지 기록을 한다.
            // lock() 해서 shared_ptr 얻기 → 구독자가 살아있으면 on_notify 호출 (lock() 실패했다는 것은 구독자가 소멸됐다는 뜻이고 nullptr 반환)
            if (auto sp = e.handle.lock()) {
                (void)tracer_.record_message("Subject", e.name, "on_notify()");
                e.on_notify(*this);
            }
        }
    }

    // 모든 구독자의 display() 를 호출해 결과를 반환
    [[nodiscard]] std::vector<std::string> collect_displays() const {
        std::vector<std::string> results;
        for (const auto& e : entries_) {
            // lock이 아니고 expired() 체크로 구독자가 살아있는지 확인한다. (display() 는 const 이므로 handle.lock() 대신 expired() 로 충분)
            // expired는 참조횟수를 올리지 않는다. display는 변경작업이 아니므로 expired로 오버헤드를 만들지 않는다.
            if (!e.handle.expired()) {
                results.push_back(e.display());
            }
        }
        return results;
    }

private:
    struct Entry {
        std::weak_ptr<void>                    handle;
        std::function<void(const Subject&)>    on_notify;
        std::function<std::string()>           display;
        std::string                            name;
    };

    std::string          data1_;
    std::string          data2_;
    std::vector<Entry>   entries_;
    viz::Tracer&         tracer_;
};

// ============================================================================
// 구독자 등록 헬퍼 (Concept 제약 적용)
// [학습] requires 절로 ObserverOf 개념을 만족하는 T 만 등록 허용.
//        만족하지 않으면 컴파일 에러와 함께 어떤 제약을 위반했는지 표시.
// 
// template으로 ObserverOf<T> 제약을 걸어서, T 가 ObserverOf 개념을 만족하지 않으면 컴파일 타임에 에러가 발생한다.
// ============================================================================
template <ObserverOf T>
void subscribe(Subject& subject, std::shared_ptr<T> obs, std::string_view name) {
    subject.register_observer(
        // 왜 void 포인터로 저장하는가? → Subject 는 구독자의 구체 타입을 몰라도 되도록 하기 위해서이다. (type erasure)
        // 람다 캡쳐 부분에서 std::weak_ptr<T> 으로 다시 구체 타입으로 변환해서 사용한다.
        std::static_pointer_cast<void>(obs), 
        [obs_weak = std::weak_ptr<T>(obs)](const Subject& s) {
            if (auto sp = obs_weak.lock()) {
                sp->on_notify(s);
            }
        },
        [obs_weak = std::weak_ptr<T>(obs)]() -> std::string {
            if (auto sp = obs_weak.lock()) {
                return sp->display();
            }
            return "(expired)";
        },
        name
    );
}

// ============================================================================
// 구체 Observer 구현 예시
// ============================================================================

/// data1 만 추적하는 관찰자
class DataObserver1 {
public:
    void on_notify(const Subject& s) {
        cached_ = s.data1();
    }
    [[nodiscard]] std::string display() const {
        return std::string("Observer1: ") + cached_;
    }
private:
    std::string cached_;
};
static_assert(ObserverOf<DataObserver1>, "DataObserver1 must satisfy ObserverOf");

/// data1 + data2 를 합쳐서 추적하는 관찰자
class DataObserver2 {
public:
    void on_notify(const Subject& s) {
        cached_ = s.data1() + ", " + s.data2();
    }
    [[nodiscard]] std::string display() const {
        return std::string("Observer2: ") + cached_;
    }
private:
    std::string cached_;
};
static_assert(ObserverOf<DataObserver2>, "DataObserver2 must satisfy ObserverOf");

} // namespace atugcc::pattern::observer