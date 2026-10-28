/**
 * @file mermaid_formatter.hpp
 * @brief MermaidFormatter 구현 — Mermaid 스니펫 생성
 */
#pragma once

#include <cctype>
#include <cstddef>
#include <format>
#include <string>
#include <string_view>
#include <vector>

namespace atugcc::pattern::viz::detail {

inline std::string mermaidId(std::string_view name) {
    const bool needs_quote = std::ranges::any_of(name, [](char c) {
        return !(std::isalnum(static_cast<unsigned char>(c)) || c == '_');
    });
    if (needs_quote) {
        return std::format("\"{}\"", name);
    }
    return std::string(name);
}

inline std::string escapeMermaidLabel(std::string_view label) {
    std::string result;
    result.reserve(label.size());
    for (char c : label) {
        if (c == ';') {
            result += "#59;";
        } else {
            result += c;
        }
    }
    return result;
}

class MermaidFormatter {
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
        out += "```mermaid\n";
        out += "sequenceDiagram\n";

        for (const auto& run : runs) {
            const auto& m = messages[run.index];
            const std::string escaped = escapeMermaidLabel(m.action);
            const std::string label = withCount(wrapLabel(escaped, labelWrap, "<br/>"), run.count);
            out += std::format("    {}->>{}:{}\n",
                mermaidId(m.from),
                mermaidId(m.to),
                label);
        }

        out += "```\n";
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
        out += "```mermaid\n";
        out += "stateDiagram-v2\n";

        if (!overBudgetNote.empty()) {
            out += std::format("%% {}\n", overBudgetNote);
        }

        for (const auto& edge : edges) {
            const auto& t = transitions[edge.index];
            const std::string escaped = escapeMermaidLabel(t.trigger);
            const std::string label = withCount(wrapLabel(escaped, labelWrap, "<br/>"), edge.count);
            out += std::format("    {} --> {} : {}\n",
                mermaidId(t.old_state),
                mermaidId(t.new_state),
                label);
        }

        out += "```\n";
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
        out += "```mermaid\n";
        out += "classDiagram\n";

        if (!overBudgetNote.empty()) {
            out += std::format("%% {}\n", overBudgetNote);
        }

        for (std::size_t idx : relations) {
            const auto& n = nodes[idx];
            const std::string escaped = escapeMermaidLabel(n.relation_type);
            const std::string label = wrapLabel(escaped, labelWrap, "<br/>");
            out += std::format("    {} --> {} : {}\n",
                mermaidId(n.parent),
                mermaidId(n.child),
                label);
        }

        out += "```\n";
        return out;
    }
};

} // namespace atugcc::pattern::viz::detail
