/**
 * @file test_diagram_split.cpp
 * @brief atugcc::pattern::viz -- 다이어그램 분할 및 가독성 단위 테스트 (Spec 020-04)
 *
 * Test groups:
 *   DiagramSplitTest -- AC-1 ~ AC-8, AC-10, Empty Tracer 검증
 */
#include <gtest/gtest.h>
#include <array>
#include <cstddef>
#include <format>
#include <set>
#include <string>
#include <string_view>
#include <vector>

#include "atugcc/pattern/visualizer.hpp"

namespace viz = atugcc::pattern::viz;

namespace {

constexpr std::array<viz::DiagramBackend, 3> kAllBackends = {
    viz::DiagramBackend::PlantUML,
    viz::DiagramBackend::Mermaid,
    viz::DiagramBackend::D2,
};

std::size_t countOccurrences(std::string_view text, std::string_view target) {
    if (target.empty()) {
        return 0;
    }
    std::size_t count = 0;
    std::string_view::size_type pos = 0;
    while ((pos = text.find(target, pos)) != std::string_view::npos) {
        ++count;
        pos += target.size();
    }
    return count;
}

std::string_view commentPrefix(viz::DiagramBackend backend) {
    switch (backend) {
    case viz::DiagramBackend::PlantUML:
        return "' ";
    case viz::DiagramBackend::Mermaid:
        return "%% ";
    case viz::DiagramBackend::D2:
        return "# ";
    }
    return "' ";
}

std::string_view lineBreakForBackend(viz::DiagramBackend backend) {
    switch (backend) {
    case viz::DiagramBackend::Mermaid:
        return "<br/>";
    case viz::DiagramBackend::PlantUML:
    case viz::DiagramBackend::D2:
        return "\\n";
    }
    return "\\n";
}

} // namespace

// ============================================================================
// AC-1: 시퀀스 메시지 수 예산 기반 분할 (세 백엔드)
// ============================================================================
TEST(DiagramSplitTest, AC1_SequenceBudgetSplitsByMessages) {
    viz::Tracer tracer;
    for (int i = 0; i < 40; ++i) {
        const char* from = (i % 3 == 0) ? "A" : ((i % 3 == 1) ? "B" : "C");
        const char* to   = (i % 3 == 0) ? "B" : ((i % 3 == 1) ? "C" : "A");
        (void)tracer.recordMessage(from, to, std::format("m{:02d}", i));
    }

    for (auto backend : kAllBackends) {
        const auto parts = tracer.diagramParts(backend);
        ASSERT_EQ(parts.size(), 3u);

        EXPECT_EQ(parts[0].kind, viz::DiagramKind::Sequence);
        EXPECT_EQ(parts[1].kind, viz::DiagramKind::Sequence);
        EXPECT_EQ(parts[2].kind, viz::DiagramKind::Sequence);

        EXPECT_EQ(parts[0].backend, backend);
        EXPECT_EQ(parts[1].backend, backend);
        EXPECT_EQ(parts[2].backend, backend);

        EXPECT_EQ(parts[0].title, "Sequence (1/3)");
        EXPECT_EQ(parts[1].title, "Sequence (2/3)");
        EXPECT_EQ(parts[2].title, "Sequence (3/3)");

        EXPECT_FALSE(parts[0].overBudget);
        EXPECT_FALSE(parts[1].overBudget);
        EXPECT_FALSE(parts[2].overBudget);

        std::size_t part0Labels = 0;
        std::size_t part1Labels = 0;
        std::size_t part2Labels = 0;

        for (int i = 0; i < 40; ++i) {
            const std::string label = std::format("m{:02d}", i);
            const std::size_t c0 = countOccurrences(parts[0].source, label);
            const std::size_t c1 = countOccurrences(parts[1].source, label);
            const std::size_t c2 = countOccurrences(parts[2].source, label);

            EXPECT_EQ(c0 + c1 + c2, 1u);

            if (i < 15) {
                EXPECT_EQ(c0, 1u);
                EXPECT_EQ(c1, 0u);
                EXPECT_EQ(c2, 0u);
            } else if (i < 30) {
                EXPECT_EQ(c0, 0u);
                EXPECT_EQ(c1, 1u);
                EXPECT_EQ(c2, 0u);
            } else {
                EXPECT_EQ(c0, 0u);
                EXPECT_EQ(c1, 0u);
                EXPECT_EQ(c2, 1u);
            }

            part0Labels += c0;
            part1Labels += c1;
            part2Labels += c2;
        }

        EXPECT_EQ(part0Labels, 15u);
        EXPECT_EQ(part1Labels, 15u);
        EXPECT_EQ(part2Labels, 10u);

        for (int i = 0; i < 14; ++i) {
            const auto posA = parts[0].source.find(std::format("m{:02d}", i));
            const auto posB = parts[0].source.find(std::format("m{:02d}", i + 1));
            EXPECT_LT(posA, posB);
        }
        for (int i = 15; i < 29; ++i) {
            const auto posA = parts[1].source.find(std::format("m{:02d}", i));
            const auto posB = parts[1].source.find(std::format("m{:02d}", i + 1));
            EXPECT_LT(posA, posB);
        }
        for (int i = 30; i < 39; ++i) {
            const auto posA = parts[2].source.find(std::format("m{:02d}", i));
            const auto posB = parts[2].source.find(std::format("m{:02d}", i + 1));
            EXPECT_LT(posA, posB);
        }
    }
}

