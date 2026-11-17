---
id: 070-20
title: 나머지 레슨의 연습 과제 정의 (essentials 12개, device_state_machine)
depends_on: [070-17, 070-18]
unblocks: []
approved: 2026-11-12
---

# Spec 070-20: 나머지 레슨의 연습 과제 정의 (essentials 12개, device_state_machine)

## 0. Assumptions (please review)
| # | Decision | Rejected alternative | Why |
|---|---|---|---|
| 1 | **범위**: `exercises.toml`이 아직 없는 레슨 13개에 070-17 형식의 과제 정의를 붙인다. essentials 12개(`02_format_text`, `03_const_correctness`, `05_source_location`, `06_concepts`, `07_ranges_views`, `08_variant_visit`, `09_chrono_time`, `10_filesystem_paths`, `12_log_recovery`, `13_lock_free_buffer`, `14_span_timing`, `15_modules`)와 `02_patterns/01_device_state_machine`. README의 "연습" 항목 39개가 대상이다(Assumption 4의 쪼갬을 더하면 과제는 41개). `lambda_capture`, `error_expected`, `testing`(070-17)과 `thread_and_log`(070-18)는 이미 있다 | 레슨 내용(새 레슨, `main.cpp` 변경)도 이 작업에서 | 이 작업의 검토 범위는 `exercises.toml`이다(Assumption 5) |
| 2 | **자동/관찰은 두 컴파일러의 결과로 정한다.** 웹(Clang)과 로컬(MSVC)에서 같은 결과를 내는 과제는 자동, 컴파일러·호스트에 따라 결과가 다르거나 로컬 도구(ASan, TSan, 리포트)가 필요하거나 수치를 비교해야 하는 과제는 관찰 과제로 둔다. 컴파일러 문구만 다르면 `build_expect`에 `\|`로 둘 다 적는다. DEV에서 두 컴파일러로 확인해 초안의 분류를 바꿀 수 있고, 바뀌면 testrecord와 이 표에 적는다 | 한 컴파일러에서만 자동 | 070-17 Assumption 14와 같다. 로컬 Windows 사용자가 같은 과제를 풀고도 통과하지 못하면 안 된다 |
| 3 | **새 규칙을 더하지 않는다.** 070-17의 `build`, `build_expect`, `exit`, `expect`, `forbid`, `source`만 쓴다. 컴파일러마다 빌드 성공/실패가 갈리는 과제(`build = "any"` 같은 규칙이 있으면 자동이 되는 것)는 관찰로 둔다 | `build = "any"`나 `platform` 조건 규칙 더하기 | 규칙이 늘면 `tools/exercises.py`, 문서, 테스트가 함께 늘고, 그 만큼의 가치가 있는 과제는 `const_correctness` 2번 하나뿐이다. 필요해지면 KI |
| 4 | **쪼개기**: 한 항목이 두 번 확인을 요구하면 070-17의 규칙대로 id 끝에 `_a`, `_b`를 붙인다. `format_text` 3(`println`으로 다시 쓰기 / `bad_pattern` 컴파일 오류), `modules` 3(`import` 지우기 / `export import`)가 해당한다 | 한 과제에 규칙을 모두 | `build = "fail"`과 `build = "ok"`는 한 과제에 함께 둘 수 없다 |
| 5 | **레슨 소스는 바꾸지 않는다.** 과제는 지금의 출력과 `source` 규칙으로 표현한다. 규칙으로 표현하려고 레슨에 출력 줄을 더해야 하는 과제는 관찰 과제로 둔다. 레슨 코드가 바뀌면 그 레슨의 과제 정규식도 같이 바뀌므로 레슨 작업이 맡는다 | 과제에 맞춰 `main.cpp`에 출력 줄 추가 | 이 작업의 검토 범위는 `exercises.toml`이다. 출력 줄이 바뀌면 다른 레슨의 evolution 페이지·README 표와의 일치도 다시 봐야 한다 |
| 6 | **README는 두 곳만 고친다.** (a) `14_span_timing` 연습 2는 `lesson.toml`의 `[run]`에 `build = "debug"`를 넣게 하는데, 070-16부터 연습 사본의 `lesson.toml`은 읽기 전용이라 연습 모드에서 풀 수 없다. 이 항목을 관찰 과제로 두고 README 문장에 "원본 편집 모드(또는 로컬)에서 하고 `git restore`로 되돌린다"를 더한다. (b) `device_state_machine`의 연습 절 제목이 `## 4. 연습 과제`라 `lessons.py check`가 항목 수를 세는지 DEV에서 확인하고, 세지 못하면 `## 연습`으로 바꾼다 | 연습 2를 연습 모드에서 풀 수 있는 다른 과제로 교체 | (a) 과제의 뜻("Debug 시간으로 성능을 판단하지 말라")은 그대로 두는 편이 읽는 사람에게 단순하다. 다른 것은 README를 안 고친다 |
| 7 | **힌트·해설은 두 언어**로 쓴다(`hint`, `hint_en`, `answer`, `answer_en`). 힌트는 답의 코드를 보이지 않고 어디를 볼지만, 해설은 고친 코드와 이유와 "되돌립니다"를 쓴다. 관찰 과제도 해설을 쓴다(무엇을 보면 되는지, 예상 출력) | 해설은 자동 과제만 | 070-17 형식이 관찰 과제에도 힌트·해설을 허용한다. 서술형 질문에 답을 보여 주지 않으면 스스로 확인할 수 없다 |
| 8 | **풀 수 있음의 검증**: 모든 자동 과제를 해설의 코드대로 연습 공간에서 고쳐 `tools/exercises.py check <id> --preset <p>`로 통과를 확인한다(Windows `windows-x64-debug`, Linux/WSL `linux-x64-debug`). 결과를 testrecord에 과제마다 한 줄로 남긴다. 해답 파일은 저장소에 두지 않는다(070-17 Assumption 6) | 해답을 `solutions/`에 두고 자동 검증 | 070-17이 이미 정한 방침이다. 과제 41개 중 자동은 28개라 손으로 돌리는 비용이 감당할 만하다 |
| 9 | **자동 과제가 프로그램을 `abort()`로 끝내게 하지 않는다**(`build = "ok"`에 `exit = "nonzero"`를 쓰는 과제가 Windows Debug에서 CRT 대화상자를 띄움, KI-050). 프로그램이 비정상 종료해야 하는 과제는 관찰로 둔다 | 자동 + `exit = "nonzero"` | 로컬 Windows Debug에서 대화상자가 떠 확인이 끝나지 않는다. KI-050은 사용자 결정 대기 |
| 10 | **일 나누기**: DEV에서 레슨 13개를 4묶음(문법: `format_text`, `const_correctness`, `source_location`, `concepts` / 표준 라이브러리: `ranges_views`, `variant_visit`, `chrono_time`, `filesystem_paths` / 로그·성능: `log_recovery`, `lock_free_buffer`, `span_timing` / 모듈·패턴: `modules`, `device_state_machine`)으로 나눠 위임하고 묶음마다 교차 리뷰한다([delegation.md](/.agent/rules/delegation.md)). 이 항목은 초안의 제안이고, 최종 단위표는 plan.md에 쓴다 | 레슨마다 하나 | 레슨 하나의 `exercises.toml`은 200–300줄이라 13번을 나누면 오버헤드가 크다 |

