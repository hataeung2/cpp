/**
 * @file test_diagram_range.cpp
 * @brief atugcc::pattern::viz -- 다이어그램 이벤트 구간(DiagramRange) 자르기 단위 테스트 (Spec 070-07 AC-2)
 *
 * Test groups:
 *   DiagramRange -- 7 unit tests for untilSeq cursor range filtering
 */
#include <gtest/gtest.h>

#include <algorithm>
#include <array>
#include <cstddef>
#include <cstdint>
#include <format>
#include <optional>
#include <source_location>
#include <string>
#include <string_view>
#include <vector>

#include "atugcc/pattern/visualizer.hpp"

namespace viz = atugcc::pattern::viz;

namespace {

// EventMeta has no default for `location`: Clang warns on a designated initializer that skips it
viz::EventMeta metaOf(std::uint64_t seq) {
    viz::EventMeta meta{ .location = std::source_location::current() };
    meta.seq = seq;
    return meta;
}

constexpr std::array<viz::DiagramBackend, 3> kAllBackends = {
    viz::DiagramBackend::PlantUML,
    viz::DiagramBackend::Mermaid,
    viz::DiagramBackend::D2,
};

void expectSameParts(
    const std::vector<viz::DiagramPart>& actual,
    const std::vector<viz::DiagramPart>& expected)
{
    ASSERT_EQ(actual.size(), expected.size());
    for (std::size_t i = 0; i < actual.size(); ++i) {
        EXPECT_EQ(actual[i].kind, expected[i].kind);
        EXPECT_EQ(actual[i].backend, expected[i].backend);
        EXPECT_EQ(actual[i].title, expected[i].title);
        EXPECT_EQ(actual[i].source, expected[i].source);
        EXPECT_EQ(actual[i].overBudget, expected[i].overBudget);
    }
}

std::optional<std::string> findSequenceSource(
    const std::vector<viz::DiagramPart>& parts)
{
    for (const auto& part : parts) {
        if (part.kind == viz::DiagramKind::Sequence) {
            return part.source;
        }
    }
    return std::nullopt;
}

std::size_t countSequenceParts(const std::vector<viz::DiagramPart>& parts) {
    return static_cast<std::size_t>(std::ranges::count_if(
        parts, [](const viz::DiagramPart& p) {
            return p.kind == viz::DiagramKind::Sequence;
        }));
}

struct SampleEvents {
    std::vector<viz::Message> messages;
    std::vector<viz::Transition> transitions;
    std::vector<viz::Node> nodes;
};

SampleEvents createSampleEvents() {
    return SampleEvents{
        .messages = {
            viz::Message{ .from = "A", .to = "B", .action = "m1", .meta = metaOf(1) },
            viz::Message{ .from = "B", .to = "C", .action = "m3", .meta = metaOf(3) },
            viz::Message{ .from = "C", .to = "A", .action = "m5", .meta = metaOf(5) },
        },
        .transitions = {
            viz::Transition{ .old_state = "A", .new_state = "B", .trigger = "t2", .meta = metaOf(2) },
            viz::Transition{ .old_state = "B", .new_state = "C", .trigger = "t4", .meta = metaOf(4) },
            viz::Transition{ .old_state = "C", .new_state = "D", .trigger = "t6", .meta = metaOf(6) },
        },
        .nodes = {
            viz::Node{ .parent = "P", .child = "C", .relation_type = "contains", .meta = metaOf(7) },
        },
    };
}

} // namespace

// ============================================================================
// 1. DefaultRangeEqualsTracerOutput
// ============================================================================
TEST(DiagramRange, DefaultRangeEqualsTracerOutput) {
    viz::Tracer tracer;
    (void)tracer.recordMessage("Alice", "Bob", "hello");
    (void)tracer.recordMessage("Bob", "Alice", "ack");
    (void)tracer.recordTransition("Init", "Ready", "setup");
    (void)tracer.recordTransition("Ready", "Active", "start");
    (void)tracer.pushNode("Root", "Child1", "contains");
    (void)tracer.pushNode("Root", "Child2", "contains");

    const auto msgs = tracer.snapshotMessages();
    const auto trans = tracer.snapshotTransitions();
    const auto nodes = tracer.snapshotNodes();

    for (auto backend : kAllBackends) {
        const auto expected = tracer.diagramParts(backend);
        ASSERT_FALSE(expected.empty());
        const auto actual = viz::diagramPartsOf(msgs, trans, nodes, backend);
        expectSameParts(actual, expected);
    }
}

