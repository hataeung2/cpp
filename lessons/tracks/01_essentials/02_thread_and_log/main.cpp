#include <chrono>
#include <iostream>
#include <thread>

#include "atugcc/core/logger.hpp"
#include "units/jthread_worker/jthread_worker.hpp"

int main() {
    const atugcc::core::Logger::Config log_config{
        .liveOutput = &std::cout,
        .enableCrashDump = false
    };

    // [학습] 스레드당 하나의 Logger 사용 (KI-014)
    // Logger::log는 내부 링 버퍼(RingBuffer::write)를 락 없이 호출하므로 여러 스레드가
    // 동시에 하나의 Logger 인스턴스를 호출하는 것은 스레드 안전하지 않습니다.
    // 따라서 각 스레드가 자신만의 Logger 인스턴스를 소유해야 하며, 만약 공유해야 한다면
    // 호출부 주변을 외부 std::mutex 등으로 감싸 동기화해야 합니다.
    // main 스레드의 logger는 워커 스레드가 동작하지 않는 시점(시작 및 조인 후)에만 사용됩니다.
    atugcc::core::Logger logger{ log_config };
    atugcc::core::Logger fast_logger{ log_config };
    atugcc::core::Logger slow_logger{ log_config };

    logger.log(atugcc::core::Level::Info, "=== thread_and_log 레슨 시작 ===");

    using atugcc::lessons::jthread_worker::PeriodicWorker;

    // 서로 다른 주기(20ms, 30ms)를 가진 두 개의 워커 스레드 생성 (각자 전용 Logger 소유)
    PeriodicWorker worker_fast{
        "WorkerFast",
        std::chrono::milliseconds(20),
        [&fast_logger](std::size_t tick) {
            fast_logger.log(atugcc::core::Level::Debug, "[WorkerFast] 틱 실행: {}", tick);
        },
        fast_logger
    };

    PeriodicWorker worker_slow{
        "WorkerSlow",
        std::chrono::milliseconds(30),
        [&slow_logger](std::size_t tick) {
            slow_logger.log(atugcc::core::Level::Debug, "[WorkerSlow] 틱 실행: {}", tick);
        },
        slow_logger
    };

    // 약 200ms 동안 두 워커가 동시에 주기적으로 실행되도록 메인 스레드 대기
    std::this_thread::sleep_for(std::chrono::milliseconds(200));

    // 워커 스레드에 정지를 요청하고 조인
    worker_fast.requestStop();
    worker_slow.requestStop();

    worker_fast.join();
    worker_slow.join();

    const std::size_t fast_ticks = worker_fast.ticks();
    const std::size_t slow_ticks = worker_slow.ticks();

    // 워커 스레드가 모두 조인된 후 안전하게 main의 logger로 결과 기록
    logger.log(atugcc::core::Level::Info,
               "=== 워커 결과: WorkerFast = {} 틱, WorkerSlow = {} 틱 ===",
               fast_ticks,
               slow_ticks);

    std::cout << "WorkerFast total ticks: " << fast_ticks << '\n';
    std::cout << "WorkerSlow total ticks: " << slow_ticks << '\n';

    return 0;
}
