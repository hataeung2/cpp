---
id: 070-02
title: 로컬 웹 플레이그라운드 — 편집·빌드·실행·시각화
depends_on: [020-05, 070-01]
unblocks: [070-05, 070-06, 070-07]
approved: 2026-10-28
---

# Spec 070-02: 로컬 웹 플레이그라운드 — 편집·빌드·실행·시각화

## 0. Assumptions (please review)
| # | Decision | Rejected alternative | Why |
|---|---|---|---|
| 1 | **로컬 전용**: 서버는 `127.0.0.1`에만 바인딩하고 인증이나 격리를 두지 않는다 | 처음부터 공개 배포용 샌드박스 | 사용자 결정(2026-10-28). 임의 코드를 실행하는 서버이므로 외부 인터페이스 바인딩은 금지(AC-9). 공개 여부는 070-05에서 결정 |
| 2 | 웹에서 저장하면 **저장소 파일에 바로** 쓴다. 쓰기 가능 범위는 `lessons/**`이고, `include/**`·`src/**`는 읽기 전용으로 보여 준다 | 별도 작업공간 + 반영 버튼 / 브라우저 저장 | 사용자 결정: VS Code와 웹이 같은 파일을 보고 git이 이력을 맡는다. 라이브러리 수정은 리뷰가 필요한 작업이라 IDE에서 한다 |
| 3 | 실행 = `linux-x64-playground` preset으로 레슨 타깃을 빌드한 뒤 바이너리 실행. 컴파일러는 WSL Ubuntu의 GCC | g++ 단일 명령 / Docker | 사용자 결정(WSL g++ 직접). preset 빌드라서 로컬 빌드와 플래그가 같고 Non-negotiable Rule 2를 지킨다. 전용 preset(별도 빌드 디렉터리)이라 사용자의 `linux-x64-debug` 빌드와 ninja 락이 충돌하지 않는다 |
| 4 | 서버는 WSL 안의 Python 3 표준 라이브러리(`http.server`)로 동작한다. 실행기 `tools/playground.py`는 Windows에서 실행하면 WSL로 위임한다(`build.py`와 같은 방식) | Node/FastAPI 서버 | 외부 패키지 없이 `tools/lessons.py`를 import해서 재사용한다. 요청은 한 명이 보내므로 성능 요구가 낮다 |
| 5 | 프론트엔드는 Vite + TypeScript, 의존성은 고정 버전(`package-lock.json` 커밋): `monaco-editor`, `mermaid`, `marked`, `dompurify`; 개발용 `vite`, `typescript`, `vitest`, `jsdom` | 빌드 없는 순수 JS | 사용자 결정. npm 설치 후 오프라인 동작 |
| 6 | 실행 서버는 빌드된 정적 파일(`web/frontend/dist`)을 함께 제공한다. 프로세스 하나, URL 하나. `--dev`면 Vite dev 서버가 API를 프록시한다 | 항상 두 프로세스 | "버튼 하나": VS Code 태스크 `Playground: start` 하나로 시작 |
| 7 | 다이어그램은 020-05의 `diagram` 줄(Mermaid)만 렌더링한다. 터미널 출력(ANSI)은 자체 변환기로 페이지 색상 토큰에 매핑한다 | PlantUML/D2 렌더링, xterm.js | PlantUML·D2는 브라우저 렌더러가 무겁거나 서버가 필요하다. diagrams.md §3은 ANSI를 페이지 토큰으로 바꾸라고 한다(xterm은 자체 팔레트를 쓴다) |
| 8 | 모든 실행은 **SSE 스트림**으로 전달한다(빌드 로그, stdout·stderr 조각, Tracer 이벤트, 종료 요약). Stop 버튼이 있다. 이 작업은 `quick` 프로필(10초)만 지원하고, `long` 프로필 레슨도 quick 제한으로 실행하면서 "070-06 필요" 안내를 표시한다 | 요청 하나에 응답 하나, 스트리밍은 나중에 | 사용자 요구(2026-10-28): 성능 측정 레슨은 실시간으로 보여야 한다. 빠른 실행도 같은 스트림을 쓰면 코드 경로가 하나라서, long 프로필(070-06)은 제한값과 화면만 추가하면 된다. 나중에 응답 방식을 바꾸면 API와 화면을 다시 만들어야 한다 |
| 9 | 웹과 VS Code의 동시 편집은 **sha 기반 충돌 감지**로 처리한다. 수정하지 않은 탭은 창에 포커스가 돌아올 때 디스크 내용으로 새로 고친다 | 파일 감시(WebSocket) | 반반 작업 흐름에서 덮어쓰기 사고를 막는 최소 장치다. 감시는 WSL의 `/mnt/c`에서 inotify가 동작하지 않아 신뢰할 수 없다 |