// ============================================================================
// 2. RangeBeforeFirstEventIsEmpty
// ============================================================================
TEST(DiagramRange, RangeBeforeFirstEventIsEmpty) {
    const auto [msgs, trans, nodes] = createSampleEvents();
    const viz::DiagramRange range{ .untilSeq = 0 };

    for (auto backend : kAllBackends) {
        const auto parts = viz::diagramPartsOf(
            msgs, trans, nodes, backend, {}, range);
        EXPECT_TRUE(parts.empty());
    }
}

// ============================================================================
// 3. RangeInTheMiddleKeepsOnlyEarlierEvents
// ============================================================================
TEST(DiagramRange, RangeInTheMiddleKeepsOnlyEarlierEvents) {
    const auto [msgs, trans, nodes] = createSampleEvents();
    const viz::DiagramRange range{ .untilSeq = 4 };
    const auto parts = viz::diagramPartsOf(
        msgs, trans, nodes, viz::DiagramBackend::Mermaid, {}, range);

    std::optional<std::string> sequenceSource;
    std::optional<std::string> stateSource;
    bool hasStructure = false;

    for (const auto& part : parts) {
        if (part.kind == viz::DiagramKind::Sequence) {
            sequenceSource = part.source;
        } else if (part.kind == viz::DiagramKind::State) {
            stateSource = part.source;
        } else if (part.kind == viz::DiagramKind::Structure) {
            hasStructure = true;
        }
    }

    ASSERT_TRUE(sequenceSource.has_value());
    EXPECT_NE(sequenceSource->find("m1"), std::string::npos);
    EXPECT_NE(sequenceSource->find("m3"), std::string::npos);
    EXPECT_EQ(sequenceSource->find("m5"), std::string::npos);

    ASSERT_TRUE(stateSource.has_value());
    EXPECT_NE(stateSource->find("t2"), std::string::npos);
    EXPECT_NE(stateSource->find("t4"), std::string::npos);
    EXPECT_EQ(stateSource->find("t6"), std::string::npos);

    EXPECT_FALSE(hasStructure);
    EXPECT_EQ(parts.size(), 2u);
}

// ============================================================================
// 4. RangeIncludesTheEventAtUntilSeq
// ============================================================================
TEST(DiagramRange, RangeIncludesTheEventAtUntilSeq) {
    const auto [msgs, trans, nodes] = createSampleEvents();

    const auto parts3 = viz::diagramPartsOf(
        msgs, trans, nodes, viz::DiagramBackend::Mermaid, {}, { .untilSeq = 3 });
    const auto seq3 = findSequenceSource(parts3);
    ASSERT_TRUE(seq3.has_value());
    EXPECT_NE(seq3->find("m3"), std::string::npos);

    const auto parts2 = viz::diagramPartsOf(
        msgs, trans, nodes, viz::DiagramBackend::Mermaid, {}, { .untilSeq = 2 });
    const auto seq2 = findSequenceSource(parts2);
    ASSERT_TRUE(seq2.has_value());
    EXPECT_EQ(seq2->find("m3"), std::string::npos);
}

// ============================================================================
// 5. RangeAtTheEndEqualsNoRange
// ============================================================================
TEST(DiagramRange, RangeAtTheEndEqualsNoRange) {
    const auto [msgs, trans, nodes] = createSampleEvents();

    for (auto backend : kAllBackends) {
        const auto defaultParts = viz::diagramPartsOf(msgs, trans, nodes, backend);
        ASSERT_FALSE(defaultParts.empty());
        const auto rangeParts = viz::diagramPartsOf(
            msgs, trans, nodes, backend, {}, { .untilSeq = 7 });
        expectSameParts(rangeParts, defaultParts);
    }
}

