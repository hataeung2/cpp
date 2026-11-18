/**
 * @file test_visualizer.cpp
 * @brief atugcc::pattern::viz -- Tracer and Formatter unit tests
 *
 * Test groups:
 *   TracerTest       -- recordMessage / recordTransition / pushNode / capacity
 *   TerminalFmtTest  -- formatTerminal() string output
 *   PlantUMLFmtTest  -- formatDiagram()/formatPlantuml() default output
 *   D2FmtTest        -- formatD2() compatibility wrapper output
 *   StateMachineTest -- state.hpp Machine + Tracer integration
 *   ObserverTest     -- observer.hpp Subject + Tracer integration
 */
#include <gtest/gtest.h>
#include <algorithm>
#include <atomic>
#include <memory>
#include <sstream>
#include <string>
#include <string_view>
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
    auto result = tracer.recordMessage("A", "B", "call()");
    ASSERT_TRUE(result.has_value());

    auto msgs = tracer.snapshotMessages();
    ASSERT_EQ(msgs.size(), 1u);
    EXPECT_EQ(msgs[0].from,   "A");
    EXPECT_EQ(msgs[0].to,     "B");
    EXPECT_EQ(msgs[0].action, "call()");
}

TEST_F(TracerTest, RecordTransitionAddsToSnapshot) {
    auto result = tracer.recordTransition("IDLE", "STANDBY", "schedule");
    ASSERT_TRUE(result.has_value());

    auto trans = tracer.snapshotTransitions();
    ASSERT_EQ(trans.size(), 1u);
    EXPECT_EQ(trans[0].old_state, "IDLE");
    EXPECT_EQ(trans[0].new_state, "STANDBY");
    EXPECT_EQ(trans[0].trigger,   "schedule");
}

TEST_F(TracerTest, PushNodeAddsToSnapshot) {
    auto result = tracer.pushNode("Deco2", "Deco1", "wraps");
    ASSERT_TRUE(result.has_value());

    auto nodes = tracer.snapshotNodes();
    ASSERT_EQ(nodes.size(), 1u);
    EXPECT_EQ(nodes[0].parent,        "Deco2");
    EXPECT_EQ(nodes[0].child,         "Deco1");
    EXPECT_EQ(nodes[0].relation_type, "wraps");
}

TEST_F(TracerTest, CapacityLimitReturnsError) {
    for (int i = 0; i < 8; ++i) {
        EXPECT_TRUE(tracer.recordMessage("A", "B", "x").has_value());
    }
    // 9번째는 초과
    auto overflow = tracer.recordMessage("A", "B", "overflow");
    ASSERT_FALSE(overflow.has_value());
    EXPECT_EQ(overflow.error(), CoreError::Unexpected);
}

TEST_F(TracerTest, ClearResetsAllBuffers) {
    (void)tracer.recordMessage("A", "B", "x");
    (void)tracer.recordTransition("S1", "S2", "t");
    (void)tracer.pushNode("P", "C", "r");
    tracer.clear();
    EXPECT_TRUE(tracer.snapshotMessages().empty());
    EXPECT_TRUE(tracer.snapshotTransitions().empty());
    EXPECT_TRUE(tracer.snapshotNodes().empty());
}

TEST_F(TracerTest, LiveOutputWithoutSinkStillRecordsEvents) {
    tracer.setLiveTerminalOutputEnabled(true);

    auto result = tracer.recordMessage("A", "B", "call()");

    ASSERT_TRUE(result.has_value());
    ASSERT_EQ(tracer.snapshotMessages().size(), 1u);
}

TEST_F(TracerTest, LiveOutputEmitsWhenSinkIsConfigured) {
    auto sink = std::make_shared<RecordingSink>();
    tracer.setOutputSink(sink);
    tracer.setLiveTerminalOutputEnabled(true);

    auto result = tracer.recordMessage("A", "B", "call()");

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

    auto result = tracer.recordTransition("IDLE", "RUN", "go");

    ASSERT_TRUE(result.has_value());
    EXPECT_TRUE(sink->snapshot().empty());
    EXPECT_EQ(tracer.snapshotTransitions().size(), 1u);
}