## 1. Objective
`lessons/`(070-01)의 레슨을 브라우저에서 고치고, 빌드·실행하고, Tracer 이벤트와 다이어그램을 보며 연습한다. 목표는 **직접 컴파일 작업과 웹 작업을 반반 섞어 쓰는 것**이다. 그래서 웹은 별도 사본이 아니라 저장소와 같은 파일, 같은 preset 빌드를 쓴다. 한쪽에서 바꾼 것이 다른 쪽에 그대로 보인다.

## 2. Requirement Details

### 2.1 구성
```text
web/
  server/
    server.py          # http.server 기반 API + 정적 파일
    runner.py          # preset 빌드, 실행, 시간·출력 제한, trace 파싱
    files.py           # 경로 검증, 읽기/쓰기, sha, 줄바꿈 보존
    test_server.py     # unittest
  frontend/
    package.json, package-lock.json, vite.config.ts, tsconfig.json
    index.html
    src/  main.ts, api.ts, editor.ts, lessonTree.ts, output.ts, ansi.ts,
          diagrams.ts, events.ts, readme.ts, theme.css
    test/ ansi.test.ts, diagnostics.test.ts, mermaidParse.test.ts
tools/playground.py    # 실행기: (필요 시) npm ci && npm run build → WSL에서 server.py
```
`CMakePresets.json`: configure·build preset `linux-x64-playground`(`linux-x64-debug` 상속, `ATUGCC_BUILD_TESTS=OFF`, `ATUGCC_BUILD_SAMPLES=OFF`, `ATUGCC_BUILD_LESSONS=ON`).
`.vscode/tasks.json`: `Playground: start`, `Playground: start (dev)`.

### 2.2 API
| Method | Path | 동작 |
|---|---|---|
| GET | `/api/lessons` | `lessons.index()` 결과(070-01 §2.4) |
| GET | `/api/files?path=<repo 상대>` | `{path, content, sha, eol, writable}` |
| PUT | `/api/files?path=…` body `{content, baseSha}` | `baseSha`가 디스크와 다르면 409 `{content, sha}`. 같으면 원래 줄바꿈(`eol`)으로 저장하고 `{sha}` |
| POST | `/api/runs` body `{lesson}` | 실행 작업 생성 → `{runId}` (즉시 반환) |
| GET | `/api/runs/<runId>/stream` | SSE. 아래 이벤트를 순서대로 보낸다 |
| POST | `/api/runs/<runId>/stop` | 실행 중이면 프로세스 그룹 종료 → 스트림에 `done{stopped:true}` |
| GET | `/api/health` | 버전, preset, 컴파일러 버전 |

SSE 이벤트(`event:` 이름, `data:`는 JSON):
| event | data |
|---|---|
| `phase` | `{phase: "configure"\|"build"\|"run", profile, limitSec}` |
| `build` | `{text}` 빌드 로그 조각 |
| `stdout` / `stderr` | `{text}` 실행 출력 조각 |
| `trace` | `{events:[…]}` 020-05 이벤트 줄 묶음(새로 생긴 줄만) |
| `done` | `{build:{ok, ms, diagnostics[]}, run:{exitCode, signal, timedOut, stopped, ms, truncated}, diagrams[], skippedTraceLines}` |

- 서버는 조각을 최대 100ms 단위로 모아서 보낸다(출력이 많을 때 브라우저 과부하 방지).

