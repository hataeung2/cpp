#include "atugcc/core/timestamp.hpp"
#include <chrono>
#include <format>
#include <iostream>

namespace atugcc::core {

std::string TimeStamp::str(OptFlags opt) noexcept {
    return str(std::chrono::system_clock::now(), opt);
}

std::string TimeStamp::str(std::chrono::system_clock::time_point tp, OptFlags opt) noexcept {
    try {
        // C++20/23: Get current local zone and time
        // Note: MSVC 2019/2022 and GCC 14+ support current_zone() and zoned_time
        auto zt = std::chrono::zoned_time{std::chrono::current_zone(), tp};
        auto local = zt.get_local_time();

        // local is a local_time<system_clock::duration> which might have nanosecond precision
        // Floor it to seconds to avoid extra precision in std::format
        auto local_seconds = std::chrono::floor<std::chrono::seconds>(local);

        const bool with_fmt = (opt & static_cast<OptFlags>(Option::WithFmt)) != 0;
        const bool add_space = (opt & static_cast<OptFlags>(Option::AddSpace)) != 0;

        std::string result;
        if (with_fmt) {
            // YYYY-MM-DD HH:MM:SS
            result = std::format("{:%Y-%m-%d %H:%M:%S}", local_seconds);
        } else {
            // YYYYMMDDHHMMSS
            result = std::format("{:%Y%m%d%H%M%S}", local_seconds);
        }

        // Manually calculate milliseconds
        auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(local.time_since_epoch()).count() % 1000;
        if (with_fmt) {
            result += std::format(".{:03}", ms);
        } else {
            result += std::format("{:03}", ms);
        }

        if (add_space) {
            result += ' ';
        }
        return result;
    } catch (...) {
        // std::format or zoned_time can theoretically throw (e.g. bad_alloc, time zone database error)
        // Return empty string to fulfill noexcept contract as per spec.
        return "";
    }
}

} // namespace atugcc::core
