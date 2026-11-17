# C++ Evolution: 스레드의 수명과 협력적 정지 (`std::jthread`, `std::stop_token`)

이 문서는 작업 스레드를 멈추는 코드가 `std::thread` + 플래그(C++11)에서 `std::jthread` + `stop_token`(C++20)으로 어떻게 바뀌었는지 보여 줍니다.

## Why
작업 스레드는 "멈춰 달라"는 요청을 알아들어야 하고, 멈춘 뒤에는 `join`되어야 합니다. 이 두 일을 사람이 손으로 하면 틀리기 쉽습니다. `join`을 잊으면 프로그램이 `std::terminate`로 끝나고, 정지 플래그만 쓰면 스레드가 자는 동안에는 요청을 못 듣습니다.

## 1. 예전 방식 (C++11/17)
`std::thread`와 `std::atomic<bool>` 플래그, `sleep_for`로 주기를 기다립니다.

```cpp
class LegacyWorker {
public:
    explicit LegacyWorker(std::chrono::milliseconds period)
        : period_{ period }, thread_{ [this] { run(); } } {}

    ~LegacyWorker() {
        requestStop();
        if (thread_.joinable()) {
            thread_.join();            // 잊으면 std::terminate
        }
    }

    void requestStop() { stop_.store(true); }

private:
    void run() {
        while (!stop_.load()) {
            std::this_thread::sleep_for(period_);   // 자는 동안에는 플래그를 못 봄
        }
    }

    std::chrono::milliseconds period_;
    std::atomic<bool> stop_{ false };
    std::thread thread_;               // 마지막: period_와 stop_이 먼저 만들어져야 함
};
```

- **수명**: `std::thread`는 `joinable()`인 채로 소멸하면 `std::terminate()`를 부릅니다. 스레드 함수가 이미 끝났어도 `join()`이나 `detach()`를 안 했다면 마찬가지입니다. 그래서 위처럼 소멸자에서 `join`하는 클래스로 감싸야 합니다. `joinable()`인 스레드에 다른 스레드를 이동 대입해도 `std::terminate`라서, 복사와 이동도 막아 둡니다.
- **정지가 늦음**: 스레드는 `sleep_for` 안에서 플래그를 읽을 수 없습니다. 정지 요청은 잠이 끝난 뒤에야 보이므로 **최대 한 주기** 늦습니다. 주기를 줄이면 덜 늦지만 깨어나는 횟수가 늘어 CPU를 씁니다.
- **정지 때 할 일**: 요청하는 쪽이 직접 불러야 합니다. 요청이 어디서 오는지 알아야 합니다.

## 2. C++20: `std::jthread`와 `std::stop_token`
`std::jthread`는 소멸자에서 `request_stop()`을 부른 뒤 `join()`하고, 호출 가능한 객체가 첫 인자로 `std::stop_token`을 받으면 그것을 넘겨 줍니다. 기다리는 쪽은 `std::condition_variable_any`의 `wait_for(lock, token, period, pred)`를 씁니다. 정지 요청이 오면 대기가 바로 끝납니다.

```cpp
std::jthread thread_{ [this](std::stop_token token) {
    std::unique_lock lock{ mutex_ };
    // 주기가 끝나거나 정지 요청이 오면 돌아온다. 정지 요청이면 pred()가 참이라 true
    while (!cv_.wait_for(lock, token, period_, [&token] { return token.stop_requested(); })) {
        lock.unlock();
        doWork();
        lock.lock();
    }
} };
```

`PeriodicWorker`(`lessons/units/jthread_worker/`)의 `run()`이 같은 생각으로 쓰여 있습니다. 레슨 `thread_and_log`는 같은 100ms 주기로 두 워커를 멈춰 시간을 잽니다. 예전 방식은 약 85ms(주기 100ms에서 먼저 기다린 15ms를 뺀 값), `std::jthread`는 0–몇 ms였습니다(값은 실행마다 다릅니다).

### `stop_token`의 세 도구
```cpp
std::stop_source source;                       // 요청하는 쪽
std::stop_token token = source.get_token();    // 요청을 확인하는 쪽 (복사해서 넘김)
std::stop_callback callback{ token, [] {       // 요청 때 한 번 불리는 함수 (CTAD)
    // 여기는 request_stop()을 부른 스레드에서 돈다
} };
source.request_stop();                         // 처음 요청이면 true, 콜백이 여기서 실행됨
```
- `std::stop_source`: 정지를 **요청**합니다. `std::jthread`도 안에 하나를 갖고 있습니다(`get_stop_source()`).
- `std::stop_token`: 정지가 요청되었는지 **확인**합니다(`stop_requested()`). 대기 함수(`condition_variable_any::wait_for`)에도 넘길 수 있습니다.
- `std::stop_callback`: 정지가 요청될 때 **한 번 불리는 함수**를 등록합니다. 콜백은 `request_stop()`을 부른 **스레드에서 바로** 돕니다. 이미 요청된 뒤에 등록하면 **등록하는 자리(생성자 안)** 에서 바로 돕니다. 소멸자는 콜백이 다른 스레드에서 도는 중이면 끝날 때까지 기다리므로, 콜백이 필요로 하는 잠금을 쥔 채 소멸시키지 마세요.

## 3. 멤버 선언 순서
`std::jthread` 멤버는 클래스의 **가장 마지막**에 선언합니다. 멤버는 선언의 역순으로 파괴되므로, 그래야 `thread_`가 가장 먼저 파괴(정지 요청과 `join`)되어 스레드 함수가 아직 쓰고 있는 다른 멤버(`cv_`, `mutex_`, `logger_`)가 먼저 사라지지 않습니다. 예전 방식의 클래스에서는 반대로 소멸자 본문이 `join`하므로 파괴 순서가 문제가 아니고, **생성** 순서가 문제입니다. `thread_`가 마지막이어야 스레드가 시작하는 순간 `period_`와 `stop_`이 이미 있습니다.

## 4. atugcc에서는
- 유닛 [`jthread_worker`](/lessons/units/jthread_worker/README.md)의 `PeriodicWorker`가 `std::jthread` + `condition_variable_any::wait_for(lock, token, …)`로 주기 작업을 합니다.
- 레슨: [`thread_and_log`](/lessons/tracks/essentials/thread_and_log/README.md) (essentials 트랙)이 `legacy_worker.hpp`의 예전 워커와 `PeriodicWorker`의 정지 시간을 재고, `std::stop_callback`의 두 동작을 찍고, 기능별 `Logger`를 씁니다.
