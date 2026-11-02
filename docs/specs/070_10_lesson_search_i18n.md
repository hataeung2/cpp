---
id: 070-10
title: 플레이그라운드 레슨·기능 검색과 한/영 전환
depends_on: [070-02, 070-08]
unblocks: [070-03]
approved: 2026-11-02
---

# Spec 070-10: 플레이그라운드 레슨·기능 검색과 한/영 전환

## 0. Assumptions (please review)
| # | Decision | Rejected alternative | Why |
|---|---|---|---|
| 1 | 070-03보다 먼저 한다(사용자 결정 2026-11-02). 이 작업은 **형식과 페이지 기능**만 만든다. 영어 필드, 태그 어휘, README 영어판 규칙을 정하고, 지금 있는 매니페스트(트랙 2, 레슨 4, 유닛 2)를 그 형식으로 채운다 | 070-03 안에서 같이 하기 | 070-03이 레슨을 여러 개 만든 다음에 형식을 정하면 그 레슨을 모두 다시 고쳐야 한다. 페이지 UI(`web/`)와 레슨 내용(`lessons/`)은 완료 조건과 테스트도 다르다 |
| 2 | 매니페스트에 영어 키 `title_en`, `summary_en`을 평평하게 더한다(`track.toml`, `lesson.toml`, `unit.toml`). 없으면 한국어로 대신 보여 준다 | `[en]` 테이블, 언어별 매니페스트 파일 | 언어는 둘뿐이다. 한국어 줄 바로 아래에 있어야 고칠 때 같이 고친다. `lessons/CMakeLists.txt`의 정규식(`id`, `sources`, `profile`, `timeout`)과 겹치지 않는다(§2.2 확인 항목) |
| 3 | `title_en`이 없으면 `lessons.py check`가 **WARN**을 낸다. `summary`가 있는데 `summary_en`이 없을 때도 WARN이다. ERROR로 하지 않는다 | ERROR, 아무 검사 없음 | 070-03 이후의 새 레슨이 영어 제목을 빠뜨리지 않게 알리되, 빌드와 실행은 막지 않는다 |
| 4 | **태그 어휘 파일** `lessons/tags.toml`을 둔다. 태그마다 `ko`, `en` 표시 이름과 `aliases`(검색 동의어: `std::jthread`, `동시성` 등)를 적는다. 매니페스트의 `tags`는 어휘의 키만 쓴다. 어휘에 없는 태그는 WARN이다 | 자유 태그(지금처럼) | "기능 검색"이 되려면 같은 기능을 같은 태그로 불러야 한다. 어휘가 없으면 `thread`/`threads`/`concurrency`처럼 흩어진다. 또 "스레드"로 찾아도 `thread` 태그 레슨이 나와야 하고, 태그 칩을 두 언어로 보여 줘야 한다 |
| 5 | 검색은 **브라우저 안에서** 인덱스(`/api/lessons`)만으로 한다. 대상: 레슨 id, 제목·요약(두 언어), 태그와 태그의 표시 이름·별칭, `uses`(`unit:…`, `lib:atugcc/…`), 레슨이 속한 트랙의 제목. 유닛도 id, 제목·요약, `files`, `uses`로 찾는다 | 서버 쪽 검색 API, 레슨 코드 전체 검색 | 인덱스는 작고 이미 페이지에 있다. 코드 전체를 찾으면 `std::`가 들어간 거의 모든 레슨이 걸려 결과가 쓸모없다. 무엇을 다루는 레슨인지는 사람이 고른 태그와 `uses`가 더 정확히 말해 준다 |
| 6 | 검색어는 공백으로 나눈 낱말 **모두**가 맞아야 한다(AND). NFC로 정규화하고 소문자로 바꾼 뒤 부분 문자열로 비교한다. 입력하는 동안 바로 거른다 | OR, 퍼지 검색, 초성 검색 | 낱말을 더할수록 결과가 줄어야 예측할 수 있다. 퍼지 검색과 초성 검색은 레슨 수가 수십 개가 될 때까지 필요 없다 |
| 7 | 검색창은 왼쪽 사이드바 머리(레슨 ↻ 옆)에 둔다. `/` 키로 포커스(에디터나 입력란에 포커스가 없을 때만), Esc로 지우기, Enter로 보이는 첫 레슨 열기 | 상단 바의 명령 팔레트(Ctrl+K) | Ctrl+K는 Monaco의 코드 단축키와 겹친다. 결과가 트리 자체이므로 트리 바로 위가 자연스럽다 |
| 8 | 레슨을 고르면 README 패널 위에 그 레슨의 **태그 칩**을 보여 준다. 칩을 누르면 검색어가 그 태그가 된다 | 트리 항목마다 태그 표시 | 트리는 좁아서 칩이 들어가면 제목이 잘린다. "이 기능을 쓰는 다른 레슨"으로 가는 길은 README를 읽는 중에 필요하다 |
| 9 | UI 문자열은 `web/frontend/src/i18n.ts` 한 곳에 `ko`와 `en` 사전으로 둔다. `en`의 타입은 `Record<keyof typeof ko, string>`이라 키가 빠지면 `tsc`가 실패한다. `index.html`의 고정 문구는 `data-i18n`, `data-i18n-title` 속성으로 바꾼다 | i18n 라이브러리(i18next 등) | 문자열이 100개 남짓이고 언어는 둘이다. 의존성을 더하지 않고 타입 검사로 빠진 번역을 막는다 |
| 10 | 상단 바 ◐ 옆에 언어 버튼을 둔다(한국어일 때 `EN`, 영어일 때 `한`). 고른 언어는 `localStorage`의 `atugcc.lang`에 둔다. 저장된 값이 없으면 `navigator.language`가 `ko`로 시작할 때 한국어, 아니면 영어다 | 항상 한국어로 시작, URL `?lang=` | 사람마다 다른 편의 설정이라 브라우저 저장소가 맞다(테마와 같은 방식). 저장소가 막혀 있어도 페이지는 기본 언어로 동작한다 |
| 11 | 언어를 바꿔도 **작업 상태는 그대로**다. 에디터 탭과 수정 내용, 실행 중인 run, Output·Events 내용, URL 해시는 바뀌지 않는다. 다시 그리는 것은 고정 문구, 트리(검색어와 선택 유지), 상단 바 레슨 제목, README 패널, Timings 헤더, 상태 문구다 | 언어 전환 시 페이지 다시 읽기 | 다시 읽으면 저장하지 않은 수정과 실행 중인 run을 잃는다 |
| 12 | README 영어판은 같은 폴더의 `README.en.md`다. 영어일 때 있으면 그것을, 없으면 한국어 README를 보여 주고 위에 "이 README는 한국어로만 있습니다"를 영어로 표시한다. 소개 글도 `lessons/intro.en.md`로 같은 규칙을 따른다 | README 안에 두 언어를 섞어 쓰기 | 한 파일에 섞으면 둘 다 읽기 어렵다. 파일이 따로 있어야 090-04 링크 검사가 각각 검사한다 |
| 13 | 번역 범위: 이 작업은 매니페스트 영어 필드 전부, `tags.toml`, `lessons/intro.en.md`를 쓴다. 레슨·유닛 README 영어판과 기존 레슨 내용 고치기는 **레슨 작업(070-03부터)이 기존 레슨과 함께** 한다(사용자 결정 2026-11-02). `README.en.md`가 없어도 check는 경고하지 않는다 | 기존 README 6개도 이번에 번역 | 범위를 형식과 기능에 묶어 둔다. 레슨 내용을 고칠 때 번역도 같이 해야 내용과 어긋나지 않는다 |
| 14 | 레슨 프로그램이 내는 출력(stdout, stderr, 로그, Tracer 이벤트, Mermaid 다이어그램 문구)은 **언제나 영어**로 쓰고, 페이지 언어에 따라 바꾸지 않는다(사용자 결정 2026-11-02). 이 작업은 이 규칙을 [`lessons/README.md`](/lessons/README.md)에 적기만 한다. 지금 한국어를 출력하는 레슨은 레슨 작업이 Assumption 13과 함께 고친다. 빌드 로그와 코드 주석은 번역하지 않는다 | 출력을 언어 설정에 맞추기, 이 작업에서 기존 출력도 고치기 | 출력은 C++ 프로그램이 정하므로 언어 하나로 고정하는 편이 단순하다. 기존 레슨 코드를 고치는 일은 레슨 작업의 몫이다 |
| 15 | 인덱스 `version`은 1로 둔다. 키를 더하기만 하고(`titleEn`, `summaryEn`, `readmeEn`, 최상위 `tags`) 기존 키는 바꾸지 않는다 | `version: 2` | 기존 소비자(페이지, `runner.py`, `lint_docs.py`)가 읽는 키가 그대로다 |