// ============================================================================
// AC-2: 시퀀스 참여자 수 예산 기반 분할 (세 백엔드)
// ============================================================================
TEST(DiagramSplitTest, AC2_SequenceBudgetSplitsByParticipants) {
    viz::Tracer tracer;
    for (int i = 0; i < 20; ++i) {
        const std::string from = std::format("P{}", i % 8);
        const std::string to   = std::format("P{}", (i + 1) % 8);
        const std::string label = std::format("msg{:02d}", i);
        (void)tracer.recordMessage(from, to, label);
    }

    for (auto backend : kAllBackends) {
        const auto parts = tracer.diagramParts(backend);
        ASSERT_EQ(parts.size(), 5u);

        std::set<std::string> unionParticipants;

        for (std::size_t k = 0; k < parts.size(); ++k) {
            const auto& part = parts[k];
            EXPECT_EQ(part.kind, viz::DiagramKind::Sequence);
            EXPECT_EQ(part.title, std::format("Sequence ({}/5)", k + 1));

            if (backend == viz::DiagramBackend::Mermaid) {
                EXPECT_EQ(countOccurrences(part.source, "->>"), 4u);
            } else {
                EXPECT_EQ(countOccurrences(part.source, "->"), 4u);
            }

            std::size_t participantCountInPart = 0;
            for (int p = 0; p < 8; ++p) {
                const std::string pName = std::format("P{}", p);
                if (part.source.find(pName) != std::string::npos) {
                    ++participantCountInPart;
                    unionParticipants.insert(pName);
                }
            }
            EXPECT_LE(participantCountInPart, 5u);
        }

        for (int i = 0; i < 20; ++i) {
            const std::string label = std::format("msg{:02d}", i);
            std::size_t totalCount = 0;
            for (const auto& part : parts) {
                totalCount += countOccurrences(part.source, label);
            }
            EXPECT_EQ(totalCount, 1u);
        }

        EXPECT_EQ(unionParticipants.size(), 8u);
    }
}

