---
id: 070-19
title: 플레이그라운드 화면 너비 조절과 줄바꿈 (가로 스크롤 없애기)
depends_on: [070-02]
unblocks: []
approved: 2026-11-10
---

# Spec 070-19: 플레이그라운드 화면 너비 조절과 줄바꿈 (가로 스크롤 없애기)

## 0. Assumptions (please review)
| # | Decision | Rejected alternative | Why |
|---|---|---|---|
| 1 | **목표**: 페이지 너비 1024px 이상에서, 기본 설정으로 **편집기와 오른쪽 패널(README, Output, Events, Timings, 070-17의 연습) 어디에도 가로 스크롤이 생기지 않는다**. 예외는 다이어그램 카드 안쪽(Assumption 7)과 Output 줄바꿈을 사용자가 끈 경우뿐이다 | — | 사용자 요청(2026-11-10): 왼쪽(코드)과 오른쪽(README, OUTPUT, …)이 잘려 좌우로 스크롤해야 한다 |
| 2 | **줄바꿈을 쓰고 80자 제한은 두지 않는다** | 소스·출력에 80자(또는 100자) 제한 | 사용자 요청의 첫째 안이 줄바꿈이고, 그것이 된다. 제한만으로는 풀리지 않는다: 오른쪽 패널의 최소 폭(320px)은 고정폭 글자 약 40자라 80자 줄도 넘치고, README의 표·출력·이벤트 설명은 글자 수 제한의 대상이 아니다. 지금 레슨 소스에는 100자를 넘는 줄(한/영 주석)이 많아 모두 고쳐야 한다 |
| 3 | **편집기**: Monaco `wordWrap: 'on'`, `wrappingIndent: 'indent'`(이어진 줄을 한 단계 들여 써서 새 줄과 구분), `wrappingStrategy: 'advanced'`(한글처럼 폭이 다른 글자를 실제 폭으로 잼). 탭 줄 끝의 `↩` 버튼과 Alt+Z로 끄고 켠다. 기본 켬, 선택은 브라우저 저장소 `atugcc.wrap.editor` | `wordWrap: 'bounded'` + 열 제한 | 패널 너비가 바뀔 때 저절로 맞는 것이 목적이다. `simple` 전략은 한글 폭을 틀리게 잡아 줄이 넘친다 |
| 4 | **Output**: `white-space: pre-wrap; overflow-wrap: anywhere`, `min-width: max-content`를 뺀다. 패널 머리의 `↩` 토글로 끄면 지금처럼 `pre`(그때만 가로 스크롤). 기본 켬, `atugcc.wrap.output` | 늘 줄바꿈 | 터미널 출력의 표·트리(`formatTerminal`, `formatTimings`, GoogleTest 요약)는 줄을 바꾸면 열이 어긋난다. 정렬을 보고 싶을 때 끌 수 있어야 한다. [diagrams.md](/.agent/rules/diagrams.md) §3의 "터미널 출력: `white-space: pre`, 가로 스크롤" 줄을 이 규칙으로 바꾼다(§8) |
| 5 | **README**: 코드 블록 `pre`를 `pre-wrap`으로, 인라인 `code`와 긴 URL은 `overflow-wrap: anywhere`, 표 칸은 줄바꿈(한글은 `word-break: keep-all`로 낱말 중간에서 끊지 않음, 그래도 넘치는 긴 토큰은 `overflow-wrap: anywhere`). 표는 `width: 100%` 안에서 칸이 줄어든다 | 표만 가로 스크롤(지금) | 레슨 README의 표(비교 표)가 가장 자주 잘린다 |
| 6 | **Events·Timings 표**: 글자 칸(설명, 라벨, 파일:줄)은 줄바꿈, 숫자 칸은 `nowrap`. Timings는 패널이 좁으면(컨테이너 쿼리, 520px 미만) `min`, `max`, `p50` 열을 숨기고 그 값은 행의 ▸ 상세에 보인다 | 모든 열을 늘 보임 | Timings는 열이 10개라 320–500px에서는 줄바꿈만으로 들어가지 않는다. 숨기는 열은 상세에서 볼 수 있어 잃는 정보가 없다 |
| 7 | **다이어그램은 지금 규칙 그대로**: 80% 아래로 줄이지 않고, 넓은 다이어그램은 **카드 안에서만** 가로로 스크롤한다(diagrams.md §3). 패널 자체는 가로로 스크롤하지 않는다 | 패널 폭에 맞게 줄임 | 다이어그램은 그림이라 줄바꿈이 없고, 너무 줄이면 글자를 읽을 수 없다(diagrams.md §3의 이유). "전체 크기"가 이미 있다 |
| 8 | **세 칼럼의 너비를 끌어서 바꾼다**: 사이드바|편집기, 편집기|오른쪽 사이에 끌기 막대(폭 6px, 가운데 선). 마우스·터치 끌기, 포커스 뒤 ←/→로 16px씩, 두 번 누르면 기본값. 최소 폭: 사이드바 160px, 편집기 360px, 오른쪽 280px. 창 크기가 바뀌면 최소 폭 안으로 다시 맞춘다. 값(사이드바 px, 오른쪽 비율)은 `atugcc.layout`. 저장소가 막히면 기본값 | 고정 폭(지금: 260px / 나머지 / 42%) | 줄바꿈만으로는 긴 코드가 여러 줄로 쪼개져 읽기 어렵다. 지금 볼 쪽을 넓히는 것이 가장 직접적인 방법이다 |
| 9 | **편집기 탭 줄**: `overflow-x: auto` 대신 `flex-wrap: wrap`(탭이 많으면 둘째 줄) | 지금처럼 스크롤 | 같은 목표(가로 스크롤 없음). 레슨의 탭은 대개 10개 아래다 |
| 10 | 900px 아래의 한 칼럼 배치(지금의 `@media`)는 그대로 두고 끌기 막대만 숨긴다 | — | 좁은 화면 배치는 이 작업의 대상이 아니다 |
| 11 | Monaco의 줄 끝 장식(Timings의 `⏱ avg ×n`, 070-06)은 줄바꿈된 줄의 마지막 줄 끝에 붙는다. 표시는 그대로 둔다 | 장식을 줄 위로 | Monaco의 기본 동작이고 읽는 데 문제가 없다(AC-5에서 확인) |
| 12 | 070-16·070-17이 더하는 화면(diff 편집기, 연습 탭)도 같은 규칙: diff 편집기 `wordWrap: 'on'`(Monaco diff의 `diffWordWrap`), 연습 탭은 README와 같은 Markdown 규칙 | — | 이 작업이 그 둘 뒤에 오므로(진행 순서) 함께 맞춘다 |