- 경로 검증: 저장소 루트 안의 정규화된 상대 경로만 허용한다. `..`, 절대 경로, 루트 밖을 가리키는 심볼릭 링크는 거부한다(400). 쓰기는 `lessons/` 아래 기존 파일과 `lessons/**/` 아래 새 `.cpp/.hpp/.md/.toml`만 허용한다(403).
- `diagnostics[]`: GCC의 `file:line:col: error|warning|note: msg`를 파싱해 저장소 상대 경로로 바꾼다. 에디터 마커로 쓴다.
- `trace`: 실행 중 `ATUGCC_TRACE_OUT`(실행마다 임시 파일)을 100ms 간격으로 읽어 새로 완성된 줄만 보낸다. `file`은 저장소 상대 경로로 바꾼다. 줄 순서가 seq와 다를 수 있으므로(020-05 §2.3) 화면이 seq로 정렬한다. 파싱할 수 없는 줄은 건너뛰고 개수를 `done`에 넣는다.
- 출력 버퍼링: 파이프로 연결된 C++ stdout은 전체 버퍼링되어 끝날 때 한꺼번에 나온다. 그래서 실행 파일을 `stdbuf -oL -eL`로 감싸 줄 단위로 나오게 한다(`std::cout`은 기본 `sync_with_stdio(true)`라 C stdio 버퍼 설정을 따른다).
- 동시 실행: 서버 전역 락 하나로 빌드·실행을 직렬화한다. 대기 중인 작업은 순서대로 처리한다. 브라우저가 스트림을 끊으면(탭 닫기) 실행을 종료한다.
- 제한(quick): 빌드 120초, 실행 10초(초과 시 프로세스 그룹 종료, `timedOut:true`), stdout·stderr 각 1 MiB(초과분 버리고 `truncated:true`). 제한값은 프로필 표 하나에 모아 070-06이 `long` 행만 추가하게 한다.
- 첫 실행 때 빌드 디렉터리가 없으면 `cmake --preset linux-x64-playground`로 configure한다(preset이므로 Rule 2 준수).

### 2.3 화면
| 영역 | 내용 |
|---|---|
| 왼쪽: 레슨 트리 | 트랙 → 레슨(순서대로). 아래에 유닛 목록과 "사용하는 레슨"(역참조). 유닛을 누르면 유닛 파일이 열린다 |
| 가운데: 에디터 | Monaco 탭: 진입점, `sources`, 해석된 `uses` 파일. 읽기 전용 파일은 잠금 표시. 수정 표시(●), Ctrl+S 저장, 빌드 진단 마커 |
| 오른쪽 탭 | **README**(레슨·유닛 설명, Markdown, sanitize) / **Output**(빌드 로그, stdout·stderr, ANSI 색) / **Diagrams**(Mermaid 조각마다 제목·스크롤 컨테이너·전체 크기 보기) / **Events**(seq 순 목록. 누르면 해당 파일·줄을 에디터에서 강조) |
| 상단 | Run(수정된 탭 저장 → 실행) / Stop, 단계(configure·build·run)와 경과 시간, 프로필과 제한 시간, 라이트/다크 |

- 다이어그램 뷰어는 [diagrams.md](/.agent/rules/diagrams.md) §3을 따른다: `useMaxWidth:false`, 축소 하한 80%, 컨테이너 안 가로 스크롤, 글자 14px 이상, 전체 크기 보기.
- 충돌(409) 시: "디스크 내용으로 새로 고침 / 내 내용으로 덮어쓰기 / 취소" 선택지. 창 포커스 때 열린 탭의 sha를 확인해 수정하지 않은 탭은 자동으로 새로 고치고, 수정한 탭은 충돌 표시를 한다.

### 2.4 Platform Specifics
- Windows: `tools/playground.py`가 프론트엔드를 Windows Node로 빌드하고(dist는 공유 파일시스템에 생김) 서버를 `wsl.exe`로 시작한다. 배포판은 `ATUGCC_WSL_DISTRO`, 없으면 기본값(`build.py`와 같음). 브라우저는 WSL2 localhost 전달로 접속한다.
- Linux: Node와 Python이 같은 머신에 있어야 한다. 위임 없이 실행한다.
- WSL에서 `/mnt/c` 파일을 쓸 때 원래 줄바꿈을 유지한다(LF/CRLF 감지 후 그대로). 새 파일은 LF로 만든다.

## 3. C++ Standard Evolution
N/A (도구 작업)

## 4. Edge Cases
- [x] 경로 탈출(`../`, 절대 경로, 인코딩된 `%2e%2e`, 심볼릭 링크) → 400/403 (AC-3)
- [x] 무한 루프·대량 출력 레슨 → 10초 종료, 1 MiB 절단 (AC-5)
- [x] 출력이 실시간으로 안 보임(파이프 버퍼링) → `stdbuf -oL -eL` (AC-11). 레슨이 `std::ios::sync_with_stdio(false)`를 쓰면 효과가 없다. 레슨 작성 안내(`lessons/README.md`)에 적는다
- [x] 실행 중 브라우저 새로 고침·탭 닫기 → 스트림 끊김 감지 후 프로세스 그룹 종료, 락 해제
- [x] 스트림 연결 전에 나온 출력 → 작업별 버퍼에 쌓아 두었다가 연결 시 처음부터 보낸다
- [x] 빌드 실패 → `build.ok:false`, 진단 마커. 이전 바이너리를 실행하지 않는다
- [x] 크래시(SIGSEGV)·`std::exit` → 종료 코드나 시그널 표시. trace 파일의 이벤트까지만 표시하고 diagram 줄이 없으면 "다이어그램 없음(정상 종료 아님)" 안내
- [x] VS Code와 웹 동시 편집 → sha 충돌 감지(Assumption 9)
- [x] 새 레슨 폴더 추가 → 다음 Run에서 CMake가 다시 glob(070-01 Assumption 4). 레슨 목록은 새로 고침 버튼으로 다시 읽음
- [x] 포트 사용 중 → 실행기가 다음 포트를 찾거나 `--port`로 지정. 바인딩은 항상 `127.0.0.1`
- [x] 다이어그램 문법 오류 → 해당 조각만 오류 상자와 원본 소스를 보여 주고 나머지는 렌더링
- N/A C++ 위험 목록(동시성·수명·ODR·UB): 이 작업은 C++ 코드를 바꾸지 않는다. 시드 레슨의 TSan 검증은 070-01

