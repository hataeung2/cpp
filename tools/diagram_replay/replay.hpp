/**
 * @file replay.hpp
 * @brief 070-07 Diagram replay tool core logic and CLI parser
 */
#pragma once

#include <charconv>
#include <cstddef>
#include <cstdint>
#include <istream>
#include <limits>
#include <optional>
#include <ostream>
#include <span>
#include <string>
#include <string_view>
#include <system_error>
#include <vector>

#include "atugcc/pattern/visualizer.hpp"
#include "event_reader.hpp"

namespace atugcc::tools::replay {

struct ReplayArgs {
    std::uint32_t tracer = 0;
    std::uint64_t until  = (std::numeric_limits<std::uint64_t>::max)();   // parenthesized: windows.h defines max
    bool          markLast = false;
};

/// Reads 020-05 JSON Lines from `in`, draws the Mermaid parts of tracer `args.tracer` up to seq `args.until`,
/// writes one "diagram" line per part to `out`, and the last line of `err` is "skipped: <N>". Returns 0.
inline int replay(std::istream& in, std::ostream& out, std::ostream& err, const ReplayArgs& args) {
    const EventSet set = readEvents(in, args.tracer);
    const auto parts = atugcc::pattern::viz::diagramPartsOf(
        set.messages,
        set.transitions,
        set.nodes,
        atugcc::pattern::viz::DiagramBackend::Mermaid,
        {},
        atugcc::pattern::viz::DiagramRange{ .untilSeq = args.until, .markLast = args.markLast });

    for (const auto& line : atugcc::pattern::viz::toJsonLines(args.tracer, parts)) {
        out << line << '\n';
    }

    err << "skipped: " << set.skipped << '\n';
    return 0;
}

inline std::optional<ReplayArgs> parseArgs(std::span<const std::string_view> argv, std::ostream& err) {
    auto fail = [&](std::string_view reason) {
        err << reason << '\n';
        err << "usage: atugcc_diagram_replay --tracer <id> [--until <seq>] [--mark-last]\n";
    };

    ReplayArgs args;
    bool has_tracer = false;

    for (std::size_t i = 0; i < argv.size(); ++i) {
        const std::string_view arg = argv[i];
        if (arg == "--tracer") {
            if (++i >= argv.size()) {
                fail("missing value for --tracer");
                return std::nullopt;
            }
            const std::string_view val = argv[i];
            if (val.empty()) {
                fail("invalid value for --tracer: empty token");
                return std::nullopt;
            }
            std::uint32_t num = 0;
            const auto [ptr, ec] = std::from_chars(val.data(), val.data() + val.size(), num);
            if (ec != std::errc{} || ptr != val.data() + val.size()) {
                fail("invalid value for --tracer: " + std::string(val));
                return std::nullopt;
            }
            args.tracer = num;
            has_tracer = true;
        } else if (arg == "--until") {
            if (++i >= argv.size()) {
                fail("missing value for --until");
                return std::nullopt;
            }
            const std::string_view val = argv[i];
            if (val.empty()) {
                fail("invalid value for --until: empty token");
                return std::nullopt;
            }
            std::uint64_t num = 0;
            const auto [ptr, ec] = std::from_chars(val.data(), val.data() + val.size(), num);
            if (ec != std::errc{} || ptr != val.data() + val.size()) {
                fail("invalid value for --until: " + std::string(val));
                return std::nullopt;
            }
            args.until = num;
        } else if (arg == "--mark-last") {
            args.markLast = true;
        } else {
            fail("unknown argument: " + std::string(arg));
            return std::nullopt;
        }
    }

    if (!has_tracer) {
        fail("missing required argument: --tracer");
        return std::nullopt;
    }

    return args;
}

} // namespace atugcc::tools::replay