## 1. Objective
지금 플레이그라운드는 세 칼럼의 폭이 고정이고(`260px | 1fr | minmax(320px, 42%)`), 편집기는 줄바꿈이 없으며 Output은 `white-space: pre` + `min-width: max-content`라서, 긴 코드 줄·출력·README의 표가 잘리고 좌우로 스크롤해야 한다. 이 작업은 칼럼 폭을 끌어서 바꾸게 하고, 편집기와 오른쪽 패널이 패널 폭 안에서 줄을 바꾸게 해 가로 스크롤을 없앤다.

## 2. Requirement Details

### 2.1 Public API Surface
없음(C++·서버 API 변경 없음).

### 2.2 Internal Implementation
| 곳 | 바꾸는 것 |
|---|---|
| [`web/frontend/index.html`](/web/frontend/index.html) | 칼럼 사이 끌기 막대 둘(`role="separator"`, `aria-orientation="vertical"`, `tabindex="0"`, `aria-valuenow`), 탭 줄의 `↩`, Output 패널 머리의 `↩` |
| [`web/frontend/src/theme.css`](/web/frontend/src/theme.css) | `.layout`의 칼럼을 CSS 변수(`--sidebar-w`, `--right-w`)로, 끌기 막대, `#output` 줄바꿈 두 상태, `.markdown pre`·`code`·표 칸, Events·Timings 칸, Timings 컨테이너 쿼리, `.tabs` 줄바꿈 |
| `web/frontend/src/layout.ts` (새) | 끌기·키보드·두 번 누르기·최소 폭 맞추기·저장. 계산은 DOM 없는 함수(`clampLayout(viewport, want) → widths`)로 빼서 시험 |
| [`web/frontend/src/editor.ts`](/web/frontend/src/editor.ts) | Monaco 옵션(Assumption 3), 토글, Alt+Z 명령 |
| [`web/frontend/src/output.ts`](/web/frontend/src/output.ts), [`timings.ts`](/web/frontend/src/timings.ts) | 줄바꿈 토글 클래스, 숨기는 열의 상세 표시 |
| [`web/frontend/src/i18n.ts`](/web/frontend/src/i18n.ts) | 새 버튼의 제목(두 언어) |
| 프런트엔드 테스트 | `clampLayout`(최소 폭, 창 줄어듦, 저장값 깨짐), 토글 저장(저장소 막힘 포함) |

