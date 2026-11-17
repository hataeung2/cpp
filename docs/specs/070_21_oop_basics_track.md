---
id: 070-21
title: OOP 입문 트랙 (트랙 구성, 커리큘럼, 첫 레슨 4개)
depends_on: [070-17, 070-20]
unblocks: []
approved: 2026-11-12
---

# Spec 070-21: OOP 입문 트랙 (트랙 구성, 커리큘럼, 첫 레슨 4개)

## 0. Assumptions (please review)
| # | Decision | Rejected alternative | Why |
|---|---|---|---|
| 1 | **범위**: (a) 새 트랙 `03_oop_basics`, (b) 트랙의 전체 커리큘럼(레슨 7개, §2.1)을 [lesson_candidates.md](/docs/lesson_candidates.md)에 확정, (c) 그중 **첫 레슨 4개**(`class_basics`, `object_lifetime`, `copy_and_move`, `inheritance_virtual`)를 만든다. 나머지 3개(`composition`, `smart_pointers`, `value_semantics`)는 번호만 비워 두고 후속 작업이 만든다 | 7개 모두 이 작업에서, 또는 목록만 | 레슨마다 코드·README 두 판·과제 정의·sanitizer 확인이 있어 7개는 리뷰 단위가 너무 크다. 목록만이면 레슨 형식이 검증되지 않는다. 070-03이 같은 방식으로 나눴다 |
| 2 | **독자**: 변수, 함수, 반복문, `struct`는 아는데 클래스는 처음 쓰는 사람. C++ 기초 문법(변수·제어문·포인터)은 이 트랙이 가르치지 않는다 | 프로그래밍 첫걸음부터 | 기초 문법 트랙은 별개의 큰 결정(범위, 순서, 언어 입문서와의 관계)이다. 이 트랙은 essentials가 "알고 있다"고 가정하는 것(`const` 멤버 함수, 가상 함수, 소멸자, 이동)을 채운다 |
| 3 | **트랙 위치는 `03_oop_basics`** (patterns 뒤, 맨 아래; 사용자 결정 2026-11-12). 폴더를 옮기지 않는다. `lessons/README.md`, `intro.md`, `intro.en.md`의 트랙 목록에 세 번째로 더한다. 앞 트랙의 레슨이 클래스·가상 함수·소멸자를 처음 쓰는 자리(`const_correctness`, `variant_visit`)에는 "낯설면 `03_oop_basics`"라는 링크 한 줄을 건다(§8) | (a) `00_`로 essentials 앞; (b) essentials 안에 끼워 넣기 | (a) 배우는 순서로는 앞이 자연스럽지만 사용자가 맨 아래를 골랐다. 이 트랙을 참고 자료처럼 쓰고, essentials·patterns를 먼저 보는 흐름을 유지한다. (b) essentials 폴더 번호는 최종 순서라 끼워 넣으면 폴더를 옮겨야 하고(070-03 Assumption 3), essentials는 C++를 이미 쓰는 독자가 대상이다 |
| 4 | **레슨 형식은 "예전 방식 → C++20/23"이 아니라 "흔한 실수 → 바른 방식"**이다. README 표의 제목을 "흔한 실수와 바른 방식"으로 한다. C++20/23은 오류의 원인을 지우는 곳에서만 쓴다: `override`, `= default`/`= delete`, `explicit`, `[[nodiscard]]`, 멤버 초기화, `std::unique_ptr`, 기본 비교(`<=>`), designated initializers. 억지로 표준 변경을 비교하지 않는다 | 다른 essentials 레슨처럼 표준 변경 비교를 모든 레슨에 | 입문자에게 "C++11 이전엔 이랬다"는 알 필요가 없는 이야기다. 필요한 것은 처음 쓰는 사람이 실제로 저지르는 실수와 그것을 막는 현대 C++의 도구다 |
| 5 | **눈에 보이는 실행**: 생성·소멸·복사·이동을 출력으로 찍는 작은 타입을 레슨이 만들어(`const_correctness`의 `Tracked`와 같은 방식) 수명과 호출 순서를 설명 대신 출력으로 보인다. 이 타입은 **레슨마다 `main.cpp`에 20줄 안팎으로 따로 쓴다**(유닛으로 뽑지 않음). 레슨은 `main.cpp` 하나다 | 모든 레슨이 쓰는 유닛 `lifetime_probe` | 읽는 사람이 한 파일 안에서 타입과 사용을 같이 읽는 편이 낫다. 같은 모양이 2–3곳 반복되는 비용은 작고, 유닛을 고치면 레슨 셋의 출력이 한꺼번에 바뀌는 비용이 더 크다. 여러 레슨이 *같은 클래스 계층*을 쓰는 설계가 필요해지면(후속 레슨) 그때 유닛으로 뽑는다 |
| 6 | **정의되지 않은 동작(UB)을 실행하지 않는다.** 기반 클래스 포인터로 `delete`(가상 소멸자 없음), 이중 해제, 슬라이싱 뒤의 잘못된 접근은 레슨이 돌리지 않는다. 그 위험은 README 글, 컴파일러 경고를 오류로 바꾸는 연습 과제(`-Wdelete-non-virtual-dtor` 등), 그리고 안전하게 보이는 출력(복사·이동 횟수, 슬라이싱 시 `name()` 결과)으로 보인다 | 실제로 돌려서 깨지는 것을 보이기 | 레슨은 smoke test와 ASan/UBSan preset에서도 통과해야 한다. UB를 돌리면 도구가 실패하고 결과도 보장되지 않는다 |
| 7 | **레슨 7개의 순서와 주제는 §2.1 표**: 클래스 기초 → 수명(생성·소멸·RAII) → 복사·이동(Rule of 0/5) → 상속·가상 함수 → 합성 대 상속 → 스마트 포인터와 소유권 → 값 의미론과 비교 연산자. 폴더 번호는 최종 순서(`01_`–`07_`)이고 후속 세 개의 번호는 비운다(070-03 Assumption 3과 같은 방식) | 번호 없이 추가 순서로 | 이후 레슨이 아무것도 옮기지 않게 한다 |
| 8 | **각 레슨은 `exercises.toml`을 갖는다**(070-17). 자동/관찰 기준과 규칙은 [070-20](/docs/specs/070_20_remaining_exercises.md) Assumption 2·3을 따른다: 웹(Clang)과 로컬(MSVC)에서 같은 결과면 자동, 아니면 관찰. 컴파일 오류를 읽는 연습을 적극적으로 쓴다(`override` 철자 틀림, `= delete`된 복사, 순수 가상 함수의 객체 생성) | 과제 정의는 후속 작업으로 | 070-20이 "새 레슨은 과제 정의를 함께 낸다"고 이미 정했다([lesson_candidates.md](/docs/lesson_candidates.md) 머리말) |
| 9 | **언어와 출력**: 프로그램 출력은 영어, 코드 주석은 한국어 줄 아래에 영어 줄, `README.md`와 `README.en.md`를 둘 다 쓴다(070-03 Assumption 10·12). 레슨 `title_en`, `summary_en`, 트랙 `title_en`, `summary_en`을 쓴다 | 한국어 우선, 영어는 나중에 | `lessons.py check`가 WARN으로 잡는다 |
| 10 | **태그**: 어휘에 `class`, `lifetime`, `copy`, `inheritance`를 더한다(별칭에 한국어 낱말 포함: 클래스, 생성자, 소멸자, 수명, 복사, 상속, 가상 함수, 다형성 등). `copy_and_move`는 기존 `move`도 붙인다. 후속 레슨의 `smart_pointer` 등은 그 작업이 더한다(`tags.toml` 머리 주석의 규칙) | 태그 없이 | 070-10의 기능 검색이 "가상 함수", "소멸자"로 찾게 한다 |
| 11 | **evolution 페이지는 만들지 않는다.** 이 트랙은 표준 변경 비교가 아니라 입문 설명이라 `docs/cpp_evolution/`에 쓸 "예전 → 새" 이야기가 없다. 설명은 레슨 README에 둔다. 단 `inheritance_virtual`의 `override`/`final`처럼 기존 페이지가 다루는 내용은 링크만 더한다 | 레슨마다 evolution 페이지 | 페이지는 두 언어 쌍을 계속 맞춰야 하는데, 가르치는 내용이 표준 역사가 아니다 |
| 12 | **진행 순서 자리는 이 스펙이 정하지 않는다.** 승인되면 `agent_todo.md`에 `BACKLOG`로만 두고 "진행 순서"의 A2·B 문단은 그대로 둔다. 070-20에 의존하므로(과제 정의 기준) 070-20보다 앞설 수 없다 | B의 레슨 줄에 넣기 | 순서를 바꾸는 것은 사용자 결정이다(`agent_todo.md` 진행 순서 머리말) |

