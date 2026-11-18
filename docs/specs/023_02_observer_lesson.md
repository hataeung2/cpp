---
id: 023-02
title: Observer — 알림 재진입 안전성, 시나리오 테스트, patterns 레슨
depends_on: []
unblocks: [021-01]
approved: 2026-11-18
---

# Spec 023-02: Observer — 알림 재진입 안전성, 시나리오 테스트, patterns 레슨

## 0. Assumptions (please review)
| # | Decision | Rejected alternative | Why |
|---|---|---|---|
| 1 | **전체 경로 작업**이다: 레슨, 시나리오 테스트 하나, `observer.hpp`의 결함 하나(Assumption 6)와 그 단위 테스트. spec 하나가 모두 정한다 ([090-13](/docs/specs/090_13_lesson_path.md) Assumption 2) | 레슨만 (레슨 경로) | 패턴 작업은 시나리오 테스트를 하나 이상 더한다(작업 공통 원칙, [test.md](/.agent/rules/test.md) §2). Observer에는 아직 시나리오가 없다 |
| 2 | **레슨 id `sensor_observers`**, patterns 트랙에서 `device_state_machine` 다음. 주제: 장비 센서 값이 바뀌면 여러 수신부(패널 화면, 알람 기록)에 알린다. `device_state_machine`과 같은 "장비" 도메인을 이어 간다 | `observer_basics` 같은 패턴 이름 | patterns 트랙의 제목이 "상황에 맞게 적용하고 바꾸기"다. 패턴 이름보다 상황이 id에 드러나는 편이 트랙과 맞다 |
| 3 | **레슨은 지금의 `Subject` API를 그대로 쓴다**(`setData(d1, d2)`, `data1()`, `data2()`). 레슨에서는 `data1` = 센서 이름, `data2` = 값 문자열로 읽는다. `Subject`를 일반화(상태 타입 템플릿, 구독 해제 토큰)하지 않고 KI로 남긴다(§6) | 이 작업에서 `Subject<T>`로 일반화 | 일반화는 API 재설계라 `ObserverTest`와 Tracer 연결까지 바꾼다. 그러면 레슨 하나짜리 작업이 헤더 재설계가 된다. 이름이 어색한 것은 레슨 README에 적는다 |
| 4 | **README 첫 절은 "예전 방식과 C++20"**(`lessons.py new`의 기본값)이다. 비교: GoF 방식(가상 함수 `IObserver`, `Subject`가 날 포인터 목록을 들고 소멸자에서 직접 `detach`) → concept `ObserverOf` + `std::weak_ptr` 구독(수신부가 사라지면 다음 알림에서 저절로 빠짐) | oop_basics처럼 "흔한 실수와 바른 방식" | patterns 트랙의 독자는 essentials를 마쳤다(`concepts`, `smart_pointers` 수준). 이 패턴에서 C++20이 바꾸는 것(concept, `erase_if`, `weak_ptr` 수명 분리)이 레슨의 요점이다 |
| 5 | **정의되지 않은 동작을 돌리지 않는다.** 예전 방식의 위험(`detach`를 잊은 수신부를 가리키는 날 포인터)은 README 글과 주석으로만 보인다. Step 1의 예전 방식 코드는 `detach`를 빠뜨리지 않은 안전한 판이다 | 댕글링을 실행해 보임 | smoke test와 sanitizer preset에서 통과해야 하고, UB의 결과는 보장되지 않는다(oop_basics Assumption 4와 같은 규칙) |
| 6 | **헤더 결함 수정: 알림 중의 구독 변경.** 지금 `notifyObservers()`는 `entries_`를 범위 `for`로 돌면서 `onNotify`를 부른다. 콜백 안에서 `subscribe`(→ `push_back`)하거나 중첩 `setData`가 `removeExpired`(→ `erase_if`)를 부르면 반복자가 무효가 되어 UB다. 고친 뒤: 알림은 시작할 때 `entries_`의 **사본**을 돈다. 알림 중에 더한 구독자는 **다음** 알림부터 받고, 알림 중에 만료된 구독자는 그 뒤 차례에서 `lock()` 실패로 건너뛴다 | (a) 인덱스로 돌고 시작 때의 크기까지만; (b) 알림 중 변경을 막는 플래그와 오류 반환 | (a) 중첩 `setData`의 `erase_if`가 앞쪽 원소를 지우면 인덱스가 밀린다. (b) 수신부 코드에 새 실패 경로가 생긴다. 사본은 읽기에 가장 단순하고 구독자 수가 작은 교육용 헤더에서 비용이 문제되지 않는다 |
| 7 | **중첩 `setData`(콜백 안에서 다시 `setData`)는 허용하되 막지 않는다.** 재귀 깊이는 수신부가 책임진다(헤더 주석에 한 줄). 사본 덕분에 메모리 안전성은 지켜진다 | 재귀를 감지해 무시 | 실제 이벤트 시스템도 대개 재귀를 막지 않는다. 막는 정책은 Subject 일반화(Assumption 3의 KI) 때 정한다 |
| 8 | **`std::weak_ptr<void>`는 그대로 둔다.** Core의 "Never `void*`"는 날 포인터를 가리킨다. `weak_ptr<void>`는 수명만 보는 손잡이(type erasure)이고, 구체 타입은 `subscribe`의 람다가 `weak_ptr<T>`로 들고 있다. 레슨 README가 이 점을 설명한다 | `weak_ptr<void>` 대신 `std::function<bool()> alive` | 지금 코드가 맞게 동작하고 `ObserverTest`가 덮는다. 바꾸면 이 작업의 범위가 커진다. 리뷰어가 같은 질문을 하지 않도록 여기에 기록한다 |
| 9 | **레슨 단계(초안, 레슨을 쓰며 lead가 다듬고 walkthrough에 남김)**: Step 1 예전 방식(가상 인터페이스, attach/detach) 출력 → Step 2 `subscribe`로 수신부 둘, `setData` 두 번, `collectDisplays()` → Step 3 한 수신부가 스코프를 벗어난 뒤 `setData`: 알림이 하나만 감 → Step 4 `formatTerminal()`과 Mermaid 시퀀스 다이어그램. 파일은 `main.cpp` 하나, 수신부 타입은 익명 namespace | 레슨용 유닛으로 수신부를 뽑음 | 수신부는 이 레슨만 쓴다. 한 파일 안에서 타입과 사용을 같이 읽는 편이 낫다 |
| 10 | **연습 과제 3개**: (1) 세 번째 수신부 타입을 만들어 구독(자동, `expect`로 새 줄); (2) 한 수신부의 `display()`를 지워 `ObserverOf` 위반 컴파일 오류 읽기(자동, `build = "fail"`, Clang·MSVC 오류 문구에 둘 다 나오는 `ObserverOf`); (3) Step 3의 수신부를 스코프 밖에서도 살려 두어 알림 수가 바뀌는 것 보기(자동, `expect`). 두 컴파일러에서 돌려 분류하고, 다르면 관찰 과제로 바꾼다 | 과제 없음 / 관찰 과제만 | [070-20](/docs/specs/070_20_remaining_exercises.md): 새 레슨은 과제 정의를 함께 낸다 |
| 11 | **태그 `observer`를 더한다**(ko "옵저버", aliases: `Observer pattern`, `publish-subscribe`, `pub/sub`, `구독`, `subscribe`). 레슨 태그: `observer`, `concepts`, `tracer` | 기존 태그만 | 기능 검색(070-10)이 한국어 낱말로도 찾게 한다 |
| 12 | **evolution 페이지를 새로 쓰지 않는다.** concept 설명은 [`concepts.md`](/docs/cpp_evolution/concepts.md)와 essentials `concepts` 레슨에 링크만 건다 | `observer.md` 페이지 | 이 패턴에서 새 표준 기능은 없다. 이미 있는 concept·`weak_ptr` 설명을 되풀이하게 된다 |
| 13 | **출력은 두 OS에서 같다**: 주소·시간을 찍지 않는다. `formatTerminal()`과 Mermaid 출력은 `device_state_machine`처럼 찍는다(시각 없이 순서만 나옴, 다르면 레슨 작성 때 그 출력은 빼고 walkthrough에 남김) | — | 과제의 `expect`가 출력을 쓴다 |

