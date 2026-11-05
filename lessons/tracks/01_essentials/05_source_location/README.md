# 레슨: 호출 위치 기록 (`source_location`)

로그 줄은 어디서 나왔는지 알려야 쓸모가 있습니다. 이 레슨은 같은 일을 네 단계로 바꿔 가며 보여 줍니다: `__FILE__`·`__LINE__` 매크로 → `std::source_location` 기본 인자 → 위치를 넘겨받는 래퍼 → 가변 인자에서 형식 문자열에 위치 붙이기. 마지막에 `atugcc::core::Logger`가 같은 방법으로 호출 줄을 기록하는 것을 봅니다. 해설: [source_location.md](/docs/cpp_evolution/source_location.md).

## 예전 방식과 C++20
| | 예전 (매크로) | C++20 (`std::source_location`) |
|---|---|---|
| 위치를 얻는 곳 | 매크로가 호출한 곳에서 `__FILE__`, `__LINE__`, `__func__`로 펼쳐짐 | 기본 인자 `std::source_location::current()`가 **호출한 곳에서** 계산됨 |
| 이름 공간, 오버로드 | 매크로는 둘 다 모름 | 보통 함수라 둘 다 됨 |
| 오류 메시지 | 매크로를 펼친 코드로 나옴 | 함수 이름으로 나옴 |
| 가변 인자 | `__VA_ARGS__` | 위치를 마지막 매개변수로 둘 수 없음 → 형식 문자열을 감싸는 타입에 붙임 |

## 실행
- 웹 플레이그라운드: 레슨 트리에서 선택 후 Run
- 로컬: `cmake --build --preset <preset> --target lesson_source_location` 후 `bin/lessons/lesson_source_location`, 또는 `ctest --preset <preset> -R lesson.source_location`

## 볼 것
- 1–4단계의 줄은 `[main.cpp:<줄> <함수>] ...` 모양입니다. `<줄>`은 그 단계의 **호출 줄**입니다. 에디터에서 줄 번호를 맞춰 보세요.
- 2단계의 두 줄은 줄 번호가 다릅니다. `startEngine()` 안에서 부른 줄은 `startEngine` 안의 줄이고, 함수 이름도 다르게 나옵니다(함수 이름 문자열은 컴파일러마다 다릅니다: MSVC는 `void __cdecl …`).
- 3단계의 `warning: low memory`는 `warn` 안의 줄이 아니라 `main`에서 `warn`을 부른 줄을 가리킵니다. `warn`이 받은 `loc`을 그대로 넘기기 때문입니다.
- 5단계의 Logger 줄은 파일의 전체 경로를 보여 줍니다. Logger는 경로를 줄이지 않습니다.

## 연습
1. `warn`의 `loc` 매개변수를 지우고 `logHere(std::format("warning: {}", msg))`만 부르게 바꿔 보세요. 3단계 줄의 번호가 어디로 바뀌는지 보고, 래퍼가 위치를 다시 받아야 하는 이유를 적어 보세요.
2. `logFormat`의 `Here<std::type_identity_t<Args>...>`를 `Here<Args...>`로 바꿔 컴파일해 보세요. 어떤 오류가 나는지, `std::type_identity_t`가 무엇을 막는지 설명해 보세요.
3. `logFormat("port {}", 8080, 9090);`처럼 인자 수가 맞지 않는 호출과 `logFormat("port {:d}", "x");`를 넣어 보세요. 어느 쪽이 컴파일 오류가 되고, 그 검사를 누가 하는지(`std::format_string`의 consteval 생성자) 확인하세요.
