# Spec: atugcc::pattern::visualizer

## Objective
디자인 패턴의 동작 방식과 구조적 변화를 런타임 환경에서 직관적으로 확인할 수 있도록 돕는 시각화(Visualization) 도구 및 트레이서를 구현합니다. 이 라이브러리는 모든 디자인 패턴 예제에 공통으로 주입되어 실행 흐름, 상태 전이, 객체 상호작용의 교육적 지표(Live Documentation) 역할을 합니다.

## Requirement Details

### 1. Terminal / ASCII 기반 시각화 (Console UI)
터미널에서 텍스트 색상 및 기호 라우팅을 사용하여 동적으로 시스템 흐름을 표시합니다.
- **Tree Visualizer (구조 패턴 활용)**: `├─`, `└─` 등의 ASCII 문자를 활용하여 런타임에 결합된 Decorator, Composite 클래스의 부모-자식 관계나 크기를 시각적으로 출력합니다.
- **State Transition Flow (상태 패턴 활용)**: `[LOCKED] ---> (coin) ---> [UNLOCKED]` 형태의 콘솔 기반 흐름도를 출력합니다.
- **Color Logging**: `atugcc::core::alog` 와 연동하여 역할(Role)이나 객체 타입별로 고유한 ANSI 색상을 부여, 텍스트 로깅의 가독성을 대폭 향상시킵니다.

### 2. Markdown / D2 스니펫 출력 모드
실행이 끝난 후, 혹은 디버깅 파이프라인에서 바로 문서에 삽입할 수 있는 마크다운 호환 스니펫을 생성합니다.
- **Message Flow**: Observer, Facade, Command 실행 시, 객체 A가 B에게 어떤 메시지를 보냈는지 순차적으로 수집하여 `A -> B: action` 형식의 D2 문법 데이터로 내보냅니다.
- **State Flow**: State 패턴의 전이 내역을 바탕으로 `OLD -> NEW: trigger` 형식의 D2 스크립트를 출력합니다.

## Architecture & API Design

### 인터페이스 스케치 (`atugcc/pattern/visualizer.hpp` 등)
```cpp
namespace atugcc::pattern::viz {

    // 디자인 패턴 컴포넌트나 이벤트가 발생할 때 트레이싱하는 코어 클래스
    class Tracer {
    public:
        // 시퀀스/메시지 호출 기록용
        void record_message(std::string_view from, std::string_view to, std::string_view action);
        
        // 상태 전이 기록용
        void record_transition(std::string_view old_state, std::string_view new_state, std::string_view trigger);
        
        // 구조 트리 기록용 (부모/자식 노드 연동)
        void push_node(std::string_view parent, std::string_view child, std::string_view relation_type);

        // 시각화 결과물 출력
        void print_terminal() const;
        void print_d2() const;
    };

    // 전역 싱글톤 스코프 트레이서 
    Tracer& get_global_tracer();
}
```

## Technical Constraints & Implementation Steps
- **C++ Standard**: C++20 기반 (`std::format`, `std::string_view`, `std::source_location` 적극 활용)
- **Dependencies**: 헤더 온리 또는 정적 라이브러리(`atugcc::core` 외 다른 특별한 서드파티 의존성 없이 순수 C++ 구현 유지). 단 터미널 ANSI 색상을 제어할 OS 호환 코드가 필요할 수 있음.

### Implementation Plan
- [ ] Step 1: `Tracer` 인터페이스 및 메모리에 실행 로그 내역(Message 구조체)을 담는 코어 자료구조 개발
- [ ] Step 2: 터미널 ANSI 색상 및 들여쓰기 처리를 위한 `TerminalFormatter` 개발
- [ ] Step 3: D2 출력을 담당하는 `D2Formatter` 개발
- [ ] Step 4: `example_visualizer.cpp` 모의(Mock) 실행 파일을 생성하여 로깅이 예쁘게 콘솔과 D2로 출력되는 지 확인.