## 1. Objective
레슨이 늘어나도(070-03, 070-04, 엔진 레슨) 플레이그라운드에서 원하는 레슨을 바로 찾고, 한국어를 읽지 못하는 사람도 페이지를 쓸 수 있게 한다.
- **레슨명 검색**: 제목 일부로 레슨을 찾는다.
- **기능 검색**: `jthread`, `source_location`, `logger.hpp`, "스레드"처럼 C++ 기능이나 라이브러리 헤더 이름으로, 그것을 다루는 레슨과 유닛을 찾는다.
- **한/영 전환**: 페이지 UI, 트랙·레슨·유닛 제목과 요약, 태그를 두 언어로 보여 준다. README는 영어판이 있으면 영어판을 보여 준다.

070-03이 이 형식(영어 필드, 태그 어휘)으로 레슨을 만들 수 있게 먼저 정해 둔다.

## 2. Requirement Details

### 2.1 Public API Surface
C++ API 변경 없음. 웹 서버 API는 `GET /api/lessons`의 응답에 키를 더하기만 한다(§2.3).

### 2.2 매니페스트와 태그 어휘
```toml
# lessons/tracks/01_essentials/02_thread_and_log/lesson.toml
id         = "thread_and_log"
title      = "std::jthread 작업 스레드와 로거 연동"
title_en   = "std::jthread workers with the logger"
summary    = "두 개의 PeriodicWorker 스레드와 Logger를 활용한 주기적 작업 및 안전한 협력적 취소"
summary_en = "Periodic work on two PeriodicWorker threads with the Logger, and cooperative cancellation"
sources    = ["main.cpp"]
uses       = ["unit:jthread_worker", "lib:atugcc/core/logger.hpp"]
tags       = ["thread", "log"]
```
`track.toml`과 `unit.toml`도 같은 두 키를 받는다.

