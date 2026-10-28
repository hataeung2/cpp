/**
 * @file test_event_stream.cpp
 * @brief atugcc::pattern::viz -- event stream (seq, TraceEventSink, JSON Lines) tests
 *
 * Test groups:
 *   EventStream -- seq / tracerId assignment, sink delivery, destructor diagram parts
 *   JsonLines   -- toJsonLine schema and escaping, JsonLinesEventSink file output
 *
 * The ATUGCC_TRACE_OUT path (process-wide sink) is covered by check_trace_stream.py,
 * because environmentEventSink() reads the variable once per process.
 */
#include <gtest/gtest.h>

#include <chrono>
#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <latch>
#include <memory>
#include <mutex>
#include <set>
#include <string>
#include <thread>
#include <vector>

#include "atugcc/pattern/visualizer.hpp"

namespace viz = atugcc::pattern::viz;

namespace {

class CountingSink final : public viz::TraceEventSink {
public:
    void onEvent(const viz::Message& event) override {
        std::lock_guard lock(mutex_);
        seqs.push_back(event.meta.seq);
        ++messages;
    }
    void onEvent(const viz::Transition& event) override {
        std::lock_guard lock(mutex_);
        seqs.push_back(event.meta.seq);
        ++transitions;
    }
    void onEvent(const viz::Node& event) override {
        std::lock_guard lock(mutex_);
        seqs.push_back(event.meta.seq);
        ++nodes;
    }
    void onDiagramParts(std::uint32_t tracerId, const std::vector<viz::DiagramPart>& parts) override {
        std::lock_guard lock(mutex_);
        diagram_tracer_id = tracerId;
        diagram_parts = parts;
        ++diagram_calls;
    }

    std::vector<std::uint64_t>     seqs;
    std::size_t                    messages{ 0 };
    std::size_t                    transitions{ 0 };
    std::size_t                    nodes{ 0 };
    std::size_t                    diagram_calls{ 0 };
    std::uint32_t                  diagram_tracer_id{ 0 };
    std::vector<viz::DiagramPart>  diagram_parts;

private:
    std::mutex mutex_;
};

std::filesystem::path tempTracePath(const char* tag) {
    const auto ticks = std::chrono::steady_clock::now().time_since_epoch().count();
    return std::filesystem::temp_directory_path() /
        ("atugcc_event_stream_" + std::string(tag) + "_" + std::to_string(ticks) + ".jsonl");
}

std::vector<std::string> readLines(const std::filesystem::path& path) {
    std::ifstream in(path, std::ios::binary);
    std::vector<std::string> lines;
    for (std::string line; std::getline(in, line);) {
        lines.push_back(line);
    }
    return lines;
}

bool contains(const std::string& text, const std::string& part) {
    return text.find(part) != std::string::npos;
}

viz::EventMeta fixedMeta(std::uint64_t seq, std::uint32_t tracerId) {
    viz::EventMeta meta{ .location = std::source_location::current() };
    meta.seq = seq;
    meta.tracerId = tracerId;
    return meta;
}

} // namespace

// ============================================================================
// EventStream
// ============================================================================

TEST(EventStream, SeqStrictlyIncreasesWithinTracer) {
    viz::Tracer tracer;
    ASSERT_TRUE(tracer.recordMessage("A", "B", "first()").has_value());
    ASSERT_TRUE(tracer.recordTransition("IDLE", "RUN", "start").has_value());
    ASSERT_TRUE(tracer.pushNode("Root", "Leaf", "contains").has_value());
    ASSERT_TRUE(tracer.recordMessage("B", "A", "second()").has_value());

    const auto messages    = tracer.snapshotMessages();
    const auto transitions = tracer.snapshotTransitions();
    const auto nodes       = tracer.snapshotNodes();
    ASSERT_EQ(messages.size(), 2u);
    ASSERT_EQ(transitions.size(), 1u);
    ASSERT_EQ(nodes.size(), 1u);

    // record order: message, transition, node, message
    const std::vector<std::uint64_t> in_record_order{
        messages[0].meta.seq, transitions[0].meta.seq, nodes[0].meta.seq, messages[1].meta.seq };
    EXPECT_GT(in_record_order[0], 0u);
    for (std::size_t i = 1; i < in_record_order.size(); ++i) {
        EXPECT_LT(in_record_order[i - 1], in_record_order[i]) << "index " << i;
    }

    EXPECT_EQ(messages[0].meta.tracerId, tracer.id());
    EXPECT_EQ(transitions[0].meta.tracerId, tracer.id());
    EXPECT_EQ(nodes[0].meta.tracerId, tracer.id());
    EXPECT_EQ(messages[1].meta.tracerId, tracer.id());
}