// ============================================================================
// AC-3: 연속 동일 메시지 합치기 및 반복 표기 (세 백엔드)
// ============================================================================
TEST(DiagramSplitTest, AC3_ConsecutiveMessagesMergedWithCount) {
    // 1) "notify()" from S to O 3회 연속
    viz::Tracer tracer1;
    (void)tracer1.recordMessage("S", "O", "notify()");
    (void)tracer1.recordMessage("S", "O", "notify()");
    (void)tracer1.recordMessage("S", "O", "notify()");

    for (auto backend : kAllBackends) {
        const auto parts = tracer1.diagramParts(backend);
        ASSERT_EQ(parts.size(), 1u);
        EXPECT_EQ(parts[0].kind, viz::DiagramKind::Sequence);
        EXPECT_EQ(countOccurrences(parts[0].source, "notify() \xC3\x97" "3"), 1u);
        EXPECT_EQ(countOccurrences(parts[0].source, "notify()"), 1u);

        if (backend == viz::DiagramBackend::Mermaid) {
            EXPECT_EQ(countOccurrences(parts[0].source, "->>"), 1u);
        } else {
            EXPECT_EQ(countOccurrences(parts[0].source, "->"), 1u);
        }
    }

    // 2) A->B labels "a()", "b()", "a()"
    viz::Tracer tracer2;
    (void)tracer2.recordMessage("A", "B", "a()");
    (void)tracer2.recordMessage("A", "B", "b()");
    (void)tracer2.recordMessage("A", "B", "a()");

    for (auto backend : kAllBackends) {
        const auto parts = tracer2.diagramParts(backend);
        ASSERT_EQ(parts.size(), 1u);
        EXPECT_EQ(parts[0].kind, viz::DiagramKind::Sequence);
        EXPECT_EQ(parts[0].source.find("\xC3\x97"), std::string::npos);
        EXPECT_EQ(countOccurrences(parts[0].source, "a()"), 2u);
        EXPECT_EQ(countOccurrences(parts[0].source, "b()"), 1u);

        if (backend == viz::DiagramBackend::Mermaid) {
            EXPECT_EQ(countOccurrences(parts[0].source, "->>"), 3u);
        } else {
            EXPECT_EQ(countOccurrences(parts[0].source, "->"), 3u);
        }

        const auto firstA = parts[0].source.find("a()");
        const auto posB   = parts[0].source.find("b()");
        const auto secondA = parts[0].source.find("a()", posB);
        EXPECT_NE(firstA, std::string::npos);
        EXPECT_NE(posB, std::string::npos);
        EXPECT_NE(secondA, std::string::npos);
        EXPECT_LT(firstA, posB);
        EXPECT_LT(posB, secondA);
    }
}

// ============================================================================
// AC-4: 상태 전이 중복 합치기 및 예산 초과 주석 (세 백엔드)
// ============================================================================
TEST(DiagramSplitTest, AC4_StateTransitionsCountAndOverBudget) {
    // 1) 비연속 동일 전이: X->Y "go", Y->X "back", X->Y "go" -> "go ×2" 1개, "back" 1개("×" 없음)
    viz::Tracer tracer1;
    (void)tracer1.recordTransition("X", "Y", "go");
    (void)tracer1.recordTransition("Y", "X", "back");
    (void)tracer1.recordTransition("X", "Y", "go");

    for (auto backend : kAllBackends) {
        const auto parts = tracer1.diagramParts(backend);
        ASSERT_EQ(parts.size(), 1u);
        EXPECT_EQ(parts[0].kind, viz::DiagramKind::State);
        EXPECT_FALSE(parts[0].overBudget);
        EXPECT_EQ(countOccurrences(parts[0].source, "go \xC3\x97" "2"), 1u);
        EXPECT_EQ(countOccurrences(parts[0].source, "go"), 1u);
        EXPECT_EQ(countOccurrences(parts[0].source, "back"), 1u);
        EXPECT_EQ(parts[0].source.find("back \xC3\x97"), std::string::npos);

        if (backend == viz::DiagramBackend::D2) {
            EXPECT_EQ(countOccurrences(parts[0].source, "->"), 2u);
        } else {
            EXPECT_EQ(countOccurrences(parts[0].source, "-->"), 2u);
        }
    }

    // 2) 경계값: 12개 상태 체인(11개 전이) -> overBudget == false, "over budget" 없음
    viz::Tracer tracer2;
    for (int i = 0; i < 11; ++i) {
        (void)tracer2.recordTransition(std::format("S{}", i), std::format("S{}", i + 1), std::format("t{}", i));
    }

    for (auto backend : kAllBackends) {
        const auto parts = tracer2.diagramParts(backend);
        ASSERT_EQ(parts.size(), 1u);
        EXPECT_EQ(parts[0].kind, viz::DiagramKind::State);
        EXPECT_FALSE(parts[0].overBudget);
        EXPECT_EQ(parts[0].source.find("over budget"), std::string::npos);
    }

    // 3) 경계값: 13개 상태 체인(12개 전이) -> overBudget == true, "<prefix>over budget: states 13 > 12"
    viz::Tracer tracer3;
    for (int i = 0; i < 12; ++i) {
        (void)tracer3.recordTransition(std::format("S{}", i), std::format("S{}", i + 1), std::format("t{}", i));
    }

    for (auto backend : kAllBackends) {
        const auto parts = tracer3.diagramParts(backend);
        ASSERT_EQ(parts.size(), 1u);
        EXPECT_EQ(parts[0].kind, viz::DiagramKind::State);
        EXPECT_TRUE(parts[0].overBudget);
        const std::string expectedNote = std::format("{}over budget: states 13 > 12", commentPrefix(backend));
        EXPECT_NE(parts[0].source.find(expectedNote), std::string::npos);
    }
}

