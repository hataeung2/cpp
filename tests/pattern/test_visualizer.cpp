/**
 * @file test_visualizer.cpp
 * @brief atugcc::pattern::viz -- Tracer and Formatter unit tests
 *
 * Test groups:
 *   TracerTest       -- record_message / record_transition / push_node / capacity
 *   TerminalFmtTest  -- format_terminal() string output
 *   PlantUMLFmtTest  -- format_diagram()/format_plantuml() default output
 *   D2FmtTest        -- format_d2() compatibility wrapper output
 *   StateMachineTest -- state.hpp Machine + Tracer integration
 *   ObserverTest     -- observer.hpp Subject + Tracer integration
 */
#include <gtest/gtest.h>
#include <atomic>
#include <memory>
#include <sstream>
#include <string>
#include <thread>
#include <vector>

#include "atugcc/pattern/observer.hpp"
#include "atugcc/pattern/state.hpp"
#include "atugcc/pattern/visualizer.hpp"

using namespace atugcc::pattern;
using namespace atugcc::core;

namespace {

class RecordingSink final : public viz::TraceOutputSink {
public:
    void setEnabled(bool enabled) noexcept override {
        enabled_.store(enabled, std::memory_order_relaxed);
    }

    [[nodiscard]] bool isEnabled() const noexcept override {
        return enabled_.load(std::memory_order_relaxed);
    }

    void emit(std::string_view text) override {
        if (!isEnabled()) {
            return;
        }
        std::lock_guard lock(mutex_);
        payloads_.emplace_back(text);
    }

    [[nodiscard]] std::vector<std::string> snapshot() const {
        std::lock_guard lock(mutex_);
        return payloads_;
    }

private:
    std::atomic_bool    enabled_{ true };
    mutable std::mutex      mutex_;
    std::vector<std::string> payloads_;
};

} // namespace

// ============================================================================
// Tracer 기본 동작
// ============================================================================
class TracerTest : public ::testing::Test {
protected:
    viz::Tracer tracer{ 8 };   // 소용량으로 오버플로 테스트
};

TEST_F(TracerTest, RecordMessageAddsToSnapshot) {
    auto result = tracer.record_message("A", "B", "call()");
    ASSERT_TRUE(result.has_value());

    auto msgs = tracer.snapshot_messages();
    ASSERT_EQ(msgs.size(), 1u);
    EXPECT_EQ(msgs[0].from,   "A");
    EXPECT_EQ(msgs[0].to,     "B");
    EXPECT_EQ(msgs[0].action, "call()");
}

TEST_F(TracerTest, RecordTransitionAddsToSnapshot) {
    auto result = tracer.record_transition("IDLE", "STANDBY", "schedule");
    ASSERT_TRUE(result.has_value());

    auto trans = tracer.snapshot_transitions();
    ASSERT_EQ(trans.size(), 1u);
    EXPECT_EQ(trans[0].old_state, "IDLE");
    EXPECT_EQ(trans[0].new_state, "STANDBY");
    EXPECT_EQ(trans[0].trigger,   "schedule");
}

TEST_F(TracerTest, PushNodeAddsToSnapshot) {
    auto result = tracer.push_node("Deco2", "Deco1", "wraps");
    ASSERT_TRUE(result.has_value());

    auto nodes = tracer.snapshot_nodes();
    ASSERT_EQ(nodes.size(), 1u);
    EXPECT_EQ(nodes[0].parent,        "Deco2");
    EXPECT_EQ(nodes[0].child,         "Deco1");
    EXPECT_EQ(nodes[0].relation_type, "wraps");
}

TEST_F(TracerTest, CapacityLimitReturnsError) {
    for (int i = 0; i < 8; ++i) {
        EXPECT_TRUE(tracer.record_message("A", "B", "x").has_value());
    }
    // 9번째는 초과
    auto overflow = tracer.record_message("A", "B", "overflow");
    ASSERT_FALSE(overflow.has_value());
    EXPECT_EQ(overflow.error(), CoreError::Unexpected);
}

TEST_F(TracerTest, ClearResetsAllBuffers) {
    (void)tracer.record_message("A", "B", "x");
    (void)tracer.record_transition("S1", "S2", "t");
    (void)tracer.push_node("P", "C", "r");
    tracer.clear();
    EXPECT_TRUE(tracer.snapshot_messages().empty());
    EXPECT_TRUE(tracer.snapshot_transitions().empty());
    EXPECT_TRUE(tracer.snapshot_nodes().empty());
}

TEST_F(TracerTest, LiveOutputWithoutSinkStillRecordsEvents) {
    tracer.setLiveTerminalOutputEnabled(true);

    auto result = tracer.record_message("A", "B", "call()");

    ASSERT_TRUE(result.has_value());
    ASSERT_EQ(tracer.snapshot_messages().size(), 1u);
}

