# 레슨: 장비 상태 머신에 State 패턴 적용 (`device_state_machine`)

`jthread_worker` 유닛(`PeriodicWorker`)과 `atugcc::pattern::state`의 상태 머신, 그리고 `atugcc::pattern::viz::Tracer`를 결합하여 백그라운드 스레드가 장비 상태 머신을 주기적으로 구동하고 전이 이력을 시각화하는 레슨입니다.

## 1. 레슨 내용

이 레슨은 다음을 다룹니다:
- 현대 C++(C++20/C++23) 스타일의 State 패턴: `std::variant`와 `std::visit`, `overloaded` 패턴을 활용하여 가상 함수 상속과 동적 힙 할당 없이 상태 머신을 구성합니다.
- 백그라운드 `PeriodicWorker` 스레드가 주기적으로(25ms 간격) 상태 머신의 `schedule()`을 호출하고, 순차적으로 `IDLE -> STANDBY -> RUN` 전이를 수행합니다.
- 상태 전이 및 메시지 호출 흐름이 `viz::Tracer`에 자동으로 기록됩니다.
- **스레드 접근 단일성 보장**: 워커 스레드가 실행 중인 동안 `Machine`과 `Tracer`는 오직 워커 스레드 내부에서만 사용되며, 워커가 정지 및 조인(join)된 후에 메인 스레드가 안전하게 결과를 읽습니다.
- 워커 종료 후 터미널 ASCII 트레이스 출력(`tracer.formatTerminal()`)과 Mermaid 상태/시퀀스 다이어그램(`tracer.formatDiagram(viz::DiagramBackend::Mermaid)`)을 출력합니다.

## 2. 핵심 학습 개념

### `std::variant` 기반 State 패턴
- 기존 GoF State 패턴은 `IState` 인터페이스를 상속받은 구체 클래스들을 포인터(`std::shared_ptr` 등)로 관리하며 가상 함수를 통해 디스패치했습니다.
- `atugcc::pattern::state::Machine`은 `std::variant<IdleState, StandbyState, RunState, ...>`로 상태를 값(value)으로 보관합니다.
- `schedule()`과 상태 전이 규칙 검증(`isTransitionAllowed`)은 `std::visit`과 `overloaded` 구조체로 컴파일 타임에 분기되므로 vtable 오버헤드가 없고 메모리 단편화가 발생하지 않습니다.

### 전이 규칙(Transition Rules)의 동작 방식
- `Machine::transition(target)`은 전이 규칙 매트릭스 `isTransitionAllowed(current, target)`를 먼저 검사합니다.
- 중첩 `std::visit`을 통해 `(현재 상태, 목표 상태)` 쌍에 대한 전이 허용 여부가 명시적으로 정의되어 있습니다.
- 허용되지 않은 전이(예: `IDLE -> RUN`)를 시도하면 상태는 변경되지 않고 `core::CoreError::InvalidArgument`를 담은 `std::unexpected`가 반환됩니다.

### 멀티스레드 동기화와 소유권 분리
- 복잡한 락(mutex) 경합을 피하기 위해, 장비 상태 머신 객체와 트레이서 객체는 워커 스레드가 살아있는 동안 워커 스레드에 의해서만 단독 접근(exclusive access)됩니다.
- 메인 스레드는 `worker.requestStop()` 및 `worker.join()`으로 워커 스레드가 완전히 종료되었음을 확인한 뒤에만 트레이서와 상태 머신을 읽습니다.

## 3. 실행 방법

### ctest를 통한 실행 (Smoke Test)
```bash
ctest -R lesson.device_state_machine --output-on-failure
```

### 실행 바이너리 직접 실행
```bash
# Windows
bin\lessons\lesson_device_state_machine.exe
# 또는 Debug 설정인 경우
bin\Debug\lessons\lesson_device_state_machine.exe

# Linux
bin/lessons/lesson_device_state_machine
```

## 4. 연습 과제

1. **상태 전이 시퀀스 확장**: 워커 람다에서 RUN 상태 도달 이후(예: `tick == 4`) `machine.transition(state::AbortState{})` 또는 `machine.transition(state::EmergencyState{})`를 호출하여 비상 정지 상태로 전이해 보세요. 터미널 트레이스와 다이어그램에 새 전이가 어떻게 반영되는지 확인합니다.
2. **불허된 전이 처리 확인**: 워커 람다의 첫 번째 전이(`tick == 1`)에서 `IDLE`에서 곧바로 `RunState`로의 전이(`machine.transition(state::RunState{})`)를 시도해 보세요. `res`에 어떤 오류(`InvalidArgument`)가 반환되는지 확인하고 로그로 출력해 봅니다.
3. **다양한 다이어그램 백엔드 출력**: 메인 함수의 마지막 부분에서 `tracer.formatDiagram(viz::DiagramBackend::PlantUML)`과 `tracer.formatDiagram(viz::DiagramBackend::D2)`를 각각 호출하여 다양한 다이어그램 형식의 출력을 비교해 보세요.
