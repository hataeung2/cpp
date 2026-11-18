/**
 * @file scenario_traced_observer.cpp
 * @brief Scenario test: Traced Observer (spec 023-02 AC-3).
 *
 * Observer 패턴과 viz::Tracer 연동, 약참조 수명 관리 및 시퀀스 다이어그램 생성 검증.
 * Verifies Observer pattern integration with viz::Tracer, weak_ptr lifetime management, and sequence diagram generation.
 */

#include "scenario.hpp"

#include <gtest/gtest.h>

#include <memory>
#include <string>
#include <vector>

#include "atugcc/pattern/observer.hpp"
#include "atugcc/pattern/visualizer.hpp"

namespace observer = atugcc::pattern::observer;
namespace viz = atugcc::pattern::viz;

TEST(TracedObserver, SubscribeNotifyExpireDiagram) {
    atugcc::test::Scenario s;

    viz::Tracer tracer;
    observer::Subject subject{ tracer };

    auto panel = std::make_shared<observer::DataObserver1>();
    auto alarm = std::make_shared<observer::DataObserver2>();

    s.step("subscribe two observers", [&] {
        // Panel과 Alarm 관찰자를 Subject에 등록한다.
        // Register Panel and Alarm observers with the Subject.
        observer::subscribe(subject, panel, "Panel");
        observer::subscribe(subject, alarm, "Alarm");

        // 등록 직후 두 관찰자의 표시 문자열을 수집할 수 있고 아직 메시지는 기록되지 않는다.
        // Immediately after subscription, displays can be collected and no messages are recorded yet.
        EXPECT_EQ(subject.collectDisplays().size(), 2U);
        EXPECT_TRUE(tracer.snapshotMessages().empty());
    });

    s.step("first update notifies both in order", [&] {
        // 첫 번째 데이터 변경 시 두 관찰자에게 등록 순서대로 알림이 전달된다.
        // First update notifies both observers in subscription order.
        subject.setData("temperature", "21.5");

        const auto msgs = tracer.snapshotMessages();
        ASSERT_EQ(msgs.size(), 2U);
        EXPECT_EQ(msgs[0].from, "Subject");
        EXPECT_EQ(msgs[0].to, "Panel");
        EXPECT_EQ(msgs[0].action, "on_notify()");
        EXPECT_EQ(msgs[1].from, "Subject");
        EXPECT_EQ(msgs[1].to, "Alarm");
        EXPECT_EQ(msgs[1].action, "on_notify()");

        const std::vector<std::string> expected_displays = {
            "Observer1: temperature",
            "Observer2: temperature, 21.5",
        };
        EXPECT_EQ(subject.collectDisplays(), expected_displays);
    });

    s.step("panel leaves", [&] {
        // Panel 관찰자의 shared_ptr을 해제하여 약참조를 만료시킨다.
        // Reset the Panel shared_ptr to expire the weak reference.
        panel.reset();
    });

    s.step("second update reaches only the alarm", [&] {
        // 두 번째 데이터 변경은 만료되지 않은 Alarm 관찰자에게만 전달된다.
        // Second update reaches only the unexpired Alarm observer.
        subject.setData("temperature", "30.0");

        const auto msgs = tracer.snapshotMessages();
        ASSERT_EQ(msgs.size(), 3U);
        EXPECT_EQ(msgs[2].from, "Subject");
        EXPECT_EQ(msgs[2].to, "Alarm");
        EXPECT_EQ(msgs[2].action, "on_notify()");

        const std::vector<std::string> expected_displays = {
            "Observer2: temperature, 30.0",
        };
        EXPECT_EQ(subject.collectDisplays(), expected_displays);
    });

    s.step("diagram shows the flow", [&] {
        // Mermaid 형식의 시퀀스 다이어그램 생성 결과를 검증한다.
        // Verify the generated Mermaid sequence diagram.
        const auto diagram = tracer.formatDiagram(viz::DiagramBackend::Mermaid);
        EXPECT_NE(diagram.find("sequenceDiagram"), std::string::npos);

        // mermaidId는 영숫자 이름을 그대로 쓴다. Alarm으로 가는 연속 두 메시지는 한 줄(횟수 표시)로 합쳐질 수 있어 앞부분만 본다.
        // mermaidId keeps alphanumeric names as they are. The two consecutive messages to Alarm may merge into one line with a count, so only its start is checked.
        EXPECT_NE(diagram.find("Subject->>Panel:on_notify()"), std::string::npos);
        EXPECT_NE(diagram.find("Subject->>Alarm:"), std::string::npos);
    });
}
