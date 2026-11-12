#pragma once

#include <atomic>
#include <chrono>
#include <thread>

namespace thread_and_log_lesson {

/**
 * @brief C++20 이전 방식의 std::thread 및 정지 플래그 기반 주기 작업 워커
 * @brief Pre-C++20 worker thread using std::thread and a stop flag
 *
 * [학습]
 * 1. 정지 지연: 스레드가 sleep_for 대기 중에는 정지 플래그를 확인할 수 없으므로(sleep_for는 중단 불가),
 *    정지 요청이 최대 한 주기 늦게 감지됩니다.
 * 2. 소멸자 join: std::thread는 소멸 시점에 여전히 joinable() 상태이면 std::terminate()를 호출합니다.
 *    따라서 ~LegacyWorker에서 반드시 join()해야 하며, 이를 잊으면 전체 프로그램이 비정상 종료됩니다.
 * 3. 복사 및 이동 금지: joinable()인 std::thread를 다른 객체로 이동 대입하면 std::terminate()가
 *    호출되고, 스레드 함수가 this 포인터를 붙잡고 있으므로 복사와 이동을 모두 삭제합니다.
 * 4. 멤버 선언 순서: C++ 규칙상 멤버는 선언 순서대로 생성되므로, 스레드 함수가 시작 즉시 period_와
 *    stop_을 안전하게 읽을 수 있도록 thread_를 가장 마지막에 선언합니다.
 *
 * [Learn]
 * 1. Delayed stop: while sleeping in sleep_for, the thread cannot observe the flag (sleep_for is not
 *    interrupted), so a stop request is noticed up to one period late.
 * 2. Destructor join: a std::thread that is still joinable() when its destructor runs calls std::terminate().
 *    That is why ~LegacyWorker joins; forgetting it terminates the whole program.
 * 3. Deleted copy and move: moving a std::thread over another one that is still joinable() calls
 *    std::terminate(), and the thread function holds the this pointer; that is why copy and move are deleted.
 * 4. Member declaration order: C++ constructs members in declaration order, so thread_ is declared last
 *    to ensure the thread function can safely read period_ and stop_ right away.
 */
class LegacyWorker {
public:
    explicit LegacyWorker(std::chrono::milliseconds period)
        : period_{ period }
        , thread_{ [this] { run(); } }
    {}

    // 소멸자에서 정지를 요청하고 스레드가 joinable()이면 join()합니다.
    // 이를 잊어 joinable()인 채 소멸하면 std::terminate()가 호출됩니다.
    // Requests stop and joins the thread if joinable().
    // If a joinable std::thread is destroyed without joining, std::terminate() is called.
    ~LegacyWorker() {
        requestStop();
        if (thread_.joinable()) {
            thread_.join();
        }
    }

    // 복사 및 이동 금지: joinable()인 std::thread의 이동 대입은 std::terminate()를 부르며 this를 캡처함
    // Deleted copy and move: moving over a joinable std::thread calls std::terminate(), and thread holds this
    LegacyWorker(const LegacyWorker&) = delete;
    LegacyWorker& operator=(const LegacyWorker&) = delete;
    LegacyWorker(LegacyWorker&&) = delete;
    LegacyWorker& operator=(LegacyWorker&&) = delete;

    // 워커 스레드에 정지를 요청합니다 (여러 번 호출 가능).
    // Requests the worker thread to stop (may be called more than once).
    void requestStop() noexcept {
        stop_.store(true);
    }

private:
    // 스레드 작업 루프: sleep_for 대기 중에는 정지 플래그를 감지하지 못하므로 최대 한 주기 늦게 종료됩니다.
    // Thread worker loop: cannot check the stop flag while sleeping, noticing the stop up to one period late.
    void run() {
        while (!stop_.load()) {
            std::this_thread::sleep_for(period_);
            // 주기적 작업이 수행될 위치
            // Periodic work would go here
        }
    }

    std::chrono::milliseconds period_;
    std::atomic<bool> stop_{ false };

    // [중요] C++ 멤버 생성 순서(선언 순서)를 위해 thread_를 가장 마지막에 선언합니다.
    // 스레드 함수가 시작 즉시 period_와 stop_을 참조하므로 이들이 먼저 생성되어 있어야 합니다.
    // [Important] thread_ is declared last because C++ constructs members in declaration order.
    // The thread function accesses period_ and stop_ right away, so they must be initialized first.
    std::thread thread_;
};

} // namespace thread_and_log_lesson
