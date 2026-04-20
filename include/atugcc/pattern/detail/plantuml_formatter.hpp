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

inline std::string plantuml_id(std::string_view name) {
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
    static std::string sequence_diagram(const std::vector<Message>& messages) {
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
                plantuml_id(m.from),
                plantuml_id(m.to),
                m.action);
        }

        out += "@enduml\n";
        return out;
    }

    static std::string state_diagram(const std::vector<Transition>& transitions) {
        if (transitions.empty()) return {};

        std::string out;
        out += "' state transitions\n";
        out += "@startuml\n";

        for (const auto& t : transitions) {
            out += std::format("{} --> {} : {}\n",
                plantuml_id(t.old_state),
                plantuml_id(t.new_state),
                t.trigger);
        }

        out += "@enduml\n";
        return out;
    }

    static std::string class_tree(const std::vector<Node>& nodes) {
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
                plantuml_id(n.parent),
                plantuml_id(n.child),
                n.relation_type);
        }

        out += "@enduml\n";
        return out;
    }
};

} // namespace atugcc::pattern::viz::detail

namespace atugcc::pattern::viz {

inline std::string Tracer::format_plantuml() const {
    std::shared_lock lock(mutex_);

    const auto msgs  = std::vector<Message>{ messages_.begin(), messages_.end() };
    const auto trans = std::vector<Transition>{ transitions_.begin(), transitions_.end() };
    const auto nods  = std::vector<Node>{ nodes_.begin(), nodes_.end() };

    std::string out;
    if (!msgs.empty()) {
        out += detail::PlantUMLFormatter::sequence_diagram(msgs);
        out += '\n';
    }
    if (!trans.empty()) {
        out += detail::PlantUMLFormatter::state_diagram(trans);
        out += '\n';
    }
    if (!nods.empty()) {
        out += detail::PlantUMLFormatter::class_tree(nods);
        out += '\n';
    }
    return out;
}

inline std::string Tracer::format_mermaid() const {
    std::shared_lock lock(mutex_);

    const auto msgs  = std::vector<Message>{ messages_.begin(), messages_.end() };
    const auto trans = std::vector<Transition>{ transitions_.begin(), transitions_.end() };
    const auto nods  = std::vector<Node>{ nodes_.begin(), nodes_.end() };

    std::string out;
    if (!msgs.empty()) {
        out += detail::MermaidFormatter::sequence_diagram(msgs);
        out += '\n';
    }
    if (!trans.empty()) {
        out += detail::MermaidFormatter::state_diagram(trans);
        out += '\n';
    }
    if (!nods.empty()) {
        out += detail::MermaidFormatter::class_tree(nods);
        out += '\n';
    }
    return out;
}

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

inline std::string Tracer::format_diagram(DiagramBackend backend) const {
    switch (backend) {
    case DiagramBackend::Mermaid:
        return format_mermaid();
    case DiagramBackend::D2:
        return format_d2();
    case DiagramBackend::PlantUML:
    default:
        return format_plantuml();
    }
}

} // namespace atugcc::pattern::viz
