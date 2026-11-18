# Plan 023-02: Observer — 알림 재진입 안전성, 시나리오 테스트, patterns 레슨

Spec: [023_02_observer_lesson.md](/docs/specs/023_02_observer_lesson.md) (approved 2026-11-18). Branch `feature/023-02-observer-lesson`.

## Files
- [MODIFY] `tests/pattern/test_visualizer.cpp` — `ObserverTest` 두 개 (AC-2)
- [MODIFY] `include/atugcc/pattern/observer.hpp` — `notifyObservers()` 사본 순회, 주석 (AC-2, spec §2.1)
- [NEW] `tests/scenario/scenario_traced_observer.cpp`, [MODIFY] `tests/CMakeLists.txt` (AC-3)
- [NEW] `lessons/tracks/patterns/sensor_observers/` — `main.cpp`, `lesson.toml`, `README.md`, `README.en.md`, `exercises.toml` (AC-4, AC-5)
- [MODIFY] `lessons/curriculum.toml`, `lessons/tags.toml`, `lessons/intro.md`, `lessons/intro.en.md`, `docs/lesson_candidates.md`, `lessons/tracks/essentials/concepts/README.md`, `README.en.md` (spec §8)
- [MODIFY] `docs/known_issues.md` — Subject 일반화 KI (spec §6)

C++20/23 features: 바뀌는 것 없음(concept, `std::erase_if`, `weak_ptr`는 이미 있음). Evolution pages: none (spec Assumption 12).

## Design notes
- AC-2는 "고치기 전 헤더에서 실패"를 요구하므로 테스트(U1)를 헤더 수정(U2)보다 먼저 한다. unit order(헤더 → 테스트)와 다른 점은 이 때문이다.
- `SubscribeDuringNotifyStartsNextTime`이 수정 전 실패를 보이는 테스트다. 구독자 **둘**(A, B; libstdc++ capacity 2)에서 A의 콜백이 C를 `subscribe` → `push_back`이 재할당 → 바깥 범위 `for`가 해제된 버퍼에서 B의 `handle.lock()`을 읽는다(ASan heap-use-after-free). 구독자가 하나면 재할당 뒤 읽는 원소가 없어 ASan이 못 잡는다. 기대: 첫 알림에서 C는 받지 않고 두 번째 알림에서 받는다.
- `NestedSetDataIsSafe` (U1 리뷰 뒤 다시 씀): 구독 순서 B, A, C, D. A의 첫 알림이 B와 D를 만료시키고 한 번만 다시 `setData`한다. 사본 순회면 C는 안쪽 1번 + 바깥 차례 1번 = 2번, 인덱스 순회면 안쪽 `erase_if`가 A 앞의 B를 지워 C가 당겨지므로 바깥에서 건너뛰어 1번이다. 만료 구독자를 건너뛰는지는 `subscribe` 람다의 `lock()` 때문에 수신부 카운트로는 보이지 않아, Subject가 보낸 Tracer 메시지 수(B 1, C 2, D 0)로 본다. `erase_if`는 재할당하지 않아 수정 전 헤더에서도 ASan은 이 테스트를 잡지 못한다(수정 전 실패는 `SubscribeDuringNotifyStartsNextTime`이 보인다).

## Units
| Unit | File | Change (what, where, AC) | Check | Risky | Author | Reviewer | Tokens (in / out) | Status |
|---|---|---|---|---|---|---|---|---|
| U1 | `tests/pattern/test_visualizer.cpp` | `ObserverTest.SubscribeDuringNotifyStartsNextTime`, `ObserverTest.NestedSetDataIsSafe` (AC-2) | `grep -c` 두 이름 = 1씩; 수정 전 헤더로 `linux-x64-asan` heap-use-after-free (observer.hpp:117); 인덱스 순회 변이 헤더에서 두 테스트 실패 | no | agy flash; review fixes lead (small) | cpp-reviewer: 4 (Nested 테스트가 인덱스 순회에서도 통과, `b_count == 0`이 실패할 수 없음, `>= 1`이 약함, 사소한 것 1) → lead가 B,A,C,D 순서와 Tracer 메시지 수로 다시 씀; 재리뷰 none | 76.6k / 17.6k | done |
| U2 | `include/atugcc/pattern/observer.hpp` | `notifyObservers()` 사본 순회, 학습 포인트 [6], 스레드·재귀 주석 (AC-1, AC-2, §2.1) | `ObserverTest.*` 6개 통과: linux-x64-asan, windows-x64-debug, linux-x64-debug | yes | agy flash; review fixes lead (small) | codex luna (high): 1 (콜백이 Subject를 파괴하면 `*this`/`tracer_` 사용) → 전제 조건 주석 두 줄(lead); 재리뷰 none | 62.2k / 8.8k (review 74.9k / 3.1k, 147.3k / 3.4k) | done |
| U3 | `tests/scenario/scenario_traced_observer.cpp`, `tests/CMakeLists.txt` | 시나리오 `TracedObserver.SubscribeNotifyExpireDiagram` (AC-3) | `--label scenario` windows-x64-debug 4/4 | no | agy flash; lead (small): 지역 변수 이름, 중복 `find` 두 줄 | cpp-reviewer: none | 94.8k / 14.3k | done |
| U4 | `lessons/tracks/patterns/sensor_observers/*`, `lessons/curriculum.toml` | `lessons.py new patterns sensor_observers --after device_state_machine` (제목, 요약, 태그, `uses` 인자) | `lessons.py check` 0/0 | no | lead (scripted) | — | — | done |
| U5 | `lessons/tracks/patterns/sensor_observers/main.cpp` | 4단계 레슨 코드 (spec A5, A9, A13; AC-4) | `--label lesson` windows-x64-debug; Windows·Linux 출력 diff 같음 | no | agy flash; lead (small): `<cstddef>` | cpp-reviewer: none | 108.6k / 19.8k | done |
| U6 | `.../sensor_observers/lesson.toml`, `lessons/tags.toml` | 매니페스트, `[observer]` 태그 (A11) | `lessons.py check` 0/0 | no | lead (small) | cpp-reviewer (U7과 함께): `profile` 줄 없음 → 기본값이라 둠(testrecord) | — | done |
| U7 | `.../sensor_observers/README.md`, `README.en.md`, `exercises.toml` | README 두 언어, 과제 3개 (A4, A8, A10, A12; AC-5) | `exercises.py check` 풀이별 두 preset 통과, 우회 편집 실패, `verify` 두 preset | no | lead | cpp-reviewer: 5 (만료 설명, 우회 2, `concepts.md` 링크, `data1()` 문장) + A8 문단 → 모두 고침; 재리뷰 none | — | done |
| U8 | spec §8 나머지 문서, KI | intro 두 언어, `lesson_candidates.md`, concepts README 두 언어, KI-058 | `lint_docs.py` 0 errors | no | lead | cpp-reviewer: 1 (concepts 링크 위치) → 둠, testrecord에 차이로 | — | done |
