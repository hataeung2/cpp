# Test Record 090-08: 부트와 편집 때의 읽기 줄이기

- Spec: [/docs/specs/090_08_boot_read_budget.md](/docs/specs/090_08_boot_read_budget.md)
- Plan: [plan.md](plan.md)

C++ 코드 변경이 없다(`include/`, `src/`, `tests/`, `lessons/` 변경 없음). 그래서 preset 빌드와 ctest는 이 task의 대상이 아니다. 검증은 [test.md](/.agent/rules/test.md) §6의 스크립트 게이트(`test_agent_scripts.py`, `lint_docs.py`, `naming_check.py`)로 한다.

## Runs (2026-11-06, Windows host)

| Run | Expected | Actual | Status |
|---|---|---|---|
| `py -3 .agent/scripts/test_agent_scripts.py` | 전부 통과 | `Ran 108 tests`, `OK` | Pass |
| `py -3 .agent/scripts/test_agent_scripts.py ArchiveDocsTest` | 전부 통과 | 14 tests OK | Pass |
| `py -3 .agent/scripts/test_agent_scripts.py LintDocsTest` | 전부 통과 | 37 tests OK (archive 13, boot 10 포함) | Pass |
| 테스트 먼저(U1, U3, U5): 구현 전 실행 | 새 테스트 실패 | U1: `import archive_docs` 실패 / U3: 새 12개 FAIL, 기존 12개 OK / U5: 새 6개 ERROR(`AttributeError`, argparse) | Pass |
| `py -3 .agent/scripts/lint_docs.py` | 0 error, 0 warning | `0 error(s), 0 warning(s), 33 info` (INFO는 봉인된 기록, 전과 같은 33개) | Pass |
| `py -3 .agent/scripts/naming_check.py` | 0 | `0 snake_case function name(s)` | Pass |
| `py -3 tools/lessons.py check` | 0 / 0 | `0 error(s), 0 warning(s)` | Pass |
| `archive_docs.py` 첫 실행(U7) 후 글 손실 대조 | HEAD의 KI 본문 46개, 표 행 46개, task 줄 전부가 새 파일들에 그대로 | 빠진 것 0 (스크립트로 대조) | Pass |

## Measurements

| What | Before | After |
|---|---|---|
| 부트 2·3단계에서 읽는 양 | `agent_todo.md` 23.6 KB + `known_issues.md` 53.8 KB = 77.3 KB | `lint_docs.py --boot` 5,463 B |
| `--boot` (archive 전, U6 직후) | — | 9,201 B, `BUDGET: open KI 25/20; finished items in the todo header` |
| `known_issues.md` (편집 때 읽는 양) | 53.8 KB | 25.5 KB (U7) → 6.4 KB (U8 정리 뒤) |
| `agent_todo.md` | 23.6 KB | 11.0 KB (U7) → 10.1 KB (U8), 머리말 3,857 B |
| 열린 KI / DEFERRED | 25 / 0 | 5 / 19 (KI-047 포함) |
| 서브 에이전트(codex `luna`, read-only, 한 파일에 대한 yes/no 질문) | 070-15 U1 review: 입력 119k (질문 범위가 다름) | 입력 39,464 토큰, 14 s |

서브 에이전트 측정은 통과 조건이 아니다(spec §12). 같은 질문의 변경 전 측정이 없어서 통제된 비교가 아니다. 119k의 원인이 부트 읽기였는지는 확인되지 않았다. 다만 좁은 질문이 40k 안팎이라는 것은 delegation.md §2의 "agy 호출 약 45k"와 같은 수준이다.

## AC evidence