```toml
# lessons/tags.toml — 태그 키: [a-z0-9_]+ (레슨 id와 같은 규칙)
[thread]
ko      = "스레드"
en      = "Thread"
aliases = ["std::thread", "std::jthread", "jthread", "stop_token", "동시성", "concurrency"]

[log]
ko      = "로그"
en      = "Logging"
aliases = ["logger", "로거", "logging"]
```
- 지금 쓰는 태그 9개(`lambda`, `capture`, `move`, `thread`, `log`, `performance`, `span`, `tracer`, `state`)를 모두 어휘에 넣는다.
- 어휘에 있지만 아무 레슨도 쓰지 않는 태그는 괜찮다(070-03이 미리 넣어 둘 수 있다).

`tools/lessons.py check`가 더하는 검사:

| 조건 | 수준 |
|---|---|
| `title_en`, `summary_en`이 문자열이 아님 | ERROR (기존 `str_field`) |
| `title_en`이 없음 / `summary`는 있는데 `summary_en`이 없음 | WARN |
| `tags.toml`을 읽을 수 없음, 표의 키가 `[a-z0-9_]+`이 아님, `ko`나 `en`이 없거나 문자열이 아님, `aliases`가 문자열 목록이 아님 | ERROR |
| 매니페스트의 태그가 어휘에 없음 | WARN (줄 번호 포함) |
| 같은 별칭(정규화 후)이 두 태그에 있음 | WARN |
| `tags.toml`이 없음 | WARN 한 번 (태그 검사는 건너뜀) |

