---
id: 070-11
title: essentials 2차 레슨 — 문법 (const의 위치, concepts, ranges, variant)
depends_on: [070-03]
unblocks: []
approved: 2026-11-04
---

# Spec 070-11: essentials 2차 레슨 — 문법 (const의 위치, concepts, ranges, variant)

## 0. Assumptions (please review)
| # | Decision | Rejected alternative | Why |
|---|---|---|---|
| 1 | **범위**: 070-03이 비워 둔 문법 자리 4개에 레슨 4개를 만든다: `03_const_correctness`(E14), `06_concepts`(E1), `07_ranges_views`(E5), `08_variant_visit`(E6). 기존 레슨, 폴더 번호, `lessons.py`는 바꾸지 않는다 | 070-12와 한 작업으로 | 070-03 Assumption 1의 분할 그대로다. 문법 레슨 넷은 라이브러리 기능이 거의 필요 없어 한 리뷰 단위로 묶기 좋다 |
| 2 | **레슨 id**: `const_correctness`, `concepts`, `ranges_views`, `variant_visit`. 폴더 이름은 `<번호>_<id>` | `const_position` 등 후보 표의 주제 이름 그대로 | 검색과 URL 해시에 남는 이름이라 C++에서 널리 쓰는 낱말을 고른다. 레슨 id와 태그 키는 겹쳐도 된다(070-10) |
| 3 | 070-11과 070-12 사이에는 **의존이 없다**. 둘 다 070-03 뒤에 어느 쪽이든 먼저 할 수 있다. 070-13(Linux 툴체인 Clang 20)은 사용자 결정으로 이 둘보다 먼저 끝났다(2026-11-03). 그래서 이 스펙은 Clang 20 + libstdc++ 14 기준이다. **진행 순서 자리는 사용자가 정한다**(070-03 Assumption 16) | 이 스펙이 순서를 정함 | 순서를 바꾸는 것은 사용자 결정이다(agent_todo.md 진행 순서 머리말) |
| 4 | 새 레슨은 070-03의 규칙을 그대로 따른다: `profile = "quick"`, 유닛 없음(`main.cpp` 하나), 출력 영어, 주석은 한국어 줄 + 영어 줄, `README.md`와 `README.en.md`, 두 preset에서 경고 없이 빌드 | 레슨마다 유닛 | 070-03 Assumption 9·12. 이 네 레슨의 코드를 다른 레슨이 가져다 쓸 일이 없다 |
| 5 | **Linux 툴체인(Clang 20 + libstdc++ 14.2)에 없는 C++23 기능만 README에 쓴다**(2026-11-04 WSL에서 `-std=gnu++23 -Wall -Wextra -Werror` 시험 컴파일, §10): range 포맷(`std::format("{}", view)`, libstdc++ 15), 파이프 형식 `ranges::to`(`v \| std::ranges::to<std::vector>()`), `std::forward_like`. 마지막 둘은 같은 원인이다: libstdc++ 14.2의 `forward_like`를 Clang 20이 "deduced return type cannot be used before it is defined"로 거부한다(직접 호출도 같음). 각 README에 비교와 MSVC 전용 연습 하나로 둔다. KI-033의 목록에 `std::forward_like`(직접 호출)를 더한다 | 레슨 코드에 `#ifdef`로 MSVC에서만 | 레슨은 두 preset에서 같은 소스로 빌드돼야 한다(lessons/README.md). KI-033은 070-13이 이미 "Linux 툴체인에 없는 C++23 기능"으로 넓혔다 |
| 6 | **두 툴체인에서 되는 C++23은 레슨 코드에 쓴다**(2026-11-04 Clang 20에서 빌드·실행 확인): `views::enumerate`, `views::zip`, `views::chunk`, `views::slide`, `views::split`, `ranges::fold_left`, **호출 형식 `std::ranges::to<std::vector>(view)`**, **deducing this**(`auto& get(this auto& self, std::size_t i)`, `forward_like` 없이 `auto&` 반환). GCC 13 초안에서 README에만 두었던 뒤의 둘은 이제 빌드되므로 코드로 옮긴다 | C++20 뷰만; deducing this를 계속 README에만 | 플레이그라운드에서 실제로 돌아가는 C++23을 보여 준다. MSVC(VS 2026)는 이 기능을 모두 지원한다 |
| 7 | **E14 `const_correctness`**: 다섯 단계. (1) `const` 멤버 함수와 `const&`로 받은 객체, (2) `mutable` 캐시, (3) `const`/비`const` 오버로드(`at()` 두 벌)와 같은 일을 하는 deducing this 함수 하나(`get`), (4) 값 반환 타입의 `const`: 복사·이동을 세는 `Tracked` 타입으로 `t = makeConst()`가 이동 대신 **복사 대입**, `v.push_back(makeConst())`가 복사가 되는 것과, `Tracked a = makeConst();`는 C++17 복사 생략으로 둘 다 아님을 표로 출력, (5) 포인터의 `const`(`const int*`, `int* const`). 컴파일 오류가 나는 줄(비`const` 함수 호출, `const int` 반환)은 주석 처리한 채 두고 연습으로 푼다 | 스칼라 `const int f()`를 코드에 | Clang 20 `-Wextra`가 스칼라 반환 `const`에 `-Wignored-qualifiers`("'const' type qualifier on return type has no effect")를 낸다(2026-11-04 시험 컴파일, 클래스 타입 `const Tracked`는 경고 없음. GCC 13도 같았다). 라이브러리 타깃이 경고를 오류로 만들므로(`CMakeLists.txt`의 `/WX`·`-Werror`) Linux에서 레슨이 빌드되지 않는다. 4단계 표는 Clang 20에서 기대와 같았다(복사 생성 1, 복사 대입 1, 이동 생성 1, 이동 대입 1, 초기화 0) |
| 8 | 기존 [`const_return_type_guide.md`](/docs/learning/const_return_type_guide.md)의 "`const std::string` 반환 → 깊은 복사" 설명은 **초기화에는 틀렸다**(C++17부터 prvalue로 초기화하면 복사도 이동도 없다). 대입과 컨테이너에 넣을 때만 복사가 된다고 고치고, 레슨 링크를 더한다 | 그대로 두고 레슨만 정확히 | 같은 저장소의 두 글이 다르게 가르치면 안 된다(070-03 Assumption 11과 같은 이유) |
| 9 | **E1 `concepts`**: 같은 함수 `twice`를 `std::enable_if_t` SFINAE와 `std::integral` concept로 쓰고, requires 식으로 만든 concept `Shape`, 축약 함수 템플릿(`const Shape auto&`), 포함 관계(subsumption)로 고르는 오버로드(`std::integral auto` vs `std::signed_integral auto`), `if constexpr (requires { … })`, 클래스 템플릿의 `requires` 절(`std::has_single_bit(N)`, `RingBuffer`와 같은 제약)을 보인다. `uses = ["lib:atugcc/pattern/observer.hpp", "lib:atugcc/core/ring_buffer.hpp"]`: 라이브러리의 `ObserverOf`와 `RingBuffer`의 `requires`를 읽게 한다 | 라이브러리 헤더를 include해서 쓰기 | 레슨은 개념을 작은 코드로 보이고, 실제 쓰임은 `uses` 탭에서 읽는다. `observer.hpp`를 쓰려면 Subject까지 끌어와 레슨이 커진다 |
| 10 | **E5 `ranges_views`**: raw loop와 `std::ranges` 알고리즘(프로젝션), 뷰 파이프라인(`filter | transform | take`), 지연 평가(변환 람다가 호출될 때마다 줄을 찍어 `take(2)`가 일찍 멈추는 것), C++23 뷰(Assumption 6), 수명(`std::ranges::dangling`, 임시 컨테이너가 `owning_view`로 옮겨지는 것)을 보인다. 출력은 요소마다 `std::format`으로 이어 붙인다(range 포맷 없음, Assumption 5) | 023-05 Iterator와 같이 | 023-05는 패턴 트랙이고 순서상 훨씬 뒤다. 후보 표의 "같이 다룰 수 있음"은 023-05가 이 레슨을 링크하는 것으로 충분하다 |
| 11 | **E6 `variant_visit`**: 같은 도형 두 개(Circle, Rect)를 가상 함수 계층(`std::unique_ptr<Shape>`)과 `std::variant<Circle, Rect>` + `std::visit`으로 쓰고, "새 연산 더하기"(variant 쪽은 타입을 고치지 않음)와 "새 타입 더하기"(variant 쪽은 모든 visitor가 컴파일 오류로 알려 줌, 연습)를 비교한다. `holds_alternative`, `get_if`, `index()`, 틀린 `std::get`의 `std::bad_variant_access`, `sizeof`를 출력한다. `overloaded`는 레슨 안에 세 줄로 정의하고, 같은 것이 있는 `lib:atugcc/pattern/state.hpp`를 `uses`로 보인다 | `state.hpp`를 include해서 `overloaded`를 씀 | `state.hpp`는 Tracer(`visualizer.hpp`)까지 끌어온다. 도우미 하나 때문에 레슨이 Tracer에 기대지 않게 한다 |
| 12 | 태그 4개를 더한다(§2.3): `const`, `concepts`, `ranges`, `variant`. `variant`는 [lesson_candidates.md](/docs/tasks/lesson_candidates.md)의 메모대로 `device_state_machine`에도 붙인다 | 기존 태그만 | 070-10 검색이 `std::visit`, `requires`, `views`로 새 레슨을 찾게 한다. 070-10이 `std::variant`, `std::visit`를 `state` 태그에서 뺀 것은 이 태그를 위해서였다 |
| 13 | 오래 남길 해설: **E1만 새 페이지** `docs/cpp_evolution/concepts.md`(영어, 기존 페이지와 같은 형식)를 쓴다(KI-001이 기다리는 페이지). E5, E6은 README의 비교 표로 충분하고, E14는 Assumption 8의 학습 문서가 맡는다 | 네 주제 모두 evolution 페이지 | KI-001의 빠진 페이지 목록에 있는 것은 `concepts.md`뿐이다. 페이지를 늘리면 README와 같은 내용을 두 곳에서 관리한다. 필요해지면 그때 쓴다 |

