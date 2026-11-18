# 레슨: 값 의미론과 연산자 — `operator<=>`, 연산자 오버로딩 (`value_semantics`)

`int`는 복사하면 서로 독립이고, `==`와 `<`로 값을 비교할 수 있습니다. 직접 만든 타입도 이렇게 **값처럼** 다룰 수 있게 만들 수 있고(값 의미론), 그러려면 복사와 비교, 필요한 연산자를 갖춰야 합니다. 이 레슨은 다섯 단계로 확인합니다: 값 타입의 복사는 독립이고 같음은 값으로 정하는 것(`== = default`), 두 `shared_ptr`가 한 객체를 나누는 참조 의미론과의 차이, 비교 연산자 여섯 개를 직접 쓸 때 하나가 틀려 여섯이 서로 맞지 않는 실수, `operator<=>`를 `= default`로 두어 여섯을 한 번에 얻는 방법과 정렬, 멤버별 비교가 뜻과 다른 분수에서 `<=>`와 `==`를 직접 쓰는 방법, 그리고 `+=`, `+`, `<<` 같은 연산자를 언제 어떻게 오버로딩하는지입니다. 앞 레슨: [copy_and_move](/lessons/tracks/oop_basics/copy_and_move/README.md)(복사와 이동), [smart_pointers](/lessons/tracks/oop_basics/smart_pointers/README.md)(`shared_ptr`).

## 흔한 실수와 바른 방식
| | 흔한 실수 | 바른 방식 |
|---|---|---|
| 같음 | 멤버를 하나씩 비교하는 `==`를 손으로 씀(멤버를 더하면 잊음) | `bool operator==(const T&) const = default;` |
| 순서 | `==`, `!=`, `<`, `<=`, `>`, `>=` 여섯 개를 직접 써서 하나가 틀리면 서로 맞지 않음 | `auto operator<=>(const T&) const = default;`: 여섯 개가 멤버의 선언 순서대로 |
| 뜻이 다른 비교 | 같은 값을 여러 표현으로 쓰는 타입(1/2, 2/4)에 기본 비교 | `<=>`와 `==`를 같은 기준으로 직접 씀, 동등하지만 같지 않으면 `std::weak_ordering` |
| `<=>`를 직접 쓸 때 | `<=>`만 쓰고 `==`도 생긴다고 기대함 | `==`도 직접 씀(`!=`는 저절로) |
| 산술 연산자 | `+`와 `+=`를 따로 구현해 규칙이 두 곳에 | `+=`는 멤버, `+`는 `+=`를 쓰는 비멤버 |
| 출력 | `print()` 같은 멤버 함수 | `std::ostream& operator<<(std::ostream&, const T&)` |

## 실행
- 웹 플레이그라운드: 레슨 트리에서 선택 후 Run
- 로컬: `cmake --build --preset <preset> --target lesson_value_semantics` 후 `bin/lessons/lesson_value_semantics`, 또는 `ctest --preset <preset> -R lesson.value_semantics`

