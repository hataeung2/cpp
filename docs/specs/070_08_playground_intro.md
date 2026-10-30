---
id: 070-08
title: 플레이그라운드 소개 페이지 (이 페이지와 라이브러리·레슨의 관계)
depends_on: [070-02]
unblocks: []
approved: 2026-10-29
---

# Spec 070-08: 플레이그라운드 소개 페이지

## 0. Assumptions (please review)
| # | Decision | Rejected alternative | Why |
|---|---|---|---|
| 1 | 소개 글은 저장소 파일 `lessons/intro.md`(한국어 Markdown)로 두고, 기존 README 패널(`ReadmePanel`)이 그대로 보여 준다 | 프론트엔드 안의 HTML 페이지(`web/frontend/src/intro.ts`) | 글을 고칠 때 프론트엔드를 다시 빌드할 필요가 없고, git으로 이력이 남는다. `lessons/` 안 파일이라 페이지에서도 편집할 수 있다. 상대 링크 처리(`.md`는 패널, 다른 파일은 에디터, 외부 링크는 새 탭)도 이미 있다 |
| 2 | 상단 바의 `atugcc playground` 옆에 **ⓘ 소개** 버튼을 둔다. 누르면 README 패널에 소개를 띄우고 README 탭으로 전환한다. 선택한 레슨, 에디터 탭, 실행 상태, URL 해시는 바뀌지 않는다 | 소개를 왼쪽 트리 맨 위 항목으로 넣기 | 트리는 `lessons.py` 인덱스(트랙·레슨·유닛)를 그대로 그린다. 소개는 레슨이 아니므로 인덱스 스키마를 바꾸지 않는다 |
| 3 | URL 해시로 레슨을 고르지 않고 페이지를 열면(해시가 없거나 그 id의 레슨이 없으면) README 패널에 소개를 띄운다 | 지금처럼 빈 패널 | 처음 연 사람이 가장 먼저 봐야 할 내용이다. 해시가 있으면 지금처럼 그 레슨의 README를 띄운다 |
| 4 | 경로는 프론트엔드 상수 `lessons/intro.md`로 둔다 | `/api/lessons` 인덱스에 `intro` 필드 추가 | 파일 하나를 고정 경로로 읽는 데 서버·인덱스 변경은 과하다. 파일이 없으면 README 패널이 기존처럼 `<path>: <오류>`를 보여 준다 |
| 5 | 소개 글의 구분: **라이브러리**(`include/atugcc/` + `src/`, 타깃 `atugcc_core`)는 다른 프로젝트에 가져다 쓰는 core 기능, 패턴 골격, Tracer(시각화·시간 측정)다. **레슨**은 이 라이브러리를 상황에 적용하는 연습(패턴 적용·변형, 구조, 실무 응용)과, 그 전에 필요한 C++ 문법·관용구(essentials 트랙)다 | "레슨 = 패턴" 하나로만 설명 | `include/atugcc/pattern/`(State 골격, Tracer)도 라이브러리다. 레슨의 몫은 패턴 자체가 아니라 *상황에 맞게 적용하는 것*이다. 또 `lambda_capture`처럼 라이브러리를 쓰지 않는 문법 레슨도 있다 |
| 6 | 루트 `README.md`에 지금 커밋되지 않은 `## Workflow` 섹션(작업 흐름)을 이 태스크 브랜치에 같이 넣는다. 소개 글은 작성자용 내용을 반복하지 않고 그 섹션과 `lessons/README.md`로 링크한다 | 별도 docs 커밋을 main에 | main 직접 커밋은 금지(hook)이고, 소개 글이 이 섹션을 링크하므로 같은 변경 단위다 |

## 1. Objective
플레이그라운드를 처음 연 사람이 다음을 한 화면에서 알 수 있게 한다.
- 지금 어디에 있는지: 저장소의 `lessons/`를 브라우저에서 편집·빌드·실행하는 로컬 페이지
- 무엇이 어디서 만들어지는지: 라이브러리(`include/`, `src/`)와 레슨(`lessons/`)의 관계
- 여기서 무엇을 할 수 있는지: 라이브러리 사용법 익히기, 코드에 적용해 보기, 시각화로 이해하기

## 2. Requirement Details

