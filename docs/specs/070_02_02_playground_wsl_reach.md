---
id: 070-02-02
title: 플레이그라운드가 WSL 서버에 닿지 않을 때 알려 주기
depends_on: [070-02, 070-02-01]
unblocks: []
approved: 2026-11-04
---

# Spec 070-02-02: 플레이그라운드가 WSL 서버에 닿지 않을 때 알려 주기

원래 스펙: [070-02 로컬 웹 플레이그라운드](/docs/specs/070_02_web_playground.md). 다시 여는 이유: [KI-040](/docs/known_issues.md). Windows에서 API 서버는 WSL 안의 `127.0.0.1`에서 듣고, 브라우저와 Vite는 WSL2의 localhost 포워딩으로 그 포트에 닿는다. 포워딩이 멈추면(2026-11-04: `wslrelay.exe` 없음) `tools/playground.py`는 정상 시작처럼 주소를 출력하고, 사용자는 Vite 프록시 오류(`ECONNREFUSED`)나 빈 페이지만 보게 된다.

## 0. Assumptions (please review)
| # | Decision | Rejected alternative | Why |
|---|---|---|---|
| 1 | Windows에서 서버가 주소를 출력하면 `playground.py`가 Windows 쪽에서 `<서버 주소>/api/health`에 접속해 본다. 응답(상태 코드 무관)이 오면 그대로 진행한다 | 확인하지 않고 KI의 해결법만 문서화 | 사용자는 문서보다 터미널을 먼저 본다. 포워딩이 멈춘 것은 브라우저에서 원인이 보이지 않는다 |
| 2 | 10초 안에 닿지 않으면 `error:` 줄과 해결법(`wsl --shutdown` 후 다시 실행)을 출력하고 exit 1, 서버는 정리한다. 기다리는 동안 서버가 끝나면 서버의 종료 코드로 바로 끝난다 | 경고만 하고 계속 실행 | 포워딩 없이는 페이지와 API가 모두 쓸 수 없다. 남겨 두면 사용자가 원인을 다시 찾아야 한다 |
| 3 | `playground.py`가 `wsl --shutdown`을 직접 실행하지 않는다 | 자동 복구 | 다른 WSL 세션과 실행 중인 프로그램을 모두 끝낸다. 사용자가 정할 일이다 |
| 4 | Linux 호스트에서는 확인하지 않는다 | 두 호스트 모두 확인 | Linux에서는 서버와 브라우저가 같은 호스트라 포워딩이 없다 |
| 5 | 두 모드(`--dev`와 일반) 모두 확인한다. `--dev`에서는 Vite를 띄우기 전에 확인한다 | `--dev`만 | 일반 모드의 페이지도 같은 포워딩으로 닿는다. Vite보다 먼저 확인해야 프록시 오류가 쏟아지지 않는다 |

## 1. Objective
WSL localhost 포워딩이 멈춘 상태에서 `py -3 tools/playground.py [--dev]`를 실행하면, 사용자가 10초 안에 원인과 해결법이 적힌 오류를 터미널에서 본다.

## 2. Requirement Details
### 2.1 Public API Surface
`tools/playground.py` (Windows 호스트)
- 서버의 `atugcc playground: <url>` 줄 다음에 `<url>api/health`를 확인한다. 닿으면 출력과 동작은 지금과 같다.
- 닿지 않으면 stderr에 아래 문구를 출력하고 exit 1:
  `error: Windows cannot reach the API server in WSL at <url> (WSL localhost forwarding is not working). Run "wsl --shutdown", then start the playground again.`

### 2.2 Internal Implementation
- `reachable(url, server, wait)`: `url`이 HTTP 응답을 주면(오류 상태 포함) `True`. 연결 실패는 0.25초 간격으로 `wait`초까지 다시 시도하고, 그동안 `server`가 끝나면 바로 `False`. 시스템 프록시 설정은 쓰지 않는다(`127.0.0.1`).
- `main`: Windows에서 `start_server` 다음, Vite 시작 전에 호출한다.

