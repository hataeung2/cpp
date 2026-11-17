# 레슨: 스마트 포인터와 소유권 — `unique_ptr`, `shared_ptr`, `weak_ptr` (`smart_pointers`)

`Widget*` 같은 날 포인터만 보고는 그 객체를 누가 지워야 하는지 알 수 없습니다. 내가 지워야 하는지, 빌린 것인지, 이미 지워졌는지가 타입에 없기 때문입니다. 스마트 포인터는 이 **소유권**을 타입으로 씁니다. 이 레슨은 생성·소멸을 찍고 살아 있는 개수를 세는 타입으로 다섯 단계를 확인합니다: 단독 소유자 `std::unique_ptr`는 복사되지 않고 이동만 되는 것, 함수 시그니처가 소유권을 주는지·빌리는지·가져가는지를 말하는 것, `std::vector<std::unique_ptr<Widget>>`에서 원소를 지우거나 꺼낼 때, 공유 소유자 `std::shared_ptr`의 `use_count`와 마지막 소유자가 놓을 때의 소멸, 서로를 가리키는 두 객체의 순환을 `std::weak_ptr`로 끊는 것입니다. 날 포인터의 누수나 이중 해제는 실행하지 않고 글로만 보입니다. 앞 레슨: [object_lifetime](/lessons/tracks/oop_basics/object_lifetime/README.md)(5단계의 `new`/`delete`), [copy_and_move](/lessons/tracks/oop_basics/copy_and_move/README.md)(이동).

## 흔한 실수와 바른 방식
| | 흔한 실수 | 바른 방식 |
|---|---|---|
| 소유 | `new`로 만들고 `Widget*`로 넘김: 누가 `delete`하는지 타입에 없어 누수나 이중 해제 | `std::make_unique`와 `std::unique_ptr`: 스코프가 끝나면 지워짐 |
| 소유권 넘기기 | 날 포인터를 복사해 두 곳이 같은 객체를 지움 | `unique_ptr`는 복사 불가, `std::move`로만 넘김 |
| 함수 시그니처 | 모든 인자를 `Widget*`로 받음 | 빌리면 `const Widget&`, 가져가면 `std::unique_ptr<Widget>`(값), 만들어 주면 `std::unique_ptr<Widget>` 반환 |
| 다형적 컨테이너 | `std::vector<Widget*>`에 담고 끝에 하나씩 `delete` | `std::vector<std::unique_ptr<Widget>>`: 원소가 지워질 때 객체도 지워짐 |
| 공유 | 소유자가 하나인데 습관으로 `shared_ptr` | 기본은 `unique_ptr`, 소유자가 정말 여럿일 때만 `shared_ptr` |
| 순환 | 서로를 `shared_ptr`로 가리켜 아무도 지워지지 않음(누수) | 거꾸로 가리키는 쪽은 `std::weak_ptr` |

## 실행
- 웹 플레이그라운드: 레슨 트리에서 선택 후 Run
- 로컬: `cmake --build --preset <preset> --target lesson_smart_pointers` 후 `bin/lessons/lesson_smart_pointers`, 또는 `ctest --preset <preset> -R lesson.smart_pointers`