### 2.1 Public API Surface
C++ API 변경 없음. 웹 서버 API 변경 없음(`GET /api/files?path=lessons/intro.md`를 그대로 쓴다).

### 2.2 Internal Implementation
**`lessons/intro.md`** (새 파일). 목차:
1. **여기는** — atugcc 로컬 플레이그라운드. 저장소 파일을 그대로 고치고 preset으로 빌드한다. VS Code에서 같은 파일을 열어도 같은 내용이다.
2. **두 층** — 라이브러리와 레슨(Assumption 5). 라이브러리 파일은 이 페이지에서 🔒 읽기 전용이고, 고치는 곳은 VS Code(`include/`, `src/`)다. 고친 라이브러리는 다음 Run부터 모든 레슨에 반영된다.
3. **여기서 하는 일** — ① 레슨 README와 코드로 라이브러리 사용법 읽기 ② 고치고 Run해서 적용해 보기 ③ Events·Diagrams·Timings 탭으로 동작을 눈으로 확인하기. 탭마다 한 줄 설명을 붙인다.
4. **순서** — 트랙 `01_essentials`(core, 문법, 스레드·로그) → `02_patterns`(상황별 패턴 적용). 레슨마다 대표 링크 하나.
5. **여기서 안 되는 것** — 라이브러리 편집, 외부 공개(`127.0.0.1` 전용), MSVC 빌드(웹은 GCC만 쓰므로 Windows 빌드는 따로 확인).
6. **레슨 만들기** — [`README.md`](/README.md)의 Workflow, [`lessons/README.md`](/lessons/README.md)로 링크.

링크는 저장소 루트 기준으로 쓴다(`/README.md`, `/include/atugcc/pattern/visualizer.hpp`, `/lessons/tracks/.../README.md`). `ReadmePanel`이 이미 지원하는 형식이고, 파일을 옮겨도 링크가 유지된다.

**프론트엔드**
- `index.html`: 상단 바 `.brand` 뒤에 `<button id="intro" title="이 페이지와 라이브러리·레슨 소개">ⓘ 소개</button>`.
- `main.ts`: `INTRO_PATH = 'lessons/intro.md'`. 버튼 클릭 시 `readme.show(INTRO_PATH)`와 `showPanel('readme')`. 그 외 상태는 건드리지 않는다.
- `loadLessons()`: 첫 로드에서 해시로 레슨을 찾지 못하면 `readme.show(INTRO_PATH)`를 부른다. ↻로 다시 읽을 때는 패널 내용을 바꾸지 않는다.
- `readme.ts`: 패널 위의 경로(`.readme-source`)를 누르면 그 Markdown 파일을 에디터에서 연다(Assumption 1의 "페이지에서도 편집"). 저장하면 기존 `editor.onSaved` 경로로 패널이 다시 그려진다.
- `readme.ts`: 읽기 실패도 늦게 온 응답이면 버린다(§4 Resource lifetime이 실패 경로에서도 성립하도록).

### 2.3 Platform Specifics
none. 서버는 이미 저장소 전체를 읽을 수 있다.

## 3. C++ Standard Evolution
N/A (C++ 변경 없음).

## 4. Edge Cases
- [x] Thread safety / memory ordering — N/A: 프론트엔드 단일 스레드, 서버 변경 없음
- [x] Resource lifetime — `ReadmePanel.show`는 늦게 온 응답을 버린다(`this.current !== path`). 소개를 누른 직후 레슨을 고르거나 그 반대여도 마지막으로 요청한 문서만 남는다
- [x] Platform differences — N/A
- [x] Template / ODR / UB — N/A
- [x] `lessons/intro.md`가 없거나 읽기 실패 — 패널이 `lessons/intro.md: <오류>`를 보여 준다(기존 동작). 페이지는 계속 쓸 수 있다
- [x] 해시가 있는 URL(`#span_timing`) — 지금처럼 그 레슨을 고르고 그 README를 띄운다. 소개로 덮지 않는다
- [x] 실행 중 소개 버튼 — README 탭으로만 전환하고 실행·출력·Timings는 계속된다. 첫 span이 오면 Timings 탭이 열리는 기존 동작도 그대로다
- [x] 좁은 화면 / 다크 테마 — 버튼은 기존 `.topbar` 줄바꿈 규칙과 `.markdown` 스타일을 따른다
- [x] `lessons.py check` — `lessons/` 바로 아래 Markdown 파일은 매니페스트로 읽지 않으므로 영향이 없다(확인: check가 경고 0)