확인 항목: 기존 `check_cmake_view`가 `title_en`, `summary_en`이 든 매니페스트를 CMake 정규식으로 읽어도 결과가 TOML 값과 같아야 한다(AC-1).

### 2.3 레슨 인덱스 (`tools/lessons.py index`, `/api/lessons`)
더하는 키(없으면 `null`):
- 트랙: `titleEn`, `summaryEn`
- 레슨: `titleEn`, `summaryEn`, `readmeEn`(`README.en.md`가 있을 때 그 경로)
- 유닛: `titleEn`, `summaryEn`, `readmeEn`
- 최상위 `tags`: `{"<tag>": {"ko": …, "en": …, "aliases": […]}}`. 어휘가 없으면 `{}`

### 2.4 프론트엔드
**`i18n.ts`** (새 파일)
- `type Lang = 'ko' | 'en'`, `ko` 사전(`as const`), `en: Record<keyof typeof ko, string>`.
- `t(key, params?)`: `{name}` 자리를 채운다. `lang()`, `setLang(l)`, `onLangChange(cb)`.
- `localized(ko: string, en: string | null): {text, fallback}`: 영어인데 `en`이 비면 한국어와 `fallback: true`.
- `applyStatic(root)`: `data-i18n`(텍스트), `data-i18n-title`(툴팁), `data-i18n-placeholder`를 채우고 `<html lang>`을 바꾼다.
- 언어 결정과 저장: Assumption 10. `localStorage` 읽기와 쓰기는 모두 `try/catch`로 감싼다.

**지금 있는 한국어 문자열**: `main.ts`, `lessonTree.ts`, `editor.ts`, `timings.ts`, `diagrams.ts`, `events.ts`, `readme.ts`, `api.ts`, `ansi.ts`, `diagnostics.ts`, `output.ts`, `index.html`의 화면 문구를 모두 `t()`나 `data-i18n`으로 옮긴다. 이 작업이 끝나면 `i18n.ts` 밖의 `src/*.ts`와 `index.html`에는 한글이 없다(AC-7의 검사).

**`search.ts`** (새 파일, DOM 없는 순수 함수)
- `normalize(s)`: NFC, 소문자, 연속 공백 하나로.
- `lessonHaystack(lesson, track, tags)`, `unitHaystack(unit)`: Assumption 5의 필드를 정규화해 한 문자열로 잇는다(필드 사이 구분자 `\u0000`이라 두 필드에 걸친 일치가 생기지 않는다).
- `matches(haystack, query)`: 낱말 모두가 부분 문자열이면 참. 빈 검색어는 모두 참.

**`lessonTree.ts`**
- `render(index, selected, query)`: 맞지 않는 레슨·유닛은 숨기고, 보이는 레슨이 없는 트랙과 보이는 유닛이 없는 "유닛" 그룹도 숨긴다. 검색어가 있으면 숨긴 그룹을 접지 않고 펼쳐 보여 준다.
- 결과 수(`레슨 n · 유닛 m`)를 검색창 아래에 보여 준다. 아무것도 없으면 "검색 결과 없음".
- 제목과 요약은 `localized()`로 고른다. 영어 모드에서 한국어로 대신 보여 준 항목은 `fallback` 클래스(흐린 글씨)다.
- 선택한 레슨이 검색으로 숨겨져도 선택과 에디터, README는 그대로다. 검색어를 지우면 다시 선택된 채로 보인다.

**`main.ts`**
- 검색창 `input` 이벤트마다 트리를 다시 거른다(인덱스를 다시 받지 않는다). ↻는 검색어를 지우지 않는다.
- 키: Assumption 7. `KeyboardEvent.isComposing`이 참이면(한글 IME 조합 중) Enter와 Esc를 처리하지 않는다.
- 언어 버튼: `setLang()` 뒤에 Assumption 11의 부분만 다시 그린다. 실행 중이면 상태 문구는 다음 갱신 때 새 언어로 나온다.
- README 경로: 영어이고 `readmeEn`이 있으면 그것, 아니면 `readme`. 소개는 `lessons/intro.en.md`를 먼저 읽고, 읽지 못하면 `lessons/intro.md`로 대신한다.

