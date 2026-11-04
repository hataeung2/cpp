# 레슨: 다형성 — 가상 함수와 `std::variant` (`variant_visit`)

같은 도형 두 개(원, 직사각형)를 두 방식으로 씁니다. 하나는 기반 클래스 `Shape`와 가상 함수, `std::vector<std::unique_ptr<Shape>>`이고, 다른 하나는 기반 클래스 없는 `Circle`, `Rect`를 `std::variant<Circle, Rect>`에 담아 `std::visit`으로 다루는 방식입니다. 같은 출력을 낸 뒤, 새 연산(`perimeter`)을 더할 때와 새 타입을 더할 때 각 방식에서 어디를 고쳐야 하는지, variant를 들여다보는 함수들, 메모리 배치를 비교합니다. 라이브러리의 `state.hpp`가 같은 `overloaded` 도우미로 상태 머신을 만들고, 레슨 [`device_state_machine`](/lessons/tracks/02_patterns/01_device_state_machine/README.md)이 그것을 씁니다.

## 가상 함수와 `std::variant`
| | 가상 함수 계층 | `std::variant` + `std::visit` |
|---|---|---|
| 타입 목록 | 열려 있음: 누구나 `Shape`를 상속 | 닫혀 있음: `variant<Circle, Rect>`에 적힌 것만 |
| 새 연산 더하기 | 기반 클래스와 **모든** 파생 클래스를 고침 | visitor 하나를 새로 씀. 타입은 그대로 |
| 새 타입 더하기 | 파생 클래스 하나를 새로 씀 | `variant`에 타입을 더하면 빠진 경우가 있는 visitor가 **컴파일 오류**로 알려 줌 |
| 저장 | 요소마다 힙 할당(`std::make_unique`), 포인터 | 값 그대로, 힙 할당 없음 |
| 호출 | vtable을 거치는 간접 호출 | 판별자(`index()`)로 고르는 호출 |

## 실행
- 웹 플레이그라운드: 레슨 트리에서 선택 후 Run
- 로컬: `cmake --build --preset <preset> --target lesson_variant_visit` 후 `bin/lessons/lesson_variant_visit`, 또는 `ctest --preset <preset> -R lesson.variant_visit`

## 볼 것
- 1·2단계: 두 방식의 출력이 같습니다. 2단계의 `area`는 일반 람다(`[](const auto& s) { return s.area(); }`) 하나로, `name`은 타입마다 람다를 둔 `overloaded`로 방문합니다. `overloaded`는 람다들을 상속해 `operator()`를 모두 가져오는 세 줄짜리 도우미입니다.
- 3단계: `perimeter`를 더하는 데 `Circle`, `Rect`는 한 줄도 바뀌지 않았습니다. 가상 함수 쪽이라면 `Shape`에 순수 가상 함수를 더하고 두 파생 클래스를 모두 고쳐야 합니다.
- 4단계: `index()`는 지금 들어 있는 타입의 순서, `holds_alternative`는 그 타입인지, `get_if`는 맞으면 포인터·아니면 `nullptr`입니다. 틀린 타입으로 `std::get`을 부르면 `std::bad_variant_access`를 던집니다. 예외 메시지는 표준 라이브러리마다 달라서 출력하지 않습니다.
- 5단계: `variant`의 크기는 가장 큰 타입에 판별자를 더한 정도입니다(값은 플랫폼마다 다를 수 있음). `unique_ptr`는 포인터 하나 크기지만 요소마다 따로 할당한 객체가 힙에 있습니다.

## 연습
1. `struct Triangle { double base; double height; [[nodiscard]] double area() const { return 0.5 * base * height; } };`를 만들어 `std::variant<Circle, Rect, Triangle>`로 바꿔 보세요. `name`과 `perimeter`의 `overloaded` visitor는 컴파일 오류가 납니다. `area`의 일반 람다는 왜 오류가 나지 않나요? 그것은 장점인가요, 위험인가요?
2. 레슨 [`device_state_machine`](/lessons/tracks/02_patterns/01_device_state_machine/README.md)의 `uses` 탭에서 `state.hpp`를 열어, 상태 전이가 이 레슨의 2·3단계와 같은 방식(`std::variant`의 상태, `overloaded` visitor)으로 쓰였는지 찾아보세요.
3. 가상 함수 쪽에 `perimeter`를 더하려면 몇 곳을 고쳐야 하는지 세고, 실제로 더해 보세요.
