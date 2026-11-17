# Lesson checklist: 070-23 `smart_pointers`

레슨 작업 하나의 기록이다([spec.md](/.agent/rules/spec.md) §6). 이 파일을 `docs/tasks/feature_NNN-SS-<slug>/checklist.md`로 복사해 쓰고, `plan.md`, `testrecord.md`, `walkthrough.md`는 쓰지 않는다. `DONE`이 되려면 아래의 `- [ ]`가 하나도 남지 않아야 한다(문서 gate가 검사). 맞지 않는 항목은 지우지 않고 `- [x] N/A: <이유>`로 쓴다.

- Track spec: `/docs/specs/tracks/oop_basics.md` (approved 2026-11-17), 행: `smart_pointers`
- Branch: `feature/070-23-smart-pointers`

## 설계
lead가 정한다. 트랙 spec의 행(주제, 비교)과 공통 규칙 안에서.

| 단계 | 출력으로 보이는 것 |
|---|---|
| 1 | `unique_ptr` 단독 소유: `unique_ptr can be copied: false`, `std::move` 뒤 `next holds solo, alive widgets: 1`, 블록 끝의 `~Widget solo`, `alive widgets: 0` |
| 2 | 시그니처의 소유권: `makeWidget`(준다), `show(const Widget&)`(빌린다), `consume(std::unique_ptr<Widget>)`(가져간다) → `~Widget parcel`이 `back in main`보다 먼저 |
| 3 | `std::vector<std::unique_ptr<Widget>>`(`Widget`, `Gadget`): 가상 호출 `kind()`, `erase`가 지우는 원소(`~Widget a`), `std::move(crate.back())`로 꺼낸 원소는 남음, 원소 하나인 `clear()`와 `reset()` |
| 4 | `shared_ptr` 공유 소유: `use_count` 1 → 2 → 1, 마지막 소유자가 사라질 때 `~Widget shared`, 빈 `survivor`의 `use_count: 0` |
| 5 | `weak_ptr`로 끊는 순환: `Parent`가 `Child`를 `shared_ptr`로, `Child`가 `Parent`를 `weak_ptr`로. `parent use_count: 1, child use_count: 2`, `lock()`, 블록 끝의 `~Parent`, `~Child`, `parent expired: true`, `alive …: 0`. 남은 순환을 `watcher.lock()`과 `adopt(nullptr)`로 손으로 끊는 `if` 블록(원본에서는 돌지 않음), `alive at the end: 0` |

| 과제 id | 무엇을 바꾸나 | 자동 / 관찰 | 관찰이면 이유 |
|---|---|---|---|
| `copy_unique` | 1단계에 `auto copy = next;` → 컴파일 오류(`deleted` / `C2280`) | 자동 | — |
| `keep_shared` | 4단계 블록 안에 `survivor = first;` → `after the block, survivor use_count: 1`, `~Widget shared`가 `reset()` 때 | 자동 | — |
| `shared_cycle` | `Child`의 `std::weak_ptr<Parent>`를 `std::shared_ptr<Parent>`로 → `use_count` 2/2, 블록 끝에 소멸 줄 없음, `parent expired: false`, `alive …: 2`, 그 뒤 `breaking the cycle by hand`, `~Child`, `~Parent`, `alive at the end: 0` | 자동 | — |

