/**
 * @file diagram_parts.hpp
 * @brief Tracer 다이어그램 조각 분할(diagramParts) 및 포맷팅(formatDiagram) 구현
 */
#pragma once

#include <algorithm>
#include <cstddef>
#include <format>
#include <set>
#include <shared_mutex>
#include <string>
#include <string_view>
#include <vector>

namespace atugcc::pattern::viz {

inline std::vector<DiagramPart> Tracer::diagramParts(
    DiagramBackend backend,
    const DiagramBudget& budget) const
{
    std::vector<Message> msgs;
    std::vector<Transition> trans;
    std::vector<Node> nods;
    {
        std::shared_lock lock(mutex_);
        msgs.assign(messages_.begin(), messages_.end());
        trans.assign(transitions_.begin(), transitions_.end());
        nods.assign(nodes_.begin(), nodes_.end());
    }

    const std::size_t max_participants = detail::clampBudget(budget.maxParticipants);
    const std::size_t max_messages     = detail::clampBudget(budget.maxMessages);
    const std::size_t max_states       = detail::clampBudget(budget.maxStates);
    const std::size_t max_nodes        = detail::clampBudget(budget.maxNodes);
    const std::size_t label_wrap       = detail::clampBudget(budget.labelWrap);

    auto formatSequence = [&](const std::vector<Message>& m,
                               const std::vector<detail::MessageRun>& r) -> std::string {
        switch (backend) {
        case DiagramBackend::Mermaid:
            return detail::MermaidFormatter::sequencePart(m, r, label_wrap);
        case DiagramBackend::D2:
            return detail::D2Formatter::sequencePart(m, r, label_wrap);
        case DiagramBackend::PlantUML:
        default:
            return detail::PlantUMLFormatter::sequencePart(m, r, label_wrap);
        }
    };

    auto formatState = [&](const std::vector<Transition>& t,
                            const std::vector<detail::EdgeRun>& e,
                            std::string_view note) -> std::string {
        switch (backend) {
        case DiagramBackend::Mermaid:
            return detail::MermaidFormatter::statePart(t, e, label_wrap, note);
        case DiagramBackend::D2:
            return detail::D2Formatter::statePart(t, e, label_wrap, note);
        case DiagramBackend::PlantUML:
        default:
            return detail::PlantUMLFormatter::statePart(t, e, label_wrap, note);
        }
    };

    auto formatStructure = [&](const std::vector<Node>& n,
                                const std::vector<std::size_t>& rels,
                                std::string_view note) -> std::string {
        switch (backend) {
        case DiagramBackend::Mermaid:
            return detail::MermaidFormatter::structurePart(n, rels, label_wrap, note);
        case DiagramBackend::D2:
            return detail::D2Formatter::structurePart(n, rels, label_wrap, note);
        case DiagramBackend::PlantUML:
        default:
            return detail::PlantUMLFormatter::structurePart(n, rels, label_wrap, note);
        }
    };

    std::vector<DiagramPart> parts;

    // Sequence (if messages non-empty)
    if (!msgs.empty()) {
        const auto runs = detail::mergeConsecutiveMessages(msgs);
        const auto chunks = detail::splitSequence(msgs, runs, max_participants, max_messages);
        const std::size_t n = chunks.size();
        for (std::size_t k = 1; k <= n; ++k) {
            parts.push_back(DiagramPart{
                .kind = DiagramKind::Sequence,
                .backend = backend,
                .title = detail::partTitle("Sequence", k, n),
                .source = formatSequence(msgs, chunks[k - 1]),
                .overBudget = false,
            });
        }
    }

    // State (if transitions non-empty)
    if (!trans.empty()) {
        const auto edges = detail::mergeTransitions(trans);
        const std::size_t states = detail::countStates(trans, edges);
        const bool over = states > max_states;
        const std::string note = over
            ? std::format("over budget: states {} > {}", states, max_states)
            : "";
        parts.push_back(DiagramPart{
            .kind = DiagramKind::State,
            .backend = backend,
            .title = detail::partTitle("State", 1, 1),
            .source = formatState(trans, edges, note),
            .overBudget = over,
        });
    }

    // Structure (if nodes non-empty)
    if (!nods.empty()) {
        const auto rel = detail::uniqueRelations(nods);
        const auto struct_parts = detail::splitStructure(nods, rel, max_nodes);
        const std::size_t n = struct_parts.size();
        for (std::size_t k = 1; k <= n; ++k) {
            const auto& part = struct_parts[k - 1];
            std::set<std::string_view> distinct_names;
            for (std::size_t idx : part.relations) {
                if (idx < nods.size()) {
                    distinct_names.insert(nods[idx].parent);
                    distinct_names.insert(nods[idx].child);
                }
            }
            const std::size_t names = distinct_names.size();
            const std::string note = part.overBudget
                ? std::format("over budget: nodes {} > {}", names, max_nodes)
                : "";
            parts.push_back(DiagramPart{
                .kind = DiagramKind::Structure,
                .backend = backend,
                .title = detail::partTitle("Structure", k, n),
                .source = formatStructure(nods, part.relations, note),
                .overBudget = part.overBudget,
            });
        }
    }

    return parts;
}

inline std::string Tracer::formatDiagram(
    DiagramBackend backend,
    const DiagramBudget& budget) const
{
    const auto parts = diagramParts(backend, budget);
    if (parts.empty()) {
        return {};
    }

    auto countForKind = [&](DiagramKind kind) -> std::size_t {
        return std::ranges::count_if(parts, [kind](const DiagramPart& p) {
            return p.kind == kind;
        });
    };

    std::string_view prefix;
    switch (backend) {
    case DiagramBackend::Mermaid:
        prefix = "%% ";
        break;
    case DiagramBackend::D2:
        prefix = "# ";
        break;
    case DiagramBackend::PlantUML:
    default:
        prefix = "' ";
        break;
    }

    std::string out;
    for (const auto& part : parts) {
        if (countForKind(part.kind) > 1) {
            out += prefix;
            out += part.title;
            out += '\n';
        }
        out += part.source;
        out += '\n';
    }
    return out;
}

inline std::string Tracer::formatPlantuml() const {
    return formatDiagram(DiagramBackend::PlantUML);
}

inline std::string Tracer::formatMermaid() const {
    return formatDiagram(DiagramBackend::Mermaid);
}

inline std::string Tracer::formatD2() const {
    return formatDiagram(DiagramBackend::D2);
}

} // namespace atugcc::pattern::viz