### 2.3 Platform Specifics
브라우저: 지금 쓰는 Chromium 계열(Edge, Chrome)과 Firefox. 컨테이너 쿼리와 `overflow-wrap: anywhere`는 셋 다 지원한다. 그 밖 none.

## 3. C++ Standard Evolution
N/A.

## 4. Edge Cases
- [x] Thread safety — N/A.
- [x] Resource lifetime — 끌기 중 `pointermove`는 `pointerup`/`pointercancel`에서 반드시 풀고 포인터 캡처를 놓는다.
- [x] Platform differences — §2.3. Windows의 고배율(125%, 150%)에서도 막대가 잡힌다(AC-4에서 한 번).
- [x] Template instantiation / concept constraints — N/A.
- [x] ODR — N/A.
- [x] Undefined behaviour — N/A.
- [x] 창이 세 최소 폭의 합(800px)보다 좁아짐 — 900px 아래는 한 칼럼 배치라 끌기 막대가 없다. 900–1000px에서는 오른쪽 → 사이드바 순으로 최소 폭까지 줄인다.
- [x] 저장된 값이 깨짐·범위 밖 — 무시하고 기본값.
- [x] 줄바꿈과 줄 번호 — Monaco는 줄 번호를 논리 줄에 붙인다. 진단·이벤트의 줄 이동은 논리 줄이라 그대로 맞는다.
- [x] 매우 긴 토큰(공백 없는 경로, base64) — `overflow-wrap: anywhere`가 아무 곳에서나 끊는다(Output, README). 편집기는 Monaco가 끊는다.
- [x] ANSI 색 구간이 줄바꿈에 걸침 — `span`이 줄을 넘어 이어질 뿐이라 색이 유지된다.
- [x] Output 줄바꿈 토글과 스크롤 위치 — 토글 뒤 맨 아래를 보고 있었으면 맨 아래에 남는다(지금의 따라가기 규칙).

## 5. Acceptance Criteria
| ID | Criterion | Verified by |
|---|---|---|
| AC-1 | 1280×800과 1024×768에서, 레슨 `format_text`, `span_timing`, `testing`, `device_state_machine`(그리고 070-16·070-17이 있으면 연습 탭, diff 편집기)을 Run한 뒤 README·Output·Events·Timings·연습 패널과 편집기 각각에서 `scrollWidth ≤ clientWidth`이다(다이어그램 카드 안쪽 제외). 오른쪽 칼럼을 최소 폭(280px)으로 끌어 놓은 상태에서도 같다 | 헤드리스 브라우저 측정 스크립트(패널마다 두 값), 스크린샷 |
| AC-2 | 편집기의 긴 줄이 패널 안에서 바뀌고 이어진 줄은 들여 쓰여 있다. `↩`/Alt+Z로 끄면 지금처럼 가로 스크롤이 생기고, 새로 고침 뒤에도 선택이 남는다 | 헤드리스 브라우저, 프런트엔드 테스트 |
| AC-3 | Output `↩`를 끄면 `pre`(열이 맞는 표, 가로 스크롤), 켜면 줄바꿈이다. 기본은 켬 | 헤드리스 브라우저 스크린샷 2장(`span_timing`의 `formatTimings` 표) |
| AC-4 | 끌기 막대가 마우스와 키보드(←/→, 두 번 누르기)로 동작하고 최소 폭을 지키며, 새로 고침 뒤 폭이 남고, 저장소가 막히면 기본값이다. 창을 줄이면 최소 폭 안으로 맞춰진다 | 프런트엔드 테스트(`clampLayout`), 헤드리스 브라우저 |
| AC-5 | 진단 표시, 이벤트 줄 이동, Timings 줄 끝 장식(`⏱`), 070-15의 테스트 실패 표시가 줄바꿈 상태에서도 맞는 줄에 붙는다 | 헤드리스 브라우저 스크린샷 |
| AC-6 | 다이어그램은 80% 아래로 줄지 않고 넓은 것은 카드 안에서만 스크롤한다(지금과 같음) | 헤드리스 브라우저(기존 다이어그램 확인과 같은 방법) |
| AC-7 | `npm --prefix web/frontend test`, `npm run build`(사전 누락 없음), `PlaygroundServer`가 통과하고 §8 문서가 결과와 맞으며 `lint_docs.py`가 exit 0이다 | 명령 출력 |