## 1. Objective
essentials 트랙의 문법 구간(070-03 §2.1의 `03_`, `06_`–`08_`)을 채운다. 이 네 레슨이 들어가면 트랙 앞부분이 "람다 → 포맷 → const → 오류 → 호출 위치 → concepts → ranges → variant"로 이어지고, 뒤의 core 기능·스레드 레슨과 patterns 트랙(특히 `device_state_machine`의 `std::variant` 상태 머신, `observer.hpp`의 concept)이 전제하는 문법을 먼저 배운다.

## 2. Requirement Details

### 2.1 트랙 안의 자리
| 폴더 | 레슨 id | 후보 | 태그 |
|---|---|---|---|
| `03_const_correctness` | `const_correctness` | E14 | `const`, `move` |
| `06_concepts` | `concepts` | E1 | `concepts` |
| `07_ranges_views` | `ranges_views` | E5 | `ranges`, `lambda` |
| `08_variant_visit` | `variant_visit` | E6 | `variant`, `state` |

다른 폴더는 옮기지 않는다. [lesson_candidates.md](/docs/tasks/lesson_candidates.md)의 essentials 표에서 네 행의 **폴더**를 채우고 **상태**를 `레슨 있음`으로 바꾼다.

### 2.2 새 레슨
모두 `profile = "quick"`, Windows(MSVC)와 Linux(Clang 20 + libstdc++ 14) preset에서 경고 없이 빌드, 출력 영어, 표준 라이브러리만 사용. README 두 판에 무엇을 보여 주는지, 예전 방식과 C++20/23 방식의 비교 표, 실행 방법, 볼 것(단계별), 연습 2–3개.