// ============================================================================
// AC-5: 구조 트리 분할, 중복 제거 및 예산 초과 (세 백엔드)
// ============================================================================
TEST(DiagramSplitTest, AC5_StructureTreeSplitsAndOverBudget) {
    // 1) 같은 관계 2회 등록 -> 1개 간선, "×" 없음
    viz::Tracer tracer1;
    (void)tracer1.pushNode("Parent", "Child", "contains");
    (void)tracer1.pushNode("Parent", "Child", "contains");

    for (auto backend : kAllBackends) {
        const auto parts = tracer1.diagramParts(backend);
        ASSERT_EQ(parts.size(), 1u);
        EXPECT_EQ(parts[0].kind, viz::DiagramKind::Structure);
        EXPECT_FALSE(parts[0].overBudget);
        EXPECT_EQ(parts[0].source.find("\xC3\x97"), std::string::npos);
        EXPECT_EQ(countOccurrences(parts[0].source, "Parent"), 1u);
        EXPECT_EQ(countOccurrences(parts[0].source, "Child"), 1u);
        EXPECT_EQ(countOccurrences(parts[0].source, "contains"), 1u);

        if (backend == viz::DiagramBackend::D2) {
            EXPECT_EQ(countOccurrences(parts[0].source, "->"), 1u);
        } else {
            EXPECT_EQ(countOccurrences(parts[0].source, "-->"), 1u);
        }
    }

    // 2) 루트 R + 4개 자식 C0..C3, 각 4개 손자 (총 21 노드) -> 여러 Structure 조각
    viz::Tracer tracer2;
    for (int i = 0; i < 4; ++i) {
        const std::string c = std::format("C{}", i);
        (void)tracer2.pushNode("R", c, "child");
        for (int j = 0; j < 4; ++j) {
            const std::string g = std::format("G{}_{}", i, j);
            (void)tracer2.pushNode(c, g, "child");
        }
    }

    for (auto backend : kAllBackends) {
        const auto parts = tracer2.diagramParts(backend);
        EXPECT_GT(parts.size(), 1u);

        for (std::size_t k = 0; k < parts.size(); ++k) {
            EXPECT_EQ(parts[k].kind, viz::DiagramKind::Structure);
            EXPECT_EQ(parts[k].title, std::format("Structure ({}/{})", k + 1, parts.size()));
        }

        auto countRelation = [&](std::string_view parent, std::string_view child) {
            std::size_t total = 0;
            const std::string relPlantUml = std::format("{} --> {} :", parent, child);
            const std::string relD2 = std::format("{} -> {}:", parent, child);
            const std::string_view pattern = (backend == viz::DiagramBackend::D2) ? relD2 : relPlantUml;
            for (const auto& part : parts) {
                total += countOccurrences(part.source, pattern);
            }
            return total;
        };

        for (int i = 0; i < 4; ++i) {
            const std::string c = std::format("C{}", i);
            EXPECT_EQ(countRelation("R", c), 1u);
            for (int j = 0; j < 4; ++j) {
                const std::string g = std::format("G{}_{}", i, j);
                EXPECT_EQ(countRelation(c, g), 1u);
            }
        }

        // [Tester] 각 조각 <= maxNodes(12) 이름, overBudget 아님 (spec AC-5)
        for (const auto& part : parts) {
            std::set<std::string> names;
            auto addIfPresent = [&](const std::string& parent, const std::string& child) {
                const std::string relPlantUml = std::format("{} --> {} :", parent, child);
                const std::string relD2 = std::format("{} -> {}:", parent, child);
                const std::string& pattern = (backend == viz::DiagramBackend::D2) ? relD2 : relPlantUml;
                if (part.source.find(pattern) != std::string::npos) {
                    names.insert(parent);
                    names.insert(child);
                }
            };
            for (int i = 0; i < 4; ++i) {
                const std::string c = std::format("C{}", i);
                addIfPresent("R", c);
                for (int j = 0; j < 4; ++j) {
                    addIfPresent(c, std::format("G{}_{}", i, j));
                }
            }
            EXPECT_FALSE(names.empty());
            EXPECT_LE(names.size(), 12u);
            EXPECT_FALSE(part.overBudget);
        }
    }

    // 3) 1개 노드에 13개 자식 -> 1개 Structure 조각, overBudget == true, "<prefix>over budget: nodes 14 > 12", 13개 관계 모두 포함
    viz::Tracer tracer3;
    for (int i = 0; i < 13; ++i) {
        (void)tracer3.pushNode("Root", std::format("Child{:02d}", i), "edge");
    }

    for (auto backend : kAllBackends) {
        const auto parts = tracer3.diagramParts(backend);
        ASSERT_EQ(parts.size(), 1u);
        EXPECT_EQ(parts[0].kind, viz::DiagramKind::Structure);
        EXPECT_TRUE(parts[0].overBudget);
        const std::string expectedNote = std::format("{}over budget: nodes 14 > 12", commentPrefix(backend));
        EXPECT_NE(parts[0].source.find(expectedNote), std::string::npos);

        for (int i = 0; i < 13; ++i) {
            const std::string child = std::format("Child{:02d}", i);
            const std::string relPlantUml = std::format("Root --> {} :", child);
            const std::string relD2 = std::format("Root -> {}:", child);
            const std::string_view pattern = (backend == viz::DiagramBackend::D2) ? relD2 : relPlantUml;
            EXPECT_EQ(countOccurrences(parts[0].source, pattern), 1u);
        }
    }
}

