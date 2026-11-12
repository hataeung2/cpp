/**
 * @file test_event_reader.cpp
 * @brief atugcc::tools::replay -- event reader (JSON Lines) tests (Spec 070-07 Assumption 7, AC-4)
 *
 * Test group:
 *   EventReader -- 12 unit tests for JSON Lines stream parsing, escaping, filtering, and sorting
 */
#include <gtest/gtest.h>

#include <cstdint>
#include <limits>
#include <optional>
#include <sstream>
#include <string>
#include <string_view>
#include <vector>

#include "event_reader.hpp"
#include "replay.hpp"

namespace viz = atugcc::pattern::viz;
namespace replay = atugcc::tools::replay;

// ============================================================================
// EventReader
// ============================================================================

TEST(EventReader, RoundTripsEveryEventKind) {
    viz::Tracer tracer;
    ASSERT_TRUE(tracer.recordMessage("Alice", "Bob", "sayHello()").has_value());
    ASSERT_TRUE(tracer.recordTransition("StateA", "StateB", "onTrigger").has_value());
    ASSERT_TRUE(tracer.pushNode("ParentNode", "ChildNode", "relatesTo").has_value());

    const auto msgs = tracer.snapshotMessages();
    const auto trans = tracer.snapshotTransitions();
    const auto nodes = tracer.snapshotNodes();
    ASSERT_EQ(msgs.size(), 1u);
    ASSERT_EQ(trans.size(), 1u);
    ASSERT_EQ(nodes.size(), 1u);

    const auto tracer_id = msgs[0].meta.tracerId;
    const std::string input = viz::toJsonLine(msgs[0]) + "\n" +
                              viz::toJsonLine(trans[0]) + "\n" +
                              viz::toJsonLine(nodes[0]) + "\n";
    std::istringstream in(input);
    const auto events = replay::readEvents(in, tracer_id);

    EXPECT_EQ(events.skipped, 0u);
    ASSERT_EQ(events.messages.size(), 1u);
    EXPECT_EQ(events.messages[0].from, "Alice");
    EXPECT_EQ(events.messages[0].to, "Bob");
    EXPECT_EQ(events.messages[0].action, "sayHello()");
    EXPECT_EQ(events.messages[0].meta.seq, msgs[0].meta.seq);
    EXPECT_EQ(events.messages[0].meta.tracerId, tracer_id);

    ASSERT_EQ(events.transitions.size(), 1u);
    EXPECT_EQ(events.transitions[0].old_state, "StateA");
    EXPECT_EQ(events.transitions[0].new_state, "StateB");
    EXPECT_EQ(events.transitions[0].trigger, "onTrigger");
    EXPECT_EQ(events.transitions[0].meta.seq, trans[0].meta.seq);
    EXPECT_EQ(events.transitions[0].meta.tracerId, tracer_id);

    ASSERT_EQ(events.nodes.size(), 1u);
    EXPECT_EQ(events.nodes[0].parent, "ParentNode");
    EXPECT_EQ(events.nodes[0].child, "ChildNode");
    EXPECT_EQ(events.nodes[0].relation_type, "relatesTo");
    EXPECT_EQ(events.nodes[0].meta.seq, nodes[0].meta.seq);
    EXPECT_EQ(events.nodes[0].meta.tracerId, tracer_id);
}

TEST(EventReader, RoundTripsEscapesAndUtf8) {
    viz::EventMeta meta{ .location = std::source_location::current() };
    meta.seq = 100;
    meta.tracerId = 42;

    const std::string from_str = "a\"b\\c";
    const std::string to_str = "line\nnewline\ttab\x01" "ctl\x1f" "end";
    const std::string action_str = std::string("상태 전이 ") + "\xF0\x9F\x98\x80";

    const viz::Message original{
        .from = from_str,
        .to = to_str,
        .action = action_str,
        .meta = meta,
    };

    const auto line = viz::toJsonLine(original);
    std::istringstream in(line + "\n");
    const auto events = replay::readEvents(in, 42);

    EXPECT_EQ(events.skipped, 0u);
    ASSERT_EQ(events.messages.size(), 1u);
    EXPECT_EQ(events.messages[0].from, from_str);
    EXPECT_EQ(events.messages[0].to, to_str);
    EXPECT_EQ(events.messages[0].action, action_str);
    EXPECT_EQ(events.messages[0].meta.seq, 100u);
    EXPECT_EQ(events.messages[0].meta.tracerId, 42u);
}

