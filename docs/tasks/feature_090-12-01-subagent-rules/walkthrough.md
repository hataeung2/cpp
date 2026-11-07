# Walkthrough 090-12-01: 서브 에이전트가 프로젝트 규칙을 빠짐없이 받는다

- Spec: [/docs/specs/090_12_01_subagent_rules.md](/docs/specs/090_12_01_subagent_rules.md) · Plan: [plan.md](plan.md) · Tests: [testrecord.md](testrecord.md)
- 원래 task: [090-12](/docs/tasks/feature_090-12-runner-subagent-preamble/walkthrough.md)

## 결과
- **Core 하나**: [impl.md](/.agent/rules/impl.md) `## Core`(1,489 B). C++ naming, C++ 필수·금지, 상대 경로, secret, `build.py --preset`, 범위, 그리고 "이럴 때 읽을 곳". 뒤 절에서 같은 규칙을 지웠고, `CLAUDE.md`의 camelCase 줄도 지웠다.
- **러너가 단위 종류별로 붙인다**: `subagent_run.py --kind code|test|lesson|review|research`(필수). 모두 Core + [delegation.md](/.agent/rules/delegation.md) `### Sub-agent limits`; test는 `test.md` §2, lesson은 레슨 작성 안내, review는 §8 `### Review checklist`. 묶음은 1.9–5.7 KB. `--print-rules <kind>`는 모델 없이 출력만.
- **lead는 설계만 쓴다**: 서브 에이전트 제한 목록과 규칙은 lead가 쓰지 않는다(§4).
- **리뷰어는 같은 목록**: codex·agy 리뷰어(`--kind review`)와 `cpp-reviewer`(`--print-rules review`)가 같은 체크리스트와 답 형식을 받는다.
- **lead도 같은 Core**: `lint_docs.py --boot`가 todo 머리말 다음에 Core를 출력한다(어느 tool이 lead여도).
- **문서 게이트**: 러너가 가리키는 절이 없거나(제목 변경), Core 1.5 KB·묶음 8 KB를 넘으면 ERROR.
- 머리말과 진입 파일 문장: "follow the prompt and the project rules it carries".

## 계획과 다르게 된 것
- AC-7을 `--kind review` 리뷰 호출과 함께 확인했다(testrecord).
- 묶음 검사는 러너가 있는 루트에서만 돈다(testrecord).
- AC-8 리뷰 뒤: 대응표를 `RULE_SECTIONS` 상수 하나로 합쳤다(종류마다 묶음 전체, 사용자 결정). `build_prompt`는 `rules`를 필수로 받는다.

## Follow-ups
- 새 KI 없음. AC-8은 사용자의 새 세션에서 통과.
