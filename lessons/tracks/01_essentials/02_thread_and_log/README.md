# 레슨: std::jthread 작업 스레드와 로거 연동 (`thread_and_log`)

`jthread_worker` 유닛(`PeriodicWorker`)과 `atugcc::core::Logger`를 사용하여 두 개의 백그라운드 스레드를 주기적으로 실행하고 안전하게 종료시키는 레슨입니다.

## 1. 레슨 내용

이 레슨은 다음을 다룹니다:
- 서로 다른 주기(20ms, 30ms)를 가진 두 개의 `PeriodicWorker` 인스턴스를 생성하여 동시에 실행합니다.
- **기능별 Logger**: 하나의 `Logger`를 여러 스레드가 함께 써도 안전합니다. 그래도 이 레슨은 워커마다 전용 Logger(`fast_logger`, `slow_logger`)를 둡니다. 기능마다 출력 대상(`liveOutput`)이나 이력 크기(`bufferCapacity`) 같은 설정을 따로 정할 수 있게 하는, 권장하는 사용법입니다.
- 메인 스레드가 약 200ms 동안 대기한 후, 두 작업 스레드에 정지(`requestStop`)를 요청하고 조인(`join`)합니다.
- 각 스레드가 수행한 총 틱(tick) 횟수를 출력하여 주기 비율(20ms vs 30ms)에 따른 동작을 확인합니다.
- 전체 실행 시간은 1초 이내(약 200~250ms)로 빠르게 완료됩니다.

## 2. 핵심 학습 개념

### `std::thread` vs `std::jthread` (C++20)
- **자동 조인(Auto-join)**: `std::thread`는 스레드 객체가 소멸할 때 `joinable()` 상태이면 `std::terminate()`를 호출해 프로그램을 비정상 종료시킵니다. 반면 `std::jthread`는 소멸자에서 자동으로 정지를 요청하고 `join()`을 호출합니다.
- **협력적 정지(Cooperative Cancellation)**: `std::jthread`는 내부적으로 `std::stop_source`를 보유하며, 스레드 함수에 `std::stop_token`을 주입할 수 있습니다. 스레드 외부에서 `request_stop()`을 호출하면 `stop_token.stop_requested()`가 참이 되어 안전하게 루프를 탈출할 수 있습니다.

### `std::condition_variable_any::wait_for`와 `std::stop_token`
- 단순 `sleep_for()`는 대기 도중 정지 요청을 감지하지 못하지만, `std::condition_variable_any`의 `wait_for(lock, stop_token, period, pred)` 오버로드는 대기 중 `stop_token`에 정지가 요청되는 즉시 대기를 중단하고 반환합니다.

### Logger의 스레드 안전성 계약
- `atugcc::core::Logger`의 모든 public 함수는 여러 스레드에서 동시에 불러도 안전하고, `log()`는 잠금을 잡지 않습니다. 각 스레드가 자기 버퍼에 줄을 넣고, 로그 스레드 하나가 이력(`snapshot()`)·실시간 출력·파일에 씁니다(spec 010-09).
- 그래서 전달은 **비동기**입니다. `std::cout`으로 직접 찍기 전에는 `logger.flush()`로 앞의 로그 줄이 모두 나오기를 기다립니다(`main.cpp` 끝; `flush()`는 어느 Logger로 쓴 줄이든 호출 전의 줄을 모두 기다립니다). 줄이 기록된 뒤 돌아와야 하면 `Config::delivery = Delivery::Sync`(OS에 쓴 뒤 돌아옴, `Durability::System`이면 디스크까지).
- 실시간 출력과 파일은 로그 스레드 하나만 쓰므로 여러 Logger가 `std::cout` 하나를 함께 써도 줄이 섞이지 않습니다.
- crash dump를 켜면(`enableCrashDump = true`, 기본값; 이 레슨은 끔) crash가 날 때 **모든 스레드**(이미 끝난 스레드 포함)의 최근 기록이 crash dump에 남습니다. `py -3 tools/read_dump.py log/crash_dump_<시각>.log`로 읽습니다. 어떤 종료에서 무엇이 남는지는 루트 README의 표에 있습니다.
- **그럼 언제 나누는가**: 스레드 수가 아니라 기능 기준으로 나눕니다(출력 대상, 이력 크기, 수동 `dump()`를 쓸 디렉터리). crash dump 대상은 프로세스에 하나이고, 처음 준비한 Logger가 디렉터리를 정합니다. 레벨 필터는 아직 없습니다. 공유 Logger와 스레드별 Logger의 성능 차이는 `logger_contention_probe`로 잴 수 있습니다(spec 010-08).

## 3. 실행 방법

### ctest를 통한 실행 (Smoke Test)
```bash
ctest -R lesson.thread_and_log --output-on-failure
```

### 실행 바이너리 직접 실행
```bash
# Windows
bin\lessons\lesson_thread_and_log.exe
# 또는 Debug 설정인 경우
bin\Debug\lessons\lesson_thread_and_log.exe

# Linux
bin/lessons/lesson_thread_and_log
```

## 4. 연습 과제

1. **주기 변경 실험**: 두 워커의 주기를 각각 10ms와 50ms로 변경해 보세요. 총 실행 시간(200ms) 동안 각 워커가 실행한 틱 수가 대략 5:1 비율이 되는지 확인합니다.
2. **조기 정지(Early Stop)**: `std::this_thread::sleep_for(100ms)` 시점에 `worker_fast.requestStop()`을 먼저 호출하고 다시 100ms를 대기해 보세요. `worker_fast`는 100ms 시점에 즉시 멈추고 `worker_slow`만 200ms까지 계속 도는지 관찰합니다.
3. **로그 레벨 변경 및 틱별 조건부 로깅**: 워커의 `task` 람다 안에서 특정 틱(예: `tick % 3 == 0`)일 때 `logger.log(atugcc::core::Level::Warn, ...)`로 경고 로그를 남기도록 코드를 수정해 보세요.
4. **공유 Logger와 기능별 Logger 비교**: 두 워커가 `logger` 하나를 함께 쓰도록 바꿔 보세요(`fast_logger`, `slow_logger` 대신 `logger`를 넘김). 출력 줄이 섞이지 않는지 확인하고, `snapshot()`에 두 워커의 줄이 시간 순서대로 함께 들어 있는지 보세요. `logger.flush()`를 지우면 마지막 `std::cout` 줄과 로그 줄의 순서가 어떻게 되는지도 보세요. 그다음 "느린 워커의 로그만 파일로 보내고 싶다"처럼 기능별 설정이 필요한 상황을 떠올려 보고(`liveOutput`에 `std::ofstream`을 넘겨 보세요), 왜 기능별 Logger가 여전히 유용한지 설명해 보세요.
