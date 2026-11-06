# Test Record 090-10: 어느 agent에서나 쓰는 skill

- Spec: [/docs/specs/090_10_portable_skills.md](/docs/specs/090_10_portable_skills.md) · Plan: [plan.md](plan.md)

C++ 변경 없음: preset 빌드·ctest 대상이 아니다. 검증은 스크립트 게이트([test.md](/.agent/rules/test.md) §6)와 사용자 확인(AC-5)이다.

## Runs (2026-11-06, Windows host)

| Run | Expected | Actual | Status |
|---|---|---|---|
| 테스트 먼저(U1): 구현 전 | 새 테스트 실패 | `import sync_skills` 실패(모듈 없음) | Pass |
| `py -3 .agent/scripts/test_agent_scripts.py` | 전부 통과 | `Ran 132 tests`, OK (`SyncSkillsTest` 16개) | Pass |
| `py -3 .agent/scripts/sync_skills.py` (실제 저장소, 첫 실행) | 복사본 4개 생성 | `wrote` 4줄 (`.claude/skills/`, `.agents/skills/` × 2 skill) | Pass |
| 같은 명령 두 번째 | 변경 없음 | `skills up to date` | Pass |
| `py -3 .agent/scripts/sync_skills.py --check` | exit 0 | exit 0, 출력 없음 | Pass |
| 복사본 줄바꿈 | LF | 6개 skill 파일(원본 2, 복사본 4) 모두 CR 0개(`tr -cd '\r' \| wc -c`) | Pass |
| `py -3 .agent/scripts/lint_docs.py` | 0 error, 0 warning | `0 error(s), 0 warning(s), 33 info` | Pass |
| `py -3 .agent/scripts/naming_check.py` | 0 | 0 | Pass |

Skill 크기: `develop-task` description 333자, `add-known-issue` 251자; 파일 2,177 B / 1,946 B(본문 4 KiB 한도 안).

## AC evidence

| AC | Criterion | Evidence | Result |
|---|---|---|---|
| AC-1 | 원본 두 개를 두 위치로 복사, 다시 실행해도 변경 없음 | `test_case1_*`, `test_review_written_bytes_are_lf_and_no_rewrite` (LF 바이트, 오래된 mtime 유지), 실제 저장소 두 번째 실행 `skills up to date` | Pass |
| AC-2 | 복사본 수정·남은 복사본·`SKILL.md` 없는 원본 → `--check` exit 1과 경로 | `test_case2_*`, `test_case3_*`, `test_case4_*`, `test_review_check_never_writes_and_reports_every_case` (세 경우 모두 `--check`, 쓰지 않음), `test_review_missing_copies_bom_hash_and_missing_source` (복사본 없음, 대상 폴더 없음) | Pass |
| AC-3 | 허용되지 않은 키, 폴더와 다른 `name`, 1024자 넘는 description → ERROR; 4 KiB 넘는 본문 → WARN | `test_case5_*`, `test_case6_*` (한글로 4096/4097 B), `test_review_validate_rules_tied_to_cause`, `test_review_missing_copies_bom_hash_and_missing_source` (`#` 포함 길이, 주석뿐인 값은 빈 값) | Pass |
| AC-4 | 문서 게이트가 `--check`를 부른다 | `test_case8_ac4_lint_docs_integration` (복사본 수정 → `skills:` ERROR, sync 뒤 없음) | Pass |
| AC-5 | 세 tool에서 두 skill이 보인다 | **사용자 수동 확인 대기** | — |
| AC-6 | 회귀 없음 | 132 tests OK, lint 0/0 | Pass |

## Reviews

| Unit | Reviewer | Question | Findings | Resolution |
|---|---|---|---|---|
| U1 | cpp-reviewer | 테스트가 사례를 정확히 확인하는가 | 테스트 버그 2건: 1024자 사례가 올바른 구현에서 실패(복사본 없음 ERROR를 같이 셈), `description: ''`는 `read_frontmatter`에서 빈 값이 아님. 약함 9건: LF를 `read_text`로 확인, mtime 같은 tick, 유효 skill이 있을 때 쓰기 거부, `--check` 세 경우·쓰지 않음, 대문자 이름이 패턴으로 잡히는지, CRLF 원본, 나머지 validate 규칙 | lead 수정 + `test_review_*` 7개 |
| U2 | lead 확인, 이어서 cpp-reviewer | 계약 일치, 죽는가, 파일을 잃는가 | lead: 대상 폴더 자체가 없으면 복사본 없음을 보고하지 않음(1024자 테스트가 통과한 이유), 테스트의 `''`에 맞춘 계약 밖 따옴표 처리. 검토: BOM 원본에서 표시 줄 위치, 원본 폴더가 없으면 복사본을 전부 말없이 삭제, 파일·폴더 충돌의 `OSError` traceback, `#`에서 잘린 description 길이 | lead 수정 + 테스트. 재검토: 전부 해결, 새 회귀 1건(주석뿐인 description이 빈 값이 아니게 됨) → lead 수정(빈 값은 `read_frontmatter` 값, 길이는 원문) + 테스트. §6.3에 따라 이 마지막 두 줄 수정은 재검토하지 않음 |
| U3 | cpp-reviewer | `check_skills` | none | — |
| U4 | cpp-reviewer | skill이 spec §0의 4~6을 따르는가, 명령이 맞는가, 문서가 도구와 맞는가 | develop-task가 검토 규칙을 "다른 계열"로 잘못 옮김, `lead (small)` 등 누락; add-known-issue에 DEFERRED 등록 뒤 `archive_docs.py` 단계 없음; test.md 문장의 빠진 규칙 | lead 수정, 재검토 해결. 재검토의 "복사본이 CRLF" 지적은 사실이 아님(위 Runs: CR 0개) |

작성자 agy(Gemini 계열), 검토자 cpp-reviewer(Claude 계열): 계열이 다른 검토. 남긴 저위험 테스트 메모 4건(같은 줄 매칭, 폴더 스냅샷, 한 대상만 LF 바이트 확인, `run_main` 거부 뒤 재확인)은 검토자도 AC를 숨기지 않는다고 동의했다.