## 1. Objective
`atugcc::pattern::observer`는 020-01에서 concept, `weak_ptr`, Tracer 연결과 단위 테스트까지 갖췄지만 레슨과 시나리오 테스트가 없고, 알림 중에 구독 목록이 바뀌면 UB가 되는 결함이 있다. 이 작업은 결함을 고치고, Observer의 한 흐름(구독 → 알림 → 수신부 소멸 → 다시 알림 → 다이어그램)을 시나리오로 고정하고, patterns 트랙에 Observer 레슨을 더한다. B 단계 "레슨 줄"의 첫 작업으로, 이후 패턴 레슨(021-01 등)이 따를 모양을 정한다.

## 2. Requirement Details

### 2.1 Public API Surface
[`include/atugcc/pattern/observer.hpp`](/include/atugcc/pattern/observer.hpp): 공개 API(이름, 시그니처)는 바뀌지 않는다. 바뀌는 것은 `notifyObservers()`의 동작 계약뿐이다.
- 알림은 시작 시점의 구독자 목록 사본을 차례로 돈다.
- 알림 중에 `subscribe`된 구독자는 그 알림을 받지 않고 다음 알림부터 받는다.
- 알림 중에 만료된 구독자는 그 뒤 차례에서 받지 않는다.
- 콜백 안의 `setData`(중첩 알림)는 메모리 안전하다. 재귀 깊이는 호출자 책임이다(주석).
- 파일 머리 주석의 "학습 포인트"에 [6] 알림 중 변경(사본 순회)을 더한다.

