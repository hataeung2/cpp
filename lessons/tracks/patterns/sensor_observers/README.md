# 레슨: 센서 값 변경을 여러 수신부에 알리는 Observer 패턴 (`sensor_observers`)

장비의 센서 값이 바뀌면 여러 수신부(패널 화면, 알람 기록)가 그 사실을 알아야 합니다. 값을 가진 쪽(Subject)이 수신부를 하나하나 알지 않고도 알리는 구조가 Observer 패턴입니다. 이 레슨은 같은 알림을 두 방식으로 씁니다: 가상 함수 인터페이스와 날 포인터 목록(예전 방식), 그리고 concept와 `std::weak_ptr` 구독(라이브러리 [`observer.hpp`](/include/atugcc/pattern/observer.hpp)). 수신부 하나가 사라진 뒤 알림이 어떻게 바뀌는지는 `Tracer`의 기록과 다이어그램으로 봅니다. essentials의 [`concepts`](/lessons/tracks/essentials/concepts/README.md)와 oop_basics의 [`smart_pointers`](/lessons/tracks/oop_basics/smart_pointers/README.md)를 먼저 보면 좋습니다. concept 해설: [concepts.md](/docs/cpp_evolution/concepts.md).

## 예전 방식과 C++20

| | 예전 방식 (Step 1) | C++20 (Step 2–3) |
|---|---|---|
| 수신부의 모양 | `IObserver`를 상속하고 `update`를 `override` | 기반 클래스 없이 `onNotify`, `display`를 가진 타입. `ObserverOf` concept가 컴파일할 때 검사 |
| Subject가 들고 있는 것 | `std::vector<IObserver*>` (날 포인터) | 구독마다 `std::weak_ptr` 손잡이와 호출할 함수 |
| 수신부가 사라질 때 | 수신부가 먼저 `detach`해야 함. 잊으면 목록에 댕글링 포인터가 남고 다음 알림이 정의되지 않은 동작 | 아무것도 안 해도 됨. 다음 알림을 시작할 때 `expired()`로 걸러져 빠짐(`std::erase_if`). 알림 도중에 사라진 수신부는 자기 차례에 `lock()`이 실패해 건너뜀 |
| 잘못된 수신부 | 순수 가상 함수를 빼먹으면 추상 클래스 오류 | 멤버 함수가 없으면 `ObserverOf`를 만족하지 않는다는 오류 |

예전 방식의 위험(`detach`를 잊음)은 이 레슨에서 실행하지 않습니다. 결과가 정해져 있지 않은 동작이라서, Step 1은 `detach`를 빠뜨리지 않은 안전한 판입니다.

이 레슨은 `Subject::setData(d1, d2)`를 (센서 이름, 값 문자열)로 씁니다. 라이브러리의 `Subject`는 데이터 두 개(`data1()`, `data2()`)를 가진 교육용 구현이고, 수신부는 알림을 받을 때 그 값을 읽어 둡니다. `data1()`, `data2()`는 Subject 멤버의 `const` 참조를 돌려줍니다. 그 값은 다음 `setData`에서 바뀌고, 그 안을 가리키는 `std::string_view`는 무효가 될 수 있으므로 수신부는 문자열을 복사해 둡니다.

Subject는 구독자의 구체 타입을 모릅니다. 구독마다 수명만 보는 손잡이 `std::weak_ptr<void>`와 호출할 함수 두 개(`std::function`)를 들고, 구체 타입(`std::weak_ptr<PanelDisplay>` 등)은 `subscribe`가 만든 람다 안에만 있습니다(type erasure). 그래서 Subject는 수신부를 소유하지 않고, 수신부가 살아 있는지만 확인합니다.

## 실행
- 웹 플레이그라운드: 레슨 트리에서 선택 후 Run
- 로컬: `cmake --build --preset <preset> --target lesson_sensor_observers` 후 `bin/lessons/lesson_sensor_observers`, 또는 `ctest --preset <preset> -R lesson.sensor_observers`

## 볼 것
- **Step 1**: `legacy panel: temperature = 21.5`. 가상 함수 호출로 알림이 갑니다. 코드에서 `detach`가 수신부의 수명과 따로 놀고 있다는 점을 보세요.
- **Step 2**: 수신부 둘이 값을 두 번 받은 뒤의 `display()` 줄과 `receivers: 2`. `PanelDisplay`, `AlarmLog`에는 기반 클래스가 없고, `subscribe`가 `ObserverOf`로 검사합니다.
- **Step 3**: 패널은 Step 2의 블록을 벗어나며 사라졌습니다. 세 번째 값은 알람에만 가서 `alarm: 3 notification(s)`, `receivers: 1`이고, 지금까지 보낸 알림은 `messages sent: 5`(2 + 2 + 1)입니다. `detach`를 부르지 않았습니다.
- **Step 4**: `Tracer`가 기록한 알림 다섯 개와 Mermaid 시퀀스 다이어그램. 같은 수신자에게 연달아 간 알림은 `×2`처럼 한 줄로 합쳐집니다. 웹에서는 Diagrams 탭의 단계 재생으로 한 알림씩 볼 수 있습니다.
- 라이브러리의 `notifyObservers()`는 알림을 시작할 때의 구독자 목록 **사본**을 돕니다. 그래서 수신부가 알림을 받는 중에 새 구독자를 더하거나 다시 `setData`를 불러도 안전하고, 새 구독자는 다음 알림부터 받습니다.

## 연습
웹의 연습 모드(기본)는 연습 사본을 고치고 원본(`lessons/`)은 그대로 둡니다. 아래의 "되돌립니다"는 웹에서는 ↺ 되돌리기, 로컬에서는 `py -3 tools/practice.py reset sensor_observers`입니다(로컬 연습: [`lessons/README.md`](/lessons/README.md)의 "연습 공간").

1. **세 번째 수신부**: 기반 클래스 없이 `onNotify`와 `display`를 가진 수신부 타입(예: 값이 바뀔 때마다 켜지는 `FanControl`)을 하나 더 만들고, Step 2에서 구독하세요. `receivers: 3`이 나오면 됩니다. 되돌립니다.
2. **concept 오류 읽기**: `PanelDisplay`의 `display()` 함수를 지우고 빌드해 보세요. 어떤 줄이 어떤 이유로 실패하나요? 되돌립니다.
3. **수신부 수명 바꾸기**: Step 2 블록 밖에서 패널이 계속 살아 있게 하세요(블록의 `shared_ptr`을 블록 밖 변수에 복사). Step 3의 출력에 `panel: temperature = 30.0`이 나오면 됩니다. 되돌립니다.
