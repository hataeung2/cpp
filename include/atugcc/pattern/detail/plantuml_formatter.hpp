/**
 * @file plantuml_formatter.hpp
 * @brief PlantUMLFormatter 구현 — PlantUML 스니펫 생성
 */
#pragma once

#include <cctype>
#include <cstddef>
#include <format>
#include <string>
#include <string_view>
#include <vector>

namespace atugcc::pattern::viz::detail {

inline std::string plantumlId(std::string_view name) {
    const bool needs_quote = std::ranges::any_of(name, [](char c) {
        return !(std::isalnum(static_cast<unsigned char>(c)) || c == '_');
    });
    if (needs_quote) {
        return std::format("\"{}\"", name);
    }
    return std::string(name);
}

class PlantUMLFormatter {
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
        out += "' sequence/message flow\n";
        out += "@startuml\n";

        for (const auto& run : runs) {
            const auto& m = messages[run.index];
            const std::string label = withCount(wrapLabel(m.action, labelWrap, "\\n"), run.count);
            out += std::format("{} -> {} : {}\n",
                plantumlId(m.from),
                plantumlId(m.to),
                label);
        }

        out += "@enduml\n";
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
        out += "' state transitions\n";
        out += "@startuml\n";

        if (!overBudgetNote.empty()) {
            out += std::format("' {}\n", overBudgetNote);
        }

        for (const auto& edge : edges) {
            const auto& t = transitions[edge.index];
            const std::string label = withCount(wrapLabel(t.trigger, labelWrap, "\\n"), edge.count);
            out += std::format("{} --> {} : {}\n",
                plantumlId(t.old_state),
                plantumlId(t.new_state),
                label);
        }

        out += "@enduml\n";
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
        out += "' class/structure tree\n";
        out += "@startuml\n";

        if (!overBudgetNote.empty()) {
            out += std::format("' {}\n", overBudgetNote);
        }

        for (std::size_t idx : relations) {
            const auto& n = nodes[idx];
            const std::string label = wrapLabel(n.relation_type, labelWrap, "\\n");
            out += std::format("{} --> {} : {}\n",
                plantumlId(n.parent),
                plantumlId(n.child),
                label);
        }

        out += "@enduml\n";
        return out;
    }
};

} // namespace atugcc::pattern::viz::detail