## 5. Acceptance Criteria
| ID | Criterion | Verified by |
|---|---|---|
| AC-1 | `lessons/intro.md`에 §2.2 목차 1–6이 있고, 상대 링크가 모두 실제 파일을 가리킨다 | 링크 검사 스크립트(파일 존재) + 리뷰, 결과는 testrecord |
| AC-2 | 해시 없이 페이지를 열면 README 패널에 `lessons/intro.md`가 렌더링된다. `#span_timing`으로 열면 그 레슨의 README가 렌더링된다 | 브라우저 확인, 스크린샷 2장 |
| AC-3 | 레슨을 고른 상태에서 **ⓘ 소개**를 누르면 README 탭에 소개가 나오고, 에디터 탭·레슨 제목·URL 해시는 그대로다 | 브라우저 확인, 스크린샷 |
| AC-4 | 소개의 `.md` 링크는 패널에서, `include/...` 링크는 🔒 에디터 탭으로, 외부 링크는 새 탭으로 열린다 | 브라우저 확인 |
| AC-5 | 프론트엔드 `npm run build`와 `npm test`가 통과하고, `PlaygroundServer` CTest와 `lessons.py check`가 회귀 없이 통과한다 | 명령 출력, testrecord |
| AC-6 | §8 문서가 갱신되고 `lint_docs.py`가 exit 0 | 명령 출력 |

## 6. Out of Scope
- 소개 글에서 링크로 레슨을 *선택*하기(`#<id>` 링크 → 트리 선택). 지금은 링크가 README만 연다 — 필요하면 후속 KI로
- `lessons/` Markdown 링크 자동 검사 — KI-019
- 커리큘럼 내용 — 070-03, 070-04

## 7. Dependencies & Adapters
none (기존 `marked`, `DOMPurify`).

## 8. Documentation Updates
| Document | Section | Change |
|---|---|---|
| [`README.md`](/README.md) | `## Workflow` (새 섹션), preset 표 | Assumption 6: 작업 흐름 섹션, `linux-x64-playground-release` 행. Web Playground 항목에 소개 버튼 한 줄 |
| [`web/README.md`](/web/README.md) | Page | 상단 바 **ⓘ 소개**, 해시 없이 열면 소개 |
| [`lessons/README.md`](/lessons/README.md) | 구조, 웹 플레이그라운드에서 보이는 방식 | `intro.md`(페이지 소개 글, 페이지에서도 편집 가능) |

## 9. Technical Constraints
- Node.js 20+, 버전은 `package-lock.json` 고정 그대로. 새 의존성 없음

## 10. Context & References
- [ReadmePanel](/web/frontend/src/readme.ts), [main.ts](/web/frontend/src/main.ts), [index.html](/web/frontend/index.html)
- [070-02 스펙](/docs/specs/070_02_web_playground.md)

## 11. Implementation Plan
- [ ] Step 1: 브랜치 `feature/070-08-playground-intro`, 커밋되지 않은 루트 README 변경을 가져온다
- [ ] Step 2: `lessons/intro.md` 작성
- [ ] Step 3: `index.html` 버튼, `main.ts` 연결(클릭, 첫 로드)
- [ ] Step 4: §8 문서 갱신

## 12. Verification Plan
- [ ] `npm --prefix web/frontend run build`, `npm --prefix web/frontend test`
- [ ] `py -3 .agent/scripts/build.py --preset linux-x64-debug --test` (PlaygroundServer, lesson smoke tests)
- [ ] `py -3 tools/lessons.py check`, `py -3 .agent/scripts/lint_docs.py`
- [ ] 브라우저: AC-2–AC-4 스크린샷을 `docs/tasks/feature_070-08-playground-intro/screenshots/`에
- [ ] Every AC row has its evidence in `testrecord.md`

## History / Amendments
- 2026-10-29: 초안, 같은 날 승인
- 2026-10-29: 리뷰 반영(구현 중). 링크를 루트 기준으로, README 패널 경로 클릭으로 편집(Assumption 1을 실제로 가능하게), 실패 경로의 늦은 응답 무시, ↻가 실패를 반복해도 패널 유지. 범위 변경 없음