| AC | Criterion | Evidence | Result |
|---|---|---|---|
| AC-1 | `--boot`: 머리말, 상태, CLOSED가 아닌 KI 행만 | `test_boot_ac1_header_status_and_open_planned_rows`, `test_boot_contract_details` (순서, 표 머리 두 줄, KI 머리말·그룹 제목·본문 없음) | Pass |
| AC-2 | `--ki` 섹션, 없는 id는 exit 1 | `test_boot_ac2_ki_sections_cli_and_errors`, `test_boot_contract_details` (여러 파일, 본문) | Pass |
| AC-3 | `---` 없으면 전체 + NOTE | `test_boot_ac3_no_separator_prints_whole_todo_with_note`, `test_boot_note_without_separator_is_exact` (정확한 문장, BUDGET보다 먼저, 들여쓴 `---`) | Pass |
| AC-4 | 한도마다 `BUDGET:` 줄, 한도 안이면 없음, 게이트 아님 | `test_boot_ac4_budget_limits_and_clean_state`, `test_boot_ac4_gate_budget_limits_not_in_lint_findings`, `test_boot_contract_details` (기본값, 20/21·30/31 경계, 정확한 줄, 한도를 바꿔도 lint 결과 같음), `test_boot_header_size_counts_only_the_header` (머리말만, 경계 같음은 통과) | Pass |
| AC-4a | DEFERRED는 개수 한 줄, `--deferred` 표, 조건 없는 DEFERRED는 ERROR | `test_boot_ac4a_deferred_summary_and_cli`, `test_boot_contract_details` (표만, 접미 문장), `test_archive_deferred_owner_condition_required` | Pass |
| AC-5 | 부트 문서 2·3단계, 서브 에이전트 문장, hook 한 줄, delegation §4 | diff: [agent_start_prompt.md](/docs/agent_start_prompt.md), [delegation.md](/.agent/rules/delegation.md) §4, lint 0 | Pass |
| AC-6 | `--boot` 10 KB 이하 | 5,463 B (archive 전에도 9,201 B) | Pass |
| AC-7 | `archive_docs.py` 상태별 이동, patch 남은 task 유지, 두 번째 실행 무변경 | `ArchiveDocsTest` 14개 (거부 사례 11개 subTest: 글을 잃는 대신 exit 1, dry-run 포함) | Pass |
| AC-8 | 옮긴 뒤에도 lint 같음, 위치 WARN, 중복 ERROR | `LintDocsTest.test_archive_*` 13개 | Pass |
| AC-9 | 첫 실행 뒤 KI 30 KB 이하, todo 12 KB 이하, 경고 0 | 25.5 KB, 11.0 KB, `0 warning(s)` | Pass |
| AC-9a | 첫 정리 뒤 `BUDGET:` 없음, 사용자 결정과 일치 | `--boot` 첫 줄이 todo 제목(`BUDGET:` 없음), 열린 KI 5/20, DEFERRED 19/30, 머리말 3,857/5,120 B, `~~` 없음. 결정: 2026-11-06 사용자 답 "제안대로 적용" (DEFERRED 18개, KI-002 dropped, KI-031 → KI-023) | Pass |
| AC-10 | 회귀 없음 | 108 tests OK, lint 0 warning | Pass |

## Reviews

| Unit | Reviewer | Question | Findings | Resolution |
|---|---|---|---|---|
| U1 | cpp-reviewer | 7개 테스트가 사례를 확인하는가, 쉽게 통과하는가 | 단언 약함 5건, 빠진 사례 7건 | lead가 단언·테스트 보강(review fixes lead (small)) |
| U2 | cpp-reviewer | 계약 일치, 글 손실·중복, 무변경 시 쓰기 | 글 손실 경로 5건(archive 자유 텍스트, `---` 없는 archive, 파일 안 중복 id, 두 파일의 같은 id, archive에 이미 있는 task), 저위험 4건; 테스트 3건 | agy `--resume`으로 수정. 재검토: 전부 해결, 새 결함 1건(행만 있는 KI를 dry-run은 통과, apply는 거부) → lead가 `plan_moves`로 옮김; 거부 사례 테스트를 이유 문장까지 확인하게 보강 |
| U3 | cpp-reviewer | 12개 테스트가 정확히 확인하는가 | 다른 ERROR로 통과 가능 2건, 약함 2건 | lead 수정 |
| U4 | cpp-reviewer | 계약 일치, 깨진 입력에 죽는가, archive 없는 저장소의 동작 | `ValueError` 삼킴(경고 0인데 archive_docs는 거부), archive 제목 앞 task, 연쇄 ERROR, 죽은 변수 | lead 수정 + 테스트 `test_archive_unreadable_todo_body_is_an_error`. 남김: `parse_ki` 실패 시 그 파일 id의 참조가 연쇄 ERROR(진단 소음, 계약 밖) |
| U5 | cpp-reviewer | 6개 테스트가 AC를 정확히 확인하는가 | 11건(CLI 미호출, 기본값·경계, 항목-한도 연결, 정확한 줄, 게이트 판정 약함 등) | lead가 테스트 3개 추가. 재검토: 게이트 기준선의 DEFERRED 초과, 끝난 항목 한도, 머리말 경계 → lead 수정 |
| U6 | cpp-reviewer | 계약 일치, 죽는가, `--status` 동일한가 | `---` 경계 불일치, NOTE·BUDGET 순서(spec과 plan 충돌 → spec), 알 수 없는 상태 행 숨김, `--ki` traceback, `--deferred`가 깨진 파일을 "없음"으로, closed archive 오류 숨김. `--status` 동일 | lead 수정 + 테스트 2개. 재검토: `none`(새 테스트는 모두 옛 코드에서 실패). 남은 작은 불일치(`--deferred`의 NOTE가 stdout) → stderr로 맞춤 |
| U8–U10 | cpp-reviewer | §8 문서, 정리 결과가 결정과 일치하는가, 규칙 간 모순 | 정리: 결정과 일치, 손실 없음. 문서 7건: archive 머리말 2건(언제 옮기는지, closed의 출처가 둘), config.md 문장(순서, machine path는 Write/Edit), deferred 머리말의 명령 형식, KI-002 Owner 형식, workflow 6단계 순서(archive가 DONE 갱신보다 앞), 2단계 다음 ID | lead 수정(머리말은 스크립트 상수와 파일 모두). 재검토: `none` |

모든 코드·테스트 단위의 작성자는 agy(Gemini 계열)이고 검토자는 cpp-reviewer(Claude 계열)다: 계열이 다른 검토.
