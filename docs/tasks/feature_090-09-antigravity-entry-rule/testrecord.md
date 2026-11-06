# Test Record 090-09: Antigravity 진입 rule

- Spec: [/docs/specs/090_09_antigravity_entry_rule.md](/docs/specs/090_09_antigravity_entry_rule.md) · Plan: [plan.md](plan.md)

C++ 변경 없음: preset 빌드·ctest 대상이 아니다. 검증은 스크립트 게이트([test.md](/.agent/rules/test.md) §6)와 사용자 확인(AC-4)으로 한다.

## Runs (2026-11-06)

| Run | Expected | Actual | Status |
|---|---|---|---|
| `py -3 .agent/scripts/test_agent_scripts.py` (Windows) | 전부 통과 | `Ran 116 tests`, OK | Pass |
| `python3 .agent/scripts/test_agent_scripts.py LintDocsTest ArchiveDocsTest` (WSL, 임시 폴더는 ext4 `/tmp`) | 전부 통과 | `Ran 57 tests`, OK | Pass |
| 테스트 먼저(U1): 구현 전 `LintDocsTest` | 새 실패 사례 테스트가 실패 | 5개 FAIL(2·3·4·5·7), 정상 사례(1)와 기존 broken link(6)는 통과, 기존 35개 OK | Pass |
| mutation: WSL 복사본에서 `check_rule_frontmatter`/`check_rule_table`의 `sorted()` 제거 후 `test_rules_review_gaps` 3회 | 실패 | 3회 모두 FAILED (NTFS는 이름 순으로 나열해 Windows에서는 이 mutation을 못 잡는다; ext4에서 잡힘) | Pass |
| `py -3 .agent/scripts/lint_docs.py` | 0 error, 0 warning | `0 error(s), 0 warning(s), 33 info` | Pass |
| `py -3 .agent/scripts/naming_check.py` | 0 | 0 | Pass |

## AC evidence

| AC | Criterion | Evidence | Result |
|---|---|---|---|
| AC-1 | `.agent/rules/boot.md`, `trigger: always_on`, 본문 1 KiB 이하 | 파일 199 B, 본문 172 B (lint가 재는 LF 기준; CRLF checkout이면 `wc -c`는 줄마다 1 B 더 크다), lint 경고 0 | Pass |
| AC-2 | 잘못된 trigger, description 없는 model_decision, always_on 두 개 → ERROR; 1 KiB 넘는 always_on 본문 → WARN | `test_rules_ac2_frontmatter_validation`, `test_rules_ac2_two_always_on`, `test_rules_ac2_always_on_body_byte_limit`, `test_rules_review_gaps` (빈 값, trigger 키 없음, 바이트 기준 한글 400자 = 1200 B, 세 파일에서 이름 순 두 번째부터) | Pass |
| AC-3 | 표에 없는 model_decision rule, 표에 있지만 없는 파일 → ERROR | `test_rules_ac3_trigger_table_missing_rule`, `test_rules_ac3_trigger_table_broken_link`, `test_rules_ac3_missing_boot_prompt`, `test_rules_review_gaps` (본문 글·코드 블록 안의 이름은 링크가 아님, 1행, 새 메시지 없음) | Pass |
| AC-4 | Antigravity 새 대화가 부트 순서로 답한다 | **사용자 수동 확인 대기** | — |
| AC-5 | 회귀 없음 | 116 tests OK, lint 0/0 | Pass |

## Reviews

| Unit | Reviewer | Question | Findings | Resolution |
|---|---|---|---|---|
| U1 | cpp-reviewer | 테스트가 사례를 정확히 확인하는가 | 7건: 사례 7이 표 메시지로 통과 가능, trigger 단언 느슨, 빈 값·trigger 키 없음 미검사, ASCII 본문(문자 = 바이트), 이름 순·"두 번째부터 모두" 미검사, 링크 대 본문 글·코드, 1행, broken link의 "새 메시지 없음" | lead가 `test_rules_review_gaps` 추가. 재검토에서 남은 값 사례 단언 → 수정; 이름 순은 ext4 mutation으로 확인 |
| U2 | cpp-reviewer | Design 일치, 죽는가 | 시그니처가 Design과 다름(동작 같음); CRLF checkout에서 `wc -c`와 lint의 바이트 차이(한도 근처에서만) | plan Design 갱신; AC-1 증거에 기준 명시 |
| U3 | cpp-reviewer | spec §2.2·§8 일치, 문서가 lint와 맞는가 | none (부트 문서 문구가 §8보다 길지만 뜻 같음) | — |

작성자 agy(Gemini 계열), 검토자 cpp-reviewer(Claude 계열): 계열이 다른 검토.