TEST_F(TracerTest, ConsoleSinkDisabledSuppressesWritesButKeepsTraceData) {
    std::ostringstream stream;
    auto sink = std::make_shared<viz::ConsoleTraceSink>(stream);
    sink->setEnabled(false);
    tracer.setOutputSink(sink);
    tracer.setLiveTerminalOutputEnabled(true);

    auto result = tracer.pushNode("Parent", "Child", "wraps");

    ASSERT_TRUE(result.has_value());
    EXPECT_TRUE(stream.str().empty());
    EXPECT_EQ(tracer.snapshotNodes().size(), 1u);
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
                    const auto result = tracer.recordMessage(
                        std::format("Worker{}", idx),
                        "Sink",
                        std::format("step{}", iter));
                    EXPECT_TRUE(result.has_value());
                }
            });
        }
    }

    EXPECT_EQ(tracer.snapshotMessages().size(), 32u);
    EXPECT_FALSE(stream.str().empty());
}

// ============================================================================
// TerminalFormatter 출력 검증
// ============================================================================
TEST(TerminalFmtTest, FormatTerminalContainsFromAndTo) {
    viz::Tracer tracer;
    (void)tracer.recordMessage("Subject", "Observer1", "notify()");
    (void)tracer.recordMessage("Subject", "Observer2", "notify()");

    const std::string out = tracer.formatTerminal();
    EXPECT_NE(out.find("Subject"),   std::string::npos);
    EXPECT_NE(out.find("Observer1"), std::string::npos);
    EXPECT_NE(out.find("notify()"),  std::string::npos);
}

TEST(TerminalFmtTest, FormatTerminalContainsTransitionArrow) {
    viz::Tracer tracer;
    (void)tracer.recordTransition("IDLE", "STANDBY", "go");

    const std::string out = tracer.formatTerminal();
    EXPECT_NE(out.find("IDLE"),    std::string::npos);
    EXPECT_NE(out.find("STANDBY"), std::string::npos);
    EXPECT_NE(out.find("go"),      std::string::npos);
}

TEST(TerminalFmtTest, FormatTerminalContainsTreeRelation) {
    viz::Tracer tracer;
    (void)tracer.pushNode("Deco2", "Deco1", "wraps");
    (void)tracer.pushNode("Deco1", "Base",  "wraps");

    const std::string out = tracer.formatTerminal();
    EXPECT_NE(out.find("Deco2"), std::string::npos);
    EXPECT_NE(out.find("Deco1"), std::string::npos);
    EXPECT_NE(out.find("Base"),  std::string::npos);
    EXPECT_NE(out.find("wraps"), std::string::npos);
}

TEST(TerminalFmtTest, EmptyTracerReturnsEmptyString) {
    viz::Tracer tracer;
    EXPECT_TRUE(tracer.formatTerminal().empty());
}

// ============================================================================
// PlantUMLFormatter 출력 검증 (기본 백엔드)
// ============================================================================
TEST(PlantUMLFmtTest, DefaultBackendIsPlantUML) {
    viz::Tracer tracer;
    (void)tracer.recordMessage("A", "B", "call()");

    const std::string out = tracer.formatDiagram();
    EXPECT_NE(out.find("@startuml"), std::string::npos);
    EXPECT_NE(out.find("A -> B : call()"), std::string::npos);
}

TEST(PlantUMLFmtTest, ExplicitPlantUMLBackend) {
    viz::Tracer tracer;
    (void)tracer.recordTransition("IDLE", "RUN", "go");

    const std::string out = tracer.formatDiagram(viz::DiagramBackend::PlantUML);
    EXPECT_NE(out.find("@startuml"), std::string::npos);
    EXPECT_NE(out.find("IDLE --> RUN : go"), std::string::npos);
}

TEST(PlantUMLFmtTest, FormatPlantUMLWrapperWorks) {
    viz::Tracer tracer;
    (void)tracer.pushNode("P", "C", "wraps");

    const std::string out = tracer.formatPlantuml();
    EXPECT_NE(out.find("@startuml"), std::string::npos);
    EXPECT_NE(out.find("P --> C : wraps"), std::string::npos);
}

