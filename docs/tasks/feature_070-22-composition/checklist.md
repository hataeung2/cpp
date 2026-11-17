# Lesson checklist: 070-22 `composition`

레슨 작업 하나의 기록이다([spec.md](/.agent/rules/spec.md) §6). 이 파일을 `docs/tasks/feature_NNN-SS-<slug>/checklist.md`로 복사해 쓰고, `plan.md`, `testrecord.md`, `walkthrough.md`는 쓰지 않는다. `DONE`이 되려면 아래의 `- [ ]`가 하나도 남지 않아야 한다(문서 gate가 검사). 맞지 않는 항목은 지우지 않고 `- [x] N/A: <이유>`로 쓴다.

- Track spec: `/docs/specs/tracks/oop_basics.md` (approved 2026-11-17), 행: `composition`
- Branch: `feature/070-22-composition`

## 설계
lead가 정한다. 트랙 spec의 행(주제, 비교)과 공통 규칙 안에서.

| 단계 | 출력으로 보이는 것 |
|---|---|
| 1 | `InheritedStack : public std::vector<int>`: `insert(begin(), 99)`가 빌드되고 꺼내는 순서가 `3 2 1 99`(스택의 약속이 바깥에서 깨짐). `std::vector<int>`의 가상 소멸자 `false`(UB는 실행하지 않고 특성으로만) |
| 2 | 합성한 `Stack`(멤버 `std::vector<int>`, 위임): 꺼내는 순서 `3 2 1`, `is_base_of_v`가 `InheritedStack` `true`, `Stack` `false` |
| 3 | 위임과 has-a 수명: `Car`가 `Engine`을 갖고 `start()`를 맡김. `Engine built`, `Car built`, `Car::start …`, `Engine::start`, `~Car`, `~Engine` |
| 4 | LSP 위반: `broken::Square : broken::Rectangle`, `stretch(Rectangle&)`가 넓이 20을 기대, 직사각형 `5 x 4, area 20`, 정사각형 `4 x 4, area 16`, `still a square: true` |
| 5 | 바른 방식: `fixed::Rectangle`, `fixed::Square`가 서로 상속하지 않고 `Shape`(넓이, 이름)만 나눔. `area 20`, `area 16`, `fixed::Square is a fixed::Rectangle: false` |

| 과제 id | 무엇을 바꾸나 | 자동 / 관찰 | 관찰이면 이유 |
|---|---|---|---|
| `composed_insert` | 2단계에 `stack.insert(stack.begin(), 99);`를 더함 → 컴파일 오류(`no member named` / `C2039`) | 자동 | — |
| `private_inherit` | `InheritedStack`을 `private` 상속으로 → 1단계의 `insert`, `begin`, `empty`가 컴파일 오류(`private` / `C2247`) | 자동 | — |
| `square_height` | `broken::Square`의 `setHeight` 오버라이드를 지움 → `square: 5 x 4, area 20`, `still a square: false` | 자동 | — |

- 트랙 spec 행과 다른 점: 없음. 행의 두 비교(코드 재사용을 위한 상속 → 합성과 위임, `Square : Rectangle`의 LSP 위반)를 1–2단계와 4–5단계가 다루고, 3단계는 위임과 has-a 수명을 출력으로 보인다(Assumption 3). private 상속은 연습 2에서 "합성이 더 단순한 대안"으로만 다룬다(다중·가상 상속은 다루지 않음, §5).
- 파일: 레슨 폴더 `lessons/tracks/oop_basics/composition/`, `curriculum.toml`의 줄, `tags.toml`의 새 태그 `composition`(Assumption 7: 새 주제), `intro.md`·`intro.en.md`의 트랙 설명에 "합성", 트랙 spec 상태 열. 새 유닛 없음, 다른 레슨의 링크 줄 없음(트랙의 레슨들은 "앞 레슨" 링크만 둔다).

## 체크리스트
항목마다 `근거:` 뒤에 명령과 결과(또는 절 이름)를 쓰고 `[x]`로 바꾼다.