## 1. Objective
essentials와 patterns 트랙은 클래스, 소멸자, 가상 함수, 복사·이동을 이미 아는 독자를 가정한다. OOP를 처음 배우는 사람이 플레이그라운드에서 "클래스가 무엇을 약속하는가, 객체는 언제 만들어지고 사라지는가, 복사와 이동은 무엇이 다른가, 상속과 가상 함수는 무엇을 하는가"를 출력으로 보고 컴파일 오류로 확인하며 익히게 한다. 이 작업은 그 트랙 `03_oop_basics`의 구성과 전체 커리큘럼을 정하고, 첫 레슨 4개를 만든다.

## 2. Requirement Details

### 2.1 트랙과 커리큘럼
`lessons/tracks/03_oop_basics/track.toml` (`title`, `title_en`, `summary`, `summary_en`: "OOP 입문: 클래스, 수명, 상속" / "OOP basics: classes, lifetime, inheritance").

| 폴더 | 레슨 id | 주제 | 흔한 실수 → 바른 방식 | 이 작업 |
|---|---|---|---|---|
| `01_class_basics` | `class_basics` | 클래스와 캡슐화 | 모든 멤버 `public`, 초기화 안 한 멤버, 한 인자 생성자의 암시적 변환 → 불변식을 지키는 멤버 함수, 생성자 초기화 목록과 멤버 기본값, `explicit` | **새로** |
| `02_object_lifetime` | `object_lifetime` | 객체의 수명: 생성·소멸·RAII | `new`/`delete` 짝 맞추기, 멤버 초기화·소멸 순서 착각 → 스코프가 수명을 정함, 소멸자에서 자원 해제(RAII) | **새로** |
| `03_copy_and_move` | `copy_and_move` | 복사와 이동, Rule of 0/5 | 자원을 가진 클래스를 얕게 복사 → 복사·이동을 직접 쓰거나(`Rule of 5`) 쓰지 않고 멤버에게 맡김(`Rule of 0`), `= default`/`= delete` | **새로** |
| `04_inheritance_virtual` | `inheritance_virtual` | 상속, 가상 함수, 추상 클래스 | 가상 소멸자 없음, 오버라이드 철자 틀림, 값으로 받아 슬라이싱 → `virtual ~Base`, `override`/`final`, 참조·포인터로 받기, 순수 가상 함수 | **새로** |
| `05_` | (후속) `composition` | has-a 대 is-a | 코드 재사용을 위한 상속 → 합성과 위임, LSP를 어기는 `Square : Rectangle` | 비움 |
| `06_` | (후속) `smart_pointers` | 소유권 | 날 포인터가 소유권을 숨김 → `unique_ptr`, `shared_ptr`/`weak_ptr`, `vector<unique_ptr<Base>>` | 비움 |
| `07_` | (후속) `value_semantics` | 값 의미론, 연산자, 비교 | 비교 연산자 6개 직접 쓰기 → `operator<=>` 기본 비교, 연산자 오버로딩의 기준 | 비움 |

