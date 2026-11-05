# 레슨: lock-free 링 버퍼 — SPSC와 mutex 큐 재기 (`lock_free_buffer`)

라이브러리의 `Logger`(010-09)는 로그를 부르는 스레드마다 링 버퍼 하나를 두고, 소비자 스레드 하나가 그것들을 비웁니다. 버퍼마다 쓰는 스레드도 하나, 읽는 스레드도 하나(SPSC)라서 잠금 없이 `std::atomic` 인덱스 두 개로 충분합니다. 이 레슨은 그 구조를 50줄 남짓의 `SpscRing<T, N>`으로 직접 만들고, `std::mutex`로 지킨 큐와 **정해진 시간(경우마다 300 ms)** 동안 처리량을 잽니다. 다섯 경우: mutex 큐 1:1, SPSC 1:1, 인덱스 둘이 한 캐시 줄에 있는 SPSC 1:1(false sharing), 생산자 4개 → mutex 큐 하나, 생산자마다 SPSC 하나 + 소비자 하나(`Logger`와 같은 구조). 각 경우는 순번이 생산자마다 늘기만 하는지와 잃은 항목이 없는지(`produced == consumed`)를 확인합니다. 실제 구현은 `uses` 탭의 [`thread_log_buffer.hpp`](/include/atugcc/core/detail/thread_log_buffer.hpp)와 [`ring_buffer.hpp`](/include/atugcc/core/ring_buffer.hpp)에서 읽습니다. 해설: [lock_free_logging.md](/docs/cpp_evolution/lock_free_logging.md).

## mutex 큐와 SPSC 링 버퍼
| | `std::mutex` 큐 | SPSC 링 버퍼 (`std::atomic`) |
|---|---|---|
| 동기화 | 넣고 뺄 때마다 잠금. 다른 쪽은 기다림 | 생산자는 `tail`만, 소비자는 `head`만 씀. 기다리지 않음 |
| 순서 보장 | 잠금이 앞뒤를 정함 | 슬롯을 쓴 뒤 `tail`을 `release`로 저장, 소비자가 `acquire`로 읽으면 슬롯 내용까지 보임 |
| 생산자 여럿 | 그대로 됨(잠금이 줄 세움) | 안 됨. 생산자마다 링 하나를 두고 소비자가 돌아가며 읽음 |
| 비용 | 잠금 경쟁, 잠자고 깨기 | 캐시 줄 주고받기. 인덱스가 한 줄에 있으면 false sharing |

## 실행
- 웹 플레이그라운드: 레슨 트리에서 선택 후 Run. `long` 레슨이라 최적화 빌드(`linux-x64-playground-release`)로 실행합니다. Debug(-O0)의 처리량은 비교를 왜곡합니다.
- 로컬: `cmake --build --preset <preset> --target lesson_lock_free_buffer` 후 `bin/lessons/lesson_lock_free_buffer`, 또는 `ctest --preset <preset> -R lesson.lock_free_buffer`
- 데이터 경쟁 검사: `py -3 .agent/scripts/build.py --preset linux-x64-tsan --test`(ThreadSanitizer, Linux)

