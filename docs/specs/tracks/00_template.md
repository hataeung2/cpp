---
track: <track id>       # lessons/curriculum.toml 의 [[track]] id
approved: null          # YYYY-MM-DD, 사용자가 승인할 때마다 새로 씀 / rewritten on every approval by the user
tasks: []               # 이 트랙 spec 아래의 레슨 작업 / lesson tasks under this track spec, e.g. [070-22, 070-23]
---

# Track spec: <트랙 제목> (`<track id>`)

트랙 spec의 규칙: [spec.md](/.agent/rules/spec.md) §6. 레슨 작업은 이 파일의 `tasks`에 있고 `approved`가 날짜이면 spec 없이 시작하고, [`00_lesson_checklist.md`](/docs/specs/tracks/00_lesson_checklist.md)를 모두 채워 끝낸다.

## 0. Assumptions (please review)
사용자가 정하지 않은 결정마다 한 줄. 사용자가 가장 자세히 보는 절이다.

| # | Decision | Rejected alternative | Why |
|---|---|---|---|
| 1 | [...] | [...] | [...] |

## 1. 독자와 목표
[누가 읽는가, 무엇을 이미 아는가, 트랙을 끝내면 무엇을 할 수 있는가.]

## 2. 레슨 형식
- 첫 절의 제목과 비교 방식: [예: "예전 방식과 C++20" / "흔한 실수와 바른 방식"]
- 단계 머리줄: [예: `== Step N: … ==`]
- 출력: [두 OS에서 같은 줄, 무엇을 찍고 무엇을 찍지 않는가]
- 파일: [예: `main.cpp` 하나, 유닛을 쓰는 기준]
- 언어: 출력 영어, 주석 한국어 줄 아래 영어 줄, `README.md`와 `README.en.md`([lessons/README.md](/lessons/README.md) "레슨 작성 안내")

## 3. 공통 규칙
- 정의되지 않은 동작: [돌리지 않는다, 위험은 글·컴파일 오류·안전한 출력으로]
- 출력 안정성: [주소·시간·해시를 찍지 않는다]
- 연습 과제: [자동·관찰을 나누는 기준]
- `docs/cpp_evolution/` 페이지: [쓰는가, 링크만 하는가]
- 태그: [이 트랙이 더하는 태그]

## 4. 커리큘럼
행 순서가 트랙 안의 순서다. 실제 순서의 원본은 [`lessons/curriculum.toml`](/lessons/curriculum.toml)이다. 작업 열은 그 레슨을 만든(만들) 작업이고, `tasks`에는 아직 끝나지 않은 레슨 작업만이 아니라 이 트랙 spec으로 시작한 모든 레슨 작업이 있다. 이 트랙 spec 전에 다른 spec으로 만든 레슨은 작업 열에 그 작업 ID를 쓰고 `tasks`에 넣지 않는다.

| 작업 | 레슨 id | 주제 | 비교 (예전 → 새, 또는 흔한 실수 → 바른 방식) | 선행 | 상태 |
|---|---|---|---|---|---|
| NNN-SS | `<id>` | [...] | [...] | — | 후보 |

상태: `후보`, `레슨 있음`.

## 5. Out of Scope
- [이 트랙이 가르치지 않는 것] — [어디서 다루는지]

## History
승인마다 한 줄: 날짜, 바뀐 것.
- YYYY-MM-DD: [처음 승인 / 행 추가 / 규칙 변경]
