/**
 * @file version.hpp
 * @brief 레슨 testing — 테스트 대상 버전 타입과 파서 및 조회 함수
 * @brief Lesson testing — version type, parser, and lookup functions under test
 *
 * 버전 구조체(Version), 문자열 파서(parseVersion), 최신 버전 조회(newestVersion)를 제공한다
 * Provides the Version struct, string parser (parseVersion), and newest version lookup (newestVersion)
 */
#pragma once

#include <algorithm>
#include <charconv>
#include <format>
#include <optional>
#include <ostream>
#include <span>
#include <string>
#include <string_view>
#include <system_error>

#include "atugcc/core/error.hpp"

// GoogleTest 자체의 네임스페이스 testing과의 충돌을 방지하기 위해 testing_lesson을 사용한다
// Use testing_lesson to avoid collisions with GoogleTest's own testing namespace
namespace testing_lesson {

// 버전 정보를 나타내는 구조체
// Struct representing version information
// 디폴트 <=> 연산자는 멤버들을 순서대로 비교하며 == 연산자도 함께 제공한다
// The defaulted <=> compares members in order and also gives ==
struct Version {
    unsigned major{0};
    unsigned minor{0};
    unsigned patch{0};
    auto operator<=>(const Version&) const = default;
};

// [학습] 버전을 "major.minor.patch" 형식의 문자열로 변환한다
// [Learn] Converts a Version into a "major.minor.patch" formatted string
// 이 레슨의 두 .cpp 파일이 이 헤더를 포함하므로 ODR 위반을 방지하기 위해 inline으로 정의한다
// Defined inline to prevent ODR violations as two .cpp files of this lesson include this header
inline std::string to_string(const Version& v) {
    return std::format("{}.{}.{}", v.major, v.minor, v.patch);
}

// [학습] GoogleTest는 동일 네임스페이스의 PrintTo를 ADL로 검색하여 실패 메시지에 사용한다. 없으면 객체의 바이트 덤프가 출력된다
// [Learn] GoogleTest finds PrintTo in the same namespace by ADL and uses it in failure messages; without it a failure shows a byte dump of the object
inline void PrintTo(const Version& v, std::ostream* os) {
    if (os != nullptr) {
        *os << to_string(v);
    }
}

// [학습] std::string_view를 보관하지 않고 파싱된 Version 값을 반환한다
// [Learn] Does not keep the std::string_view and returns the parsed Version value
// 점('.')으로 정확히 세 부분으로 나누고, 비어 있지 않은 각 부분 전체를 std::from_chars로 unsigned로 읽는다
// Splits text at '.' into exactly three parts and reads each non-empty part whole into unsigned with std::from_chars
// 빈 부분, 숫자가 아닌 글자, 범위 초과, 점 개수 오류는 모두 CoreError::InvalidArgument다
// An empty part, a non-digit character, an out-of-range number or a wrong number of dots all give CoreError::InvalidArgument
// 두 .cpp 파일에서 포함하므로 ODR 위반을 방지하기 위해 inline으로 정의한다
// Defined inline to prevent ODR violations as two .cpp files include this header
[[nodiscard]] inline atugcc::core::Expected<Version> parseVersion(std::string_view text) {
    const auto firstDot = text.find('.');
    if (firstDot == std::string_view::npos) {
        return std::unexpected(atugcc::core::CoreError::InvalidArgument);
    }

    const auto secondDot = text.find('.', firstDot + 1);
    if (secondDot == std::string_view::npos) {
        return std::unexpected(atugcc::core::CoreError::InvalidArgument);
    }

    const auto thirdDot = text.find('.', secondDot + 1);
    if (thirdDot != std::string_view::npos) {
        return std::unexpected(atugcc::core::CoreError::InvalidArgument);
    }

    const auto part1 = text.substr(0, firstDot);
    const auto part2 = text.substr(firstDot + 1, secondDot - (firstDot + 1));
    const auto part3 = text.substr(secondDot + 1);

    auto parsePart = [](std::string_view part, unsigned& out) -> bool {
        if (part.empty()) {
            return false;
        }
        const auto [ptr, ec] = std::from_chars(part.data(), part.data() + part.size(), out);
        return ec == std::errc{} && ptr == part.data() + part.size();
    };

    Version version{};
    if (!parsePart(part1, version.major) ||
        !parsePart(part2, version.minor) ||
        !parsePart(part3, version.patch)) {
        return std::unexpected(atugcc::core::CoreError::InvalidArgument);
    }

    return version;
}

// [학습] 버전 목록에서 최댓값 버전을 반환한다 (목록이 비어 있으면 std::nullopt)
// [Learn] Returns the maximum version in the span (or std::nullopt if the span is empty)
// 두 .cpp 파일에서 포함하므로 ODR 위반을 방지하기 위해 inline으로 정의한다
// Defined inline to prevent ODR violations as two .cpp files include this header
[[nodiscard]] inline std::optional<Version> newestVersion(std::span<const Version> versions) {
    if (versions.empty()) {
        return std::nullopt;
    }
    return std::ranges::max(versions);
}

} // namespace testing_lesson