TEST_F(TracerTest, LiveOutputEmitsWhenSinkIsConfigured) {
    auto sink = std::make_shared<RecordingSink>();
    tracer.setOutputSink(sink);
    tracer.setLiveTerminalOutputEnabled(true);

    auto result = tracer.record_message("A", "B", "call()");

    ASSERT_TRUE(result.has_value());
    const auto payloads = sink->snapshot();
    ASSERT_EQ(payloads.size(), 1u);
    EXPECT_NE(payloads[0].find("A"), std::string::npos);
    EXPECT_NE(payloads[0].find("B"), std::string::npos);
    EXPECT_NE(payloads[0].find("call()"), std::string::npos);
}

TEST_F(TracerTest, LiveOutputDisabledSuppressesSinkWrites) {
    auto sink = std::make_shared<RecordingSink>();
    tracer.setOutputSink(sink);
    tracer.setLiveTerminalOutputEnabled(false);

    auto result = tracer.record_transition("IDLE", "RUN", "go");

    ASSERT_TRUE(result.has_value());
    EXPECT_TRUE(sink->snapshot().empty());
    EXPECT_EQ(tracer.snapshot_transitions().size(), 1u);
}

TEST_F(TracerTest, ConsoleSinkDisabledSuppressesWritesButKeepsTraceData) {
    std::ostringstream stream;
    auto sink = std::make_shared<viz::ConsoleTraceSink>(stream);
    sink->setEnabled(false);
    tracer.setOutputSink(sink);
    tracer.setLiveTerminalOutputEnabled(true);

    auto result = tracer.push_node("Parent", "Child", "wraps");

    ASSERT_TRUE(result.has_value());
    EXPECT_TRUE(stream.str().empty());
    EXPECT_EQ(tracer.snapshot_nodes().size(), 1u);
}

TEST(TracerConcurrencyTest, LiveOutputHandlesConcurrentRecording) {
    viz::Tracer tracer{ 64 };
    std::ostringstream stream;
    auto sink = std::make_shared<viz::ConsoleTraceSink>(stream);
    tracer.setOutputSink(sink);
    tracer.setLiveTerminalOutputEnabled(true);

    {
        std::vector<std::jthread> workers;
        for (int idx = 0; idx < 4; ++idx) {
            workers.emplace_back([&tracer, idx]() {
                for (int iter = 0; iter < 8; ++iter) {
                    const auto result = tracer.record_message(
                        std::format("Worker{}", idx),
                        "Sink",
                        std::format("step{}", iter));
                    EXPECT_TRUE(result.has_value());
                }
            });
        }
    }

    EXPECT_EQ(tracer.snapshot_messages().size(), 32u);
    EXPECT_FALSE(stream.str().empty());
}

// ============================================================================
// TerminalFormatter 출력 검증
// ============================================================================
TEST(TerminalFmtTest, FormatTerminalContainsFromAndTo) {
    viz::Tracer tracer;
    (void)tracer.record_message("Subject", "Observer1", "notify()");
    (void)tracer.record_message("Subject", "Observer2", "notify()");

    const std::string out = tracer.format_terminal();
    EXPECT_NE(out.find("Subject"),   std::string::npos);
    EXPECT_NE(out.find("Observer1"), std::string::npos);
    EXPECT_NE(out.find("notify()"),  std::string::npos);
}

TEST(TerminalFmtTest, FormatTerminalContainsTransitionArrow) {
    viz::Tracer tracer;
    (void)tracer.record_transition("IDLE", "STANDBY", "go");

    const std::string out = tracer.format_terminal();
    EXPECT_NE(out.find("IDLE"),    std::string::npos);
    EXPECT_NE(out.find("STANDBY"), std::string::npos);
    EXPECT_NE(out.find("go"),      std::string::npos);
}

TEST(TerminalFmtTest, FormatTerminalContainsTreeRelation) {
    viz::Tracer tracer;
    (void)tracer.push_node("Deco2", "Deco1", "wraps");
    (void)tracer.push_node("Deco1", "Base",  "wraps");

    const std::string out = tracer.format_terminal();
    EXPECT_NE(out.find("Deco2"), std::string::npos);
    EXPECT_NE(out.find("Deco1"), std::string::npos);
    EXPECT_NE(out.find("Base"),  std::string::npos);
    EXPECT_NE(out.find("wraps"), std::string::npos);
}

TEST(TerminalFmtTest, EmptyTracerReturnsEmptyString) {
    viz::Tracer tracer;
    EXPECT_TRUE(tracer.format_terminal().empty());
}

