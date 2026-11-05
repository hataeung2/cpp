# Walkthrough: 090-07 문서 구조 정리

- Spec: [/docs/specs/090_07_docs_layout.md](/docs/specs/090_07_docs_layout.md) (사용자 승인 2026-11-05, 질문 답)
- Test record: [testrecord.md](/docs/tasks/feature_090-07-docs-layout/testrecord.md)

## 결과
- `docs/learning/`이 없어졌다. 학습 문서는 모두 `docs/cpp_evolution/`에 주제마다 두 벌(`<x>.md` 한국어, `<x>.en.md` 영어), 11쌍이다. 영어 원문 9개는 `git mv`로 `.en.md`가 되어 이력이 이어지고, 한국어판은 새 번역이다. 한국어 원문 2개(`const_return_type`, `modern_ring_buffer_architecture`)에는 영어판을 새로 썼다.
- `docs/cpp_evolution.md`(+ `.en.md`)는 essentials 레슨 16개 순서의 목차다: 레슨, 예전 방식 → 지금 방식, 해설 페이지, atugcc 코드. 페이지가 없는 레슨과 레슨이 없는 페이지, 옛 구조의 기록도 따로 적었다.
- `docs/` 바로 아래: `agent_start_prompt.md`, `agent_todo.md`, `known_issues.md`, `lesson_candidates.md`, `cpp_evolution.md`(+`.en.md`). `docs/tasks/`에는 태스크 기록 폴더만 있다. `docs/artifacts/` → `docs/guides/`.
- 링크는 같은 언어끼리: 한국어 문서 → `README.md`·`.md`, 영어 문서 → `README.en.md`·`.en.md`. 레슨 README의 "(영어)"/"(Korean)" 표시는 지웠다.
- `lint_docs.py`가 evolution 페이지 짝(없음, 제목 수준 순서, 코드 블록 수)을 WARN으로 검사한다. 규칙(`impl.md` §6, 부트 문서, workflow, 스펙 템플릿)도 두 파일 규칙으로 바꿨다.
- 봉인된 기록(이전 태스크의 `docs/tasks/feature_*`)은 고치지 않았다. 그 안의 옮긴 경로 링크 12개는 문서 게이트의 INFO로 남는다.

## 검증
문서 게이트 0 error / 0 warning, 스크립트 테스트 71 OK, `lessons.py check` 0/0, 코드 블록 대조 9쌍 일치, AC-3·AC-4 `git grep`. 리뷰 세 번(R1 한국어 번역, R2 코드·영어 번역·목차, R3 수정 재확인): 뜻이 바뀐 번역 0건, 코드 결함 3건과 표현 6건을 고침. C++ 빌드는 돌리지 않았다(CMake 입력 변경 0개).

## Follow-ups
- KI-043: `scripts/parse_dump.py`가 `tools/read_dump.py`로 대체되었는지 확인하고 지우거나 옮기기.
- KI-044: `libs/`에 CMake 파일만 있는 배치, 040-01에서 정함.
- R2의 (4) `~~~` 펜스·`#\t` 제목은 짝 검사가 모르지만 지금 페이지에 없어 KI로 두지 않았다. 그런 문법을 쓰게 되면 `agent_common.strip_code`와 함께 고친다.

`lead (fallback)` 단위 없음.
