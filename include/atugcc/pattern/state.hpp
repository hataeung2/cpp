/**
 * @file state.hpp
 * @brief atugcc::pattern::state — std::variant + std::visit 기반 상태 머신
 *
 * 기존 `astate::` namespace 및 가상 함수 기반 구현을 C++23 스타일로 재작성.
 *
 * ==========================================================================
 * 학습 포인트
 * --------------------------------------------------------------------------
 * [1] std::variant<States...>
 *     - 여러 타입 중 하나를 저장하는 타입-세이프 유니온.
 *     - 모든 상태 타입을 힙 할당(shared_ptr) 없이 값으로 보관.
 *     - sizeof(variant) = max(sizeof(States...)) + 1 byte discriminant.
 *
 * [2] std::visit(visitor, variant)
 *     - variant 안의 실제 타입에 맞는 overload 를 컴파일 타임에 선택.
 *     - 가상 함수 vtable 디스패치보다 빠르고, 패턴 확장이 명시적.
 *
 * [3] overloaded 패턴 (Overloaded idiom)
 *     - 여러 람다를 하나의 visitor 객체로 합치는 관용구.
 *     - C++17 이상에서 CTAD(Class Template Argument Deduction) 활용.
 *
 * [4] std::expected (Core::Result)
 *     - transition 이 불가능한 경우 예외 대신 Result 반환.
 *
 * [5] atugcc::pattern::viz::Tracer 연동
 *     - 상태 전이 시 record_transition(), 스케줄 호출 시 record_message().
 *     - 출력은 호출자(main/test)가 tracer.format_terminal() 로 수행.
 * ==========================================================================
 */
#pragma once

#include <format>
#include <string_view>
#include <variant>

#include "atugcc/core/error.hpp"
#include "atugcc/pattern/visualizer.hpp"

namespace atugcc::pattern::state {

// ============================================================================
// [학습] overloaded 헬퍼
// 여러 람다를 하나의 std::visit 용 visitor 로 묶어주는 관용구.
//
// 사용 예:
//   std::visit(overloaded{
//       [](IdleState&)    { … },
//       [](StandbyState&) { … },
//   }, machine.current());
// ============================================================================

// ============================================================================
// overloaded 구조체 템플릿 정의
// typename... Ts 는 T가 여러 개일 수 있음을 나타낸다 (variadic template).
// 즉, 이 구조체는 아래와 같은 코드를 생성할 수 있다.
//  struct overloaded : Lambda1, Lambda2, Lambda3 { 
//      using Lambda1::operator();
//      using Lambda2::operator();
//      using Lambda3::operator();
//  };
// lambda 들이 operator() 를 제공하므로, overloaded 객체는 이 operator() 들을 모두 사용할 수 있다.
// ============================================================================
template <typename... Ts>
struct overloaded : Ts... {
    using Ts::operator()...;
};
// C++17 CTAD(Class Template Argument Deduction, 클래스 템플릿 인자 추론) 가이드 
// "->" 뒤에 오는 것은 이 구조체 템플릿이 어떤 타입으로 추론되어야 하는지를 명시한다.
// C++20 에서는 불필요하지만 명시하면 이해에 도움
template <typename... Ts>
overloaded(Ts...) -> overloaded<Ts...>;

// ============================================================================
// 상태 타입들 — 단순 태그 구조체
// [학습] 힙 할당 없이 값으로 보관. 각 상태에 필요한 데이터가 있다면 멤버 추가.
// ============================================================================
struct IdleState      { static constexpr std::string_view name = "IDLE";      };
struct StandbyState   { static constexpr std::string_view name = "STANDBY";   };
struct RunState       { static constexpr std::string_view name = "RUN";       };
struct AbortState     { static constexpr std::string_view name = "ABORT";     };
struct EmergencyState { static constexpr std::string_view name = "EMERGENCY"; };

// [학습] variant 에 가능한 상태를 열거.
//        어떤 상태가 가능한지 타입 시스템이 알고 있으므로 enum 불필요.
using MachineStateVariant = std::variant<
    IdleState,
    StandbyState,
    RunState,
    AbortState,
    EmergencyState
>;

// ============================================================================
// 현재 상태 이름을 string_view 로 반환
// ============================================================================
inline std::string_view state_name(const MachineStateVariant& s) {
    return std::visit(overloaded{
        [](const IdleState&)      { return IdleState::name;      },
        [](const StandbyState&)   { return StandbyState::name;   },
        [](const RunState&)       { return RunState::name;       },
        [](const AbortState&)     { return AbortState::name;     },
        [](const EmergencyState&) { return EmergencyState::name; },
    }, s);
}

// ============================================================================
// Machine — 상태 머신 컨텍스트
// ============================================================================
class Machine {
public:
    explicit Machine(viz::Tracer& tracer = viz::get_global_tracer())
        : state_{ IdleState{} }
        , tracer_(tracer)
    {}