TEST(EventReader, DecodesUnicodeEscapes) {
    const std::string line = R"({"v":1,"kind":"message","seq":1,"tracer":1,"from":"A","to":"B","action":"\u00e9\uD83D\uDE00A"})";
    std::istringstream in(line + "\n");
    const auto events = replay::readEvents(in, 1);

    EXPECT_EQ(events.skipped, 0u);
    ASSERT_EQ(events.messages.size(), 1u);
    const std::string expected = "\xC3\xA9\xF0\x9F\x98\x80" "A";
    EXPECT_EQ(events.messages[0].action, expected);
}

TEST(EventReader, LoneSurrogateAndBadHexAreSkipped) {
    const std::string input =
        R"({"v":1,"kind":"message","seq":1,"tracer":1,"from":"A","to":"B","action":"\uD83D"})" "\n"
        R"({"v":1,"kind":"message","seq":2,"tracer":1,"from":"A","to":"B","action":"\uDE00"})" "\n"
        R"({"v":1,"kind":"message","seq":3,"tracer":1,"from":"A","to":"B","action":"\u12G4"})" "\n";
    std::istringstream in(input);
    const auto events = replay::readEvents(in, 1);

    EXPECT_EQ(events.skipped, 3u);
    EXPECT_TRUE(events.messages.empty());
    EXPECT_TRUE(events.transitions.empty());
    EXPECT_TRUE(events.nodes.empty());
}

TEST(EventReader, UnknownKeysWhitespaceAndScalarsAreAccepted) {
    const std::string line =
        R"({"v": 1, "kind": "message", "seq": 5, "tracer": 1, "from": "A", "to": "B", "action": "test", "x": true, "y": null, "z": -5, "w": "s"})";
    std::istringstream in(line + "\n");
    const auto events = replay::readEvents(in, 1);

    EXPECT_EQ(events.skipped, 0u);
    ASSERT_EQ(events.messages.size(), 1u);
    EXPECT_EQ(events.messages[0].from, "A");
    EXPECT_EQ(events.messages[0].to, "B");
    EXPECT_EQ(events.messages[0].action, "test");
    EXPECT_EQ(events.messages[0].meta.seq, 5u);
    EXPECT_EQ(events.messages[0].meta.tracerId, 1u);
}

TEST(EventReader, BrokenLinesAreSkippedAndCounted) {
    const std::string input =
        "not json\n"
        R"({"v":1,"kind":"message")" "\n"
        R"({"v":1,"kind":"message","seq":1,"tracer":1,"from":"A","to":"B","action":"first"})" "\n"
        R"({"v":1} x)" "\n"
        R"({"v":1,"kind":"message","extra":{"a":1}})" "\n"
        R"({"v":1,"kind":"message","seq":2,"tracer":1,"from":"B","to":"A","action":"second"})" "\n"
        R"({"v":1,"kind":"message","seq":"3","tracer":1,"from":"A","to":"B","action":"third"})" "\n";
    std::istringstream in(input);
    const auto events = replay::readEvents(in, 1);

    EXPECT_EQ(events.skipped, 5u);
    ASSERT_EQ(events.messages.size(), 2u);
    EXPECT_EQ(events.messages[0].action, "first");
    EXPECT_EQ(events.messages[0].meta.seq, 1u);
    EXPECT_EQ(events.messages[1].action, "second");
    EXPECT_EQ(events.messages[1].meta.seq, 2u);
}

