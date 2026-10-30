#pragma once

#include <atomic>
#include <chrono>
#include <condition_variable>
#include <cstddef>
#include <functional>
#include <mutex>
#include <stop_token>
#include <string>
#include <thread>
#include <utility>

#include "atugcc/core/logger.hpp"

namespace atugcc::lessons::jthread_worker {

/**
 * @class PeriodicWorker
 * @brief 주기적으로 지정된 작업을 실행하는 RAII 기반 백그라운드 작업 스레드
 *
 * [학습 포인트]
 * 1. std::jthread: 소멸 시 자동으로 request_stop() 및 join()을 수행하므로
 *    예외나 스코프 종료 시 스레드 누수나 std::terminate() 호출을 방지합니다.
 * 2. std::condition_variable_any + std::stop_token:
 *    주기 대기 중 stop이 요청되면 남은 시간을 채우지 않고 즉시 깨어나 안전하게 종료합니다.
 * 3. 멤버 선언 순서: std::jthread member(thread_)는 반드시 클래스의 가장 마지막에 선언되어야 합니다.
 *    C++ 규칙상 멤버는 선언 역순으로 파괴되므로, thread_가 가장 먼저 파괴(stop + join)되어
 *    스레드 함수가 다른 멤버(cv, mutex, logger 등)를 참조하는 중에 이들이 먼저 파괴되는 것을 방지합니다.
 * 4. 주입받는 atugcc::core::Logger&는 참조로 보관하므로 워커보다 오래 살아야 합니다.
 *    Logger는 여러 스레드가 함께 써도 안전합니다(spec 010-08). 워커마다 다른 Logger를 넘기는 것은
 *    기능별로 설정을 나누고 싶을 때입니다.
 */
class PeriodicWorker {
public:
    PeriodicWorker(std::string name,
                   std::chrono::milliseconds period,
                   std::function<void(std::size_t tick)> task,
                   atugcc::core::Logger& logger)
        : name_{ std::move(name) }
        , period_{ period }
        , task_{ std::move(task) }
        , logger_{ logger }
        , ticks_{ 0 }
        , cv_mutex_{}
        , cv_{}
        , thread_{ [this](std::stop_token st) { run(st); } }
    {}

    ~PeriodicWorker() = default;

    // 복사 및 이동 금지
    PeriodicWorker(const PeriodicWorker&) = delete;
    PeriodicWorker& operator=(const PeriodicWorker&) = delete;
    PeriodicWorker(PeriodicWorker&&) = delete;
    PeriodicWorker& operator=(PeriodicWorker&&) = delete;

    /// 작업 스레드에 협력적 정지를 요청하고 대기 중인 CV를 깨웁니다.
    void requestStop() {
        thread_.request_stop();
        cv_.notify_all();
    }

    /// 스레드가 종료될 때까지 대기합니다.
    void join() {
        if (thread_.joinable()) {
            thread_.join();
        }
    }

    /// 지금까지 실행된 틱(tick) 횟수를 반환합니다.
    [[nodiscard]] std::size_t ticks() const noexcept {
        return ticks_.load();
    }

private:
    void run(std::stop_token stop_token) {
        logger_.log(atugcc::core::Level::Info, "[{}] worker started (period: {}ms)", name_, period_.count());

        while (!stop_token.stop_requested()) {
            std::unique_lock lock(cv_mutex_);
            const bool stopped = cv_.wait_for(lock, stop_token, period_, [&stop_token] {
                return stop_token.stop_requested();
            });

            if (stopped || stop_token.stop_requested()) {
                break;
            }

            lock.unlock();

            if (task_) {
                const std::size_t current_tick = ticks_.fetch_add(1);
                task_(current_tick);
            }
        }

        logger_.log(atugcc::core::Level::Info, "[{}] worker stopped (total ticks: {})", name_, ticks_.load());
    }

    std::string name_;
    std::chrono::milliseconds period_;
    std::function<void(std::size_t tick)> task_;
    atugcc::core::Logger& logger_;
    std::atomic<std::size_t> ticks_{ 0 };
    std::mutex cv_mutex_;
    std::condition_variable_any cv_;

    // [중요] C++ 멤버 파괴 순서(선언의 역순)를 위해 std::jthread는 반드시 가장 마지막에 선언합니다.
    // 소멸 시 thread_가 먼저 stop_token 요청 및 join을 완료한 후 나머지 멤버들이 안전하게 파괴됩니다.
    std::jthread thread_;
};

} // namespace atugcc::lessons::jthread_worker