## 5. Acceptance Criteria
| ID | Criterion | Verified by |
|---|---|---|
| AC-1 | `Playground: start` 태스크 하나로 서버가 뜨고 브라우저에서 레슨 트리에 070-01 시드 레슨 3개와 유닛 2개가 보인다 | 수동, 스크린샷 |
| AC-2 | 웹에서 레슨을 고쳐 Run하면 저장소 파일이 바뀌고(`git diff`에 보임), 같은 레슨을 `build.py --preset linux-x64-debug`로 빌드해 실행한 stdout이 웹 Output과 같다 | 수동 + diff, testrecord |
| AC-3 | 경로 탈출 6종과 쓰기 금지 경로(`include/`, `src/`, 저장소 루트 파일)가 거부된다 | `web/server/test_server.py` |
| AC-4 | 디스크 파일이 바뀐 뒤 옛 `baseSha`로 저장하면 409와 현재 내용이 오고, CRLF 파일을 저장해도 CRLF가 유지된다 | 같은 unittest |
| AC-5 | 무한 루프 레슨은 10초 안팎에 `timedOut:true`로 끝나고 남은 프로세스가 없다. 2 MiB를 출력하는 레슨은 `truncated:true` | unittest(테스트용 레슨 fixture) |
| AC-6 | 컴파일 오류가 있는 레슨을 Run하면 해당 파일·줄에 에디터 마커가 표시된다 | `diagnostics.test.ts` + 수동 |
| AC-7 | `device_state_machine` 레슨 실행 후 Events 탭에 seq 순서로 이벤트가 나오고, 하나를 누르면 그 이벤트의 소스 줄이 에디터에서 강조된다 | 수동, 스크린샷 |
| AC-8 | 시드 레슨이 만든 모든 Mermaid 조각이 `mermaid.parse`를 통과하고, 화면에서 80% 미만으로 축소되지 않으며 넓은 조각은 컨테이너 안에서 가로 스크롤된다 | `mermaidParse.test.ts`(시드 레슨 실행 결과를 fixture로) + 수동 |
| AC-9 | 서버는 `127.0.0.1`에만 바인딩된다(다른 인터페이스 주소로 접속 불가) | unittest(바인딩 주소 확인) |
| AC-10 | `npm run build`, `npm test`, `test_server.py`, `lint_docs.py`가 모두 exit 0 | 실행 기록 |
| AC-11 | 1초마다 한 줄씩 5초 동안 출력하는 fixture 레슨에서 `done` 전에 `stdout` 이벤트가 4번 이상 서로 다른 시각에 도착한다 | unittest(SSE 클라이언트) |
| AC-12 | Stop을 누르면 1초 안에 `done{stopped:true}`가 오고 남은 프로세스가 없다. 스트림을 끊어도 같다 | unittest |

## 6. Out of Scope
- 공개 배포(샌드박스, 인증, 호스팅) — 070-05 (사용자 결정 대기)
- `long` 프로필(긴 제한 시간, release 빌드), 코드 구간별 시간 측정 화면 — 070-06 (C++ 쪽 구간 타이머는 020-06)
- 단계별 다이어그램 재생 — 070-07
- 표준 입력 제공 — 필요 시 새 작업
- PlantUML·D2 렌더링 — 필요 시 새 작업
- Windows(MSVC) 빌드로 웹 실행 — 로컬 Windows 빌드는 070-01에서 이미 가능. 웹은 GCC 하나
- 라이브러리(`include/`, `src/`) 웹 편집 — Assumption 2
- KI-010(Mermaid 문자열 출력의 제목 위치): 웹은 구조화된 조각을 쓰므로 영향 없음. KI는 Markdown 문자열 출력 결정으로 남긴다