**`const_correctness`** (E14): `uses = []`, README가 [`const_return_type_guide.md`](/docs/learning/const_return_type_guide.md)를 링크
- 1단계: `Counter`의 `value() const`와 `increment()`. `const Counter&`로 받은 함수는 `value()`만 부른다. `increment()` 호출 줄은 주석 처리(연습 1).
- 2단계: `Document::wordCount() const`가 `mutable std::optional<std::size_t>`에 결과를 저장한다. 세 번 불러 계산이 한 번만 일어남을 계산 횟수로 출력. README: `mutable`은 "`const` 함수는 여러 스레드가 동시에 불러도 된다"는 기대를 깨므로 공유하면 잠금이나 atomic이 필요하다.
- 3단계: `Buffer::at(i)`와 `at(i) const`가 `int&`/`const int&`를 돌려준다. 비`const` 객체와 `const&`에서 각각 어느 쪽이 불리는지 출력. 이어서 C++23 deducing this 함수 하나 `auto& get(this auto& self, std::size_t i)`가 두 벌을 대신한다: `b.at(0) = 11`, `b.get(1) = 21`로 쓰고, `const&`에서의 반환 타입이 `const int&`임을 `static_assert`와 출력으로. README: rvalue까지 다루는 `this Self&& self` + `std::forward_like<Self>`는 Linux 툴체인에서 빌드되지 않는다(Assumption 5, MSVC에서만).
- 4단계: `Tracked`(복사 생성·복사 대입·이동 생성·이동 대입 횟수를 셈)로 `Tracked makeValue()`와 `const Tracked makeConst()`를 비교하는 표: 초기화, 대입, `push_back`. 기대: 초기화는 둘 다 0/0, 대입·`push_back`은 `makeValue`가 이동, `makeConst`가 복사.
- 5단계: `const int* p`, `int* const q`, `const int* const r`로 무엇을 바꿀 수 있는지(가리키는 값, 포인터 자신) 출력.
- 연습: (1) 1단계의 주석을 풀어 컴파일 오류 읽기, (2) `const int makeInt()`를 더해 Clang의 `-Wignored-qualifiers`(경고가 오류라 빌드 실패) 보기, MSVC는 어떤가, (3) `get`의 반환 타입을 `auto&`에서 `auto`로 바꾸면 `b.get(1) = 21`이 왜 컴파일 오류인가, 그리고 MSVC에서 `std::forward_like`로 rvalue 판 만들기.

