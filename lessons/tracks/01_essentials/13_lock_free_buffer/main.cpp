/**
 * @file main.cpp
 * @brief 레슨 lock_free_buffer — lock-free 링 버퍼: SPSC와 mutex 큐 재기
 * @brief Lesson lock_free_buffer — lock-free ring buffer: measuring SPSC against a mutex queue
 *
 * release/acquire로 동기화하는 단일 생산자 단일 소비자(SPSC) 링 버퍼를 구현하고 처리량을 측정한다
 * Implement and benchmark a single-producer single-consumer (SPSC) ring buffer synchronized with release/acquire
 * 뮤텍스 큐, 캐시 라인 패딩(false sharing 방지), 다중 생산자 환경에서의 스레드별 버퍼 구조를 비교한다
 * Compare a mutex queue, cache-line padding (false sharing prevention), and per-thread buffer architectures
 */
#include <array>
#include <atomic>
#include <bit>
#include <chrono>
#include <cstddef>
#include <cstdint>
#include <format>
#include <iostream>
#include <memory>
#include <mutex>
#include <stop_token>
#include <string>
#include <string_view>
#include <thread>
#include <type_traits>
#include <vector>

namespace {

// 전송할 항목 구조체: 생산자 식별자와 단조 증가 순번
// Transferred item struct: producer identifier and monotonically increasing sequence
struct Item {
    std::uint32_t producer;
    std::uint64_t seq;
};

// 현대 CPU의 전형적인 L1 캐시 라인 크기 (바이트)
// Typical L1 cache line size on modern CPUs (in bytes)
constexpr std::size_t kCacheLine = 64;

// 각 경우를 실행할 측정 시간
// Run time duration for each test case
constexpr auto kRunTime = std::chrono::milliseconds{300};

// 링 버퍼의 슬롯 수 (2의 거듭제곱)
// Number of slots in the ring buffer (power of two)
constexpr std::size_t kCapacity = 1024;

// 다중 생산자 측정 시 사용할 생산자 스레드 수
// Number of producer threads for multi-producer benchmarks
constexpr int kProducers = 4;

using AtomicIndex = std::atomic<std::size_t>;

// 링 버퍼의 두 인덱스 배치. Padded: head 와 tail 이 캐시 줄 하나씩을 혼자 차지한다
// Layout of the ring's two indices. Padded: head and tail each own a whole cache line
// 남는 바이트는 filler 로 직접 채운다: alignas 때문에 컴파일러가 패딩을 넣으면 MSVC /W4 가 C4324 경고를 낸다
// The spare bytes are filled explicitly: padding inserted by the compiler for alignas raises MSVC /W4 warning C4324
template <bool Padded>
struct Indices {
    alignas(kCacheLine) AtomicIndex head{0};
    std::array<std::byte, kCacheLine - sizeof(AtomicIndex)> headFiller{};
    alignas(kCacheLine) AtomicIndex tail{0};
    std::array<std::byte, kCacheLine - sizeof(AtomicIndex)> tailFiller{};
};

// 패딩 없음: 두 인덱스가 반드시 같은 캐시 줄 하나에 들어간다(구조체 전체가 그 한 줄)
// Not padded: both indices are guaranteed to share one cache line (the whole struct is that line)
template <>
struct alignas(kCacheLine) Indices<false> {
    AtomicIndex head{0};
    AtomicIndex tail{0};
    std::array<std::byte, kCacheLine - 2 * sizeof(AtomicIndex)> filler{};
};

static_assert(sizeof(Indices<true>) == 2 * kCacheLine);
static_assert(sizeof(Indices<false>) == kCacheLine);

// release/acquire 동기화를 사용하는 단일 생산자 단일 소비자(SPSC) 링 버퍼
// Single-producer single-consumer (SPSC) ring buffer using release/acquire synchronization
template <typename T, std::size_t N, bool Padded = true>
    requires (std::has_single_bit(N) && std::is_trivially_copyable_v<T>)
class SpscRing {
public:
    static_assert(std::atomic<std::size_t>::is_always_lock_free);

