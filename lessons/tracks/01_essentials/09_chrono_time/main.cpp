/**
 * @file main.cpp
 * @brief 레슨 chrono_time — std::chrono의 기간, 시계, 달력, 시간대
 * @brief Lesson chrono_time — std::chrono durations, clocks, calendar, and time zones
 *
 * duration 변환과 steady_clock 구간 측정, year_month_day 달력 계산을 살펴본다
 * Examine duration conversions, steady_clock interval timing, and year_month_day calendar arithmetic
 * 고정 시점의 zoned_time 시간대 변환과 chrono format/parse 서식화를 확인한다
 * Check converting one fixed instant between time zones with zoned_time, and chrono format/parse
 */
#include <array>
#include <chrono>
#include <format>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <thread>

#include "atugcc/core/timestamp.hpp"

namespace chr = std::chrono;
namespace core = atugcc::core;

namespace {

// 변환 대상 시간대 목록 (UTC 및 세 대륙의 대표 도시)
// Target time zone list (UTC and representative cities across three continents)
constexpr std::array<std::string_view, 4> kZones{
    "UTC",
    "Asia/Seoul",
    "America/New_York",
    "Europe/Berlin",
};

} // namespace

int main() {
    using namespace std::chrono_literals;

    std::cout << "== 1. durations ==\n";
    // duration_cast 는 0 방향으로 자르고, round 는 가장 가까운 값으로 반올림하되 정확히 중간이면 짝수 쪽을 고른다(1.5s -> 2s, 2.5s -> 2s)
    // duration_cast truncates toward zero; round goes to the nearest value, and an exact tie goes to the even one (1.5s -> 2s, 2.5s -> 2s)
    std::cout << std::format("duration_cast<seconds>(1500ms) = {}\n",
                             chr::duration_cast<chr::seconds>(1500ms));
    std::cout << std::format("round<seconds>(1500ms) = {}\n",
                             chr::round<chr::seconds>(1500ms));
    // 음수에서 duration_cast 는 0 쪽으로 잘라 -1s 가 되고, floor 는 음의 무한대 쪽으로 내려 -2s 가 된다
    // For negative values, duration_cast truncates toward zero to -1s, whereas floor rounds down toward -infinity to -2s
    std::cout << std::format("duration_cast<seconds>(-1500ms) = {}\n",
                             chr::duration_cast<chr::seconds>(-1500ms));
    std::cout << std::format("floor<seconds>(-1500ms) = {}\n",
                             chr::floor<chr::seconds>(-1500ms));
    // 서로 다른 단위의 duration 을 더하면 두 단위의 공통 단위(common_type)로 자동 승격된다
    // Adding durations of different units automatically promotes them to their common_type
    std::cout << std::format("1h + 30min = {}\n", 1h + 30min);
    std::cout << "== 2. clocks ==\n";
    // steady_clock 은 단조 증가하므로 시스템 시간 조정에 영향을 받지 않고 구간 측정에 적합하다
    // steady_clock is monotonic and immune to system clock adjustments, making it ideal for interval timing
    const auto t0 = chr::steady_clock::now();
    std::this_thread::sleep_for(20ms);
    const auto t1 = chr::steady_clock::now();
    const auto elapsed = t1 - t0;
    std::cout << std::format("elapsed >= 20ms: {}\n", elapsed >= 20ms);
    std::cout << std::format("elapsed (rounded) = {}\n", chr::round<chr::milliseconds>(elapsed));
    // steady_clock 은 항상 단조 증가하지만 system_clock 은 동기화나 조정으로 역행할 수 있어 steady 가 아니다
    // steady_clock is guaranteed monotonic, whereas system_clock may adjust backwards and is not steady
    std::cout << std::format("steady_clock::is_steady = {}\n", chr::steady_clock::is_steady);
    std::cout << std::format("system_clock::is_steady = {}\n", chr::system_clock::is_steady);
    std::cout << "== 3. calendar ==\n";
    // year_month_day 는 유효하지 않은 날짜도 표현할 수 있으며 ok() 로 유효성을 검사한다
    // year_month_day can represent invalid calendar dates and checks validity via ok()
    const chr::year_month_day ymd2024 = 2024y / chr::February / 29;
    const chr::year_month_day ymd2023 = 2023y / chr::February / 29;
    std::cout << std::format("2024-02-29 ok() = {}\n", ymd2024.ok());
    std::cout << std::format("2023-02-29 ok() = {}\n", ymd2023.ok());
    // last 지정자를 사용하면 해당 월의 마지막 날을 안전하게 계산할 수 있다
    // Using the last specifier safely computes the last day of the given month
    const chr::year_month_day ymdFebLast{2026y / chr::February / chr::last};
    std::cout << std::format("2026y/February/last = {}\n", ymdFebLast);
    // 날짜에 months 를 더하면 일(day)이 유지되어 2월 31일 같은 유효하지 않은 날짜가 생길 수 있다
    // Adding months to a date preserves the day field, which can produce an invalid date like February 31
    const chr::year_month_day jan31 = 2026y / chr::January / 31;
    const chr::year_month_day invalidFeb = jan31 + chr::months{1};
    std::cout << std::format("2026-01-31 + months{{1}} = {}\n", invalidFeb);
    std::cout << std::format("2026-01-31 + months{{1}} ok() = {}\n", invalidFeb.ok());
    // 유효하지 않은 날짜는 year/month/last 로 해당 월의 말일로 보정(clamp)한다
    // An invalid date is repaired by clamping to the end of that month using year/month/last
    const chr::year_month_day clamped{invalidFeb.year() / invalidFeb.month() / chr::last};
    std::cout << std::format("clamped to {}\n", clamped);
    // sys_days 변환을 거쳐 요일(weekday)을 구하고 {:%A} 로 전체 요일 이름을 출력한다
    // Converting through sys_days determines the weekday and prints the full weekday name via {:%A}
    const chr::weekday wd{chr::sys_days{ymd2024}};
    std::cout << std::format("weekday of 2024-02-29 = {:%A}\n", wd);
    // 두 sys_days 사이의 뺄셈으로 두 날짜 사이의 일(days) 수를 정확하게 계산한다
    // Subtracting two sys_days values calculates the exact number of days between two dates
    const auto daysDiff = chr::sys_days{2026y / chr::December / 25} - chr::sys_days{2026y / chr::November / 3};
    std::cout << std::format("days from 2026-11-03 to 2026-12-25 = {}\n", daysDiff.count());
    std::cout << "== 4. time zones ==\n";
    // 고정된 UTC 순간을 constexpr 로 정의하여 플랫폼 간 동일한 기준 시점을 만든다
    // Define a fixed UTC instant at compile time to provide an identical reference across platforms
    constexpr auto instant = chr::sys_days{2026y / chr::November / 3} + 9h;
    std::cout << std::format("instant (UTC): {:%F %T}\n", instant);
    // 시간대 약어(%Z)는 라이브러리마다 다르므로 %z(오프셋)와 시간대 공식 이름만 출력한다
    // Time zone abbreviations (%Z) vary across libraries, so print only %z (offset) and the canonical zone name
    for (const auto zoneName : kZones) {
        try {
            const auto* tz = chr::locate_zone(zoneName);
            const chr::zoned_time zt{tz, instant};
            std::cout << std::format("{:%F %T %z} {}\n", zt, zt.get_time_zone()->name());
        } catch (const std::runtime_error&) {
            std::cout << std::format("time zone database unavailable: {}\n", zoneName);
        }
    }
    // 서머타임(DST) 시작으로 시계가 2시에서 3시로 건너뛰면 02:30 은 현지 시각에 존재하지 않는다
    // When Daylight Saving Time begins and clocks jump from 2 to 3, 02:30 does not exist in local time
    try {
        const auto* nyZone = chr::locate_zone("America/New_York");
        const auto localTime = chr::local_days{2026y / chr::March / 8} + 2h + 30min;
        const chr::zoned_time zt{nyZone, localTime};
        std::cout << std::format("{:%F %T %z}\n", zt);
    } catch (const chr::nonexistent_local_time&) {
        // 존재하지 않는 현지 시각은 nonexistent_local_time 예외를 발생시킨다
        // A nonexistent local time throws a nonexistent_local_time exception
        std::cout << "2026-03-08 02:30 America/New_York: nonexistent local time\n";
        try {
            // 없는 시각에 choose::earliest 를 주면 건너뛴 구간이 끝나는 순간(03:00 EDT)이 된다(latest 도 같은 순간)
            // For a nonexistent time, choose::earliest gives the instant where the skipped gap ends (03:00 EDT; latest gives the same)
            const auto* nyZone = chr::locate_zone("America/New_York");
            const auto localTime = chr::local_days{2026y / chr::March / 8} + 2h + 30min;
            const chr::zoned_time ztEarliest{nyZone, localTime, chr::choose::earliest};
            std::cout << std::format("{:%F %T %z}\n", ztEarliest);
        } catch (const std::runtime_error&) {
            std::cout << "time zone database unavailable: America/New_York\n";
        }
    } catch (const std::runtime_error&) {
        std::cout << "time zone database unavailable: America/New_York\n";
    }
    std::cout << "== 5. format and parse ==\n";
    // chrono 포맷 지정자: %F 는 YYYY-MM-DD, %T 는 HH:MM:SS 를 서식화한다
    // chrono format specifiers: %F formats YYYY-MM-DD, while %T formats HH:MM:SS
    std::cout << std::format("{:%F %T}\n", instant);
    // %A 는 요일 전체 이름(Tuesday), %j 는 연중 일수(307)를 서식화한다
    // %A formats the full weekday name (Tuesday), and %j formats the day of the year (307)
    std::cout << std::format("{:%A}\n", chr::weekday{chr::floor<chr::days>(instant)});
    std::cout << std::format("{:%j}\n", instant);
    // hh_mm_ss 는 duration 을 시, 분, 초(그리고 duration 의 정밀도만큼의 초 이하 부분)로 나눠 포맷한다
    // hh_mm_ss splits a duration into hours, minutes, seconds (and a sub-second part at the duration's own precision) for formatting
    std::cout << std::format("{}\n", chr::hh_mm_ss{3725s});
    // std::chrono::parse 는 포맷의 역이다: 같은 지정자로 문자열을 읽어 시간 지점(sys_time)을 만든다
    // std::chrono::parse is the inverse of format: it reads a string with the same specifiers into a time point (sys_time)
    std::istringstream in{"2026-11-03 09:00"};
    chr::sys_time<chr::minutes> parsed;
    in >> chr::parse("%F %R", parsed);
    const bool parseOk = !in.fail();
    std::cout << std::format("parse ok: {}\n", parseOk);
    std::cout << std::format("parsed == instant: {}\n", parseOk && (parsed == instant));
    // 시스템의 현재 시간대 이름과 atugcc_core 의 TimeStamp 유틸리티 출력을 확인한다
    // Inspect the system current time zone name and the atugcc_core TimeStamp utility output
    try {
        std::cout << std::format("current_zone: {}\n", chr::current_zone()->name());
    } catch (const std::runtime_error&) {
        std::cout << "current_zone: unavailable\n";
    }
    std::cout << std::format("TimeStamp::str(): {}\n",
                             core::TimeStamp::str(static_cast<core::TimeStamp::OptFlags>(core::TimeStamp::Option::WithFmt)));

    return 0;
}