## 1. Objective
070-17이 만든 과제 확인(자동 규칙, 힌트·해설, 진행 기록)이 지금은 레슨 5개에만 걸려 있다. 나머지 레슨 13개의 README 연습 39항목에 같은 형식의 과제 정의를 붙여, 어떤 레슨을 열어도 연습 탭이 동작하고 진행 표시(`2/3`)가 보이게 한다. 새 과제 규칙·도구·화면은 만들지 않는다.

## 2. Requirement Details

### 2.1 Public API Surface
C++ API 변경 없음. 도구·서버·프런트엔드 변경 없음(070-17의 것을 쓴다).

### 2.2 Internal Implementation
| 파일 | 바꾸는 것 |
|---|---|
| `lessons/tracks/01_essentials/{02,03,05,06,07,08,09,10,12,13,14,15}_*/exercises.toml` (새 12개) | §2.4 표대로 |
| `lessons/tracks/02_patterns/01_device_state_machine/exercises.toml` (새) | §2.4 표대로 |
| `lessons/tracks/01_essentials/14_span_timing/README.md`, `README.en.md` | 연습 2의 문장(Assumption 6a) |
| `lessons/tracks/02_patterns/01_device_state_machine/README.md`(필요하면) | 연습 절 제목(Assumption 6b) |

