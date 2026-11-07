# Test Record 090-12-01: 서브 에이전트가 프로젝트 규칙을 빠짐없이 받는다

- Spec: [/docs/specs/090_12_01_subagent_rules.md](/docs/specs/090_12_01_subagent_rules.md) · Plan: [plan.md](plan.md)

C++ 변경 없음: preset 빌드·ctest 대상이 아니다. 검증은 스크립트 게이트([test.md](/.agent/rules/test.md) §6), 실제 호출 한 번(AC-7), 새 세션 확인(AC-8)이다.

## Spec과 다르게 한 것
- **AC-7은 `--kind code`가 아니라 `--kind review` 호출로 확인했다.** U1–U6 리뷰와 한 번에 해서 호출 하나(약 77k token)를 아꼈다. Core와 Sub-agent limits는 다섯 종류에 같게 붙고(`test_rule_bundle_kinds`), 질문(Q4)은 Core 문장만 물었다.
- **대응표는 상수 두 개**(`COMMON_RULES` + `RULE_SECTIONS`, `rule_sections()`가 합침)다. spec §0 #4는 "상수 하나", §2.2는 "공통 앞부분"이라고 적었다. `cpp-reviewer` 지적(AC-8 실행). 모든 사용처(`rule_bundle`, `lint_docs.check_rule_bundles`)가 `rule_sections()`를 거쳐 공통 절이 빠지는 길이 없으므로 코드는 그대로 두고 여기 적는다(lead 결정, 2026-11-06).
- 문서 게이트의 묶음 검사는 `.agent/scripts/subagent_run.py`가 있는 루트에서만 돈다(spec §2.2에는 조건이 없었다). 규칙 파일만 만드는 lint fixture(`test_rules_clean_set`)가 `impl.md`를 갖고 있어서 `impl.md` 유무로는 가를 수 없었다.

## Runs (2026-11-06)

| Run | Expected | Actual | Status |
|---|---|---|---|
| `py -3 .agent/scripts/test_agent_scripts.py` | 전부 통과 | `Ran 163 tests`, OK | Pass |
| 변경 뒤 첫 실행(테스트를 고치기 전) | 예전 머리말·`--kind` 없는 호출이 실패 | 14 FAIL, 1 ERROR(머리말 문장, `--kind` 없는 `run` 8개, `load_prompt` 인자, lint fixture의 Core 없는 `impl.md`) | Pass |
| `--print-rules <kind>` 크기(bytes) | 8,192 이하 | code 1,947, test 5,738, lesson 3,596, review 3,209, research 1,951 | Pass |
| `--model flash --prompt-file x`(`--kind` 없음) | exit 2 | `error: missing --kind (or use --print-rules <kind>)`, exit 2 | Pass |
| `py -3 .agent/scripts/sync_skills.py --check` | exit 0 | exit 0 | Pass |
| `py -3 .agent/scripts/lint_docs.py` | 0 error, 0 warning | `0 error(s), 0 warning(s), 33 info` | Pass |
| `lint_docs.py --boot` 크기 | 16,384 이하 | 6,329 B(Core 포함, 이전 4,687 B) | Pass |

## AC evidence

| AC | Criterion | Evidence | Result |
|---|---|---|---|
| AC-1 | 다섯 종류 묶음, 프롬프트 순서 | `test_rule_bundle_kinds`(fixture로 정확한 문자열, 펜스 안의 `## `, 더 깊은 제목), `test_real_rule_bundles_build`, `test_build_prompt_rules_order`, `test_run_codex`(codex stdin = 머리말 + review 묶음 + 본문), `test_load_prompt_validation`(agy 한도에 묶음 포함, 경계 양쪽) | Pass |
| AC-2 | `--kind` 없음·절 없음 → exit 2 | `test_run_refusal_starts_no_cli`(`--kind` 없음, `--model` 없음, CLI 미실행), `test_rule_bundle_missing_section`(파일·제목을 말함, 파일 없음, 모르는 kind) | Pass |
| AC-3 | `--print-rules`가 모델을 부르지 않음 | `test_print_rules_calls_no_model`(다섯 종류 출력 = `rule_bundle`, `subprocess.run` 안 불림, 모르는 kind exit 2) | Pass |
| AC-4 | 문서 게이트: 절 누락, Core·묶음 한도 | `test_rule_bundles_gate`(러너 없는 트리는 건너뜀, 제목 바뀜, 파일 없음, 공통 절은 한 번만, Core 1,536/1,537 B, test 묶음 8 KB 초과); 저장소 lint 0 error | Pass |
| AC-5 | `--boot`가 Core 출력, `CLAUDE.md` camelCase 줄 없음 | `test_boot_prints_core`(머리말 뒤 `states:` 앞, Core만, 없을 때 NOTE); `grep -c camelCase CLAUDE.md` = 0 | Pass |
| AC-6 | Core 규칙 중복 없음, 위험 목록은 §8만, §4에 lead 목록 없음 | `grep -n "snake_case_\|kPascalCase" impl.md` → 11행(Core)만; `grep -c "data races"` delegation.md 1, `cpp-reviewer.md` 0; `cpp-reviewer.md` 1단계가 `--print-rules review`; §4는 러너가 붙이는 것과 `### Sub-agent limits` | Pass |
| AC-7 | 실제 호출에서 Core를 인용 | agy flash, 대화 `8587d30e`, 프롬프트 본문에 규칙 없음. Q4 응답: "members `snake_case_`; constants `kPascalCase`", "Build and test only through `py -3 .agent/scripts/build.py --preset <p>` (Linux `python3`), never an ad-hoc `cmake`" — Core 문장 그대로. 답은 체크리스트의 `VERDICT`/`NOT CHECKED` 형식을 따랐다. 리뷰어가 스스로 `test_agent_scripts.py`를 실행했다(파일 변경 없음, `git status` 확인) | Pass |
| AC-8 | `cpp-reviewer`가 `--print-rules review`를 실행하고 체크리스트를 인용 | 사용자의 새 Claude Code 세션(2026-11-06), 프롬프트에 규칙 없음. 리뷰어 보고: 실행한 명령 `py -3 .agent/scripts/subagent_run.py --print-rules review`, 체크리스트 첫 항목 "data races, wrong memory_order, lock held across a callback or I/O, deadlock order;"(원문 그대로) | Pass |

## Reviews

| Unit | Reviewer | Question | Findings | Resolution |
|---|---|---|---|---|
| U3, U4 | agy flash (`--kind review`) | spec §0 #4, #6, #7, #9–#11, §2.2, §4: 절 경계, 붙지 않는 kind, `--kind` 우회, 발동하지 않거나 저장소에서 발동하는 lint | none | — |
| U5 | agy flash | 새 테스트 8개가 AC-1–AC-5를 검사하나; 그냥 통과할 테스트 | none | — |
| U1, U2, U6 | agy flash | §0 #1–#3, #5, #8, AC-6; 모순 | none | — |
| U3 | `cpp-reviewer` (사용자 세션, AC-8) | `subagent_run.py` diff가 spec §0 #4와 맞나 | 기능은 맞음. 형태 2건: (1) 대응표가 상수 두 개, (2) `build_prompt(text, files, rules="")`의 기본값으로 규칙 없는 프롬프트를 만들 수 있음 | (1) 코드 유지, "Spec과 다르게 한 것"에 기록; (2) `review fixes lead (small)`: `rules` 필수, 비면 `InputError`, `test_build_prompt`에 빈 값 case. 5줄이라 다시 리뷰하지 않음(§6.3과 다름) |