## 7. Dependencies & Adapters
- 서버: Python 3.11+ 표준 라이브러리, WSL의 CMake·Ninja·GCC(`linux-x64-*` preset과 같은 전제)
- 프론트엔드: Node 20+ (이 머신 24.19), Assumption 5의 패키지(정확한 버전은 plan에서 고정)

## 8. Documentation Updates
| Document | Section | Change |
|---|---|---|
| `README.md` | 새 섹션 "Web Playground" | 시작 방법, 요구 사항(WSL, Node), 로컬 전용 경고 |
| `web/README.md` (신규) | 전체 | 구조, API, 개발 모드, 테스트 |
| `lessons/README.md` | 레슨 작성 | 웹에서 보이는 방식(README 탭, uses 탭, Tracer 이벤트) |
| `docs/agent_start_prompt.md` | Quick reference | playground 실행 명령 |
| `docs/known_issues.md` | KI-010 | 웹은 영향 없음 메모, Owner 갱신 |
| `.agent/rules/config.md` | presets | `linux-x64-playground` 용도 |

## 9. Technical Constraints
- 서버: Python 3.11+ stdlib. 프론트엔드: Vite + TypeScript, 고정 버전
- C++ 쪽 변경 없음(CMake preset 추가만)

## 10. Context & References
- [레슨 구조 스펙](/docs/specs/070_01_lesson_structure.md)
- [Tracer 이벤트 스트림 스펙](/docs/specs/020_05_tracer_event_stream.md)
- [diagrams.md](/.agent/rules/diagrams.md) §3 Viewer policy
- [build.py](/.agent/scripts/build.py) — WSL 위임 방식
- [CMakePresets](/CMakePresets.json)

## 11. Implementation Plan
- [ ] Step 1: preset `linux-x64-playground`, `web/server/files.py` + 테스트(AC-3, AC-4)
- [ ] Step 2: `runner.py`(preset 빌드, 프로필 제한, Stop, 출력·trace 수집, 진단 파싱) + 테스트(AC-5, AC-12)
- [ ] Step 3: `server.py` API·SSE, `tools/playground.py`, VS Code 태스크 + 테스트(AC-9, AC-11)
- [ ] Step 4: 프론트엔드 골격: 레슨 트리, 에디터 탭, 저장·충돌
- [ ] Step 5: Output(ANSI), Diagrams(뷰어 정책), Events(줄 강조), README 탭 + vitest
- [ ] Step 6: 수동 시나리오(AC-1, 2, 6, 7, 8) 스크린샷과 문서

## 12. Verification Plan
- [ ] `py -3 web/server/test_server.py` (WSL에서도 `python3`)
- [ ] `npm --prefix web/frontend ci && npm --prefix web/frontend run build && npm --prefix web/frontend test`
- [ ] `py -3 .agent/scripts/lint_docs.py`
- [ ] 수동 시나리오는 `testrecord.md`에 스크린샷과 함께
- [ ] Every AC row has its evidence in `testrecord.md`

## History / Amendments
- 2026-10-28: 초안. 사용자 결정 반영: 로컬 전용, 저장소 파일에 직접 저장, WSL g++ 실행, Vite + TypeScript.
- 2026-10-28: 검토 반영: 모든 실행을 SSE 스트림으로 전달하고 Stop 추가(Assumption 8). long 프로필과 시간 측정은 070-06, 단계별 다이어그램은 070-07로 분리.
- 2026-10-28: 사용자 승인. 구현 중 확정한 세부(plan D3, D4, D7): AC-5·11·12의 fixture는 레슨이 아닌 테스트 전용 프로그램 `tests/playground/playground_fixture.cpp`(CTest `PlaygroundServer`)로 만든다(§9 "C++ 변경 없음"은 라이브러리·레슨 기준). `done`에 최상위 `stopped`를 추가하고 `build`에 `timedOut`을 둔다. 서버는 `Host`·`Origin`·`Content-Type`을 확인해 다른 사이트의 요청을 거부한다.
- 2026-10-29: 070-06이 확장(이 스펙은 바꾸지 않음): `trace` 이벤트에서 `span` 줄을 빼고 서버가 키별로 집계해 새 `spans` 이벤트로 보낸다. `phase.buildType`, `done.run.traceLimit`, `POST /api/runs`의 `profileOverride`·`spanMeter`, 프로필 표 `long` 행. [070-06](/docs/specs/070_06_long_run_timings.md) §2.
