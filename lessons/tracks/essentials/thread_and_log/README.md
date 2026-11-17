# 레슨: std::jthread 작업 스레드와 로거 연동 — 정지가 늦는 예전 방식과 협력적 정지 (`thread_and_log`)

작업 스레드를 멈추려면 "멈춰 달라"는 요청을 스레드가 알아듣고, 멈춘 뒤에 스레드를 `join`해야 합니다. 이 레슨은 네 단계로 보입니다. (1) `std::thread` + `std::atomic<bool>` 플래그 + `sleep_for`로 만든 예전 워커가 정지 요청 뒤 **얼마나 늦게** 멈추는지 재고, (2) 같은 주기의 `std::jthread` + `stop_token` 워커(`jthread_worker` 유닛의 `PeriodicWorker`)가 멈추는 시간을 재고, (3) 정지 요청 때 한 번 불리는 함수 `std::stop_callback`을 보고, (4) 두 `PeriodicWorker`와 기능별 `Logger`로 주기 작업을 합니다. 전체 실행은 1초 안입니다. 해설: [jthread_stop_token.md](/docs/cpp_evolution/jthread_stop_token.md).

## 예전 방식과 C++20
| | `std::thread` + 플래그 (C++11) | `std::jthread` + `stop_token` (C++20) |
|---|---|---|
| 수명 | `joinable()`인 채 소멸하면 `std::terminate`. 소멸자에서 `join()`을 직접 부르는 클래스를 써야 함 | 소멸자가 `request_stop()`을 부른 뒤 `join()` |
| 정지 요청 | `std::atomic<bool>` 플래그를 직접 만들고 스레드 함수가 직접 읽음 | `stop_source`가 요청, 스레드 함수가 `stop_token`을 받음 |
| 대기 중 깨우기 | 불가: `sleep_for`가 끝나야 플래그를 봄. 정지가 **최대 한 주기** 늦음 | `condition_variable_any::wait_for(lock, token, …)`가 정지 요청에 바로 깸 |
| 정지 때 할 일 | 요청하는 쪽이 직접 부름 | `std::stop_callback`을 등록 |

예전 방식의 코드는 [legacy_worker.hpp](legacy_worker.hpp)와 [jthread_stop_token.md](/docs/cpp_evolution/jthread_stop_token.md)에 있습니다. `std::thread`를 `join`하지 않고 끝내면 프로그램이 `std::terminate`로 끝나서 뒤 단계가 돌지 못하므로, 레슨은 그 모습을 실행하지 않고 연습 6번으로 남겼습니다.

## 실행
- 웹 플레이그라운드: 레슨 트리에서 선택 후 Run
- 로컬: `py -3 .agent/scripts/build.py --preset <preset> --target lesson_thread_and_log` 후 `out/build/<preset>/bin/lessons/lesson_thread_and_log`(Windows는 `.exe`), 또는 `ctest --preset <preset> -R lesson.thread_and_log`

