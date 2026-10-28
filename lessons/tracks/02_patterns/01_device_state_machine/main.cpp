#include <chrono>
#include <iostream>
#include <thread>

#include "atugcc/core/logger.hpp"
#include "atugcc/pattern/state.hpp"
#include "atugcc/pattern/visualizer.hpp"
#include "units/jthread_worker/jthread_worker.hpp"

int main() {
    atugcc::core::Logger logger{
        atugcc::core::Logger::Config{
            .liveOutput = &std::cout,
            .enableCrashDump = false
        }
    };

    logger.log(atugcc::core::Level::Info, "=== device_state_machine 레슨 시작 ===");

    // 자체 Tracer 객체를 생성하여 Machine에 주입
    atugcc::pattern::viz::Tracer tracer;
    atugcc::pattern::state::Machine machine{ tracer };

    using atugcc::lessons::jthread_worker::PeriodicWorker;
    namespace state = atugcc::pattern::state;
    namespace viz = atugcc::pattern::viz;

    // [학습 / 스레드 안전성]
    // Machine과 Tracer는 워커 스레드가 시작된 후 정지(requestStop) 및 조인(join)되어
    // 완전히 종료될 때까지 "오직 워커 스레드에 의해서만" 사용됩니다.
    // 워커 스레드가 완전히 종료된 이후에만 main 스레드가 안전하게 Machine과 Tracer를 읽습니다.
    {
        PeriodicWorker worker{
            "DeviceWorker",
            std::chrono::milliseconds(25),
            [&machine, &logger](std::size_t tick) {
                // 매 틱마다 schedule()을 실행하고 IDLE -> STANDBY -> RUN 순서로 상태를 전이
                if (tick == 0) {
                    machine.schedule();
                } else if (tick == 1) {
                    const auto res = machine.transition(state::StandbyState{});
                    if (!res) {
                        logger.log(atugcc::core::Level::Error, "STANDBY 전이 실패");
                    }
                    machine.schedule();
                } else if (tick == 2) {
                    const auto res = machine.transition(state::RunState{});
                    if (!res) {
                        logger.log(atugcc::core::Level::Error, "RUN 전이 실패");
                    }
                    machine.schedule();
                } else {
                    machine.schedule();
                }
            },
            logger
        };

        // 워커가 틱들을 순차적으로 실행할 수 있도록 약 120ms 대기
        std::this_thread::sleep_for(std::chrono::milliseconds(120));

        // 워커 정지 요청 및 완료 대기
        worker.requestStop();
        worker.join();
    }

    // 워커 스레드가 정지 및 조인 완료되었으므로 main 스레드에서 안전하게 결과 확인
    logger.log(atugcc::core::Level::Info,
               "장비 상태 머신 종료. 최종 상태: {}",
               machine.currentStateName());

    std::cout << "\n=== 터미널 추적 결과 (formatTerminal) ===\n";
    std::cout << tracer.formatTerminal() << '\n';

    std::cout << "=== Mermaid 다이어그램 결과 (formatDiagram) ===\n";
    std::cout << tracer.formatDiagram(viz::DiagramBackend::Mermaid) << '\n';

    return 0;
}