### 2.3 Platform Specifics
- 빌드 로그 정규식은 Clang(웹, `linux-x64-*`)과 MSVC(`windows-x64-*`) 문구를 `|`로 함께 쓴다(Assumption 2).
- 출력 정규식은 두 OS에서 같은 줄만 쓴다. 경로·시간이 든 줄은 쓰지 않는다(070-17 §2.3).
- `chrono_time` 3, `filesystem_paths` 3, `modules` 3_a처럼 호스트마다 결과가 다른 과제는 관찰이다.

### 2.4 과제 정의 (초안 — 정규식과 문구는 DEV에서 실제 출력·실제 컴파일러 문구로 확정)
"자동 규칙"의 `source`는 연습 사본 파일 검사다. 모든 자동 과제는 070-17 Assumption 5에 따라 원본이 통과하지 않아야 한다.

| 레슨 | # (id 초안) | 종류 | 규칙 |
|---|---|---|---|
| `format_text` | 1 `drop_format_arg` | 자동 | `build = "fail"`, `build_expect`(consteval/format string 문구, Clang \| MSVC)만 쓴다. 인자는 여러 줄에 걸친 호출에서 지워지므로 줄 단위 `source` 규칙을 쓰지 않는다. 인자를 하나 더 넣는 뒷부분은 컴파일되므로 해설로만 |
| | 2 `polar_formatter` | 자동 | `source.has`: `{:p}` 호출, `std::hypot`, `std::atan2`; `build = "ok"`, `exit = 0` |
| | 3_a `use_println` | 자동 | `source.lacks`: `std::cout\s*<<\s*formatRow\(row\)`와 `std::cout\s*<<\s*std::format\("\{:<10\}`; `build = "ok"`. 파일 전체의 `std::println`은 7단계에 이미 있어 `has`로 쓸 수 없다 |
| | 3_b `println_bad_pattern` | 자동 | `build = "fail"`, `source.has`: `std::println\(bad_pattern`, `build_expect` |
| `const_correctness` | 1 `call_increment_on_const` | 자동 | `build = "fail"`, `build_expect`(`const`/`C2662`), `source.has`: 풀린 `c.increment();` |
| | 2 `const_return_int` | 관찰 | Clang은 `-Wignored-qualifiers` + `-Werror`로 실패, MSVC는 DEV에서 확인(실패하면 자동으로 올림, Assumption 2·3) |
| | 3 `get_returns_value` | 자동 | `build = "fail"`, `build_expect`(`rvalue`/`non-const lvalue`/`C2106`), `source.has`: `b.get(1) = 21;` |
| `source_location` | 1 `warn_without_loc` | 자동 | `source.lacks`: `void warn\(.*source_location`, `source.has`: `logHere\(std::format\("warning: \{\}", msg\)\)\s*;`(원본은 뒤에 `, loc`가 있음); `build = "ok"` |
| | 2 `type_identity` | 자동 | `build = "fail"`, `build_expect`(deduce/`C2672`), `source.has`: `Here<Args\.\.\.>` |
| | 3 `format_arg_mismatch` | 자동 | `build = "fail"`, `source.has`: 두 호출 줄, `build_expect`(format string/`consteval`) |
| `concepts` | 1 `unconstrained_calls` | 자동 | `build = "fail"`, `source.has`: `printShape\(42\)`, `twiceSfinae\("x"\)`, `build_expect`(`constraints not satisfied`/`C7602`/`no matching`) |
| | 2 `printable_concept` | 자동 | `source.has`: `concept\s+Printable`, `static_assert\(Printable<Circle>\)`; `build = "ok"` |
| | 3 `fixed_ring_six` | 자동 | `build = "fail"`, `source.has`: `FixedRing<6>`, `build_expect` |
| `ranges_views` | 1 `drop_take` | 자동 | `source.lacks`: `views::take\(2\)`; `build = "ok"`. 호출 횟수는 해설로만 |
| | 2 `find_on_temporary` | 자동 | `build = "fail"`, `source.has`: `ranges::find\(makeNumbers\(\)`, `build_expect`(`dangling`) |
| | 3 `ranges_to_msvc` | 관찰 | `std::ranges::to`·`std::format("{}", view)`는 MSVC에서만 도는 부분이 있음(원문) |
| `variant_visit` | 1 `add_triangle` | 자동 | `build = "fail"`, `source.has`: `struct Triangle`, `std::variant<Circle, Rect, Triangle>`, `build_expect`(no matching/`C2672`) |
| | 2 `find_state_hpp` | 관찰 | 다른 파일을 읽는 과제 |
| | 3 `virtual_perimeter` | 관찰 | 몇 곳을 고치는지 세는 과제(수치) |
| `chrono_time` | 1 `seconds_from_ms` | 자동 | `build = "fail"`, `source.has`: `std::chrono::seconds s = 1500ms;`, `build_expect`(no viable conversion/`C2440`) |
| | 2 `ambiguous_local_time` | 자동 | `source.has`: `ambiguous_local_time`, `choose::earliest`, `choose::latest`; `build = "ok"`, `exit = 0` |
| | 3 `parse_invalid_date` | 관찰 | libstdc++와 MSVC의 `fail()` 결과가 다름(원문) |
| `filesystem_paths` | 1 `unsorted_listing` | 관찰 | 순서가 같은지 여러 번 실행해 보는 과제 |
| | 2 `copy_recursive` | 자동 | `source.has`: `copy_options::recursive`; `build = "ok"`, `exit = 0` |
| | 3 `raw_file_time` | 관찰 | 두 호스트의 숫자를 비교 |
| `log_recovery` | 1 `quick_exit` | 자동 | `source.has`: `std::quick_exit\(0\)`, `source.lacks`: `std::_Exit\(0\)`. 두 번째 실행은 해설 |
| | 2 `no_mapped_dir` | 자동 | `source.lacks`: `^\s*\.mappedDir\s*=`(다른 줄의 주석에도 이름이 있음); `build = "ok"` |
| | 3 `crash_dump_abort` | 관찰 | `std::abort()` + 로컬 도구(`read_dump.py`), Windows Debug 대화상자(Assumption 9) |
| `lock_free_buffer` | 1 `relaxed_tsan` | 관찰 | `linux-x64-tsan` 로컬 preset |
| | 2 `cached_head` | 관찰 | 처리량 수치 비교 |
| | 3 `small_capacity` | 자동 | `source.has`: `kCapacity\s*=\s*8`; `exit = 0`; 출력의 `verified` 줄은 DEV에서 정규식 확정(없으면 `source`만) |
| `span_timing` | 1 `no_reserve` | 자동 | `source.has`: `//\s*values\.reserve\(kElements\)`. "이전 대비"는 Timings 탭의 몫이라 stdout으로는 못 봄 |
| | 2 `debug_build_profile` | 관찰 | 연습 사본의 `lesson.toml`은 읽기 전용(Assumption 6a) |
| | 3 `span_in_hot_loop` | 자동 | `source.has`: `lookUp` 안 `for`의 span 선언(DEV에서 정규식 확정); `build = "ok"` |
| `modules` | 1 `call_detail` | 자동 | `build = "fail"`, `source.has`: `detail::clampSide\(5\.0\)`, `build_expect`: MSVC `C2039` \| Clang `must be imported from module` (README 원문) |
| | 2 `rebuild_scope` | 관찰 | 빌드 두 번의 로그 비교 |
| | 3_a `remove_import` | 관찰 | Clang은 실패, MSVC는 `import` 이름이 새어 나가 성공(원문) — 컴파일러마다 달라 관찰 |
| | 3_b `export_import` | 자동 | `source.has`: `export\s+import\s+atugcc\.core;`(`geometry.cppm`), `source.lacks`: `main.cpp`의 `import atugcc\.core;`; `build = "ok"` |
| `device_state_machine` | 1 `emergency_state` | 자동 | `source.has`: `transition\(state::(Abort\|Emergency)State\{\}\)`; `build = "ok"`, `exit = 0` |
| | 2 `rejected_transition` | 자동 | `source.lacks`: `transition\(state::StandbyState\{\}\)`(원본은 `tick == 1`에서 Standby, `tick == 2`에서 Run으로 전이하므로 `RunState`는 `has`로 쓸 수 없다); `expect`: `STANDBY transition failed`(원본 코드가 실패하면 찍는 Error 로그. Logger가 stdout에 쓰는지는 DEV에서 확인, 아니면 관찰로) |
| | 3 `diagram_backends` | 자동 | `source.has`: `DiagramBackend::PlantUML`, `DiagramBackend::D2`; `build = "ok"`, `exit = 0` |

