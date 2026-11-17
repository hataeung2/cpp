# Plan 070-27: 레슨·유닛 뼈대 생성 (`lessons.py new`, `new-unit`)

Spec: [070_27_lesson_scaffold.md](/docs/specs/070_27_lesson_scaffold.md) (approved 2026-11-17)
Branch: `feature/070-27-lesson-scaffold`

## Files
- [NEW] `tools/lesson_templates/lesson/{lesson.toml,README.md,README.en.md,main.cpp,exercises.toml}.tmpl`
- [NEW] `tools/lesson_templates/unit/{unit.toml,unit.hpp,README.md,README.en.md}.tmpl`
- [MODIFY] `tools/lessons.py` — 하위 명령 `new`, `new-unit`; `check`의 `[scaffold]` WARN; docstring
- [MODIFY] `tools/test_lessons.py` — AC-1 ~ AC-6
- [MODIFY] `lessons/curriculum.toml` 머리 주석, `lessons/README.md`, `docs/agent_start_prompt.md` (§8)

C++ 라이브러리 변경 없음. `lessons/CMakeLists.txt`, `web/`, `tools/exercises.py`, `tools/practice.py`는 그대로.

## Decisions made while implementing
- **템플릿 변수는 두 벌이다**: Markdown·C++용 글 그대로(`$id`, `$track`, `$title`, `$title_en`, `$summary`, `$summary_en`)와 TOML 값(`$title_toml`, `$title_en_toml`, `$summary_toml`, `$summary_en_toml`, `$tags_toml`, `$uses_toml`, 따옴표·대괄호 포함, TOML 기본 문자열 이스케이프). spec Assumption 5는 `$tags`, `$uses`로 적었는데, TOML 값과 글을 나누어야 이스케이프가 한 곳에서 끝난다.
- **리뷰로 더한 조건**(§2.2를 좁힘, spec이 막으려던 경우): `--after`와 `--before`를 함께 주면 argparse 오류(2)가 아니라 조건 실패(1); `lessons` 배열은 한 줄에 id 하나, `[`와 `]`는 따로 줄에(아니면 오류), 고친 글을 tomllib로 다시 읽어 기대한 목록인지 확인; 제목·요약에 `*/`(C++ 주석이 끝남)나 UTF-8이 아닌 글이면 오류; 목록에 이미 있는데 폴더가 없는 id면 오류(두 번 나오게 되므로); `mkdir`은 부모를 만들지 않음; `new`는 새 폴더의 결과만 보여 줌.
- **`--root`, `--out`은 명령 이름 앞에도 쓸 수 있다**(옛 사용법 `--out - index` 유지). `check --out X`는 이제 argparse 오류다(예전에는 무시). 저장소 안에 그렇게 부르는 곳은 없다.
- **레슨 수는 21개다.** spec AC-6은 "22개 레슨"이라고 적었는데 070-26의 세는 실수를 옮긴 것이다(070-26 plan과 같음). 확인은 실제 트리의 21개 레슨과 2개 유닛으로 했다.
- **빠진 제목·요약의 대체 글**: `[scaffold] 한국어 제목`, `[scaffold] English title`, `[scaffold] 한 줄 요약`, `[scaffold] One-line summary`.

## Unit table
| Unit | File | Change (what, where, AC) | Check | Risky | Author | Reviewer | Tokens (in / out) | Status |
|---|---|---|---|---|---|---|---|---|
| U1 | `tools/lesson_templates/**` | 템플릿 9개 (§2.3, AC-1, AC-5) | 임시 루트의 생성물 `check` ERROR 0 | no | lead (lesson text) | cpp-reviewer (with U2): none for templates (note: `*/` in a title → fixed in U2) | — | done |
| U2 | `tools/lessons.py` | `new`, `new-unit`, 조건, 쓰기·되돌리기, curriculum 편집 (§2.1, §2.2, AC-1 ~ AC-5) | 임시 루트(LF, CRLF, 쉼표 없는 끝 항목)에서 실행; 기존 108 OK | no | agy flash; review fixes lead (small) | cpp-reviewer: 7 mismatches → fixed by lead; re-review none; 1 leftover (stale entry) → fixed by lead | 269k / 88k | done |
| U3 | `tools/lessons.py` | `check`의 `[scaffold]` WARN (AC-6) | 실제 저장소 `check` 0 warnings | no | lead (small) | cpp-reviewer (with U2): wording → fixed | — | done |
| U4 | `tools/test_lessons.py` | 새 테스트 39개 (AC-1 ~ AC-6) | 147 OK; 변이 7개(끝에만 넣기, rmtree 없음, 중복·폴더·track.toml 검사 없음, curriculum 복원 없음, 검사 파일 줄임) 모두 실패 | no | agy flash; review fixes lead (small) | cpp-reviewer: 9 weak tests (메시지를 보지 않음, 폴더 없는 snapshot, 반쯤 쓴 curriculum 없음, 파일마다 WARN 하나) → fixed by lead; re-review none | 226k / 56k | done |
| U5 | (저장소, 커밋 없음) | 실제 레슨·유닛 만들어 두 호스트 빌드 (AC-7) | testrecord R3–R6 | no | lead | — | — | done |
| U6 | 문서 §8 | README, curriculum 주석, Quick reference | `lint_docs.py` 0 errors | no | lead | cpp-reviewer: none | — | done |