    // ------------------------------------------------------------------
    // schedule(): 현재 상태의 동작을 실행하고 메시지를 기록
    // [학습] std::visit 으로 상태별 동작 분기.
    // switch-case 대신 람다로 각 상태에 대한 동작을 명시적으로 표현한다.
    // ------------------------------------------------------------------
    void schedule() {
        std::visit(overloaded{
            [&](const IdleState&) {
                (void)tracer_.record_message("Machine", "IO", "update_io()");
            },
            [&](const StandbyState&) {
                (void)tracer_.record_message("Machine", "Actuator", "prepare()");
            },
            [&](const RunState&) {
                (void)tracer_.record_message("Machine", "Controller", "run_cycle()");
            },
            [&](const AbortState&) {
                (void)tracer_.record_message("Machine", "SafetyModule", "abort_sequence()");
            },
            [&](const EmergencyState&) {
                (void)tracer_.record_message("Machine", "Alarm", "emergency_stop()");
            },
        }, state_);
    }

    // ------------------------------------------------------------------
    // transition(target): 전이 가능하면 상태 변경, 아니면 Unexpected 반환
    // [학습] std::expected 로 실패를 값으로 전달 (예외 없음).
    // ------------------------------------------------------------------
    [[nodiscard]] core::Result transition(const MachineStateVariant& target) {
        if (!is_transition_allowed(state_, target)) {
            return std::unexpected(core::CoreError::InvalidArgument);
        }
        const auto old_name = state_name(state_);
        state_ = target;
        const auto new_name = state_name(state_);
        (void)tracer_.record_transition(old_name, new_name,
            std::format("{}->{}", old_name, new_name));
        return {};
    }

    [[nodiscard]] std::string_view current_state_name() const {
        return state_name(state_);
    }

private:
    // ------------------------------------------------------------------
    // 전이 허용 규칙
    // [학습] 중첩 std::visit: (현재, 목표) 쌍에 대한 매트릭스.
    //        variant index 비교보다 의미가 명확하고 오타를 컴파일러가 잡는다.
    // ------------------------------------------------------------------
    static bool is_transition_allowed(
        const MachineStateVariant& from,
        const MachineStateVariant& to)
    {
        return std::visit(overloaded{
            // Idle → Standby, Emergency
            [](const IdleState&,      const StandbyState&)   { return true; },
            [](const IdleState&,      const EmergencyState&) { return true; },
            // Standby → Run, Abort, Emergency
            [](const StandbyState&,   const RunState&)        { return true; },
            [](const StandbyState&,   const AbortState&)      { return true; },
            [](const StandbyState&,   const EmergencyState&)  { return true; },
            // Run → Standby, Abort, Emergency
            [](const RunState&,       const StandbyState&)    { return true; },
            [](const RunState&,       const AbortState&)      { return true; },
            [](const RunState&,       const EmergencyState&)  { return true; },
            // Abort / Emergency → Idle
            [](const AbortState&,     const IdleState&)       { return true; },
            [](const EmergencyState&, const IdleState&)       { return true; },
            // 그 외 불허
            [](const auto&, const auto&) { return false; },
        }, from, to);
    }

    MachineStateVariant state_;
    viz::Tracer&        tracer_;
};

} // namespace atugcc::pattern::state