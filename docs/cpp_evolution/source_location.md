# C++ Evolution: 호출 위치와 줄 단위 출력

## Why
로그 줄은 어디서 왔는지 말해 줄 때만 쓸모가 있습니다. `atugcc::core::Logger`는 모든 호출에서 위치를 자기 헤더 안(`logger.hpp:41`)으로 기록했습니다. `std::source_location::current()`를 호출하는 곳이 아니라 logger 본문에서 불렀기 때문입니다(KI-013). 여러 스레드가 스트림 하나에 쓰면 줄이 섞일 수도 있었습니다. 태스크 010-08은 매크로 없이 둘 다 고칩니다.

## C++11/17 (Legacy): 매크로
```cpp
#define LOG_INFO(...) \
  ::logLine(Level::Info, __FILE__, __LINE__, __func__, fmt::format(__VA_ARGS__))

void logLine(Level lv, const char* file, int line, const char* func, const std::string& msg) {
  std::lock_guard lock(g_cout_mutex);  // every writer must know this mutex
  std::cout << '[' << name(lv) << "] [" << file << ':' << line << ' ' << func << "] " << msg << '\n';
}
```
- 호출한 쪽의 `__FILE__` / `__LINE__`을 잡는 방법은 매크로뿐입니다.
- 매크로는 네임스페이스를 무시하고, 오버로드할 수 없고, 오류 메시지에는 펼쳐진 모습으로 나타납니다.
- 줄 단위 출력에는 `std::cout`에 쓰는 모든 코드가 약속으로 공유하는 뮤텍스가 필요합니다.

## C++20: 기본 인자로 쓰는 `std::source_location`
기본 인자는 **호출하는 곳에서** 계산되므로, 거기서 부른 `std::source_location::current()`는 호출한 쪽을 기록합니다.
```cpp
void log(std::string_view msg, std::source_location loc = std::source_location::current());
log("hello");  // loc is this line
```
가변 포맷 인자가 있으면 위치를 마지막 매개변수로 둘 수 없고(`Args&&...`가 삼켜 버립니다), 호출하는 쪽이 직접 쓰지 않는 한 첫 번째로 둘 수도 없습니다. 흔히 쓰는 답은 위치를 **포맷 문자열**에 붙이는 것입니다. 생성자가 문자열과 위치를 받는 작은 감싸개입니다.
```cpp
template <typename... Args>
struct FormatWithLocation {
  std::format_string<Args...> fmt;
  std::source_location loc;

  template <typename S>
    requires std::convertible_to<const S&, std::string_view>
  consteval FormatWithLocation(const S& s, std::source_location l = std::source_location::current())
      : fmt(s), loc(l) {}
};

template <typename... Args>
void log(Level lv, FormatWithLocation<std::type_identity_t<Args>...> f, Args&&... args);

logger.log(Level::Info, "user {} logged in", id);  // unchanged call site, caller's file and line
```
- `consteval`은 포맷 문자열의 컴파일 시간 검사를 유지합니다. `std::format_string`의 생성자는 `consteval`이고, 거기에 감싸개의 매개변수 `s`(그 자체로는 상수가 아님)를 넘기는 것은 다른 즉시 함수(immediate function) 안에서만 허용됩니다. `consteval` 감싸개 생성자가 바로 그 함수이고, 호출하는 곳의 리터럴이 상수입니다.
- `std::type_identity_t`는 감싸개를 템플릿 인자 추론에서 뺍니다. `Args`는 인자들에서만 나오고, 문자열 리터럴은 감싸개로 변환됩니다.
- `requires` 절은 `log(Level::Info, ...)`가 `Level`을 포맷 문자열로 바꾸려 하지 않게 막습니다.

## C++20: 줄 단위 출력을 위한 `std::osyncstream`
```cpp
std::osyncstream(*out) << line << '\n' << std::flush;
```
동기화 스트림은 줄을 자기 버퍼에 모았다가, 없어질 때 감싼 스트림에 한 번에 씁니다. 이때 감싼 스트림 버퍼에 딸린 잠금을 씁니다. `std::cout`(이나 파일)을 공유하는 `Logger` 두 개는 더 이상 글자가 섞이지 않고, 어느 쪽도 상대의 뮤텍스를 알 필요가 없습니다. 여기서 `std::flush`는 flush를 그 한 번의 쓰기 안에서 하라고 요청하므로, 어떤 스레드도 잠금 밖에서 공유 스트림을 flush하지 않습니다.

## C++23 (Current, atugcc)
- [`logger.hpp`](/include/atugcc/core/logger.hpp): `FormatWithLocation`, 편의용 `log` 오버로드 두 개, 그리고 받은 위치를 전달하는 코드를 위한 명시적 `log(std::source_location, Level, std::format_string, ...)`.
- crash dump 준비의 실패는 `std::expected`(`atugcc::core::Result`)로 알립니다. [error_expected.md](/docs/cpp_evolution/error_expected.md) 참고.
- 관련: `std::print`(C++23)는 포맷한 텍스트를 스트림이나 `FILE*`에 바로 쓰지만, 그것만으로는 두 쓰는 쪽의 줄을 떼어 놓지 않습니다. `std::osyncstream`은 떼어 놓습니다.
- 레슨: [`source_location`](/lessons/tracks/01_essentials/05_source_location/README.md)(essentials 트랙)은 매크로에서 기본 인자로, 다시 `FormatWithLocation`으로 가서 `Logger::log`로 끝납니다.
- 테스트 프레임워크는 여전히 매크로를 씁니다. `std::source_location`은 실패한 파일과 줄을 줄 수 있지만, 검사한 식을 텍스트로 바꾸는 것(`#expr`)은 전처리기만 할 수 있고, `ASSERT_*`는 테스트 함수에서 return합니다. 레슨: [`testing`](/lessons/tracks/01_essentials/16_testing/README.md) A3.