// ============================================================================
// 6. TracerOverloadMatchesFreeFunction
// ============================================================================
TEST(DiagramRange, TracerOverloadMatchesFreeFunction) {
    viz::Tracer tracer;
    for (int i = 1; i <= 6; ++i) {
        (void)tracer.recordMessage("Sender", "Receiver", std::format("action_{}", i));
    }

    const auto msgs = tracer.snapshotMessages();
    ASSERT_EQ(msgs.size(), 6u);
    const auto trans = tracer.snapshotTransitions();
    const auto nodes = tracer.snapshotNodes();

    const std::uint64_t thirdSeq = msgs[2].meta.seq;
    const viz::DiagramRange range{ .untilSeq = thirdSeq };

    const auto tracerParts = tracer.diagramParts(viz::DiagramBackend::Mermaid, {}, range);
    const auto freeParts = viz::diagramPartsOf(
        msgs, trans, nodes, viz::DiagramBackend::Mermaid, {}, range);

    expectSameParts(tracerParts, freeParts);

    const auto seqSource = findSequenceSource(tracerParts);
    ASSERT_TRUE(seqSource.has_value());
    EXPECT_NE(seqSource->find("action_3"), std::string::npos);
    EXPECT_EQ(seqSource->find("action_4"), std::string::npos);
}

// ============================================================================
// 7. SequencePartsStopAtTheCursor
// ============================================================================
TEST(DiagramRange, SequencePartsStopAtTheCursor) {
    viz::Tracer tracer;
    for (int i = 1; i <= 40; ++i) {
        (void)tracer.recordMessage("A", "B", std::format("step_{:02d}", i));
    }

    const auto msgs = tracer.snapshotMessages();
    ASSERT_EQ(msgs.size(), 40u);

    const std::uint64_t seq10 = msgs[9].meta.seq;
    const std::uint64_t seq20 = msgs[19].meta.seq;
    const std::uint64_t seq40 = msgs[39].meta.seq;

    for (auto backend : kAllBackends) {
        const auto parts10 = tracer.diagramParts(backend, {}, { .untilSeq = seq10 });
        EXPECT_EQ(countSequenceParts(parts10), 1u);

        const auto parts20 = tracer.diagramParts(backend, {}, { .untilSeq = seq20 });
        EXPECT_EQ(countSequenceParts(parts20), 2u);

        const auto parts40 = tracer.diagramParts(backend, {}, { .untilSeq = seq40 });
        EXPECT_EQ(countSequenceParts(parts40), 3u);
    }
}

namespace {

std::optional<std::string> findPartSource(
    const std::vector<viz::DiagramPart>& parts,
    viz::DiagramKind kind)
{
    for (const auto& part : parts) {
        if (part.kind == kind) {
            return part.source;
        }
    }
    return std::nullopt;
}

std::size_t countSubstring(std::string_view text, std::string_view sub) {
    if (sub.empty()) {
        return 0;
    }
    std::size_t count = 0;
    std::size_t pos = 0;
    while ((pos = text.find(sub, pos)) != std::string_view::npos) {
        ++count;
        pos += sub.size();
    }
    return count;
}

} // namespace

// ============================================================================
// 8. MarkLastWrapsTheLastMessageInRect
// ============================================================================
TEST(DiagramRange, MarkLastWrapsTheLastMessageInRect) {
    const std::vector<viz::Message> msgs = {
        viz::Message{ .from = "Alice", .to = "Bob", .action = "action1", .meta = metaOf(1) },
        viz::Message{ .from = "Alice", .to = "Bob", .action = "action2", .meta = metaOf(2) },
        viz::Message{ .from = "Alice", .to = "Bob", .action = "action3", .meta = metaOf(3) },
    };

    const auto parts = viz::diagramPartsOf(
        msgs, {}, {}, viz::DiagramBackend::Mermaid, {}, { .markLast = true });
    const auto seq = findSequenceSource(parts);
    ASSERT_TRUE(seq.has_value());
    const std::string& src = *seq;

    const std::string rectTag = "rect rgba(255, 235, 59, 0.35)";
    EXPECT_EQ(countSubstring(src, rectTag), 1u);

    const auto rectPos = src.find(rectTag);
    ASSERT_NE(rectPos, std::string::npos);

    const auto endPos = src.find("end", rectPos);
    ASSERT_NE(endPos, std::string::npos);

    const auto m1Pos = src.find("action1");
    const auto m3Pos = src.find("action3");
    ASSERT_NE(m1Pos, std::string::npos);
    ASSERT_NE(m3Pos, std::string::npos);

    EXPECT_LT(m1Pos, rectPos);
    EXPECT_GT(m3Pos, rectPos);
    EXPECT_LT(m3Pos, endPos);
}