## 볼 것
- **처리량 숫자는 기계, 부하, 빌드마다 다릅니다.** 보통 SPSC가 mutex 큐보다 빠르고, false sharing 행이 패딩한 SPSC보다 느립니다. 그렇지 않다면 왜인지 보세요(코어 수, 다른 프로그램, Debug 빌드). 특히 false sharing 행은 패딩한 SPSC와 비슷하거나 더 빠르게 나오기도 합니다(2026-11-04 Release 실행에서 그랬습니다). 이 단순한 링은 넣고 뺄 때마다 상대의 인덱스를 읽으므로, 패딩해도 그 줄은 어차피 코어 사이를 오갑니다. 연습 2처럼 상대 인덱스의 사본을 두어 읽기를 줄이면 패딩의 차이가 드러납니다. 코어가 5개보다 적으면 4·5행에 `(oversubscribed: N cores)`가 붙습니다. 스레드가 코어보다 많아 서로 양보(`yield()`)하며 돌기 때문입니다. 그래도 `verified`는 언제나 `ok`여야 합니다.
- **`release`/`acquire`**: 생산자는 슬롯을 먼저 쓰고 `indices_.tail.store(tail + 1, std::memory_order_release)`로 공개합니다. 소비자가 `indices_.tail.load(std::memory_order_acquire)`로 그 값을 보면, 그 저장 **이전**의 모든 쓰기(슬롯 내용)도 보입니다(happens-before). 거꾸로 소비자의 `head` `release`와 생산자의 `acquire`는 "그 슬롯은 다 읽었으니 다시 써도 된다"를 넘깁니다.
- **인덱스를 계속 늘리고 마스크로 자름**: `head`와 `tail`은 0으로 돌아가지 않고 늘기만 하며, 슬롯은 `index & (N - 1)`로 고릅니다(`N`은 2의 거듭제곱, 레슨 `concepts`의 `FixedRing`). 그래서 빔은 `head == tail`, 가득 참은 `tail - head == N`으로 구분됩니다. 인덱스를 `N`에서 0으로 되돌리면 두 상태가 같아 보여 슬롯 하나를 비워 둬야 합니다.
- **`alignas(64)`**: `head`와 `tail`이 한 캐시 줄(보통 64바이트)에 있으면, 한쪽이 쓸 때마다 다른 코어의 그 줄이 무효가 되어 서로 상관없는 두 변수가 줄을 주고받습니다(3행). 레슨의 `Indices<true>`는 인덱스마다 64바이트 줄 하나를 주고, `Indices<false>`는 둘을 64바이트로 정렬한 한 줄에 넣습니다. 둘 다 남는 바이트를 직접 채우는데, `alignas` 때문에 컴파일러가 패딩을 넣으면 MSVC가 C4324 경고(여기서는 오류)를 내기 때문입니다. 표준의 `std::hardware_destructive_interference_size`도 두 툴체인에서 64이지만, 대상 CPU 옵션에 따라 값이 바뀔 수 있어 ABI나 파일 형식에 넣지 않습니다. 라이브러리와 이 레슨은 상수 64를 씁니다.
- **생산자가 여럿이면 SPSC 하나를 함께 쓰면 안 됨**: 두 생산자가 같은 `tail`을 읽고 같은 슬롯에 쓰면 한쪽이 사라집니다. 예전 Logger가 정확히 그랬습니다([KI-025](/docs/known_issues.md): 모든 스레드가 단일 생산자 큐 하나에 넣음). 010-09는 5행처럼 스레드마다 버퍼를 두는 구조로 바꿨습니다.
- **라이브러리에서 같은 줄 찾기**: `thread_log_buffer.hpp`의 `BufferHeader`에 `writePos`·`readPos`가 있고, [`thread_log_buffer.cpp`](/src/core/thread_log_buffer.cpp)에서 생산자가 `readPos`를 `acquire`로 읽고 `writePos`를 `release`로 저장합니다. 이 레슨의 `tail`/`head`와 같은 짝입니다. 다만 라이브러리는 두 인덱스를 64바이트 `BufferHeader` 하나에 둡니다. 그 헤더가 메모리 매핑 파일의 형식이기도 하기 때문입니다(010-10).

## 연습
1. 사본을 만들어 `release`와 `acquire`를 모두 `std::memory_order_relaxed`로 바꾸고 `linux-x64-tsan` preset으로 실행해 보세요. ThreadSanitizer가 어느 변수(슬롯)에서 data race를 보고하나요? x86에서는 relaxed로도 결과가 맞아 보일 수 있는데, 그래도 틀린 이유는 무엇인가요?
2. 생산자가 매번 `head`를 `acquire`로 읽지 않도록, 마지막으로 본 `head` 값을 생산자 쪽에 사본으로 두고 가득 찬 것 같을 때만 다시 읽게 바꿔 보세요. 2행의 처리량이 어떻게 바뀌나요?
3. 버퍼 크기 `kCapacity`를 1024에서 8로 줄여 보세요. 가득 참이 잦아지면 각 행의 처리량은 어떻게 되나요? `verified`는 그대로 `ok`인가요?