**`readme.ts`**
- `show(path, {fallbackNotice})`: `fallbackNotice`면 내용 위에 안내 줄을 붙인다.
- 레슨일 때 태그 칩 줄(Assumption 8). 칩 글자는 현재 언어의 표시 이름, 툴팁은 태그 키. 누르면 `onTag(tag)` 콜백으로 검색어를 그 태그 키로 바꾼다.

### 2.5 내용
- 트랙 2, 레슨 4, 유닛 2의 `title_en`, `summary_en`.
- `lessons/tags.toml`: 태그 9개, 각 태그에 쓸모 있는 별칭(C++ 이름, 한국어 이름).
- `lessons/intro.en.md`: `lessons/intro.md`의 영어판. 목차와 링크는 같다. 링크가 README를 가리키면 그대로 한국어 README로 둔다(영어판이 없으므로).

### 2.6 Platform Specifics
none. 서버는 WSL/Linux에서 그대로 돌고, 바뀌는 것은 인덱스 키뿐이다. `tags.toml`은 UTF-8이며 `tomllib`이 읽는다.

## 3. C++ Standard Evolution
N/A (C++ 변경 없음).

## 4. Edge Cases
- [x] Thread safety / memory ordering — N/A: 프론트엔드 단일 스레드. 서버는 인덱스를 요청마다 새로 만든다(기존)
- [x] Resource lifetime — README를 언어 전환 직후에 다시 읽는 동안 다른 레슨을 고르면, 기존 규칙(`this.current !== path`면 버림)대로 마지막 요청만 남는다. 영어 → 한국어로 바로 바꿔도 같다
- [x] Platform differences — N/A
- [x] Template / ODR / UB — N/A
- [x] 한글 IME 조합 중 — `input` 이벤트는 조합 중에도 와서 바로 거른다. 조합 중의 Enter는 글자를 확정할 뿐이며 레슨을 열지 않는다(`isComposing`)
- [x] 유니코드 정규화 — 매니페스트는 NFC지만 붙여 넣은 검색어가 NFD일 수 있다. 양쪽 모두 NFC로 바꾼다
- [x] 대소문자와 기호 — `std::jthread`, `logger.hpp`처럼 `:`와 `.`가 든 낱말은 그대로 부분 문자열로 비교한다. 정규식으로 해석하지 않는다(검색어에 `(`가 있어도 오류 없음)
- [x] 공백만 있는 검색어 — 빈 검색어와 같다(전부 보임)
- [x] 해시로 연 레슨이 검색으로 숨겨짐 — 열린 채로 둔다. 트리에서만 보이지 않는다
- [x] 저장소가 막힘(사생활 보호 창 등) — 언어는 기본값으로 시작하고, 버튼으로 바꾼 언어는 그 페이지에서만 유지된다. 예외가 밖으로 나가지 않는다
- [x] 영어 필드가 없는 새 레슨(070-03이 빠뜨림) — 영어 모드에서 한국어 제목을 흐리게 보여 주고 check가 WARN을 낸다. 페이지는 계속 쓸 수 있다
- [x] `tags.toml`의 태그 키가 별칭에 다시 나옴 — 중복 WARN 대상이 아니다(같은 태그 안). 다른 태그의 키와 같은 별칭은 WARN이다
- [x] 매니페스트 오류로 인덱스가 일부만 있음 — 검색은 있는 항목만 대상으로 한다. `problems` 상자는 거르지 않고 늘 보인다
- [x] 실행 중 언어 전환 — run, SSE, Timings 집계는 끊기지 않는다. Timings 표는 헤더와 단위 문구만 새 언어로 다시 그린다

