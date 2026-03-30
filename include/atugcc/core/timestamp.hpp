#pragma once

#include <chrono>
#include <string>
#include <type_traits>

namespace atugcc::core {

/**
 * @brief Utility class for standardized time stamp generation using C++20 chrono/format.
 */
class TimeStamp final {
public:
    enum class Option : unsigned int {
        None      = 0x0000,
        WithFmt   = 0x0001, // "YYYY-MM-DD HH:MM:SS.mmm"
        AddSpace  = 0x0002, // Add a space at the end
    };
    
    using OptFlags = std::underlying_type_t<Option>;

    /**
     * @brief Returns the current local time as a formatted string.
     * @param opt Formatting options (defaults to WithFmt | AddSpace).
     * @return Formatted time string.
     */
    [[nodiscard]] static std::string str(
        OptFlags opt = static_cast<OptFlags>(Option::WithFmt) | static_cast<OptFlags>(Option::AddSpace)
    ) noexcept;

    /**
     * @brief Returns a specific time_point as a formatted string.
     * @param tp The time point to format.
     * @param opt Formatting options.
     * @return Formatted time string.
     */
    [[nodiscard]] static std::string str(
        std::chrono::system_clock::time_point tp,
        OptFlags opt = static_cast<OptFlags>(Option::WithFmt) | static_cast<OptFlags>(Option::AddSpace)
    ) noexcept;

    TimeStamp() = delete;
};

/**
 * @brief Bitwise OR operator for TimeStamp::Option.
 */
[[nodiscard]] constexpr TimeStamp::OptFlags operator|(TimeStamp::Option a, TimeStamp::Option b) noexcept {
    return static_cast<TimeStamp::OptFlags>(a) | static_cast<TimeStamp::OptFlags>(b);
}

/**
 * @brief Bitwise OR operator for combining TimeStamp::Option with existing flags.
 */
[[nodiscard]] constexpr TimeStamp::OptFlags operator|(TimeStamp::OptFlags a, TimeStamp::Option b) noexcept {
    return a | static_cast<TimeStamp::OptFlags>(b);
}

} // namespace atugcc::core
