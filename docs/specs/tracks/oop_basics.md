---
track: oop_basics
approved: 2026-11-17    # YYYY-MM-DD, 사용자가 승인할 때마다 새로 씀
tasks: [070-22, 070-23, 070-24]
---

# Track spec: OOP 입문 (`oop_basics`)

트랙 spec의 규칙: [spec.md](/.agent/rules/spec.md) §6. 레슨 작업은 이 파일의 `tasks`에 있고 `approved`가 날짜이면 spec 없이 시작하고, [`00_lesson_checklist.md`](/docs/specs/tracks/00_lesson_checklist.md)를 모두 채워 끝낸다.

이 트랙의 형식과 첫 레슨 4개는 [070-21](/docs/specs/070_21_oop_basics_track.md)(승인 2026-11-12)이 정했다. 이 파일은 그 결정 가운데 트랙 전체에 걸린 것(070-21 Assumption 2, 4, 5, 6, 8, 9, 10, 11, §2.1 표, §2.4, §4, §9; 행마다 출처를 적음)을 옮겨 왔고, 그 뒤로는 이 파일이 원본이다. 070-21 Assumption 3(폴더 번호 `03_`)은 [070-26](/docs/specs/070_26_lesson_order_manifest.md)이 대신한다: 순서는 [`curriculum.toml`](/lessons/curriculum.toml)이 정하고 이 트랙은 patterns 뒤, 맨 아래다(사용자 결정 2026-11-12).

