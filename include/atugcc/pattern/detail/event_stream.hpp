/**
 * @file event_stream.hpp
 * @brief Tracer JSON Lines 이벤트 스트림 구현
 *
 * ※ visualizer.hpp 가 이 파일을 마지막에 include 하므로
 *   Tracer 클래스 및 다이어그램 관련 정의가 이미 완성된 상태에서 파싱된다.
 *   직접 include 하지 말 것.
 */
#pragma once

#include <atomic>
#include <cassert>
#include <charconv>
#include <chrono>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <filesystem>
#include <format>
#include <fstream>
#include <iterator>
#include <memory>
#include <mutex>
#include <optional>
#include <string>
#include <string_view>
#include <vector>

namespace atugcc::pattern::viz {

namespace detail {

[[nodiscard]] inline std::uint64_t nextEventSeq() noexcept {
    static std::atomic<std::uint64_t> counter{ 0 };
    return (counter.fetch_add)(1, std::memory_order_relaxed) + 1;
}

[[nodiscard]] inline std::uint32_t nextTracerId() noexcept {
    static std::atomic<std::uint32_t> counter{ 0 };
    return (counter.fetch_add)(1, std::memory_order_relaxed) + 1;
}

[[nodiscard]] inline std::string jsonEscape(std::string_view sv) {
    std::string out;
    out.reserve(sv.size() + 16);
    for (const char ch : sv) {
        const auto uc = static_cast<unsigned char>(ch);
        switch (uc) {
        case '"':
            out += "\\\"";
            break;
        case '\\':
            out += "\\\\";
            break;
        case '\b':
            out += "\\b";
            break;
        case '\f':
            out += "\\f";
            break;
        case '\n':
            out += "\\n";
            break;
        case '\r':
            out += "\\r";
            break;
        case '\t':
            out += "\\t";
            break;
        default:
            if (uc < 0x20u) {
                constexpr char kHex[] = "0123456789abcdef";
                out += "\\u00";
                out += kHex[(uc >> 4) & 0x0fu];
                out += kHex[uc & 0x0fu];
            } else {
                out += ch;
            }
            break;
        }
    }
    return out;
}

[[nodiscard]] constexpr inline std::string_view kindName(DiagramKind kind) noexcept {
    switch (kind) {
    case DiagramKind::Sequence:
        return "sequence";
    case DiagramKind::State:
        return "state";
    case DiagramKind::Structure:
        return "structure";
    }
    return "";
}

[[nodiscard]] constexpr inline std::string_view backendName(DiagramBackend backend) noexcept {
    switch (backend) {
    case DiagramBackend::PlantUML:
        return "plantuml";
    case DiagramBackend::Mermaid:
        return "mermaid";
    case DiagramBackend::D2:
        return "d2";
    }
    return "";
}

inline void appendMeta(std::string& out, const EventMeta& meta) {
    const auto t_us = std::chrono::duration_cast<std::chrono::microseconds>(
        meta.timestamp.time_since_epoch()).count();
    std::format_to(
        std::back_inserter(out),
        ",\"file\":\"{}\",\"line\":{},\"func\":\"{}\",\"tUs\":{}",
        jsonEscape(meta.location.file_name()),
        meta.location.line(),
        jsonEscape(meta.location.function_name()),
        t_us);
}

[[nodiscard]] inline std::optional<std::filesystem::path> readEnvironmentPath(std::string_view asciiName) {
#ifdef _WIN32
    std::wstring wname;
    wname.reserve(asciiName.size());
    for (const char ch : asciiName) {
        wname.push_back(static_cast<wchar_t>(static_cast<unsigned char>(ch)));
    }
    wchar_t* buffer = nullptr;
    std::size_t len = 0;
    if (_wdupenv_s(&buffer, &len, wname.c_str()) != 0 || buffer == nullptr) {
        return std::nullopt;
    }
    if (buffer[0] == L'\0') {
        std::free(buffer);
        return std::nullopt;
    }
    std::filesystem::path result(buffer);
    std::free(buffer);
    return result;
#else
    const std::string name(asciiName);
    const char* val = std::getenv(name.c_str());
    if (val == nullptr || val[0] == '\0') {
        return std::nullopt;
    }
    return std::filesystem::path(val);
#endif
}

[[nodiscard]] inline std::optional<std::string> readEnvironmentAscii(std::string_view name) {
    const auto path_opt = readEnvironmentPath(name);
    if (!path_opt.has_value()) {
        return std::nullopt;
    }
    const auto& native_str = path_opt->native();
    std::string result;
    result.reserve(native_str.size());
    for (const auto ch : native_str) {
        using UnsignedChar = std::make_unsigned_t<std::decay_t<decltype(ch)>>;
        if (static_cast<UnsignedChar>(ch) > 0x7Fu) {
            return std::nullopt;
        }
        result.push_back(static_cast<char>(ch));
    }
    return result;
}

[[nodiscard]] inline std::chrono::milliseconds environmentFlushInterval() {
    // unset or empty -> 0 without a message, like ATUGCC_TRACE_OUT
    if (!readEnvironmentPath(kTraceFlushEnv).has_value()) {
        return std::chrono::milliseconds{ 0 };
    }
    const auto env_opt = readEnvironmentAscii(kTraceFlushEnv);
    if (!env_opt.has_value()) {
        std::fprintf(stderr, "atugcc: invalid ATUGCC_TRACE_FLUSH_MS (not ASCII), using 0\n");
        return std::chrono::milliseconds{ 0 };
    }
    std::uint32_t val = 0;
    const char* const first = env_opt->data();
    const char* const last = env_opt->data() + env_opt->size();
    const auto [ptr, ec] = (std::from_chars)(first, last, val);
    if (ec != std::errc{} || ptr != last) {
        std::fprintf(stderr, "atugcc: invalid ATUGCC_TRACE_FLUSH_MS '%s', using 0\n", env_opt->c_str());
        return std::chrono::milliseconds{ 0 };
    }
    return std::chrono::milliseconds{ val };
}

} // namespace detail

[[nodiscard]] inline std::string toJsonLine(const Message& event) {
    std::string out = std::format(
        "{{\"v\":1,\"kind\":\"message\",\"seq\":{},\"tracer\":{},\"from\":\"{}\",\"to\":\"{}\",\"action\":\"{}\"",
        event.meta.seq,
        event.meta.tracerId,
        detail::jsonEscape(event.from),
        detail::jsonEscape(event.to),
        detail::jsonEscape(event.action));
    detail::appendMeta(out, event.meta);
    out.push_back('}');
    return out;
}

[[nodiscard]] inline std::string toJsonLine(const Transition& event) {
    std::string out = std::format(
        "{{\"v\":1,\"kind\":\"transition\",\"seq\":{},\"tracer\":{},\"old\":\"{}\",\"new\":\"{}\",\"trigger\":\"{}\"",
        event.meta.seq,
        event.meta.tracerId,
        detail::jsonEscape(event.old_state),
        detail::jsonEscape(event.new_state),
        detail::jsonEscape(event.trigger));
    detail::appendMeta(out, event.meta);
    out.push_back('}');
    return out;
}

[[nodiscard]] inline std::string toJsonLine(const Node& event) {
    std::string out = std::format(
        "{{\"v\":1,\"kind\":\"node\",\"seq\":{},\"tracer\":{},\"parent\":\"{}\",\"child\":\"{}\",\"relation\":\"{}\"",
        event.meta.seq,
        event.meta.tracerId,
        detail::jsonEscape(event.parent),
        detail::jsonEscape(event.child),
        detail::jsonEscape(event.relation_type));
    detail::appendMeta(out, event.meta);
    out.push_back('}');
    return out;
}

[[nodiscard]] inline std::string toJsonLine(
    std::uint32_t tracerId,
    std::size_t part,
    std::size_t parts,
    const DiagramPart& diagram)
{
    return std::format(
        "{{\"v\":1,\"kind\":\"diagram\",\"tracer\":{},\"part\":{},\"parts\":{},\"diagram\":\"{}\",\"backend\":\"{}\",\"title\":\"{}\",\"overBudget\":{},\"source\":\"{}\"}}",
        tracerId,
        part,
        parts,
        detail::kindName(diagram.kind),
        detail::backendName(diagram.backend),
        detail::jsonEscape(diagram.title),
        diagram.overBudget ? "true" : "false",
        detail::jsonEscape(diagram.source));
}

inline JsonLinesEventSink::JsonLinesEventSink(
    std::ofstream stream,
    std::chrono::milliseconds flushInterval) noexcept
    : stream_(std::move(stream))
    , flush_interval_(flushInterval)
    , last_flush_(std::chrono::steady_clock::now())
{}

[[nodiscard]] inline std::shared_ptr<JsonLinesEventSink> JsonLinesEventSink::open(
    const std::filesystem::path& path,
    std::chrono::milliseconds flushInterval)
{
    std::ofstream s(path, std::ios::binary | std::ios::trunc);
    if (!s.is_open()) {
        return nullptr;
    }
    return std::shared_ptr<JsonLinesEventSink>(
        new JsonLinesEventSink(std::move(s), flushInterval));
}

inline JsonLinesEventSink::~JsonLinesEventSink() {
    std::lock_guard lock(mutex_);
    if (stream_.is_open()) {
        stream_.flush();
    }
}

inline void JsonLinesEventSink::writeLine(std::string_view line) {
    std::lock_guard lock(mutex_);
    if (!stream_.is_open()) {
        return;
    }
    stream_.write(line.data(), static_cast<std::streamsize>(line.size()));
    stream_.put('\n');
    if (flush_interval_ == std::chrono::milliseconds{ 0 }) {
        stream_.flush();
    } else {
        const auto now = std::chrono::steady_clock::now();
        if (now - last_flush_ >= flush_interval_) {
            stream_.flush();
            last_flush_ = now;
        }
    }
}

inline void JsonLinesEventSink::onEvent(const Message& event) {
    writeLine(toJsonLine(event));
}

inline void JsonLinesEventSink::onEvent(const Transition& event) {
    writeLine(toJsonLine(event));
}

inline void JsonLinesEventSink::onEvent(const Node& event) {
    writeLine(toJsonLine(event));
}

inline void JsonLinesEventSink::onEvent(const Span& event) {
    writeLine(toJsonLine(event));
}

inline void JsonLinesEventSink::onDiagramParts(std::uint32_t tracerId, const std::vector<DiagramPart>& parts) {
    if (parts.empty()) {
        return;
    }

    std::size_t count_sequence = 0;
    std::size_t count_state = 0;
    std::size_t count_structure = 0;
    for (const auto& part : parts) {
        switch (part.kind) {
        case DiagramKind::Sequence:
            ++count_sequence;
            break;
        case DiagramKind::State:
            ++count_state;
            break;
        case DiagramKind::Structure:
            ++count_structure;
            break;
        }
    }

    std::size_t idx_sequence = 0;
    std::size_t idx_state = 0;
    std::size_t idx_structure = 0;

    for (const auto& part : parts) {
        std::size_t cur_idx = 0;
        std::size_t total_count = 0;
        switch (part.kind) {
        case DiagramKind::Sequence:
            cur_idx = idx_sequence++;
            total_count = count_sequence;
            break;
        case DiagramKind::State:
            cur_idx = idx_state++;
            total_count = count_state;
            break;
        case DiagramKind::Structure:
            cur_idx = idx_structure++;
            total_count = count_structure;
            break;
        }
        writeLine(toJsonLine(tracerId, cur_idx, total_count, part));
    }
}

[[nodiscard]] inline std::shared_ptr<TraceEventSink> environmentEventSink() {
    static const std::shared_ptr<TraceEventSink> sink = []() -> std::shared_ptr<TraceEventSink> {
        const auto path_opt = detail::readEnvironmentPath(kTraceOutEnv);
        if (!path_opt.has_value()) {
            return nullptr;
        }
        return JsonLinesEventSink::open(*path_opt, detail::environmentFlushInterval());
    }();
    return sink;
}

inline Tracer::~Tracer() {
    assert(live_spans_.load(std::memory_order_acquire) == 0 && "ScopedSpan outlived its Tracer");
    if (!event_sink_) {
        return;
    }
    try {
        event_sink_->onDiagramParts(id_, diagramParts(DiagramBackend::Mermaid));
    } catch (const std::exception& e) {
        std::fprintf(stderr, "Tracer::~Tracer exception: %s\n", e.what());
    } catch (...) {
        std::fprintf(stderr, "Tracer::~Tracer unknown exception\n");
    }
}

static_assert(EventSink<JsonLinesEventSink, Message> &&
              EventSink<JsonLinesEventSink, Transition> &&
              EventSink<JsonLinesEventSink, Node> &&
              EventSink<JsonLinesEventSink, Span>);

} // namespace atugcc::pattern::viz
