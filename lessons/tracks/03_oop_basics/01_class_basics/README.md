# 레슨: 클래스와 캡슐화 — 불변식, 초기화, `explicit` (`class_basics`)

클래스는 "데이터와 그 데이터를 다루는 규칙"을 한 덩어리로 묶는 도구입니다. 이 레슨은 변수, 함수, 반복문, `struct`는 아는 사람이 클래스를 처음 쓸 때 가장 자주 하는 실수를 다섯 단계로 출력해서 보여 줍니다: `struct`와 `class`의 접근 차이, 모든 멤버를 `public`으로 두어 깨지는 불변식, 본문에서 대입하는 초기화, 한 인자 생성자의 암시적 변환, `const` 멤버 함수입니다. 이 트랙은 C++의 기초 문법(변수, 제어문, 포인터)은 가르치지 않습니다.

## 흔한 실수와 바른 방식
| | 흔한 실수 | 바른 방식 |
|---|---|---|
| 접근 | 모든 멤버를 `public`으로 두어 아무나 값을 바꿈 | 데이터는 `private`, 멤버 함수가 불변식(잔액은 음수가 아님)을 지킴 |
| 초기화 | 생성자 본문에서 대입, 초기화하지 않은 멤버 | 생성자 초기화 목록과 멤버 기본값 |
| 변환 | 한 인자 생성자 때문에 `double`이 조용히 클래스가 됨 | `explicit` |
| 조회 | `const`를 빼먹어 `const&`로 받은 객체에서 못 부름 | 바꾸지 않는 함수는 `const` 멤버 함수 ([const_correctness](/lessons/tracks/01_essentials/03_const_correctness/README.md)) |

## 실행
- 웹 플레이그라운드: 레슨 트리에서 선택 후 Run
- 로컬: `cmake --build --preset <preset> --target lesson_class_basics` 후 `bin/lessons/lesson_class_basics`, 또는 `ctest --preset <preset> -R lesson.class_basics`

## 볼 것
- 1단계: `struct`의 멤버는 기본이 `public`, `class`의 멤버는 기본이 `private`입니다. 같은 `value_`가 `OpenBox`에서는 밖에서 보이고(`true`), `ClosedBox`에서는 보이지 않습니다(`false`). 기본 접근(상속할 때의 기본 접근 포함)이 두 키워드의 유일한 차이입니다.
- 2단계: `LooseAccount`는 멤버가 `public`이라 100에서 150을 빼 `-50`이 되는 것을 아무도 막지 못합니다. `Account`는 `balance_`를 `private`으로 감추고 `withdraw`가 "잔액보다 많이 뺄 수 없다"는 불변식을 지킵니다. 어긴 요청은 상태를 바꾸지 않고 `core::Expected`의 오류(`InvalidArgument`)로 돌아옵니다([error_expected](/lessons/tracks/01_essentials/04_error_expected/README.md)).
- 3단계: 초기화 목록은 멤버를 처음부터 원하는 값으로 만듭니다(`ByList`: `Part(first)`, `Part(second)` 두 줄). 본문에서 대입하면 멤버가 먼저 기본값으로 만들어진 뒤 다시 대입되어 일이 두 배입니다(`ByBody`). 목록에 없는 멤버는 선언의 기본값을 씁니다(`Config()`는 `retries=3`). 멤버는 **선언한 순서**대로 초기화되고, 초기화 목록에 쓴 순서는 상관없습니다.
- 4단계: `Feet(double)`은 `explicit`이 없어서 `showFeet(3.5)`가 조용히 `Feet`로 바꿔 줍니다(`double -> Feet implicit conversion: true`). `Meters`는 `explicit`이라 `Meters{3.5}`로 써야 합니다(`false`). 의도하지 않은 변환을 막는 것이 `explicit`의 일입니다.
- 5단계: `report(const Account&)`는 `balance()`만 부릅니다. `const&`로 받은 객체에서는 `const` 멤버 함수만 부를 수 있습니다.

```cpp
class Account {
public:
    explicit Account(long opening) : balance_(opening) {}
    [[nodiscard]] core::Expected<long> withdraw(long amount);   // 불변식을 지킨다
    [[nodiscard]] long balance() const { return balance_; }     // 읽기만 한다
private:
    long balance_ = 0;                                          // 밖에서는 못 건드림
};
```

## 연습
웹의 연습 모드(기본)는 연습 사본을 고치고 원본(`lessons/`)은 그대로 둡니다. 아래의 "되돌립니다"는 웹에서는 ↺ 되돌리기, 로컬에서는 `py -3 tools/practice.py reset class_basics`입니다(로컬 연습: [`lessons/README.md`](/lessons/README.md)의 "연습 공간").

1. `Meters`의 생성자에서 `explicit`을 지우고 4단계 출력을 보세요. `double -> Meters implicit conversion`이 어떻게 바뀌나요? 이제 `showMeters(3.5);`는 컴파일되나요? 되돌립니다.
2. `ByList`의 초기화 목록에서 `first_`와 `second_`를 쓴 순서를 서로 바꿔 빌드해 보세요. 컴파일러가 무엇을 경고하나요(Clang은 `-Wreorder`)? 이 저장소는 경고를 오류로 다루므로 Linux 빌드가 실패합니다. MSVC는 어떤가요? 초기화는 실제로 어느 순서로 일어나나요? 되돌립니다.
3. `LooseAccount`의 `struct`를 `class`로 바꿔 빌드하고, 오류 메시지가 어느 줄을 가리키며 무엇이 접근할 수 없다고 하는지 읽으세요. 되돌립니다.