### 2.3 Platform Specifics
Windows 전용 확인이다(Assumption 4). WSL은 새 localhost 포트를 보통 1초 안에 포워딩한다. 10초는 그 몇 배의 여유다.

## 3. C++ Standard Evolution
N/A (도구 스크립트).

## 4. Edge Cases
- [x] 포워딩이 늦게 생김(1초 안팎) → 다시 시도하는 동안 닿으면 정상 진행 (§2.2)
- [x] 서버가 403 같은 오류 상태로 응답 → 닿은 것으로 본다 (Assumption 1)
- [x] 기다리는 동안 서버가 끝남 → 서버의 종료 코드로 끝난다 (Assumption 2)
- [x] 시스템 HTTP 프록시가 설정됨 → 쓰지 않는다 (§2.2)
- N/A 스레드·수명·ODR·UB: C++ 코드 변경 없음

## 5. Acceptance Criteria
| ID | Criterion | Verified by |
|---|---|---|
| AC-1 | `reachable`: 응답(200, 403)이면 `True`, 닫힌 포트는 `wait` 뒤 `False`, 서버가 끝나면 기다리지 않고 `False` | `tools/test_playground.py` `ReachableTest` |
| AC-2 | Windows에서 닿지 않으면 `main`이 §2.1의 문구를 출력하고 1을 돌려주며 서버를 정리하고 Vite를 띄우지 않는다. Linux에서는 확인하지 않는다 | `tools/test_playground.py` `ReachableTest` (mock) |
| AC-3 | 포워딩이 멈춘 실제 WSL에서 `playground.py`가 §2.1의 오류로 끝난다 | 수동 실행, `testrecord.md` |
| AC-4 | 포워딩이 동작할 때 `DevLaunchTest`, `ServeLaunchTest`가 이전처럼 통과한다 | `py -3 tools/test_playground.py` |

## 6. Out of Scope
- 포워딩을 자동으로 복구하기 (Assumption 3)
- WSL mirrored 네트워킹 모드로 바꾸기 — 사용자 환경 설정

## 7. Dependencies & Adapters
none

## 8. Documentation Updates
| Document | Section | Change |
|---|---|---|
| `tools/playground.py` | docstring | 닿는지 확인 |
| [`web/README.md`](/web/README.md) | Start | 오류와 해결법 한 줄 |
| [`docs/known_issues.md`](/docs/known_issues.md) | KI-040 | 새 항목, 이 작업으로 CLOSED |
| [`docs/specs/070_02_web_playground.md`](/docs/specs/070_02_web_playground.md) | History | 이 서브스펙 |

## 9. Technical Constraints
Python 3.11+ 표준 라이브러리 (070-02와 같음).

## 10. Context & References
[`tools/playground.py`](/tools/playground.py) `main`, `start_server`; [`web/server/server.py`](/web/server/server.py) `/api/health`.

## 11. Implementation Plan
- [x] Step 1: `reachable`, `main` 변경
- [x] Step 2: `tools/test_playground.py` `ReachableTest`
- [x] Step 3: 문서

## 12. Verification Plan
- [x] `py -3 tools/test_playground.py` (Windows 호스트, WSL 서버)
- [x] `py -3 .agent/scripts/lint_docs.py`, `py -3 .agent/scripts/naming_check.py`
- [ ] Every AC row has its evidence in `testrecord.md` (AC-3 pending)

## History / Amendments
- 2026-11-04: 사용자가 `--dev --port 9000`의 프록시 오류(`ECONNREFUSED`)를 보고. 원인은 WSL localhost 포워딩 중단(`wslrelay.exe` 없음, 고정 포트 8799도 닿지 않음). 리드가 "닿지 않으면 해결법과 함께 오류로 끝내기"를 제안했고, 사용자가 "제안대로 작은 작업으로 부탁해"로 승인. Assumption 1–5는 그 제안을 구체화한 것.
