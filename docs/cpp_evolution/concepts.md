# C++ Evolution: 템플릿 제약 (SFINAE → Concepts)

## Why
템플릿은 안쪽 어딘가에서 컴파일이 실패하기 전까지 어떤 타입이든 받아들입니다. 그러면 오류는 템플릿 본문 깊숙한 곳을 가리키고, 템플릿이 무엇을 요구하는지는 문서에만 적혀 있습니다. C++20 concepts는 요구 사항을 시그니처에 둡니다. 컴파일러가 호출하는 곳에서 검사하고, 만족하지 못한 요구 사항을 이름으로 알려 주며, 오버로드 중에서는 더 강하게 제약된 쪽을 고릅니다. atugcc는 observer의 요구 사항에 concept을, `RingBuffer`의 2의 거듭제곱 규칙에 `requires` 절을 씁니다.

레슨: [`concepts`](/lessons/tracks/01_essentials/06_concepts/README.md)(essentials 트랙).

## C++11/17 (Legacy): `std::enable_if`를 쓴 SFINAE
```cpp
template <typename T, std::enable_if_t<std::is_integral_v<T>, int> = 0>
T twiceSfinae(T x) { return x * 2; }

twiceSfinae(21);    // 42
twiceSfinae("x");   // error: no matching function ... candidate template ignored:
                    //        requirement 'std::is_integral_v<const char *>' was not satisfied (Clang 20)
```
- "치환 실패는 오류가 아니다(Substitution failure is not an error)": 시그니처에 잘못된 타입이 생기면 실패하는 대신 그 오버로드가 후보에서 빠집니다. `std::enable_if_t<cond, int> = 0`은 조건을 그런 실패로 바꿉니다.
- 조건이 템플릿 매개변수 안에 숨어 있습니다. 조건이 반대인 두 오버로드는 정확히 하나만 남도록 써야 하고, "더 구체적인 쪽"을 고르는 순서는 없습니다.
- 멤버(`x.size()`)가 있는지 검사하려면 `std::void_t`나 detection idiom 도우미가 필요합니다.

## C++20: concepts와 `requires`
```cpp
template <std::integral T>
T twice(T x) { return x * 2; }

template <typename T>
concept Shape = requires(const T& s) {
    { s.area() } -> std::convertible_to<double>;
    { s.name() } -> std::convertible_to<std::string_view>;
};

void printShape(const Shape auto& s);           // abbreviated function template

std::string_view describe(auto);                 // least constrained
std::string_view describe(std::integral auto);
std::string_view describe(std::signed_integral auto);   // chosen for -3: it subsumes std::integral

if constexpr (requires { x.size(); }) { /* x has size() */ }

template <std::size_t N>
    requires (std::has_single_bit(N))
struct FixedRing { static constexpr std::size_t kMask = N - 1; };
```
- **concept**은 타입에 대한, 이름 붙은 컴파일 시간 조건입니다. **requires 식**은 유효해야 하는 식들을 나열하고, `-> concept`으로 그 결과가 만족해야 할 조건을 적습니다.
- **제약을 두는 자리**: `template <std::integral T>`, 템플릿 머리나 선언자 뒤의 `requires` 절, 또는 매개변수의 `Concept auto`(축약 템플릿).
- **포섭(subsumption)**: 두 오버로드가 모두 맞으면, 제약이 상대의 제약을 함축하는 쪽이 이깁니다. 표준 concept을 통해서도 됩니다(`std::signed_integral`은 `std::integral<T> && std::is_signed_v<T>`로 정의되어 있습니다). 두 원자 제약은 소스의 같은 자리에 쓴 하나의 식에서 나왔을 때만 같은 것으로 치므로(글자가 같은 식을 두 번 쓴 것은 다른 제약입니다), 포섭에는 공유하는 concept이 필요합니다. `B`를 `A`로 정의하거나(`concept B = A<T> && ...`), 둘 다 공통 concept 위에 세웁니다(둘 다 `std::integral<T>`). 같은 조건을 서로 다른 두 concept에 따로 쓰면 대신 모호성 오류가 납니다.
- **`if constexpr (requires { ... })`**는 함수 안에서 한 번만 하는 검사에 detection idiom을 대신합니다.
- 오류는 호출하는 곳에서 concept과 실패한 요구 사항의 이름을 댑니다.

## C++23 (Current, atugcc)
- [`observer.hpp`](/include/atugcc/pattern/observer.hpp): `ObserverOf<T>`는 `onNotify(const Subject&)`와 `display()`를 요구합니다. `subscribe`는 `template <ObserverOf T>`를 받으므로, 그 멤버가 없는 observer는 `subscribe`를 호출하는 곳에서 빠진 멤버의 이름과 함께 실패합니다.
- [`ring_buffer.hpp`](/include/atugcc/core/ring_buffer.hpp): `RingBuffer`에는 `requires (BlockCount > 1 && (BlockCount & (BlockCount - 1)) == 0) && (BlockSize >= 4)`가 있습니다. 비트 기법 `(n & (n - 1)) == 0`은 "2의 거듭제곱"을 C++20 이전에 쓰던 방식입니다(0에서도 참입니다. `> 1`은 0과 1을 빼고, `has_single_bit`은 0만 뺍니다). C++20 `std::has_single_bit(n)`(`<bit>`)은 이를 이름으로 말하고, 레슨의 `FixedRing`이 이것을 씁니다.
- 새 코드는 `enable_if`보다 `concept`/`requires`를 씁니다([impl.md](/.agent/rules/impl.md) §1).