// ============================================================================
// AC-6: 라벨 줄바꿈 및 Mermaid 세미콜론 이스케이프 (세 백엔드)
// ============================================================================
TEST(DiagramSplitTest, AC6_LabelLineBreakAndMermaidEscape) {
    viz::Tracer tracer1;
    (void)tracer1.recordMessage("Sender", "Receiver", "alpha beta gamma delta epsilon");

    for (auto backend : kAllBackends) {
        const auto parts = tracer1.diagramParts(backend);
        ASSERT_EQ(parts.size(), 1u);
        const std::string expectedLabel = std::format("alpha beta gamma delta{}epsilon", lineBreakForBackend(backend));
        EXPECT_NE(parts[0].source.find(expectedLabel), std::string::npos);
    }

    viz::Tracer tracer2;
    (void)tracer2.recordMessage("A", "B", "a;b");
    const auto mermaidParts = tracer2.diagramParts(viz::DiagramBackend::Mermaid);
    ASSERT_EQ(mermaidParts.size(), 1u);
    EXPECT_NE(mermaidParts[0].source.find("a#59;b"), std::string::npos);
    EXPECT_EQ(mermaidParts[0].source.find("a;b"), std::string::npos);
}

// ============================================================================
// AC-7: 예산 내 단일 조각 다이어그램 포맷팅 (세 백엔드)
// ============================================================================
TEST(DiagramSplitTest, FormatDiagramJoinsUnsplitPartsWithoutHeaders) {
    viz::Tracer tracer;
    (void)tracer.recordMessage("A", "B", "m1");
    (void)tracer.recordMessage("B", "C", "m2");
    (void)tracer.recordTransition("S1", "S2", "t1");
    (void)tracer.pushNode("P", "C", "rel");

    for (auto backend : kAllBackends) {
        const auto parts = tracer.diagramParts(backend);
        ASSERT_EQ(parts.size(), 3u);

        EXPECT_EQ(parts[0].kind, viz::DiagramKind::Sequence);
        EXPECT_EQ(parts[1].kind, viz::DiagramKind::State);
        EXPECT_EQ(parts[2].kind, viz::DiagramKind::Structure);

        EXPECT_EQ(parts[0].title, "Sequence");
        EXPECT_EQ(parts[1].title, "State");
        EXPECT_EQ(parts[2].title, "Structure");

        for (const auto& part : parts) {
            EXPECT_EQ(part.title.find('('), std::string::npos);
            EXPECT_FALSE(part.overBudget);
        }

        std::string expected;
        for (const auto& part : parts) {
            expected += part.source;
            expected += '\n';
        }

        const std::string formatted = tracer.formatDiagram(backend);
        EXPECT_EQ(formatted, expected);

        EXPECT_EQ(formatted.find(std::format("{}Sequence", commentPrefix(backend))), std::string::npos);
        EXPECT_EQ(formatted.find(std::format("{}State", commentPrefix(backend))), std::string::npos);
        EXPECT_EQ(formatted.find(std::format("{}Structure", commentPrefix(backend))), std::string::npos);
    }
}

