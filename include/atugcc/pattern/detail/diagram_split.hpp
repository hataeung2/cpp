/**
 * @file diagram_split.hpp
 * @brief Tracer 다이어그램 분할 및 반복 횟수 축약 (백엔드 독립)
 *
 * ==========================================================================
 * 학습 포인트 (C++20/23)
 * --------------------------------------------------------------------------
 * [1] std::string_view — 불필요한 복사 없이 텍스트 파싱 및 라벨 줄바꿈
 * [2] std::format — UTF-8 횟수 접미사("\xC3\x97") 및 조각 제목 생성
 * [3] DFS / 서브트리 탐색 — 재귀 람다와 방문 집합을 통한 순환 방지
 * [4] Designated Initializers — MessageRun / EdgeRun / StructurePart 집계체 초기화
 * ==========================================================================
 */
#pragma once

#include <algorithm>
#include <cstddef>
#include <format>
#include <map>
#include <set>
#include <string>
#include <string_view>
#include <tuple>
#include <utility>
#include <vector>

namespace atugcc::pattern::viz::detail {

struct MessageRun {
    std::size_t index;
    std::size_t count;
};

struct EdgeRun {
    std::size_t index;
    std::size_t count;
};

struct StructurePart {
    std::vector<std::size_t> relations;
    bool overBudget;
};

[[nodiscard]] inline std::size_t clampBudget(std::size_t value) noexcept {
    return value == 0 ? 1 : value;
}

[[nodiscard]] inline std::vector<MessageRun> mergeConsecutiveMessages(
    const std::vector<Message>& messages)
{
    if (messages.empty()) {
        return {};
    }

    std::vector<MessageRun> runs;
    std::size_t start_idx = 0;
    std::size_t count = 1;

    for (std::size_t i = 1; i < messages.size(); ++i) {
        if (messages[i].from == messages[start_idx].from &&
            messages[i].to == messages[start_idx].to &&
            messages[i].action == messages[start_idx].action) {
            ++count;
        } else {
            runs.push_back(MessageRun{ start_idx, count });
            start_idx = i;
            count = 1;
        }
    }
    runs.push_back(MessageRun{ start_idx, count });
    return runs;
}

[[nodiscard]] inline std::vector<std::vector<MessageRun>> splitSequence(
    const std::vector<Message>& messages, const std::vector<MessageRun>& runs,
    std::size_t maxParticipants, std::size_t maxMessages)
{
    if (runs.empty()) {
        return {};
    }

    const std::size_t budget_participants = clampBudget(maxParticipants);
    const std::size_t budget_messages = clampBudget(maxMessages);

    std::vector<std::vector<MessageRun>> parts;
    std::vector<MessageRun> current_part;
    std::set<std::string_view> current_participants;

    for (const auto& run : runs) {
        const auto& msg = messages[run.index];
        std::size_t candidate_participants_count = current_participants.size();
        if (!current_participants.contains(msg.from)) {
            ++candidate_participants_count;
        }
        if (msg.from != msg.to && !current_participants.contains(msg.to)) {
            ++candidate_participants_count;
        }

        const bool exceeds_runs = !current_part.empty() && (current_part.size() >= budget_messages);
        const bool exceeds_participants = !current_part.empty() && (candidate_participants_count > budget_participants);

        if (exceeds_runs || exceeds_participants) {
            parts.push_back(std::move(current_part));
            current_part.clear();
            current_participants.clear();
        }

        current_part.push_back(run);
        current_participants.insert(msg.from);
        current_participants.insert(msg.to);
    }

    if (!current_part.empty()) {
        parts.push_back(std::move(current_part));
    }

    return parts;
}

[[nodiscard]] inline std::vector<EdgeRun> mergeTransitions(
    const std::vector<Transition>& transitions)
{
    std::vector<EdgeRun> result;
    std::map<std::tuple<std::string_view, std::string_view, std::string_view>, std::size_t> seen;

    for (std::size_t i = 0; i < transitions.size(); ++i) {
        const auto& t = transitions[i];
        auto key = std::make_tuple(
            std::string_view{ t.old_state },
            std::string_view{ t.new_state },
            std::string_view{ t.trigger });

        auto it = seen.find(key);
        if (it == seen.end()) {
            seen.emplace(key, result.size());
            result.push_back(EdgeRun{ i, 1 });
        } else {
            result[it->second].count += 1;
        }
    }

    return result;
}

[[nodiscard]] inline std::size_t countStates(
    const std::vector<Transition>& transitions, const std::vector<EdgeRun>& edges)
{
    std::set<std::string_view> states;
    for (const auto& edge : edges) {
        if (edge.index < transitions.size()) {
            const auto& t = transitions[edge.index];
            states.insert(t.old_state);
            states.insert(t.new_state);
        }
    }
    return states.size();
}

[[nodiscard]] inline std::vector<std::size_t> uniqueRelations(
    const std::vector<Node>& nodes)
{
    std::vector<std::size_t> result;
    std::set<std::tuple<std::string_view, std::string_view, std::string_view>> seen;

    for (std::size_t i = 0; i < nodes.size(); ++i) {
        const auto& n = nodes[i];
        auto key = std::make_tuple(
            std::string_view{ n.parent },
            std::string_view{ n.child },
            std::string_view{ n.relation_type });

        if (seen.insert(key).second) {
            result.push_back(i);
        }
    }

    return result;
}

[[nodiscard]] inline std::vector<StructurePart> splitStructure(
    const std::vector<Node>& nodes, const std::vector<std::size_t>& relations, std::size_t maxNodes)
{
    if (relations.empty()) {
        return {};
    }

    const std::size_t budget_nodes = clampBudget(maxNodes);

    std::set<std::string_view> all_distinct_nodes;
    std::set<std::string_view> all_children;
    for (std::size_t idx : relations) {
        if (idx < nodes.size()) {
            all_distinct_nodes.insert(nodes[idx].parent);
            all_distinct_nodes.insert(nodes[idx].child);
            all_children.insert(nodes[idx].child);
        }
    }

    if (all_distinct_nodes.size() <= budget_nodes) {
        return { StructurePart{ relations, false } };
    }

    std::vector<std::string_view> roots;
    std::set<std::string_view> seen_roots;
    for (std::size_t idx : relations) {
        if (idx < nodes.size()) {
            std::string_view p = nodes[idx].parent;
            if (!all_children.contains(p) && seen_roots.insert(p).second) {
                roots.push_back(p);
            }
        }
    }

    if (roots.empty()) {
        return { StructurePart{ relations, all_distinct_nodes.size() > budget_nodes } };
    }

    std::map<std::string_view, std::vector<std::size_t>> outgoing;
    for (std::size_t idx : relations) {
        if (idx < nodes.size()) {
            outgoing[nodes[idx].parent].push_back(idx);
        }
    }

    std::set<std::size_t> assigned;
    std::vector<StructurePart> parts;

    auto collectSubtree = [&](auto& selfDfs, std::string_view curr,
                               std::vector<std::size_t>& sub_relations,
                               std::set<std::string_view>& sub_nodes,
                               std::set<std::string_view>& visited) -> void {
        visited.insert(curr);
        sub_nodes.insert(curr);
        auto it = outgoing.find(curr);
        if (it == outgoing.end()) {
            return;
        }
        for (std::size_t rel_idx : it->second) {
            if (assigned.contains(rel_idx)) {
                continue;
            }
            sub_relations.push_back(rel_idx);
            std::string_view child = nodes[rel_idx].child;
            sub_nodes.insert(child);
            if (!visited.contains(child)) {
                selfDfs(selfDfs, child, sub_relations, sub_nodes, visited);
            }
        }
    };

    auto pack = [&](auto& selfPack, std::string_view u) -> void {
        auto it_out = outgoing.find(u);
        if (it_out == outgoing.end()) {
            return;
        }
        bool has_unassigned = false;
        for (std::size_t rel_idx : it_out->second) {
            if (!assigned.contains(rel_idx)) {
                has_unassigned = true;
                break;
            }
        }
        if (!has_unassigned) {
            return;
        }

        std::vector<std::size_t> sub_relations;
        std::set<std::string_view> sub_nodes;
        std::set<std::string_view> visited;
        collectSubtree(collectSubtree, u, sub_relations, sub_nodes, visited);

        if (sub_nodes.size() <= budget_nodes) {
            for (std::size_t rel_idx : sub_relations) {
                assigned.insert(rel_idx);
            }
            parts.push_back(StructurePart{ std::move(sub_relations), false });
            return;
        }

        std::vector<std::size_t> star_relations;
        std::set<std::string_view> star_nodes;
        star_nodes.insert(u);
        std::vector<std::string_view> child_order;

        for (std::size_t rel_idx : it_out->second) {
            if (!assigned.contains(rel_idx)) {
                star_relations.push_back(rel_idx);
                std::string_view child = nodes[rel_idx].child;
                star_nodes.insert(child);
                child_order.push_back(child);
            }
        }

        if (star_relations.empty()) {
            return;
        }

        const bool over_budget = star_nodes.size() > budget_nodes;

        for (std::size_t rel_idx : star_relations) {
            assigned.insert(rel_idx);
        }

        std::vector<std::string_view> unadded_children;
        std::set<std::string_view> seen_children;

        for (std::string_view child : child_order) {
            if (!seen_children.insert(child).second) {
                continue;
            }

            if (star_nodes.size() > budget_nodes) {
                unadded_children.push_back(child);
                continue;
            }

            std::vector<std::size_t> child_sub_relations;
            std::set<std::string_view> child_sub_nodes;
            std::set<std::string_view> child_visited;
            child_visited.insert(u);
            collectSubtree(collectSubtree, child, child_sub_relations, child_sub_nodes, child_visited);

            std::set<std::string_view> combined_nodes = star_nodes;
            combined_nodes.insert(child_sub_nodes.begin(), child_sub_nodes.end());

            if (combined_nodes.size() <= budget_nodes) {
                star_relations.insert(star_relations.end(), child_sub_relations.begin(), child_sub_relations.end());
                star_nodes = std::move(combined_nodes);
                for (std::size_t rel_idx : child_sub_relations) {
                    assigned.insert(rel_idx);
                }
            } else {
                unadded_children.push_back(child);
            }
        }

        parts.push_back(StructurePart{ std::move(star_relations), over_budget });

        for (std::string_view child : unadded_children) {
            selfPack(selfPack, child);
        }
    };

    for (std::string_view r : roots) {
        pack(pack, r);
    }

    for (std::size_t rel_idx : relations) {
        if (!assigned.contains(rel_idx) && rel_idx < nodes.size()) {
            pack(pack, nodes[rel_idx].parent);
        }
    }

    std::vector<std::size_t> remaining;
    std::set<std::string_view> remaining_nodes;
    for (std::size_t rel_idx : relations) {
        if (!assigned.contains(rel_idx)) {
            remaining.push_back(rel_idx);
            remaining_nodes.insert(nodes[rel_idx].parent);
            remaining_nodes.insert(nodes[rel_idx].child);
            assigned.insert(rel_idx);
        }
    }
    if (!remaining.empty()) {
        const bool over_budget = remaining_nodes.size() > budget_nodes;
        parts.push_back(StructurePart{ std::move(remaining), over_budget });
    }

    return parts;
}

[[nodiscard]] inline std::string wrapLabel(
    std::string_view label, std::size_t width, std::string_view lineBreak)
{
    const std::size_t budget_width = clampBudget(width);
    if (label.size() <= budget_width) {
        return std::string(label);
    }

    std::vector<std::string_view> words;
    std::size_t i = 0;
    while (i < label.size()) {
        while (i < label.size() && label[i] == ' ') {
            ++i;
        }
        if (i >= label.size()) {
            break;
        }
        std::size_t word_start = i;
        while (i < label.size() && label[i] != ' ') {
            ++i;
        }
        words.push_back(label.substr(word_start, i - word_start));
    }

    if (words.empty()) {
        return std::string(label);
    }

    std::string result;
    std::size_t current_line_len = 0;

    for (std::string_view word : words) {
        if (word.size() <= budget_width) {
            if (current_line_len == 0) {
                result += word;
                current_line_len = word.size();
            } else if (current_line_len + 1 + word.size() <= budget_width) {
                result += ' ';
                result += word;
                current_line_len += 1 + word.size();
            } else {
                result += lineBreak;
                result += word;
                current_line_len = word.size();
            }
        } else {
            if (current_line_len > 0) {
                result += lineBreak;
                current_line_len = 0;
            }

            std::size_t offset = 0;
            while (offset + budget_width < word.size()) {
                if (offset > 0) {
                    result += lineBreak;
                }
                result += word.substr(offset, budget_width);
                offset += budget_width;
            }
            if (offset > 0) {
                result += lineBreak;
            }
            std::string_view tail = word.substr(offset);
            result += tail;
            current_line_len = tail.size();
        }
    }

    return result;
}

[[nodiscard]] inline std::string withCount(std::string label, std::size_t count) {
    if (count > 1) {
        return std::format("{} \xC3\x97{}", label, count);
    }
    return label;
}

[[nodiscard]] inline std::string partTitle(
    std::string_view kind, std::size_t k, std::size_t n)
{
    if (n <= 1) {
        return std::string(kind);
    }
    return std::format("{} ({}/{})", kind, k, n);
}

} // namespace atugcc::pattern::viz::detail