각 레슨은 `profile = "quick"`, `sources = ["main.cpp"]`, `uses = []`(필요하면 `lib:` 참조), 단계 머리줄 `== Step N: … ==`, 출력 영어. 레슨 사이의 참조는 링크(`const_correctness`, `error_expected`, `variant_visit`)만 건다.

### 2.2 첫 레슨 4개
| 레슨 | 단계(출력으로 보이는 것) | 연습(초안, 과제 정의는 DEV에서) |
|---|---|---|
| `class_basics` | 1 `struct`와 `class`의 기본 접근 차이, 2 불변식이 깨지는 `public` 멤버와 지키는 멤버 함수(`Account::withdraw`가 `core::Expected`로 실패 반환), 3 생성자 초기화 목록 대 본문 대입과 멤버 기본값(순서 출력), 4 `explicit`이 막는 암시적 변환, 5 `const` 멤버 함수 한 줄 복습([const_correctness](/lessons/tracks/essentials/const_correctness/README.md) 링크) | `explicit` 지우고 의도치 않은 변환이 일어나게 하기, 멤버 선언 순서와 초기화 목록 순서를 다르게 해 경고 읽기, `public` 멤버를 `private`로 바꿔 오류 읽기 |
| `object_lifetime` | 1 스코프를 벗어나면 소멸자가 호출됨(생성·소멸 줄), 2 멤버·기반 객체의 생성/소멸 순서(역순), 3 임시 객체와 `const&`로의 수명 연장, 4 RAII 가드(`ScopedFile`류, 자원은 출력 줄로 표현)와 예외가 나도 해제되는 것, 5 `new`/`delete` 직접 쓰기와 `std::unique_ptr` 비교(누수는 실행하지 않고 코드·README로만) | 멤버 선언 순서를 바꿔 소멸 순서 확인, 가드에서 `return` 경로 추가, 임시 객체를 참조로 묶어 수명 연장 확인 |
| `copy_and_move` | 1 복사·이동 횟수를 세는 타입으로 값 전달(복사 / `std::move` / 반환), 2 자원을 가진 클래스에서 얕은 복사가 두 소유자를 만드는 문제를 소유자 수 카운터로 보임(UB 실행 없음, Assumption 6), 3 Rule of 5로 직접 쓰기, 4 Rule of 0(`std::string`, `std::vector` 멤버), 5 `= delete`로 복사 금지(`std::unique_ptr` 멤버가 있으면 저절로 그렇게 됨) | 복사 생성자를 `= delete`하고 컴파일 오류 읽기, 이동 후 원본이 어떤 상태인지 출력, 이동 생성자에 `noexcept`를 빼고 `std::vector` 재할당 때 복사로 바뀌는 것 확인 |
| `inheritance_virtual` | 1 `Base`/`Derived`와 비가상 함수 호출(정적 결합), 2 `virtual`과 `override`(동적 결합), 3 가상 소멸자가 있을 때의 소멸 순서(없을 때의 위험은 README), 4 값으로 받으면 슬라이싱되는 것을 `name()` 결과로 보임, 5 추상 클래스와 순수 가상 함수, `vector<unique_ptr<Shape>>`로 다형적 사용, 6 `final` | `override`의 철자 틀림, `-Wdelete-non-virtual-dtor`를 오류로 읽기, 추상 클래스 객체 생성 시도, `final` 클래스에서 상속 |

