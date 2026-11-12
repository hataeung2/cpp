#include <chrono>
#include <format>
#include <iostream>
#include <stop_token>
#include <thread>

#include "atugcc/core/logger.hpp"
#include "legacy_worker.hpp"
#include "units/jthread_worker/jthread_worker.hpp"

namespace {

constexpr std::chrono::milliseconds kPeriod{100};
constexpr std::chrono::milliseconds kHeadStart{15};

auto elapsedMs(std::chrono::steady_clock::time_point t0,
               std::chrono::steady_clock::time_point t1) {
    return std::chrono::round<std::chrono::milliseconds>(t1 - t0).count();
}

// [학습] 정지 지연 비교: 예전 방식 (LegacyWorker)
// sleep_for로 대기 중에는 정지 플래그를 확인할 수 없으므로, 정지 요청 후 대기가 끝날 때까지
// 최대 한 주기(kPeriod)만큼 늦게 종료됩니다.
// [Learn] Comparing stop latency: legacy approach (LegacyWorker)
// While sleeping in sleep_for, the thread cannot observe the stop flag, so it stops up to
// one full period (kPeriod) late after the stop request.
void stepLegacyStop() {
    std::cout << "== Step 1: std::thread with a stop flag (the old way) ==\n";

    std::chrono::steady_clock::time_point t0;
    {
        thread_and_log_lesson::LegacyWorker worker{ kPeriod };
        std::this_thread::sleep_for(kHeadStart);
        t0 = std::chrono::steady_clock::now();
        worker.requestStop();
    }
    const auto t1 = std::chrono::steady_clock::now();

    std::cout << std::format("legacy stop took {} ms (period {} ms)\n",
                             elapsedMs(t0, t1),
                             kPeriod.count());
}

// [학습] 정지 지연 비교: C++20 협력적 정지 (PeriodicWorker)
// std::jthread와 stop_token, condition_variable_any를 사용하면 정지 요청 시 대기 중인
// 조건 변수가 즉시 깨어나므로 남은 주기를 채우지 않고 즉시 정지합니다.
// [Learn] Comparing stop latency: C++20 cooperative stop (PeriodicWorker)
// Using std::jthread, stop_token, and condition_variable_any, a stop request immediately wakes
// the waiting condition variable, stopping at once without waiting out the remaining period.
void stepJthreadStop() {
    std::cout << "== Step 2: std::jthread with a stop_token ==\n";

    atugcc::core::Logger quiet_logger{
        atugcc::core::Logger::Config{ .enableCrashDump = false }
    };

    std::chrono::steady_clock::time_point t0;
    {
        atugcc::lessons::jthread_worker::PeriodicWorker worker{
            "StopTimer",
            kPeriod,
            {},
            quiet_logger
        };
        std::this_thread::sleep_for(kHeadStart);
        t0 = std::chrono::steady_clock::now();
        worker.requestStop();
        worker.join();
    }
    const auto t1 = std::chrono::steady_clock::now();

    std::cout << std::format("jthread stop took {} ms\n", elapsedMs(t0, t1));
}

// [학습] std::stop_callback의 동작 특성
// std::stop_callback은 stop_token에 정지 요청이 전달될 때 실행할 콜백을 등록하는 RAII 객체입니다.
// 1. 요청 스레드에서 실행: 콜백은 request_stop()을 호출한 스레드의 실행 흐름에서 직접 실행됩니다.
// 2. 사후 등록 시 즉시 실행: 이미 정지 요청된 토큰에 콜백을 등록하면 생성자 내부에서 콜백이 즉시 실행됩니다.
// [Learn] Behavior of std::stop_callback
// std::stop_callback is an RAII object that registers a callback to invoke when stop is requested.
// 1. Runs on requesting thread: the callback executes synchronously on the thread calling request_stop().
// 2. Runs at once if already requested: registering a callback after stop is already requested executes
//    the callback immediately inside the constructor before returning.
void stepStopCallback() {
    std::cout << "== Step 3: std::stop_callback ==\n";

    std::stop_source source;
    std::thread::id callback_thread_id;

    std::stop_callback cb{ source.get_token(), [&callback_thread_id] {
        callback_thread_id = std::this_thread::get_id();
    } };

    std::thread::id requester_thread_id;
    std::thread requester{ [&source, &requester_thread_id] {
        requester_thread_id = std::this_thread::get_id();
        source.request_stop();
    } };
    requester.join();

    const auto main_thread_id = std::this_thread::get_id();
    std::cout << std::format("callback ran on the requesting thread: {}\n",
                             callback_thread_id == requester_thread_id);
    std::cout << std::format("callback ran on the main thread: {}\n",
                             callback_thread_id == main_thread_id);

    bool late_callback_ran{ false };
    std::stop_callback late_cb{ source.get_token(), [&late_callback_ran] {
        late_callback_ran = true;
    } };
    std::cout << std::format("registered after the request, callback ran at once: {}\n",
                             late_callback_ran);
}

} // namespace