## 6. Out of Scope
- 900px 아래 배치 개선, 사이드바 접기 — 계획 없음(필요하면 KI)
- 소스·출력의 글자 수 제한 — 하지 않는다(Assumption 2)
- 글꼴 크기 조절 — 계획 없음(브라우저 확대로 됨)

## 7. Dependencies & Backends
없음(새 패키지 없음).

## 8. Documentation Updates
| Document | Section | Change |
|---|---|---|
| [`.agent/rules/diagrams.md`](/.agent/rules/diagrams.md) | §3 Viewer policy | 터미널·ASCII 출력 줄: 기본은 줄바꿈(`pre-wrap`), 정렬을 볼 때 끌 수 있고 그때만 가로 스크롤. "페이지는 가로로 스크롤하지 않는다"를 패널 단위로 |
| [`web/README.md`](/web/README.md) | Page | 끌기 막대, 편집기·Output 줄바꿈 토글, Timings의 좁은 폭 열 |
| [`lessons/README.md`](/lessons/README.md) | 웹 플레이그라운드에서 보이는 방식 | 줄바꿈 토글 한 줄 |
| [`docs/agent_todo.md`](/docs/agent_todo.md) | Phase 7 | 070-19 줄 |

## 9. Technical Constraints
- 프런트엔드: 지금의 Vite + TypeScript + Monaco(버전 고정, 새 패키지 없음)
- 브라우저: Chromium 계열, Firefox 최신

## 10. Context & References
- [`web/frontend/src/theme.css`](/web/frontend/src/theme.css)(`.layout`, `#output`, `.markdown`, 표), [`web/frontend/index.html`](/web/frontend/index.html), [`web/frontend/src/editor.ts`](/web/frontend/src/editor.ts)(`monaco.editor.create` 옵션)
- [.agent/rules/diagrams.md](/.agent/rules/diagrams.md) §3
- [070-02 스펙](/docs/specs/070_02_web_playground.md)(페이지 배치), [070-06 스펙](/docs/specs/070_06_long_run_timings.md)(Timings, 줄 끝 장식)

## 11. Implementation Plan
- [ ] Step 1: `layout.ts`와 끌기 막대, CSS 변수, 테스트
- [ ] Step 2: 편집기 줄바꿈과 토글
- [ ] Step 3: Output·README·Events·Timings·탭 줄 CSS와 토글, Timings 좁은 폭
- [ ] Step 4: 측정 스크립트(AC-1)와 스크린샷
- [ ] Step 5: §8 문서

## 12. Verification Plan
- [ ] `npm --prefix web/frontend run build`, `npm --prefix web/frontend test`
- [ ] `ctest -R PlaygroundServer` (`linux-x64-debug`)
- [ ] 헤드리스 브라우저(AC-1–AC-6)
- [ ] `lint_docs.py` exit 0
- [ ] 모든 AC 행의 증거가 `testrecord.md`에

## History / Amendments
- 2026-11-10: 초안
- 2026-11-10: 승인(사용자, 070-07·070-16·070-17·070-18과 함께)