집계(초안): 과제 41개 = 자동 28, 관찰 13(`const_correctness` 2, `ranges_views` 3, `variant_visit` 2·3, `chrono_time` 3, `filesystem_paths` 1·3, `log_recovery` 3, `lock_free_buffer` 1·2, `span_timing` 2, `modules` 2·3_a). DEV의 두 컴파일러 확인으로 분류가 바뀌면 이 표와 숫자를 고친다.

## 3. C++ Standard Evolution
N/A. 레슨 내용을 바꾸지 않는다.

## 4. Edge Cases
- [x] Thread safety / memory ordering — N/A. `lock_free_buffer`의 `relaxed` 과제는 TSan이 필요해 관찰이다(자동 확인 없음).
- [x] Resource lifetime — 연습 Run 하나의 빌드·출력·종료 코드와 사본 파일만 본다(070-17). `source` 규칙은 사본 파일을 읽을 뿐이다.
- [x] Platform differences — Assumption 2·3. `build_expect`는 두 컴파일러 문구를 `|`로 쓴다.
- [x] Template instantiation / concept constraints — N/A (레슨 소스를 바꾸지 않음).
- [x] ODR — N/A.
- [x] Undefined behaviour — Assumption 9: 자동 과제는 프로그램을 `abort()`로 끝내지 않는다.
- [x] 정규식 과적합: 고친 줄이 *있는지* 보는 `source.has`는 주석 처리한 같은 줄에도 맞을 수 있다. 줄 머리 공백 뒤에서 시작하는 패턴(`^\s*…`)을 쓰고, 주석 처리가 정답인 과제(`span_timing` 1)만 `//`를 포함한다.
- [x] 원본이 통과하는 정규식(070-17 Assumption 5): 자동 과제 28개 모두 `exercises_verify`가 걸러낸다(AC-2).
- [x] `-Werror`: 컴파일 오류를 보는 과제의 변경은 경고 때문에 실패하는 경우가 있다(`const_correctness` 2). 두 컴파일러에서 확인해 분류한다.
- [x] 영어 필드 누락은 `lessons.py check` WARN이다(AC-1).