TEST(EventStream, SeqDisjointAcrossTracers) {
    viz::Tracer first;
    viz::Tracer second;
    EXPECT_NE(first.id(), second.id());

    for (int i = 0; i < 10; ++i) {
        ASSERT_TRUE(first.recordMessage("A", "B", "ping()").has_value());
        ASSERT_TRUE(second.recordMessage("C", "D", "pong()").has_value());
    }

    std::set<std::uint64_t> seqs;
    for (const auto& m : first.snapshotMessages()) {
        EXPECT_EQ(m.meta.tracerId, first.id());
        seqs.insert(m.meta.seq);
    }
    for (const auto& m : second.snapshotMessages()) {
        EXPECT_EQ(m.meta.tracerId, second.id());
        seqs.insert(m.meta.seq);
    }
    EXPECT_EQ(seqs.size(), 20u);
}

TEST(EventStream, SinkReceivesEveryRecordedEvent) {
    auto sink = std::make_shared<CountingSink>();
    viz::Tracer tracer;
    tracer.setEventSink(sink);
    EXPECT_EQ(tracer.eventSink(), sink);

    ASSERT_TRUE(tracer.recordMessage("A", "B", "go()").has_value());
    ASSERT_TRUE(tracer.recordTransition("IDLE", "RUN", "start").has_value());
    ASSERT_TRUE(tracer.pushNode("Root", "Leaf", "contains").has_value());

    EXPECT_EQ(sink->messages, 1u);
    EXPECT_EQ(sink->transitions, 1u);
    EXPECT_EQ(sink->nodes, 1u);
    ASSERT_EQ(sink->seqs.size(), 3u);
    EXPECT_EQ(sink->seqs[0], tracer.snapshotMessages()[0].meta.seq);
}

TEST(EventStream, RejectedEventReachesNoSink) {
    auto sink = std::make_shared<CountingSink>();
    viz::Tracer tracer{ 1 };
    tracer.setEventSink(sink);

    EXPECT_TRUE(tracer.recordMessage("A", "B", "accepted()").has_value());
    EXPECT_FALSE(tracer.recordMessage("A", "B", "rejected()").has_value());

    EXPECT_EQ(sink->messages, 1u);
    EXPECT_EQ(tracer.snapshotMessages().size(), 1u);
}

TEST(EventStream, NullSinkDisablesStreaming) {
    auto sink = std::make_shared<CountingSink>();
    {
        viz::Tracer tracer;
        tracer.setEventSink(sink);
        tracer.setEventSink(nullptr);
        EXPECT_EQ(tracer.eventSink(), nullptr);
        ASSERT_TRUE(tracer.recordMessage("A", "B", "go()").has_value());
    }
    EXPECT_EQ(sink->messages, 0u);
    EXPECT_EQ(sink->diagram_calls, 0u);
}

TEST(EventStream, DestructorEmitsMermaidParts) {
    auto sink = std::make_shared<CountingSink>();
    std::size_t expected_parts = 0;
    std::uint32_t expected_id = 0;
    {
        viz::Tracer tracer;
        tracer.setEventSink(sink);
        // 20 distinct messages > default budget of 15 per part -> the sequence splits in two
        for (int i = 0; i < 20; ++i) {
            ASSERT_TRUE(tracer.recordMessage("A", "B", "step" + std::to_string(i) + "()").has_value());
        }
        ASSERT_TRUE(tracer.recordTransition("IDLE", "RUN", "start").has_value());
        ASSERT_TRUE(tracer.pushNode("Root", "Leaf", "contains").has_value());
        expected_parts = tracer.diagramParts(viz::DiagramBackend::Mermaid).size();
        expected_id = tracer.id();
        EXPECT_EQ(sink->diagram_calls, 0u);
    }
    EXPECT_GE(expected_parts, 4u);
    EXPECT_EQ(sink->diagram_calls, 1u);
    EXPECT_EQ(sink->diagram_tracer_id, expected_id);
    ASSERT_EQ(sink->diagram_parts.size(), expected_parts);
    for (const auto& part : sink->diagram_parts) {
        EXPECT_EQ(part.backend, viz::DiagramBackend::Mermaid);
    }
}

// ============================================================================
// JsonLines
// ============================================================================