## 0. Assumptions (please review)
| # | Decision | Rejected alternative | Why |
|---|---|---|---|
| 1 | **독자**는 변수, 함수, 반복문, `struct`는 아는데 클래스는 처음 쓰는 사람이다. 기초 문법(변수·제어문·포인터)은 가르치지 않는다 (070-21 A2) | 프로그래밍 첫걸음부터 | 기초 문법 트랙은 별개의 큰 결정이다. 이 트랙은 essentials가 "알고 있다"고 가정하는 것(`const` 멤버 함수, 가상 함수, 소멸자, 이동)을 채운다 |
| 2 | **형식은 "흔한 실수 → 바른 방식"**이고 README 첫 절의 제목은 "흔한 실수와 바른 방식"(영어 "Common mistakes and the right way")이다. C++20/23은 오류의 원인을 지우는 곳에서만 쓴다: `override`, `= default`/`= delete`, `explicit`, `[[nodiscard]]`, 멤버 초기화, `std::unique_ptr`, 기본 비교(`<=>`), designated initializers. 억지로 표준 변경을 비교하지 않는다 (070-21 A4) | "예전 방식 → C++20/23" 비교 | 입문자에게 표준의 역사는 알 필요가 없는 이야기다 |
| 3 | **수명과 호출 순서는 출력으로 보인다.** 생성·소멸·복사·이동을 찍는 작은 타입을 레슨마다 `main.cpp`에 20줄 안팎으로 따로 쓴다(유닛으로 뽑지 않음). 레슨은 `main.cpp` 하나다. 여러 레슨이 같은 클래스 계층을 써야 할 때만 유닛으로 뽑는다. 여러 레슨이 쓰는 유닛이나 기존 유닛의 변경은 레슨 경로 밖이므로 그 부분은 따로 작업(또는 KI)이 되고 레슨 작업은 `BLOCKED`다([spec.md](/.agent/rules/spec.md) §6) (070-21 A5) | 모든 레슨이 쓰는 유닛 | 한 파일 안에서 타입과 사용을 같이 읽는 편이 낫다 |
| 4 | **정의되지 않은 동작을 실행하지 않는다.** 기반 클래스 포인터로 `delete`(가상 소멸자 없음), 이중 해제, 슬라이싱 뒤의 잘못된 접근은 돌리지 않는다. 위험은 README 글, 컴파일러 경고를 오류로 바꾸거나 컴파일 오류를 읽는 과제(`-Wdelete-non-virtual-dtor` 등), 안전하게 보이는 출력(횟수, 카운터, `name()` 결과)으로 보인다. 자원은 실제 파일·메모리가 아니라 출력 줄과 카운터로 표현하고, 댕글링 참조는 README 글과 주석으로만 보인다. 잘못된 코드는 주석이나 과제 입력으로만 두고 컴파일되는 코드에는 두지 않는다 (070-21 A6, §4, §9) | 돌려서 깨지는 것을 보임 | smoke test와 ASan/UBSan에서 통과해야 하고, UB의 결과는 보장되지 않는다 |
| 5 | **과제**: 레슨마다 `exercises.toml`. 웹(Clang)과 로컬(MSVC)에서 같은 결과면 자동, 아니면 관찰. 컴파일 오류를 읽는 과제를 적극적으로 쓴다. 경고의 유무는 컴파일러마다 달라 그런 과제는 두 컴파일러에서 돌려 보고 분류한다 (070-21 A8, §2.4, [070-20](/docs/specs/070_20_remaining_exercises.md) A2·A3) | 과제 없음 | 070-20이 "새 레슨은 과제 정의를 함께 낸다"고 정했다 |
| 6 | **언어**: 출력 영어, 주석은 한국어 줄 아래 영어 줄, `README.md`와 `README.en.md`, 매니페스트의 `title_en`, `summary_en` (070-21 A9) | 한국어 먼저 | `lessons.py check`가 WARN으로 잡는다 |
| 7 | **태그**: 레슨이 새 주제를 가르치면 그 레슨 작업이 [`tags.toml`](/lessons/tags.toml)에 태그를 더한다(한국어 별칭 포함). 지금 있는 것: `class`, `lifetime`, `copy`, `inheritance`, `move`. `smart_pointers`는 `smart_pointer`를 더한다 (070-21 A10) | 태그 없음 | 기능 검색(070-10)이 한국어 낱말로 찾게 한다 |
| 8 | **evolution 페이지를 만들지 않는다.** 설명은 레슨 README에 두고, 기존 페이지가 다루는 내용(`override`/`final` 등)은 링크만 건다 (070-21 A11) | 레슨마다 페이지 | 가르치는 내용이 표준의 역사가 아니다 |
| 9 | **출력은 두 OS에서 같다**: 주소·시간·해시를 찍지 않고, 이동한 뒤의 상태는 레슨이 직접 정의한 타입만 찍는다(표준 타입의 이동 후 값은 지정되지 않음). 복사 생략은 보장되는 곳만 출력에 기댄다 (070-21 §2.4, §4) | — | 과제의 `expect`가 출력을 쓰고, C5 항목이 비교한다 |
| 10 | **레슨 사이의 참조는 링크만** 건다(앞 레슨의 타입을 가져다 쓰지 않음). 단계 머리줄은 `== Step N: … ==`, 매니페스트는 `profile = "quick"`, `sources = ["main.cpp"]`, `uses = []`(필요하면 `lib:` 참조, 예: `class_basics`의 `lib:atugcc/core/error.hpp`) (070-21 §2.1) | — | 레슨 하나가 혼자 읽혀야 한다 |

## 1. 독자와 목표
독자: Assumption 1. 트랙을 끝내면 "클래스가 무엇을 약속하는가, 객체는 언제 만들어지고 사라지는가, 복사와 이동은 무엇이 다른가, 상속과 가상 함수는 무엇을 하는가, 누가 객체를 소유하는가, 값처럼 다루는 타입은 어떻게 만드는가"를 출력으로 보고 컴파일 오류로 확인해 설명할 수 있다.

## 2. 레슨 형식
- 첫 절: "흔한 실수와 바른 방식"(Assumption 2). `lessons.py new`의 기본 제목 "예전 방식과 C++20"을 바꾼다.
- 단계 머리줄 `== Step N: … ==`, 단계마다 출력으로 보이는 것 하나 이상(Assumption 10).
- 파일: `main.cpp` 하나, 클래스는 익명 namespace(Assumption 3).
- 언어: Assumption 6. README 절 순서는 [lessons/README.md](/lessons/README.md)의 뼈대대로(첫 절 → 실행 → 볼 것 → 연습).