TEST(MermaidFmtTest, BackendSelectorToMermaidWorks) {
    viz::Tracer tracer;
    (void)tracer.recordMessage("A", "B", "call()");

    const std::string out = tracer.formatDiagram(viz::DiagramBackend::Mermaid);
    EXPECT_NE(out.find("sequenceDiagram"), std::string::npos);
    EXPECT_NE(out.find("A->>B:call()"), std::string::npos);
}

TEST(MermaidFmtTest, FormatMermaidWrapperWorks) {
    viz::Tracer tracer;
    (void)tracer.recordTransition("IDLE", "RUN", "go");

    const std::string out = tracer.formatMermaid();
    EXPECT_NE(out.find("stateDiagram-v2"), std::string::npos);
    EXPECT_NE(out.find("IDLE --> RUN : go"), std::string::npos);
}

// ============================================================================
// D2Formatter 출력 검증
// ============================================================================
TEST(D2FmtTest, MessageFlowHeader) {
    viz::Tracer tracer;
    (void)tracer.recordMessage("A", "B", "call()");

    const std::string out = tracer.formatD2();
    EXPECT_NE(out.find("# sequence/message flow"), std::string::npos);
    EXPECT_NE(out.find("A -> B: call()"),          std::string::npos);
}

TEST(D2FmtTest, StateFlowHeader) {
    viz::Tracer tracer;
    (void)tracer.recordTransition("IDLE", "STANDBY", "go");

    const std::string out = tracer.formatD2();
    EXPECT_NE(out.find("# state transitions"), std::string::npos);
    EXPECT_NE(out.find("IDLE -> STANDBY: go"), std::string::npos);
}

TEST(D2FmtTest, StructureTreeHeader) {
    viz::Tracer tracer;
    (void)tracer.pushNode("P", "C", "wraps");

    const std::string out = tracer.formatD2();
    EXPECT_NE(out.find("# class/structure tree"), std::string::npos);
    EXPECT_NE(out.find("P -> C: wraps"),          std::string::npos);
}

TEST(D2FmtTest, DuplicateMessagesDeduped) {
    viz::Tracer tracer;
    (void)tracer.recordMessage("A", "B", "ping()");
    (void)tracer.recordMessage("A", "B", "ping()");
    (void)tracer.recordMessage("A", "B", "ping()");

    const std::string out = tracer.formatD2();
    // "A -> B: ping()" 가 딱 한 번만 등장해야 한다
    const auto first  = out.find("A -> B: ping()");
    const auto second = out.find("A -> B: ping()", first + 1);
    EXPECT_NE(first,  std::string::npos);
    EXPECT_EQ(second, std::string::npos);
}

TEST(D2FmtTest, BackendSelectorToD2Works) {
    viz::Tracer tracer;
    (void)tracer.recordMessage("A", "B", "call()");

    const std::string out = tracer.formatDiagram(viz::DiagramBackend::D2);
    EXPECT_NE(out.find("# sequence/message flow"), std::string::npos);
    EXPECT_NE(out.find("A -> B: call()"), std::string::npos);
}

// ============================================================================
// State Machine + Tracer 연동
// ============================================================================
TEST(StateMachineTest, ValidTransitionRecorded) {
    viz::Tracer tracer;
    state::Machine machine{ tracer };

    EXPECT_EQ(machine.currentStateName(), "IDLE");
    auto r = machine.transition(state::StandbyState{});
    ASSERT_TRUE(r.has_value());
    EXPECT_EQ(machine.currentStateName(), "STANDBY");

    auto trans = tracer.snapshotTransitions();
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
    EXPECT_EQ(machine.currentStateName(), "IDLE"); // 상태 변화 없음
}

TEST(StateMachineTest, ScheduleRecordsMessage) {
    viz::Tracer tracer;
    state::Machine machine{ tracer };

    machine.schedule(); // IDLE 상태의 schedule
    auto msgs = tracer.snapshotMessages();
    ASSERT_FALSE(msgs.empty());
    EXPECT_EQ(msgs[0].from, "Machine");
}

