/**
 * @file terminal_formatter.hpp
 * @brief Tracer::format_terminal() 구현 — ANSI 색상 + ASCII 트리/흐름 출력
 *
 * ※ visualizer.hpp 가 이 파일을 마지막에 include 하므로
 *   Tracer 클래스 정의가 이미 완성된 상태에서 파싱된다.
 *   직접 include 하지 말 것.
 *
 * ==========================================================================
 * 학습 포인트
 * --------------------------------------------------------------------------
 * [1] ANSI Escape Code: "\033[CODEm" 형식. Windows Terminal 은 기본 지원.
 *     구형 Windows Console(cmd.exe) 은 ENABLE_VIRTUAL_TERMINAL_PROCESSING
 *     플래그를 SetConsoleMode() 로 활성화해야 한다.
 * [2] constexpr 문자열 테이블: 역할(Role)→색상 매핑을 컴파일 타임 배열로.
 * [3] std::format 기반 들여쓰기: std::string(depth*2, ' ') 패턴.
 * [4] 중복 node 관계 제거: std::ranges::sort + std::ranges::unique 사용.
 * ==========================================================================
 */
#pragma once

// NOTE: 이 파일은 visualizer.hpp 내부에서만 include 된다.
// atugcc::pattern::viz::Tracer 가 이미 정의되어 있음을 가정한다.

#include <algorithm>
#include <format>
#include <map>
#include <ranges>
#include <string>
#include <vector>

#ifdef _WIN32
#  ifndef WIN32_LEAN_AND_MEAN
#    define WIN32_LEAN_AND_MEAN
#  endif
#  include <windows.h>
#endif

namespace atugcc::pattern::viz::detail {

// ============================================================================
// ANSI 색상 코드
// [학습] constexpr string_view 배열: 런타임 오버헤드 없이 색상 팔레트 관리.
// ============================================================================
namespace ansi {
    inline constexpr std::string_view Reset       = "\033[0m";
    inline constexpr std::string_view Bold        = "\033[1m";
    inline constexpr std::string_view Red         = "\033[31m";
    inline constexpr std::string_view Green       = "\033[32m";
    inline constexpr std::string_view Yellow      = "\033[33m";
    inline constexpr std::string_view Blue        = "\033[34m";
    inline constexpr std::string_view Magenta     = "\033[35m";
    inline constexpr std::string_view Cyan        = "\033[36m";
    inline constexpr std::string_view White       = "\033[37m";
    inline constexpr std::string_view BoldCyan    = "\033[1;36m";
    inline constexpr std::string_view BoldYellow  = "\033[1;33m";
    inline constexpr std::string_view BoldGreen   = "\033[1;32m";
    inline constexpr std::string_view BoldMagenta = "\033[1;35m";
} // namespace ansi

// ============================================================================
// Windows 콘솔 ANSI 활성화 유틸리티
// [학습] Windows 에서 ANSI 가 동작하지 않을 때 이 함수를 한 번 호출한다.
//        Windows Terminal 은 자동 지원이지만 구형 cmd.exe 는 아니다.
// ============================================================================
inline void enable_windows_ansi() noexcept {
#ifdef _WIN32
    // Ensure console uses UTF-8 so UTF-8 encoded output displays correctly.
    // This sets the process console code page to UTF-8 (CP_UTF8).
    SetConsoleOutputCP(CP_UTF8);
    SetConsoleCP(CP_UTF8);

    HANDLE hOut = GetStdHandle(STD_OUTPUT_HANDLE);
    if (hOut == INVALID_HANDLE_VALUE) return;
    DWORD dwMode = 0;
    if (!GetConsoleMode(hOut, &dwMode)) return;

    // Enable ANSI escape code processing (color support)
    SetConsoleMode(hOut, dwMode | ENABLE_VIRTUAL_TERMINAL_PROCESSING);
#endif
}

// ============================================================================
// TerminalFormatter
// ============================================================================
class TerminalFormatter {
public:
    // ----------------------------------------------------------------------
    // 섹션 헤더 유틸리티
    // ----------------------------------------------------------------------
    static std::string section_header(std::string_view title) {
        return std::format("\n{}{}══ {} ══{}\n",
            ansi::Bold, ansi::BoldCyan, title, ansi::Reset);
    }

    // -----------------------------------------------------------------------
    // format_messages: 시퀀스 메시지 목록을 번호 붙인 화살표로 출력
    //
    // 출력 예:
    //   ── Sequence Messages ──
    //    [1] Subject  ──▶  Observer1  ::  notify()
    //    [2] Observer1 ──▶ Observer1  ::  pull()
    // -----------------------------------------------------------------------
    static std::string format_messages(const std::vector<Message>& messages) {
        if (messages.empty()) return {};

        std::string out = section_header("Sequence Messages");
        int idx = 1;
        for (const auto& m : messages) {
            out += std::format("  {}[{}]{} {}{}{} {}──▶{} {}{}{} {}::{} {}\n",
                ansi::Yellow, idx++, ansi::Reset,
                ansi::BoldGreen,  m.from,   ansi::Reset,
                ansi::Cyan,                  ansi::Reset,
                ansi::BoldMagenta, m.to,    ansi::Reset,
                ansi::White,                 ansi::Reset,
                m.action);
        }
        return out;
    }

