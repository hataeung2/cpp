/**
 * @file event_reader.hpp
 * @brief 020-05 Tracer JSON Lines event reader (Spec 070-07 Assumption 7, AC-4)
 */
#pragma once

#include <algorithm>
#include <charconv>
#include <cstddef>
#include <cstdint>
#include <istream>
#include <limits>
#include <string>
#include <string_view>
#include <system_error>
#include <utility>
#include <vector>

#include "atugcc/pattern/visualizer.hpp"

namespace atugcc::tools::replay {

struct EventSet {
    std::vector<atugcc::pattern::viz::Message>    messages;
    std::vector<atugcc::pattern::viz::Transition> transitions;
    std::vector<atugcc::pattern::viz::Node>       nodes;
    std::size_t skipped = 0;   // lines that could not be used
};

namespace detail {

enum class ValueKind { String, Int, Bool, Null };

struct Value {
    ValueKind     kind = ValueKind::Null;
    std::string   str;
    std::uint64_t u64 = 0;
    bool          is_neg = false;
};

[[nodiscard]] inline int hexVal(char c) noexcept {
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    if (c >= 'A' && c <= 'F') return c - 'A' + 10;
    return -1;
}

[[nodiscard]] inline bool parseHex4(std::string_view s, std::size_t& pos, std::uint32_t& out) noexcept {
    if (pos + 4 > s.size()) return false;
    std::uint32_t v = 0;
    for (int i = 0; i < 4; ++i) {
        const int h = hexVal(s[pos++]);
        if (h < 0) return false;
        v = (v << 4) | static_cast<std::uint32_t>(h);
    }
    out = v;
    return true;
}

inline void appendUtf8(std::uint32_t cp, std::string& out) {
    if (cp <= 0x7Fu) {
        out.push_back(static_cast<char>(cp));
    } else if (cp <= 0x7FFu) {
        out.push_back(static_cast<char>(0xC0u | ((cp >> 6) & 0x1Fu)));
        out.push_back(static_cast<char>(0x80u | (cp & 0x3Fu)));
    } else if (cp <= 0xFFFFu) {
        out.push_back(static_cast<char>(0xE0u | ((cp >> 12) & 0x0Fu)));
        out.push_back(static_cast<char>(0x80u | ((cp >> 6) & 0x3Fu)));
        out.push_back(static_cast<char>(0x80u | (cp & 0x3Fu)));
    } else {
        out.push_back(static_cast<char>(0xF0u | ((cp >> 18) & 0x07u)));
        out.push_back(static_cast<char>(0x80u | ((cp >> 12) & 0x3Fu)));
        out.push_back(static_cast<char>(0x80u | ((cp >> 6) & 0x3Fu)));
        out.push_back(static_cast<char>(0x80u | (cp & 0x3Fu)));
    }
}

inline void skipWhitespace(std::string_view s, std::size_t& pos) noexcept {
    while (pos < s.size() && (s[pos] == ' ' || s[pos] == '\t' || s[pos] == '\n' || s[pos] == '\r')) {
        ++pos;
    }
}

[[nodiscard]] inline bool parseString(std::string_view s, std::size_t& pos, std::string& out) {
    if (pos >= s.size() || s[pos++] != '"') return false;
    out.clear();
    while (pos < s.size()) {
        const char c = s[pos++];
        if (c == '"') return true;
        if (c != '\\') {
            out.push_back(c);
            continue;
        }
        if (pos >= s.size()) return false;
        switch (s[pos++]) {
        case '"':  out.push_back('"'); break;
        case '\\': out.push_back('\\'); break;
        case '/':  out.push_back('/'); break;
        case 'b':  out.push_back('\b'); break;
        case 'f':  out.push_back('\f'); break;
        case 'n':  out.push_back('\n'); break;
        case 'r':  out.push_back('\r'); break;
        case 't':  out.push_back('\t'); break;
        case 'u': {
            std::uint32_t cp1 = 0;
            if (!parseHex4(s, pos, cp1)) return false;
            if (cp1 >= 0xD800u && cp1 <= 0xDBFFu) {
                if (pos + 2 > s.size() || s[pos] != '\\' || s[pos + 1] != 'u') return false;
                pos += 2;
                std::uint32_t cp2 = 0;
                if (!parseHex4(s, pos, cp2) || cp2 < 0xDC00u || cp2 > 0xDFFFu) return false;
                appendUtf8(0x10000u + (((cp1 - 0xD800u) << 10) | (cp2 - 0xDC00u)), out);
            } else if (cp1 >= 0xDC00u && cp1 <= 0xDFFFu) {
                return false;
            } else {
                appendUtf8(cp1, out);
            }
            break;
        }
        default:
            return false;
        }
    }
    return false;
}

[[nodiscard]] inline bool matchKeyword(std::string_view s, std::size_t& pos, std::string_view kw) noexcept {
    if (pos + kw.size() <= s.size() && s.substr(pos, kw.size()) == kw) {
        const auto next = pos + kw.size();
        if (next < s.size() && s[next] != ' ' && s[next] != '\t' && s[next] != '\n' && s[next] != '\r' && s[next] != ',' && s[next] != '}') {
            return false;
        }
        pos = next;
        return true;
    }
    return false;
}

[[nodiscard]] inline bool parseValue(std::string_view s, std::size_t& pos, Value& val) {
    if (pos >= s.size()) return false;
    const char c = s[pos];
    if (c == '"') {
        val.kind = ValueKind::String;
        return parseString(s, pos, val.str);
    }
    if (c == '[' || c == '{') return false;
    if (c == 't' || c == 'f' || c == 'n') {
        const auto kw = (c == 't') ? "true" : (c == 'f') ? "false" : "null";
        if (!matchKeyword(s, pos, kw)) return false;
        val.kind = (c == 'n') ? ValueKind::Null : ValueKind::Bool;
        return true;
    }
    if (c == '-' || (c >= '0' && c <= '9')) {
        const std::size_t start = pos;
        std::size_t end = pos;
        while (end < s.size() && s[end] != ' ' && s[end] != '\t' && s[end] != '\n' && s[end] != '\r' && s[end] != ',' && s[end] != '}') {
            ++end;
        }
        if (c == '-') {
            if (end - start < 2) return false;
            val.is_neg = true;
            std::int64_t num = 0;
            const auto [ptr, ec] = std::from_chars(s.data() + start, s.data() + end, num);
            if (ec != std::errc{} || ptr != s.data() + end) return false;
            val.kind = ValueKind::Int;
        } else {
            val.is_neg = false;
            std::uint64_t num = 0;
            const auto [ptr, ec] = std::from_chars(s.data() + start, s.data() + end, num);
            if (ec != std::errc{} || ptr != s.data() + end) return false;
            val.kind = ValueKind::Int; val.u64 = num;
        }
        pos = end;
        return true;
    }
    return false;
}

[[nodiscard]] inline bool parseObject(std::string_view s, std::vector<std::pair<std::string, Value>>& fields) {
    std::size_t pos = 0;
    skipWhitespace(s, pos);
    if (pos >= s.size() || s[pos++] != '{') return false;
    skipWhitespace(s, pos);
    if (pos < s.size() && s[pos] == '}') {
        skipWhitespace(s, ++pos);
        return pos == s.size();
    }
    while (pos < s.size()) {
        std::string key;
        Value val;
        skipWhitespace(s, pos);
        if (!parseString(s, pos, key)) return false;
        skipWhitespace(s, pos);
        if (pos >= s.size() || s[pos++] != ':') return false;
        skipWhitespace(s, pos);
        if (!parseValue(s, pos, val)) return false;

        auto it = std::find_if(fields.begin(), fields.end(), [&](const auto& p) { return p.first == key; });
        if (it != fields.end()) {
            it->second = std::move(val);
        } else {
            fields.emplace_back(std::move(key), std::move(val));
        }

        skipWhitespace(s, pos);
        if (pos >= s.size()) return false;
        if (s[pos] == ',') { ++pos; continue; }
        if (s[pos] == '}') { skipWhitespace(s, ++pos); return pos == s.size(); }
        return false;
    }
    return false;
}

[[nodiscard]] inline const std::string* getString(
    const std::vector<std::pair<std::string, Value>>& fields, std::string_view key) noexcept {
    for (const auto& [k, v] : fields) {
        if (k == key && v.kind == ValueKind::String) return &v.str;
    }
    return nullptr;
}

[[nodiscard]] inline bool getNonNegativeInt(
    const std::vector<std::pair<std::string, Value>>& fields, std::string_view key, std::uint64_t& out) noexcept {
    for (const auto& [k, v] : fields) {
        if (k == key && v.kind == ValueKind::Int && !v.is_neg) {
            out = v.u64;
            return true;
        }
    }
    return false;
}

[[nodiscard]] inline bool getSeqTracer(
    const std::vector<std::pair<std::string, Value>>& fields, std::uint64_t& seq, std::uint32_t& trk) noexcept {
    std::uint64_t raw_trk = 0;
    if (!getNonNegativeInt(fields, "seq", seq) || !getNonNegativeInt(fields, "tracer", raw_trk) ||
        raw_trk > static_cast<std::uint64_t>((std::numeric_limits<std::uint32_t>::max)())) {
        return false;
    }
    trk = static_cast<std::uint32_t>(raw_trk);
    return true;
}

} // namespace detail

[[nodiscard]] inline EventSet readEvents(std::istream& in, std::uint32_t tracer) {
    EventSet events;
    std::string line;
    std::vector<std::pair<std::string, detail::Value>> fields;

    while (std::getline(in, line)) {
        if (!line.empty() && line.back() == '\r') line.pop_back();
        if (line.empty()) continue;

        fields.clear();
        if (!detail::parseObject(line, fields)) {
            ++events.skipped;
            continue;
        }

        std::uint64_t v = 0;
        if (!detail::getNonNegativeInt(fields, "v", v) || v != 1) {
            ++events.skipped;
            continue;
        }

        const auto* kind_ptr = detail::getString(fields, "kind");
        if (kind_ptr == nullptr) {
            ++events.skipped;
            continue;
        }
        const auto& kind = *kind_ptr;

        if (kind == "span" || kind == "diagram") {
            continue;
        }

        std::uint64_t seq = 0;
        std::uint32_t trk = 0;
        if (kind == "message") {
            const auto* from = detail::getString(fields, "from");
            const auto* to = detail::getString(fields, "to");
            const auto* action = detail::getString(fields, "action");
            if (!detail::getSeqTracer(fields, seq, trk) || !from || !to || !action) {
                ++events.skipped;
                continue;
            }
            if (trk == tracer) {
                auto& msg = events.messages.emplace_back();
                msg.from = *from; msg.to = *to; msg.action = *action;
                msg.meta.seq = seq; msg.meta.tracerId = trk;
            }
        } else if (kind == "transition") {
            const auto* old_state = detail::getString(fields, "old");
            const auto* new_state = detail::getString(fields, "new");
            const auto* trigger = detail::getString(fields, "trigger");
            if (!detail::getSeqTracer(fields, seq, trk) || !old_state || !new_state || !trigger) {
                ++events.skipped;
                continue;
            }
            if (trk == tracer) {
                auto& tr = events.transitions.emplace_back();
                tr.old_state = *old_state; tr.new_state = *new_state; tr.trigger = *trigger;
                tr.meta.seq = seq; tr.meta.tracerId = trk;
            }
        } else if (kind == "node") {
            const auto* parent = detail::getString(fields, "parent");
            const auto* child = detail::getString(fields, "child");
            const auto* relation = detail::getString(fields, "relation");
            if (!detail::getSeqTracer(fields, seq, trk) || !parent || !child || !relation) {
                ++events.skipped;
                continue;
            }
            if (trk == tracer) {
                auto& node = events.nodes.emplace_back();
                node.parent = *parent; node.child = *child; node.relation_type = *relation;
                node.meta.seq = seq; node.meta.tracerId = trk;
            }
        } else {
            ++events.skipped;
            continue;
        }
    }

    auto bySeq = [](const auto& a, const auto& b) noexcept {
        return a.meta.seq < b.meta.seq;
    };
    std::stable_sort(events.messages.begin(), events.messages.end(), bySeq);
    std::stable_sort(events.transitions.begin(), events.transitions.end(), bySeq);
    std::stable_sort(events.nodes.begin(), events.nodes.end(), bySeq);

    return events;
}

} // namespace atugcc::tools::replay
