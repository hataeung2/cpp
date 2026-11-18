# Lesson checklist: 070-24 `value_semantics`

레슨 작업 하나의 기록이다([spec.md](/.agent/rules/spec.md) §6). 이 파일을 `docs/tasks/feature_NNN-SS-<slug>/checklist.md`로 복사해 쓰고, `plan.md`, `testrecord.md`, `walkthrough.md`는 쓰지 않는다. `DONE`이 되려면 아래의 `- [ ]`가 하나도 남지 않아야 한다(문서 gate가 검사). 맞지 않는 항목은 지우지 않고 `- [x] N/A: <이유>`로 쓴다.

- Track spec: `/docs/specs/tracks/oop_basics.md` (approved 2026-11-17), 행: `value_semantics`
- Branch: `feature/070-24-value-semantics`

## 설계
lead가 정한다. 트랙 spec의 행(주제, 비교)과 공통 규칙 안에서.

| 단계 | 출력으로 보이는 것 |
|---|---|
| 1 | 값 의미론: `Point b = a;` 뒤 `b.x = 10`이 `a`를 바꾸지 않음, `== = default`로 `a == b`가 `false` → `b = a` 뒤 `true`. 참조 의미론과의 차이: `shared_ptr<Point>` 둘 `p`, `q`에서 `q->x = 10`이 `*p`에 보임 |
| 2 | 흔한 실수: `OldDate`의 비교 연산자 여섯 개를 직접 씀, `operator<`가 `day`를 잊음 → `!= true`인데 `<`, `>` 모두 `false`, `<=`, `>=` 모두 `true` |
| 3 | 바른 방식: `Date`의 `auto operator<=>(const Date&) const = default;` → 여섯 결과가 서로 맞음, `std::ranges::sort`로 날짜 순 |
| 4 | 직접 쓰는 `<=>`와 `==`: `Fraction`(1/2, 2/4)의 `std::weak_ordering`, `1/2 == 2/4: true`, `1/2 < 2/4: false`, `is equivalent: true` |
| 5 | 연산자 오버로딩의 기준: `+=` 멤버, `+=`로 만든 비멤버 `+`, `operator<<`. `6/8`, `6/8 == 3/4: true` |

| 과제 id | 무엇을 바꾸나 | 자동 / 관찰 | 관찰이면 이유 |
|---|---|---|---|
| `alias_point` | `Point b = a;` → `Point& b = a;` → `a: (10, 2) …`, `a == b: true` | 자동 | — |
| `default_fraction` | `Fraction`의 `<=>`, `==`를 `auto operator<=>(const Fraction&) const = default;` 한 줄로 → `1/2 == 2/4: false`, `1/2 < 2/4: true`, `is equivalent: false`, `6/8 == 3/4: false` | 자동 | — |
| `remove_custom_equal` | `Fraction`의 `operator==`만 지움 → 컴파일 오류(`invalid operands` / `C2676`·`C2678`), `<` 줄은 빌드됨 | 자동 | — |

- 트랙 spec 행과 다른 점: 없음. 행의 비교(비교 연산자 6개 직접 쓰기 → `operator<=>` 기본 비교, 연산자 오버로딩의 기준)를 2–5단계가 다루고, 1단계는 행의 주제 "값 의미론"을 출력으로 보인다. 표준 타입의 이동 후 상태는 찍지 않는다(Assumption 9, 이 레슨은 이동을 쓰지 않음). `docs/cpp_evolution/` 페이지는 만들지 않는다(Assumption 8, `operator<=>` 페이지는 없어서 링크도 없음).
- 파일: 레슨 폴더 `lessons/tracks/oop_basics/value_semantics/`, `curriculum.toml`의 줄, `tags.toml`의 새 태그 `operator`(Assumption 7: 새 주제), `intro.md`·`intro.en.md` 트랙 설명에 "값 의미론과 연산자", 트랙 spec 상태 열(이것으로 7행 모두 `레슨 있음`). 새 유닛 없음, 링크 줄 없음.

## 체크리스트
항목마다 `근거:` 뒤에 명령과 결과(또는 절 이름)를 쓰고 `[x]`로 바꾼다.

