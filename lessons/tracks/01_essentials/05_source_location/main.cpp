/**
 * @file main.cpp
 * @brief 레슨 source_location — std::source_location과 호출 위치 기록
 * @brief Lesson source_location — std::source_location and call site tracking
 *
 * 매크로(__FILE__, __LINE__)에서 std::source_location과 FormatWithLocation으로의 전환
 * Transition from macros (__FILE__, __LINE__) to std::source_location and FormatWithLocation
 */
#include <concepts>
#include <filesystem>
#include <format>
#include <iostream>
#include <source_location>
#include <string>
#include <string_view>
#include <type_traits>
#include <utility>

#include "atugcc/core/logger.hpp"

namespace core = atugcc::core;

namespace {

// 파일 이름에서 경로를 떼어내고 파일명만 반환한다
// Strips the directory path and returns only the file name
[[nodiscard]] std::string shortName(const char* file) {
    return std::filesystem::path(file).filename().string();
}

// 레거시 매크로가 호출하는 도우미 함수
// Helper function invoked by the legacy macro
void logAt(const char* file, int line, const char* func, std::string_view msg) {
    std::cout << std::format("[{}:{} {}] {}\n", shortName(file), line, func, msg);
}

// 2. std::source_location 기본 인자: 선언에 쓰지만 호출할 때마다 호출한 곳에서 계산된다
// 2. std::source_location default argument: written in the declaration, evaluated at each call site
void logHere(std::string_view msg, std::source_location loc = std::source_location::current()) {
    std::cout << std::format("[{}:{} {}] {}\n",
                             shortName(loc.file_name()),
                             loc.line(),
                             loc.function_name(),
                             msg);
}

// 호출 지점의 줄 번호가 캡처되는 것을 보여주는 도우미 함수
// Helper function demonstrating that the call site line number is captured
void startEngine() {
    logHere("engine starting");
}

// 3. 호출 위치를 전달하는 래퍼 함수
// 3. Wrapper function forwarding the source location
// [학습] 매개변수 없이 logHere를 호출하면 warn 내부의 줄 번호가 기록된다
// [Learn] Calling logHere without a parameter would record the line inside warn
// 호출자의 위치를 남기려면 기본 인자로 loc을 받아 다음 함수로 넘겨야 한다
// To preserve the caller's site, accept loc as a default argument and forward it
void warn(std::string_view msg, std::source_location loc = std::source_location::current()) {
    logHere(std::format("warning: {}", msg), loc);
}

// 4. 가변 인자: 형식 문자열에 호출 위치를 결합한다
// 4. Variadic arguments: attach call location to the format string
// [학습] 위치를 Args&&... 뒤에 두면 쓸 수 없다: 마지막이 아닌 매개변수 팩은 추론되지 않아 Args가 비고,
// 호출의 인자가 모두 loc 하나에 들어가야 해서 logFormat("x", 1)이 컴파일되지 않는다
// [Learn] The location cannot go after Args&&...: a parameter pack that is not last is never deduced, so Args
// is empty and every argument of the call would have to go into loc, and logFormat("x", 1) does not compile
// 그래서 첫 매개변수의 타입이 형식 문자열을 감싸고, 그 생성자의 기본 인자로 std::source_location::current()를 받는다
// So the first parameter's type wraps the format string and takes std::source_location::current() as its constructor's default argument
template <typename... Args>
struct Here {
    std::format_string<Args...> fmt;
    std::source_location loc;

    template <typename S>
        requires std::convertible_to<const S&, std::string_view>
    consteval Here(const S& s, std::source_location l = std::source_location::current())
        : fmt(s), loc(l) {}
};

// std::type_identity_t는 Args가 Here 매개변수에서 추론되지 않고 뒤의 가변 인자에서만 추론되도록 막는다
// std::type_identity_t prevents Args from being deduced from Here, deducing only from trailing arguments
template <typename... Args>
void logFormat(Here<std::type_identity_t<Args>...> here, Args&&... args) {
    std::cout << std::format("[{}:{} {}] {}\n",
                             shortName(here.loc.file_name()),
                             here.loc.line(),
                             here.loc.function_name(),
                             std::format(here.fmt, std::forward<Args>(args)...));
}

} // namespace

// MACRO: 레거시 __FILE__, __LINE__ 매크로 방식을 보여주기 위한 예시 (std::source_location과 비교)
// MACRO: Legacy __FILE__, __LINE__ macro example for comparison with std::source_location
#define LOG_HERE(msg) logAt(__FILE__, __LINE__, __func__, msg)

int main() {
    // 1. 매크로 방식: 호출 위치를 기록하는 레거시 패턴
    // 1. Macro approach: legacy pattern for recording call sites
    std::cout << "== 1. macro ==\n";
    // 매크로가 호출 지점의 __FILE__, __LINE__, __func__를 확장한다
    // The macro expands __FILE__, __LINE__, and __func__ at the call site
    LOG_HERE("legacy macro logging");
#undef LOG_HERE

    // 2. std::source_location 기본 인자: 호출자의 줄 번호 기록
    // 2. std::source_location default argument: records caller's line number
    std::cout << "== 2. std::source_location default argument ==\n";
    // 기본 인자는 호출자의 위치에서 평가된다
    // Default arguments are evaluated at the caller's location
    logHere("called from main");
    startEngine();

    // 3. 래퍼 함수에서 호출 위치 전달
    // 3. Forwarding call location through a wrapper function
    std::cout << "== 3. wrapper that forwards the location ==\n";
    // warn 호출 지점의 줄 번호가 logHere까지 전달된다
    // The line number at the warn call site is forwarded to logHere
    warn("low memory");

    // 4. 가변 인자와 형식 문자열 결합
    // 4. Combining variadic arguments with format strings
    std::cout << "== 4. variadic: attach the location to the format string ==\n";
    // 가변 인자 포맷팅과 호출 위치 캡처가 동시에 동작한다
    // Variadic formatting and call site capture work together
    logFormat("server listening on {}:{}", "127.0.0.1", 8080);

    // 5. atugcc::core::Logger 라이브러리 연동
    // 5. Integration with atugcc::core::Logger library
    std::cout << "== 5. atugcc::core::Logger does the same ==\n";
    // 라이브러리의 Logger는 include/atugcc/core/logger.hpp의 FormatWithLocation으로 같은 방식을 쓴다
    // The library Logger uses the same approach via FormatWithLocation in include/atugcc/core/logger.hpp
    // Logger는 전체 파일 경로를 출력한다
    // Logger prints the full file path
    core::Logger logger{core::Logger::Config{.liveOutput = &std::cout, .enableCrashDump = false}};
    logger.log(core::Level::Info, "port {} ready", 8080);
    logger.flush();

    return 0;
}
