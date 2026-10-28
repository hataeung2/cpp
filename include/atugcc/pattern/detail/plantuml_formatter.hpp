/**
 * @file plantuml_formatter.hpp
 * @brief PlantUML formatter + Tracer diagram API 구현
 */
#pragma once

#include <cctype>
#include <format>
#include <set>
#include <string>
#include <tuple>
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
    static std::string sequenceDiagram(const std::vector<Message>& messages) {
        if (messages.empty()) return {};

        std::string out;
        out += "' sequence/message flow\n";
        out += "@startuml\n";

        std::set<std::tuple<std::string, std::string, std::string>> seen;
        for (const auto& m : messages) {
            auto key = std::make_tuple(m.from, m.to, m.action);
            if (seen.contains(key)) continue;
            seen.insert(key);

            out += std::format("{} -> {} : {}\n",
                plantumlId(m.from),
                plantumlId(m.to),
                m.action);
        }

        out += "@enduml\n";
        return out;
    }

    static std::string stateDiagram(const std::vector<Transition>& transitions) {
        if (transitions.empty()) return {};

        std::string out;
        out += "' state transitions\n";
        out += "@startuml\n";

        for (const auto& t : transitions) {
            out += std::format("{} --> {} : {}\n",
                plantumlId(t.old_state),
                plantumlId(t.new_state),
                t.trigger);
        }

        out += "@enduml\n";
        return out;
    }

    static std::string classTree(const std::vector<Node>& nodes) {
        if (nodes.empty()) return {};

        std::string out;
        out += "' class/structure tree\n";
        out += "@startuml\n";

        std::set<std::tuple<std::string, std::string, std::string>> seen;
        for (const auto& n : nodes) {
            auto key = std::make_tuple(n.parent, n.child, n.relation_type);
            if (seen.contains(key)) continue;
            seen.insert(key);

            out += std::format("{} --> {} : {}\n",
                plantumlId(n.parent),
                plantumlId(n.child),
                n.relation_type);
        }

        out += "@enduml\n";
        return out;
    }
};

} // namespace atugcc::pattern::viz::detail

namespace atugcc::pattern::viz {

inline std::string Tracer::formatPlantuml() const {
    std::shared_lock lock(mutex_);

    const auto msgs  = std::vector<Message>{ messages_.begin(), messages_.end() };
    const auto trans = std::vector<Transition>{ transitions_.begin(), transitions_.end() };
    const auto nods  = std::vector<Node>{ nodes_.begin(), nodes_.end() };

    std::string out;
    if (!msgs.empty()) {
        out += detail::PlantUMLFormatter::sequenceDiagram(msgs);
        out += '\n';
    }
    if (!trans.empty()) {
        out += detail::PlantUMLFormatter::stateDiagram(trans);
        out += '\n';
    }
    if (!nods.empty()) {
        out += detail::PlantUMLFormatter::classTree(nods);
        out += '\n';
    }
    return out;
}

inline std::string Tracer::formatMermaid() const {
    std::shared_lock lock(mutex_);

    const auto msgs  = std::vector<Message>{ messages_.begin(), messages_.end() };
    const auto trans = std::vector<Transition>{ transitions_.begin(), transitions_.end() };
    const auto nods  = std::vector<Node>{ nodes_.begin(), nodes_.end() };

    std::string out;
    if (!msgs.empty()) {
        out += detail::MermaidFormatter::sequenceDiagram(msgs);
        out += '\n';
    }
    if (!trans.empty()) {
        out += detail::MermaidFormatter::stateDiagram(trans);
        out += '\n';
    }
    if (!nods.empty()) {
        out += detail::MermaidFormatter::classTree(nods);
        out += '\n';
    }
    return out;
}

inline std::string Tracer::formatD2() const {
    std::shared_lock lock(mutex_);

    const auto msgs  = std::vector<Message>{ messages_.begin(), messages_.end() };
    const auto trans = std::vector<Transition>{ transitions_.begin(), transitions_.end() };
    const auto nods  = std::vector<Node>{ nodes_.begin(), nodes_.end() };

    std::string out;
    if (!msgs.empty()) {
        out += detail::D2Formatter::messageFlow(msgs);
        out += '\n';
    }
    if (!trans.empty()) {
        out += detail::D2Formatter::stateFlow(trans);
        out += '\n';
    }
    if (!nods.empty()) {
        out += detail::D2Formatter::structureTree(nods);
        out += '\n';
    }
    return out;
}

inline std::string Tracer::formatDiagram(DiagramBackend backend) const {
    switch (backend) {
    case DiagramBackend::Mermaid:
        return formatMermaid();
    case DiagramBackend::D2:
        return formatD2();
    case DiagramBackend::PlantUML:
    default:
        return formatPlantuml();
    }
}

} // namespace atugcc::pattern::viz
