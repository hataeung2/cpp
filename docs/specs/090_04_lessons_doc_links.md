---
id: 090-04
title: 문서 게이트가 lessons/ Markdown 링크도 검사 (KI-019)
depends_on: [070-08]
unblocks: []
approved: 2026-10-29
---

# Spec 090-04: 문서 게이트가 `lessons/` Markdown 링크도 검사

승인: 사용자가 2026-10-29 세션에서 KI-019를 제안한 방법(`DOC_DIRS`에 `lessons` 추가)대로 진행하라고 지시함.

## 0. Assumptions (please review)
| # | Decision | Rejected alternative | Why |
|---|---|---|---|
| 1 | `.agent/scripts/lint_docs.py`의 `DOC_DIRS`에 `"lessons"`를 더한다. `lessons/` 아래 `.md`(와 `.json`)가 다른 문서와 같은 검사(깨진 링크, 기계 경로, KI id)를 받는다 | `tools/lessons.py check`에 링크 검사를 따로 구현 | 같은 규칙을 두 곳에 두지 않는다. `lint_docs.py`의 링크 해석(상대 경로, `/`는 저장소 루트)은 웹 `ReadmePanel`과 같다. `lessons.py check`는 이미 문서 게이트에서 실행된다 |
| 2 | 레벨은 다른 문서와 같은 ERROR | WARN | 깨진 링크는 페이지에서 누르면 바로 오류가 나는 결함이다. 미리 돌려 본 결과 현재 `lessons/` Markdown 8개에서 걸리는 것이 없다 |

## 1. Objective
레슨 폴더 이름을 바꾸거나(070-03, 070-04) 파일을 옮길 때 `lessons/intro.md`와 레슨·유닛 README의 링크가 조용히 깨지지 않게 한다. KI-019를 닫는다.

## 2. Requirement Details
### 2.1 Public API Surface
none.
### 2.2 Internal Implementation
`DOC_DIRS = ("docs", ".agent", ".claude", "lessons")`. `tools/lessons.py`, 웹 코드는 바꾸지 않는다.
### 2.3 Platform Specifics
none.

## 3. C++ Standard Evolution
N/A.

## 4. Edge Cases
- [x] Thread safety, lifetime, platform, templates, ODR, UB — N/A (Python 문서 검사 스크립트)
- [x] `lessons/`의 Markdown이 아닌 파일(`.cpp`, `.hpp`, `.toml`) — `PATH_CHECKED_SUFFIXES`(`.md`, `.json`) 밖이라 이전처럼 검사하지 않는다
- [x] 코드 블록 안의 링크 모양 — 기존 `strip_code`가 빼므로 README의 예제 코드는 링크로 보지 않는다
- [x] 봉인된 기록 — `lessons/`에는 봉인 규칙(`feature_*`)이 해당하지 않으므로 ERROR

## 5. Acceptance Criteria
| ID | Criterion | Verified by |
|---|---|---|
| AC-1 | `lessons/` 아래 Markdown의 깨진 링크가 `lint_docs.py`에서 ERROR가 되고, 고치면 사라진다 | `test_agent_scripts.py`의 새 테스트, 변이(`lessons` 제거)로 실패 확인 |
| AC-2 | 현재 저장소에서 `lint_docs.py` exit 0, `test_agent_scripts.py` 통과 | 명령 출력 |

## 6. Out of Scope
- `.cpp`/`.hpp` 주석 안의 경로 검사 — 필요해지면 KI

## 7. Dependencies & Adapters
none.

## 8. Documentation Updates
| Document | Section | Change |
|---|---|---|
| [`.agent/rules/test.md`](/.agent/rules/test.md) | Docs gate | 링크 검사 범위에 `lessons/` 포함 |
| [`lessons/README.md`](/lessons/README.md) | 새 레슨 추가 | 문서 게이트가 README·`intro.md` 링크도 검사 |
| [`docs/known_issues.md`](/docs/known_issues.md) | KI-019 | CLOSED by 090-04 |

## 9. Technical Constraints
- Python 3.11+ 표준 라이브러리

## 10. Context & References
- [lint_docs.py](/.agent/scripts/lint_docs.py), [test_agent_scripts.py](/.agent/scripts/test_agent_scripts.py), [070-08](/docs/specs/070_08_playground_intro.md)

## 11. Implementation Plan
- [ ] `DOC_DIRS`에 `lessons` 추가, 테스트 추가, §8 문서

## 12. Verification Plan
- [ ] `py -3 .agent/scripts/test_agent_scripts.py`, `py -3 .agent/scripts/lint_docs.py`
- [ ] 변이: `lessons` 없이 새 테스트가 실패

## History / Amendments
- 2026-10-29: 초안, 같은 날 승인(KI-019 진행 지시)