TEST(JsonLines, MessageTransitionNodeFields) {
    const viz::Message message{ .from = "A", .to = "B", .action = "go()", .meta = fixedMeta(7, 3) };
    const auto m = viz::toJsonLine(message);
    EXPECT_TRUE(m.starts_with(R"j({"v":1,"kind":"message","seq":7,"tracer":3,"from":"A","to":"B","action":"go()","file":")j")) << m;

    const viz::Transition transition{ .old_state = "IDLE", .new_state = "RUN", .trigger = "start", .meta = fixedMeta(8, 3) };
    const auto t = viz::toJsonLine(transition);
    EXPECT_TRUE(t.starts_with(R"({"v":1,"kind":"transition","seq":8,"tracer":3,"old":"IDLE","new":"RUN","trigger":"start","file":")")) << t;

    const viz::Node node{ .parent = "Root", .child = "Leaf", .relation_type = "contains", .meta = fixedMeta(9, 3) };
    const auto n = viz::toJsonLine(node);
    EXPECT_TRUE(n.starts_with(R"({"v":1,"kind":"node","seq":9,"tracer":3,"parent":"Root","child":"Leaf","relation":"contains","file":")")) << n;

    for (const auto& line : { m, t, n }) {
        EXPECT_TRUE(contains(line, "test_event_stream.cpp")) << line;
        EXPECT_TRUE(contains(line, R"(","line":)")) << line;
        EXPECT_TRUE(contains(line, R"(,"func":")")) << line;
        EXPECT_TRUE(contains(line, R"(","tUs":)")) << line;
        EXPECT_TRUE(line.ends_with("}")) << line;
        EXPECT_FALSE(contains(line, "\n")) << line;
    }
}

TEST(JsonLines, EscapesSpecialCharacters) {
    // "\x01" "f" is split on purpose: "\x01f" would be one hex escape (0x1f)
    const viz::Message message{
        .from   = "Quote\"Back\\slash",
        .to     = "Tab\tNew\nline\rCR",
        .action = "bs\bff\fctl\x01" "f\x1f" "end\x7f 한글",
        .meta   = fixedMeta(1, 1),
    };
    const auto line = viz::toJsonLine(message);
    EXPECT_TRUE(contains(line, R"("from":"Quote\"Back\\slash")")) << line;
    EXPECT_TRUE(contains(line, R"("to":"Tab\tNew\nline\rCR")")) << line;
    // 0x1f is the last byte that must be escaped; 0x7f and UTF-8 pass through unchanged
    EXPECT_TRUE(contains(line, "\"action\":\"bs\\bff\\fctl\\u0001f\\u001fend\x7f 한글\"")) << line;
    for (const char ch : line) {
        EXPECT_GE(static_cast<unsigned char>(ch), 0x20u) << "raw control character in " << line;
    }
}

TEST(JsonLines, DiagramLinesIndexPartsPerKind) {
    const auto path = tempTracePath("diagram");
    {
        auto sink = viz::JsonLinesEventSink::open(path);
        ASSERT_NE(sink, nullptr);
        const std::vector<viz::DiagramPart> parts{
            { viz::DiagramKind::Sequence, viz::DiagramBackend::Mermaid, "Sequence (1/2)", "sequenceDiagram\n  A->>B: x", false },
            { viz::DiagramKind::Sequence, viz::DiagramBackend::Mermaid, "Sequence (2/2)", "sequenceDiagram\n  B->>A: y", false },
            { viz::DiagramKind::State,    viz::DiagramBackend::Mermaid, "State",          "stateDiagram-v2",            true  },
        };
        sink->onDiagramParts(5, parts);
    }
    const auto lines = readLines(path);
    std::filesystem::remove(path);

    ASSERT_EQ(lines.size(), 3u);
    EXPECT_EQ(lines[0], R"j({"v":1,"kind":"diagram","tracer":5,"part":0,"parts":2,"diagram":"sequence","backend":"mermaid","title":"Sequence (1/2)","overBudget":false,"source":"sequenceDiagram\n  A->>B: x"})j");
    EXPECT_TRUE(contains(lines[1], R"("part":1,"parts":2,"diagram":"sequence")")) << lines[1];
    EXPECT_TRUE(contains(lines[2], R"("part":0,"parts":1,"diagram":"state")")) << lines[2];
    EXPECT_TRUE(contains(lines[2], R"("overBudget":true)")) << lines[2];
}

TEST(JsonLines, EmptyDiagramPartsWriteNothing) {
    const auto path = tempTracePath("empty");
    {
        auto sink = viz::JsonLinesEventSink::open(path);
        ASSERT_NE(sink, nullptr);
        sink->onDiagramParts(1, {});
    }
    EXPECT_TRUE(readLines(path).empty());
    std::filesystem::remove(path);
}

TEST(JsonLines, OpenFailsForMissingDirectory) {
    const auto missing_dir = tempTracePath("missing_dir");
    ASSERT_FALSE(std::filesystem::exists(missing_dir));
    EXPECT_EQ(viz::JsonLinesEventSink::open(missing_dir / "trace.jsonl"), nullptr);
}

TEST(JsonLines, ConcurrentWritersProduceWholeLines) {
    constexpr int kThreads = 4;
    constexpr int kPerThread = 500;
    const auto path = tempTracePath("concurrent");
    {
        auto sink = viz::JsonLinesEventSink::open(path);
        ASSERT_NE(sink, nullptr);

        std::latch start{ kThreads };
        std::vector<std::thread> threads;
        for (int t = 0; t < kThreads; ++t) {
            threads.emplace_back([&sink, &start, t] {
                viz::Tracer tracer;   // destroyed in this thread: its diagram lines race with the others
                tracer.setEventSink(sink);
                start.arrive_and_wait();
                for (int i = 0; i < kPerThread; ++i) {
                    (void)tracer.recordMessage("Worker" + std::to_string(t), "Collector",
                        "deliver a reasonably long payload label " + std::to_string(i) + "()");
                }
            });
        }
        for (auto& thread : threads) {
            thread.join();
        }
    }

    const auto lines = readLines(path);
    std::filesystem::remove(path);

    std::size_t message_lines = 0;
    std::size_t diagram_lines = 0;
    std::set<std::uint64_t> seqs;
    for (const auto& line : lines) {
        ASSERT_TRUE(line.starts_with(R"({"v":1,"kind":")")) << line;
        ASSERT_TRUE(line.ends_with("}")) << line;
        if (line.starts_with(R"({"v":1,"kind":"message","seq":)")) {
            ++message_lines;
            const auto at = line.find(R"("seq":)") + 6;
            seqs.insert(std::stoull(line.substr(at, line.find(',', at) - at)));
        } else if (line.starts_with(R"({"v":1,"kind":"diagram")")) {
            ++diagram_lines;
        }
    }
    EXPECT_EQ(message_lines, static_cast<std::size_t>(kThreads * kPerThread));
    EXPECT_EQ(seqs.size(), static_cast<std::size_t>(kThreads * kPerThread));
    EXPECT_GT(diagram_lines, 0u);
    EXPECT_EQ(message_lines + diagram_lines, lines.size());
}

TEST(JsonLines, ConcurrentRecordersOnOneTracer) {
    // AC-6 on the path where the record lock and the sink call outside it interact:
    // four threads record on the same Tracer.
    constexpr int kThreads = 4;
    constexpr int kPerThread = 500;
    const auto path = tempTracePath("one_tracer");
    std::vector<std::uint64_t> recorded_seqs;
    {
        auto sink = viz::JsonLinesEventSink::open(path);
        ASSERT_NE(sink, nullptr);
        viz::Tracer tracer{ kThreads * kPerThread };
        tracer.setEventSink(sink);

        std::latch start{ kThreads };
        std::vector<std::thread> threads;
        for (int t = 0; t < kThreads; ++t) {
            threads.emplace_back([&tracer, &start, t] {
                start.arrive_and_wait();
                for (int i = 0; i < kPerThread; ++i) {
                    (void)tracer.recordMessage("Worker" + std::to_string(t), "Hub", "tick " + std::to_string(i));
                }
            });
        }
        for (auto& thread : threads) {
            thread.join();
        }
        for (const auto& m : tracer.snapshotMessages()) {
            recorded_seqs.push_back(m.meta.seq);
        }
    }

    const auto lines = readLines(path);
    std::filesystem::remove(path);

    ASSERT_EQ(recorded_seqs.size(), static_cast<std::size_t>(kThreads * kPerThread));
    // stored order is seq order within one Tracer (seq is assigned under the record lock)
    for (std::size_t i = 1; i < recorded_seqs.size(); ++i) {
        ASSERT_LT(recorded_seqs[i - 1], recorded_seqs[i]) << "index " << i;
    }

    std::set<std::uint64_t> streamed_seqs;
    for (const auto& line : lines) {
        ASSERT_TRUE(line.starts_with(R"({"v":1,"kind":")")) << line;
        ASSERT_TRUE(line.ends_with("}")) << line;
        if (line.starts_with(R"({"v":1,"kind":"message","seq":)")) {
            const auto at = line.find(R"("seq":)") + 6;
            streamed_seqs.insert(std::stoull(line.substr(at, line.find(',', at) - at)));
        }
    }
    EXPECT_EQ(streamed_seqs, std::set<std::uint64_t>(recorded_seqs.begin(), recorded_seqs.end()));
}
