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

#include "atugcc/pattern/observer.hpp"
#include "atugcc/pattern/state.hpp"
#include "atugcc/pattern/visualizer.hpp"

int main() {
    // ANSI 활성화 (Windows 구형 콘솔 대응)
    atugcc::pattern::viz::detail::enable_windows_ansi();

    auto desktop_console = atugcc::pattern::viz::DesktopConsoleTraceSink::create(
        "atugcc tracer",
        true,
        atugcc::pattern::viz::DesktopConsoleWindowMode::KeepOpen);

    std::shared_ptr<atugcc::pattern::viz::TraceOutputSink> dedicated_console =
        std::static_pointer_cast<atugcc::pattern::viz::TraceOutputSink>(desktop_console);
    if (!dedicated_console) {
        dedicated_console = std::make_shared<atugcc::pattern::viz::ConsoleTraceSink>(std::clog, true);
    }

    std::string sink_source = "std::clog";
    if (desktop_console) {
        sink_source = desktop_console->isWindowAttached() ? "desktop window" : "file-only fallback";
        std::cout << "[tracer] dedicated console sink initialized; log path: "
                  << desktop_console->logPath() << '\n';
        if (!desktop_console->isWindowAttached()) {
            std::cout << "[tracer] window launch failed; output will be written to the log file." << '\n';
        }
    }

    // 각 데모마다 독립 Tracer 를 사용한다 (전역 싱글톤 오염 방지)

    // ========================================================================
    // Demo 1: State Machine
    // ========================================================================
    {
        atugcc::pattern::viz::Tracer tracer;
        atugcc::pattern::state::Machine machine{ tracer };

        tracer.setOutputSink(dedicated_console);
        tracer.setLiveTerminalOutputEnabled(true);
        if (dedicated_console) {
            dedicated_console->setEnabled(true);
        }

        std::cout << "==================================================" << '\n';
        std::cout << "DEMO 1: State Machine" << '\n';
        std::cout << "==================================================" << '\n';
        std::cout << "  dedicated console sink: ON (" << sink_source << ")" << '\n';

        auto try_transition = [&](auto target_state) {
            if (auto r = machine.transition(target_state); !r) {
                std::cout << "  [BLOCKED] "
                          << machine.current_state_name()
                          << " -> "
                          << atugcc::pattern::state::state_name(target_state)
                          << " (transition blocked: "
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

        std::cout << "\n---- PlantUML (default) Snippet ----" << '\n';
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

        tracer.setOutputSink(dedicated_console);
        tracer.setLiveTerminalOutputEnabled(true);
        if (dedicated_console) {
            dedicated_console->setEnabled(false);
        }

        auto obs1 = std::make_shared<atugcc::pattern::observer::DataObserver1>();
        auto obs2 = std::make_shared<atugcc::pattern::observer::DataObserver2>();

        atugcc::pattern::observer::subscribe(subject, obs1, "Observer1");
        atugcc::pattern::observer::subscribe(subject, obs2, "Observer2");

        std::cout << "\n==================================================" << '\n';
        std::cout << "DEMO 2: Observer Pattern" << '\n';
        std::cout << "==================================================" << '\n';
        std::cout << "  dedicated console sink: OFF" << '\n';

        subject.set_data("temperature", "42.5°C");
        subject.set_data("humidity",    "65%");

        std::cout << "  Observer results:" << '\n';
        for (const auto& d : subject.collect_displays()) {
            std::cout << "    - " << d << '\n';
        }

        std::cout << tracer.format_terminal();

        std::cout << "\n---- PlantUML (default) Snippet ----" << '\n';
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

        tracer.setOutputSink(dedicated_console);
        tracer.setLiveTerminalOutputEnabled(true);
        if (dedicated_console) {
            dedicated_console->setEnabled(true);
        }

        // Decorator 래핑 관계 기록
        // ((Product wrapped by Deco1) wrapped by Deco1) wrapped by Deco2
        (void)tracer.push_node("Deco2", "Deco1_outer", "wraps");
        (void)tracer.push_node("Deco1_outer", "Deco1_inner", "wraps");
        (void)tracer.push_node("Deco1_inner", "Product", "wraps");

        std::cout << "\n==================================================" << '\n';
        std::cout << "DEMO 3: Decorator Tree" << '\n';
        std::cout << "==================================================" << '\n';
        std::cout << "  dedicated console sink: ON (" << sink_source << ")" << '\n';

        std::cout << tracer.format_terminal();

        std::cout << "\n---- PlantUML (default) Snippet ----" << '\n';
        std::cout << tracer.format_diagram();

        // std::cout << "\n──── Mermaid (optional backend) Snippet ────" << '\n';
        // std::cout << tracer.format_diagram(atugcc::pattern::viz::DiagramBackend::Mermaid);

        // std::cout << "\n──── D2 (optional backend) Snippet ────" << '\n';
        // std::cout << tracer.format_diagram(atugcc::pattern::viz::DiagramBackend::D2);
    }

    return 0;
}