TEST(EventReader, MissingFieldAndUnknownKindAreSkipped) {
    const std::string input =
        R"({"v":1,"kind":"message","seq":1,"tracer":1,"from":"A","to":"B"})" "\n"
        R"({"v":1,"kind":"transition","seq":2,"tracer":1,"old":"S1","trigger":"t1"})" "\n"
        R"({"v":1,"kind":"node","seq":3,"tracer":1,"parent":"P","child":"C"})" "\n"
        R"({"v":1,"kind":"widget","seq":4,"tracer":1,"foo":"bar"})" "\n";
    std::istringstream in(input);
    const auto events = replay::readEvents(in, 1);

    EXPECT_EQ(events.skipped, 4u);
    EXPECT_TRUE(events.messages.empty());
    EXPECT_TRUE(events.transitions.empty());
    EXPECT_TRUE(events.nodes.empty());
}

TEST(EventReader, OtherVersionIsSkippedAndCounted) {
    const std::string input =
        R"({"v":2,"kind":"message","seq":1,"tracer":1,"from":"A","to":"B","action":"act1"})" "\n"
        R"({"kind":"message","seq":2,"tracer":1,"from":"A","to":"B","action":"act2"})" "\n"
        R"({"v":1,"kind":"message","seq":3,"tracer":1,"from":"A","to":"B","action":"act3"})" "\n";
    std::istringstream in(input);
    const auto events = replay::readEvents(in, 1);

    EXPECT_EQ(events.skipped, 2u);
    ASSERT_EQ(events.messages.size(), 1u);
    EXPECT_EQ(events.messages[0].action, "act3");
    EXPECT_EQ(events.messages[0].meta.seq, 3u);
}

TEST(EventReader, OtherTracerSpanAndDiagramAreIgnoredWithoutCounting) {
    const viz::DiagramPart part{
        .kind = viz::DiagramKind::Sequence,
        .backend = viz::DiagramBackend::Mermaid,
        .title = "t",
        .source = "s",
        .overBudget = false,
    };
    const std::string diagram_line = viz::toJsonLine(1, 0, 1, part);
    const std::string input =
        R"({"v":1,"kind":"message","seq":1,"tracer":1,"from":"A","to":"B","action":"act"})" "\n"
        R"({"v":1,"kind":"message","seq":2,"tracer":2,"from":"C","to":"D","action":"other"})" "\n"
        R"({"v":1,"kind":"span","seq":9,"tracer":1,"label":"x","meter":"wall","durationNs":5})" "\n" +
        diagram_line + "\n";

    std::istringstream in(input);
    const auto events = replay::readEvents(in, 1);

    EXPECT_EQ(events.skipped, 0u);
    ASSERT_EQ(events.messages.size(), 1u);
    EXPECT_EQ(events.messages[0].from, "A");
    EXPECT_EQ(events.messages[0].meta.tracerId, 1u);
    EXPECT_TRUE(events.transitions.empty());
    EXPECT_TRUE(events.nodes.empty());
}

TEST(EventReader, ListsAreSortedBySeq) {
    const std::string input =
        R"({"v":1,"kind":"message","seq":3,"tracer":1,"from":"A","to":"B","action":"m3"})" "\n"
        R"({"v":1,"kind":"message","seq":1,"tracer":1,"from":"A","to":"B","action":"m1"})" "\n"
        R"({"v":1,"kind":"message","seq":2,"tracer":1,"from":"A","to":"B","action":"m2"})" "\n"
        R"({"v":1,"kind":"transition","seq":7,"tracer":1,"old":"S1","new":"S2","trigger":"b"})" "\n"
        R"({"v":1,"kind":"transition","seq":7,"tracer":1,"old":"S1","new":"S2","trigger":"a"})" "\n"
        R"({"v":1,"kind":"transition","seq":2,"tracer":1,"old":"S0","new":"S1","trigger":"first"})" "\n"
        R"({"v":1,"kind":"node","seq":9,"tracer":1,"parent":"R","child":"late","relation":"contains"})" "\n"
        R"({"v":1,"kind":"node","seq":4,"tracer":1,"parent":"R","child":"early","relation":"contains"})" "\n";

    std::istringstream in(input);
    const auto events = replay::readEvents(in, 1);

    EXPECT_EQ(events.skipped, 0u);
    ASSERT_EQ(events.messages.size(), 3u);
    EXPECT_EQ(events.messages[0].meta.seq, 1u);
    EXPECT_EQ(events.messages[0].action, "m1");
    EXPECT_EQ(events.messages[1].meta.seq, 2u);
    EXPECT_EQ(events.messages[1].action, "m2");
    EXPECT_EQ(events.messages[2].meta.seq, 3u);
    EXPECT_EQ(events.messages[2].action, "m3");

    // equal seq keeps the file order ("b" before "a": a non-stable sort or a sort by trigger would swap them)
    ASSERT_EQ(events.transitions.size(), 3u);
    EXPECT_EQ(events.transitions[0].trigger, "first");
    EXPECT_EQ(events.transitions[1].trigger, "b");
    EXPECT_EQ(events.transitions[2].trigger, "a");

    ASSERT_EQ(events.nodes.size(), 2u);
    EXPECT_EQ(events.nodes[0].child, "early");
    EXPECT_EQ(events.nodes[1].child, "late");
}