// ============================================================================
// 9. MarkLastFollowsUntilSeq
// ============================================================================
TEST(DiagramRange, MarkLastFollowsUntilSeq) {
    const std::vector<viz::Message> msgs = {
        viz::Message{ .from = "Alice", .to = "Bob", .action = "action1", .meta = metaOf(1) },
        viz::Message{ .from = "Alice", .to = "Bob", .action = "action2", .meta = metaOf(2) },
        viz::Message{ .from = "Alice", .to = "Bob", .action = "action3", .meta = metaOf(3) },
    };

    const auto parts = viz::diagramPartsOf(
        msgs, {}, {}, viz::DiagramBackend::Mermaid, {}, { .untilSeq = 2, .markLast = true });
    const auto seq = findSequenceSource(parts);
    ASSERT_TRUE(seq.has_value());
    const std::string& src = *seq;

    const std::string rectTag = "rect rgba(255, 235, 59, 0.35)";
    EXPECT_EQ(countSubstring(src, rectTag), 1u);

    const auto rectPos = src.find(rectTag);
    ASSERT_NE(rectPos, std::string::npos);

    const auto endPos = src.find("end", rectPos);
    ASSERT_NE(endPos, std::string::npos);

    const auto m1Pos = src.find("action1");
    const auto m2Pos = src.find("action2");
    ASSERT_NE(m1Pos, std::string::npos);
    ASSERT_NE(m2Pos, std::string::npos);

    EXPECT_LT(m1Pos, rectPos);
    EXPECT_GT(m2Pos, rectPos);
    EXPECT_LT(m2Pos, endPos);
    EXPECT_EQ(src.find("action3"), std::string::npos);
}

// ============================================================================
// 10. MarkLastWrapsAMergedRunOnce
// ============================================================================
TEST(DiagramRange, MarkLastWrapsAMergedRunOnce) {
    const std::vector<viz::Message> msgs = {
        viz::Message{ .from = "Alice", .to = "Bob", .action = "ping", .meta = metaOf(1) },
        viz::Message{ .from = "Alice", .to = "Bob", .action = "ping", .meta = metaOf(2) },
        viz::Message{ .from = "Alice", .to = "Bob", .action = "ping", .meta = metaOf(3) },
    };

    const auto parts = viz::diagramPartsOf(
        msgs, {}, {}, viz::DiagramBackend::Mermaid, {}, { .markLast = true });
    const auto seq = findSequenceSource(parts);
    ASSERT_TRUE(seq.has_value());
    const std::string& src = *seq;

    const std::string rectTag = "rect rgba(255, 235, 59, 0.35)";
    EXPECT_EQ(countSubstring(src, rectTag), 1u);
    EXPECT_NE(src.find("\xC3\x97" "3"), std::string::npos);

    const auto rectPos = src.find(rectTag);
    ASSERT_NE(rectPos, std::string::npos);

    const auto endPos = src.find("end", rectPos);
    ASSERT_NE(endPos, std::string::npos);

    const auto actionPos = src.find("ping");
    ASSERT_NE(actionPos, std::string::npos);
    EXPECT_GT(actionPos, rectPos);
    EXPECT_LT(actionPos, endPos);

    EXPECT_EQ(countSubstring(src, "->>"), 1u);
}

