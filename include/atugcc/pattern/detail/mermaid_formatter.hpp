/**
 * @file mermaid_formatter.hpp
 * @brief MermaidFormatter 구현 — Mermaid 스니펫 생성
 */
#pragma once

#include <cctype>
#include <format>
#include <set>
#include <string>
#include <tuple>
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

class MermaidFormatter {
public:
    static std::string sequenceDiagram(const std::vector<Message>& messages) {
        if (messages.empty()) return {};

        std::string out;
        out += "```mermaid\n";
        out += "sequenceDiagram\n";

        std::set<std::tuple<std::string, std::string, std::string>> seen;
        for (const auto& m : messages) {
            auto key = std::make_tuple(m.from, m.to, m.action);
            if (seen.contains(key)) continue;
            seen.insert(key);

            out += std::format("    {}->>{}:{}\n",
                mermaidId(m.from),
                mermaidId(m.to),
                m.action);
        }

        out += "```\n";
        return out;
    }

    static std::string stateDiagram(const std::vector<Transition>& transitions) {
        if (transitions.empty()) return {};

        std::string out;
        out += "```mermaid\n";
        out += "stateDiagram-v2\n";

        for (const auto& t : transitions) {
            out += std::format("    {} --> {} : {}\n",
                mermaidId(t.old_state),
                mermaidId(t.new_state),
                t.trigger);
        }

        out += "```\n";
        return out;
    }

    static std::string classTree(const std::vector<Node>& nodes) {
        if (nodes.empty()) return {};

        std::string out;
        out += "```mermaid\n";
        out += "classDiagram\n";

        std::set<std::tuple<std::string, std::string, std::string>> seen;
        for (const auto& n : nodes) {
            auto key = std::make_tuple(n.parent, n.child, n.relation_type);
            if (seen.contains(key)) continue;
            seen.insert(key);

            out += std::format("    {} --> {} : {}\n",
                mermaidId(n.parent),
                mermaidId(n.child),
                n.relation_type);
        }

        out += "```\n";
        return out;
    }
};

} // namespace atugcc::pattern::viz::detail
