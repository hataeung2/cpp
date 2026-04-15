/**
 * @file visualizer.hpp
 * @brief atugcc::pattern::viz — 디자인 패턴 런타임 트레이서
 *
 * 이 헤더 하나로 패턴 실행 흐름을 기록하고, 두 가지 형식의 문자열로
 * 변환(터미널 ASCII / D2)할 수 있다.
 *
 * 출력 책임은 호출자에게 있다:
 *   std::cout << tracer.format_terminal();
 *   atugcc::core::Logger::global().log("{}", tracer.format_d2());
 *
 * ==========================================================================
 * 학습 포인트 (C++20/23)
 * --------------------------------------------------------------------------
 * [1] Concept  — EventSink concept: Tracer 내부 저장 방식을 추상화할 때 사용
 * [2] std::expected — record_* API 는 Result 반환(버퍼 오버플로 등 실패 표현)
 * [3] std::string_view — 입력은 항상 string_view, 내부 저장은 std::string
 * [4] std::mutex + std::shared_mutex — record(write) vs format(read) 분리 락
 * [5] std::source_location — EventMeta 에 자동 주입
 * [6] Designated Initializers (C++20) — EventMeta 구조체 초기화 시 활용
 * ==========================================================================
 */
#pragma once

#include <algorithm>
#include <chrono>
#include <deque>
#include <format>
#include <mutex>
#include <shared_mutex>
#include <source_location>
#include <string>
#include <string_view>
#include <vector>

#include "atugcc/core/error.hpp"

namespace atugcc::pattern::viz {

// ============================================================================
// 이벤트 메타데이터
// C++20 Designated Initializer 로 초기화:
//   EventMeta meta{ .location = std::source_location::current() };
// ============================================================================
struct EventMeta {
    std::source_location location;
    std::chrono::system_clock::time_point timestamp{ std::chrono::system_clock::now() };
};

// ============================================================================
// 세 가지 이벤트 타입
// ============================================================================

/// 시퀀스 메시지: A가 B에게 어떤 요청을 보냈는가
struct Message {
    std::string from;       ///< 송신자 (ex. "Subject", "Invoker")
    std::string to;         ///< 수신자 (ex. "Observer1", "Receiver")
    std::string action;     ///< 메시지/행위 (ex. "notify()", "execute()")
    EventMeta   meta;
};

/// 상태 전이: 어떤 이벤트로 상태가 바뀌었는가
struct Transition {
    std::string old_state;  ///< 이전 상태 (ex. "LOCKED")
    std::string new_state;  ///< 다음 상태 (ex. "UNLOCKED")
    std::string trigger;    ///< 전이 원인 (ex. "coin_inserted")
    EventMeta   meta;
};

/// 구조 노드: 객체 계층 트리 (Decorator, Composite 등)
struct Node {
    std::string parent;         ///< 상위 컴포넌트
    std::string child;          ///< 하위 컴포넌트
    std::string relation_type;  ///< 관계 종류 (ex. "wraps", "contains", "delegates")
    EventMeta   meta;
};

// ============================================================================
// EventSink Concept
// --------------------------------------------------------------------------
// [학습] Concept 는 함수 호환성을 컴파일 타임에 검사한다.
// Tracer 가 기록한 이벤트를 외부 싱크(Logger, 파일, 테스트 mock 등)로
// 흘려보낼 때 이 concept 를 활용한다.
//
// T 가 EventSink<Message> 를 만족하려면:
//   void T::on_event(const Message&) 가 존재해야 한다.
// ============================================================================
template <typename T, typename Event>
concept EventSink = requires(T& sink, const Event& e) {
    { sink.on_event(e) } -> std::same_as<void>;
};

// ============================================================================
// Tracer
// --------------------------------------------------------------------------
// - record_*(…) : 이벤트를 내부 버퍼에 저장 (write → unique_lock)
// - format_terminal() : ANSI/ASCII 문자열 반환  (read → shared_lock)
// - format_d2()       : D2 스니펫 문자열 반환 (read → shared_lock)
// - snapshot_*()      : 테스트/검사용 복사본 반환
// - get_global_tracer(): 프로세스 전역 싱글톤
//
// [학습] std::shared_mutex:
//   여러 스레드가 동시에 format_(read) 를 호출할 수 있도록 공유 락을 허용.
//   record_(write) 는 단독 점유 락(unique_lock) 사용.
// ============================================================================
class Tracer {
public:
    static constexpr std::size_t kDefaultCapacity = 1024;