### 2.3 Internal Implementation
| 파일 | 변경 |
|---|---|
| `lessons/tracks/03_oop_basics/track.toml` (새) | §2.1 |
| `lessons/tracks/03_oop_basics/{01_class_basics,02_object_lifetime,03_copy_and_move,04_inheritance_virtual}/` (새) | `lesson.toml`, `main.cpp`, `README.md`, `README.en.md`, `exercises.toml` |
| [`lessons/tags.toml`](/lessons/tags.toml) | Assumption 10 |
| `tools/lessons.py`, 서버, 프런트엔드 | 변경 없음 예정(DEV에서 `03_` 접두사가 트리와 인덱스에서 `02_patterns` 뒤에 오는지만 확인, AC-4) |

### 2.4 Platform Specifics
- Windows(MSVC)와 Linux(Clang 20, libstdc++ 14) preset 모두 경고 없이 빌드. 경고를 오류로 다룬다.
- 소멸·복사 순서처럼 표준이 정한 출력은 두 컴파일러에서 같다. 복사 생략(C++17 보장 생략)에 기대는 줄은 "보장되는 곳"만 쓴다.
- `-Wdelete-non-virtual-dtor` 같은 경고의 유무는 컴파일러마다 달라 해당 연습은 DEV에서 분류한다(070-20 Assumption 2).

## 3. C++ Standard Evolution
Assumption 4: 레슨이 표준 변경을 비교하지 않는다. 쓰는 기능: `override`/`final`(C++11), `= default`/`= delete`(C++11), 보장된 복사 생략(C++17), `[[nodiscard]]`(C++17), `operator<=>`(C++20, 후속 레슨), `std::expected`(C++23). N/A for evolution pages (Assumption 11).

