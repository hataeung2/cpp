/**
 * @file trace_stream_probe.cpp
 * @brief Probe for check_trace_stream.py (spec 020-05 AC-2, AC-4, AC-5; spec 020-06 AC-3, AC-8)
 *
 * Records events on two Tracers (one fed by two threads) and spans on the first, and prints,
 * before the Tracers are destroyed, one JSON object with what the stream must contain: the number
 * of recorded events and spans and the Mermaid part count per Tracer and diagram kind. The destructors
 * then write the `diagram` lines when ATUGCC_TRACE_OUT is set. stdout must not depend on the
 * variable.
 */
#include <chrono>
#include <cstddef>
#include <cstdio>
#include <format>
#include <source_location>
#include <string>
#include <thread>
#include <vector>

#include "atugcc/pattern/visualizer.hpp"

namespace viz = atugcc::pattern::viz;

namespace {

std::string partCounts(const viz::Tracer& tracer) {
    std::size_t sequence = 0;
    std::size_t state = 0;
    std::size_t structure = 0;
    for (const auto& part : tracer.diagramParts(viz::DiagramBackend::Mermaid)) {
        switch (part.kind) {
        case viz::DiagramKind::Sequence:  ++sequence;  break;
        case viz::DiagramKind::State:     ++state;     break;
        case viz::DiagramKind::Structure: ++structure; break;
        }
    }
    return std::format(R"("{}":{{"sequence":{},"state":{},"structure":{}}})",
        tracer.id(), sequence, state, structure);
}

} // namespace

int main() {
    // Same list as EXPECTED_LABELS in check_trace_stream.py (the script does not trust the probe for them).
    // "\x01" "f" is split on purpose: "\x01f" would be one hex escape (0x1f)
    const std::vector<std::string> tricky_labels{
        "Quote\"Back\\slash",
        "Tab\tNew\nline\rCR",
        "bs\bff\fctl\x01" "f\x1f" "end",
        "한글 라벨",
    };

    std::size_t recorded = 0;
    auto count = [&recorded](const atugcc::core::Result& result) {
        if (result.has_value()) {
            ++recorded;
        }
    };

    viz::Tracer first;
    viz::Tracer second;

    for (const auto& label : tricky_labels) {
        count(first.recordMessage("Client", "Server", label));
    }
    count(first.recordTransition("IDLE", "RUN", "start"));
    count(first.recordTransition("RUN", "IDLE", "stop"));
    count(first.pushNode("Root", "Leaf", "contains"));
    count(first.pushNode("Root", "Branch", "contains"));

    // Spans (020-06): two measured with the Tracer's meter (ATUGCC_SPAN_METER), one from an
    // outside "perf" measurement. Labels match SCOPED_SPAN_LABELS / PERF_SPAN in the script.
    std::size_t spans = 0;
    {
        auto span = first.timeScope("probe scope");
        ++spans;
    }
    {
        viz::ScopedSpan span(first, "구간 \"quoted\"");
        ++spans;
    }
    if (first.recordSpan("external", std::chrono::microseconds(250), std::source_location::current(), "perf").has_value()) {
        ++spans;
    }

    constexpr int kPerThread = 10;
    std::vector<std::thread> workers;
    for (int t = 0; t < 2; ++t) {
        workers.emplace_back([&second, t] {
            for (int i = 0; i < kPerThread; ++i) {
                (void)second.recordMessage(std::format("Worker{}", t), "Hub", std::format("tick {}", i));
            }
        });
    }
    for (auto& worker : workers) {
        worker.join();
    }
    recorded += second.snapshotMessages().size();

    const auto summary = std::format(R"({{"events":{},"spans":{},"tracers":{{{},{}}}}})",
        recorded, spans, partCounts(first), partCounts(second));
    std::puts(summary.c_str());
    return 0;
}
