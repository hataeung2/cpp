/**
 * @file main.cpp
 * @brief 레슨 error_expected — 예외와 std::expected 오류 처리 방식을 비교한다
 * @brief Lesson error_expected — compare exception and std::expected error handling
 *
 * 설정 줄에서 포트를 읽는 함수를 예외 방식과 core::Expected 방식으로 구현하여 비교한다
 * The function that reads the port from a config line is written with exceptions and with core::Expected, to compare them
 * C++23 and_then, transform, or_else 모나드 연산으로 오류 처리 단계를 합성한다
 * Compose error handling steps using C++23 monadic operations: and_then, transform, and or_else
 */
#include <charconv>
#include <cstdint>
#include <format>
#include <iostream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <system_error>

#include "atugcc/core/error.hpp"

namespace core = atugcc::core;

namespace {

// 예외 방식: 유효하지 않은 포트이거나 범위를 벗어나면 예외를 던진다
// Exception approach: throw an exception if the port is invalid or out of range
[[nodiscard]] std::uint16_t parsePortThrowing(std::string_view text) {
    std::size_t pos = 0;
    const int val = std::stoi(std::string(text), &pos);
    if (pos != text.size()) {
        throw std::invalid_argument("trailing characters after the port");
    }
    if (val < 1 || val > 65535) {
        throw std::out_of_range("port out of range");
    }
    return static_cast<std::uint16_t>(val);
}

// std::expected 방식: 실패 시 예외 대신 CoreError 를 unexpected 로 반환한다
// std::expected approach: return CoreError as unexpected on failure instead of throwing
[[nodiscard]] core::Expected<std::uint16_t> parsePort(std::string_view text) {
    if (text.empty()) {
        return std::unexpected(core::CoreError::InvalidArgument);
    }
    int val = 0;
    const auto [ptr, ec] = std::from_chars(text.data(), text.data() + text.size(), val);
    if (ec != std::errc{} || ptr != text.data() + text.size() || val < 1 || val > 65535) {
        return std::unexpected(core::CoreError::InvalidArgument);
    }
    return static_cast<std::uint16_t>(val);
}

// 반환된 string_view 는 line 을 가리키므로 호출자가 line 의 수명을 유지해야 한다
// The returned view points into line, so the caller must keep line alive
[[nodiscard]] core::Expected<std::string_view> valueOf(std::string_view line, std::string_view key) {
    const auto eq = line.find('=');
    if (eq == std::string_view::npos) {
        return std::unexpected(core::CoreError::InvalidArgument);
    }
    const auto actualKey = line.substr(0, eq);
    if (actualKey != key) {
        return std::unexpected(core::CoreError::InvalidArgument);
    }
    return line.substr(eq + 1);
}

// 1024 미만의 잘 알려진 포트는 거부한다
// Reject the well-known ports below 1024
[[nodiscard]] core::Expected<std::uint16_t> requireUnprivileged(std::uint16_t port) {
    if (port < 1024u) {
        return std::unexpected(core::CoreError::InvalidArgument);
    }
    return port;
}

} // namespace

int main() {
    std::cout << "== 1. exceptions ==\n";
    // 1. 예외 방식: 호출자가 try-catch 블록으로 오류를 처리한다
    // 1. Exception approach: callers handle errors with a try-catch block
    constexpr std::string_view kTestInputs[] = {"8080", "abc", "70000", ""};
    for (const auto input : kTestInputs) {
        try {
            const auto port = parsePortThrowing(input);
            std::cout << "parsePortThrowing(\"" << input << "\") -> " << port << '\n';
        } catch (const std::invalid_argument& e) {
            std::cout << "parsePortThrowing(\"" << input << "\") threw: invalid_argument ("
                      << e.what() << ")\n";
        } catch (const std::out_of_range& e) {
            std::cout << "parsePortThrowing(\"" << input << "\") threw: out_of_range ("
                      << e.what() << ")\n";
        }
    }

    std::cout << "\n== 2. std::expected ==\n";
    // 2. std::expected 방식: 반환값을 검사하여 오류를 처리한다
    // 2. std::expected approach: callers inspect the return value to handle errors
    for (const auto input : kTestInputs) {
        const auto result = parsePort(input);
        if (result.has_value()) {
            std::cout << "parsePort(\"" << input << "\") -> " << *result << '\n';
        } else {
            std::cout << "parsePort(\"" << input << "\") -> error "
                      << core::to_string(result.error()) << '\n';
        }
    }

    std::cout << "\n== 3. and_then / transform / or_else ==\n";
    // 3. and_then 과 transform 으로 여러 단계를 합성한다
    // 3. Compose multiple steps with and_then and transform
    constexpr std::string_view kConfigLines[] = {
        "port=8080",
        "port=80",
        "host=example",
        "port=x",
    };
    for (const auto line : kConfigLines) {
        const auto r = valueOf(line, "port")
                           .and_then(parsePort)
                           .and_then(requireUnprivileged)
                           .transform([](std::uint16_t p) {
                               return std::format("listen on :{}", p);
                           });

        if (r) {
            std::cout << line << " -> " << *r << '\n';
        } else {
            std::cout << line << " -> error " << core::to_string(r.error()) << '\n';
        }
    }

    // or_else 로 실패 시 기본 포트를 제공하는 대체 경로를 지정한다
    // Provide a fallback path to a default port on failure with or_else
    const auto fallback = valueOf("port=x", "port")
                              .and_then(parsePort)
                              .and_then(requireUnprivileged)
                              .or_else([](core::CoreError) -> core::Expected<std::uint16_t> {
                                  return std::uint16_t{8080};
                              });

    // or_else 가 언제나 값을 돌려주므로 fallback 은 늘 값을 가진다
    // or_else always returns a value here, so fallback always holds one
    std::cout << "port=x (with fallback) -> " << *fallback << '\n';

    return 0;
}