// ============================================================================
// [Tester] AC-7: 분할·반복이 없는 trace의 출력은 020-04 이전과 바이트 단위로 같다.
// 기대 문자열은 main(020-04 이전) 헤더로 빌드한 같은 trace의 실제 출력이다.
// ============================================================================
TEST(DiagramSplitTest, AC7_OutputUnchangedFromBeforeSplitting) {
    viz::Tracer tracer;
    (void)tracer.recordMessage("A", "B", "m1");
    (void)tracer.recordMessage("B", "C", "m2");
    (void)tracer.recordTransition("S1", "S2", "t1");
    (void)tracer.recordTransition("S2", "S3", "t2");
    (void)tracer.pushNode("P", "C", "rel");
    (void)tracer.pushNode("P", "D", "rel");

    const std::string plantUml =
        "' sequence/message flow\n@startuml\nA -> B : m1\nB -> C : m2\n@enduml\n\n"
        "' state transitions\n@startuml\nS1 --> S2 : t1\nS2 --> S3 : t2\n@enduml\n\n"
        "' class/structure tree\n@startuml\nP --> C : rel\nP --> D : rel\n@enduml\n\n";
    const std::string mermaid =
        "```mermaid\nsequenceDiagram\n    A->>B:m1\n    B->>C:m2\n```\n\n"
        "```mermaid\nstateDiagram-v2\n    S1 --> S2 : t1\n    S2 --> S3 : t2\n```\n\n"
        "```mermaid\nclassDiagram\n    P --> C : rel\n    P --> D : rel\n```\n\n";
    const std::string d2 =
        "# sequence/message flow\nA -> B: m1\nB -> C: m2\n\n"
        "# state transitions\nS1 -> S2: t1\nS2 -> S3: t2\n\n"
        "# class/structure tree\nP -> C: rel\nP -> D: rel\n\n";

    EXPECT_EQ(tracer.formatDiagram(viz::DiagramBackend::PlantUML), plantUml);
    EXPECT_EQ(tracer.formatDiagram(viz::DiagramBackend::Mermaid), mermaid);
    EXPECT_EQ(tracer.formatDiagram(viz::DiagramBackend::D2), d2);
    EXPECT_EQ(tracer.formatPlantuml(), plantUml);
    EXPECT_EQ(tracer.formatMermaid(), mermaid);
    EXPECT_EQ(tracer.formatD2(), d2);
}