    // 생산자 전용: 버퍼가 가득 차지 않았으면 항목을 슬롯에 쓰고 tail을 전진시킨다
    // Producer only: writes an item into a slot and advances tail if the buffer is not full
    [[nodiscard]] bool tryPush(const T& item) {
        // 생산자 스레드만 tail을 수정하므로 relaxed 로드로 자신의 최신 쓰기 위치를 읽는다
        // Producer is the sole writer of tail, so a relaxed load reads its latest write position
        const std::size_t tail = indices_.tail.load(std::memory_order_relaxed);

        // 소비자의 release 저장과 동기화하여 소비자가 슬롯 읽기를 마친 최신 head 위치를 관측한다
        // Acquire load pairs with consumer's release store to observe that slot reads have finished
        const std::size_t head = indices_.head.load(std::memory_order_acquire);

        // tail과 head의 차이는 현재 버퍼에 들어 있는 항목 수이며, N과 같으면 모든 슬롯이 가득 찬 상태다
        // The difference (tail - head) represents current item count; when it equals N, the buffer is full
        if (tail - head == N) {
            return false;
        }

        // N이 2의 거듭제곱이므로 (N - 1) 비트마스크로 유효 슬롯 인덱스를 빠르게 계산한다
        // Because N is a power of two, bitwise AND with (N - 1) maps the monotonically increasing index to a slot
        slots_[tail & (N - 1)] = item;

        // 슬롯 데이터 쓰기를 발행하며, 소비자의 acquire 로드가 이 최신 슬롯 내용을 관측하도록 동기화한다
        // Release store publishes slot data writes, pairing with consumer's acquire load to make contents visible
        indices_.tail.store(tail + 1, std::memory_order_release);
        return true;
    }

    // 소비자 전용: 버퍼가 비어 있지 않으면 슬롯에서 항목을 읽고 head를 전진시킨다
    // Consumer only: reads an item from a slot and advances head if the buffer is not empty
    [[nodiscard]] bool tryPop(T& item) {
        // 소비자 스레드만 head를 수정하므로 relaxed 로드로 자신의 최신 읽기 위치를 읽는다
        // Consumer is the sole writer of head, so a relaxed load reads its latest read position
        const std::size_t head = indices_.head.load(std::memory_order_relaxed);

        // 생산자의 release 저장과 동기화하여 생산자가 작성한 슬롯 데이터 내용을 안전하게 관측한다
        // Acquire load pairs with producer's release store to safely observe written slot contents
        const std::size_t tail = indices_.tail.load(std::memory_order_acquire);

        // tail == head이면 버퍼에 꺼낼 항목이 없는 비어 있는 상태다
        // When tail == head, there are no items to consume and the buffer is empty
        if (tail == head) {
            return false;
        }

        // 2의 거듭제곱 크기이므로 비트 AND 마스크로 슬롯 위치를 계산하여 읽는다
        // Calculate the slot index via bitwise AND and read the item
        item = slots_[head & (N - 1)];

        // 슬롯 데이터 읽기 완료를 발행하며, 생산자의 acquire 로드가 슬롯 재사용 공간을 관측하도록 동기화한다
        // Release store publishes that the slot has been read, pairing with producer's acquire load to free the slot
        indices_.head.store(head + 1, std::memory_order_release);
        return true;
    }

private:
    // Padded 가 참이면 head 와 tail 이 각자 캐시 줄 하나씩을 차지해 false sharing 을 막고,
    // When Padded is true, head and tail each own a cache line, which prevents false sharing;
    // 거짓이면 한 캐시 줄을 함께 써서 한쪽이 쓸 때마다 다른 코어의 그 줄이 무효가 된다(3번 경우)
    // when false, they share one line, so every write by one side invalidates it on the other core (case 3)
    // 슬롯 배열을 앞에 두면 그 크기(64의 배수)가 인덱스를 캐시 줄 경계에 놓는다(객체는 64바이트 정렬)
    // With the slots first, their size (a multiple of 64) puts the indices on a cache-line boundary (the object is 64-byte aligned)
    std::array<T, N> slots_{};
    Indices<Padded> indices_;
};

// 뮤텍스로 동기화하는 고정 크기 링 버퍼 큐 (성능 비교 기준)
// Fixed-capacity ring buffer queue synchronized with a mutex (baseline comparison)
template <typename T, std::size_t N>
    requires (std::has_single_bit(N) && std::is_trivially_copyable_v<T>)
class MutexQueue {
public:
    // 뮤텍스 잠금 하에 버퍼가 차 있지 않으면 항목을 밀어 넣는다
    // Pushes an item into the queue under mutex protection if not full
    [[nodiscard]] bool tryPush(const T& item) {
        std::lock_guard<std::mutex> lock(mutex_);
        if (tail - head == N) {
            return false;
        }
        slots_[tail & (N - 1)] = item;
        ++tail;
        return true;
    }