## 5. Acceptance Criteria
| ID | Criterion | Verified by |
|---|---|---|
| AC-1 | 13개 레슨에 `exercises.toml`이 있고 `py -3 tools/lessons.py check`가 ERROR·WARN 0이다. 레슨마다 README "연습" 항목 수와 과제 수(하위 과제는 하나로)가 같다 | 명령 출력 |
| AC-2 | `build.py --preset windows-x64-debug --test --label lesson`와 `linux-x64-debug`에서 `lesson.<id>.exercises_verify` 13개가 통과한다(원본이 어떤 자동 과제도 통과하지 않음) | 명령 출력, testrecord |
| AC-3 | 모든 자동 과제를 해설의 코드대로 연습 공간에서 고치면 `tools/exercises.py check <id>`가 그 과제를 통과로 보고한다. 두 preset(`windows-x64-debug`, `linux-x64-debug`)에서 확인하고, 결과를 과제마다 한 줄로 기록한다. 한쪽에서만 통과하는 과제는 관찰로 내리고 §2.4를 고친다 | testrecord의 과제별 표 |
| AC-4 | 해설대로 고친 뒤 되돌리면(`practice.py reset`) 진행 기록은 남고 원본은 변하지 않는다(`git status --porcelain`이 비어 있음) | 명령 출력 |
| AC-5 | 관찰 과제는 모두 힌트와 해설이 있고, 자동 과제는 `fail_hint`가 있다. 영어판(`*_en`)이 모두 채워졌다 | `lessons.py check`, 읽기 확인 |
| AC-6 | README 두 곳(Assumption 6)이 고쳐졌고, `span_timing` 연습 2의 문장이 연습 모드에서 풀 수 없다는 사실과 어긋나지 않는다. 영어판이 한국어판과 연습 수·코드 블록 수가 같다 | 읽기 확인, 070-03의 비교 스크립트 |
| AC-7 | 플레이그라운드에서 레슨 2개(자동과 관찰이 섞인 것 하나, 자동뿐인 것 하나)를 열면 연습 탭에 과제 목록이 보이고, 자동 과제 하나를 풀면 `✓`와 `n/m`이 바뀐다 | 헤드리스 브라우저 확인 기록 |
| AC-8 | 전체 suite가 두 preset에서 통과하고 `lint_docs.py`가 exit 0이다 | 명령 출력 |