## 4. Edge Cases
- [x] Thread safety / memory ordering — N/A. 모든 레슨은 단일 스레드다.
- [x] Resource lifetime / RAII — 이 트랙의 주제 그 자체. 자원은 실제 파일·메모리가 아니라 출력 줄과 카운터로 표현해 sanitizer 결과가 레슨 의도와 섞이지 않게 한다. 댕글링 참조(`const&` 수명 연장의 한계)는 README 글과 주석으로만 보인다.
- [x] Platform differences — §2.4.
- [x] Template instantiation / concept constraints — N/A (템플릿은 이 트랙의 범위 밖).
- [x] ODR — 클래스는 `main.cpp` 안 익명 namespace에 둔다. 헤더·유닛 없음.
- [x] Undefined behaviour — Assumption 6. 레슨이 UB를 실행하지 않는다. 슬라이싱은 정의된 동작이다. 이동한 뒤의 객체는 "유효하지만 지정되지 않은 상태"이므로, 레슨은 *레슨이 직접 정의한* 타입의 이동 후 상태만 찍고 표준 타입(`std::string` 등)의 이동 후 값은 찍지 않는다.
- [x] 출력의 안정성 — 주소·시간·해시를 찍지 않는다. 모든 줄이 두 OS에서 같다(`exercises.toml`이 출력을 `expect`로 쓸 수 있도록).
- [x] ASan/UBSan: 실제 누수나 이중 해제를 만들지 않는다(Assumption 6).

## 5. Acceptance Criteria
| ID | Criterion | Verified by |
|---|---|---|
| AC-1 | 레슨 4개가 `windows-x64-debug`, `linux-x64-debug`에서 경고 없이 빌드되고 smoke test `lesson.<id>`가 통과한다. 출력에 §2.2의 단계 머리줄과 각 단계의 핵심 줄(소멸 순서, 복사·이동 횟수, 슬라이싱 결과 등)이 있다 | 빌드 로그, `ctest -R lesson.`, 출력 발췌 |
| AC-2 | `linux-x64-asan`(UBSan 포함이면 그것)에서 `ctest -R lesson.<id>`가 4개 모두 통과한다 | 명령 출력 |
| AC-3 | `py -3 tools/lessons.py check`가 ERROR·WARN 0이고(`title_en`·`README.en.md`·태그·과제 수 포함) `lint_docs.py`가 exit 0이다 | 명령 출력 |
| AC-4 | `lessons.py index`와 플레이그라운드 트리에서 `03_oop_basics`가 `02_patterns` 뒤(맨 아래)에 오고, 영어 화면에서 트랙 제목·레슨 제목·README가 영어로 나온다. 검색 "소멸자", "virtual", "상속"이 해당 레슨을 찾는다 | 인덱스 JSON, 헤드리스 브라우저 확인 기록 |
| AC-5 | 각 레슨의 `exercises.toml`이 `lessons.py check`를 통과하고, `lesson.<id>.exercises_verify`가 통과하며(원본이 어떤 자동 과제도 통과하지 않음), 자동 과제는 해설대로 풀면 연습 공간에서 통과한다 | 070-17의 도구, 풀이 기록(testrecord) |
| AC-6 | README 두 판이 같은 절·연습 수·코드 블록 수를 갖는다. 영어판의 링크는 영어판 README를 가리킨다 | 070-03의 비교 스크립트, 읽기 확인 |
| AC-7 | [`lesson_candidates.md`](/docs/lesson_candidates.md)에 OOP 입문 표(§2.1)가 있고 레슨 4개가 `레슨 있음`, 3개가 `후보`다. `lessons/README.md` 구조·트랙 문단과 `intro.md`/`intro.en.md`의 트랙 목록이 `03_oop_basics`를 포함한다 | 읽기 확인, `lint_docs.py`(링크) |
| AC-8 | 전체 suite가 두 preset에서 통과한다 | 명령 출력 |

## 6. Out of Scope
- 나머지 레슨 3개(`composition`, `smart_pointers`, `value_semantics`) — 이 작업 승인 뒤 후속 작업으로 todo에 등록
- C++ 기초 문법 트랙(변수, 제어문, 포인터, 함수) — 필요하면 별도 결정(Assumption 2)
- 템플릿·제네릭 프로그래밍 — essentials의 `concepts`
- 디자인 패턴 — `02_patterns` 트랙(021–024)
- 예외 안전성, 다중 상속, 가상 상속 — 후보 목록에 새 행으로 남기지 않았다. 필요하면 후속 레슨 목록에 더한다
- 기존 레슨의 내용 변경 — 이 트랙 링크를 걸 필요가 생기면 각 레슨의 README에 링크 한 줄만(이 작업 §8)