    // 뮤텍스 잠금 하에 버퍼가 비어 있지 않으면 항목을 꺼낸다
    // Pops an item from the queue under mutex protection if not empty
    [[nodiscard]] bool tryPop(T& item) {
        std::lock_guard<std::mutex> lock(mutex_);
        if (tail == head) {
            return false;
        }
        item = slots_[head & (N - 1)];
        ++head;
        return true;
    }

private:
    std::mutex mutex_;
    std::size_t head{0};
    std::size_t tail{0};
    std::array<T, N> slots_{};
};

// 각 벤치마크 케이스의 측정 및 검증 결과
// Measurement and verification result of each benchmark case
struct CaseResult {
    std::string_view name;
    int producers;
    std::uint64_t items;
    double itemsPerSecond;
    bool verified;
};

// 주어진 푸시/팝 연산으로 생산자와 소비자를 실행하고 처리량 및 데이터 정합성을 검증한다
// Runs producers and a consumer with given push/pop operations, measuring throughput and verifying ordering
template <typename Push, typename Pop>
[[nodiscard]] CaseResult runCase(std::string_view name, int producers, Push push, Pop pop) {
    // 생산자가 완료 후 각자의 총 생산량을 기록하는 배열 (조인 후 메인 스레드가 합산)
    // Array where each producer records total items after completion (read by main after join)
    std::vector<std::uint64_t> produced(static_cast<std::size_t>(producers), 0);

    // 소비자가 각 생산자별로 기대하는 다음 순번
    // Next expected sequence number per producer tracked by consumer
    std::vector<std::uint64_t> nextSeq(static_cast<std::size_t>(producers), 0);
    std::uint64_t consumed = 0;
    bool ordered = true;

    // 소비자 스레드를 먼저 시작하여 생산자가 밀어 넣을 데이터를 즉시 처리할 수 있게 한다
    // Start consumer thread first so it is ready to process items pushed by producers
    std::jthread consumer([&pop, &nextSeq, &consumed, &ordered](std::stop_token st) {
        // 꺼낸 항목 하나를 확인한다: 생산자마다 순번이 하나씩만 늘어야 한다
        // Checks one item taken out: each producer's sequence must grow by exactly one
        const auto check = [&nextSeq, &consumed, &ordered](const Item& item) {
            if (item.producer >= nextSeq.size() || item.seq != nextSeq[item.producer]) {
                ordered = false;
            } else {
                ++nextSeq[item.producer];
            }
            ++consumed;
        };
        Item item{};
        while (true) {
            if (pop(item)) {
                check(item);
            } else if (st.stop_requested()) {
                // 정지 요청 후 버퍼에 남은 잔여 항목을 모두 비운다
                // Drain any remaining items after stop request until pop fails
                while (pop(item)) {
                    check(item);
                }
                break;
            } else {
                std::this_thread::yield();
            }
        }
    });

    // 생산자 스레드들을 생성하고 시작한다
    // Create and launch producer threads
    std::vector<std::jthread> producerThreads;
    producerThreads.reserve(static_cast<std::size_t>(producers));
    for (int i = 0; i < producers; ++i) {
        producerThreads.emplace_back([i, &push, &produced](std::stop_token st) {
            std::uint64_t seq = 0;
            while (!st.stop_requested()) {
                if (push(i, Item{static_cast<std::uint32_t>(i), seq})) {
                    ++seq;
                } else {
                    std::this_thread::yield();
                }
            }
            produced[static_cast<std::size_t>(i)] = seq;
        });
    }

    const auto t0 = std::chrono::steady_clock::now();
    std::this_thread::sleep_for(kRunTime);

    // 생산자를 먼저 정지하고 합류시켜 소비자가 먼저 종료되어 생산자가 블록 대기하는 데드락을 방지한다
    // Stop producers first to prevent deadlocks where a blocked producer waits on an already stopped consumer
    for (auto& t : producerThreads) {
        t.request_stop();
    }
    for (auto& t : producerThreads) {
        t.join();
    }

    // 모든 생산자가 종료된 후 소비자에 정지를 요청하고 잔여 항목 처리를 기다린다
    // Request stop on the consumer and wait for it to drain all remaining items after producers exit
    consumer.request_stop();
    consumer.join();

    const auto elapsed = std::chrono::steady_clock::now() - t0;

    std::uint64_t totalProduced = 0;
    for (const std::uint64_t count : produced) {
        totalProduced += count;
    }

    const bool verified = ordered && (consumed == totalProduced);
    const double elapsedSec = std::chrono::duration<double>(elapsed).count();
    const double itemsPerSecond = elapsedSec > 0.0 ? static_cast<double>(consumed) / elapsedSec : 0.0;

    return CaseResult{
        .name = name,
        .producers = producers,
        .items = consumed,
        .itemsPerSecond = itemsPerSecond,
        .verified = verified,
    };
}

} // namespace