TEST(StateMachineTest, FullFlowProducesDefaultPlantUMLOutput) {
    viz::Tracer tracer;
    state::Machine machine{ tracer };

    (void)machine.transition(state::StandbyState{});
    (void)machine.transition(state::RunState{});
    machine.schedule();

    const std::string diagram = tracer.formatDiagram();
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

    subject.setData("hello", "world");

    auto msgs = tracer.snapshotMessages();
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

    subject.setData("x", "y");
    // 만료된 구독자에게 메시지가 기록되지 않아야 한다
    auto msgs = tracer.snapshotMessages();
    const bool notified_expired = std::ranges::any_of(msgs, [](const viz::Message& m) {
        return m.to == "TempObs";
    });
    EXPECT_FALSE(notified_expired);
}

TEST(ObserverTest, SubscribeDuringNotifyStartsNextTime) {
    // 알림 도중 등록된 구독자는 이번 알림을 받지 않고 다음 알림부터 받는다.
    // A subscriber added from inside a notification does not receive that notification; it receives the next one.
    struct CountingObserver {
        int count_{ 0 };

        void onNotify(const observer::Subject&) {
            ++count_;
        }

        [[nodiscard]] std::string display() const {
            return std::to_string(count_);
        }
    };
    static_assert(observer::ObserverOf<CountingObserver>);

    struct SubscribingObserver {
        observer::Subject* subject_{ nullptr };
        std::shared_ptr<CountingObserver> observer_c_{ nullptr };
        int count_{ 0 };

        void onNotify(const observer::Subject&) {
            ++count_;
            if (count_ == 1 && subject_ != nullptr && observer_c_ != nullptr) {
                observer::subscribe(*subject_, observer_c_, "ObserverC");
            }
        }

        [[nodiscard]] std::string display() const {
            return std::to_string(count_);
        }
    };
    static_assert(observer::ObserverOf<SubscribingObserver>);

    viz::Tracer tracer;
    observer::Subject subject{ tracer };

    auto obs_a = std::make_shared<SubscribingObserver>();
    auto obs_b = std::make_shared<CountingObserver>();
    auto obs_c = std::make_shared<CountingObserver>();

    obs_a->subject_ = &subject;
    obs_a->observer_c_ = obs_c;

    // 알림 전에 A, B 두 개의 구독자만 먼저 등록한다.
    // Exactly two subscribers A and B are subscribed before any notification.
    observer::subscribe(subject, obs_a, "ObserverA");
    observer::subscribe(subject, obs_b, "ObserverB");

    // 첫 번째 알림: A=1, B=1, C=0 (C는 알림 중 등록되었으므로 이번 알림을 받지 않음)
    // First notification: expect A=1, B=1, C=0.
    subject.setData("a", "1");
    EXPECT_EQ(obs_a->count_, 1);
    EXPECT_EQ(obs_b->count_, 1);
    EXPECT_EQ(obs_c->count_, 0);

    // 두 번째 알림: A=2, B=2, C=1 (C는 다음 알림부터 수신)
    // Second notification: expect A=2, B=2, C=1.
    subject.setData("b", "2");
    EXPECT_EQ(obs_a->count_, 2);
    EXPECT_EQ(obs_b->count_, 2);
    EXPECT_EQ(obs_c->count_, 1);
}