### 2.2 Internal Implementation
- `notifyObservers()`: `removeExpired()` 뒤 `const auto snapshot = entries_;`를 돌며 지금처럼 `lock()` → `recordMessage` → `onNotify`.
- 레슨: `lessons/tracks/patterns/sensor_observers/` (`main.cpp`, `lesson.toml`, `README.md`, `README.en.md`, `exercises.toml`), `py -3 tools/lessons.py new patterns sensor_observers --after device_state_machine`으로 만든다. 매니페스트 `profile = "quick"`, `sources = ["main.cpp"]`, `uses = ["lib:atugcc/pattern/observer.hpp", "lib:atugcc/pattern/visualizer.hpp"]`.
- 시나리오: `tests/scenario/scenario_traced_observer.cpp` (`atugcc_scenarios` 목록에 더함), 단계는 §5 AC-3.
- 단위 테스트: [`tests/pattern/test_visualizer.cpp`](/tests/pattern/test_visualizer.cpp)의 `ObserverTest`에 둘 더함(§5 AC-2).

### 2.3 Platform Specifics
none. 과제 (2)의 컴파일 오류 문구만 Clang과 MSVC가 다르므로 두 컴파일러에서 확인한다(Assumption 10).

## 3. C++ Standard Evolution
| Approach | Standard | Description |
|----------|----------|-------------|
| Legacy | C++98/11 | 순수 가상 `IObserver`, `Subject`가 `std::vector<IObserver*>`를 들고 수신부가 소멸자에서 `detach` (잊으면 댕글링) |
| Modern | C++11/20 | `std::weak_ptr`로 수명을 분리(C++11), concept `ObserverOf`로 상속 없이 인터페이스 검사, `std::erase_if`로 만료 구독자 제거(C++20) |
| Latest | C++23 | 해당 없음 (`std::move_only_function`은 사본 순회에 복사가 필요해 쓰지 않는다) |

Reference: [`/docs/cpp_evolution/concepts.md`](/docs/cpp_evolution/concepts.md) (링크만, Assumption 12).