**`concepts`** (E1): `uses = ["lib:atugcc/pattern/observer.hpp", "lib:atugcc/core/ring_buffer.hpp"]`
- 1단계: `twiceSfinae`(`std::enable_if_t<std::is_integral_v<T>, int> = 0`)와 `twice`(`template <std::integral T>`)가 같은 값을 낸다.
- 2단계: requires 식으로 `concept Shape`(`area()`가 `double`로, `name()`이 `std::string_view`로 바뀜)를 정의하고 `printShape(const Shape auto&)`로 `Circle`, `Square`를 출력. `Shape<int>`, `Shape<Circle>`를 `std::boolalpha`로 출력하고 `static_assert`로도 둔다.
- 3단계: `describe(auto)`, `describe(std::integral auto)`, `describe(std::signed_integral auto)` 세 오버로드에 `-3`, `3u`, `2.5`를 넣어 가장 좁은 제약이 고르는 것을 출력.
- 4단계: `if constexpr (requires { x.size(); })`로 `size()`가 있으면 크기를, 없으면 `no size()`를 출력(`std::vector`, `int`).
- 5단계: `template <std::size_t N> requires (std::has_single_bit(N)) struct FixedRing`의 마스크 계산을 출력하고, README가 같은 제약을 쓴 `RingBuffer`의 줄을 가리킨다.
- 연습: (1) `printShape(42)`와 `twiceSfinae("x")`의 컴파일 오류 메시지를 두 컴파일러에서 비교, (2) `observer.hpp`의 `ObserverOf`를 읽고 비슷한 concept `Printable` 쓰기, (3) `FixedRing<6>`의 오류 읽기.

**`ranges_views`** (E5): `uses = []`
- 1단계: `struct Item { std::string name; int price; int stock; }` 다섯 개를 raw loop로 가장 싼 재고 있는 물건을 찾고, 같은 일을 `std::ranges::min_element(… , {}, &Item::price)`(프로젝션)와 `std::ranges::sort(items, {}, &Item::price)`로.
- 2단계: `items | views::filter(inStock) | views::transform(&Item::name) | views::take(3)`.
- 3단계: 변환 람다가 `  transform(<name>)`을 찍는다. 파이프라인을 만든 직후 `pipeline built, nothing ran yet`을 찍고, `take(2)`로 돌면 변환이 필요한 만큼만 불린다.
- 4단계: C++23 뷰: `enumerate`(번호 붙이기), `zip(names, prices)`, `chunk(2)`, `slide(2)`, `"a,b,c"`의 `split(',')`, `fold_left`로 합계. 2단계 파이프라인의 결과를 호출 형식 `std::ranges::to<std::vector>(pipeline)`으로 벡터에 모아 크기를 출력(파이프 형식은 README, Assumption 5).
- 5단계: 임시 벡터에 `ranges::find`를 부르면 결과 타입이 `std::ranges::dangling`임을 `static_assert`와 출력(`std::same_as`)으로, 임시 벡터에 뷰를 붙이면 `owning_view`가 벡터를 가져가 안전함을 출력.
- README: 파이프 형식 `ranges::to`, range 포맷(Assumption 5).
- 연습: (1) 3단계에서 `take`를 지우면 몇 번 불리는지, (2) 5단계의 `dangling` 결과를 역참조해 컴파일 오류 보기, (3) MSVC에서 `| std::ranges::to<std::vector>()`와 `std::format("{}", view)`(Linux 툴체인에서는 빌드되지 않음).

