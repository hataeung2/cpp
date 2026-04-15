/**
 * @file d2_formatter.hpp
 * @brief Tracer::format_d2() 구현 — D2 스니펫 생성
 *
 * ※ visualizer.hpp 가 terminal_formatter.hpp 다음에 이 파일을 include 한다.
 *
 * ======================================================================
 * 학습 포인트
 * ----------------------------------------------------------------------
 * [1] D2 syntax:
 *     관계는 `A -> B: label` 형식으로 표현한다.
 * [2] 식별자 이스케이프:
 *     공백/특수문자가 있으면 "name" 형태로 감싼다.
 * [3] 중복 엣지 제거:
 *     동일 (from, to, action) 반복은 std::set 으로 정리한다.
 * ======================================================================
 */
#pragma once

// NOTE: visualizer.hpp 내부에서만 include 된다.

#include <cctype>
#include <format>
#include <set>
#include <string>
#include <tuple>
#include <vector>

namespace atugcc::pattern::viz::detail {

// ============================================================================
// D2 식별자 이스케이프 유틸리티
// 공백/특수문자가 있으면 "이름" 형태로 감싼다.
// ============================================================================
inline std::string d2_id(std::string_view name) {
    const bool needs_quote = std::ranges::any_of(name, [](char c) {
        return !(std::isalnum(static_cast<unsigned char>(c)) || c == '_');
    });
    if (needs_quote) {
        return std::format("\"{}\"", name);
    }
    return std::string(name);
}

// ============================================================================
// D2Formatter
// ============================================================================
class D2Formatter {
public:
    // -----------------------------------------------------------------------
    // messages: Message 목록 -> D2 directional edges
    // -----------------------------------------------------------------------
    static std::string message_flow(const std::vector<Message>& messages) {
        if (messages.empty()) return {};

        std::string out;
        out += "# sequence/message flow\n";

        std::set<std::tuple<std::string, std::string, std::string>> seen;
        for (const auto& m : messages) {
            auto key = std::make_tuple(m.from, m.to, m.action);
            if (seen.contains(key)) continue;
            seen.insert(key);

            out += std::format("{} -> {}: {}\n",
                d2_id(m.from),
                d2_id(m.to),
                m.action);
        }

        return out;
    }

    // -----------------------------------------------------------------------
    // transitions: Transition 목록 -> D2 state edges
    // -----------------------------------------------------------------------
    static std::string state_flow(const std::vector<Transition>& transitions) {
        if (transitions.empty()) return {};

        std::string out;
        out += "# state transitions\n";

        for (const auto& t : transitions) {
            out += std::format("{} -> {}: {}\n",
                d2_id(t.old_state),
                d2_id(t.new_state),
                t.trigger);
        }

        return out;
    }

    // -----------------------------------------------------------------------
    // nodes: Node 목록 -> D2 structure edges
    // -----------------------------------------------------------------------
    static std::string structure_tree(const std::vector<Node>& nodes) {
        if (nodes.empty()) return {};

        std::string out;
        out += "# class/structure tree\n";

        std::set<std::tuple<std::string, std::string, std::string>> seen;
        for (const auto& n : nodes) {
            auto key = std::make_tuple(n.parent, n.child, n.relation_type);
            if (seen.contains(key)) continue;
            seen.insert(key);

            out += std::format("{} -> {}: {}\n",
                d2_id(n.parent),
                d2_id(n.child),
                n.relation_type);
        }

        return out;
    }
};

} // namespace atugcc::pattern::viz::detail

// ============================================================================
// Tracer::format_d2() 구현 (inline — 헤더 온리)
// ============================================================================
namespace atugcc::pattern::viz {

inline std::string Tracer::format_d2() const {
    std::shared_lock lock(mutex_);

    const auto msgs  = std::vector<Message>{ messages_.begin(), messages_.end() };
    const auto trans = std::vector<Transition>{ transitions_.begin(), transitions_.end() };
    const auto nods  = std::vector<Node>{ nodes_.begin(), nodes_.end() };

    std::string out;
    if (!msgs.empty()) {
        out += detail::D2Formatter::message_flow(msgs);
        out += '\n';
    }
    if (!trans.empty()) {
        out += detail::D2Formatter::state_flow(trans);
        out += '\n';
    }
    if (!nods.empty()) {
        out += detail::D2Formatter::structure_tree(nods);
        out += '\n';
    }
    return out;
}

} // namespace atugcc::pattern::viz