## 4. Edge Cases
- [x] Thread safety / memory ordering: `Subject`는 스레드 안전을 약속하지 않는다(지금과 같음, 헤더 주석에 한 줄 더함). `Tracer`는 자체 잠금이 있다. 레슨과 시나리오는 한 스레드에서만 쓴다.
- [x] Resource lifetime / RAII / dangling views: 핵심 경우다. 알림 중 구독 추가·만료·중첩 알림은 사본 순회로 안전(Assumption 6, 7). `data1()`/`data2()`가 돌려주는 참조는 다음 `setData`까지 유효하다는 점을 README에 적는다. 레슨은 댕글링을 실행하지 않는다(Assumption 5).
- [x] Platform differences (MSVC vs Clang): 컴파일 오류 과제 문구만(§2.3).
- [x] Template instantiation / concept constraints: `subscribe<T>`의 `ObserverOf` 위반이 과제 (2)다. `static_assert` 두 줄은 그대로 둔다.
- [x] ODR: 헤더의 함수는 클래스 안 정의와 함수 템플릿뿐이라 지금도 `inline`이다. 바뀌지 않는다.
- [x] Undefined behaviour: 고치는 결함 자체가 반복자 무효화 UB다. AC-2 테스트는 `linux-x64-asan`에서도 돌린다.

## 5. Acceptance Criteria
| ID | Criterion | Verified by |
|---|---|---|
| AC-1 | 기존 `ObserverTest` 두 개가 바뀌지 않고 통과한다 | `build.py --preset <p> --target atugcc_tests --gtest-filter "ObserverTest.*"`, 두 preset |
| AC-2 | 새 단위 테스트 `ObserverTest.SubscribeDuringNotifyStartsNextTime`(콜백이 새 구독자를 더함 → 그 알림에는 안 가고 다음 알림에 감)과 `ObserverTest.NestedSetDataIsSafe`(콜백이 한 번만 다시 `setData` → 최종 데이터가 안쪽 값, 크래시 없음)가 통과한다. 고치기 전 헤더에서는 `linux-x64-asan`에서 AC-2 중 하나 이상이 실패한다 | 위 명령 + `linux-x64-asan`; 수정 전 실패는 testrecord에 기록 |
| AC-3 | 시나리오 `scenario.TracedObserver.*`가 단계별로 통과한다: 구독자 둘 → `setData` → 메시지 2개(수신자 이름 순서대로) → 한 구독자 소멸 → `setData` → 새 메시지 1개, `collectDisplays()` 1개 → Mermaid 출력에 `sequenceDiagram`과 두 수신자 이름 | `build.py --preset <p> --label scenario`, 두 preset |
| AC-4 | 레슨 `sensor_observers`가 두 preset에서 경고 없이 빌드되고 smoke test `lesson.sensor_observers`, `lesson.sensor_observers.exercises_verify`가 통과한다. 출력이 Windows와 Linux에서 같다 | `build.py --preset <p> --label lesson`; 두 출력의 diff |
| AC-5 | `exercises.toml`의 자동 과제마다 풀이를 넣은 사본이 통과하고, 원본은 어느 자동 과제도 통과하지 않는다 | `py -3 tools/exercises.py check sensor_observers --preset <p>`, 두 preset(풀이 사본은 practice/에서, 기록은 testrecord) |
| AC-6 | `py -3 tools/lessons.py check`와 docs gate `py -3 .agent/scripts/lint_docs.py`가 exit 0 | 명령 |
| AC-7 | 전체 suite가 `windows-x64-debug`, `linux-x64-debug`에서 통과한다. CI(main)가 통과한다 | `build.py --preset <p> --test --report`; `gh run list` |

## 6. Out of Scope
- `Subject` 일반화(상태 타입 템플릿, 구독 해제 토큰, 재귀 정책) — 작업 끝에 새 KI로 등록(Assumption 3, 7). 사용자 결정 2026-11-18: 엔진 작업(Phase 6)에서 이벤트 시스템이 필요해질 때 레슨 하나를 더해 다룬다
- 스레드 안전한 Subject — 같은 KI에 적음
- `main.cpp`의 죽은 호출 `observer::observerSample()` — 070-04 (KI-023)
- patterns 트랙 순서와 여러 패턴을 엮는 도메인 시나리오 — 070-04
- web 테스트의 CI 잡 — KI-057 (이 작업은 `web/`을 바꾸지 않는다)

## 7. Dependencies & Backends
none.

