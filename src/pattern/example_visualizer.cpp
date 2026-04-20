/**
 * @file example_visualizer.cpp
 * @brief atugcc::pattern::viz 사용 예제 — 터미널 출력 + PlantUML/Mermaid/D2 스니펫 생성
 *
 * 실행 결과로 확인할 수 있는 것:
 *   1. State 패턴: IDLE → STANDBY → RUN 전이와 각 상태의 schedule() 메시지
 *   2. Observer 패턴: Subject 데이터 변경 → Observer1/2 notify 시퀀스
 *   3. Decorator 구조: 트리 계층 ASCII 시각화
 *   4. 동일 Tracer 로 다이어그램 백엔드(기본 PlantUML, 선택 Mermaid/D2) 생성
 *
 * 빌드 후 실행:
 *   ./bin/atugcc_pattern_example
 *
 * PlantUML 출력은 plantuml 렌더러,
 * Mermaid 출력은 Markdown Preview/mermaid.live,
 * D2 출력은 d2 CLI/d2lang.com/play 에서 렌더 가능.
 */
#include <iostream>
#include <memory>
#include <string>

#include "atugcc/pattern/visualizer.hpp"
#include "atugcc/pattern/detail/terminal_formatter.hpp"
#include "atugcc/pattern/state.hpp"
#include "atugcc/pattern/observer.hpp"

// Windows 에서 ANSI 색상이 깨지는 경우를 대비한 초기화
#include "atugcc/pattern/detail/terminal_formatter.hpp"

int main() {
    // ANSI 활성화 (Windows 구형 콘솔 대응)
    atugcc::pattern::viz::detail::enable_windows_ansi();

    // 각 데모마다 독립 Tracer 를 사용한다 (전역 싱글톤 오염 방지)

    // ========================================================================
    // Demo 1: State Machine
    // ========================================================================
    {
        atugcc::pattern::viz::Tracer tracer;
        atugcc::pattern::state::Machine machine{ tracer };

        std::cout << "╔══════════════════════════════════════════════╗" << '\n';
        std::cout << "║       DEMO 1: State Machine                  ║" << '\n';
        std::cout << "╚══════════════════════════════════════════════╝" << '\n';

        auto try_transition = [&](auto target_state) {
            if (auto r = machine.transition(target_state); !r) {
                std::cout << "  [BLOCKED] "
                          << machine.current_state_name()
                          << " → "
                          << atugcc::pattern::state::state_name(target_state)
                          << " 전이 불가 ("
                          << atugcc::core::to_string(r.error())
                          << ")" << '\n';
            }
        };

        machine.schedule();                                          // IDLE
        try_transition(atugcc::pattern::state::RunState{});         // 불허
        try_transition(atugcc::pattern::state::StandbyState{});     // 허용
        machine.schedule();                                          // STANDBY
        try_transition(atugcc::pattern::state::RunState{});         // 허용
        machine.schedule();                                          // RUN
        try_transition(atugcc::pattern::state::AbortState{});       // 허용
        try_transition(atugcc::pattern::state::IdleState{});        // 허용

        // 터미널 시각화
        std::cout << tracer.format_terminal();

        std::cout << "\n──── PlantUML (default) Snippet ────" << '\n';
        std::cout << tracer.format_diagram();

        // std::cout << "\n──── Mermaid (optional backend) Snippet ────" << '\n';
        // std::cout << tracer.format_diagram(atugcc::pattern::viz::DiagramBackend::Mermaid);

        // std::cout << "\n──── D2 (optional backend) Snippet ────" << '\n';
        // std::cout << tracer.format_diagram(atugcc::pattern::viz::DiagramBackend::D2);
    }

    // ========================================================================
    // Demo 2: Observer Pattern
    // ========================================================================
    {
        atugcc::pattern::viz::Tracer tracer;
        atugcc::pattern::observer::Subject subject{ tracer };

        auto obs1 = std::make_shared<atugcc::pattern::observer::DataObserver1>();
        auto obs2 = std::make_shared<atugcc::pattern::observer::DataObserver2>();

        atugcc::pattern::observer::subscribe(subject, obs1, "Observer1");
        atugcc::pattern::observer::subscribe(subject, obs2, "Observer2");

        std::cout << "\n╔══════════════════════════════════════════════╗" << '\n';
        std::cout << "║       DEMO 2: Observer Pattern               ║" << '\n';
        std::cout << "╚══════════════════════════════════════════════╝" << '\n';

        subject.set_data("temperature", "42.5°C");
        subject.set_data("humidity",    "65%");

        std::cout << "  Observer 표시 결과:" << '\n';
        for (const auto& d : subject.collect_displays()) {
            std::cout << "    - " << d << '\n';
        }

        std::cout << tracer.format_terminal();

        std::cout << "\n──── PlantUML (default) Snippet ────" << '\n';
        std::cout << tracer.format_diagram();

        // std::cout << "\n──── Mermaid (optional backend) Snippet ────" << '\n';
        // std::cout << tracer.format_diagram(atugcc::pattern::viz::DiagramBackend::Mermaid);

        // std::cout << "\n──── D2 (optional backend) Snippet ────" << '\n';
        // std::cout << tracer.format_diagram(atugcc::pattern::viz::DiagramBackend::D2);
    }

    // ========================================================================
    // Demo 3: Decorator Tree (수동 push_node 으로 구조 표현)
    // ========================================================================
    {
        atugcc::pattern::viz::Tracer tracer;

        // Decorator 래핑 관계 기록
        // ((Product wrapped by Deco1) wrapped by Deco1) wrapped by Deco2
        (void)tracer.push_node("Deco2", "Deco1_outer", "wraps");
        (void)tracer.push_node("Deco1_outer", "Deco1_inner", "wraps");
        (void)tracer.push_node("Deco1_inner", "Product", "wraps");

        std::cout << "\n╔══════════════════════════════════════════════╗" << '\n';
        std::cout << "║       DEMO 3: Decorator Tree                 ║" << '\n';
        std::cout << "╚══════════════════════════════════════════════╝" << '\n';

        std::cout << tracer.format_terminal();

        std::cout << "\n──── PlantUML (default) Snippet ────" << '\n';
        std::cout << tracer.format_diagram();

        // std::cout << "\n──── Mermaid (optional backend) Snippet ────" << '\n';
        // std::cout << tracer.format_diagram(atugcc::pattern::viz::DiagramBackend::Mermaid);

        // std::cout << "\n──── D2 (optional backend) Snippet ────" << '\n';
        // std::cout << tracer.format_diagram(atugcc::pattern::viz::DiagramBackend::D2);
    }

    return 0;
}