- [x] **C1** 바뀐 파일이 레슨 경로의 범위(spec [090-13](/docs/specs/090_13_lesson_path.md) §2.1) 안에 있다. 근거: `git diff --stat main...` + 새 파일 → `lessons/tracks/oop_basics/value_semantics/` 5개, `lessons/curriculum.toml`(줄 1), `lessons/tags.toml`(태그 추가), `lessons/intro.md`·`intro.en.md`(트랙 목록), 트랙 spec 상태 열, `docs/agent_todo.md`, 이 checklist. 모두 §2.1 안
- [x] **C2** 설계 절이 트랙 spec 행(주제, 비교)과 맞고 다른 점이 적혀 있다. 트랙 spec을 고칠 일이면 멈췄다. 근거: 설계 절. 트랙 spec 변경 없음(상태 열만)
- [x] **C3** `lessons.py check`: ERROR 0, 이 레슨·유닛에 WARN 0(`[scaffold]` 포함). 근거: `py -3 tools/lessons.py check` → `0 error(s), 0 warning(s); 3 track(s), 24 lesson(s), 2 unit(s)`(리뷰 수정 뒤)
- [x] **C4** `lesson_<id>`가 `windows-x64-debug`와 `linux-x64-debug`에서 경고 없이 빌드된다. 근거: `build.py --preset windows-x64-debug --target lesson_value_semantics`(`--test --label lesson`이 빌드), `--preset linux-x64-debug --target lesson_value_semantics`(WSL, Clang 20.1.2) → 둘 다 빌드, 경고 없음(리뷰 수정 뒤 다시)
- [x] **C5** 두 OS의 출력이 같다(줄 끝 제외). 주소·시간·해시 없음. 근거: Windows 실행 출력과 WSL 실행 출력을 ``을 지우고 `diff` → 같음(`SAME_OUTPUT`, 리뷰 수정 뒤). 출력은 정수, 날짜, 분수, `true`/`false`뿐
- [x] **C6** `--label lesson`이 `windows-x64-debug`, `linux-x64-debug`, `linux-x64-asan`에서 통과한다(`lesson.<id>`, `lesson.<id>.exercises_verify`). 근거: `build.py --preset <p> --test --label lesson --report` → `windows-x64-debug` 48/48, `linux-x64-debug` 48/48, `linux-x64-asan` 48/48(report `out/test-reports/linux-x64-asan/20261117-155646`); `lesson.value_semantics`, `lesson.value_semantics.exercises_verify` Passed. 리뷰 수정(주석·문장만) 뒤 `windows-x64-debug` 다시 48/48
- [x] **C7** 자동 과제마다 답의 변경으로 두 컴파일러에서 통과한다. 관찰 과제는 이유가 설계 절에 있다. 근거: 연습 사본에 답의 변경을 하나씩 적용 → `tools/exercises.py check value_semantics --preset windows-x64-debug`(MSVC)와 WSL의 `--preset linux-x64-debug`(Clang)에서 `alias_point`, `default_fraction`, `remove_custom_equal` 모두 pass. 리뷰 수정 뒤 `default_fraction`, `remove_custom_equal`을 MSVC에서 다시 pass. 매번 `practice.py reset`, 원본 diff 없음. 관찰 과제 없음
- [x] **C8** README 두 판의 절, 과제, 코드 블록 수가 같고, "연습" 항목 수 = `exercises.toml` 과제 수. 근거: 두 판 모두 절 4, 코드 펜스 2(블록 1), 표 행 7, 연습 3 = `exercises.toml` 과제 3
- [x] **C9** 레슨 작성 안내([lessons/README.md](/lessons/README.md) "레슨 작성 안내")와 트랙 spec 공통 규칙을 따른다: 영어 출력, 두 언어 주석, UB를 돌리지 않음. 근거: 리뷰 절: 출력 영어, 주석은 한국어 줄 아래 영어 줄, UB 없음(`Fraction`의 곱셈은 작은 값만, 전제를 주석에 씀), 이동 후 상태 출력 없음, evolution 페이지 없음
- [x] **C10** fresh reviewer 한 번, 지적은 모두 고쳤거나 이유를 적고 남겼다. 근거: 리뷰 절: `cpp-reviewer` 한 번, must-fix 0, should-fix 2·nit 4 모두 고침
- [x] **C11** 목록 문서(트랙 spec 상태 열, `lesson_candidates.md`, 필요하면 `intro.md`·`intro.en.md`, 링크 줄)가 맞다. 근거: 트랙 spec `value_semantics` 행 `레슨 있음`(7행 모두 `레슨 있음`); `lesson_candidates.md`는 트랙 spec을 가리키기만 해서 변경 없음; `intro.md`·`intro.en.md` 트랙 설명에 값 의미론과 연산자 추가; 링크 줄 없음. `lint_docs.py` → C13
- [x] **C12** 후속은 KI로 등록했다. 근거: 없음
- [x] **C13** `lint_docs.py` exit 0. 근거: `py -3 .agent/scripts/lint_docs.py` → `0 error(s), 0 warning(s)`, exit 0

## 리뷰
| 리뷰어 | 질문 | 지적 | 처리 |
|---|---|---|---|
| `cpp-reviewer` | 코드·두 README가 기술적으로 틀리거나 입문자를 오도하거나 트랙 규칙을 어기는가; 기본 `<=>`와 다시 쓰기 규칙, `weak_ordering`, 2단계의 `std::sort`·`std::map` 문장, 인용한 진단, `[[nodiscard]]`와 hidden friend `+` | should-fix: (1) `OldDate`의 `<`는 여전히 strict weak ordering이라 "엉뚱한 결과"가 틀림(같은 달의 다른 날을 같은 것으로 다룸, map은 키 하나만), (2) "동등하지만 같지 않다"가 같은 단계의 `1/2 == 2/4: true`와 모순으로 읽힘. nit: "여섯이 서로 맞지 않음"(실은 `==`/`!=`와 나머지 넷), "같은 두 날짜"의 뜻, `remove_custom_equal`의 진단 문구가 두 줄·두 코드를 섞음, 큰 값의 곱셈 넘침 전제. 기본 `<=>`, 다시 쓰기 규칙, `weak_ordering` 변환, `[[nodiscard]]`, hidden friend `+`, 태그 충돌 없음은 맞음 | 모두 고침: 2단계를 "`<`, `<=`, `>`, `>=`는 같다, `==`, `!=`는 다르다"와 "`std::sort`·`std::map`은 `<`만 써서 같은 달의 다른 날을 같은 것으로, map에 11-18이 들어가지 않음"으로, 4단계에 `strong_ordering`의 "같다"(어디에 써도 바꿔 넣을 수 있음)와 이 레슨의 `==`(같은 값 = 동등)를 설명, "2단계와 같은 두 날짜", 진단을 "Clang `invalid operands to binary expression`, MSVC `C2676` 또는 `C2678`"로, `Fraction` 생성자 주석에 넘침 전제 |

## 후속
- 없음