- 트랙 spec 행과 다른 점: 없음. 행의 비교(날 포인터가 소유권을 숨김 → `unique_ptr`, `shared_ptr`/`weak_ptr`, `vector<unique_ptr<Base>>`)를 1–5단계가 다룬다. 날 포인터의 누수·이중 해제는 실행하지 않고 README 글로만(Assumption 4). 출력은 지정된 순서에만 기댄다: 원소 하나의 `erase`, 원소가 하나 남은 `clear()`, 지역 변수의 역순 소멸(Assumption 9). 표준 타입의 이동 후 상태는 찍지 않는다(Assumption 9): 이동한 `unique_ptr`가 `nullptr`라는 것은 README 글로만 쓰고, 출력은 `Widget::alive()`와 소멸 줄로 보인다(리뷰 지적으로 `owner == nullptr`, `made == nullptr` 출력을 뺌).
- 실제 메모리 누수도 돌리지 않는다(Assumption 4 "자원은 출력 줄과 카운터로"): `shared_cycle`이 만든 순환은 5단계 끝의 `if` 블록이 손으로 끊어서 과제를 적용한 사본도 누수 없이 끝난다(리뷰 지적으로 처음 설계의 "누수를 남기는 과제"를 바꿈). 순환이 스스로 풀리지 않는다는 것을 그 블록이 보여 준다.
- 파일: 레슨 폴더 `lessons/tracks/oop_basics/smart_pointers/`, `curriculum.toml`의 줄, `tags.toml`의 새 태그 `smart_pointer`(Assumption 7), `intro.md`·`intro.en.md` 트랙 설명에 "스마트 포인터", 트랙 spec 상태 열. 새 유닛 없음, 링크 줄 없음.

## 체크리스트
항목마다 `근거:` 뒤에 명령과 결과(또는 절 이름)를 쓰고 `[x]`로 바꾼다.

- [x] **C1** 바뀐 파일이 레슨 경로의 범위(spec [090-13](/docs/specs/090_13_lesson_path.md) §2.1) 안에 있다. 근거: `git diff --stat main...` + 새 파일 → `lessons/tracks/oop_basics/smart_pointers/` 5개, `lessons/curriculum.toml`(줄 1), `lessons/tags.toml`(태그 추가), `lessons/intro.md`·`intro.en.md`(트랙 목록), 트랙 spec 상태 열, `docs/agent_todo.md`, 이 checklist. 모두 §2.1 안
- [x] **C2** 설계 절이 트랙 spec 행(주제, 비교)과 맞고 다른 점이 적혀 있다. 트랙 spec을 고칠 일이면 멈췄다. 근거: 설계 절. 트랙 spec 변경 없음(상태 열만). 리뷰가 A4·A9에 걸린 두 곳은 트랙 spec을 고치지 않고 레슨을 규칙에 맞게 바꿈(설계 절 끝의 두 줄)
- [x] **C3** `lessons.py check`: ERROR 0, 이 레슨·유닛에 WARN 0(`[scaffold]` 포함). 근거: `py -3 tools/lessons.py check` → `0 error(s), 0 warning(s); 3 track(s), 23 lesson(s), 2 unit(s)`(리뷰 수정 뒤)
- [x] **C4** `lesson_<id>`가 `windows-x64-debug`와 `linux-x64-debug`에서 경고 없이 빌드된다. 근거: `build.py --preset windows-x64-debug --target lesson_smart_pointers`, `--preset linux-x64-debug --target lesson_smart_pointers`(WSL, Clang 20.1.2) → 둘 다 빌드, 경고 없음(리뷰 수정 뒤 다시)
- [x] **C5** 두 OS의 출력이 같다(줄 끝 제외). 주소·시간·해시 없음. 근거: Windows 실행 출력과 WSL 실행 출력을 ``을 지우고 `diff` → 같음(`SAME_OUTPUT`, 리뷰 수정 뒤). 출력은 이름, 정수, `true`/`false`뿐(주소·시간·해시 없음)
- [x] **C6** `--label lesson`이 `windows-x64-debug`, `linux-x64-debug`, `linux-x64-asan`에서 통과한다(`lesson.<id>`, `lesson.<id>.exercises_verify`). 근거: `build.py --preset <p> --test --label lesson --report`(리뷰 수정 뒤) → `windows-x64-debug` 46/46, `linux-x64-debug` 46/46, `linux-x64-asan` 46/46(report `out/test-reports/linux-x64-asan/20261117-154245`); `lesson.smart_pointers`, `lesson.smart_pointers.exercises_verify` Passed
- [x] **C7** 자동 과제마다 답의 변경으로 두 컴파일러에서 통과한다. 관찰 과제는 이유가 설계 절에 있다. 근거: 연습 사본에 답의 변경을 하나씩 적용 → `tools/exercises.py check smart_pointers --preset windows-x64-debug`(MSVC)와 WSL의 `--preset linux-x64-debug`(Clang)에서 `copy_unique`, `keep_shared`, `shared_cycle` 모두 pass(리뷰 수정 뒤 다시). `shared_cycle`은 `--preset linux-x64-asan`에서도 pass(누수 없음). 매번 `practice.py reset`, 원본 diff 없음. 관찰 과제 없음
- [x] **C8** README 두 판의 절, 과제, 코드 블록 수가 같고, "연습" 항목 수 = `exercises.toml` 과제 수. 근거: 두 판 모두 절 4, 코드 펜스 2(블록 1), 표 행 7, 연습 3 = `exercises.toml` 과제 3
- [x] **C9** 레슨 작성 안내([lessons/README.md](/lessons/README.md) "레슨 작성 안내")와 트랙 spec 공통 규칙을 따른다: 영어 출력, 두 언어 주석, UB를 돌리지 않음. 근거: 리뷰 절: 출력 영어, 주석은 한국어 줄 아래 영어 줄, UB·실제 누수를 돌리지 않음, 출력은 지정된 소멸 순서에만 기댐
- [x] **C10** fresh reviewer 한 번, 지적은 모두 고쳤거나 이유를 적고 남겼다. 근거: 리뷰 절: `cpp-reviewer` 한 번, must-fix 0, should-fix 2·nit 3 모두 고침
- [x] **C11** 목록 문서(트랙 spec 상태 열, `lesson_candidates.md`, 필요하면 `intro.md`·`intro.en.md`, 링크 줄)가 맞다. 근거: 트랙 spec `smart_pointers` 행 `레슨 있음`; `lesson_candidates.md`는 트랙 spec을 가리키기만 해서 변경 없음; `intro.md`·`intro.en.md` 트랙 설명에 스마트 포인터 추가; 링크 줄 없음. `lint_docs.py` → C13
- [x] **C12** 후속은 KI로 등록했다. 근거: 없음
- [x] **C13** `lint_docs.py` exit 0. 근거: `py -3 .agent/scripts/lint_docs.py` → `0 error(s), 0 warning(s)`, exit 0