// ============================================================================
// 11. MarkLastMarksTheArrivalStateOfTheLastTransition
// ============================================================================
TEST(DiagramRange, MarkLastMarksTheArrivalStateOfTheLastTransition) {
    const std::vector<viz::Transition> trans = {
        viz::Transition{ .old_state = "A", .new_state = "B", .trigger = "t1", .meta = metaOf(1) },
        viz::Transition{ .old_state = "B", .new_state = "C", .trigger = "t2", .meta = metaOf(2) },
    };

    const auto parts = viz::diagramPartsOf(
        {}, trans, {}, viz::DiagramBackend::Mermaid, {}, { .markLast = true });
    ASSERT_EQ(parts.size(), 1u);
    EXPECT_EQ(parts[0].kind, viz::DiagramKind::State);
    const std::string& src = parts[0].source;

    EXPECT_EQ(countSubstring(src, "classDef current"), 1u);
    EXPECT_NE(src.find("class C current"), std::string::npos);
    EXPECT_EQ(src.find("class B current"), std::string::npos);
}

// ============================================================================
// 12. MarkLastQuotedStateGetsNoClass
// ============================================================================
TEST(DiagramRange, MarkLastQuotedStateGetsNoClass) {
    const std::vector<viz::Transition> trans = {
        viz::Transition{ .old_state = "Init", .new_state = "in progress", .trigger = "start", .meta = metaOf(1) },
    };

    const auto parts = viz::diagramPartsOf(
        {}, trans, {}, viz::DiagramBackend::Mermaid, {}, { .markLast = true });
    ASSERT_EQ(parts.size(), 1u);
    EXPECT_EQ(parts[0].kind, viz::DiagramKind::State);
    const std::string& src = parts[0].source;

    EXPECT_EQ(src.find("classDef"), std::string::npos);
    EXPECT_EQ(src.find("class "), std::string::npos);
    EXPECT_NE(src.find("Init --> \"in progress\""), std::string::npos);
}

// ============================================================================
// 13. MarkLastStylesTheChildOfTheLastNode
// ============================================================================
TEST(DiagramRange, MarkLastStylesTheChildOfTheLastNode) {
    const std::vector<viz::Node> nodes = {
        viz::Node{ .parent = "Root", .child = "A", .relation_type = "contains", .meta = metaOf(1) },
        viz::Node{ .parent = "A", .child = "B", .relation_type = "contains", .meta = metaOf(2) },
    };

    const auto parts = viz::diagramPartsOf(
        {}, {}, nodes, viz::DiagramBackend::Mermaid, {}, { .markLast = true });
    ASSERT_EQ(parts.size(), 1u);
    EXPECT_EQ(parts[0].kind, viz::DiagramKind::Structure);
    const std::string& src = parts[0].source;

    // the child of the marked relation A --> B is styled; Root and A are not
    EXPECT_NE(src.find("    style B fill:#fff3b0,stroke:#e0a800,color:#000\n"), std::string::npos);
    EXPECT_EQ(src.find("style A"), std::string::npos);
    EXPECT_EQ(src.find("style Root"), std::string::npos);
    EXPECT_EQ(src.find("linkStyle"), std::string::npos);  // classDiagram has no linkStyle
}

