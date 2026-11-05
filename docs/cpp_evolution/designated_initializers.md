# C++ Evolution: 옵션 구조체와 지정 초기화(Designated Initializers)

## Why
`Tracer::diagramParts()`와 `formatDiagram()`은 한도 다섯 개를 담은 `DiagramBudget`을 받습니다. 호출하는 쪽은 보통 그중 하나만 바꾸고 싶어 합니다. 옵션 객체를 어떻게 만드느냐에 따라, 호출하는 코드가 *어느* 값을 바꾸는지 드러나는지가 갈립니다.

```cpp
struct DiagramBudget {
    std::size_t maxParticipants = 5;
    std::size_t maxMessages     = 15;
    std::size_t maxStates       = 12;
    std::size_t maxNodes        = 12;
    std::size_t labelWrap       = 24;
};
```

## C++14/17 (Legacy)
하나는 위치 기반 집합체 초기화입니다. 앞쪽 필드를 모두 다시 써야 하고, 읽는 사람은 위치를 세어야 합니다(C++14 이상. C++11에서는 기본 멤버 초기화가 있는 구조체가 집합체가 아니라서 이것조차 컴파일되지 않습니다).

```cpp
DiagramBudget budget{5, 30};             // which one is 30?
tracer.formatDiagram(DiagramBackend::Mermaid, budget);
```

다른 하나는 옵션 타입마다 손으로 쓰는 빌더/setter 체인입니다.

```cpp
auto budget = DiagramBudget{}.withMaxMessages(30);   // extra code per field
```

## C++20 (Modern)
지정 초기화는 필드 이름을 대고, 나머지 필드는 모두 기본 멤버 초기화 값을 유지합니다.

```cpp
tracer.formatDiagram(DiagramBackend::Mermaid, {.maxMessages = 30});
tracer.diagramParts(DiagramBackend::PlantUML, {.maxParticipants = 4, .labelWrap = 32});
```

알아 둘 규칙:
- 지정자는 선언 순서를 따라야 합니다(`{.labelWrap = 32, .maxMessages = 30}`은 컴파일되지 않습니다).
- 집합체만 됩니다: 사용자가 선언했거나 상속받은 생성자가 없고, private이나 protected인 비정적 데이터 멤버가 없고, 가상 함수가 없고, virtual·private·protected 기반 클래스가 없어야 합니다. (private 멤버 함수와 정적 멤버는 괜찮습니다.)
- 이름을 대지 않은 필드는 기본 멤버 초기화 값을 유지합니다.

## C++23 (Latest)
지정 초기화에 새로 생긴 것은 없습니다. 옵션 구조체 패턴은 atugcc의 다른 곳에 있는 C++23 코드와 잘 어울립니다. 예를 들어 사용자 입력을 검증한 뒤 `core::Expected<Options>`(`std::expected<Options, CoreError>`, [`error.hpp`](/include/atugcc/core/error.hpp))를 돌려주는 함수가 있고, 호출하는 쪽은 그 값을 그대로 넘깁니다.

## In atugcc
- [`visualizer.hpp`](/include/atugcc/pattern/visualizer.hpp): `DiagramBudget`, `diagramParts()`, `formatDiagram()`
- [`example_visualizer.cpp`](/src/pattern/example_visualizer.cpp): Demo 4가 `{.maxParticipants = 4}`를 씁니다
- 스펙: [020-04](/docs/specs/020_04_diagram_readability.md)
