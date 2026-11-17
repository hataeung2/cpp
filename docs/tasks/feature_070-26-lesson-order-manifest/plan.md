# Plan 070-26: 레슨 순서를 매니페스트로 옮기고 폴더 번호 제거

Spec: [070_26_lesson_order_manifest.md](/docs/specs/070_26_lesson_order_manifest.md) (approved 2026-11-16)
Branch: `feature/070-26-lesson-order-manifest`

## Files
- [NEW] `lessons/curriculum.toml` — 트랙 3개, 레슨 21개의 지금 순서 (Assumption 10)
- [MODIFY] `tools/lessons.py` — `apply_curriculum`(순서, 목록 검사), 레슨 폴더 이름 = id, 트랙 폴더 이름 `[a-z][a-z0-9_]*`, 모듈 머리 설명
- [MODIFY] `tools/test_lessons.py` — `CurriculumTest`(AC-3, AC-4), 픽스처에 `curriculum.toml`, 번호 픽스처 이름 정리
- [MODIFY] `tools/test_practice.py`, `tools/test_exercises.py`, `web/server/test_server.py`, `.agent/scripts/test_agent_scripts.py` — 번호 픽스처 이름(`01_t/01_a` → `t/a`), lint 픽스처에 `curriculum.toml`
- [RENAME] `lessons/tracks/**` — 트랙 3개, 레슨 21개 (`git mv`)
- [MODIFY] 살아 있는 문서와 레슨 README·`exercises.toml`의 링크, 끝난 spec 9개의 링크 대상 (스크립트, 59개 파일 321곳)
- [MODIFY] `lessons/README.md`, `docs/lesson_candidates.md`, `README.md` — 순서 규칙 (§8)
- [NEW] `migrate.py` (이 폴더) — 한 번 쓴 옮기기 스크립트, 기록 (Assumption 8)
- 로컬 `practice/` — 사본 폴더 24개 이동, `state.json` 53개 항목 (커밋 없음)

C++ 변경 없음. `lessons/CMakeLists.txt`, `web/`, `tools/practice.py`, `tools/exercises.py`는 그대로(§2.3).

## Decisions made while implementing
- **레슨 수는 21개다.** spec §1, AC-2, Assumption 10은 22개라고 적었는데 세는 실수였다. 옮기기 전 인덱스가 21개다(testrecord R1).
- **AC-5의 grep은 끝난 spec과 archive를 뺀다.** spec의 명령(`":!docs/tasks"`만 뺌)은 Assumption 7과 맞지 않는다: Assumption 7은 끝난 spec 본문의 글(코드 꼴 경로 포함)은 그때의 기록으로 둔다고 했고, 그런 경로가 끝난 spec에 32곳 있다. 그래서 확인은 두 갈래다: 살아 있는 파일(`docs/tasks`, `docs/specs`, `docs/archive` 밖)에 번호 경로 0, `docs/specs`·`docs/archive`의 링크 대상에 번호 경로 0.
- **바꾸는 단위는 경로가 아니라 옛 폴더 이름 토큰이다.** 참조는 세 꼴(`/lessons/tracks/01_essentials/…` 경로, `../05_source_location/README.md` 상대 링크, `[11_thread_and_log](…)` 링크 글)이라, 옛 폴더 이름 24개를 낱말 경계로 바꿨다. 끝난 spec과 archive에서는 링크 대상 `](…)` 안에서만 바꿨다.
- **픽스처 이름도 바꿨다**(`01_t/01_a` → `t/a`). 새 규칙에서 번호 폴더는 ERROR이고, 픽스처가 번호를 쓰면 AC-5의 grep이 남는다. 바뀐 이름이 시험의 뜻을 바꾸지 않는지 리뷰가 확인한다.

## Unit table
| Unit | File | Change (what, where, AC) | Check | Risky | Author | Reviewer | Tokens (in / out) | Status |
|---|---|---|---|---|---|---|---|---|
| U1 | `tools/lessons.py` | `apply_curriculum`, 폴더 이름 검사 (AC-1, AC-3, AC-4) | 번호 트리에서 25 ERROR(예상), 옮긴 뒤 0 | no | lead (small) | codex luna | — | done |
| U2 | `tools/test_lessons.py` | `CurriculumTest` 10개, 픽스처 | 108 OK; 변이 2개(정렬 없음, 트랙 검사 없음) 모두 실패 | no | lead | cpp-reviewer | — | done |
| U3 | `migrate.py` + 실행 | 폴더 이동, 링크, 연습 공간 (AC-1, AC-2, AC-5, AC-7) | dry run 59 파일 321곳; 전후 인덱스 순서 같음; 전후 `practice.py status` 같음 | yes (여러 파일이 함께 바뀜) | lead (scripted) | codex luna | — | done |
| U4 | 픽스처 4개 파일 | 번호 픽스처 이름 | 각 시험 묶음 OK | no | lead (scripted) | cpp-reviewer | — | done |
| U5 | `lessons/curriculum.toml`, `lessons/README.md`, `docs/lesson_candidates.md`, `README.md` | 순서 규칙 문서 (§8) | `lint_docs.py` 0 errors | no | lead | cpp-reviewer | — | done |
