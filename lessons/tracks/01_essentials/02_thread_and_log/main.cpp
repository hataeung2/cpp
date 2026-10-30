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

    // [학습] 기능별 Logger
    // Logger는 여러 스레드가 함께 써도 안전합니다(spec 010-08, 010-09). 여기서는 워커마다 전용 Logger를
    // 두어 기능별로 설정(출력 대상, 이력 크기)을 따로 정할 수 있게 합니다. 출력은 로그 스레드 하나가
    // 쓰므로 세 Logger가 std::cout 하나를 함께 써도 줄이 섞이지 않습니다.
    atugcc::core::Logger logger{ log_config };
    atugcc::core::Logger fast_logger{ log_config };
    atugcc::core::Logger slow_logger{ log_config };

    logger.log(atugcc::core::Level::Info, "=== thread_and_log 레슨 시작 ===");

    using atugcc::lessons::jthread_worker::PeriodicWorker;

    // 서로 다른 주기(20ms, 30ms)를 가진 두 개의 워커 스레드 생성 (기능별 Logger)
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

    // [학습] Logger는 비동기로 전달한다(spec 010-09). std::cout으로 직접 찍기 전에 flush()로
    // 앞의 로그 줄이 모두 출력되기를 기다려야 순서가 섞이지 않는다. flush()는 어느 Logger로 쓴 줄이든
    // 호출 전의 줄을 모두 기다리므로 fast_logger, slow_logger의 줄도 포함된다.
    logger.flush();

    std::cout << "WorkerFast total ticks: " << fast_ticks << '\n';
    std::cout << "WorkerSlow total ticks: " << slow_ticks << '\n';

    return 0;
}