## 6. Out of Scope
- 새 과제 규칙(`build = "any"`, 플랫폼 조건) — 필요해지면 KI
- 해답 파일의 자동 검증 — 070-17 Assumption 6
- 레슨 `main.cpp`·출력의 변경 — 각 레슨 작업(Assumption 5)
- `device_state_machine` README를 essentials 형식으로 다시 쓰기 — 070-04 / 021–024
- Windows Debug `abort()` 대화상자 — KI-050 (사용자 결정 대기)

## 7. Dependencies & Backends
없음.

## 8. Documentation Updates
| Document | Section | Change |
|---|---|---|
| `lessons/tracks/**/exercises.toml` (13개) | 전체 | 새로 씀(§2.4) |
| `lessons/tracks/01_essentials/14_span_timing/README.md`, `README.en.md` | 연습 2 | Assumption 6a |
| [`lessons/README.md`](/lessons/README.md) | "연습 과제 정의" | 예시·문구가 "시범 레슨"만 가정하면 고침. 관찰 과제의 기준(Assumption 2)을 한 문장 |
| [`docs/lesson_candidates.md`](/docs/lesson_candidates.md) | 머리글 | "새 레슨은 ... 과제를 정의한다" 문장과 일치 확인 |
| [`docs/agent_todo.md`](/docs/agent_todo.md) | 070-20 줄 | 상태 |

## 9. Technical Constraints
- Compiler: MSVC (VS 2026) / Clang 20 with libstdc++ 14 (Linux)
- CMake: 4.0+
- C++ Standard: C++23 (C++20 minimum)
- Python 3 (`tools/exercises.py`는 표준 라이브러리만)

## 10. Context & References
- [070-17 스펙](/docs/specs/070_17_exercise_check.md)(과제 정의 형식, 규칙, 원본 통과 검사)
- [070-18 스펙](/docs/specs/070_18_thread_and_log_lesson.md)(레슨 하나의 과제 정의 예)
- [`lessons/README.md`](/lessons/README.md) "연습 과제 정의"
- 예: [`04_error_expected/exercises.toml`](/lessons/tracks/essentials/error_expected/exercises.toml), [`01_lambda_capture/exercises.toml`](/lessons/tracks/essentials/lambda_capture/exercises.toml)
- [`tools/exercises.py`](/tools/exercises.py), [`tools/lessons.py`](/tools/lessons.py)
- [070-16 스펙](/docs/specs/070_16_practice_workspace.md)(연습 사본, 매니페스트 읽기 전용)
- [KI-050](/docs/known_issues.md)

## 11. Implementation Plan
- [ ] Step 1: 묶음 1(문법 4개) — `exercises.toml`, 두 컴파일러 문구 확인, 풀이 확인
- [ ] Step 2: 묶음 2(표준 라이브러리 4개)
- [ ] Step 3: 묶음 3(로그·성능 3개) + `span_timing` README 두 판
- [ ] Step 4: 묶음 4(`modules`, `device_state_machine`)
- [ ] Step 5: 묶음마다 교차 리뷰, 분류가 바뀐 과제를 §2.4에 반영
- [ ] Step 6: `lessons/README.md` 문구, 플레이그라운드 확인, 문서 게이트

## 12. Verification Plan
- [ ] `py -3 tools/lessons.py check` (ERROR·WARN 0)
- [ ] `py -3 .agent/scripts/build.py --preset windows-x64-debug --test --label lesson`, `--preset linux-x64-debug`
- [ ] 자동 과제마다 `py -3 tools/exercises.py check <id> --preset <p>`로 풀이 확인 후 `practice.py reset`
- [ ] 헤드리스 브라우저로 AC-7
- [ ] `py -3 .agent/scripts/lint_docs.py` exit 0
- [ ] 모든 AC 행의 증거가 `testrecord.md`에

## History / Amendments
- 2026-11-12: 초안
- 2026-11-12: 승인(사용자). 승인 전 검토에서 레슨 소스와 대조해 정규식 대상 5곳을 고침(`format_text` 1·3_a, `source_location` 1, `log_recovery` 2, `device_state_machine` 2)
