# 레슨: 합성과 위임 — has-a 대 is-a, LSP (`composition`)

상속은 "파생 클래스는 기반 클래스의 한 종류다(is-a)"라는 약속이지 코드를 다시 쓰는 도구가 아닙니다. 코드를 다시 쓰고 싶을 때는 대개 그 클래스를 **멤버로 갖고(has-a) 일을 맡기는(위임)** 합성이 맞습니다. 이 레슨은 다섯 단계로 확인합니다: `std::vector<int>`를 상속한 스택에는 `insert`가 따라와 스택 밑에 값을 끼워 넣을 수 있는 것, `std::vector<int>`를 멤버로 가진 스택은 스택의 함수만 내놓는 것, `Car`가 `Engine`을 갖고 `start()`를 맡길 때 부분이 전체보다 먼저 만들어지고 나중에 사라지는 것, 수학에서는 맞는 "정사각형은 직사각형이다"를 상속으로 쓰면 리스코프 치환 원칙(LSP)이 깨지는 것, 그리고 그 바른 방식입니다. `std::vector`처럼 가상 소멸자가 없는 클래스를 기반 클래스 포인터로 지우는 것(정의되지 않은 동작)은 실행하지 않고 특성으로만 보입니다. 앞 레슨: [inheritance_virtual](/lessons/tracks/oop_basics/inheritance_virtual/README.md).

## 흔한 실수와 바른 방식
| | 흔한 실수 | 바른 방식 |
|---|---|---|
| 코드 재사용 | 함수 몇 개를 쓰려고 `public` 상속: 기반 클래스의 인터페이스가 모두 따라와 불변식을 깨는 길이 열림 | 합성: 멤버로 갖고, 필요한 함수만 내놓고 그 안에서 멤버에게 맡김(위임) |
| 표준 컨테이너 상속 | `class Stack : public std::vector<int>`: 가상 소멸자가 없어서 `std::vector<int>*`로 지우면 정의되지 않은 동작 | `std::vector<int>`를 멤버로 |
| is-a 판단 | 현실의 분류("정사각형은 직사각형")를 그대로 상속으로 씀 | 기반 클래스를 쓰는 코드가 믿는 약속을 파생 클래스가 모두 지킬 때만 상속(LSP) |
| 약속이 다른 두 타입 | `Square : Rectangle`에서 setter가 두 변을 함께 바꿔 `Rectangle`의 약속을 깸 | 서로 상속하지 않고, 둘 다 지킬 수 있는 약속(넓이, 이름)만 인터페이스로 나눔 |

## 실행
- 웹 플레이그라운드: 레슨 트리에서 선택 후 Run
- 로컬: `cmake --build --preset <preset> --target lesson_composition` 후 `bin/lessons/lesson_composition`, 또는 `ctest --preset <preset> -R lesson.composition`