## 볼 것
- 1단계: `Point b = a;`는 새 `Point`를 만들어서 `b.x = 10`은 `a`를 바꾸지 않습니다(`a: (1, 2)`). `Point`의 `==`는 `= default`라서 멤버를 모두 비교하고, `b = a` 뒤에는 `true`입니다: 같음은 주소가 아니라 값으로 정합니다. 반대로 `std::shared_ptr<Point>` 두 개 `p`, `q`는 **한 객체를 나누므로** `q->x = 10`이 `*p`에서도 보입니다(참조 의미론, 연습 1).
- 2단계: `OldDate`는 비교 연산자 여섯 개를 직접 썼는데 `operator<`가 `day`를 잊었습니다. 2026-11-17과 2026-11-18은 `!=`가 `true`인데 `<`도 `>`도 `false`이고, `<=`와 `>=`가 모두 `true`입니다: `<`, `<=`, `>`, `>=` 넷은 "같다"고 하고 `==`, `!=`는 "다르다"고 해서 서로 맞지 않습니다. 정의된 동작이고 컴파일러도 경고하지 않습니다. `std::sort`와 `std::map`은 `<`만 쓰므로 같은 달의 다른 날을 같은 것으로 다룹니다: `std::map`에 11-17이 있으면 11-18은 같은 키로 보여 들어가지 않습니다(이 레슨은 그것을 실행하지 않습니다).
- 3단계: `Date`는 `auto operator<=>(const Date&) const = default;` 한 줄로 여섯 연산자를 모두 얻습니다. 멤버를 **선언 순서대로**(`year`, `month`, `day`) 비교하므로 2단계와 같은 두 날짜가 `<`에서 `true`, `>`에서 `false`로 서로 맞고, `std::ranges::sort`가 날짜 순서로 정렬합니다. 기본 `<=>`는 기본 `==`도 함께 선언합니다.
- 4단계: `Fraction`은 1/2과 2/4가 같은 값이지만 멤버는 다릅니다. 그래서 `<=>`를 직접 써서 `a/b`와 `c/d`를 `a*d`와 `c*b`로 비교하고, 결과 타입은 `std::weak_ordering`입니다: `std::strong_ordering`의 "같다"(equal)는 어디에 써도 바꿔 넣을 수 있다는 뜻인데, 1/2과 2/4는 `<<`로 찍으면 다르게 나오므로 **동등**(equivalent)할 뿐입니다(`is equivalent: true`). 이 레슨의 `==`가 묻는 것은 "같은 값인가"이고, 그것이 동등입니다. `<=>`를 직접 쓰면 `==`는 생기지 않으므로 같은 기준으로 `==`도 씁니다(연습 3). 기본 비교로 바꾸면 결과가 틀립니다(연습 2).
- 5단계: 산술 연산자는 `int`와 같은 뜻일 때만 오버로딩합니다. `+=`는 자기 값을 바꾸는 멤버로, `+`는 왼쪽 피연산자를 값으로 받아 `+=`를 쓰는 비멤버(`friend`)로 써서 덧셈의 규칙이 한 곳에만 있습니다. 1/2 + 1/4는 `6/8`(약분하지 않음)이고, 4단계의 `==` 덕분에 `6/8 == 3/4`는 `true`입니다. `operator<<`는 `std::cout << half`처럼 출력에 씁니다. 뜻이 놀라운 연산자(예: 두 날짜의 `+`)는 오버로딩하지 않고 이름 있는 함수로 둡니다.

```cpp
struct Date {
    int year = 0;
    int month = 0;
    int day = 0;
    [[nodiscard]] auto operator<=>(const Date&) const = default;   // 여섯 비교, 멤버 순서대로
};
class Fraction {
public:
    [[nodiscard]] std::weak_ordering operator<=>(const Fraction& other) const;   // 뜻이 다르면 직접
    [[nodiscard]] bool operator==(const Fraction& other) const;                  // == 도 직접
    Fraction& operator+=(const Fraction& other);
    friend Fraction operator+(Fraction left, const Fraction& right);             // += 로 만든다
};
```

## 연습
웹의 연습 모드(기본)는 연습 사본을 고치고 원본(`lessons/`)은 그대로 둡니다. 아래의 "되돌립니다"는 웹에서는 ↺ 되돌리기, 로컬에서는 `py -3 tools/practice.py reset value_semantics`입니다(로컬 연습: [`lessons/README.md`](/lessons/README.md)의 "연습 공간").

1. 1단계의 `Point b = a;`를 `Point& b = a;`로 바꾸고 실행해 보세요. `b.x = 10`이 이제 무엇을 바꾸고, `a == b` 줄은 어떻게 되나요? 되돌립니다.
2. `Fraction`의 `operator<=>`와 `operator==`를 지우고 `[[nodiscard]] auto operator<=>(const Fraction&) const = default;` 한 줄로 바꾼 뒤 실행해 보세요. 4단계와 5단계의 어느 값이 바뀌고, 왜 틀린 답인가요? 되돌립니다.
3. `Fraction`의 `operator==`만 지우고 빌드해 보세요. `<` 줄은 되는데 `==` 줄은 왜 오류인가요? 되돌립니다.
