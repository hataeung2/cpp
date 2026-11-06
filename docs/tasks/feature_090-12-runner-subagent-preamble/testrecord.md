# Test Record 090-12: 서브 에이전트는 부트를 읽지 않는다

- Spec: [/docs/specs/090_12_runner_subagent_preamble.md](/docs/specs/090_12_runner_subagent_preamble.md) · Plan: [plan.md](plan.md)

C++ 변경 없음: preset 빌드·ctest 대상이 아니다. 검증은 스크립트 게이트([test.md](/.agent/rules/test.md) §6)와 실제 호출 한 번이다.

## Spec과 다르게 한 것
- Antigravity lead의 fresh reviewer를 agy `flash --read-only`(spec §0 #10)에서 agy `sonnet --read-only`로 바꿨다. U4 리뷰 지적: flash는 ordinary 코드 작성자와 같은 계열(Gemini)이다. spec History에 적었다.

## Runs (2026-11-06)

| Run | Expected | Actual | Status |
|---|---|---|---|
| `py -3 .agent/scripts/test_agent_scripts.py` | 전부 통과 | `Ran 156 tests`, OK | Pass |
| 변경 전 러너로 새 테스트 | 실패 | `SUBAGENT_PREAMBLE`이 없어 실패(main의 `subagent_run.py`에는 상수가 없다); `test_run_codex`는 첫 실행에서 실제로 FAIL(입력에 머리말이 없다고 기대한 예전 단언) | Pass |
| `py -3 .agent/scripts/sync_skills.py --check` | exit 0 | exit 0 | Pass |
| `py -3 .agent/scripts/lint_docs.py` | 0 error, 0 warning | `0 error(s), 0 warning(s), 33 info` | Pass |

## AC evidence

| AC | Criterion | Evidence | Result |
|---|---|---|---|
| AC-1 | 머리말 → 목록 → 본문 | `test_build_prompt`(문장은 spec 그대로 비교), `test_run_codex`(codex stdin), `test_load_prompt_validation`(agy 한도에 머리말 포함, 경계 양쪽) | Pass |
| AC-2 | 이미 있으면 한 번 | `test_build_prompt_keeps_one_preamble`: 앞 빈 줄·공백, CRLF, `--files`와 함께; 둘째 줄 이후의 인용은 그대로 | Pass |
| AC-3 | 진입 파일 3개 첫 본문 줄, `cpp-reviewer.md` | `grep -c "stops here: skip the boot sequence"` CLAUDE.md 1, AGENTS.md 1, boot.md 1; `cpp-reviewer.md`에 "do not run the repository's boot sequence" 1 | Pass |
| AC-4 | §0 Roles·표, `cpp-reviewer`는 §0 표와 §8에만, lead가 첫 줄을 쓰라는 문장 없음 | `grep -n cpp-reviewer delegation.md` → 22행(§0 표), 113행(§8); `grep -c "follow this prompt only"`는 delegation.md·skill 3벌 모두 0; `sync_skills.py --check` exit 0 | Pass |
| AC-5 | `ai_sec` 없음, KI-047 CLOSED, 문서 게이트 | `grep -c ai_sec` 두 파일 0; KI-047은 `docs/archive/known_issues_closed.md`(closed by 090-12); lint exit 0 | Pass |
| AC-6 | 머리말 없는 프롬프트로 부트를 돌지 않음 | 프롬프트 파일(scratch)에 머리말 없음. agy 대화 기록(`conversation_summaries.db`, 대화 `e47fe6a0`)의 첫 줄은 `/plan You are a sub-agent started with this task prompt. Do not run the repository's boot sequence; follow this prompt only.`(러너가 붙임). 응답 Q4 "list every shell command you ran": `none`; 답은 프롬프트의 질문만 다룸. agy가 실행한 도구 기록은 러너 JSON과 CLI 로그에 없어서, "부트 명령을 돌지 않음"은 서브 에이전트의 보고다 | Pass (부트 미실행은 자기 보고) |

## Reviews

| Unit | Reviewer | Question | Findings | Resolution |
|---|---|---|---|---|
| U1 | agy flash | `build_prompt`·`strip_preamble`이 §0 #1–#3, §2.2와 맞나; 글이 빠지거나 겹치는 입력 | none | — |
| U2 | agy flash | AC-1·AC-2를 검사하나; 그냥 통과할 테스트 | none | — |
| U3, U4 | agy flash | delegation.md가 §0 #7–#10과 맞나; 모순 | §1에 `cpp-reviewer`가 남음; Antigravity lead의 fresh reviewer(agy flash)가 작성자와 같은 계열이라 "cross-family" 문장과 모순 | lead 수정(§1 문장을 §0 참조로, Antigravity → agy `sonnet`), `--resume`으로 다시 확인: none |
