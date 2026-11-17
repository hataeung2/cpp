# C++ Evolution: Thread Lifetime and Cooperative Stop (`std::jthread`, `std::stop_token`)

This page shows how code that stops a worker thread changed from `std::thread` + a flag (C++11) to `std::jthread` + `stop_token` (C++20).

## Why
A worker thread has to hear the request "please stop", and after it stops it has to be `join`ed. Doing both by hand is easy to get wrong. Forget `join` and the program ends with `std::terminate`; use only a stop flag and the thread cannot hear the request while it sleeps.

## 1. Legacy (C++11/17)
`std::thread`, a `std::atomic<bool>` flag, and `sleep_for` for the period.

```cpp
class LegacyWorker {
public:
    explicit LegacyWorker(std::chrono::milliseconds period)
        : period_{ period }, thread_{ [this] { run(); } } {}

    ~LegacyWorker() {
        requestStop();
        if (thread_.joinable()) {
            thread_.join();            // forget it and std::terminate is called
        }
    }

    void requestStop() { stop_.store(true); }

private:
    void run() {
        while (!stop_.load()) {
            std::this_thread::sleep_for(period_);   // cannot see the flag while asleep
        }
    }

    std::chrono::milliseconds period_;
    std::atomic<bool> stop_{ false };
    std::thread thread_;               // last: period_ and stop_ must exist first
};
```

- **Lifetime**: a `std::thread` destroyed while `joinable()` calls `std::terminate()`. This holds even if the thread function has already ended, when you did not `join()` or `detach()`. So you wrap it in a class whose destructor joins, as above. Move-assigning another thread onto a `joinable()` one is also `std::terminate`, so copy and move are deleted too.
- **A late stop**: the thread cannot read the flag inside `sleep_for`. The request is seen only after the sleep ends, so the stop is **up to one period** late. A shorter period makes it less late but wakes up more often and costs CPU.
- **What to do at stop**: the requester has to call it directly, so it has to know where the request comes from.

## 2. C++20: `std::jthread` and `std::stop_token`
`std::jthread` calls `request_stop()` and then `join()` in its destructor, and hands a `std::stop_token` to the callable if it takes one as its first parameter. The waiting side uses `wait_for(lock, token, period, pred)` of `std::condition_variable_any`. When a stop is requested, the wait ends at once.

```cpp
std::jthread thread_{ [this](std::stop_token token) {
    std::unique_lock lock{ mutex_ };
    // returns when the period ends or a stop is requested; on a stop pred() is true, so it returns true
    while (!cv_.wait_for(lock, token, period_, [&token] { return token.stop_requested(); })) {
        lock.unlock();
        doWork();
        lock.lock();
    }
} };
```

`run()` of `PeriodicWorker` (`lessons/units/jthread_worker/`) is written with the same idea. The lesson `thread_and_log` stops two workers with the same 100 ms period and times them. The old way took about 85 ms (the 100 ms period minus the 15 ms waited first), `std::jthread` took 0 to a few ms (the values differ from run to run).

### The three tools of `stop_token`
```cpp
std::stop_source source;                       // the requesting side
std::stop_token token = source.get_token();    // the checking side (copy it around)
std::stop_callback callback{ token, [] {       // a function called once at the request (CTAD)
    // this runs on the thread that called request_stop()
} };
source.request_stop();                         // true for the first request; the callback runs here
```
- `std::stop_source`: **requests** the stop. A `std::jthread` holds one inside (`get_stop_source()`).
- `std::stop_token`: **checks** whether a stop was requested (`stop_requested()`). You can also pass it to a wait function (`condition_variable_any::wait_for`).
- `std::stop_callback`: registers a **function called once** when a stop is requested. The callback runs **at once on the thread that calls** `request_stop()`. If you register it after the request, it runs **at the place of registration (inside the constructor)**. Its destructor waits for the callback to end if the callback runs on another thread, so do not destroy it while holding a lock the callback needs.

## 3. Member declaration order
Declare the `std::jthread` member **last** in the class. Members are destroyed in reverse declaration order, so `thread_` is destroyed first (stop request and `join`), and the other members the thread function still uses (`cv_`, `mutex_`, `logger_`) cannot disappear before it. In the legacy class it is the other way round: the destructor body joins, so destruction order is not the problem; **construction** order is. With `thread_` last, `period_` and `stop_` already exist at the moment the thread starts.

## 4. In atugcc
- The `PeriodicWorker` of the unit [`jthread_worker`](/lessons/units/jthread_worker/README.en.md) does periodic work with `std::jthread` + `condition_variable_any::wait_for(lock, token, …)`.
- Lesson: [`thread_and_log`](/lessons/tracks/essentials/thread_and_log/README.en.md) (essentials track) times the stop of the legacy worker in `legacy_worker.hpp` against `PeriodicWorker`, prints the two behaviours of `std::stop_callback`, and uses one `Logger` per feature.