## 8. Documentation Updates
| Document | Section | Change |
|---|---|---|
| [`observer.hpp`](/include/atugcc/pattern/observer.hpp) | 머리 주석 "학습 포인트", `notifyObservers` 주석 | [6] 알림 중 변경(사본 순회), 스레드 안전을 약속하지 않음, 재귀는 호출자 책임 |
| 레슨 `sensor_observers` | `README.md`, `README.en.md` 전체 | 새로 씀(예전 방식과 C++20, 실행, 볼 것, 연습) |
| [`lessons/curriculum.toml`](/lessons/curriculum.toml) | patterns | `device_state_machine` 다음에 `sensor_observers` |
| [`lessons/tags.toml`](/lessons/tags.toml) | — | `[observer]` (Assumption 11) |
| [`lessons/intro.md`](/lessons/intro.md), [`intro.en.md`](/lessons/intro.en.md) | 트랙 목록의 patterns 줄 | 예시에 Observer 레슨 링크 |
| [`docs/lesson_candidates.md`](/docs/lesson_candidates.md) | E1 `concepts` 행 "기존 자료" | `observer.hpp`의 concept 주석 → 레슨 `patterns/sensor_observers`도 |
| essentials `concepts` 레슨 README(두 언어) | 연습 또는 끝 | `sensor_observers`로 가는 링크 한 줄 (concept을 실제 패턴에 쓰는 예) |
| [`docs/agent_todo.md`](/docs/agent_todo.md) | 023-02 줄, Phase 2.3 개수 | 상태와 링크 |
| [`docs/known_issues.md`](/docs/known_issues.md) | — | Subject 일반화 KI(§6) |

## 9. Technical Constraints
- Compiler: MSVC (VS 2026) / Clang 20 with libstdc++ 14 (Linux)
- CMake: 4.0+ (C++20 modules always on)
- C++ Standard: C++23 (C++20 minimum)

## 10. Context & References
- [observer.hpp](/include/atugcc/pattern/observer.hpp), [visualizer.hpp](/include/atugcc/pattern/visualizer.hpp)
- [ObserverTest](/tests/pattern/test_visualizer.cpp), 시나리오 선례 [scenario_traced_state_machine.cpp](/tests/scenario/scenario_traced_state_machine.cpp), [scenario.hpp](/tests/scenario/scenario.hpp)
- 레슨 선례 [device_state_machine](/lessons/tracks/patterns/device_state_machine/README.md), 작성 안내 [lessons/README.md](/lessons/README.md)
- 규칙: [090-13](/docs/specs/090_13_lesson_path.md) Assumption 2, 12; [070-20](/docs/specs/070_20_remaining_exercises.md)

## 11. Implementation Plan
- [ ] Step 1: AC-2 테스트를 먼저 쓰고 수정 전 헤더에서 `linux-x64-asan` 실패를 기록
- [ ] Step 2: `notifyObservers()` 사본 순회 + 주석
- [ ] Step 3: 시나리오 `scenario_traced_observer.cpp`
- [ ] Step 4: 레슨 뼈대(`lessons.py new`), `main.cpp`, README 두 언어, `exercises.toml`, 태그
- [ ] Step 5: 문서 갱신(§8), Subject 일반화 KI
- [ ] Step 6: 검증(§12), 리뷰(`cpp-reviewer`)

## 12. Verification Plan
- [ ] Build, zero warnings, full suite: `py -3 .agent/scripts/build.py --preset windows-x64-debug --test --report`, 같은 명령 `linux-x64-debug`
- [ ] Sanitizer: `py -3 .agent/scripts/build.py --preset linux-x64-asan --target atugcc_tests --gtest-filter "ObserverTest.*"`
- [ ] Scenarios: `py -3 .agent/scripts/build.py --preset <p> --label scenario`
- [ ] Lesson: `--label lesson`, `py -3 tools/exercises.py check sensor_observers --preset <p>`, `py -3 tools/lessons.py check`
- [ ] Every AC row has its evidence in `testrecord.md` ([test.md](/.agent/rules/test.md) §6)

## History / Amendments
- 2026-11-18: 초안, 사용자 승인 (A3 일반화는 엔진 작업 때 레슨과 함께 하는 KI)
