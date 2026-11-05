# C++ Evolution: 텍스트 포맷팅

## Why
모든 프로그램은 숫자, 표, 로그 줄을 출력합니다. C++20 이전에는 짧지만 타입 안전하지 않은 `printf`와, 타입 안전하지만 장황하고 포맷 상태를 스트림에 남기는 `iostream` 중에서 골라야 했습니다. `std::format`(C++20)은 `printf`의 짧은 포맷 문자열에 컴파일 시간 타입 검사를 더하고, `std::print`(C++23)는 그 결과를 한 번의 호출로 스트림이나 `FILE*`에 씁니다. atugcc의 `Logger`는 `std::format_string`을 받으므로 로그 호출도 같은 컴파일 시간 검사를 받습니다.

레슨: [`format_text`](/lessons/tracks/01_essentials/02_format_text/README.md)(essentials 트랙).

## C++11/17 (Legacy): `printf`와 `iostream`
```cpp
std::printf("%-10s|%6d|%6.1f%%\n", name.c_str(), count, share);   // %d with a long: undefined behaviour
std::printf("%s\n", count);                                        // compiles (warning at best); undefined behaviour, typically a crash

std::cout << std::left << std::setw(10) << name << '|'
          << std::right << std::setw(6) << count << '|'
          << std::fixed << std::setprecision(1) << std::setw(6) << share << "%\n";
// std::fixed and setprecision stay on std::cout for every later output
```
- `printf`는 포맷 문자열을 믿습니다. 잘못된 변환은 컴파일 오류가 아니라 정의되지 않은 동작입니다. 사용자 타입은 먼저 `to_string` 도우미가 필요합니다.
- `iostream`은 타입 안전하지만, 표 한 줄에 조작자가 여러 개 필요하고 그중 일부는 계속 남으며, 문장을 번역하려면 `<<` 체인의 순서를 바꿔야 합니다.
- `std::format`이 된 `{}` 문법은 `{fmt}` 라이브러리가 처음 만들었습니다.

## C++20: `std::format`
```cpp
std::string row = std::format("{:<10}|{:>6}|{:>6.1f}%", name, count, share);
std::string order = std::format("{0} -> {1} -> {0}", "idle", "run");   // positional arguments, reused
std::format("{}", count, extra);   // fine: extra arguments are ignored
std::format("{:d}", name);         // compile error: std::format_string checks the string against the types
```
- 포맷 문자열은 생성자가 `consteval`인 `std::format_string<Args...>`입니다. 잘못된 지정자나 빠진 인자는 **컴파일 오류**입니다.
- 실행 시간에만 알 수 있는 문자열은 `std::vformat(text, std::make_format_args(args...))`로 보내고, 이것은 대신 `std::format_error`를 던집니다.
- `std::format_to(std::back_inserter(buffer), ...)`는 기존 버퍼 뒤에 덧붙이고, `std::formatted_size`는 길이를 먼저 알려 줍니다.
- 사용자 타입은 `std::formatter<T>`를 특수화해서 끼웁니다(`parse`가 지정자를 읽고 `format`이 값을 씁니다). 그러면 Logger를 포함해 모든 `{}` 자리에서 쓸 수 있습니다.

## C++23: `std::print`
```cpp
std::print("{:<10}|{:>6}\n", name, count);   // to stdout in one call
std::println(stderr, "error: {}", message);  // with a newline, to a FILE* or std::ostream
```
- 프로그램을 UTF-8로 컴파일하면(MSVC `/utf-8`), Windows 콘솔로 가는 `std::print`는 콘솔 코드 페이지가 무엇이든 콘솔 API로 유니코드를 씁니다.
- 이제 이 프로젝트의 모든 툴체인에 있습니다: MSVC, 그리고 Linux에서 Clang 20과 libstdc++ 14(스펙 070-13. 그전 Linux 툴체인인 GCC 13에는 `<print>`가 없었습니다). `format_text` 레슨에는 `std::print` / `std::println` 단계가 있습니다(7단계, 태스크 070-14): 같은 표 한 줄을 `std::println`과 `std::cout`으로, `std::println` 안의 `Vec2` formatter, 그리고 `std::print(stdout, …)`.
- 여러 스레드의 로그 줄에는 `Logger`를 쓰세요. 호출한 스레드에서 포맷하고, 로그 스레드 하나에서 줄 단위로 씁니다([lock_free_logging.md](/docs/cpp_evolution/lock_free_logging.md) 참고).

## C++23 (Current, atugcc)
- [`logger.hpp`](/include/atugcc/core/logger.hpp): `Logger::log`는 호출 위치로 감싼 `std::format_string`을 받으므로(`FormatWithLocation`, [source_location.md](/docs/cpp_evolution/source_location.md) 참고) 잘못된 로그 포맷은 컴파일 오류입니다.
- 새 코드는 `{fmt}`가 아니라 `std::format`을 씁니다([impl.md](/.agent/rules/impl.md) §2).
