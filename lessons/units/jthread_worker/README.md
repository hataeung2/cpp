# jthread_worker 유닛

`std::jthread`와 `std::stop_token`을 활용하여 주기적인 작업을 수행하고, 안전한 협력적 취소(cooperative cancellation) 및 RAII 소멸을 보장하는 백그라운드 작업 스레드 유닛입니다.

## 1. 개요 및 학습 포인트

C++20에 도입된 `std::jthread`는 기존 `std::thread`의 여러 취약점을 개선하였습니다. 본 유닛의 `PeriodicWorker`는 다음 원칙을 따릅니다:

1. **RAII 기반 자동 조인 및 취소 (`std::jthread`)**
   - 기존 `std::thread`는 스레드가 종료되기 전에 명시적으로 `join()`이나 `detach()`를 호출하지 않고 소멸하면 `std::terminate()`를 호출하여 프로세스를 강제 종료시켰습니다.
   - `std::jthread`는 소멸자에서 내부적으로 `request_stop()`을 호출한 후 `join()`을 수행하므로 자원 누수나 비정상 종료 없이 안전하게 정리됩니다.

2. **`std::condition_variable_any`와 `std::stop_token` 연동**
   - 작업 주기를 대기할 때 단순 `std::this_thread::sleep_for()`를 쓰면 대기 시간 도중에 정지 요청이 들어와도 주기가 끝날 때까지 멈추지 않습니다.
   - `cv_.wait_for(lock, stop_token, period, pred)`를 사용하면, 대기 도중에 `request_stop()`이 호출되는 순간 `stop_token`의 콜백을 통해 조건 변수가 즉시 깨어나 지연 없이 스레드를 종료할 수 있습니다.

3. **클래스 멤버 파괴 순서 (선언 역순)와 스레드 안전성**
   - C++ 표준에 따라 클래스 멤버 변수들은 **선언된 순서의 역순**으로 소멸자가 호출됩니다.
   - `PeriodicWorker` 클래스에서 `std::jthread thread_` 멤버는 **반드시 클래스의 가장 마지막 멤버로 선언**되어 있습니다.
   - 이렇게 선언하면 소멸자가 동작할 때 `thread_`가 가장 먼저 소멸(stop 요청 + join 완료)됩니다. 스레드 루프 함수(`run()`)가 완전히 끝난 뒤에 비로소 다른 멤버(`logger_`, `task_`, `cv_mutex_`, `cv_` 등)가 소멸하므로, 스레드가 이미 파괴된 멤버에 접근하는 Dangling Reference / Use-After-Free 버그를 완벽히 방지합니다.

4. **Logger 스레드 안전성 계약 (Thread Safety Contract)**
   - `PeriodicWorker` 생성자에 주입되는 `atugcc::core::Logger&`는 **동시에 다른 스레드에서 사용되어서는 안 됩니다**.
   - `Logger::log`는 내부 링 버퍼(`RingBuffer::write`)를 단일 스레드 무잠금으로 호출하므로(KI-014), 여러 스레드가 동시에 동일한 `Logger` 인스턴스에 로그를 남기면 데이터 레이스가 발생합니다.
   - 따라서 워커마다 독립된 `Logger` 인스턴스를 주입하거나, 부득이하게 공유해야 하는 경우 호출부 외부에서 `std::mutex` 등으로 동기화해야 합니다.

## 2. 주요 인터페이스

```cpp
namespace atugcc::lessons::jthread_worker {

class PeriodicWorker {
public:
    PeriodicWorker(std::string name,
                   std::chrono::milliseconds period,
                   std::function<void(std::size_t tick)> task,
                   atugcc::core::Logger& logger);

    ~PeriodicWorker() = default;

    // 복사 및 이동 금지
    PeriodicWorker(const PeriodicWorker&) = delete;
    PeriodicWorker& operator=(const PeriodicWorker&) = delete;
    PeriodicWorker(PeriodicWorker&&) = delete;
    PeriodicWorker& operator=(PeriodicWorker&&) = delete;

    void requestStop();
    void join();
    [[nodiscard]] std::size_t ticks() const noexcept;
};

} // namespace atugcc::lessons::jthread_worker
```

## 3. 사용 예시

```cpp
#include "atugcc/core/logger.hpp"
#include "units/jthread_worker/jthread_worker.hpp"

// [주의] 주입되는 Logger는 이 워커 스레드 전용이어야 하며, 다른 스레드에서 동시에 사용되어서는 안 됩니다.
atugcc::core::Logger worker_logger;

atugcc::lessons::jthread_worker::PeriodicWorker worker{
    "Worker1",
    std::chrono::milliseconds(50),
    [](std::size_t tick) {
        // 매 50ms마다 호출되는 작업 (0부터 시작하는 틱 번호 전달)
    },
    worker_logger
};

std::this_thread::sleep_for(std::chrono::milliseconds(200));
worker.requestStop();
worker.join();
```
