# 유닛: lambda_capture

람다는 캡처한 것을 멤버로 가진 이름 없는 클래스의 객체입니다. 캡처 방식에 따라 그 멤버가 **사본**인지 **원본을 가리키는 참조**인지가 정해집니다.

| 함수 | 캡처 | closure가 가진 것 | 주의할 점 |
|---|---|---|---|
| `makeCounterByValue(start)` | `[count = start]` + `mutable` | `count`의 사본 | 원본 변수와 무관하게 자기 값만 바뀝니다 |
| `makeAdderByReference(total)` | `[&total]` | `total`에 대한 참조 | 람다가 `total`보다 오래 살면 dangling reference가 됩니다 |
| `makeGreeter(name)` | `[name = std::move(name)]` | 이름 문자열(옮겨 온 것) | 인자는 값으로 받고 closure 안으로 move합니다 |
| `makeOwner(value)` | `[value = std::move(value)]` | `unique_ptr` | closure가 move-only가 됩니다. `std::function`에는 담을 수 없고 `std::move_only_function`(C++23)에는 담을 수 있습니다 |

사용하는 레슨: `lambda_capture` (essentials 트랙).
