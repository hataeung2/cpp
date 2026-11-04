# 레슨: 템플릿 제약 — SFINAE에서 concepts로 (`concepts`)

템플릿은 아무 타입이나 받다가, 본문 깊은 곳에서 컴파일이 실패해야 비로소 "이 타입은 안 된다"고 알려 줍니다. C++20 concepts는 요구 사항을 시그니처에 씁니다. 이 레슨은 같은 제약을 `std::enable_if`(SFINAE)와 concept로 쓰고, requires 식으로 concept를 만들고, 축약 함수 템플릿(`const Shape auto&`), 가장 좁은 제약이 이기는 오버로드, `if constexpr (requires { … })`, 클래스 템플릿의 `requires` 절을 차례로 출력합니다. 라이브러리에서의 실제 쓰임은 `uses` 탭의 [`observer.hpp`](/include/atugcc/pattern/observer.hpp)(`ObserverOf`)와 [`ring_buffer.hpp`](/include/atugcc/core/ring_buffer.hpp)(`RingBuffer`의 `requires`)에서 읽습니다. 해설: [concepts.md](/docs/cpp_evolution/concepts.md)(영어).

## 예전 방식과 C++20
| | C++11/17 | C++20 |
|---|---|---|
| 제약 쓰기 | `template <typename T, std::enable_if_t<std::is_integral_v<T>, int> = 0>` | `template <std::integral T>`, `requires` 절, `std::integral auto` |
| 요구 사항 묶기 | 문서에만, 또는 `std::void_t` 검출 도우미 | `concept Shape = requires(const T& s) { … };` |
| 오버로드 고르기 | 조건이 서로 겹치지 않게 직접 맞춤 | 포함 관계(subsumption): 더 좁은 제약이 이김 |
| 멤버가 있는지 | 검출 관용구(detection idiom) | `if constexpr (requires { x.size(); })` |
| 오류 메시지 | 템플릿 본문 안이나 "후보 무시됨" | 호출한 곳에서, 만족하지 못한 concept와 요구 사항 이름 |

## 실행
- 웹 플레이그라운드: 레슨 트리에서 선택 후 Run
- 로컬: `cmake --build --preset <preset> --target lesson_concepts` 후 `bin/lessons/lesson_concepts`, 또는 `ctest --preset <preset> -R lesson.concepts`

## 볼 것
- 1단계: `twiceSfinae`와 `twice`는 같은 값을 냅니다. 다른 것은 제약이 어디에 보이느냐입니다. `enable_if`는 템플릿 매개변수 하나를 써서 조건을 숨기고, concept는 타입 자리에 이름으로 씁니다.
- 2단계: `Shape`는 "`area()`가 `double`로, `name()`이 `std::string_view`로 바뀌는 타입"입니다. `Circle`, `Square`는 공통 기반 클래스 없이 이 concept를 만족합니다. `Shape<int>`는 `false`이고, 같은 사실을 `static_assert`로도 둡니다.
- 3단계: `-3`에는 세 오버로드가 모두 맞지만, `std::signed_integral`이 `std::integral`을 포함하므로 가장 좁은 것이 골라집니다. `3u`는 `signed_integral`이 아니라서 `integral`, `2.5`는 제약 없는 `auto`입니다. 이 포함 관계는 표준 concept끼리 성립합니다. 직접 만든 concept 둘은 같은 concept를 공유할 때만(한쪽이 다른 쪽을 써서 정의하거나, 둘 다 `std::integral<T>` 같은 공통 concept 위에 만들 때) 포함 관계가 생기고, 같은 조건을 두 concept에 따로 쓰면 모호하다는 오류가 납니다.
- 4단계: `if constexpr (requires { x.size(); })`는 그 식이 컴파일되는지를 `bool`로 바꿉니다. `std::vector`에는 `size()`가 있고 `int`에는 없습니다. 거짓인 쪽은 인스턴스화되지 않으므로 `int`에서 `x.size()`를 써도 오류가 나지 않습니다.
- 5단계: `FixedRing<N>`은 `requires (std::has_single_bit(N))`로 2의 거듭제곱만 받습니다. 2의 거듭제곱일 때만 `index & (N - 1)`이 `index % N`과 같으므로, 이 제약이 마스크 계산을 올바르게 만듭니다. 라이브러리의 `RingBuffer`도 `requires` 절로 2의 거듭제곱을 검사하지만, C++20 이전 방식의 비트 식 `BlockCount > 1 && (BlockCount & (BlockCount - 1)) == 0`으로 쓰고 1도 거부합니다(`ring_buffer.hpp`의 `requires` 줄).

## 연습
1. `main`에 `printShape(42);`와 `twiceSfinae("x");`를 한 줄씩 더하고 빌드해 보세요. 두 오류 메시지를 비교하고, 가능하면 MSVC와 Clang의 메시지도 비교하세요. 어느 쪽이 무엇이 빠졌는지 더 바로 알려 주나요?
2. `observer.hpp`의 `ObserverOf`를 읽고, 같은 모양으로 `concept Printable`(`std::string toString() const`가 있는 타입)을 써서 `Circle`에 `toString()`을 더해 보세요. `static_assert(Printable<Circle>)`로 확인합니다.
3. `FixedRing<6>`을 만들어 보세요. 오류 메시지에서 어떤 제약이 만족되지 않았다고 나오나요? `RingBuffer<64, 6>`도 같은 이유로 실패하는지 확인하세요.