**`variant_visit`** (E6): `uses = ["lib:atugcc/pattern/state.hpp"]`, README가 레슨 `device_state_machine`을 링크
- 1단계: 가상 함수 계층 `Shape`(가상 소멸자, `area()`, `name()`)과 `CircleV`, `RectV`를 `std::vector<std::unique_ptr<Shape>>`에 넣고 출력.
- 2단계: 기반 클래스 없는 `Circle`, `Rect`를 `std::vector<std::variant<Circle, Rect>>`에 넣고 `std::visit`(일반 람다로 `area`, `overloaded`로 `name`)으로 같은 출력.
- 3단계: 새 연산 `perimeter`를 variant 쪽에서 visitor 하나로 더한다(타입은 그대로). README의 표: 새 연산 / 새 타입을 더할 때 각 방식에서 고칠 곳.
- 4단계: `index()`, `holds_alternative<Circle>`, `get_if<Rect>`, 틀린 타입의 `std::get`이 던지는 `std::bad_variant_access`를 잡아 `bad_variant_access caught` 출력(메시지는 라이브러리마다 달라 찍지 않는다).
- 5단계: `sizeof(Circle)`, `sizeof(Rect)`, `sizeof(std::variant<Circle, Rect>)`, `sizeof(std::unique_ptr<Shape>)`과 "variant 요소는 힙 할당 없음, `unique_ptr` 요소마다 할당 1번"을 출력.
- 연습: (1) variant에 `Triangle`을 더하고 `overloaded` visitor가 컴파일 오류를 내는 것 보기(일반 람다 visitor는 왜 안 나는가), (2) `device_state_machine`의 상태 전이를 이 레슨의 방식으로 읽기, (3) 가상 함수 쪽에 `perimeter`를 더하려면 몇 곳을 고치는지 세기.

### 2.3 태그 어휘 (`lessons/tags.toml`에 더함)
| 키 | ko | en | aliases |
|---|---|---|---|
| `const` | const | const | `const member function`, `const 멤버 함수`, `const correctness`, `상수 정확성`, `-Wignored-qualifiers`, `deducing this`, `explicit object parameter` |
| `concepts` | 컨셉 | Concepts | `concept`, `requires`, `requires clause`, `std::enable_if`, `enable_if`, `SFINAE`, `템플릿 제약`, `constraint`, `제약`, `subsumption`, `std::integral` |
| `ranges` | 레인지 | Ranges | `std::ranges`, `std::views`, `views`, `range adaptor`, `뷰`, `파이프라인`, `projection`, `프로젝션`, `lazy evaluation`, `지연 평가`, `std::ranges::dangling`, `std::ranges::to` |
| `variant` | variant | Variant | `std::variant`, `std::visit`, `overloaded`, `std::holds_alternative`, `std::get_if`, `sum type`, `합 타입`, `virtual function`, `가상 함수` |

070-10의 중복 별칭 경고(한 이름은 한 태그에만)를 지킨다. `device_state_machine`의 `tags`에 `variant`를 더한다. `mutable`은 이미 `capture` 태그의 별칭이므로 `const` 태그에 넣지 않고, `const_correctness`의 `summary`에 낱말 `mutable`을 넣는다(검색은 제목·요약·태그 이름의 부분 문자열, `web/frontend/src/search.ts`. AC-8의 `mutable` 검색은 `lambda_capture`도 함께 찾는다).

### 2.4 Platform Specifics
- 표준 라이브러리만 쓴다. Linux 툴체인(Clang 20 + libstdc++ 14.2)에 없는 기능은 README에만(Assumption 5).
- `std::ranges::dangling`과 `owning_view`(P2415, libstdc++ 12+, MSVC 19.31+)는 두 툴체인에 있다(Clang 20에서 2026-11-04 확인). 구현 때 두 preset에서 다시 확인한다.
- 레슨 소스도 모듈 스캔을 거친다(070-13, 모든 타깃). `import`는 쓰지 않으므로 영향은 없다.
- `sizeof` 값은 두 플랫폼에서 다를 수 있다(`std::variant`의 판별자 크기). AC는 값이 아니라 관계(`sizeof(variant) >= max(sizeof 요소)`)를 본다.

## 3. C++ Standard Evolution
| Approach | Standard | Description |
|----------|----------|-------------|
| Legacy | C++11/17 | 값 반환에 `const`, `std::enable_if` SFINAE, 반복자 쌍과 raw loop, 가상 함수 계층과 `unique_ptr` |
| Modern | C++20 | concepts와 requires 식·절, 축약 함수 템플릿, `std::ranges` 알고리즘과 뷰, `owning_view`/`dangling` |
| Latest | C++23 | `views::enumerate`/`zip`/`chunk`/`slide`, `ranges::fold_left`, 호출 형식 `ranges::to`, deducing this, (README에서만) 파이프 형식 `ranges::to`, range 포맷, `std::forward_like` |