## 3. 공통 규칙
- 정의되지 않은 동작: Assumption 4.
- 출력 안정성: Assumption 9.
- 연습 과제: Assumption 5.
- `docs/cpp_evolution/` 페이지: Assumption 8.
- 태그: Assumption 7.
- 템플릿, 다중 상속, 가상 상속, 예외 안전성은 다루지 않는다(§5).

## 4. 커리큘럼
행 순서가 트랙 안의 순서다. 실제 순서의 원본은 [`lessons/curriculum.toml`](/lessons/curriculum.toml)이다. 처음 4개는 070-21이 만들었고 `tasks`에 넣지 않는다. "선행" 열은 070-21 뒤의 [lesson_candidates.md](/docs/lesson_candidates.md) 표에서 옮겼다(070-21 §2.1에는 없던 열).

| 작업 | 레슨 id | 주제 | 흔한 실수 → 바른 방식 | 선행 | 상태 |
|---|---|---|---|---|---|
| 070-21 | `class_basics` | 클래스와 캡슐화 | 모든 멤버 `public`, 초기화 안 한 멤버, 한 인자 생성자의 암시적 변환 → 불변식을 지키는 멤버 함수, 초기화 목록과 멤버 기본값, `explicit` | — | 레슨 있음 |
| 070-21 | `object_lifetime` | 객체의 수명: 생성·소멸·RAII | `new`/`delete` 짝 맞추기, 멤버 초기화·소멸 순서 착각 → 스코프가 수명을 정함, 소멸자에서 자원 해제(RAII) | — | 레슨 있음 |
| 070-21 | `copy_and_move` | 복사와 이동, Rule of 0/5 | 자원을 가진 클래스를 얕게 복사 → 복사·이동을 직접 쓰거나(Rule of 5) 쓰지 않고 멤버에게 맡김(Rule of 0), `= default`/`= delete` | — | 레슨 있음 |
| 070-21 | `inheritance_virtual` | 상속, 가상 함수, 추상 클래스 | 가상 소멸자 없음, 오버라이드 철자 틀림, 값으로 받아 슬라이싱 → `virtual ~Base`, `override`/`final`, 참조·포인터로 받기, 순수 가상 함수 | — | 레슨 있음 |
| 070-22 | `composition` | has-a 대 is-a | 코드 재사용을 위한 상속 → 합성과 위임, LSP를 어기는 `Square : Rectangle` | `inheritance_virtual` | 레슨 있음 |
| 070-23 | `smart_pointers` | 소유권 | 날 포인터가 소유권을 숨김 → `unique_ptr`, `shared_ptr`/`weak_ptr`, `vector<unique_ptr<Base>>` | `object_lifetime`, `copy_and_move` | 레슨 있음 |
| 070-24 | `value_semantics` | 값 의미론, 연산자, 비교 | 비교 연산자 6개 직접 쓰기 → `operator<=>` 기본 비교, 연산자 오버로딩의 기준 | `copy_and_move` | 레슨 있음 |

상태: `후보`, `레슨 있음`. 070-23은 [agent_todo.md](/docs/agent_todo.md)의 070-23 줄대로 021-01 Factory보다 먼저 한다(070-21에 없던 순서 결정).

## 5. Out of Scope
- C++ 기초 문법(변수, 제어문, 포인터, 함수) — 필요하면 별도 결정(Assumption 1)
- 템플릿·제네릭 프로그래밍 — essentials `concepts`
- 디자인 패턴 — patterns 트랙(021–024)
- 예외 안전성, 다중 상속, 가상 상속 — 필요하면 이 표에 행을 더하고 사용자 승인

## History
- 2026-11-17: 090-13이 070-21의 트랙 결정을 옮겨 처음 씀, `tasks` 070-22 ~ 070-24. 사용자 승인