// ============================================================================
// PlantUMLFormatter 출력 검증 (기본 백엔드)
// ============================================================================
TEST(PlantUMLFmtTest, DefaultBackendIsPlantUML) {
    viz::Tracer tracer;
    (void)tracer.record_message("A", "B", "call()");

    const std::string out = tracer.format_diagram();
    EXPECT_NE(out.find("@startuml"), std::string::npos);
    EXPECT_NE(out.find("A -> B : call()"), std::string::npos);
}

TEST(PlantUMLFmtTest, ExplicitPlantUMLBackend) {
    viz::Tracer tracer;
    (void)tracer.record_transition("IDLE", "RUN", "go");

    const std::string out = tracer.format_diagram(viz::DiagramBackend::PlantUML);
    EXPECT_NE(out.find("@startuml"), std::string::npos);
    EXPECT_NE(out.find("IDLE --> RUN : go"), std::string::npos);
}

TEST(PlantUMLFmtTest, FormatPlantUMLWrapperWorks) {
    viz::Tracer tracer;
    (void)tracer.push_node("P", "C", "wraps");

    const std::string out = tracer.format_plantuml();
    EXPECT_NE(out.find("@startuml"), std::string::npos);
    EXPECT_NE(out.find("P --> C : wraps"), std::string::npos);
}

TEST(MermaidFmtTest, BackendSelectorToMermaidWorks) {
    viz::Tracer tracer;
    (void)tracer.record_message("A", "B", "call()");

    const std::string out = tracer.format_diagram(viz::DiagramBackend::Mermaid);
    EXPECT_NE(out.find("sequenceDiagram"), std::string::npos);
    EXPECT_NE(out.find("A->>B:call()"), std::string::npos);
}

TEST(MermaidFmtTest, FormatMermaidWrapperWorks) {
    viz::Tracer tracer;
    (void)tracer.record_transition("IDLE", "RUN", "go");

    const std::string out = tracer.format_mermaid();
    EXPECT_NE(out.find("stateDiagram-v2"), std::string::npos);
    EXPECT_NE(out.find("IDLE --> RUN : go"), std::string::npos);
}

// ============================================================================
// D2Formatter 출력 검증
// ============================================================================
TEST(D2FmtTest, MessageFlowHeader) {
    viz::Tracer tracer;
    (void)tracer.record_message("A", "B", "call()");

    const std::string out = tracer.format_d2();
    EXPECT_NE(out.find("# sequence/message flow"), std::string::npos);
    EXPECT_NE(out.find("A -> B: call()"),          std::string::npos);
}

TEST(D2FmtTest, StateFlowHeader) {
    viz::Tracer tracer;
    (void)tracer.record_transition("IDLE", "STANDBY", "go");

    const std::string out = tracer.format_d2();
    EXPECT_NE(out.find("# state transitions"), std::string::npos);
    EXPECT_NE(out.find("IDLE -> STANDBY: go"), std::string::npos);
}

TEST(D2FmtTest, StructureTreeHeader) {
    viz::Tracer tracer;
    (void)tracer.push_node("P", "C", "wraps");

    const std::string out = tracer.format_d2();
    EXPECT_NE(out.find("# class/structure tree"), std::string::npos);
    EXPECT_NE(out.find("P -> C: wraps"),          std::string::npos);
}

TEST(D2FmtTest, DuplicateMessagesDeduped) {
    viz::Tracer tracer;
    (void)tracer.record_message("A", "B", "ping()");
    (void)tracer.record_message("A", "B", "ping()");
    (void)tracer.record_message("A", "B", "ping()");

    const std::string out = tracer.format_d2();
    // "A -> B: ping()" 가 딱 한 번만 등장해야 한다
    const auto first  = out.find("A -> B: ping()");
    const auto second = out.find("A -> B: ping()", first + 1);
    EXPECT_NE(first,  std::string::npos);
    EXPECT_EQ(second, std::string::npos);
}

TEST(D2FmtTest, BackendSelectorToD2Works) {
    viz::Tracer tracer;
    (void)tracer.record_message("A", "B", "call()");

    const std::string out = tracer.format_diagram(viz::DiagramBackend::D2);
    EXPECT_NE(out.find("# sequence/message flow"), std::string::npos);
    EXPECT_NE(out.find("A -> B: call()"), std::string::npos);
}

// ============================================================================
// State Machine + Tracer 연동
// ============================================================================
TEST(StateMachineTest, ValidTransitionRecorded) {
    viz::Tracer tracer;
    state::Machine machine{ tracer };

    EXPECT_EQ(machine.current_state_name(), "IDLE");
    auto r = machine.transition(state::StandbyState{});
    ASSERT_TRUE(r.has_value());
    EXPECT_EQ(machine.current_state_name(), "STANDBY");

    auto trans = tracer.snapshot_transitions();
    ASSERT_EQ(trans.size(), 1u);
    EXPECT_EQ(trans[0].old_state, "IDLE");
    EXPECT_EQ(trans[0].new_state, "STANDBY");
}