## 5. Acceptance Criteria
| ID | Criterion | Verified by |
|---|---|---|
| AC-1 | `lessons.py check`가 `title_en`, `summary_en`을 받고, 없으면 WARN, 문자열이 아니면 ERROR를 낸다. 영어 키가 든 매니페스트에서 CMake 정규식이 읽은 값이 TOML 값과 같다 | `tools/test_lessons.py` 새 케이스 |
| AC-2 | `tags.toml`의 §2.2 검사 6가지가 각각 표의 수준으로 나온다(깨진 경우 하나씩) | `tools/test_lessons.py` 새 케이스 |
| AC-3 | 인덱스에 §2.3 키가 있고(없으면 `null`, 어휘 없으면 `tags: {}`), 기존 키와 값은 바뀌지 않는다 | `tools/test_lessons.py`(인덱스 비교), `PlaygroundServer` CTest 회귀 없음 |
| AC-4 | 저장소의 `py -3 tools/lessons.py check`가 ERROR 0, WARN 0이다(모든 매니페스트에 영어 필드, 모든 태그가 어휘에 있음) | 명령 출력, testrecord |
| AC-5 | `search.ts`: AND 결합, 대소문자 무시, NFC 정규화, 한국어 별칭으로 태그 찾기("스레드" → `thread_and_log`), `lib:` 경로로 찾기(`logger.hpp`), 유닛 찾기, 필드 경계를 넘는 일치 없음, 정규식 문자가 든 검색어 | vitest `test/search.test.ts` |
| AC-6 | 검색 UI: 입력하면 트리가 걸러지고 빈 트랙이 숨고 결과 수가 나온다. 결과가 없으면 안내가 나온다. `/`는 에디터 밖에서만 검색창으로 간다. Esc가 지운다. Enter가 첫 레슨을 연다. 한글 조합 중 Enter는 레슨을 열지 않는다. 태그 칩을 누르면 검색어가 그 태그가 된다 | 브라우저 확인, 스크린샷(검색 중, 결과 없음, 태그 칩) |
| AC-7 | `en` 사전에 키가 빠지면 `tsc`가 실패한다. `i18n.ts` 밖의 `src/*.ts`와 `index.html`에 한글이 없다 | `npm run build`(빠진 키를 일부러 넣어 실패 확인, testrecord), vitest `test/i18n.test.ts`(한글 검사, `t()` 치환, `localized()` 대체) |
| AC-8 | 언어 전환: 고정 문구, 트리, 레슨 제목, README(영어판 또는 안내 줄), 소개가 영어로 바뀐다. 수정한 에디터 탭(●), 실행 중인 run, Output 내용, URL 해시는 그대로다. 다시 열면 고른 언어로 시작한다. 저장소가 막혀도 오류 없이 동작한다 | 브라우저 확인, 스크린샷(영어 화면, 실행 중 전환), 저장소 차단은 vitest(`localStorage`가 던지는 jsdom) |
| AC-9 | `npm run build`, `npm test`, `PlaygroundServer` CTest, 레슨 스모크 테스트, `tools/test_lessons.py`가 통과한다 | 명령 출력, testrecord |
| AC-10 | §8 문서가 갱신되고 `lint_docs.py`가 exit 0이다(`intro.en.md` 링크 포함) | 명령 출력 |

## 6. Out of Scope
- 레슨·유닛 README 영어판, 기존 레슨 내용 고치기 — Assumption 13, 070-03(기존 레슨과 함께)
- 지금 한국어를 출력하는 레슨 4개와 유닛 2개의 출력을 영어로 — Assumption 14, 070-03
- 레슨 코드 내용 전체 검색, 검색 결과 강조 표시, 퍼지·초성 검색 — 레슨 수가 늘어 필요해지면 그때 KI로 등록한다
- 공개 배포 — 070-05
- 세 번째 언어 — 새 작업(형식이 언어 둘을 전제한다)

## 7. Dependencies & Backends
none. 새 npm 의존성 없음. Python은 표준 라이브러리(`tomllib`, `unicodedata`)만.