// ============================================================================
// 14. MarkLastPicksTheKindWithTheLargestSeq
// ============================================================================
TEST(DiagramRange, MarkLastPicksTheKindWithTheLargestSeq) {
    const std::vector<viz::Message> msgs = {
        viz::Message{ .from = "A", .to = "B", .action = "m1", .meta = metaOf(1) },
        viz::Message{ .from = "B", .to = "C", .action = "m3", .meta = metaOf(3) },
    };
    const std::vector<viz::Transition> trans = {
        viz::Transition{ .old_state = "S1", .new_state = "S2", .trigger = "t2", .meta = metaOf(2) },
        viz::Transition{ .old_state = "S2", .new_state = "S3", .trigger = "t4", .meta = metaOf(4) },
    };
    const std::vector<viz::Node> nodes = {
        viz::Node{ .parent = "Root", .child = "Leaf", .relation_type = "contains", .meta = metaOf(5) },
    };

    // 1) markLast default untilSeq (max seq = 5, Structure)
    {
        const auto parts = viz::diagramPartsOf(
            msgs, trans, nodes, viz::DiagramBackend::Mermaid, {}, { .markLast = true });
        const auto seqSrc = findPartSource(parts, viz::DiagramKind::Sequence);
        const auto stateSrc = findPartSource(parts, viz::DiagramKind::State);
        const auto structSrc = findPartSource(parts, viz::DiagramKind::Structure);

        ASSERT_TRUE(seqSrc.has_value());
        ASSERT_TRUE(stateSrc.has_value());
        ASSERT_TRUE(structSrc.has_value());

        EXPECT_EQ(seqSrc->find("rect"), std::string::npos);
        EXPECT_EQ(stateSrc->find("classDef"), std::string::npos);
        EXPECT_NE(structSrc->find("style Leaf fill:#fff3b0"), std::string::npos);
    }

    // 2) untilSeq = 4 (max seq = 4, State)
    {
        const auto parts = viz::diagramPartsOf(
            msgs, trans, nodes, viz::DiagramBackend::Mermaid, {}, { .untilSeq = 4, .markLast = true });
        const auto seqSrc = findPartSource(parts, viz::DiagramKind::Sequence);
        const auto stateSrc = findPartSource(parts, viz::DiagramKind::State);

        ASSERT_TRUE(seqSrc.has_value());
        ASSERT_TRUE(stateSrc.has_value());

        EXPECT_EQ(seqSrc->find("rect"), std::string::npos);
        EXPECT_NE(stateSrc->find("classDef current"), std::string::npos);
        EXPECT_NE(stateSrc->find("class S3 current"), std::string::npos);
    }

    // 3) untilSeq = 3 (max seq = 3, Sequence)
    {
        const auto parts = viz::diagramPartsOf(
            msgs, trans, nodes, viz::DiagramBackend::Mermaid, {}, { .untilSeq = 3, .markLast = true });
        const auto seqSrc = findPartSource(parts, viz::DiagramKind::Sequence);
        const auto stateSrc = findPartSource(parts, viz::DiagramKind::State);

        ASSERT_TRUE(seqSrc.has_value());
        ASSERT_TRUE(stateSrc.has_value());

        EXPECT_NE(seqSrc->find("rect rgba(255, 235, 59, 0.35)"), std::string::npos);
        EXPECT_EQ(stateSrc->find("classDef"), std::string::npos);
    }
}

// ============================================================================
// 15. MarkLastIsIgnoredByPlantUmlAndD2
// ============================================================================
TEST(DiagramRange, MarkLastIsIgnoredByPlantUmlAndD2) {
    const auto [msgs, trans, nodes] = createSampleEvents();
    for (auto backend : { viz::DiagramBackend::PlantUML, viz::DiagramBackend::D2 }) {
        const auto defaultParts = viz::diagramPartsOf(msgs, trans, nodes, backend);
        const auto markedParts = viz::diagramPartsOf(
            msgs, trans, nodes, backend, {}, { .markLast = true });
        expectSameParts(markedParts, defaultParts);
    }
}

// ============================================================================
// 16. MarkLastOffChangesNothing
// ============================================================================
TEST(DiagramRange, MarkLastOffChangesNothing) {
    const auto [msgs, trans, nodes] = createSampleEvents();
    const auto parts = viz::diagramPartsOf(
        msgs, trans, nodes, viz::DiagramBackend::Mermaid, {}, { .markLast = false });

    ASSERT_FALSE(parts.empty());
    for (const auto& part : parts) {
        EXPECT_EQ(part.source.find("rect"), std::string::npos);
        EXPECT_EQ(part.source.find("classDef"), std::string::npos);
        EXPECT_EQ(part.source.find("style "), std::string::npos);
    }
}