Reference: 새 `docs/cpp_evolution/concepts.md`(§8), [`const_return_type_guide.md`](/docs/learning/const_return_type_guide.md).

## 4. Edge Cases
- [x] Thread safety / memory ordering — 스레드를 만들지 않는다. `mutable` 캐시가 스레드 안전하지 않다는 것은 README의 설명으로만 다룬다
- [x] Resource lifetime / dangling views — `ranges_views` 5단계가 주제다. 레슨 코드는 임시 객체에 대한 반복자를 역참조하지 않는다(`dangling`은 타입만 검사). `views::split`의 부분 범위는 원래 `string_view`가 살아 있는 동안만 쓴다. `transform(&Item::name)`은 `items`를 참조하므로 파이프라인을 다 돈 뒤 `items`를 바꾼다
- [x] Platform differences — §2.4. 출력에 표준 라이브러리 메시지(`what()`)를 찍지 않는다
- [x] Template / concept — `concepts`의 `static_assert`는 두 컴파일러에서 같은 결과여야 한다. 포함 관계 오버로드는 표준 concept(`std::signed_integral`이 `std::integral`을 포함)만 쓴다: 사용자 concept끼리의 포함은 원자 제약이 같은 식이어야 해서 헷갈리는 오류가 난다(README에 한 줄)
- [x] ODR — 레슨마다 실행 파일 하나, 새 유닛·헤더 없음. 레슨 안의 `overloaded`는 `main.cpp` 안에서만 쓴다
- [x] Undefined behaviour — `Tracked`의 횟수는 전역 정적 카운터가 아니라 지역 구조체에 둔다(정적 초기화 순서 문제 없음). `std::get` 오류는 예외로 잡는다
- [x] 복사 생략 차이 — `Tracked a = makeConst();`의 0/0은 C++17이 보장한다. `return T{…};`(prvalue)로 쓰고, 이름 있는 지역 변수 반환(NRVO, 보장 아님)은 쓰지 않는다. Debug와 Release에서 같은 표가 나와야 한다(AC-3)
- [x] 클래스 타입 반환 `const`의 경고 — Clang 20 `-Wall -Wextra -Werror`는 경고하지 않았다(2026-11-04, GCC 13도 2026-11-03에 같음). MSVC에서 경고가 나면(경고는 오류다) 그 줄에만 `#pragma warning(suppress: …)`를 쓰지 않고 스펙을 다시 본다(STOP)
- [x] 지연 평가 출력의 순서 — 뷰 순회 중 출력과 결과 출력이 섞이지 않게 결과는 한 줄로 모아 순회가 끝난 뒤 찍는다
- [x] deducing this의 반환 타입 — `get`은 `auto&`로 돌려준다. `auto`로 쓰면 값 복사가 되어 쓰기가 사라지고(연습 3), `std::forward_like`는 Linux에서 빌드되지 않는다(Assumption 5). `get`은 lvalue `self`만 받는다(`this auto&`), rvalue `Buffer`에서는 부를 수 없다
- [x] 새 태그 이름 `const`, `variant` — `ko`가 영어 낱말이다. 070-10의 검색은 대소문자를 무시하므로 `Const`, `VARIANT`로도 찾는다

