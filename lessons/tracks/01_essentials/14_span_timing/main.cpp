/**
 * @file main.cpp
 * @brief 레슨 span_timing — 코드 구간의 시간을 span 으로 재고 비교한다
 *
 * 같은 일을 두 방식으로 하는 구간 네 개를 kRunFor 동안 번갈아 재고, 끝에 formatTimings() 표를 출력한다.
 * 웹 플레이그라운드에서는 실행 중에 Timings 탭과 에디터 줄 끝(⏱)에 시간이 나온다 (spec 070-06).
 * span 사용법: include/atugcc/pattern/visualizer.hpp 머리 주석, spec 020-06.
 */
#include <chrono>
#include <cstddef>
#include <cstdint>
#include <iostream>
#include <map>
#include <random>
#include <unordered_map>
#include <vector>

#include "atugcc/pattern/visualizer.hpp"

namespace viz = atugcc::pattern::viz;
using namespace std::chrono_literals;

namespace {

constexpr auto kRunFor = 15s;                 // 측정 시간: 횟수가 아니라 시간으로 정한다 (Debug 에서도 같은 시간)
constexpr std::size_t kElements = 100'000;    // 벡터 원소 수, map 크기
constexpr std::size_t kLookups = 10'000;      // 한 구간의 find 횟수

std::uint64_t fillWithoutReserve() {
    std::vector<std::uint64_t> values;
    for (std::size_t i = 0; i < kElements; ++i) {
        values.push_back(i);                  // 용량이 모자랄 때마다 다시 할당하고 옮긴다
    }
    return values.back();
}

std::uint64_t fillWithReserve() {
    std::vector<std::uint64_t> values;
    values.reserve(kElements);                // 할당 한 번
    for (std::size_t i = 0; i < kElements; ++i) {
        values.push_back(i);
    }
    return values.back();
}

template <typename Map>
std::uint64_t lookUp(const Map& map, const std::vector<int>& keys) {
    std::uint64_t sum = 0;
    for (const int key : keys) {
        sum += static_cast<std::uint64_t>(map.find(key)->second);
    }
    return sum;
}

} // namespace

int main() {
    viz::Tracer tracer;

    std::map<int, int> ordered;
    std::unordered_map<int, int> hashed;
    for (int i = 0; i < static_cast<int>(kElements); ++i) {
        ordered.emplace(i, i);
        hashed.emplace(i, i);
    }
    std::mt19937 random(42);
    std::uniform_int_distribution<int> pick(0, static_cast<int>(kElements) - 1);
    std::vector<int> keys(kLookups);
    for (int& key : keys) {
        key = pick(random);
    }

    std::uint64_t checksum = 0;   // 결과를 쓰지 않으면 최적화 빌드가 계산을 지울 수 있다
    int rounds = 0;
    const auto start = std::chrono::steady_clock::now();
    auto report = start + 3s;
    while (std::chrono::steady_clock::now() - start < kRunFor) {
        {
            auto span = tracer.timeScope("push_back");
            checksum += fillWithoutReserve();
        }
        {
            auto span = tracer.timeScope("reserve + push_back");
            checksum += fillWithReserve();
        }
        {
            auto span = tracer.timeScope("std::map::find");
            checksum += lookUp(ordered, keys);
        }
        {
            auto span = tracer.timeScope("std::unordered_map::find");
            checksum += lookUp(hashed, keys);
        }
        ++rounds;
        if (std::chrono::steady_clock::now() >= report) {
            std::cout << "rounds: " << rounds << '\n';
            report += 3s;
        }
    }

    std::cout << rounds << " rounds, checksum " << checksum << "\n\n" << tracer.formatTimings();
    return 0;
}