- [x] **C1** 바뀐 파일이 레슨 경로의 범위(spec [090-13](/docs/specs/090_13_lesson_path.md) §2.1) 안에 있다. 근거: `git diff --stat main...` + 새 파일 → `lessons/tracks/oop_basics/composition/` 5개, `lessons/curriculum.toml`(줄 1), `lessons/tags.toml`(태그 추가), `lessons/intro.md`·`intro.en.md`(트랙 목록), 트랙 spec 상태 열, `docs/agent_todo.md`, 이 checklist. 모두 §2.1 안
- [x] **C2** 설계 절이 트랙 spec 행(주제, 비교)과 맞고 다른 점이 적혀 있다. 트랙 spec을 고칠 일이면 멈췄다. 근거: 설계 절. 트랙 spec 변경 없음(상태 열만)
- [x] **C3** `lessons.py check`: ERROR 0, 이 레슨·유닛에 WARN 0(`[scaffold]` 포함). 근거: `py -3 tools/lessons.py check` → `0 error(s), 0 warning(s); 3 track(s), 22 lesson(s), 2 unit(s)`(리뷰 수정 뒤 다시 실행)
- [x] **C4** `lesson_<id>`가 `windows-x64-debug`와 `linux-x64-debug`에서 경고 없이 빌드된다. 근거: `build.py --preset windows-x64-debug --target lesson_composition`, `--preset linux-x64-debug --target lesson_composition`(WSL, Clang 20.1.2) → 둘 다 빌드, 경고 없음
- [x] **C5** 두 OS의 출력이 같다(줄 끝 제외). 주소·시간·해시 없음. 근거: Windows 실행 출력과 WSL 실행 출력을 ``을 지우고 `diff` → 같음(`SAME_OUTPUT`). 출력은 정수, `true`/`false`, 고정 문자열뿐
- [x] **C6** `--label lesson`이 `windows-x64-debug`, `linux-x64-debug`, `linux-x64-asan`에서 통과한다(`lesson.<id>`, `lesson.<id>.exercises_verify`). 근거: `build.py --preset <p> --test --label lesson --report` → `windows-x64-debug` 44/44, `linux-x64-debug` 44/44, `linux-x64-asan` 44/44(report `out/test-reports/linux-x64-asan/20261117-145254`); `lesson.composition`, `lesson.composition.exercises_verify` Passed. 리뷰 수정(문장만) 뒤 `windows-x64-debug` 다시 44/44
- [x] **C7** 자동 과제마다 답의 변경으로 두 컴파일러에서 통과한다. 관찰 과제는 이유가 설계 절에 있다. 근거: 연습 사본에 답의 변경을 하나씩 적용 → `tools/exercises.py check composition --preset windows-x64-debug`(MSVC)와 WSL의 `--preset linux-x64-debug`(Clang)에서 `composed_insert`, `private_inherit`, `square_height` 모두 pass, 다른 두 과제는 fail(서로 섞이지 않음). 매번 `practice.py reset`. 관찰 과제 없음
- [x] **C8** README 두 판의 절, 과제, 코드 블록 수가 같고, "연습" 항목 수 = `exercises.toml` 과제 수. 근거: 두 판 모두 절 4, 코드 펜스 2(블록 1), 표 행 5, 연습 3 = `exercises.toml` 과제 3
- [x] **C9** 레슨 작성 안내([lessons/README.md](/lessons/README.md) "레슨 작성 안내")와 트랙 spec 공통 규칙을 따른다: 영어 출력, 두 언어 주석, UB를 돌리지 않음. 근거: 리뷰 절: 출력 영어, 주석은 한국어 줄 아래 영어 줄, UB는 실행하지 않음(`std::vector`의 가상 소멸자는 특성으로만)
- [x] **C10** fresh reviewer 한 번, 지적은 모두 고쳤거나 이유를 적고 남겼다. 근거: 리뷰 절: `cpp-reviewer` 한 번, must-fix 0, should-fix 2·nit 4 모두 고침
- [x] **C11** 목록 문서(트랙 spec 상태 열, `lesson_candidates.md`, 필요하면 `intro.md`·`intro.en.md`, 링크 줄)가 맞다. 근거: 트랙 spec `composition` 행 `레슨 있음`; `lesson_candidates.md`는 트랙 spec을 가리키기만 해서 변경 없음; `intro.md`·`intro.en.md` 트랙 설명에 합성 추가; 링크 줄 없음(트랙 관례가 "앞 레슨" 링크뿐). `lint_docs.py` → C13
- [x] **C12** 후속은 KI로 등록했다. 근거: 없음
- [x] **C13** `lint_docs.py` exit 0. 근거: `py -3 .agent/scripts/lint_docs.py` → `0 error(s), 0 warning(s)`, exit 0

## 리뷰
| 리뷰어 | 질문 | 지적 | 처리 |
|---|---|---|---|
| `cpp-reviewer` | 코드·두 README가 기술적으로 틀리거나 입문자를 오도하거나 트랙 규칙(UB, 영어 출력, 두 언어 주석, ko/en 일치)을 어기는가; 3단계 수명, 4·5단계 LSP, private 상속 답, 5단계 "컴파일되지 않는다" 문장 | should-fix: (1) private 상속 답이 `using …::empty;`를 둘 곳(`public:`)을 말하지 않음, (2) 5단계 문장이 레슨에 없는 코드를 근거로 함. nit: "모두 숨긴다"가 부정확, "수명이 묶이는 것이 has-a"가 합성에만 맞음, en "just to write"가 ko와 다름, `composed_insert` 힌트의 `insert`/`begin` 질문에 답이 없음. 기술 오류·UB 없음 | 6개 모두 고침: `public:` 아래를 명시, 5단계를 "`fixed::Rectangle&`를 받는 함수에 `fixed::Square`를 넘기면 컴파일 오류"로, "public 함수를 private 멤버로 만든다", "멤버로 갖는 has-a(합성)", "to implement … with it", 힌트의 질문 삭제 |

## 후속
- 없음
