# 레슨: std::jthread 작업 스레드와 로거 연동 (`thread_and_log`)

`jthread_worker` 유닛(`PeriodicWorker`)과 `atugcc::core::Logger`를 사용하여 두 개의 백그라운드 스레드를 주기적으로 실행하고 안전하게 종료시키는 레슨입니다.

## 1. 레슨 내용

이 레슨은 다음을 다룹니다:
- 서로 다른 주기(20ms, 30ms)를 가진 두 개의 `PeriodicWorker` 인스턴스를 생성하여 동시에 실행합니다.
- **스레드별 독립 Logger 소유**: `Logger::log`의 내부 링 버퍼 구현 특성(KI-014: `RingBuffer::write`가 락 없이 동작)으로 인해 여러 스레드가 동시에 하나의 Logger를 호출하면 데이터 레이스가 발생합니다. 따라서 각 워커에 전용 Logger(`fast_logger`, `slow_logger`)를 할당합니다.
- 메인 스레드가 약 200ms 동안 대기한 후, 두 작업 스레드에 정지(`requestStop`)를 요청하고 조인(`join`)합니다.
- 각 스레드가 수행한 총 틱(tick) 횟수를 출력하여 주기 비율(20ms vs 30ms)에 따른 동작을 확인합니다.
- 전체 실행 시간은 1초 이내(약 200~250ms)로 빠르게 완료됩니다.

## 2. 핵심 학습 개념

### `std::thread` vs `std::jthread` (C++20)
- **자동 조인(Auto-join)**: `std::thread`는 스레드 객체가 소멸할 때 `joinable()` 상태이면 `std::terminate()`를 호출해 프로그램을 비정상 종료시킵니다. 반면 `std::jthread`는 소멸자에서 자동으로 정지를 요청하고 `join()`을 호출합니다.
- **협력적 정지(Cooperative Cancellation)**: `std::jthread`는 내부적으로 `std::stop_source`를 보유하며, 스레드 함수에 `std::stop_token`을 주입할 수 있습니다. 스레드 외부에서 `request_stop()`을 호출하면 `stop_token.stop_requested()`가 참이 되어 안전하게 루프를 탈출할 수 있습니다.

### `std::condition_variable_any::wait_for`와 `std::stop_token`
- 단순 `sleep_for()`는 대기 도중 정지 요청을 감지하지 못하지만, `std::condition_variable_any`의 `wait_for(lock, stop_token, period, pred)` 오버로드는 대기 중 `stop_token`에 정지가 요청되는 즉시 대기를 중단하고 반환합니다.

### Logger의 스레드 안전성 계약 (KI-014)
- `atugcc::core::Logger`는 내부 로그 히스토리 보호용 뮤텍스를 갖추고 있으나, 내부 링 버퍼(`RingBuffer::write`) 호출은 뮤텍스 밖에서 무잠금(single-thread 전용)으로 실행됩니다.
- 따라서 여러 스레드에서 동시에 하나의 `Logger` 객체를 직접 호출해서는 안 되며, 스레드마다 독립된 Logger를 사용하거나 외부에서 `std::mutex`로 동기화해야 합니다.

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
4. **단일 Logger의 안전한 공유 (KI-014 동기화 실습)**: 두 워커가 단일 `Logger` 인스턴스를 안전하게 공유하도록 코드를 변경해 보세요. `std::mutex`를 사용하여 `log` 호출을 감싸는 동기화 래퍼 함수(또는 람다)를 작성해 보고, 왜 현재 라이브러리 구조에서 이 동기화 래퍼가 필요한지 설명해 보세요. 주의: `PeriodicWorker`는 주입받은 `Logger`로 시작·종료 로그를 직접 남기므로, `task` 콜백 안의 `log`만 잠가서는 부족합니다. 워커에게는 공유 Logger 대신 같은 mutex로 감싼 경로만 쓰게 하거나(예: 워커 전용 Logger는 그대로 두고 공유 기록은 래퍼로), `PeriodicWorker`가 로그 함수를 받도록 바꿔 보세요.