int main() {
    std::vector<CaseResult> results;
    results.reserve(5);

    // 1. 단일 생산자 - 단일 소비자 뮤텍스 큐
    // 1. Single-producer single-consumer mutex queue
    auto mutexQueue1 = std::make_unique<MutexQueue<Item, kCapacity>>();
    results.push_back(runCase(
        "mutex queue 1:1",
        1,
        [&mutexQueue1](int, const Item& item) { return mutexQueue1->tryPush(item); },
        [&mutexQueue1](Item& item) { return mutexQueue1->tryPop(item); }));

    // 2. 단일 생산자 - 단일 소비자 SPSC 링 버퍼 (캐시 라인 패딩 적용)
    // 2. Single-producer single-consumer SPSC ring buffer (cache-line padded)
    auto spscPadded = std::make_unique<SpscRing<Item, kCapacity, true>>();
    results.push_back(runCase(
        "SPSC 1:1",
        1,
        [&spscPadded](int, const Item& item) { return spscPadded->tryPush(item); },
        [&spscPadded](Item& item) { return spscPadded->tryPop(item); }));

    // 3. false sharing 이 발생하는 SPSC 링 버퍼 (head와 tail이 같은 캐시 라인)
    // 3. SPSC ring buffer with false sharing (head and tail share a cache line)
    auto spscUnpadded = std::make_unique<SpscRing<Item, kCapacity, false>>();
    results.push_back(runCase(
        "SPSC 1:1, false sharing",
        1,
        [&spscUnpadded](int, const Item& item) { return spscUnpadded->tryPush(item); },
        [&spscUnpadded](Item& item) { return spscUnpadded->tryPop(item); }));

    // 4. 4개 생산자 스레드가 단일 뮤텍스 큐에 경합
    // 4. Four producer threads contending on a single mutex queue
    auto mutexQueue4 = std::make_unique<MutexQueue<Item, kCapacity>>();
    results.push_back(runCase(
        "mutex queue 4:1",
        kProducers,
        [&mutexQueue4](int, const Item& item) { return mutexQueue4->tryPush(item); },
        [&mutexQueue4](Item& item) { return mutexQueue4->tryPop(item); }));

    // 5. 생산자마다 전용 SPSC 링 버퍼를 두고 소비자가 라운드로빈으로 폴링 (010-09 Logger 구조)
    // 5. Dedicated SPSC ring buffer per producer with consumer polling round-robin (010-09 Logger design)
    std::array<std::unique_ptr<SpscRing<Item, kCapacity, true>>, static_cast<std::size_t>(kProducers)> perThreadRings;
    for (int i = 0; i < kProducers; ++i) {
        perThreadRings[static_cast<std::size_t>(i)] = std::make_unique<SpscRing<Item, kCapacity, true>>();
    }
    results.push_back(runCase(
        "SPSC per producer 4:1",
        kProducers,
        [&perThreadRings](int producer, const Item& item) {
            return perThreadRings[static_cast<std::size_t>(producer)]->tryPush(item);
        },
        [&perThreadRings, rrIndex = std::size_t{0}](Item& item) mutable {
            for (std::size_t offset = 0; offset < static_cast<std::size_t>(kProducers); ++offset) {
                const std::size_t idx = (rrIndex + offset) % static_cast<std::size_t>(kProducers);
                if (perThreadRings[idx]->tryPop(item)) {
                    rrIndex = (idx + 1) % static_cast<std::size_t>(kProducers);
                    return true;
                }
            }
            return false;
        }));

    std::cout << "== lock-free buffer: 5 cases, 300 ms each ==\n";
    std::cout << std::format("{:<32} {:>9} {:>12} {:>14} {:>9}\n",
                             "case", "producers", "items", "items/s", "verified");

    const unsigned int cores = std::thread::hardware_concurrency();
    bool allVerified = true;

    for (const auto& res : results) {
        if (!res.verified) {
            allVerified = false;
        }

        std::string row = std::format("{:<32} {:>9} {:>12} {:>14} {:>9}",
                                      res.name,
                                      res.producers,
                                      res.items,
                                      static_cast<std::uint64_t>(res.itemsPerSecond),
                                      res.verified ? "ok" : "FAILED");
        if (res.producers == kProducers && cores > 0 && cores < 5) {
            row += std::format(" (oversubscribed: {} cores)", cores);
        }
        std::cout << row << '\n';
    }

    std::cout << std::format("all cases verified: {}\n", allVerified);
    return allVerified ? 0 : 1;
}