## 5. Acceptance Criteria
| ID | Criterion | Verified by |
|---|---|---|
| AC-1 | 인덱스의 essentials 순서에 새 레슨 4개가 폴더 번호 자리(§2.1)에 들어간다: `lambda_capture, format_text, const_correctness, error_expected, source_location, concepts, ranges_views, variant_visit, …`. 기존 레슨의 id와 서로의 순서는 그대로다 | `py -3 tools/lessons.py index -` 출력, testrecord |
| AC-2 | 새 레슨 4개가 `windows-x64-debug`와 `linux-x64-debug`에서 경고 없이 빌드되고 smoke test가 통과한다. 각 레슨의 출력에 §2.2의 단계가 모두 나온다 | 빌드 로그, `ctest -L lesson`, 레슨별 출력 전문을 testrecord에 |
| AC-3 | `const_correctness` 4단계의 표가 Assumption 7의 기대와 같다(초기화 0/0, `makeValue` 대입·`push_back`은 이동, `makeConst`는 복사). 두 preset의 Debug, 그리고 `linux-x64-playground-release`에서 같다 | 세 빌드의 출력 비교, testrecord |
| AC-4 | `concepts` 3단계가 `-3`→signed_integral, `3u`→integral, `2.5`→auto를 고른다. `ranges_views` 3단계에서 `take(2)`일 때 변환 호출 줄이 필요한 만큼만(재고 있는 앞 두 개) 나온다. `variant_visit` 5단계의 `sizeof(variant)`가 요소의 가장 큰 `sizeof` 이상이다 | 출력 전문, testrecord |
| AC-5 | 레슨 4개 모두 `README.en.md`가 있고, 각 영어판은 한국어판과 절 제목 수, 연습 과제 수, 코드 블록 수가 같다. 영어판의 링크는 영어판이 있는 README면 영어판을 가리킨다 | 070-03의 비교 스크립트, `cpp-reviewer` 번역 검토 한 번 |
| AC-6 | 새 레슨의 stdout·stderr에 한글이 없다. 새 소스에서 한글 주석 줄(또는 문단)마다 바로 다음이 같은 뜻의 영어 주석이다 | 070-03 AC-5의 두 스크립트, testrecord |
| AC-7 | 저장소에서 `py -3 tools/lessons.py check`가 ERROR 0, WARN 0이다 | 명령 출력 |
| AC-8 | 웹 검색: `std::visit`, `requires`, `views`, `mutable`, `컨셉`이 각각 해당 새 레슨을 찾고, `std::variant`는 `variant_visit`과 `device_state_machine`을 둘 다 찾는다. 영어 화면에서 새 레슨 4개의 README가 안내 줄 없이 영어판으로 나온다 | 헤드리스 브라우저(070-03 AC-8과 같은 방식): 검색어 6개 결과 기록, 스크린샷 2장(검색 하나, 영어 README 하나) |
| AC-9 | 전체 suite가 두 preset에서 통과한다. `npm --prefix web/frontend test`, `tools/test_lessons.py` 통과 | 명령 출력, testrecord |
| AC-10 | §8 문서가 갱신되고 `lint_docs.py`가 exit 0이다 | 명령 출력 |

## 6. Out of Scope
- E8, E9, E12(시간·파일·lock-free) — 070-12
- 파이프 형식 `ranges::to`, range 포맷, `std::forward_like`를 레슨 코드에 — Linux 툴체인이 libstdc++ 15로 가면(KI-033)
- concepts를 쓰도록 `observer.hpp` 외 패턴 헤더를 고치기 — 각 패턴 작업(KI-023)
- Iterator 패턴과 ranges 연결 — 023-05(이 레슨을 링크)
- E5 ranges, E6 variant의 evolution 페이지 — 필요해지면(Assumption 13)

## 7. Dependencies & Backends
none. 새 의존성 없음. 레슨은 `atugcc_core`만 링크한다(기존).

## 8. Documentation Updates
| Document | Section | Change |
|---|---|---|
| `lessons/tracks/01_essentials/{03_const_correctness,06_concepts,07_ranges_views,08_variant_visit}/README.md`, `README.en.md` | 전체 | 새로 씀 |
| [`lessons/tags.toml`](/lessons/tags.toml) | — | 태그 4개(§2.3) |
| [`lessons/tracks/02_patterns/01_device_state_machine/lesson.toml`](/lessons/tracks/02_patterns/01_device_state_machine/lesson.toml) | `tags` | `variant` 더함 |
| [`docs/tasks/lesson_candidates.md`](/docs/tasks/lesson_candidates.md) | Essentials 표 | E14, E1, E5, E6 폴더와 `레슨 있음`, E6 행의 `variant` 태그 메모 지움(한 일) |
| `docs/cpp_evolution/concepts.md` | 새 페이지 | Legacy SFINAE → concepts·requires → 축약 템플릿, 레슨 링크 |
| [`docs/learning/const_return_type_guide.md`](/docs/learning/const_return_type_guide.md) | 1. 리턴 타입 앞의 const | 복사 생략 설명 고침(Assumption 8), 레슨 링크 |
| [`docs/known_issues.md`](/docs/known_issues.md) | KI-001, KI-033 | KI-001: `concepts.md` 씀. KI-033: 제목은 070-13이 이미 넓힘. 없는 목록에 `std::forward_like`(직접 호출도 Clang 20 + libstdc++ 14.2에서 오류)를 더하고, `ranges_views`·`const_correctness`가 호출 형식 `ranges::to`와 deducing this를 코드에 쓴다고 적음 |
| [`lessons/README.md`](/lessons/README.md) | — | 바꿀 것 없음을 확인(빈 번호 설명이 그대로 맞음) |
| [`docs/tasks/agent_todo.md`](/docs/tasks/agent_todo.md) | Phase 7 | 070-11 줄(링크, 상태) |

