---
id: 070-02-01
title: 플레이그라운드 --port를 페이지 포트로 (dev 모드 포함)
depends_on: [070-02]
unblocks: []
approved: 2026-10-29
---

# Spec 070-02-01: 플레이그라운드 `--port`를 페이지 포트로 (dev 모드 포함)

원래 스펙: [070-02 로컬 웹 플레이그라운드](/docs/specs/070_02_web_playground.md). 다시 여는 이유: [KI-017](/docs/known_issues.md). `--dev`에서 `--port`가 API 서버만 옮기고 페이지(Vite)는 5173에 남아, 사용자가 페이지 포트를 정할 방법이 없다.

## 0. Assumptions (please review)
| # | Decision | Rejected alternative | Why |
|---|---|---|---|
| 1 | `tools/playground.py --port N`은 두 모드 모두 **페이지 포트**(브라우저에 여는 주소). 기본값은 그대로: 일반 8765, `--dev` 5173 | `--dev-port` 옵션을 따로 추가 | 사용자가 `--port`를 페이지 포트로 읽었고, 일반 모드에서는 이미 그 뜻이다. 옵션 하나가 한 가지 뜻만 갖는다 |
| 2 | `--dev`에서 API 서버는 빈 포트를 자동으로 잡는다(`server.py --port 0`). 페이지는 Vite 프록시(`/api`)로만 서버에 닿으므로 사용자는 이 포트를 알 필요가 없다 | 8765부터 찾기(지금 방식) | 사용자가 `--dev --port 8765`를 주면 서버와 Vite가 같은 포트를 두고 다툰다. WSL에서 포트 0으로 띄운 서버에 Windows에서 바로 접근되는 것을 확인함(2026-10-29) |
| 3 | `--dev`에서 페이지 포트가 사용 중이면 `playground.py`가 다음 빈 포트를 찾는다(20개까지, 서버와 같은 규칙). Vite는 `strictPort`를 유지한다 | Vite의 자동 증가(`strictPort: false`) | Vite가 스스로 옮기면 `playground.py`가 실제 포트를 모르므로 `--open`과 서버의 `--allow-origin`이 틀린 주소를 쓴다. 확인과 실제 바인딩 사이에 다른 프로그램이 포트를 가져가면 Vite가 조용히 옮기지 않고 실패한다 |
| 4 | 포트는 Vite CLI 인자로 넘긴다(`npm run dev -- --port N`). `vite.config.ts`의 5173은 `npm run dev`를 직접 실행할 때의 기본값으로 남긴다 | 환경 변수 `ATUGCC_DEV_PORT` | CLI 인자가 Vite 설정보다 우선하는 표준 방법이고 설정 파일을 바꿀 필요가 없다 |

## 1. Objective
`py -3 tools/playground.py --dev --open --port 9000`이 `http://127.0.0.1:9000/`에 hot reload 페이지를 띄우고, 그 페이지에서 편집·Run이 그대로 동작하게 한다.

## 2. Requirement Details
### 2.1 Public API Surface
`tools/playground.py`
- `--port N`: 페이지 포트. 생략하면 일반 8765, `--dev` 5173. 사용 중이면 다음 빈 포트(20개까지). 범위: 일반 0..65535(0은 이전처럼 서버가 아무 빈 포트), `--dev` 1..65535. 범위 밖은 사용법 오류(exit 2).
- `--dev`: 서버는 `--port 0`과 `--allow-origin http://127.0.0.1:<페이지 포트>`(그리고 `localhost`)로 시작하고, Vite는 `--port <페이지 포트>`로 시작한다. `dev page:` 줄과 `--open`이 그 포트를 쓴다.
- 일반 모드의 동작은 바뀌지 않는다(서버가 `--port`부터 빈 포트를 찾음).

### 2.2 Internal Implementation
- `free_port(first, tries)`: `127.0.0.1`에 바인딩을 시도해 첫 빈 포트를 돌려준다(없으면 `None`, 65535를 넘지 않음). 소켓 옵션은 Vite의 바인딩과 같게: Linux에서는 `SO_REUSEADDR`(libuv와 같음, 직전 실행이 남긴 TIME_WAIT 포트를 빈 포트로 봄), Windows는 기본값.
- `launch_plan(port, dev)`: 서버 포트, 서버 추가 인자, 페이지 포트를 정하는 순수 함수(테스트 대상).
- `wait_any(procs)`: 서버나 Vite 중 하나가 끝나면 launcher도 끝나고 `finally`가 나머지를 정리한다. 이전에는 서버만 기다려서, Vite가 실패해도 launcher가 남았다.