    // -----------------------------------------------------------------------
    // format_transitions: 상태 전이를 흐름도로 출력
    //
    // 출력 예:
    //   ── State Transitions ──
    //    [IDLE] ──( schedule )──▶ [STANDBY]
    // -----------------------------------------------------------------------
    static std::string format_transitions(const std::vector<Transition>& transitions) {
        if (transitions.empty()) return {};

        std::string out = section_header("State Transitions");
        for (const auto& t : transitions) {
            out += std::format("  {}[{}]{} ──{}( {} ){}──▶ {}[{}]{}\n",
                ansi::BoldYellow, t.old_state, ansi::Reset,
                ansi::Cyan,       t.trigger,   ansi::Reset,
                ansi::BoldGreen,  t.new_state, ansi::Reset);
        }
        return out;
    }

    // -----------------------------------------------------------------------
    // format_tree: 객체 구조 계층을 ASCII 트리로 출력
    //
    // [학습] std::map 으로 parent→children 인접 리스트 구성 후 재귀 DFS.
    //        std::ranges::sort / unique 로 중복 제거.
    //
    // 출력 예:
    //   ── Object Tree ──
    //   Deco2
    //   ├─ wraps ─▶ Deco1
    //   │           ├─ wraps ─▶ Product
    // -----------------------------------------------------------------------
    static std::string format_tree(const std::vector<Node>& nodes) {
        if (nodes.empty()) return {};

        // parent → [ {child, relation} ] 인접 리스트
        std::map<std::string, std::vector<std::pair<std::string,std::string>>> adj;
        // 루트 후보 (부모가 없는 노드)
        std::vector<std::string> all_parents, all_children;

        for (const auto& n : nodes) {
            adj[n.parent].emplace_back(n.child, n.relation_type);
            all_parents.push_back(n.parent);
            all_children.push_back(n.child);
        }

        // [학습] std::ranges::sort + std::ranges::unique (C++20)
        std::ranges::sort(all_children);
        all_children.erase(
            std::ranges::unique(all_children).begin(),
            all_children.end());

        std::ranges::sort(all_parents);
        all_parents.erase(
            std::ranges::unique(all_parents).begin(),
            all_parents.end());

        // child 에 없는 parent 가 루트
        std::vector<std::string> roots;
        for (const auto& p : all_parents) {
            if (!std::ranges::binary_search(all_children, p)) {
                roots.push_back(p);
            }
        }
        if (roots.empty() && !all_parents.empty()) {
            roots.push_back(all_parents.front()); // 순환 방어
        }

        std::string out = section_header("Object Tree");
        for (const auto& root : roots) {
            out += render_node(adj, root, "", true);
        }
        return out;
    }

private:
    // 재귀 렌더러
    static std::string render_node(
        const std::map<std::string,
            std::vector<std::pair<std::string,std::string>>>& adj,
        const std::string& node,
        const std::string& prefix,
        bool is_root)
    {
        std::string out;
        if (is_root) {
            out += std::format("  {}{}{}\n", ansi::BoldCyan, node, ansi::Reset);
        }

        auto it = adj.find(node);
        if (it == adj.end()) return out;

        const auto& children = it->second;
        for (std::size_t i = 0; i < children.size(); ++i) {
            const bool last = (i == children.size() - 1);
            const auto& [child, rel] = children[i];

            const std::string branch = last ? "└─" : "├─";
            const std::string cont   = last ? "  " : "│ ";

            out += std::format("  {}{}{}{} {}─({})─▶{} {}{}{}\n",
                prefix,
                ansi::Yellow, branch, ansi::Reset,
                ansi::Cyan, rel,      ansi::Reset,
                ansi::BoldMagenta, child, ansi::Reset);

            out += render_node(adj, child, prefix + cont, false);
        }
        return out;
    }
};

inline std::string LiveTerminalFormatter::formatMessage(const Message& message) {
    return std::format("{}[msg]{} {}{}{} {}──▶{} {}{}{} {}::{} {}\n",
        ansi::Yellow, ansi::Reset,
        ansi::BoldGreen, message.from, ansi::Reset,
        ansi::Cyan, ansi::Reset,
        ansi::BoldMagenta, message.to, ansi::Reset,
        ansi::White, ansi::Reset,
        message.action);
}

inline std::string LiveTerminalFormatter::formatTransition(const Transition& transition) {
    return std::format("{}[state]{} {}[{}]{} ──{}( {} ){}──▶ {}[{}]{}\n",
        ansi::BoldCyan, ansi::Reset,
        ansi::BoldYellow, transition.old_state, ansi::Reset,
        ansi::Cyan, transition.trigger, ansi::Reset,
        ansi::BoldGreen, transition.new_state, ansi::Reset);
}

inline std::string LiveTerminalFormatter::formatNode(const Node& node) {
    return std::format("{}[tree]{} {}{}{} {}─({})─▶{} {}{}{}\n",
        ansi::BoldCyan, ansi::Reset,
        ansi::BoldGreen, node.parent, ansi::Reset,
        ansi::Cyan, node.relation_type, ansi::Reset,
        ansi::BoldMagenta, node.child, ansi::Reset);
}

} // namespace atugcc::pattern::viz::detail

// ============================================================================
// Tracer::format_terminal() 구현 (inline — 헤더 온리)
// ============================================================================
namespace atugcc::pattern::viz {

inline std::string Tracer::format_terminal() const {
    std::shared_lock lock(mutex_);

    const auto msgs  = std::vector<Message>{    messages_.begin(),    messages_.end() };
    const auto trans = std::vector<Transition>{ transitions_.begin(), transitions_.end() };
    const auto nods  = std::vector<Node>{       nodes_.begin(),       nodes_.end() };

    std::string out;
    out += detail::TerminalFormatter::format_messages(msgs);
    out += detail::TerminalFormatter::format_transitions(trans);
    out += detail::TerminalFormatter::format_tree(nods);
    return out;
}

} // namespace atugcc::pattern::viz
