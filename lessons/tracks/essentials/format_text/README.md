# 레슨: 텍스트 포맷팅 — `std::format` (`format_text`)

숫자, 표, 로그 줄처럼 모든 프로그램이 글자를 만듭니다. 이 레슨은 `std::format`(C++20)과 `std::print`(C++23)의 기능을 일곱 단계로 출력해 봅니다: 위치 인자, 폭·채움·정렬, 진법과 정밀도, 사용자 타입의 `std::formatter`, 버퍼에 이어 쓰기(`std::format_to`), 실행 시간에 받은 형식 문자열(`std::vformat`), 스트림에 바로 출력하기(`std::print`/`std::println`). `atugcc::core::Logger::log`도 `std::format_string`을 받으므로([`logger.hpp`](/include/atugcc/core/logger.hpp), 이 레슨은 Logger를 쓰지 않고 위치만 보여 줍니다), 여기서 본 형식이 그대로 로그에 쓰입니다. 해설: [format.md](/docs/cpp_evolution/format.md).

## 예전 방식과 C++20/23
| | `printf` | `iostream` | `std::format` (C++20) | `std::print` (C++23) |
|---|---|---|---|---|
| 타입 검사 | 없음(틀리면 정의되지 않은 동작) | 있음 | 있음, 형식 문자열까지 **컴파일 시간**에 | `std::format`과 같음 |
| 표 한 줄 | 짧음(`%-10s%6d`) | 조작자 여러 개, 일부는 스트림에 남음(`std::fixed`) | 짧음(`{:<10}{:>6}`) | 같음, 스트림에 바로 출력 |
| 사용자 타입 | 먼저 문자열로 바꿔야 함 | `operator<<` | `std::formatter<T>` 특수화 | 같음 |
| 순서 바꾸기(번역) | 표준 C에는 없음(POSIX의 `%1$s`) | 안 됨 | `{1} {0}` | 같음 |

7단계는 C++23 `<print>`의 `std::print`와 `std::println`을 씁니다. 두 툴체인(MSVC, Linux의 Clang 20 + libstdc++ 14) 모두에서 지원됩니다.

## 실행
- 웹 플레이그라운드: 레슨 트리에서 선택 후 Run
- 로컬: `cmake --build --preset <preset> --target lesson_format_text` 후 `bin/lessons/lesson_format_text`, 또는 `ctest --preset <preset> -R lesson.format_text`

## 볼 것
- 1단계: `{0}`을 두 번 써서 같은 인자를 다시 씁니다(`idle -> run -> idle`).
- 2단계: 제목 줄과 구분선(`{:-<10}`, 채움 글자 `-`)과 세 행이 같은 폭으로 맞습니다. 숫자는 오른쪽, 이름은 왼쪽 정렬입니다.
- 3단계: `{:#x}`는 `0xff`, `{:#o}`는 `0377`, `{:012b}`는 폭 12를 0으로 채운 `000011111111`입니다. `{:>12.2f}`는 폭 12에 소수 둘째 자리까지입니다.
- 4단계: `Vec2`의 `{:.1}`은 `(1.5, -2.2)`입니다. `-2.25`가 `-2.3`이 아닌 이유: 2.25는 2진수로 정확히 표현되고, 반올림은 가장 가까운 짝수 쪽(round-half-to-even)입니다.
- 5단계: `std::format_to`가 같은 `std::string` 뒤에 세 번 이어 씁니다.
- 6단계: 실행 시간 문자열은 `std::vformat`으로 형식화하고, 잘못된 형식 `"{0} {"`는 컴파일 오류가 아니라 실행 중 `std::format_error`가 됩니다. 메시지 내용은 표준 라이브러리마다 다릅니다.
- 7단계: `std::println`으로 찍은 행과 `std::cout`으로 찍은 행이 같고, 4단계의 `Vec2` formatter도 `std::println`에서 그대로 동작하며, `std::print(stdout, …)`으로 출력 스트림을 고릅니다. `std::cout`이 기본으로 C stdio와 동기화되어 있어서(`std::ios::sync_with_stdio(true)`) `std::cout`과 섞어 써도 순서가 유지되며, Windows 콘솔에서는 `std::print`가 유니코드 콘솔 API(P2093)를 통해 출력합니다.

## 연습
1. 3단계의 `std::format("dec: {}, hex: {:#x}, …", …)`에서 인자 하나를 지워 보세요. 컴파일 오류 메시지를 읽고, 그 검사를 누가 하는지(`std::format_string`의 consteval 생성자) 찾아보세요. 인자를 하나 **더** 넣으면 어떻게 되나요?
2. `Vec2`의 formatter에 `p` 표시를 더해 `{:p}`가 극좌표 `(r, θ)`를 쓰게 해 보세요. `parse`에서 `p`를 읽고 `format`에서 `std::hypot`, `std::atan2`를 씁니다.
3. 2단계의 표를 `std::println`으로 다시 써 보세요(`<<`와 `'\n'`이 사라집니다). 이어서 6단계의 실행 시간 문자열 `bad_pattern`을 `std::println(bad_pattern, word);`처럼 넘겨 컴파일 오류를 읽어 보세요(`std::print`와 `std::println`도 `std::format_string`을 받습니다). 실행 시간 형식 문자열을 출력하는 함수는 `std::vprint_unicode`입니다.
