/**
 * @file mermaid_formatter.hpp
 * @brief MermaidFormatter 구현 — Mermaid 스니펫 생성
 */
#pragma once

#include <algorithm>
#include <cctype>
#include <cstddef>
#include <format>
#include <optional>
#include <string>
#include <string_view>
#include <vector>

namespace atugcc::pattern::viz::detail {

[[nodiscard]] inline bool mermaidNeedsQuote(std::string_view name) {
    return std::ranges::any_of(name, [](char c) {
        return !(std::isalnum(static_cast<unsigned char>(c)) || c == '_');
    });
}

inline std::string mermaidId(std::string_view name) {
    if (mermaidNeedsQuote(name)) {
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
        std::size_t labelWrap,
        std::optional<std::size_t> mark = std::nullopt)
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
            const bool is_marked = mark.has_value() && run.index <= *mark && *mark < run.index + run.count;
            if (is_marked) {
                out += "    rect rgba(255, 235, 59, 0.35)\n";
                out += std::format("        {}->>{}:{}\n",
                    mermaidId(m.from),
                    mermaidId(m.to),
                    label);
                out += "    end\n";
            } else {
                out += std::format("    {}->>{}:{}\n",
                    mermaidId(m.from),
                    mermaidId(m.to),
                    label);
            }
        }

        out += "```\n";
        return out;
    }

    static std::string statePart(
        const std::vector<Transition>& transitions,
        const std::vector<EdgeRun>& edges,
        std::size_t labelWrap,
        std::string_view overBudgetNote,
        std::optional<std::size_t> mark = std::nullopt)
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

        if (mark.has_value() && *mark < transitions.size()) {
            const auto& new_state = transitions[*mark].new_state;
            if (!mermaidNeedsQuote(new_state)) {
                out += "    classDef current fill:#fff3b0,stroke:#e0a800,color:#000\n";
                out += std::format("    class {} current\n", new_state);
            }
        }

        out += "```\n";
        return out;
    }

    static std::string structurePart(
        const std::vector<Node>& nodes,
        const std::vector<std::size_t>& relations,
        std::size_t labelWrap,
        std::string_view overBudgetNote,
        std::optional<std::size_t> mark = std::nullopt)
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

        if (mark.has_value() && *mark < nodes.size()) {
            const auto& target = nodes[*mark];
            const auto it = std::ranges::find_if(relations, [&](std::size_t idx) {
                if (idx >= nodes.size()) {
                    return false;
                }
                const auto& n = nodes[idx];
                return n.parent == target.parent &&
                       n.child == target.child &&
                       n.relation_type == target.relation_type;
            });
            // Mermaid 12 classDiagram has no linkStyle (it reads the line as a class): the child of the
            // last relation is styled instead; a quoted id cannot be styled
            if (it != relations.end() && !mermaidNeedsQuote(target.child)) {
                out += std::format("    style {} fill:#fff3b0,stroke:#e0a800,color:#000\n", target.child);
            }
        }

        out += "```\n";
        return out;
    }
};

} // namespace atugcc::pattern::viz::detail
