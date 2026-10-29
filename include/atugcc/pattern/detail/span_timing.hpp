/**
 * @file span_timing.hpp
 * @brief Tracer span timing and aggregation implementation
 *
 * ※ visualizer.hpp 가 이 파일을 마지막에 include 하므로
 *   Tracer 클래스 및 관련 정의가 이미 완성된 상태에서 파싱된다.
 *   직접 include 하지 말 것.
 */
#pragma once

#include <algorithm>
#include <array>
#include <atomic>
#include <chrono>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <format>
#include <memory>
#include <shared_mutex>
#include <string>
#include <string_view>
#include <tuple>
#include <vector>

#ifndef _WIN32
#  include <time.h>
#endif

namespace atugcc::pattern::viz {

inline std::uint64_t WallSpanMeter::nowNs() const noexcept {
    const auto duration = std::chrono::steady_clock::now().time_since_epoch();
    return static_cast<std::uint64_t>(
        std::chrono::duration_cast<std::chrono::nanoseconds>(duration).count());
}

inline std::uint64_t ThreadCpuSpanMeter::nowNs() const noexcept {
#ifdef _WIN32
    FILETIME creation_time{};
    FILETIME exit_time{};
    FILETIME kernel_time{};
    FILETIME user_time{};
    if (!GetThreadTimes(GetCurrentThread(), &creation_time, &exit_time, &kernel_time, &user_time)) {
        return 0;
    }
    const auto to100Ns = [](const FILETIME& ft) noexcept -> std::uint64_t {
        return (static_cast<std::uint64_t>(ft.dwHighDateTime) << 32) |
               static_cast<std::uint64_t>(ft.dwLowDateTime);
    };
    const std::uint64_t total100ns = to100Ns(kernel_time) + to100Ns(user_time);
    return total100ns * 100ULL;
#else
    struct timespec ts{};
    if ((clock_gettime)(CLOCK_THREAD_CPUTIME_ID, &ts) != 0) {
        return 0;
    }
    return static_cast<std::uint64_t>(ts.tv_sec) * 1'000'000'000ULL +
           static_cast<std::uint64_t>(ts.tv_nsec);
#endif
}

namespace detail {

[[nodiscard]] inline std::shared_ptr<SpanMeter> defaultSpanMeter() {
    static const auto meter = std::make_shared<WallSpanMeter>();
    return meter;
}

[[nodiscard]] inline std::uint64_t currentThreadOrdinal() noexcept {
    static std::atomic<std::uint64_t> counter{ 0 };
    thread_local const std::uint64_t ordinal = (counter.fetch_add)(1, std::memory_order_relaxed) + 1;
    return ordinal;
}

[[nodiscard]] inline std::string formatDuration(std::uint64_t ns) {
    if (ns < 1'000ULL) {
        return std::format("{} ns", ns);
    }
    if (ns < 1'000'000ULL) {
        return std::format("{:.3f} µs", static_cast<double>(ns) / 1'000.0);
    }
    if (ns < 1'000'000'000ULL) {
        return std::format("{:.3f} ms", static_cast<double>(ns) / 1'000'000.0);
    }
    return std::format("{:.3f} s", static_cast<double>(ns) / 1'000'000'000.0);
}

[[nodiscard]] inline std::string_view baseName(std::string_view path) noexcept {
    const auto pos = (path.find_last_of)("/\\");
    if (pos == std::string_view::npos) {
        return path;
    }
    return path.substr(pos + 1);
}

[[nodiscard]] inline std::string meterDisplayName(std::string_view meter) {
#ifdef _WIN32
    if (meter == "cpu") {
        return "cpu (~15.6 ms tick)";
    }
#endif
    return std::string(meter);
}

[[nodiscard]] inline std::size_t utf8CodePointCount(std::string_view sv) noexcept {
    std::size_t count = 0;
    for (const char ch : sv) {
        if ((static_cast<unsigned char>(ch) & 0xC0u) != 0x80u) {
            ++count;
        }
    }
    return count;
}

inline std::string LiveTerminalFormatter::formatSpan(const Span& span) {
    return std::format("⏱ {}  {}  ({}:{})\n",
        span.label,
        detail::formatDuration(span.durationNs),
        detail::baseName(span.meta.location.file_name()),
        span.meta.location.line());
}

} // namespace detail

[[nodiscard]] inline std::shared_ptr<SpanMeter> makeSpanMeter(std::string_view name) {
    if (name == "wall") {
        return detail::defaultSpanMeter();
    }
    if (name == "cpu") {
        static const auto meter = std::make_shared<ThreadCpuSpanMeter>();
        return meter;
    }
    return nullptr;
}

namespace detail {

[[nodiscard]] inline std::shared_ptr<SpanMeter> environmentSpanMeter() {
    static const std::shared_ptr<SpanMeter> meter = []() -> std::shared_ptr<SpanMeter> {
        const auto env_opt = readEnvironmentAscii(kSpanMeterEnv);
        if (!env_opt.has_value()) {
            return defaultSpanMeter();
        }
        auto created = makeSpanMeter(*env_opt);
        if (created != nullptr) {
            return created;
        }
        std::fprintf(stderr, "atugcc: unknown ATUGCC_SPAN_METER '%s', using wall\n", env_opt->c_str());
        return defaultSpanMeter();
    }();
    return meter;
}

} // namespace detail

[[nodiscard]] inline std::string toJsonLine(const Span& event) {
    std::string out = std::format(
        "{{\"v\":1,\"kind\":\"span\",\"seq\":{},\"tracer\":{},\"label\":\"{}\",\"meter\":\"{}\",\"durNs\":{},\"thread\":{}",
        event.meta.seq,
        event.meta.tracerId,
        detail::jsonEscape(event.label),
        detail::jsonEscape(event.meter),
        event.durationNs,
        event.threadId);
    detail::appendMeta(out, event.meta);
    out.push_back('}');
    return out;
}

inline ScopedSpan::ScopedSpan(Tracer& tracer, std::string_view label, std::source_location loc)
    : tracer_(&tracer)
    , label_(label)
    , location_(loc)
    , meter_(tracer.spanMeter())
{
    (tracer_->live_spans_.fetch_add)(1, std::memory_order_relaxed);
    start_ns_ = meter_->nowNs();
}

inline ScopedSpan::~ScopedSpan() {
    stop();
}

inline void ScopedSpan::stop() noexcept {
    if (!active_) {
        return;
    }
    const auto end = meter_->nowNs();
    active_ = false;
    try {
        const auto diff = (end >= start_ns_) ? (end - start_ns_) : 0ULL;
        (void)tracer_->recordSpan(
            label_,
            std::chrono::nanoseconds{ diff },
            location_,
            meter_->name());
    } catch (const std::exception& e) {
        std::fprintf(stderr, "ScopedSpan::stop exception: %s\n", e.what());
    } catch (...) {
        std::fprintf(stderr, "ScopedSpan::stop unknown exception\n");
    }
    (tracer_->live_spans_.fetch_sub)(1, std::memory_order_release);
}

inline ScopedSpan Tracer::timeScope(std::string_view label, std::source_location loc) {
    return ScopedSpan(*this, label, loc);
}

inline std::vector<SpanStats> Tracer::spanStats() const {
    std::vector<SpanStats> result;
    {
        std::shared_lock lock(mutex_);
        result.reserve(span_stats_.size());
        for (const auto& [key, agg] : span_stats_) {
            result.push_back(SpanStats{
                .label   = key.label,
                .meter   = key.meter,
                .file    = key.file,
                .line    = key.line,
                .count   = agg.count,
                .totalNs = agg.totalNs,
                .minNs   = agg.minNs,
                .maxNs   = agg.maxNs,
            });
        }
    }

    std::ranges::sort(result, [](const SpanStats& a, const SpanStats& b) {
        if (a.totalNs != b.totalNs) {
            return a.totalNs > b.totalNs;
        }
        return std::tie(a.file, a.line, a.label, a.meter) <
               std::tie(b.file, b.line, b.label, b.meter);
    });

    return result;
}

inline std::string Tracer::formatTimings() const {
    const auto stats = spanStats();
    if (stats.empty()) {
        return "(no spans)\n";
    }

    struct ColumnSpec {
        std::string_view name;
        bool is_number;
    };

    static constexpr ColumnSpec kColumns[] = {
        { "label",    false },
        { "meter",    false },
        { "location", false },
        { "count",    true  },
        { "total",    true  },
        { "mean",     true  },
        { "min",      true  },
        { "max",      true  },
    };
    static constexpr std::size_t kColCount = sizeof(kColumns) / sizeof(kColumns[0]);

    std::vector<std::array<std::string, kColCount>> rows;
    rows.reserve(stats.size());

    std::array<std::size_t, kColCount> widths{};
    for (std::size_t c = 0; c < kColCount; ++c) {
        widths[c] = detail::utf8CodePointCount(kColumns[c].name);
    }

    for (const auto& stat : stats) {
        std::array<std::string, kColCount> row;
        row[0] = stat.label;
        row[1] = detail::meterDisplayName(stat.meter);
        row[2] = std::format("{}:{}", detail::baseName(stat.file), stat.line);
        row[3] = std::format("{}", stat.count);
        row[4] = detail::formatDuration(stat.totalNs);
        row[5] = detail::formatDuration(stat.count > 0 ? (stat.totalNs / stat.count) : 0ULL);
        row[6] = detail::formatDuration(stat.minNs);
        row[7] = detail::formatDuration(stat.maxNs);

        for (std::size_t c = 0; c < kColCount; ++c) {
            const auto w = detail::utf8CodePointCount(row[c]);
            if (w > widths[c]) {
                widths[c] = w;
            }
        }
        rows.push_back(std::move(row));
    }

    auto pad = [](std::string_view text, std::size_t width, bool is_number) -> std::string {
        const auto text_width = detail::utf8CodePointCount(text);
        const auto padding = (width > text_width) ? (width - text_width) : 0U;
        if (is_number) {
            std::string s;
            s.append(padding, ' ');
            s.append(text);
            return s;
        }
        std::string s(text);
        s.append(padding, ' ');
        return s;
    };

    std::string out;
    // Header
    for (std::size_t c = 0; c < kColCount; ++c) {
        if (c > 0) {
            out += "  ";
        }
        out += pad(kColumns[c].name, widths[c], kColumns[c].is_number);
    }
    out += '\n';

    // Dashed rule
    for (std::size_t c = 0; c < kColCount; ++c) {
        if (c > 0) {
            out += "  ";
        }
        out.append(widths[c], '-');
    }
    out += '\n';

    // Data rows
    for (const auto& row : rows) {
        for (std::size_t c = 0; c < kColCount; ++c) {
            if (c > 0) {
                out += "  ";
            }
            out += pad(row[c], widths[c], kColumns[c].is_number);
        }
        out += '\n';
    }

    return out;
}

} // namespace atugcc::pattern::viz