## 9. Technical Constraints
- Compiler: MSVC (VS 2026) / Clang 20 + libstdc++ 14 (플레이그라운드와 `linux-x64-*` preset, 070-13)
- CMake: 4.0+
- C++ Standard: C++23 (레슨이 쓰는 C++23: `views::enumerate`/`zip`/`chunk`/`slide`, `ranges::fold_left`, 호출 형식 `ranges::to`, deducing this)

## 10. Context & References
- [070-03 스펙](/docs/specs/070_03_essentials_curriculum.md)(트랙 순서, 레슨 규칙), [레슨 후보 목록](/docs/tasks/lesson_candidates.md), [lessons/README.md](/lessons/README.md), [tags.toml](/lessons/tags.toml)
- [observer.hpp](/include/atugcc/pattern/observer.hpp)(`ObserverOf`), [ring_buffer.hpp](/include/atugcc/core/ring_buffer.hpp)(`requires` 절), [state.hpp](/include/atugcc/pattern/state.hpp)(`overloaded`, variant 상태 머신)
- [const_return_type_guide.md](/docs/learning/const_return_type_guide.md), [KI-001, KI-033](/docs/known_issues.md), [070-13 스펙](/docs/specs/070_13_modules_clang_toolchain.md)(Linux 툴체인)
- 시험 2026-11-04(WSL, Clang 20.1.2, libstdc++ 14.2, `-std=gnu++23 -Wall -Wextra -Werror`, 저장소 밖 단일 파일): `ranges_views`의 1–5단계(프로젝션, 파이프라인, C++23 뷰 여섯, 호출 형식 `ranges::to`, `dangling`/`owning_view`), `concepts`의 1–5단계, `variant_visit`의 1·2·4·5단계, `const_correctness` 3단계의 deducing this와 4단계 표: 빌드·실행 성공. 오류로 확인: 파이프 형식 `ranges::to`와 `std::forward_like` 직접 호출(같은 `forward_like` 오류), range 포맷(`formatter` 없음), `const int` 반환(`-Wignored-qualifiers`)

## 11. Implementation Plan
- [ ] Step 1: `tags.toml` 태그 4개, `device_state_machine`에 `variant`, `lessons.py check`
- [ ] Step 2: `const_correctness`(코드, 매니페스트), 두 preset 빌드·실행, `const_return_type_guide.md` 고침
- [ ] Step 3: `concepts`, `docs/cpp_evolution/concepts.md`
- [ ] Step 4: `ranges_views`
- [ ] Step 5: `variant_visit`
- [ ] Step 6: README 두 판 ×4, 그 밖의 §8 문서(KI-001, KI-033, lesson_candidates)

## 12. Verification Plan
- [ ] `py -3 tools/test_lessons.py`, `py -3 tools/lessons.py check`(ERROR 0, WARN 0)
- [ ] `py -3 .agent/scripts/build.py --preset windows-x64-debug --test`, `--preset linux-x64-debug --test` (0 warnings, 전체 suite)
- [ ] `const_correctness`를 `linux-x64-playground-release`로도 실행(AC-3)
- [ ] 출력 한글 검사, 주석 짝 검사(AC-6)
- [ ] `npm --prefix web/frontend test`
- [ ] 브라우저(AC-8): 스크린샷을 `docs/tasks/feature_070-11-essentials-syntax/screenshots/`에
- [ ] `py -3 .agent/scripts/lint_docs.py` exit 0
- [ ] Every AC row has its evidence in `testrecord.md`

## History / Amendments
- 2026-11-03: 초안
- 2026-11-04: 070-13(Linux 툴체인 Clang 20 + libstdc++ 14, CMake 4) 뒤 승인 전 개정. Assumption 3·5·6·7, §2.2(`const_correctness` 3단계·연습, `ranges_views` 4단계·README·연습), §2.4, §3, §4, §6, §8 KI-033, §9, §10. deducing this와 호출 형식 `ranges::to`를 README에서 코드로, `std::forward_like`를 README 목록에. `unblocks`에서 070-13을 뺌(이미 끝남)
- 2026-11-04: 승인
- 2026-11-04 (DEV, U1): §2.3에서 `const` 태그의 별칭 `mutable`을 뺌(이미 `capture` 태그의 것, `lessons.py check` WARN). 대신 레슨 summary에 `mutable`
- 2026-11-04 (DEV, U2 리뷰): §2.2 3단계의 예시 값을 코드에 맞춤(`b.get(1) = 21`)
