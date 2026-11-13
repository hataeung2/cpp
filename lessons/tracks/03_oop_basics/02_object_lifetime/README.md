# 레슨: 객체의 수명 — 생성, 소멸, 임시 객체, RAII (`object_lifetime`)

C++의 객체는 만들어지는 순간과 사라지는 순간이 코드에 정해져 있습니다. 이 레슨은 생성과 소멸을 한 줄씩 출력하는 작은 타입(`Noisy`)으로 그 순간을 눈에 보이게 하고, 다섯 단계로 수명의 규칙을 확인합니다: 스코프가 수명을 정한다는 것, 기반 클래스와 멤버의 생성·소멸 순서, 임시 객체와 `const&`로의 수명 연장, 소멸자로 자원을 돌려주는 RAII 가드(예외가 나도 돌려줌), `new`/`delete`와 `std::unique_ptr`의 비교입니다. 자원(파일, 메모리)은 실제로 얻지 않고 출력 줄과 카운터로 표현해서, 이 레슨은 누수나 이중 해제를 일으키지 않습니다.

## 흔한 실수와 바른 방식
| | 흔한 실수 | 바른 방식 |
|---|---|---|
| 해제 | `new`와 `delete`를 직접 짝지음(사이에 `return`이나 예외가 있으면 누수) | 스코프가 수명을 정함: 지역 변수, `std::unique_ptr` |
| 순서 | 멤버가 초기화 목록에 쓴 순서로 만들어진다고 착각 | 선언한 순서로 만들고, 정확히 그 역순으로 소멸 |
| 자원 | 함수 끝에서 `close()`를 부르다가 중간 `return`이나 예외에서 빠뜨림 | RAII: 생성자에서 얻고 소멸자에서 돌려줌 |
| 임시 객체 | 임시 객체가 문장이 끝난 뒤에도 산다고 가정 | 문장 끝에서 사라짐, `const&`에 묶으면 그 참조의 스코프까지 |

## 실행
- 웹 플레이그라운드: 레슨 트리에서 선택 후 Run
- 로컬: `cmake --build --preset <preset> --target lesson_object_lifetime` 후 `bin/lessons/lesson_object_lifetime`, 또는 `ctest --preset <preset> -R lesson.object_lifetime`

## 볼 것
- 1단계: `+ outer`, `+ inner` 뒤 `- inner`, `- outer`. 스코프를 벗어나면 소멸자가 불리고, 같은 스코프의 객체는 만든 순서의 **역순**으로 사라집니다. `alive`가 이를 셉니다.
- 2단계: `Derived`는 `Base`를 상속하고 멤버 둘(`first_`, `second_`)을 갖습니다. 만드는 순서는 기반 클래스 `Base`의 멤버(출력의 `base`) → `Base`의 본문 → 멤버를 선언한 순서(`first`, `second`) → `Derived`의 본문이고, 소멸은 정확히 그 역순입니다(`construction order`와 `destruction order` 줄). 순서를 정하는 것은 **선언 순서**입니다.
- 3단계: `makeNoisy("temporary")`로 만든 임시 객체는 그 문장이 끝나면 곧바로 사라집니다(`alive after the statement: 0`). `const&`에 묶으면 그 참조가 있는 블록이 끝날 때까지 삽니다(`extended`). 함수가 지역 변수의 참조를 돌려주는 경우에는 이 연장이 적용되지 않습니다(README의 글로만: 이 레슨은 그 코드를 실행하지 않습니다).
- 4단계: `ScopedFile`은 생성자에서 `open`, 소멸자에서 `close`를 찍습니다. `process(0)`처럼 정상으로 끝나도, `process(1)`처럼 예외를 던져도 `close`가 한 번씩 찍히고(`guard summary: opened 2, closed 2`), 예외는 `catch`에 닿기 전에 지역 객체의 소멸자를 부릅니다(스택 되감기).
- 5단계: `new`로 만든 객체는 `delete`로 직접 지워야 합니다. 중간에 `return`이나 예외가 있으면 `delete`를 건너뛰어 누수가 되는데, 이 레슨은 바로 `delete`해서 실행하지 않습니다. `std::unique_ptr`는 스코프가 끝나면 알아서 소멸시키므로 그런 경로가 없습니다.

```cpp
class ScopedFile {
public:
    explicit ScopedFile(std::string path) { /* 자원을 얻는다 */ }
    ~ScopedFile() { /* 어느 경로로 나가든 돌려준다 */ }
    ScopedFile(const ScopedFile&) = delete;             // 복사하면 두 번 돌려주게 된다
    ScopedFile& operator=(const ScopedFile&) = delete;
};
```

## 연습
웹의 연습 모드(기본)는 연습 사본을 고치고 원본(`lessons/`)은 그대로 둡니다. 아래의 "되돌립니다"는 웹에서는 ↺ 되돌리기, 로컬에서는 `py -3 tools/practice.py reset object_lifetime`입니다(로컬 연습: [`lessons/README.md`](/lessons/README.md)의 "연습 공간").

1. `Derived`에서 `first_`와 `second_`의 **선언** 순서를 서로 바꾸고 2단계의 `construction order`와 `destruction order` 줄이 어떻게 바뀌는지 보세요. 되돌립니다.
2. `process`에 `if (stage == 2) { return; }`을 `ScopedFile` 선언 뒤에 더하고, 4단계에서 `process(2);`를 한 번 더 부르세요. 일찍 `return`해도 `close`가 찍히나요? `guard summary`의 두 숫자는 같은가요? 되돌립니다.
3. 3단계 첫 문장 `static_cast<void>(makeNoisy("temporary"));`를 `const Noisy& kept = makeNoisy("temporary");`로 바꾸고 `kept.name()`을 한 번 출력하세요(쓰지 않는 변수 경고를 피하기 위해). `alive after the statement`가 어떻게 바뀌나요? 소멸은 언제 일어나나요? 되돌립니다.
