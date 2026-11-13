# Plan 070-16-01: 연습 백업을 레슨·유닛별 한 폴더에 모으기

Spec: [070_16_01_backup_by_owner.md](/docs/specs/070_16_01_backup_by_owner.md) (approved 2026-11-12)
Branch: `feature/070-16-01-backup-by-owner`

## Prior Round Reference
- Original spec: [/docs/specs/070_16_practice_workspace.md](/docs/specs/070_16_practice_workspace.md)
- Original artifacts: [/docs/tasks/feature_070-16-practice-workspace/walkthrough.md](/docs/tasks/feature_070-16-practice-workspace/walkthrough.md)
- Reason for reopen: 되돌리기 한 번마다 백업 폴더가 하나 생겨 같은 레슨의 백업이 흩어지고, "최근 10번" 보관이 다른 파일의 백업을 밀어낸다

## Files
- [MODIFY] `tools/practice.py` — `_Backup`을 소유자 폴더 + `<이름>.<시각><확장자>` + 파일마다 10개로, `Workspace`가 소유자 표를 넘김, 모듈 머리 설명
- [MODIFY] `tools/test_practice.py` — 백업 시험(`test_06`, `test_07`, `test_11`)을 새 규칙으로, 새 시험 추가
- [MODIFY] `web/server/test_server.py` — 백업 파일을 찾는 곳(reset 시험)을 새 이름 규칙에 맞춤
- [MODIFY] `lessons/README.md`, `web/README.md` — 백업 위치 설명
- [MODIFY] `docs/specs/070_16_practice_workspace.md` — History 한 줄 (이미 함)
- C++ 변경 없음, evolution 페이지 없음

## Unit table
| Unit | File | Change (what, where, AC) | Check | Risky | Author | Reviewer | Tokens (in / out) | Status |
|---|---|---|---|---|---|---|---|---|
| U1 | `tools/practice.py` | `_Backup`와 이름 규칙 함수, 소유자 표(`Workspace._owners`), 호출 3곳 (AC-1..6) | `py -3 tools/test_practice.py`(U2 뒤), `git diff --stat` 한 파일 | no | lead (small) | cpp-reviewer | — | pending |
| U2 | `tools/test_practice.py` | AC-1..6 시험 | `py -3 tools/test_practice.py` | no | lead (small) | cpp-reviewer ("each test checks its AC; can any pass trivially?") | — | pending |
| U3 | `web/server/test_server.py` | AC-7: 백업 파일 위치 확인을 새 규칙으로 | `PlaygroundServer` 시험 | no | lead (small) | cpp-reviewer | — | pending |
| U4 | `lessons/README.md`, `web/README.md` | 백업 문단 (AC-9) | `lint_docs.py` | no | lead | — | — | pending |

Python 도구만 바꾼다(C++ 위험 항목 없음). 한 함수 크기라 모델 호출보다 lead가 쓰는 쪽이 싸다(delegation.md §1 small change).