## 리뷰
| 리뷰어 | 질문 | 지적 | 처리 |
|---|---|---|---|
| `cpp-reviewer` | 코드·두 README가 기술적으로 틀리거나 입문자를 오도하거나 트랙 규칙(UB, 지정되지 않은 동작에 기댄 출력, 영어 출력, 두 언어 주석, ko/en 일치)을 어기는가; 3단계 소멸 순서, 5단계 순서와 `use_count`, `shared_cycle`의 누수, 이동한 `unique_ptr`, 인용한 진단 | should-fix: (1) `shared_cycle`이 실제 메모리를 누수시켜 A4("자원은 출력 줄과 카운터로")와 맞지 않고 ASan preset에서는 실패할 것, (2) 이동한 `unique_ptr`의 상태(`owner == nullptr`, `made == nullptr`)를 찍어 A9("이동 후 상태는 레슨의 타입만")의 글자와 맞지 않음. nit: 값 매개변수의 소멸 시점 표현, `Gadget`이 바르게 지워진다는 문장을 받치는 출력 없음, 누수는 글로만이라는 첫 문단. 3단계·5단계 순서, 2/2 값, 진단 문구, 태그 충돌 없음은 맞음 | 트랙 spec을 고치지 않고 레슨을 규칙에 맞춤: (1) 5단계 끝에 남은 순환을 `watcher.lock()`과 `adopt(nullptr)`로 끊는 `if` 블록을 더해 과제 사본도 누수 없이 끝남(ASan에서 pass 확인), 과제 `expect`·답 갱신; (2) 두 출력을 빼고 `alive widgets: 1`과 `back in main`으로, `nullptr`는 README 글로만. nit 셋 모두 고침("호출이 끝날 때(그 문장이 끝나기 전)", `Gadget` 줄은 기반 `~Widget`이 찍고 가상 소멸자는 inheritance_virtual 3단계가 보인다고 씀, 첫 문단은 실제 누수가 없어져 그대로 맞음) |

## 후속
- 없음
