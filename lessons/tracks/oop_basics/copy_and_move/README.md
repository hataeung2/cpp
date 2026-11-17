# 레슨: 복사와 이동 — Rule of 0/5, `= delete` (`copy_and_move`)

객체를 함수에 넘기거나 다른 변수에 담을 때 C++는 복사하거나 이동합니다. 복사는 같은 값의 새 객체를 만들고, 이동은 원본의 내용을 새 객체로 넘기고 원본을 유효하지만 지정되지 않은 상태(대개 비어 있음)로 둡니다. 이 레슨은 복사·이동 횟수를 세는 타입(`Tracked`)으로 그 차이를 출력하고, 다섯 단계로 확인합니다: 값 전달에서 복사 / `std::move` / 임시 객체의 횟수, 자원을 가진 클래스를 기본 복사했을 때 소유자가 둘이 되는 문제(실제 해제는 하지 않고 소유자 수 카운터로 표현), Rule of 5로 직접 쓰기, Rule of 0으로 맡기기, 복사 금지입니다. 이동한 뒤의 객체는 "유효하지만 지정되지 않은 상태"이므로, 이 레슨은 레슨이 직접 정의한 타입의 이동 후 상태만 찍고 `std::string` 등 표준 타입의 이동 후 값은 찍지 않습니다. 앞 레슨: [object_lifetime](/lessons/tracks/oop_basics/object_lifetime/README.md).

## 흔한 실수와 바른 방식
| | 흔한 실수 | 바른 방식 |
|---|---|---|
| 자원을 가진 클래스 | 기본 복사(얕은 복사)로 같은 자원의 소유자가 둘이 됨 | 복사·이동을 직접 쓰거나(Rule of 5) 자원을 멤버에게 맡김(Rule of 0) |
| 특수 멤버 함수 | 소멸자만 쓰고 복사·이동은 잊음 | 다섯 개(소멸자, 복사 생성·대입, 이동 생성·대입)를 함께 정하거나 하나도 쓰지 않음 |
| 이동 | 이동 생성자에 `noexcept`가 없어 `std::vector`가 재할당할 때 복사함 | 이동 연산은 `noexcept` |
| 복사 금지 | 복사하면 안 되는 클래스를 문서로만 알림 | `= delete`로 컴파일러가 막음, `std::unique_ptr` 멤버가 있으면 저절로 그렇게 됨 |

## 실행
- 웹 플레이그라운드: 레슨 트리에서 선택 후 Run
- 로컬: `cmake --build --preset <preset> --target lesson_copy_and_move` 후 `bin/lessons/lesson_copy_and_move`, 또는 `ctest --preset <preset> -R lesson.copy_and_move`

## 볼 것
- 1단계: `takeByValue(a)`는 복사 1회, `takeByValue(std::move(a))`는 이동 1회, `takeByValue(makeTracked())`는 0회(C++17의 보장된 복사 생략), `takeByConstRef(a)`는 0회입니다. 값으로 받는 함수에 왼값을 주면 복사입니다.
- 2단계: `ShallowHandle`은 포인터만 가진 클래스입니다. 기본 복사 생성자가 포인터를 그대로 복사하고 "소유자 수"는 늘리지 않으므로 핸들이 둘인데 카운터는 1입니다. 둘이 사라지면 카운터가 `-1`이 됩니다: 같은 자원을 두 번 돌려준 것입니다. 실제 자원이었다면 이중 해제(정의되지 않은 동작)이므로 이 레슨은 카운터로만 보입니다.
- 3단계: `IntBox`는 `new`로 만든 `int`를 가지므로 다섯 특수 멤버 함수를 모두 씁니다. 복사는 **별도 저장소**를 만들고(`copy has its own storage: true`), 이동은 포인터를 넘기고 원본을 비웁니다(`moved-from IntBox is empty: true`). 이동 생성자가 `noexcept`라서 `std::vector<IntBox>`가 재할당할 때 원소를 복사하지 않고 이동합니다(`relocation used only moves: true`).
- 4단계: `Person`은 `std::string`과 `std::vector<int>` 멤버에게 자원을 맡겼으므로 특수 멤버 함수를 하나도 쓰지 않습니다(Rule of 0). 복사도 이동도 저절로 맞고, 이동 생성이 `noexcept`입니다.
- 5단계: `Ticket`은 복사를 `= delete`했고(`copyable: false`), `unique_ptr` 멤버를 가진 `Owner`는 아무것도 쓰지 않았는데 복사할 수 없고 이동할 수 있습니다.

```cpp
class Person {                       // Rule of 0: 특수 멤버 함수가 없다
    std::string name_;
    std::vector<int> scores_;
};
class Ticket {                       // 복사 금지, 이동만 가능
public:
    Ticket(const Ticket&) = delete;
    Ticket(Ticket&&) = default;
};
```

## 연습
웹의 연습 모드(기본)는 연습 사본을 고치고 원본(`lessons/`)은 그대로 둡니다. 아래의 "되돌립니다"는 웹에서는 ↺ 되돌리기, 로컬에서는 `py -3 tools/practice.py reset copy_and_move`입니다(로컬 연습: [`lessons/README.md`](/lessons/README.md)의 "연습 공간").

1. `Tracked`의 복사 생성자를 `Tracked(const Tracked&) = delete;`로 바꿔 빌드하고, 어느 줄이 오류를 내는지 읽으세요. 되돌립니다.
2. 1단계의 `takeByValue(std::move(a));` 바로 아래에서 `a.movedFrom()`을 출력해 보세요. 이동한 뒤의 `a`는 어떤 상태인가요? 이 레슨이 `std::string`의 이동 후 값은 찍지 않는 이유는 무엇인가요? 되돌립니다.
3. `IntBox`의 이동 생성자에서 `noexcept`를 지우고 3단계의 `relocation used only moves`를 보세요. 어떻게 바뀌나요? `std::vector`가 재할당 때 왜 복사를 고르나요? 되돌립니다.