## 볼 것
예시 출력(숫자는 실행마다 다릅니다. 레슨은 값을 판정하지 않고 찍기만 합니다):
```text
== Step 1: std::thread with a stop flag (the old way) ==
legacy stop took 83 ms (period 100 ms)
== Step 2: std::jthread with a stop_token ==
jthread stop took 0 ms
== Step 3: std::stop_callback ==
callback ran on the requesting thread: true
callback ran on the main thread: false
registered after the request, callback ran at once: true
```
- 1단계: `LegacyWorker`(주기 100ms)를 만들고 15ms 뒤에 `requestStop()`을 부릅니다. 스레드는 그때 `sleep_for` 안에 있어서 플래그를 못 보고, 잠이 끝난 뒤에야 보고 멈춥니다. 블록이 끝나며 `~LegacyWorker`가 `join`하므로 재는 시간은 대략 `100 - 15 = 85ms`입니다. 정지는 **최대 한 주기** 늦습니다.
- 2단계: 같은 주기의 `PeriodicWorker`는 `condition_variable_any::wait_for(lock, stop_token, …)`로 기다려서, `requestStop()`이 대기를 바로 깨웁니다. 재는 시간은 보통 0–몇 ms입니다. 두 시간의 차이가 이 레슨의 핵심입니다.
- 3단계: `stop_callback`의 콜백은 `request_stop()`을 **부른 스레드**에서 바로 돕니다(요청한 스레드에서 `true`, 메인에서 `false`). 이미 요청된 뒤에 등록하면 콜백이 등록하는 자리(생성자 안)에서 바로 돕니다.
- 4단계: 이전부터 있던 부분입니다. 주기가 20ms와 30ms인 두 워커가 약 200ms 돌고 틱 수를 찍습니다. `Logger`는 여러 스레드가 함께 써도 안전하고, `log()`는 잠금을 잡지 않으며, 줄은 로그 스레드 하나가 이력·실시간 출력·파일에 씁니다(spec 010-09). 그래서 세 `Logger`가 `std::cout` 하나를 함께 써도 줄이 섞이지 않습니다. 전달은 **비동기**라서 `std::cout`으로 직접 찍기 전에는 `logger.flush()`로 앞의 로그 줄이 모두 나오기를 기다립니다(`flush()`는 어느 `Logger`로 쓴 줄이든 호출 전의 줄을 모두 기다림). 줄이 기록된 뒤 돌아와야 하면 `Config::delivery = Delivery::Sync`입니다. crash dump를 켜면(`enableCrashDump = true`, 기본값; 이 레슨은 끔) crash 때 **모든 스레드**(이미 끝난 스레드 포함)의 최근 기록이 남고 `py -3 tools/read_dump.py log/crash_dump_<시각>.log`로 읽습니다.
- 워커마다 `Logger`를 나누는 기준은 스레드 수가 아니라 **기능**입니다(출력 대상, 이력 크기, 수동 `dump()`를 쓸 디렉터리). crash dump 대상은 프로세스에 하나이고, 처음 준비한 `Logger`가 디렉터리를 정합니다. 공유 `Logger`와 스레드별 `Logger`의 성능 차이는 `logger_contention_probe`로 잴 수 있습니다(spec 010-08).
- 대기 정밀도는 OS마다 다릅니다. Windows는 `sleep_for`와 조건 변수 대기가 약 16ms 단위로 움직여서, 1단계의 값이 주기(100ms)를 조금 넘기도 하고(10번 중 한 번 102ms), 4단계에서 20ms와 30ms 워커의 틱 수가 같게 나오기도 합니다.

## 연습
1. **주기 변경 실험**: 4단계 두 워커의 주기를 각각 10ms와 50ms로 바꿔 보세요. 총 실행 시간(약 200ms) 동안 각 워커가 실행한 틱 수가 대략 5:1 비율이 되는지 확인합니다(Windows는 대기 정밀도 때문에 비율이 덜 벌어질 수 있습니다).
2. **조기 정지(Early Stop)**: 4단계에서 `std::this_thread::sleep_for(100ms)` 시점에 `worker_fast.requestStop()`을 먼저 호출하고 다시 100ms를 대기해 보세요. `worker_fast`는 100ms 시점에 즉시 멈추고 `worker_slow`만 200ms까지 계속 도는지 관찰합니다.
3. **로그 레벨 변경 및 틱별 조건부 로깅**: 워커의 `task` 람다 안에서 특정 틱(예: `tick % 3 == 0`)일 때 `fast_logger.log(atugcc::core::Level::Warn, ...)`로 경고 로그를 남기도록 코드를 수정해 보세요.
4. **공유 Logger와 기능별 Logger 비교**: 두 워커가 `logger` 하나를 함께 쓰도록 바꿔 보세요(생성자 인자와 람다의 `fast_logger`, `slow_logger`를 모두 `logger`로). 출력 줄이 섞이지 않는지 확인하고, `snapshot()`에 두 워커의 줄이 시간 순서대로 함께 들어 있는지 보세요. `logger.flush()`를 지우면 마지막 `std::cout` 줄과 로그 줄의 순서가 어떻게 되는지도 보세요. 그다음 "느린 워커의 로그만 파일로 보내고 싶다"처럼 기능별 설정이 필요한 상황을 떠올려 보고(`liveOutput`에 `std::ofstream`을 넘겨 보세요), 왜 기능별 `Logger`가 여전히 유용한지 설명해 보세요.
5. **예전 방식의 주기 키우기**: `main.cpp`의 `kPeriod`를 500ms로 바꾸고 실행해 보세요. `legacy stop took … ms (period 500 ms)`는 얼마나 되고, `jthread stop took … ms`는 어떻게 달라지나요? 정지가 늦는 시간은 무엇에 비례하나요?
6. **`join()` 지워 보기**: `legacy_worker.hpp`의 `~LegacyWorker`에서 `join()` 호출을 지우고 실행해 보세요. 어떻게 끝나나요? 왜 `std::jthread`에는 이런 일이 없나요? 확인한 뒤 되돌립니다.
