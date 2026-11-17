# 레슨: 상속과 가상 함수 — 가상 소멸자, 슬라이싱, 추상 클래스, `final` (`inheritance_virtual`)

상속은 "파생 클래스는 기반 클래스의 한 종류다"를 코드로 쓰는 방법이고, 가상 함수는 기반 클래스의 참조나 포인터로 부르더라도 **실제 객체의 함수**가 불리게 하는 장치입니다. 이 레슨은 여섯 단계로 확인합니다: 비가상 함수의 호출은 변수의 선언된 타입으로 정해지는 것(정적 결합), `virtual`과 `override`로 실제 타입의 함수가 불리는 것(동적 결합), 가상 소멸자가 있을 때의 소멸 순서, 값으로 받으면 파생 부분이 잘려 나가는 슬라이싱, 추상 클래스와 `std::vector<std::unique_ptr<Shape>>`로의 다형적 사용, `final`입니다. 기반 클래스 포인터로 `delete`했는데 소멸자가 가상이 아닌 경우(정의되지 않은 동작)는 이 레슨이 실행하지 않고, 특성(`std::has_virtual_destructor_v`)과 글로만 보입니다. 값 형식의 다형성(`std::variant`)과의 비교는 [variant_visit](/lessons/tracks/essentials/variant_visit/README.md)에 있습니다. 앞 레슨: [copy_and_move](/lessons/tracks/oop_basics/copy_and_move/README.md).

## 흔한 실수와 바른 방식
| | 흔한 실수 | 바른 방식 |
|---|---|---|
| 소멸자 | 기반 클래스 소멸자가 가상이 아니어서, 기반 포인터로 지우면 파생 소멸자가 안 불림(정의되지 않은 동작) | 기반 클래스에 `virtual ~Base()` |
| 오버라이드 | 시그니처를 조금 틀리게 써서 오버라이드가 아니라 **새 함수**가 됨 | `override`: 틀리면 컴파일 오류 |
| 값 전달 | 기반 클래스를 값으로 받아 파생 부분이 잘림(슬라이싱) | 참조나 포인터로 받음 |
| 인터페이스 | 기본 구현이 의미 없는데 빈 함수로 둠 | 순수 가상 함수 `= 0`: 추상 클래스는 객체를 만들 수 없음 |
| 더 이상 상속 안 함 | 누군가 상속해서 오버라이드를 바꿈 | `final` |

## 실행
- 웹 플레이그라운드: 레슨 트리에서 선택 후 Run
- 로컬: `cmake --build --preset <preset> --target lesson_inheritance_virtual` 후 `bin/lessons/lesson_inheritance_virtual`, 또는 `ctest --preset <preset> -R lesson.inheritance_virtual`

## 볼 것
- 1단계: `PlainDerived` 객체의 `name()`은 `PlainDerived::name`이지만, `PlainBase&`로 부르면 `PlainBase::name`입니다. 비가상 함수는 변수의 선언된 타입으로 정해집니다.
- 2단계: `sound()`를 `virtual`로 선언하고 `Dog`가 `override`하면 `Animal&`로 불러도 `woof`입니다. 오버라이드에는 `override`를 쓰세요: 기반 클래스에 같은 시그니처의 가상 함수가 없으면 컴파일러가 알려 줍니다.
- 3단계: `Resource`에 가상 소멸자가 있어서 `std::unique_ptr<Resource>`가 `FileResource`를 지울 때 `~FileResource`, `~Resource`가 차례로 불립니다(파생 → 기반). 가상 소멸자가 없으면 파생 소멸자가 불리지 않는 정의되지 않은 동작이 됩니다. 이 레슨은 그것을 실행하지 않고 `std::has_virtual_destructor_v`로 `Resource`는 `true`, `NonVirtualBase`는 `false`임을 보입니다. `override`를 쓰면 컴파일러가 파생 소멸자가 가상 소멸자를 오버라이드하는지 확인해 줍니다(연습 2). `virtual` 함수가 하나도 없는 클래스는 경고 없이 같은 위험에 빠질 수 있으니, 기반 클래스는 `virtual ~Base()`를 습관으로 씁니다.
- 4단계: `describeByValue(Animal)`는 `Dog`를 값으로 받으며 `Animal` 부분만 복사하므로 `...`가 나옵니다(슬라이싱, 정의된 동작). `describeByReference(const Animal&)`는 `woof`입니다.
- 5단계: `Shape`에는 순수 가상 함수가 있어서 `std::is_abstract_v<Shape>`가 `true`이고, `Shape s;`는 컴파일되지 않습니다. 구체 타입 `Circle`, `Square`를 `std::vector<std::unique_ptr<Shape>>`에 담으면 하나의 반복문이 서로 다른 타입을 다룹니다.
- 6단계: `Square`는 `final`이라 더 상속할 수 없고(`true`), `Circle`은 상속할 수 있습니다(`false`).

```cpp
class Shape {
public:
    virtual ~Shape() = default;                         // 가상 소멸자
    [[nodiscard]] virtual double area() const = 0;      // 순수 가상 함수
};
class Circle : public Shape {
public:
    [[nodiscard]] double area() const override;         // 오버라이드는 override
};
class Square final : public Shape { /* … */ };          // 더 이상 상속하지 않음
```

## 연습
웹의 연습 모드(기본)는 연습 사본을 고치고 원본(`lessons/`)은 그대로 둡니다. 아래의 "되돌립니다"는 웹에서는 ↺ 되돌리기, 로컬에서는 `py -3 tools/practice.py reset inheritance_virtual`입니다(로컬 연습: [`lessons/README.md`](/lessons/README.md)의 "연습 공간").

1. `Dog`의 `sound()`를 `soundd()`처럼 철자를 틀리게 고치고 빌드해 보세요. `override` 때문에 어떤 오류가 나나요? `override`를 지우면 어떻게 되나요(빌드는 되지만 2단계 출력이 어떻게 바뀌나요)? 되돌립니다.
2. `Resource`의 `virtual ~Resource()`에서 `virtual`을 지우고 빌드해 보세요. 오류가 나는 줄은 어디이고, `~FileResource() override`가 왜 오류가 되나요? (`override`까지 지우면 빌드가 되지만, `std::unique_ptr<Resource>`로 `FileResource`를 지우는 것은 정의되지 않은 동작이므로 **실행하지 마세요**.) 되돌립니다.
3. 5단계에서 `Shape` 객체(`Shape base;`)를 직접 만들어 보세요. 어떤 오류가 나고, 어느 함수가 순수 가상이라고 알려 주나요? 되돌립니다.
4. `Square`를 상속하는 클래스(`class BigSquare : public Square {};`)를 하나 만들어 보세요. 어떤 오류가 나나요? 되돌립니다.
