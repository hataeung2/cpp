# 레슨: `const`의 위치 — 멤버 함수, `mutable`, 반환 타입 (`const_correctness`)

`const`는 붙는 자리에 따라 뜻이 다릅니다. 멤버 함수 뒤의 `const`는 "이 함수는 객체를 바꾸지 않는다"는 약속이고, 값 반환 타입 앞의 `const`는 대부분 아무 도움이 안 되거나 이동을 막습니다. 이 레슨은 다섯 단계로 그 차이를 직접 출력합니다. `const` 멤버 함수, `mutable` 캐시, `const`/비`const` 오버로드와 그것을 하나로 합치는 C++23 deducing this, 복사·이동 횟수를 세는 타입으로 본 반환 타입의 `const`, 포인터의 `const`입니다. 설명 글: [const_return_type.md](/docs/cpp_evolution/const_return_type.md).

## 예전 방식과 C++23
| | 예전 방식 | 이 레슨의 방식 |
|---|---|---|
| 조회 함수 | `const`를 빼먹어 `const&`로 받은 객체에서 부를 수 없음 | 상태를 바꾸지 않는 함수는 모두 `const` |
| 캐시 | `const`를 빼거나 `const_cast` | `mutable` 멤버(스레드에서 함께 쓰면 잠금이나 atomic이 필요) |
| `const`/비`const` 두 벌 | 같은 본문을 두 번 쓰거나 `const_cast`로 한쪽을 다른 쪽에 위임 | C++23 deducing this: `auto& get(this auto& self, std::size_t i)` 하나 |
| 값 반환 | `const std::string name()`("호출자가 못 바꾸게") | `std::string name()`: `const`는 대입과 `push_back`에서 이동을 막음 |

## 실행
- 웹 플레이그라운드: 레슨 트리에서 선택 후 Run
- 로컬: `cmake --build --preset <preset> --target lesson_const_correctness` 후 `bin/lessons/lesson_const_correctness`, 또는 `ctest --preset <preset> -R lesson.const_correctness`

## 볼 것
- 1단계: `report(const Counter&)`는 `value()`만 부릅니다. `const&`로 받은 객체에서는 `const` 멤버 함수만 부를 수 있습니다.
- 2단계: `wordCount()`는 `const`인데 첫 호출 때 결과를 `mutable` 멤버에 저장하므로, 세 번 불러도 `computations = 1`입니다. 대신 `mutable`은 "`const` 함수는 여러 스레드가 동시에 불러도 된다"는 기대를 깹니다. 이 객체를 스레드끼리 공유하면 캐시를 잠금이나 `std::atomic`으로 보호해야 합니다.
- 3단계: 같은 `at(0)`이 비`const` 객체에서는 `int&`, `const&`에서는 `const int&`를 돌려줍니다. 컴파일러가 객체의 `const`로 오버로드를 고릅니다. 그 아래 `get`은 C++23 deducing this로 쓴 함수 하나입니다. `self`의 타입이 `Buffer&`나 `const Buffer&`로 추론되고, 반환 타입 `auto&`가 그 `const`를 그대로 따라갑니다.
- 4단계: 표를 보세요. 초기화(`Tracked a = makeConst();`)는 C++17의 보장된 복사 생략 때문에 `const`가 있어도 0입니다. 대입과 `push_back`에서는 `makeValue`가 이동, `makeConst`가 **복사**입니다. `const` 임시 객체는 `Tracked&&`에 묶이지 않아서 이동 연산을 고를 수 없기 때문입니다.
- 5단계: `const int*`는 가리키는 값이, `int* const`는 포인터 자신이 `const`입니다. 오른쪽에서 왼쪽으로 읽으면 됩니다("`p`는 `const int`를 가리키는 포인터").

rvalue 객체까지 다루는 deducing this(`this Self&& self`와 `std::forward_like<Self>(self.data_[i])`)는 MSVC에서는 빌드되지만, Linux 툴체인(Clang 20 + libstdc++ 14.2)에서는 `forward_like`가 컴파일 오류라서 레슨 코드에 넣지 않았습니다([KI-033](/docs/known_issues.md)).

```cpp
template <typename Self>
auto&& get(this Self&& self, std::size_t i) {
    return std::forward_like<Self>(self.data_[i]);   // Buffer&& 에서는 int&&
}
```

## 연습
1. 1단계 `report` 안의 `// c.increment();` 주석을 풀고 빌드해 보세요. 컴파일 오류 메시지에서 무엇이 `const`인지 읽고 되돌립니다.
2. 4단계의 `// const int makeInt() { return 1; }` 주석을 풀고 `main`에서 한 번 불러 보세요(부르지 않으면 쓰지 않는 함수라는 오류도 함께 납니다). Clang은 `-Wignored-qualifiers` 경고를 내고, 이 저장소는 경고를 오류로 다루므로 Linux 빌드가 실패합니다. MSVC는 어떤가요? 클래스 타입 `const Tracked`에는 왜 경고가 없을까요?
3. `get`의 반환 타입을 `auto&`에서 `auto`로 바꿔 보세요. `b.get(1) = 21;`이 왜 컴파일 오류가 되나요? MSVC를 쓸 수 있다면 위 코드처럼 `std::forward_like`로 rvalue 판을 만들어 `std::move(b).get(1)`의 타입을 확인해 보세요.