// ============================================================================
// 17. MarkInADuplicateStructureRelation
// ============================================================================
TEST(DiagramRange, MarkInADuplicateStructureRelation) {
    const std::vector<viz::Node> nodes = {
        viz::Node{ .parent = "Root", .child = "A", .relation_type = "contains", .meta = metaOf(1) },
        viz::Node{ .parent = "A", .child = "B", .relation_type = "contains", .meta = metaOf(2) },
        viz::Node{ .parent = "Root", .child = "A", .relation_type = "contains", .meta = metaOf(3) },
    };

    const auto parts = viz::diagramPartsOf(
        {}, {}, nodes, viz::DiagramBackend::Mermaid, {}, { .markLast = true });
    ASSERT_EQ(parts.size(), 1u);
    EXPECT_EQ(parts[0].kind, viz::DiagramKind::Structure);
    const std::string& src = parts[0].source;

    // the duplicate (seq 3) is dropped from the diagram; its first occurrence Root --> A is relation line 0
    EXPECT_NE(src.find("style A fill:#fff3b0"), std::string::npos);
    EXPECT_EQ(src.find("style B"), std::string::npos);
    EXPECT_EQ(countSubstring(src, "Root --> A"), 1u);
}


// ============================================================================
// 18. MarkLastTieGoesToSequenceThenState
// ============================================================================
TEST(DiagramRange, MarkLastTieGoesToSequenceThenState) {
    const std::vector<viz::Message> msgs = {
        viz::Message{ .from = "A", .to = "B", .action = "m", .meta = metaOf(5) },
    };
    const std::vector<viz::Transition> trans = {
        viz::Transition{ .old_state = "S1", .new_state = "S2", .trigger = "t", .meta = metaOf(5) },
    };
    const std::vector<viz::Node> nodes = {
        viz::Node{ .parent = "Root", .child = "Leaf", .relation_type = "contains", .meta = metaOf(5) },
    };

    {
        const auto parts = viz::diagramPartsOf(
            msgs, trans, nodes, viz::DiagramBackend::Mermaid, {}, { .markLast = true });
        EXPECT_NE(findPartSource(parts, viz::DiagramKind::Sequence)->find("rect"), std::string::npos);
        EXPECT_EQ(findPartSource(parts, viz::DiagramKind::State)->find("classDef"), std::string::npos);
        EXPECT_EQ(findPartSource(parts, viz::DiagramKind::Structure)->find("style Leaf"), std::string::npos);
    }
    {
        const auto parts = viz::diagramPartsOf(
            {}, trans, nodes, viz::DiagramBackend::Mermaid, {}, { .markLast = true });
        EXPECT_NE(findPartSource(parts, viz::DiagramKind::State)->find("classDef current"), std::string::npos);
        EXPECT_EQ(findPartSource(parts, viz::DiagramKind::Structure)->find("style Leaf"), std::string::npos);
    }
}

// ============================================================================
// 19. MarkLastOnlyTheChunkWithTheMessageHasRect
// ============================================================================
TEST(DiagramRange, MarkLastOnlyTheChunkWithTheMessageHasRect) {
    std::vector<viz::Message> msgs;
    for (std::uint64_t i = 1; i <= 20; ++i) {
        msgs.push_back(viz::Message{
            .from = "A", .to = "B", .action = std::format("act{}", i), .meta = metaOf(i) });
    }

    // default budget: 15 messages per part -> two chunks (15 + 5); the 20th message is in the second
    const auto parts = viz::diagramPartsOf(
        msgs, {}, {}, viz::DiagramBackend::Mermaid, {}, { .markLast = true });
    ASSERT_EQ(parts.size(), 2u);
    EXPECT_EQ(countSubstring(parts[0].source, "rect"), 0u);
    EXPECT_EQ(countSubstring(parts[1].source, "rect rgba("), 1u);
    EXPECT_NE(parts[1].source.find("act20"), std::string::npos);
}

// ============================================================================
// 20. MarkLastQuotedStructureChildGetsNoStyle
// ============================================================================
TEST(DiagramRange, MarkLastQuotedStructureChildGetsNoStyle) {
    const std::vector<viz::Node> nodes = {
        viz::Node{ .parent = "Root", .child = "my child", .relation_type = "contains", .meta = metaOf(1) },
    };

    const auto parts = viz::diagramPartsOf(
        {}, {}, nodes, viz::DiagramBackend::Mermaid, {}, { .markLast = true });
    ASSERT_EQ(parts.size(), 1u);
    EXPECT_EQ(parts[0].source.find("style "), std::string::npos);
    EXPECT_NE(parts[0].source.find("Root --> \"my child\""), std::string::npos);
}