TEST(EventReader, CarriageReturnsAndEmptyLinesAreTolerated) {
    const std::string input =
        "\r\n"
        R"({"v":1,"kind":"message","seq":1,"tracer":1,"from":"A","to":"B","action":"m1"})" "\r\n"
        "\r\n"
        "\r\n"
        R"({"v":1,"kind":"transition","seq":2,"tracer":1,"old":"S1","new":"S2","trigger":"t1"})" "\r\n"
        "\r\n";

    std::istringstream in(input);
    const auto events = replay::readEvents(in, 1);

    EXPECT_EQ(events.skipped, 0u);
    ASSERT_EQ(events.messages.size(), 1u);
    EXPECT_EQ(events.messages[0].action, "m1");
    ASSERT_EQ(events.transitions.size(), 1u);
    EXPECT_EQ(events.transitions[0].trigger, "t1");
}

TEST(EventReader, EmptyInputGivesEmptySet) {
    std::istringstream in("");
    const auto events = replay::readEvents(in, 1);

    EXPECT_EQ(events.skipped, 0u);
    EXPECT_TRUE(events.messages.empty());
    EXPECT_TRUE(events.transitions.empty());
    EXPECT_TRUE(events.nodes.empty());
}

// ReplayArgs: the tool's command line (spec 070-07 Assumption 7)
namespace {

std::optional<replay::ReplayArgs> parse(const std::vector<std::string_view>& args, std::string& err_text) {
    std::ostringstream err;
    const auto result = replay::parseArgs(args, err);
    err_text = err.str();
    return result;
}

} // namespace

TEST(ReplayArgs, ParsesTracerUntilAndMarkLast) {
    std::string err;
    const auto args = parse({ "--tracer", "3", "--until", "42", "--mark-last" }, err);
    ASSERT_TRUE(args.has_value());
    EXPECT_EQ(args->tracer, 3u);
    EXPECT_EQ(args->until, 42u);
    EXPECT_TRUE(args->markLast);
    EXPECT_TRUE(err.empty());
}

TEST(ReplayArgs, UntilDefaultsToEverythingAndMarkToOff) {
    std::string err;
    const auto args = parse({ "--tracer", "1" }, err);
    ASSERT_TRUE(args.has_value());
    EXPECT_EQ(args->until, (std::numeric_limits<std::uint64_t>::max)());
    EXPECT_FALSE(args->markLast);
}

TEST(ReplayArgs, RejectsBadCommandLinesWithUsage) {
    const std::vector<std::vector<std::string_view>> bad_lines = {
        {}, { "--until", "5" }, { "--tracer" }, { "--tracer", "x" }, { "--tracer", "-1" },
        { "--tracer", "1", "--bogus" }, { "--tracer", "1", "--until", "5x" },
        { "--tracer", "99999999999" },
    };
    for (const auto& bad : bad_lines) {
        std::string err;
        EXPECT_FALSE(parse(bad, err).has_value()) << "args: " << bad.size();
        EXPECT_NE(err.find("usage: atugcc_diagram_replay"), std::string::npos);
    }
}