TEST(StateMachineTest, InvalidTransitionReturnsError) {
    viz::Tracer tracer;
    state::Machine machine{ tracer };

    // IDLE → RUN は不可
    auto r = machine.transition(state::RunState{});
    ASSERT_FALSE(r.has_value());
    EXPECT_EQ(r.error(), CoreError::InvalidArgument);
    EXPECT_EQ(machine.current_state_name(), "IDLE"); // 상태 변화 없음
}

TEST(StateMachineTest, ScheduleRecordsMessage) {
    viz::Tracer tracer;
    state::Machine machine{ tracer };

    machine.schedule(); // IDLE 상태의 schedule
    auto msgs = tracer.snapshot_messages();
    ASSERT_FALSE(msgs.empty());
    EXPECT_EQ(msgs[0].from, "Machine");
}

TEST(StateMachineTest, FullFlowProducesDefaultPlantUMLOutput) {
    viz::Tracer tracer;
    state::Machine machine{ tracer };

    (void)machine.transition(state::StandbyState{});
    (void)machine.transition(state::RunState{});
    machine.schedule();

    const std::string diagram = tracer.format_diagram();
    EXPECT_NE(diagram.find("@startuml"), std::string::npos);
    EXPECT_NE(diagram.find("IDLE"),      std::string::npos);
    EXPECT_NE(diagram.find("STANDBY"),   std::string::npos);
    EXPECT_NE(diagram.find("RUN"),       std::string::npos);
}

// ============================================================================
// Observer + Tracer 연동
// ============================================================================
TEST(ObserverTest, NotifyRecordsMessages) {
    viz::Tracer tracer;
    observer::Subject subject{ tracer };

    auto obs1 = std::make_shared<observer::DataObserver1>();
    auto obs2 = std::make_shared<observer::DataObserver2>();
    observer::subscribe(subject, obs1, "Observer1");
    observer::subscribe(subject, obs2, "Observer2");

    subject.set_data("hello", "world");

    auto msgs = tracer.snapshot_messages();
    ASSERT_GE(msgs.size(), 2u);

    const bool has_obs1 = std::ranges::any_of(msgs, [](const viz::Message& m) {
        return m.to == "Observer1";
    });
    const bool has_obs2 = std::ranges::any_of(msgs, [](const viz::Message& m) {
        return m.to == "Observer2";
    });
    EXPECT_TRUE(has_obs1);
    EXPECT_TRUE(has_obs2);
}

TEST(ObserverTest, ExpiredObserverNotNotified) {
    viz::Tracer tracer;
    observer::Subject subject{ tracer };

    {
        auto obs = std::make_shared<observer::DataObserver1>();
        observer::subscribe(subject, obs, "TempObs");
        // 이 블록을 벗어나면 obs 소멸 → weak_ptr 만료
    }

    subject.set_data("x", "y");
    // 만료된 구독자에게 메시지가 기록되지 않아야 한다
    auto msgs = tracer.snapshot_messages();
    const bool notified_expired = std::ranges::any_of(msgs, [](const viz::Message& m) {
        return m.to == "TempObs";
    });
    EXPECT_FALSE(notified_expired);
}

TEST(ObserverTest, DisplayReflectsLatestData) {
    viz::Tracer tracer;
    observer::Subject subject{ tracer };

    auto obs1 = std::make_shared<observer::DataObserver1>();
    auto obs2 = std::make_shared<observer::DataObserver2>();
    observer::subscribe(subject, obs1, "Observer1");
    observer::subscribe(subject, obs2, "Observer2");

    subject.set_data("foo", "bar");

    const auto displays = subject.collect_displays();
    ASSERT_EQ(displays.size(), 2u);
    EXPECT_NE(displays[0].find("foo"),       std::string::npos);
    EXPECT_NE(displays[1].find("foo, bar"),  std::string::npos);
}

TEST(ObserverTest, D2MessageFlowGenerated) {
    viz::Tracer tracer;
    observer::Subject subject{ tracer };

    auto obs = std::make_shared<observer::DataObserver1>();
    observer::subscribe(subject, obs, "Observer1");
    subject.set_data("a", "b");

    const std::string d2 = tracer.format_d2();
    EXPECT_NE(d2.find("# sequence/message flow"), std::string::npos);
    EXPECT_NE(d2.find("Subject"),                 std::string::npos);
    EXPECT_NE(d2.find("Observer1"),               std::string::npos);
}