## 볼 것
- 1단계: `std::make_unique<Widget>("solo")`로 만든 객체의 소유자는 `owner` 하나입니다. `unique_ptr`는 복사할 수 없고(`false`, 연습 1), `std::move`로 `next`에게 소유권을 넘겨도 객체는 하나입니다(`alive widgets: 1`). 이동한 `owner`는 비어 있습니다: 이동 후 값이 지정되지 않는 대부분의 표준 타입과 달리 `unique_ptr`는 이동 후 `nullptr`로 정해져 있습니다(출력은 레슨 규칙대로 레슨이 정의한 타입의 상태만 찍습니다). `delete`를 쓰지 않았는데 블록이 끝나면 `~Widget solo`가 찍히고 `alive widgets: 0`입니다.
- 2단계: 시그니처가 소유권을 말합니다. `makeWidget`은 `std::unique_ptr<Widget>`를 돌려줘 소유권을 호출한 쪽에 주고, `show(const Widget&)`는 빌려서 쓸 뿐이며, `consume(std::unique_ptr<Widget>)`는 값으로 받아 소유권을 가져갑니다. 그래서 `~Widget parcel`은 `consume` 호출이 끝날 때(그 문장이 끝나기 전), `back in main` 줄보다 먼저 찍힙니다. `consume`에 넘기려면 `std::move(made)`가 필요하고, 넘긴 뒤 `made`는 비어 있습니다.
- 3단계: `std::vector<std::unique_ptr<Widget>>`에 `Widget`과 `Gadget`을 담으면 하나의 반복문이 `kind()`의 가상 호출로 둘을 구분합니다(`Gadget`의 소멸 줄도 기반의 `~Widget`이 찍습니다. `Widget`의 소멸자가 가상이라서 `unique_ptr<Widget>`가 `Gadget`을 바르게 지운다는 것은 [inheritance_virtual](/lessons/tracks/oop_basics/inheritance_virtual/README.md) 3단계가 출력으로 보입니다). `erase`는 원소와 함께 객체를 지우고(`~Widget a`), `std::move(crate.back())`로 꺼낸 객체는 `pop_back` 뒤에도 `taken`이 갖고 있습니다(소멸 줄 없음). `clear()`와 `reset()`이 남은 둘을 지웁니다.
- 4단계: `std::make_shared`로 만든 객체는 `shared_ptr`가 복사될 때마다 소유자가 늘어납니다: `use_count` 1 → 2 → 1. 마지막 소유자 `first`가 블록 끝에서 사라질 때 `~Widget shared`가 찍힙니다. 블록 밖의 `survivor`는 아무것도 갖지 않아 `use_count`가 0입니다. `survivor`에게 소유권을 하나 주면 수명이 블록을 넘어 늘어납니다(연습 2).
- 5단계: `Parent`는 `Child`를 `shared_ptr`로 소유하고, `Child`는 `Parent`를 `std::weak_ptr`로 바라만 봅니다. `weak_ptr`는 `use_count`에 들어가지 않으므로 `parent use_count: 1`이고(`child`는 지역 변수와 부모, 둘이 소유해서 2), 블록이 끝나면 `~Parent`, `~Child`가 차례로 찍힙니다. `watcher`도 `weak_ptr`라서 객체를 붙잡지 않고, 사라진 뒤에는 `expired()`가 `true`입니다. 쓸 때는 `lock()`으로 `shared_ptr`를 얻어 살아 있는지 확인합니다. `Child`도 `shared_ptr`로 가지면 순환이 생겨 블록이 끝나도 아무도 지워지지 않습니다(연습 3). 마지막의 `if` 블록은 그때 남은 순환을 `lock()`과 `adopt(nullptr)`로 손으로 끊어 누수 없이 끝내고, 원본에서는 `watcher`가 이미 비어 있어 돌지 않습니다(`alive at the end: 0`).

```cpp
[[nodiscard]] std::unique_ptr<Widget> makeWidget(std::string name);   // 소유권을 준다
void show(const Widget& widget);                                      // 빌린다
void consume(std::unique_ptr<Widget> widget);                         // 가져간다: consume(std::move(p))
class Child {
    std::weak_ptr<Parent> parent_;    // 거꾸로 가리키는 쪽은 weak_ptr: 순환이 생기지 않는다
};
```

## 연습
웹의 연습 모드(기본)는 연습 사본을 고치고 원본(`lessons/`)은 그대로 둡니다. 아래의 "되돌립니다"는 웹에서는 ↺ 되돌리기, 로컬에서는 `py -3 tools/practice.py reset smart_pointers`입니다(로컬 연습: [`lessons/README.md`](/lessons/README.md)의 "연습 공간").

1. 1단계의 `auto next = std::move(owner);` 아래에 `auto copy = next;`를 더하고 빌드해 보세요. 어떤 오류가 나고, `unique_ptr`는 왜 복사할 수 없게 만들어졌나요? 되돌립니다.
2. 4단계 블록 안의 `std::cout << "leaving the block\n";` 위에 `survivor = first;`를 더하고 실행해 보세요. `~Widget shared` 줄은 이제 언제 찍히나요? 되돌립니다.
3. `Child`의 멤버 `std::weak_ptr<Parent> parent_;`를 `std::shared_ptr<Parent> parent_;`로 바꾸고 실행해 보세요. 5단계의 `use_count`, 소멸 줄, `parent expired`, `alive parents and children`이 어떻게 바뀌나요? 되돌립니다.
