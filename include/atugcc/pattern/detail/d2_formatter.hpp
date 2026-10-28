/**
 * @file d2_formatter.hpp
 * @brief D2Formatter 구현 — D2 스니펫 생성
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
 * [3] 반복 처리 (020-04):
 *     연속 반복 메시지와 같은 상태 간선은 `×N` 으로 합치고(diagram_split.hpp),
 *     구조 관계는 중복을 하나로 그린다. 순서는 바뀌지 않는다.
 * ======================================================================
 */
#pragma once

// NOTE: visualizer.hpp 내부에서만 include 된다.

#include <cctype>
#include <cstddef>
#include <format>
#include <string>
#include <string_view>
#include <vector>

namespace atugcc::pattern::viz::detail {

// ============================================================================
// D2 식별자 이스케이프 유틸리티
// 공백/특수문자가 있으면 "이름" 형태로 감싼다.
// ============================================================================
inline std::string d2Id(std::string_view name) {
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
    static std::string sequencePart(
        const std::vector<Message>& messages,
        const std::vector<MessageRun>& runs,
        std::size_t labelWrap)
    {
        if (runs.empty()) {
            return {};
        }

        std::string out;
        out += "# sequence/message flow\n";

        for (const auto& run : runs) {
            const auto& m = messages[run.index];
            const std::string label = withCount(wrapLabel(m.action, labelWrap, "\\n"), run.count);
            out += std::format("{} -> {}: {}\n",
                d2Id(m.from),
                d2Id(m.to),
                label);
        }

        return out;
    }

    static std::string statePart(
        const std::vector<Transition>& transitions,
        const std::vector<EdgeRun>& edges,
        std::size_t labelWrap,
        std::string_view overBudgetNote)
    {
        if (edges.empty()) {
            return {};
        }

        std::string out;
        out += "# state transitions\n";

        if (!overBudgetNote.empty()) {
            out += std::format("# {}\n", overBudgetNote);
        }

        for (const auto& edge : edges) {
            const auto& t = transitions[edge.index];
            const std::string label = withCount(wrapLabel(t.trigger, labelWrap, "\\n"), edge.count);
            out += std::format("{} -> {}: {}\n",
                d2Id(t.old_state),
                d2Id(t.new_state),
                label);
        }

        return out;
    }

    static std::string structurePart(
        const std::vector<Node>& nodes,
        const std::vector<std::size_t>& relations,
        std::size_t labelWrap,
        std::string_view overBudgetNote)
    {
        if (relations.empty()) {
            return {};
        }

        std::string out;
        out += "# class/structure tree\n";

        if (!overBudgetNote.empty()) {
            out += std::format("# {}\n", overBudgetNote);
        }

        for (std::size_t idx : relations) {
            const auto& n = nodes[idx];
            const std::string label = wrapLabel(n.relation_type, labelWrap, "\\n");
            out += std::format("{} -> {}: {}\n",
                d2Id(n.parent),
                d2Id(n.child),
                label);
        }

        return out;
    }
};

} // namespace atugcc::pattern::viz::detail

// Tracer 멤버 함수 구현은 plantuml_formatter.hpp 에서 제공한다.
