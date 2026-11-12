/**
 * @file scenario_diagram_replay.cpp
 * @brief Scenario test: diagram replay tool (spec 070-07 AC-1).
 *
 * Verifies that replaying recorded JSON Lines events through the replay tool
 * reproduces the exact Mermaid diagram lines emitted by the Tracer destructor,
 * correctly filters by range and tracer ID, and highlights the last event.
 */

#include "scenario.hpp"
#include "replay.hpp"

#include <gtest/gtest.h>

#include <algorithm>
#include <atomic>
#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <format>
#include <fstream>
#include <limits>
#include <memory>
#include <sstream>
#include <string>
#include <string_view>
#include <thread>
#include <utility>
#include <vector>

#include "atugcc/pattern/visualizer.hpp"

namespace viz = atugcc::pattern::viz;
namespace replay = atugcc::tools::replay;

namespace {

[[nodiscard]] std::vector<std::string> splitLines(std::string_view text) {
    std::vector<std::string> lines;
    std::string s(text);
    std::istringstream iss(s);
    for (std::string line; std::getline(iss, line);) {
        if (!line.empty() && line.back() == '\r') {
            line.pop_back();
        }
        lines.push_back(std::move(line));
    }
    return lines;
}

} // namespace

TEST(DiagramReplay, ReplayMatchesTheTracerDestructor) {
    atugcc::test::Scenario s;

    std::unique_ptr<viz::Tracer> tracer = std::make_unique<viz::Tracer>();
    std::unique_ptr<viz::Tracer> other = std::make_unique<viz::Tracer>();
    std::shared_ptr<viz::JsonLinesEventSink> sink;
    const std::filesystem::path tracePath = s.workDir() / "trace.jsonl";

    std::uint32_t id = 0;
    std::uint32_t otherId = 0;
    std::uint64_t mid = 0;
    std::uint64_t lastSeq = 0;
    std::vector<std::string> expectedMid;
    std::string fileContent;
    std::vector<std::string> expectedFull;
    std::vector<std::string> expectedOther;

    s.step("record events from two threads", [&] {
        sink = viz::JsonLinesEventSink::open(tracePath);
        ASSERT_NE(sink, nullptr) << "Failed to open sink at " << tracePath.string();
        tracer->setEventSink(sink);
        other->setEventSink(sink);

        std::atomic<int> workerFailures{ 0 };
        {
            std::jthread t1([&] {
                for (int i = 1; i <= 20; ++i) {
                    const auto res = tracer->recordMessage("A", "B", std::format("act{}", i));
                    if (!res.has_value()) {
                        ++workerFailures;
                    }
                }
            });
            std::jthread t2([&] {
                for (int i = 0; i < 6; ++i) {
                    const auto res = tracer->recordTransition(
                        std::format("S{}", i),
                        std::format("S{}", i + 1),
                        std::format("t{}", i + 1));
                    if (!res.has_value()) {
                        ++workerFailures;
                    }
                }
                for (int i = 1; i <= 4; ++i) {
                    const auto res = tracer->pushNode("Root", std::format("C{}", i), "contains");
                    if (!res.has_value()) {
                        ++workerFailures;
                    }
                }
            });

            for (int i = 1; i <= 3; ++i) {
                const auto res = other->recordMessage("X", "Y", std::format("other_msg{}", i));
                ASSERT_TRUE(res.has_value());
            }
            for (int i = 0; i < 2; ++i) {
                const auto res = other->recordTransition(
                    std::format("OS{}", i),
                    std::format("OS{}", i + 1),
                    std::format("ot{}", i + 1));
                ASSERT_TRUE(res.has_value());
            }
        } // t1 and t2 join here

        ASSERT_EQ(workerFailures.load(), 0);
    });

    s.step("draw the middle of the run with the Tracer", [&] {
        const auto msgs = tracer->snapshotMessages();
        ASSERT_GE(msgs.size(), 12U);
        id = msgs[0].meta.tracerId;
        mid = msgs[11].meta.seq;

        expectedMid = viz::toJsonLines(
            id,
            tracer->diagramParts(
                viz::DiagramBackend::Mermaid,
                {},
                viz::DiagramRange{ .untilSeq = mid, .markLast = true }));

        const auto trans = tracer->snapshotTransitions();
        const auto nodes = tracer->snapshotNodes();
        lastSeq = 0;
        for (const auto& m : msgs) {
            lastSeq = (std::max)(lastSeq, m.meta.seq);
        }
        for (const auto& t : trans) {
            lastSeq = (std::max)(lastSeq, t.meta.seq);
        }
        for (const auto& n : nodes) {
            lastSeq = (std::max)(lastSeq, n.meta.seq);
        }

        const auto otherMsgs = other->snapshotMessages();
        ASSERT_FALSE(otherMsgs.empty());
        otherId = otherMsgs[0].meta.tracerId;
    });

    s.step("end the tracers", [&] {
        tracer.reset();
        other.reset();
        sink.reset();
    });

    s.step("read the file", [&] {
        std::ifstream in(tracePath);
        ASSERT_TRUE(in.is_open()) << "Failed to open " << tracePath.string();

        fileContent.clear();
        expectedFull.clear();
        expectedOther.clear();

        const std::string needleId = std::format("\"tracer\":{},", id);
        const std::string needleOther = std::format("\"tracer\":{},", otherId);

        for (std::string line; std::getline(in, line);) {
            if (!line.empty() && line.back() == '\r') {
                line.pop_back();
            }
            fileContent += line;
            fileContent += '\n';
            if (line.find("\"kind\":\"diagram\"") != std::string::npos &&
                line.find(needleId) != std::string::npos) {
                expectedFull.push_back(line);
            }
            if (line.find("\"kind\":\"diagram\"") != std::string::npos &&
                line.find(needleOther) != std::string::npos) {
                expectedOther.push_back(line);
            }
        }

        ASSERT_FALSE(expectedFull.empty());
        ASSERT_FALSE(expectedOther.empty());
    });

    s.step("replay to the last event equals the destructor", [&] {
        std::istringstream in(fileContent);
        std::ostringstream out;
        std::ostringstream err;
        const int rc = replay::replay(
            in,
            out,
            err,
            replay::ReplayArgs{ .tracer = id, .until = lastSeq });
        EXPECT_EQ(rc, 0);

        const auto lines = splitLines(out.str());
        EXPECT_EQ(lines, expectedFull);

        const auto errLines = splitLines(err.str());
        ASSERT_FALSE(errLines.empty());
        EXPECT_EQ(errLines.back(), "skipped: 0");
    });

    s.step("replay to the middle equals the Tracer's own range output", [&] {
        std::istringstream in(fileContent);
        std::ostringstream out;
        std::ostringstream err;
        const int rc = replay::replay(
            in,
            out,
            err,
            replay::ReplayArgs{ .tracer = id, .until = mid, .markLast = true });
        EXPECT_EQ(rc, 0);

        const auto lines = splitLines(out.str());
        EXPECT_EQ(lines, expectedMid);

        const std::string joined = out.str();
        EXPECT_NE(joined.find("rect rgba("), std::string::npos);
        EXPECT_EQ(joined.find("act13"), std::string::npos);
    });

    s.step("the other tracer is not mixed in", [&] {
        std::istringstream in(fileContent);
        std::ostringstream out;
        std::ostringstream err;
        const int rc = replay::replay(
            in,
            out,
            err,
            replay::ReplayArgs{
                .tracer = otherId,
                .until = (std::numeric_limits<std::uint64_t>::max)() });
        EXPECT_EQ(rc, 0);

        const auto lines = splitLines(out.str());
        EXPECT_EQ(lines, expectedOther);

        const std::string joined = out.str();
        EXPECT_EQ(joined.find("act1"), std::string::npos);
    });
}
