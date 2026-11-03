# 레슨: 오류 처리 — 예외와 `std::expected` (`error_expected`)

설정 줄 `port=8080`에서 포트를 읽는 같은 일을 두 방식으로 씁니다. 하나는 예외를 던지고(`parsePortThrowing`), 하나는 `atugcc::core::Expected`를 돌려줍니다(`parsePort`). 같은 입력 네 개로 결과를 나란히 보고, C++23의 `and_then`, `transform`, `or_else`로 단계를 잇습니다. 라이브러리 전체가 같은 타입(`core::Expected<T>`, `core::Result`, `core::CoreError`, [`error.hpp`](/include/atugcc/core/error.hpp))을 쓰므로, 이 레슨을 보면 라이브러리 함수의 반환값을 바로 읽을 수 있습니다. 해설: [error_expected.md](/docs/cpp_evolution/error_expected.md)(영어).

## 예외와 `std::expected`
| | 예외 | `std::expected<T, E>` (C++23) |
|---|---|---|
| 실패가 보이는 곳 | 함수 시그니처에 없음. 문서나 구현을 봐야 앎 | 반환 타입에 있음 |
| 처리하지 않으면 | 위로 올라가다 아무도 안 잡으면 `std::terminate` | 값을 꺼내기 전에 검사해야 함(`[[nodiscard]]`와 함께) |
| 단계 잇기 | `try` 하나에 여러 호출 | `and_then`(다음 단계도 실패할 수 있음), `transform`(값만 바꿈), `or_else`(실패를 다른 값이나 오류로) |
| 어울리는 곳 | 정말 예외적인 일, 생성자 실패 | 입력 검사, 파일 열기처럼 **예상할 수 있는** 실패 |

## 실행
- 웹 플레이그라운드: 레슨 트리에서 선택 후 Run
- 로컬: `cmake --build --preset <preset> --target lesson_error_expected` 후 `bin/lessons/lesson_error_expected`, 또는 `ctest --preset <preset> -R lesson.error_expected`

## 볼 것
- 1단계: `abc`와 빈 문자열은 `std::stoi`가 `invalid_argument`를, `70000`은 범위 검사가 `out_of_range`를 던집니다. 호출하는 쪽은 어떤 예외가 나올지 시그니처만 보고는 모릅니다.
- 2단계: 같은 입력이 `-> error InvalidArgument`로 나옵니다. 실패 이유는 값으로 돌아오고 `core::to_string`으로 출력합니다.
- 3단계: `port=80`은 파싱은 되지만 `requireUnprivileged`에서 실패합니다. `host=example`은 첫 단계 `valueOf`에서 실패하고, 그 뒤 단계는 불리지 않습니다. `or_else`를 붙인 마지막 줄은 실패 대신 기본 포트 8080을 씁니다.

## 연습
1. 1단계의 `catch (const std::out_of_range& e)` 절을 지우고 실행해 보세요. `70000`에서 무슨 일이 생기는지(웹에서는 종료 코드가 0이 아님) 보고, 예외가 시그니처에 보이지 않는다는 말을 설명해 보세요. 확인한 뒤 되돌립니다.
2. 3단계의 `transform` 람다가 `std::string` 대신 `core::Expected<std::string>`을 돌려주게 바꿔 보세요. 결과 타입이 어떻게 되는지, 그럴 때는 왜 `and_then`을 써야 하는지 확인하세요.
3. "포트 범위 밖"과 "숫자가 아님"을 구분해서 출력하고 싶다면 무엇을 바꿔야 할까요? `CoreError`는 라이브러리 공통 어휘라 레슨 하나를 위해 값을 더하지 않습니다. 레슨 안에 자기 오류 타입(`enum class PortError`)을 두고 `std::expected<std::uint16_t, PortError>`로 바꿔 보세요.
