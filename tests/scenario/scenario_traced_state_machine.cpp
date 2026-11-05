/**
 * @file scenario_traced_state_machine.cpp
 * @brief Scenario test S1: Traced State Machine (spec 040-02, section 2.2).
 *
 * Demonstrates the State pattern integrated with viz::Tracer, ScopedSpan timing,
 * and JsonLinesEventSink streaming within an isolated scenario process.
 */

#include "scenario.hpp"

#include <gtest/gtest.h>

#include <charconv>
#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <format>
#include <fstream>
#include <memory>
#include <optional>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

#include "atugcc/pattern/state.hpp"
#include "atugcc/pattern/visualizer.hpp"

namespace viz = atugcc::pattern::viz;
namespace state = atugcc::pattern::state;

namespace {

[[nodiscard]] std::optional<std::string> stringField(std::string_view line, std::string_view key) {
    const std::string needle = std::format("\"{}\":\"", key);
    const auto pos = line.find(needle);
    if (pos == std::string_view::npos) {
        return std::nullopt;
    }
    const auto start = pos + needle.size();
    std::size_t end = start;
    while (end < line.size()) {
        if (line[end] == '"' && (end == start || line[end - 1] != '\\')) {
            break;
        }
        ++end;
    }
    if (end >= line.size()) {
        return std::nullopt;
    }
    return std::string(line.substr(start, end - start));
}

[[nodiscard]] std::optional<std::uint64_t> uintField(std::string_view line, std::string_view key) {
    const std::string needle = std::format("\"{}\":", key);
    const auto pos = line.find(needle);
    if (pos == std::string_view::npos) {
        return std::nullopt;
    }
    auto start = pos + needle.size();
    while (start < line.size() && line[start] == ' ') {
        ++start;
    }
    if (start >= line.size()) {
        return std::nullopt;
    }
    std::uint64_t value = 0;
    const char* const first = line.data() + start;
    const char* const last = line.data() + line.size();
    const auto [ptr, ec] = std::from_chars(first, last, value);
    if (ec != std::errc{} || ptr == first) {
        return std::nullopt;
    }
    return value;
}

} // namespace

TEST(TracedStateMachine, EventsReachStreamInOrder) {
    atugcc::test::Scenario s;

    std::unique_ptr<viz::Tracer> tracer = std::make_unique<viz::Tracer>();
    std::shared_ptr<viz::JsonLinesEventSink> sink;
    const std::filesystem::path tracePath = s.workDir() / "trace.jsonl";

    const std::vector<std::pair<std::string, std::string>> expectedTransitions = {
        { std::string(state::IdleState::name), std::string(state::StandbyState::name) },
        { std::string(state::StandbyState::name), std::string(state::RunState::name) },
        { std::string(state::RunState::name), std::string(state::StandbyState::name) },
        { std::string(state::StandbyState::name), std::string(state::AbortState::name) },
        { std::string(state::AbortState::name), std::string(state::IdleState::name) },
    };

    s.step("attach a JSON Lines sink to a tracer", [&] {
        sink = viz::JsonLinesEventSink::open(tracePath);
        ASSERT_NE(sink, nullptr) << "Failed to open sink at " << tracePath.string();
        tracer->setEventSink(sink);
    });

    s.step("run the device state machine", [&] {
        state::Machine m(*tracer);
        const std::vector<state::MachineStateVariant> targets = {
            state::StandbyState{}, state::RunState{}, state::StandbyState{},
            state::AbortState{}, state::IdleState{},
        };
        for (const auto& target : targets) {
            const auto name = state::stateName(target);
            viz::ScopedSpan span(*tracer, std::format("transition {}", name));
            const auto result = m.transition(target);
            ASSERT_TRUE(result.has_value()) << "Transition to " << name << " failed";
        }
    });

    s.step("end the tracer", [&] {
        tracer.reset();
        sink.reset();
    });

    s.step("the stream has the run in order", [&] {
        std::ifstream in(tracePath);
        ASSERT_TRUE(in.is_open()) << "Failed to open " << tracePath.string();

        std::vector<std::string> lines;
        for (std::string line; std::getline(in, line);) {
            if (!line.empty() && line.back() == '\r') {
                line.pop_back();
            }
            if (!line.empty()) {
                lines.push_back(std::move(line));
            }
        }

        ASSERT_FALSE(lines.empty()) << "Trace file is empty";

        // 1. Transition lines in file order have old/new equal to expected pairs
        std::vector<std::pair<std::string, std::string>> actualTransitions;
        for (const auto& line : lines) {
            if (stringField(line, "kind") == "transition") {
                const auto oldState = stringField(line, "old");
                const auto newState = stringField(line, "new");
                ASSERT_TRUE(oldState.has_value()) << "Transition line missing 'old': " << line;
                ASSERT_TRUE(newState.has_value()) << "Transition line missing 'new': " << line;
                actualTransitions.emplace_back(*oldState, *newState);
            }
        }
        EXPECT_EQ(actualTransitions, expectedTransitions);

        // 2. Every line that has "seq" has a strictly greater seq than the previous such line
        std::optional<std::uint64_t> prevSeq;
        for (const auto& line : lines) {
            if (const auto seq = uintField(line, "seq"); seq.has_value()) {
                if (prevSeq.has_value()) {
                    EXPECT_GT(*seq, *prevSeq) << "Sequence number not strictly increasing: " << line;
                }
                prevSeq = seq;
            }
        }
        EXPECT_TRUE(prevSeq.has_value()) << "Expected at least one line with 'seq'";

        // 3. The number of span lines == 5
        std::size_t spanCount = 0;
        for (const auto& line : lines) {
            if (stringField(line, "kind") == "span") {
                ++spanCount;
            }
        }
        EXPECT_EQ(spanCount, 5U);

        // 4. The last line is a diagram line ("kind":"diagram")
        EXPECT_EQ(stringField(lines.back(), "kind").value_or(""), "diagram");
    });
}