## 볼 것
- 1단계: `InheritedStack`은 `push`, `pop`만 쓰려고 `std::vector<int>`를 `public` 상속했습니다. 그래서 `std::vector`의 `insert`도 `InheritedStack`의 함수이고, 1 2 3을 넣은 뒤 `insert(begin(), 99)`로 밑에 99를 끼워 넣을 수 있습니다. 꺼내는 순서는 `3 2 1 99`: 마지막에 들어간 99가 마지막에 나옵니다. 스택의 약속("나중에 넣은 것이 먼저 나온다")을 바깥 코드가 깰 수 있는 것입니다. `std::vector<int>`에는 가상 소멸자가 없어서(`false`) `std::vector<int>*`로 `InheritedStack`을 지우면 정의되지 않은 동작이 됩니다([inheritance_virtual](/lessons/tracks/oop_basics/inheritance_virtual/README.md) 3단계).
- 2단계: `Stack`은 `std::vector<int>`를 멤버 `items_`로 갖고, `push`, `pop`, `empty`, `size`만 내놓습니다. 각 함수는 `items_`에게 일을 맡깁니다(위임). 꺼내는 순서는 `3 2 1`이고, `insert`를 부를 길이 없습니다(연습 1). `std::is_base_of_v`로 `InheritedStack`은 `std::vector<int>`의 한 종류(`true`), `Stack`은 아님(`false`)을 봅니다.
- 3단계: `Car`는 `Engine`을 멤버로 갖고 `start()`를 `engine_.start()`에게 맡깁니다. 출력 순서 `Engine built`, `Car built`, …, `~Car`, `~Engine`: 멤버(부분)는 전체의 생성자 본문보다 먼저 만들어지고 전체의 소멸자 본문보다 나중에 사라집니다. 멤버로 갖는 has-a(합성)는 부분의 수명을 전체에 묶습니다. `Car`는 `Engine`의 한 종류가 아니므로 상속할 이유가 없습니다.
- 4단계: `broken::Square`는 `broken::Rectangle`을 상속하고, 네 변이 같다는 불변식을 지키려고 `setWidth`와 `setHeight`가 두 변을 함께 바꿉니다. `stretch(Rectangle&)`는 `Rectangle`의 약속(너비를 바꿔도 높이는 그대로)만 믿고 너비 5, 높이 4로 바꾸므로 넓이 20을 기대합니다. 직사각형은 `5 x 4, area 20`이지만 정사각형은 `4 x 4, area 16`입니다: `Rectangle&`를 받는 코드에 `Square`를 넣으니 그 코드가 믿는 약속이 깨졌습니다. 이것이 **리스코프 치환 원칙(LSP)** 위반입니다: 기반 클래스를 쓰는 코드는 파생 클래스를 넣어도 그대로 맞아야 합니다. 정의된 동작이고 컴파일러도 경고하지 않는, 설계의 버그입니다. 반대로 고치면(연습 3) 정사각형이 아니게 됩니다.
- 5단계: `fixed::Rectangle`과 `fixed::Square`는 서로 상속하지 않고, 둘 다 지킬 수 있는 약속(`area`, `name`)만 추상 클래스 `Shape`로 나눕니다. `Square`에는 변 하나를 바꾸는 `setSide`만 있어서 불변식을 깨는 함수가 처음부터 없고, `fixed::Square`는 `fixed::Rectangle`의 한 종류가 아닙니다(`false`). 그래서 `fixed::Rectangle&`를 받는 함수(4단계의 `stretch` 같은)에 `fixed::Square`를 넘기면 컴파일 오류이고, `Shape`에는 잘못 쓸 너비·높이 setter가 없습니다.

```cpp
class Stack {                                  // 상속하지 않고
public:
    void push(int value) { items_.push_back(value); }   // 필요한 함수만 내놓고 멤버에게 맡긴다
private:
    std::vector<int> items_;                   // has-a
};
class Shape {                                  // 둘 다 지킬 수 있는 약속만
public:
    virtual ~Shape() = default;
    [[nodiscard]] virtual int area() const = 0;
};
class Rectangle final : public Shape { /* setWidth, setHeight */ };
class Square final : public Shape { /* setSide */ };
```

## 연습
웹의 연습 모드(기본)는 연습 사본을 고치고 원본(`lessons/`)은 그대로 둡니다. 아래의 "되돌립니다"는 웹에서는 ↺ 되돌리기, 로컬에서는 `py -3 tools/practice.py reset composition`입니다(로컬 연습: [`lessons/README.md`](/lessons/README.md)의 "연습 공간").

1. 2단계의 `stack.push(3);` 아래에 `stack.insert(stack.begin(), 99);`를 더하고 빌드해 보세요. 1단계의 `leaky.insert(…)`는 되는데 이 줄은 왜 오류인가요? 되돌립니다.
2. `class InheritedStack : public std::vector<int>`의 `public`을 `private`로 바꾸고 빌드해 보세요. 오류가 나는 줄은 어디이고, `insert`와 함께 막힌 함수 가운데 스택에도 필요한 것은 무엇인가요? 되돌립니다.
3. `broken::Square`의 `setHeight` 오버라이드를 지우고 실행해 보세요. 4단계의 `square:` 줄과 `still a square` 줄이 어떻게 바뀌고, 이번에는 무엇이 깨졌나요? 되돌립니다.