    explicit Tracer(std::size_t capacity = kDefaultCapacity)
        : capacity_(capacity) {}

    // ------------------------------------------------------------------
    // record API — 실패 시 core::Result 로 표현
    // [학습] std::expected<void, CoreError>:
    //   예외 대신 값으로 실패를 전달. capacity 초과 시 Unexpected 반환.
    // ------------------------------------------------------------------

    [[nodiscard]] core::Result record_message(
        std::string_view from,
        std::string_view to,
        std::string_view action,
        std::source_location loc = std::source_location::current())
    {
        std::unique_lock lock(mutex_);
        if (messages_.size() >= capacity_) {
            return std::unexpected(core::CoreError::Unexpected);
        }
        messages_.push_back(Message{
            .from   = std::string(from),
            .to     = std::string(to),
            .action = std::string(action),
            .meta   = EventMeta{ .location = loc },
        });
        return {};
    }

    [[nodiscard]] core::Result record_transition(
        std::string_view old_state,
        std::string_view new_state,
        std::string_view trigger,
        std::source_location loc = std::source_location::current())
    {
        std::unique_lock lock(mutex_);
        if (transitions_.size() >= capacity_) {
            return std::unexpected(core::CoreError::Unexpected);
        }
        transitions_.push_back(Transition{
            .old_state = std::string(old_state),
            .new_state = std::string(new_state),
            .trigger   = std::string(trigger),
            .meta      = EventMeta{ .location = loc },
        });
        return {};
    }

    [[nodiscard]] core::Result push_node(
        std::string_view parent,
        std::string_view child,
        std::string_view relation_type,
        std::source_location loc = std::source_location::current())
    {
        std::unique_lock lock(mutex_);
        if (nodes_.size() >= capacity_) {
            return std::unexpected(core::CoreError::Unexpected);
        }
        nodes_.push_back(Node{
            .parent        = std::string(parent),
            .child         = std::string(child),
            .relation_type = std::string(relation_type),
            .meta          = EventMeta{ .location = loc },
        });
        return {};
    }

    // ------------------------------------------------------------------
    // 출력 문자열 생성 — 포맷터에 위임
    // 선언만 여기에, 구현은 detail/terminal_formatter.hpp 와
    // detail/d2_formatter.hpp 에서 포함 후 인라인 제공.
    // ------------------------------------------------------------------
    [[nodiscard]] std::string format_terminal() const;
    [[nodiscard]] std::string format_d2() const;

    // ------------------------------------------------------------------
    // 스냅샷 — 테스트용 복사본 반환
    // [학습] std::shared_lock 으로 다중 독자 허용
    // ------------------------------------------------------------------
    [[nodiscard]] std::vector<Message>    snapshot_messages()    const {
        std::shared_lock lock(mutex_);
        return { messages_.begin(), messages_.end() };
    }
    [[nodiscard]] std::vector<Transition> snapshot_transitions() const {
        std::shared_lock lock(mutex_);
        return { transitions_.begin(), transitions_.end() };
    }
    [[nodiscard]] std::vector<Node>       snapshot_nodes()       const {
        std::shared_lock lock(mutex_);
        return { nodes_.begin(), nodes_.end() };
    }

    void clear() {
        std::unique_lock lock(mutex_);
        messages_.clear();
        transitions_.clear();
        nodes_.clear();
    }

    // ------------------------------------------------------------------
    // 전역 싱글톤
    // [학습] static local variable 초기화는 C++11 이후 스레드 안전 보장.
    //        Meyers Singleton 패턴.
    // ------------------------------------------------------------------
    [[nodiscard]] static Tracer& global() noexcept {
        static Tracer instance{ kDefaultCapacity };
        return instance;
    }

private:
    std::size_t               capacity_;
    std::deque<Message>       messages_;
    std::deque<Transition>    transitions_;
    std::deque<Node>          nodes_;
    mutable std::shared_mutex mutex_;
};

// ============================================================================
// 편의 접근자
// ============================================================================
[[nodiscard]] inline Tracer& get_global_tracer() noexcept {
    return Tracer::global();
}

} // namespace atugcc::pattern::viz

// 포맷터 구현 포함 — 이 순서가 중요: Tracer 정의 이후에 포함해야 한다.
#include "atugcc/pattern/detail/terminal_formatter.hpp"
#include "atugcc/pattern/detail/d2_formatter.hpp"