// ============================================================================
// AC-8: 예산 0 입력 시 1로 보정 및 정상 분할
// ============================================================================
TEST(DiagramSplitTest, AC8_ZeroBudgetClampedToOne) {
    // 1) maxMessages = 0 with 3 messages between the SAME two participants A->B
    {
        viz::Tracer tracer;
        (void)tracer.recordMessage("A", "B", "m1");
        (void)tracer.recordMessage("A", "B", "m2");
        (void)tracer.recordMessage("A", "B", "m3");

        const viz::DiagramBudget zeroMsgBudget{ .maxMessages = 0 };

        for (auto backend : kAllBackends) {
            const auto parts = tracer.diagramParts(backend, zeroMsgBudget);
            ASSERT_EQ(parts.size(), 3u);

            EXPECT_EQ(parts[0].title, "Sequence (1/3)");
            EXPECT_EQ(parts[1].title, "Sequence (2/3)");
            EXPECT_EQ(parts[2].title, "Sequence (3/3)");

            EXPECT_EQ(countOccurrences(parts[0].source, "m1"), 1u);
            EXPECT_EQ(countOccurrences(parts[0].source, "m2"), 0u);
            EXPECT_EQ(countOccurrences(parts[0].source, "m3"), 0u);

            EXPECT_EQ(countOccurrences(parts[1].source, "m1"), 0u);
            EXPECT_EQ(countOccurrences(parts[1].source, "m2"), 1u);
            EXPECT_EQ(countOccurrences(parts[1].source, "m3"), 0u);

            EXPECT_EQ(countOccurrences(parts[2].source, "m1"), 0u);
            EXPECT_EQ(countOccurrences(parts[2].source, "m2"), 0u);
            EXPECT_EQ(countOccurrences(parts[2].source, "m3"), 1u);

            for (const auto& part : parts) {
                if (backend == viz::DiagramBackend::Mermaid) {
                    EXPECT_EQ(countOccurrences(part.source, "->>"), 1u);
                } else {
                    EXPECT_EQ(countOccurrences(part.source, "->"), 1u);
                }
            }
        }
    }

    // 2) labelWrap = 0 with one message "ab" -> no hang, source contains "a" + LB + "b"
    {
        viz::Tracer tracer;
        (void)tracer.recordMessage("A", "B", "ab");

        const viz::DiagramBudget zeroWrapBudget{ .labelWrap = 0 };

        for (auto backend : kAllBackends) {
            const auto parts = tracer.diagramParts(backend, zeroWrapBudget);
            ASSERT_EQ(parts.size(), 1u);
            const std::string expectedWrap = std::format("a{}b", lineBreakForBackend(backend));
            EXPECT_NE(parts[0].source.find(expectedWrap), std::string::npos);
        }
    }
}

