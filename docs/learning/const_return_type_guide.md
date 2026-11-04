# C++ 함수 반환 타입의 `const`와 멤버 함수의 `const` 차이

C++에서 함수 시그니처에 `const` 키워드를 어디에 붙이느냐에 따라 그 의미와 동작이 완전히 달라집니다. 특히, 리턴 타입에 `const`를 붙이는 것(`virtual const bool hasNext()`)과 멤버 함수 뒤에 `const`를 붙이는 것(`virtual bool hasNext() const`)은 전혀 다른 결과를 가져옵니다.

## 1. 리턴 타입 앞의 `const` (예: `const bool`)

```cpp
virtual const bool hasNext() = 0;  // ❌ 피해야 할 패턴
```

위와 같이 리턴되는 원시 타입(Primitive Type: `bool`, `int` 등)에 `const`를 붙이는 것은 C++에서 **아무런 의미가 없습니다.**

### 이유는 무엇인가요?
원시 타입 값을 반환할 때는(Return-by-Value), 리턴된 값은 어차피 호출자 측에서 받는 일회용 임시 객체(rvalue)로 전달됩니다. 호출하는 쪽 코드에서 그 반환값을 일반 변수에 복사해서 담든, `const` 변수에 담든 전적으로 호출자의 자유입니다.

```cpp
bool a = iter->hasNext();        // 어차피 내 변수 a에 값을 복사함
const bool b = iter->hasNext();  // 내가 직접 const로 받으면 그만임
```

따라서 리턴 타입 자체에 `const`를 강제하는 것은 무의미하며, 엄격한 컴파일러(Clang·GCC의 `-Wall -Wextra`)는 `[-Wignored-qualifiers]`라는 경고를 냅니다. 이 저장소는 경고를 오류로 다루므로 빌드가 실패합니다.

### 클래스 타입에서는 이동을 막는다
`bool`에서는 이 경고가 문제의 전부지만, `std::string`이나 `std::vector` 같은 클래스 타입의 반환 타입에 `const`를 붙이면 경고 없이 성능 문제가 생깁니다. 다만 **어디에서** 생기는지는 정확히 알아야 합니다.

```cpp
const std::string makeName();

std::string a = makeName();   // 복사도 이동도 없음 (C++17 보장된 복사 생략)
a = makeName();               // 이동 대입 대신 복사 대입
names.push_back(makeName());  // 이동 생성 대신 복사 생성
```

- **초기화**(`std::string a = makeName();`): C++17부터 `return std::string{...};`처럼 prvalue를 돌려주면 반환 값이 곧 `a`가 됩니다(보장된 복사 생략). `const`가 붙어 있어도 복사도 이동도 일어나지 않습니다.
- **대입과 컨테이너에 넣기**: 이미 있는 객체에 넣을 때는 반환된 임시 객체에서 가져와야 하는데, 그 임시 객체가 `const`라서 이동 연산(`std::string&&`를 받음)을 고를 수 없고 복사 연산(`const std::string&`)이 불립니다. 문자열이나 벡터라면 **깊은 복사**입니다.

레슨 [`const_correctness`](/lessons/tracks/01_essentials/03_const_correctness/README.md) 4단계가 복사·이동 횟수를 세는 타입으로 이 비교를 표로 직접 출력합니다.

**결론:** 값 반환(Return-by-Value) 타입에는 `const`를 붙이지 않습니다. 원시 타입에서는 의미가 없고, 클래스 타입에서는 대입과 컨테이너 삽입에서 이동을 막습니다.

---

## 2. 함수 시그니처 뒤의 `const` (예: `hasNext() const`)

```cpp
virtual bool hasNext() const = 0;  // ✅ 올바른 패턴 (함수가 안전함)
```

만약 "이 함수는 객체 내부 상태를 수정하지 않는 안전한 함수다"라는 의도를 담고 싶다면, 리턴 타입의 앞쪽이 아니라 **함수 선언 맨 뒤**에 `const`를 붙여야 합니다.

### 이유는 무엇인가요?
함수 소괄호 `()` 뒤에 붙는 `const`는 **"이 멤버 함수를 호출하더라도 객체의 멤버 변수 데이터는 절대 변하지 않는다"**는 것을 컴파일러에게, 그리고 코드를 읽는 동료 개발자에게 보장하는 약속입니다.

만약 이 함수 구현부 안에서 실수로 멤버 변수의 값을 변경하려고 하면, 컴파일러가 강력하게 에러를 뿜어주어 버그를 미연에 방지합니다.

- 상태를 변화시키는 함수 (`setter`, 버퍼 갱신 등): `const` 없이 선언.
- 상태를 조회만 하는 함수 (`getter`, `hasNext()`, `isAvailable()` 등): 뒷부분에 반드시 `const`와 함께 선언.

`const` 멤버 함수, `mutable` 캐시, `const`/비`const` 오버로드(와 C++23 deducing this로 하나로 합치기)는 같은 레슨의 1–3단계에 있습니다.