TEST(ObserverTest, NestedSetDataIsSafe) {
    // 알림 콜백에서 다시 setData를 불러도 안전하고, 바깥 알림은 시작 때의 사본을 끝까지 돈다.
    // Calling setData from inside onNotify is safe, and the outer notification walks its start-time copy to the end.
    struct RecordingObserver {
        int count_{ 0 };
        std::string last_data1_;

        void onNotify(const observer::Subject& s) {
            ++count_;
            last_data1_ = s.data1();
        }

        [[nodiscard]] std::string display() const {
            return last_data1_;
        }
    };
    static_assert(observer::ObserverOf<RecordingObserver>);

    // 첫 알림에서 B와 D를 만료시킨 뒤 한 번만 다시 setData를 부른다.
    // On its first notification it expires B and D, then calls setData once more.
    struct NestedInvokingObserver {
        observer::Subject* subject_{ nullptr };
        std::shared_ptr<RecordingObserver>* expire_b_{ nullptr };
        std::shared_ptr<RecordingObserver>* expire_d_{ nullptr };
        int count_{ 0 };
        std::string last_data1_;

        void onNotify(const observer::Subject& s) {
            ++count_;
            last_data1_ = s.data1();
            if (count_ == 1) {
                expire_b_->reset();
                expire_d_->reset();
                subject_->setData("inner", "2");
            }
        }

        [[nodiscard]] std::string display() const {
            return last_data1_;
        }
    };
    static_assert(observer::ObserverOf<NestedInvokingObserver>);

    viz::Tracer tracer;
    observer::Subject subject{ tracer };

    auto obs_b = std::make_shared<RecordingObserver>();
    auto obs_a = std::make_shared<NestedInvokingObserver>();
    auto obs_c = std::make_shared<RecordingObserver>();
    auto obs_d = std::make_shared<RecordingObserver>();
    obs_a->subject_ = &subject;
    obs_a->expire_b_ = &obs_b;
    obs_a->expire_d_ = &obs_d;

    // B를 A 앞에 둔다: 안쪽 알림이 B를 지우면 A 뒤의 원소가 앞으로 당겨진다.
    // 인덱스로 도는 구현은 그때 C를 건너뛴다.
    // B comes before A: when the inner notification erases B, the elements after A move forward.
    // An implementation that walks by index then skips C.
    observer::subscribe(subject, obs_b, "ObserverB");
    observer::subscribe(subject, obs_a, "ObserverA");
    observer::subscribe(subject, obs_c, "ObserverC");
    observer::subscribe(subject, obs_d, "ObserverD");

    subject.setData("outer", "1");

    // 최종 데이터는 안쪽 호출의 값이다.
    // The final data is the inner call's.
    EXPECT_EQ(subject.data1(), "inner");

    // A: 바깥 1번 + 안쪽 1번. C: 안쪽 1번 + 바깥 사본의 차례 1번.
    // A: once outer + once inner. C: once inner + its turn in the outer copy.
    EXPECT_EQ(obs_a->count_, 2);
    EXPECT_EQ(obs_c->count_, 2);
    EXPECT_EQ(obs_a->last_data1_, "inner");
    EXPECT_EQ(obs_c->last_data1_, "inner");

    // Subject가 보낸 메시지로 확인한다: B는 만료 전 바깥 알림 1번뿐, D는 차례가 오기 전에 만료되어 0번.
    // Checked through the messages the Subject sent: B only once (the outer one, before it expired);
    // D expired before its turn, so none.
    const auto msgs = tracer.snapshotMessages();
    const auto sent_to = [&msgs](std::string_view name) {
        return std::ranges::count_if(msgs, [name](const viz::Message& m) { return m.to == name; });
    };
    EXPECT_EQ(sent_to("ObserverB"), 1);
    EXPECT_EQ(sent_to("ObserverD"), 0);
    EXPECT_EQ(sent_to("ObserverC"), 2);
}

TEST(ObserverTest, DisplayReflectsLatestData) {
    viz::Tracer tracer;
    observer::Subject subject{ tracer };

    auto obs1 = std::make_shared<observer::DataObserver1>();
    auto obs2 = std::make_shared<observer::DataObserver2>();
    observer::subscribe(subject, obs1, "Observer1");
    observer::subscribe(subject, obs2, "Observer2");

    subject.setData("foo", "bar");

    const auto displays = subject.collectDisplays();
    ASSERT_EQ(displays.size(), 2u);
    EXPECT_NE(displays[0].find("foo"),       std::string::npos);
    EXPECT_NE(displays[1].find("foo, bar"),  std::string::npos);
}

TEST(ObserverTest, D2MessageFlowGenerated) {
    viz::Tracer tracer;
    observer::Subject subject{ tracer };

    auto obs = std::make_shared<observer::DataObserver1>();
    observer::subscribe(subject, obs, "Observer1");
    subject.setData("a", "b");

    const std::string d2 = tracer.formatD2();
    EXPECT_NE(d2.find("# sequence/message flow"), std::string::npos);
    EXPECT_NE(d2.find("Subject"),                 std::string::npos);
    EXPECT_NE(d2.find("Observer1"),               std::string::npos);
}