### 2.3 Platform Specifics
Windows에서 서버는 WSL 안에서 돌고 Vite는 호스트(Windows)에서 돈다. 페이지 포트 확인은 Vite와 같은 호스트에서 한다.

## 3. C++ Standard Evolution
N/A (도구 스크립트).

## 4. Edge Cases
- [x] 페이지 포트 사용 중 → 다음 빈 포트, 20개 모두 사용 중이면 `error:`와 exit 1 (Assumption 3)
- [x] 확인 후 다른 프로그램이 포트를 가져감 → Vite `strictPort`로 실패, Ctrl+C 없이도 `finally`가 서버를 정리
- [x] `--dev --port 8765` → 서버는 포트 0이라 충돌 없음 (Assumption 2)
- [x] 직전 실행이 남긴 TIME_WAIT 포트(Linux) → 빈 포트로 본다 (§2.2)
- [x] `--port 0`, 음수, 65535 초과 → §2.1의 범위 규칙
- N/A 스레드·수명·ODR·UB: C++ 코드 변경 없음

## 5. Acceptance Criteria
| ID | Criterion | Verified by |
|---|---|---|
| AC-1 | `--dev --port N`: 페이지가 `127.0.0.1:N`에서 응답하고, 같은 주소의 `/api/health`가 프록시를 거쳐 서버의 응답을 돌려주며, 5173은 쓰이지 않는다 | `tools/test_playground.py` `DevLaunchTest` (실제 실행) |
| AC-2 | `--dev`에서 서버는 포트 0으로 시작하고 페이지 origin만 허용한다. `--port`가 없으면 페이지는 5173, 일반 모드는 8765(서버가 결정) | `tools/test_playground.py` `LaunchPlanTest`, `WaitAnyTest`, `DevLaunchTest`(실제 서버에 Origin 헤더로 200/403) |
| AC-3 | `--dev`에서 페이지 포트가 사용 중이면 다음 빈 포트를 쓰고, 모두 사용 중이면 오류로 끝난다. Vite가 끝나면 launcher도 끝나고 서버를 정리한다 | `tools/test_playground.py` `LaunchPlanTest`, `FreePortTest`, `WaitAnyTest` |
| AC-4 | 일반 모드 `--port N`은 이전과 같다: 페이지와 API가 `127.0.0.1:N` | `tools/test_playground.py` `ServeLaunchTest` (실제 실행) |

## 6. Out of Scope
- API 서버 포트를 사용자가 따로 정하는 옵션 — 필요해지면 새 KI

## 7. Dependencies & Adapters
none

## 8. Documentation Updates
| Document | Section | Change |
|---|---|---|
| `tools/playground.py` | docstring, `--help` | `--port`의 뜻과 기본값 |
| [`web/README.md`](/web/README.md) | Start | dev 행과 "Another port" 행 |
| `.vscode/tasks.json` | dev 태스크 `detail` | 포트 설명 |
| `web/frontend/vite.config.ts` | 머리 주석 | 포트를 CLI로 받음 |
| [`docs/known_issues.md`](/docs/known_issues.md) | KI-017 | CLOSED |
| [`docs/specs/070_02_web_playground.md`](/docs/specs/070_02_web_playground.md) | History | 이 서브스펙 |

## 9. Technical Constraints
Python 3.11+ 표준 라이브러리, Node.js 20+ (070-02와 같음).

## 10. Context & References
[`tools/playground.py`](/tools/playground.py), [`web/server/server.py`](/web/server/server.py) `make_server`, [`web/frontend/vite.config.ts`](/web/frontend/vite.config.ts).

## 11. Implementation Plan
- [x] Step 1: `free_port`, `launch_plan`, `main` 변경
- [x] Step 2: `tools/test_playground.py`
- [x] Step 3: 문서

## 12. Verification Plan
- [x] `py -3 tools/test_playground.py` (Windows 호스트, WSL 서버)
- [x] `py -3 tools/test_lessons.py`, `py -3 .agent/scripts/lint_docs.py`, `py -3 .agent/scripts/naming_check.py`
- [x] Every AC row has its evidence in `testrecord.md`

## History / Amendments
- 2026-10-29: KI-017을 사용자가 "단순 작업이라 바로 진행 승인"으로 승인. Assumption 1–4는 KI-017의 Next를 구체화한 것.
- 2026-10-29: 검토(`cpp-reviewer`) 반영: Linux `SO_REUSEADDR`, `--port` 범위 규칙(일반 모드 `--port 0` 유지), `wait_any`를 §2.2에 명시, AC-2·3 검증 항목 추가.