## 8. Documentation Updates
| Document | Section | Change |
|---|---|---|
| [`lessons/README.md`](/lessons/README.md) | 구조, 매니페스트, 레슨 작성 규칙 | `intro.en.md`, `tags.toml`, `README.en.md`(선택), `title_en`·`summary_en`, 태그는 어휘의 키만, 프로그램 출력은 영어(Assumption 14) |
| [`web/README.md`](/web/README.md) | API(`/api/lessons`), Page, Structure | 인덱스의 새 키, 검색창과 단축키, 태그 칩, 언어 버튼, `i18n.ts`·`search.ts`, 새 vitest 파일 |
| [`lessons/intro.md`](/lessons/intro.md) | 여기서 하는 일 | 검색과 언어 버튼 한 줄 |
| [`docs/specs/070_01_lesson_structure.md`](/docs/specs/070_01_lesson_structure.md) | History / Amendments | "070-10이 매니페스트에 `title_en`, `summary_en`과 태그 어휘를 더함" |
| [`docs/tasks/agent_todo.md`](/docs/tasks/agent_todo.md) | 진행 순서, Phase 7 | 070-10 줄과 순서(070-03 앞), 070-03 줄에 070-10 선행 |
| [`docs/tasks/lesson_candidates.md`](/docs/tasks/lesson_candidates.md) | 머리말 | 새 레슨은 영어 필드와 어휘의 태그를 쓰고, 출력은 영어. 레슨 작업은 기존 레슨의 README 영어판과 영어 출력도 맡는다 |

## 9. Technical Constraints
- Node.js 20+, 버전은 `package-lock.json` 고정 그대로
- Python 3.11+ (`tomllib`)
- 브라우저: `String.prototype.normalize`, `KeyboardEvent.isComposing`(지금 쓰는 브라우저 모두 지원)

## 10. Context & References
- [lessons.py](/tools/lessons.py), [test_lessons.py](/tools/test_lessons.py), [lessons/CMakeLists.txt](/lessons/CMakeLists.txt)
- [lessonTree.ts](/web/frontend/src/lessonTree.ts), [main.ts](/web/frontend/src/main.ts), [readme.ts](/web/frontend/src/readme.ts), [index.html](/web/frontend/index.html)
- [070-01 스펙](/docs/specs/070_01_lesson_structure.md)(매니페스트), [070-02 스펙](/docs/specs/070_02_web_playground.md)(페이지), [070-08 스펙](/docs/specs/070_08_playground_intro.md)(소개)
- [레슨 후보 목록](/docs/tasks/lesson_candidates.md)

## 11. Implementation Plan
- [ ] Step 1: `lessons.py`: 영어 키, `tags.toml` 읽기와 검사, 인덱스 키. `test_lessons.py`의 유효 트리에 영어 키와 어휘를 더하고 AC-1–AC-3 케이스
- [ ] Step 2: 내용: 매니페스트 8개의 영어 필드, `lessons/tags.toml`, `lessons/intro.en.md`. `lessons.py check` WARN 0
- [ ] Step 3: `i18n.ts`, 한국어 문자열 옮기기, `index.html`의 `data-i18n`, 언어 버튼, `test/i18n.test.ts`
- [ ] Step 4: `search.ts`, `test/search.test.ts`, 검색창, 트리 거르기, 단축키, 태그 칩
- [ ] Step 5: §8 문서 갱신

## 12. Verification Plan
- [ ] `py -3 tools/test_lessons.py`, `py -3 tools/lessons.py check`(ERROR 0, WARN 0)
- [ ] `npm --prefix web/frontend run build`, `npm --prefix web/frontend test`
- [ ] `py -3 .agent/scripts/build.py --preset linux-x64-debug --test` (PlaygroundServer, lesson smoke tests)
- [ ] `py -3 .agent/scripts/lint_docs.py`
- [ ] 브라우저: AC-6, AC-8 스크린샷을 `docs/tasks/feature_070-10-lesson-search-i18n/screenshots/`에
- [ ] Every AC row has its evidence in `testrecord.md`

## History / Amendments
- 2026-11-02: 초안. 같은 날 사용자 답변 반영(Assumption 13: README 영어판과 기존 레슨 고치기는 레슨 작업이 함, 14: 레슨 출력은 언제나 영어) 후 승인