## 7. Dependencies & Backends
없음.

## 8. Documentation Updates
| Document | Section | Change |
|---|---|---|
| [`lessons/README.md`](/lessons/README.md) | 구조, "트랙은 학습 순서" 문단 | `03_oop_basics`를 세 번째 트랙으로 추가, 순서 문장 |
| [`lessons/intro.md`](/lessons/intro.md), [`intro.en.md`](/lessons/intro.en.md) | 트랙 목록 | 트랙 한 줄과 예 링크 |
| [`docs/lesson_candidates.md`](/docs/lesson_candidates.md) | 새 절 "OOP 입문 트랙 (070-21)" | §2.1 표, 머리말의 "essentials는 070-03" 문장에 이 트랙 추가 |
| [`lessons/tags.toml`](/lessons/tags.toml) | 새 태그 4개 | Assumption 10 |
| `lessons/tracks/01_essentials/03_const_correctness/README.md`, `README.en.md`; `08_variant_visit/…` | "볼 것" 끝 | "클래스·가상 함수가 낯설면 `03_oop_basics`" 링크 한 줄(Assumption 3). 내용은 바꾸지 않음 |
| [`docs/agent_todo.md`](/docs/agent_todo.md) | 070-21 줄 | `SPEC_DRAFT` → 승인 후 상태 |

## 9. Technical Constraints
- Compiler: MSVC (VS 2026) / Clang 20 with libstdc++ 14 (Linux)
- CMake: 4.0+
- C++ Standard: C++23 (C++20 minimum)
- 레슨 코드는 [Core rules](/.agent/rules/impl.md)를 따른다: `using namespace std;` 금지, C 스타일 캐스트·`void*` 금지, 이름 규칙(타입 `PascalCase`, 함수 `camelCase`, 멤버 `snake_case_`). 입문 레슨이 *잘못된* 코드를 보이는 곳은 주석 처리하거나 연습 과제의 입력으로만 두고, 컴파일되는 코드에는 두지 않는다

## 10. Context & References
- [070-03](/docs/specs/070_03_essentials_curriculum.md) — 트랙·레슨 형식, 영어판, 번호 정책
- [070-17](/docs/specs/070_17_exercise_check.md), [070-20](/docs/specs/070_20_remaining_exercises.md) — 과제 정의
- [`03_const_correctness`](/lessons/tracks/essentials/const_correctness/README.md) — 복사·이동 횟수를 세는 타입의 예, README 형식
- [`08_variant_visit`](/lessons/tracks/essentials/variant_visit/README.md) — 가상 함수와 variant 비교(`inheritance_virtual`을 선행 읽을거리로 링크)
- [lessons/README.md](/lessons/README.md) — 매니페스트, 새 레슨 추가 절차

## 11. Implementation Plan
- [ ] Step 1: 트랙 폴더, `track.toml`, 태그, 트리·인덱스 확인(`03_` 접두사)
- [ ] Step 2: `class_basics`, `object_lifetime`(코드, README 두 판)
- [ ] Step 3: `copy_and_move`, `inheritance_virtual`
- [ ] Step 4: 레슨마다 `exercises.toml`과 풀이 확인
- [ ] Step 5: sanitizer 실행, 두 OS 출력 비교
- [ ] Step 6: 문서(`lessons/README.md`, intro 두 판, `lesson_candidates.md`), 플레이그라운드 확인, 문서 게이트

## 12. Verification Plan
- [ ] `py -3 .agent/scripts/build.py --preset windows-x64-debug --test --label lesson`, `--preset linux-x64-debug`
- [ ] `--preset linux-x64-asan`의 `ctest -R lesson.`(4개 id)
- [ ] `py -3 tools/lessons.py check`, `py -3 tools/lessons.py index`, `py -3 .agent/scripts/lint_docs.py` exit 0
- [ ] 자동 과제마다 `py -3 tools/exercises.py check <id> --preset <p>`로 풀이 확인
- [ ] 헤드리스 브라우저로 AC-4
- [ ] 모든 AC 행의 증거가 `testrecord.md`에

## History / Amendments
- 2026-11-12: 초안
- 2026-11-12: 승인(사용자). 트랙 위치를 `00_`에서 `03_oop_basics`(맨 아래)로 바꿈(Assumption 3)