// ============================================================================
// AC-10: 분할된 다이어그램 포맷팅 시 조각 제목 주석 삽입 (세 백엔드)
// ============================================================================
TEST(DiagramSplitTest, AC10_FormattedDiagramIncludesPartCommentHeaders) {
    // 1) AC-1 분할 시퀀스 trace: 각 조각 앞에 <prefix>Sequence (k/3) 포함
    {
        viz::Tracer tracer;
        for (int i = 0; i < 40; ++i) {
            const char* from = (i % 3 == 0) ? "A" : ((i % 3 == 1) ? "B" : "C");
            const char* to   = (i % 3 == 0) ? "B" : ((i % 3 == 1) ? "C" : "A");
            (void)tracer.recordMessage(from, to, std::format("m{:02d}", i));
        }

        for (auto backend : kAllBackends) {
            const auto parts = tracer.diagramParts(backend);
            ASSERT_EQ(parts.size(), 3u);

            const std::string formatted = tracer.formatDiagram(backend);
            const std::string_view prefix = commentPrefix(backend);

            const std::string header1 = std::format("{}Sequence (1/3)\n", prefix);
            const std::string header2 = std::format("{}Sequence (2/3)\n", prefix);
            const std::string header3 = std::format("{}Sequence (3/3)\n", prefix);

            const auto posH1 = formatted.find(header1);
            const auto posS1 = formatted.find(parts[0].source);
            const auto posH2 = formatted.find(header2);
            const auto posS2 = formatted.find(parts[1].source);
            const auto posH3 = formatted.find(header3);
            const auto posS3 = formatted.find(parts[2].source);

            EXPECT_NE(posH1, std::string::npos);
            EXPECT_NE(posS1, std::string::npos);
            EXPECT_NE(posH2, std::string::npos);
            EXPECT_NE(posS2, std::string::npos);
            EXPECT_NE(posH3, std::string::npos);
            EXPECT_NE(posS3, std::string::npos);

            EXPECT_EQ(posH1 + header1.size(), posS1);
            EXPECT_EQ(posH2 + header2.size(), posS2);
            EXPECT_EQ(posH3 + header3.size(), posS3);

            EXPECT_LT(posS1, posS2);
            EXPECT_LT(posS2, posS3);
        }
    }

    // 2) 혼합 trace: 40개 메시지 시퀀스 + 1개 상태 전이 S1->S2 "t"
    // State 조각에는 헤더 주석이 없고, formatDiagram은 정확히 각 Sequence 조각 헤더+소스 뒤에 State 소스가 붙는다
    {
        viz::Tracer tracer;
        for (int i = 0; i < 40; ++i) {
            const char* from = (i % 3 == 0) ? "A" : ((i % 3 == 1) ? "B" : "C");
            const char* to   = (i % 3 == 0) ? "B" : ((i % 3 == 1) ? "C" : "A");
            (void)tracer.recordMessage(from, to, std::format("m{:02d}", i));
        }
        (void)tracer.recordTransition("S1", "S2", "t");

        for (auto backend : kAllBackends) {
            const auto parts = tracer.diagramParts(backend);
            ASSERT_EQ(parts.size(), 4u);
            EXPECT_EQ(parts[0].kind, viz::DiagramKind::Sequence);
            EXPECT_EQ(parts[1].kind, viz::DiagramKind::Sequence);
            EXPECT_EQ(parts[2].kind, viz::DiagramKind::Sequence);
            EXPECT_EQ(parts[3].kind, viz::DiagramKind::State);

            const std::string formatted = tracer.formatDiagram(backend);
            const std::string_view prefix = commentPrefix(backend);

            EXPECT_EQ(formatted.find(std::format("{}State", prefix)), std::string::npos);

            std::string expected;
            for (std::size_t k = 0; k < 3; ++k) {
                expected += std::format("{}Sequence ({}/3)\n", prefix, k + 1);
                expected += parts[k].source;
                expected += '\n';
            }
            expected += parts[3].source;
            expected += '\n';

            EXPECT_EQ(formatted, expected);
        }
    }
}

// ============================================================================
// 빈 Tracer: diagramParts는 빈 벡터, formatDiagram은 빈 문자열
// ============================================================================
TEST(DiagramSplitTest, EmptyTracerReturnsEmptyPartsAndEmptyString) {
    viz::Tracer tracer;
    for (auto backend : kAllBackends) {
        const auto parts = tracer.diagramParts(backend);
        EXPECT_TRUE(parts.empty());

        const std::string formatted = tracer.formatDiagram(backend);
        EXPECT_TRUE(formatted.empty());
    }
}
