/**
 * @file main.cpp
 * @brief 레슨 sensor_observers — 센서 값 변경을 여러 수신부에 알리는 Observer 패턴
 * @brief Lesson sensor_observers — The Observer pattern: tell several receivers when a sensor value changes
 *
 * 가상 함수 기반의 고전적 Observer 패턴과 C++20 Concept + std::weak_ptr 기반 구현을 비교하고,
 * 수신부 수명 종료 시 Tracer를 통해 알림 흐름이 어떻게 변화하는지 확인한다.
 *
 * Compare the classic virtual-interface Observer with C++20 Concept + std::weak_ptr,
 * and observe through Tracer how notification flow changes when a receiver goes out of scope.
 */

#include <cstddef>
#include <format>
#include <iostream>
#include <memory>
#include <string>
#include <string_view>
#include <vector>

#include "atugcc/pattern/observer.hpp"
#include "atugcc/pattern/visualizer.hpp"

namespace observer = atugcc::pattern::observer;
namespace viz = atugcc::pattern::viz;

namespace {

// ============================================================================
// Step 1: 고전적 Observer 인터페이스와 구현
// Step 1: Classic Observer interface and implementations
// ============================================================================

// 순수 가상 함수를 가진 고전적 Observer 인터페이스
// Classic Observer interface with pure virtual function
class IObserver {
public:
    virtual ~IObserver() = default;
    virtual void update(std::string_view sensor, std::string_view value) = 0;
};

// 날 포인터를 관리하는 예전 방식의 Sensor (Subject)
// Legacy Sensor (Subject) managing raw pointers
class LegacySensor {
public:
    void attach(IObserver* obs) {
        observers_.push_back(obs);
    }

    void detach(IObserver* obs) {
        std::erase(observers_, obs);
    }

    void set(std::string_view sensor, std::string_view value) {
        for (auto* obs : observers_) {
            obs->update(sensor, value);
        }
    }

private:
    std::vector<IObserver*> observers_;
};

// IObserver를 상속받은 화면 패널
// Legacy panel inheriting from IObserver
class LegacyPanel : public IObserver {
public:
    void update(std::string_view sensor, std::string_view value) override {
        std::cout << std::format("legacy panel: {} = {}\n", sensor, value);
    }
};

// ============================================================================
// Step 2 & 3: C++20 Concept 기반 수신부
// Step 2 & 3: C++20 Concept-based receivers
// ============================================================================

// [학습] 도메인: 장비 센서 값이 바뀔 때 패널 화면(PanelDisplay)과 알람 기록(AlarmLog)에 알린다.
// [학습] Subject::setData(d1, d2)는 (센서 이름, 값 문자열)의 쌍으로 사용한다 (spec 023-02 Assumption 3).
// [Learn] Domain: when a device sensor value changes, notify a panel display (PanelDisplay) and an alarm log (AlarmLog).
// [Learn] Subject::setData(d1, d2) is used as (sensor name, value string) (spec 023-02 Assumption 3).

// 베이스 클래스 없이 ObserverOf 개념을 만족하는 패널 화면
// Panel display satisfying ObserverOf concept without a base class
class PanelDisplay {
public:
    void onNotify(const observer::Subject& subject) {
        sensor_ = subject.data1();
        value_ = subject.data2();
    }

    [[nodiscard]] std::string display() const {
        return std::format("panel: {} = {}", sensor_, value_);
    }

private:
    std::string sensor_;
    std::string value_;
};
static_assert(observer::ObserverOf<PanelDisplay>, "PanelDisplay must satisfy ObserverOf");

// 베이스 클래스 없이 ObserverOf 개념을 만족하는 알람 기록기
// Alarm log satisfying ObserverOf concept without a base class
class AlarmLog {
public:
    void onNotify(const observer::Subject& subject) {
        ++count_;
        last_value_ = subject.data2();
    }

    [[nodiscard]] std::string display() const {
        return std::format("alarm: {} notification(s), last value {}", count_, last_value_);
    }

private:
    std::size_t count_{ 0 };
    std::string last_value_;
};
static_assert(observer::ObserverOf<AlarmLog>, "AlarmLog must satisfy ObserverOf");

} // namespace

int main() {
    // ------------------------------------------------------------------------
    // Step 1: classic Observer (virtual interface, attach/detach)
    // ------------------------------------------------------------------------
    std::cout << "== Step 1: classic Observer (virtual interface, attach/detach) ==\n";

    LegacySensor legacy_sensor;
    LegacyPanel legacy_panel;
    legacy_sensor.attach(&legacy_panel);
    legacy_sensor.set("temperature", "21.5");
    legacy_sensor.detach(&legacy_panel);

    // [학습] detach를 잊은 채 수신부가 소멸되면 관찰자 목록에 댕글링 날 포인터가 남는다.
    // [학습] 다음 set 호출 시 정의되지 않은 동작(UB)이 발생하므로 주의해야 한다 (spec A5: 레슨에서는 이를 실행하지 않음).
    // [Learn] Forgetting detach before the receiver is destroyed leaves a dangling raw pointer in the list.
    // [Learn] The next set call would cause undefined behaviour (spec A5: not run in this lesson).

    // ------------------------------------------------------------------------
    // Step 2: concept + weak_ptr subscription
    // ------------------------------------------------------------------------
    viz::Tracer tracer;
    observer::Subject subject{ tracer };

    auto alarm = std::make_shared<AlarmLog>();

    std::cout << "== Step 2: concept + weak_ptr subscription ==\n";

    // [학습] 이 블록은 패널(panel)의 수명 범위를 한정한다.
    // [학습] 패널을 더 오래 살려 두려면 shared_ptr을 블록 외부 변수로 복사하면 된다 (연습 과제 3, 여기서는 복사하지 않음).
    // [Learn] This block defines the lifetime of the panel.
    // [Learn] To keep it alive longer, copy the shared_ptr to a variable outside the block (exercise 3, not done here).
    {
        auto panel = std::make_shared<PanelDisplay>();
        observer::subscribe(subject, panel, "Panel");
        observer::subscribe(subject, alarm, "Alarm");

        subject.setData("temperature", "21.5");
        subject.setData("temperature", "23.0");

        for (const auto& display_line : subject.collectDisplays()) {
            std::cout << display_line << '\n';
        }
        std::cout << std::format("receivers: {}\n", subject.collectDisplays().size());
    }

    // ------------------------------------------------------------------------
    // Step 3: a receiver goes away
    // ------------------------------------------------------------------------
    std::cout << "== Step 3: a receiver goes away ==\n";

    // [학습] Subject는 std::weak_ptr만 보관하므로, 만료된 패널(panel)은 다음 알림 시 자동으로 감지되어 제거된다.
    // [학습] 따라서 명시적인 detach 호출이 필요 없다.
    // [Learn] The Subject holds only a std::weak_ptr, so the expired panel is dropped at the next notification.
    // [Learn] No explicit detach is needed.
    subject.setData("temperature", "30.0");

    for (const auto& display_line : subject.collectDisplays()) {
        std::cout << display_line << '\n';
    }
    std::cout << std::format("receivers: {}\n", subject.collectDisplays().size());
    std::cout << std::format("messages sent: {}\n", tracer.snapshotMessages().size());

    // ------------------------------------------------------------------------
    // Step 4: trace and diagram
    // ------------------------------------------------------------------------
    std::cout << "== Step 4: trace and diagram ==\n";
    std::cout << tracer.formatTerminal();
    std::cout << "=== Mermaid diagram ===\n";
    std::cout << tracer.formatDiagram(viz::DiagramBackend::Mermaid);

    return 0;
}