int main() {
    stepLegacyStop();
    stepJthreadStop();
    stepStopCallback();

    std::cout << "== Step 4: workers with one Logger per feature ==\n";

    const atugcc::core::Logger::Config log_config{
        .liveOutput = &std::cout,
        .enableCrashDump = false
    };

    // [학습] 기능별 Logger
    // Logger는 여러 스레드가 함께 써도 안전합니다(spec 010-08, 010-09). 여기서는 워커마다 전용 Logger를
    // 두어 기능별로 설정(출력 대상, 이력 크기)을 따로 정할 수 있게 합니다. 출력은 로그 스레드 하나가
    // 쓰므로 세 Logger가 std::cout 하나를 함께 써도 줄이 섞이지 않습니다.
    // [Learn] One Logger per feature
    // A Logger is safe to share between threads (spec 010-08, 010-09). Here each worker gets its own Logger
    // so that each feature can have its own settings (output target, history size). One log thread does the
    // output, so the lines of the three Loggers do not mix although they share one std::cout.
    atugcc::core::Logger logger{ log_config };
    atugcc::core::Logger fast_logger{ log_config };
    atugcc::core::Logger slow_logger{ log_config };

    logger.log(atugcc::core::Level::Info, "=== thread_and_log lesson start ===");

    using atugcc::lessons::jthread_worker::PeriodicWorker;

    // 서로 다른 주기(20ms, 30ms)를 가진 두 개의 워커 스레드 생성 (기능별 Logger)
    // Two worker threads with different periods (20ms, 30ms), each with its own Logger
    PeriodicWorker worker_fast{
        "WorkerFast",
        std::chrono::milliseconds(20),
        [&fast_logger](std::size_t tick) {
            fast_logger.log(atugcc::core::Level::Debug, "[WorkerFast] tick {}", tick);
        },
        fast_logger
    };

    PeriodicWorker worker_slow{
        "WorkerSlow",
        std::chrono::milliseconds(30),
        [&slow_logger](std::size_t tick) {
            slow_logger.log(atugcc::core::Level::Debug, "[WorkerSlow] tick {}", tick);
        },
        slow_logger
    };

    // 약 200ms 동안 두 워커가 동시에 주기적으로 실행되도록 메인 스레드 대기
    // The main thread waits about 200ms while both workers run their periodic work
    std::this_thread::sleep_for(std::chrono::milliseconds(200));

    // 워커 스레드에 정지를 요청하고 조인
    // Ask the worker threads to stop, then join them
    worker_fast.requestStop();
    worker_slow.requestStop();

    worker_fast.join();
    worker_slow.join();

    const std::size_t fast_ticks = worker_fast.ticks();
    const std::size_t slow_ticks = worker_slow.ticks();

    // 워커 스레드가 모두 조인된 후 안전하게 main의 logger로 결과 기록
    // Both workers are joined, so main's logger can safely record the result
    logger.log(atugcc::core::Level::Info,
               "=== worker result: WorkerFast = {} ticks, WorkerSlow = {} ticks ===",
               fast_ticks,
               slow_ticks);

    // [학습] Logger는 비동기로 전달한다(spec 010-09). std::cout으로 직접 찍기 전에 flush()로
    // 앞의 로그 줄이 모두 출력되기를 기다려야 순서가 섞이지 않는다. flush()는 어느 Logger로 쓴 줄이든
    // 호출 전의 줄을 모두 기다리므로 fast_logger, slow_logger의 줄도 포함된다.
    // [Learn] The Logger delivers asynchronously (spec 010-09). Before printing to std::cout directly, wait
    // with flush() until every earlier log line is out, or the order mixes. flush() waits for every line
    // written before the call through any Logger, so the lines of fast_logger and slow_logger are included.
    logger.flush();

    std::cout << "WorkerFast total ticks: " << fast_ticks << '\n';
    std::cout << "WorkerSlow total ticks: " << slow_ticks << '\n';

    return 0;
}
