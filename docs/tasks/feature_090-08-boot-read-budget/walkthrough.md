# Walkthrough 090-08: 부트와 편집 때의 읽기 줄이기

- Spec: [/docs/specs/090_08_boot_read_budget.md](/docs/specs/090_08_boot_read_budget.md) · Plan: [plan.md](plan.md) · Tests: [testrecord.md](testrecord.md)

## 결과
- **부트**: 2·3단계는 파일 두 개(77.3 KB)를 읽는 대신 `py -3 .agent/scripts/lint_docs.py --boot`(5.5 KB)를 실행한다. 출력은 todo 머리말, task 상태, 열린 KI 표, DEFERRED 개수다. KI 본문은 `--ki KI-NNN`, 조건부 항목은 `--deferred`로 본다. 어느 agent든 같은 명령이다.
- **위치는 상태가 정한다**: `py -3 .agent/scripts/archive_docs.py`가 KI를 상태에 맞는 파일로 옮긴다(OPEN·PLANNED: `docs/known_issues.md`, DEFERRED: `docs/known_issues_deferred.md`, CLOSED: `docs/archive/known_issues_closed.md`). DONE task는 `docs/archive/agent_todo_done.md`로 옮긴다. 글을 잃을 수 있는 입력이면 옮기지 않고 거부한다(exit 1, 아무것도 쓰지 않음). 문서 게이트는 네 파일을 함께 읽는다.
- **편집 때 읽는 양**: `known_issues.md` 53.8 → 6.4 KB, `agent_todo.md` 23.6 → 10.1 KB.
- **한도**(task를 고를 때 적용): 열린 KI 20, DEFERRED 30, todo 머리말 5 KiB, 머리말에 끝난 항목 없음, `--boot` 16 KiB. 넘으면 `--boot` 첫 줄에 `BUDGET:`가 나오고, lead는 다음 task 전에 정리안을 사용자에게 낸다(workflow 2단계). 문서 게이트의 조건은 아니다.
- **첫 정리**(사용자 결정 2026-11-06): 열린 KI 25 → 5. DEFERRED 18개, KI-002 닫음(dropped), KI-031은 KI-023에 합침. todo 진행 순서에서 끝난 A 목록과 `~~…~~` 항목을 정리했다.
- **서브 에이전트**: 모든 위임 프롬프트의 첫 줄이 "부트 순서를 따르지 말라"다(delegation.md §4, 부트 문서 맨 위). 같은 저장소에서 codex에 좁은 질문 하나를 맡기면 입력 39.5k 토큰이었다. 변경 전과 통제된 비교는 아니다(testrecord Measurements).
- 부트 문서의 hook 문단은 한 줄로 줄였다. 자세한 내용은 config.md에 있고, 같은 명령 줄에서 만든 브랜치는 commit 판정 때 아직 없다는 점을 더했다(이 task에서 실제로 겪음).

## Follow-ups
- [KI-047](/docs/known_issues_deferred.md) (DEFERRED): 러너(`subagent_run.py`)가 서브 에이전트 첫 줄을 직접 붙이는 것. 러너가 ai_sec과 공유 kit로 옮겨질 때.
- 이 task의 검토에서 계약 밖으로 남긴 것(KI 아님, 진단 품질): `parse_ki`가 실패한 KI 파일의 id를 가리키는 참조는 "not defined" ERROR가 연달아 난다. 실제 원인 ERROR가 함께 나오므로 고치지 않았다.

## 단위와 작성자
코드·테스트 단위 6개는 agy `flash`가 썼고, 문서 단위와 검토 지적의 작은 수정은 lead가 했다(plan.md 단위 표). `lead (fallback)` 단위는 없다. 모든 단위는 cpp-reviewer가 검토했고, 지적이 있던 단위는 한 번 더 검토받았다(testrecord Reviews).
