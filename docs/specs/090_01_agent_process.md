---
id: 090-01
title: 에이전트 운영 규칙 개선 (ai_sec 규칙 비교 반영)
depends_on: []
unblocks: [090-02, 020-04]
approved: 2026-10-28
---

# Spec 090-01: 에이전트 운영 규칙 개선 (ai_sec 규칙 비교 반영)

## 0. Assumptions (please review)
| # | Decision | Rejected alternative | Why |
|---|---|---|---|
| 1 | 규칙 본문은 영어, 스펙·todo 본문은 한국어를 유지한다 | 전부 한국어로 번역 | 기존 `.agent/rules`가 영어이고, 같은 규칙을 ai_sec(영어)에 역적용할 때 diff 비교가 쉽다 |
| 2 | boot 문서는 1페이지, 규칙은 필요할 때 로드 | ai_sec처럼 boot 시 constitution·instruction·delegation·workflow 전부 읽기(약 700줄) | 매 세션 컨텍스트 비용. 규칙은 trigger 표로 찾게 한다 |
| 3 | 상태는 7개(`BACKLOG/SPEC_DRAFT/APPROVED/DEV/TEST/DONE/BLOCKED`) | ai_sec의 12개 상태 | 단일 저장소 C++ 라이브러리에 INTEGRATED/REGRESSION_PASSED 분리는 과하다. 통합·회귀는 TEST→DONE 게이트 안에 포함 |
| 4 | 작업 산출물은 3종(plan/testrecord/walkthrough) 유지, handoff 내용은 섹션으로 흡수 | ai_sec의 6종 파일 | 문서 수보다 내용(단위표, AC 대응표, 검토 결과)이 검증력을 만든다 |
| 5 | 작업 ID 그룹 = Phase×10 + 하위 Phase (Phase 2.3 → `023`) | ai_sec처럼 순번 그룹 | 기존 todo의 Phase 구조를 그대로 ID에 담는다 |
| 6 | 기존 스펙 파일은 이름을 바꾸지 않는다(legacy) | 전부 `NNN_SS_` 로 rename | 링크·커밋 이력 보존. todo 줄의 링크가 ID 매핑의 기준 |
| 7 | 이 작업은 `feature/dedicated-console` 끝에서 분기 | 규칙대로 `main`에서 분기 | `main`이 8커밋 뒤처져 있고 모든 브랜치가 일렬로 병합 가능(fast-forward). main 갱신은 사용자 결정(KI-003) |

## 1. Objective
ai_sec 프로젝트의 에이전트 운영 규칙(위임·교차검증·스펙 승인·다이어그램 가독성·lint 게이트)을 C++ 라이브러리에 맞게 경량화해 도입하고, cpp 규칙 내부의 모순을 제거한다. 결과 규칙은 이후 ai_sec에 역적용 검토할 기준이 된다(§11).

## 2. Requirement Details

### 2.1 Step 1 — 진입점과 규칙 모순 정리
- `CLAUDE.md`, `AGENTS.md`: 짧은 진입 파일. 둘 다 `docs/agent_start_prompt.md`(단일 boot 문서)를 가리킨다.
- 모순 제거: `test.md`/템플릿의 즉석 `cmake -S . -B build`, 워크플로 5단계 중복, `config.md`의 절대 경로.
- 함수 명명은 camelCase로 확정(사용자 결정 2026-10-28). 기존 snake_case 함수 이름 변경은 090-02.

### 2.2 Step 2 — 스펙·작업 관리
- 템플릿: frontmatter(`id`, `approved`), Assumptions, Acceptance Criteria(`AC-n`), Out of Scope, Documentation Updates, History.
- `agent_todo.md`: `- !STATE | NNN-SS | 제목` 문법, 그룹별 `(k/n DONE)`.
- 재오픈(패치 번호 `NNN-SS-PP`) 규칙, `docs/known_issues.md`(KI-id).

### 2.3 Step 3 — 위임·검토·테스트 순서 (경량판)
- `.agent/rules/delegation.md`: 작성자 ≠ 검증자, C++ 위험 단위 목록, 서브에이전트 프롬프트 규칙, 1회 검토.
- 워크플로: 단위표 → 단위별 Check → Tester 단계(AC 대응) → 통합 게이트.

### 2.4 Step 4 — 시각화 가독성
- `.agent/rules/diagrams.md`: 생성기 예산, 뷰어 정책, 문서 다이어그램 한도.
- 코드 변경(Mermaid 포매터 분할·반복 횟수 표기)은 별도 작업 020-04 (스펙 승인 필요).

### 2.5 Step 5 — 기계 검증
- 문서 lint 스크립트(링크, todo 문법, 스펙 승인 상태).
- 빌드 스크립트(preset 자동 선택, MSVC 환경 초기화) + `CMakePresets.json` 절대 경로 제거.
- sanitizer preset(Linux ASan+UBSan), 경고=오류 preset.
- Claude Code hook: 즉석 cmake, 절대 경로 기록 차단.

## 3. C++ Standard Evolution
N/A (프로세스 작업)

## 4. Edge Cases
- [ ] Windows/Linux 모두에서 hook·스크립트가 동작 (Git Bash, PowerShell, bash)
- [ ] `VCPKG_ROOT` 미설정 환경에서 preset이 명확한 오류를 낸다
- [ ] legacy 스펙(frontmatter 없음)이 lint에서 오류가 아닌 정보로 보고된다

## 5. Acceptance Criteria
| ID | Criterion | Verified by |
|---|---|---|
| AC-1 | `CLAUDE.md`, `AGENTS.md`가 존재하고 `docs/agent_start_prompt.md`를 가리킨다. boot 문서는 80줄 이하 | `wc -l`, grep |
| AC-2 | 규칙·템플릿에 즉석 cmake 명령이 실행 지시로 남아 있지 않다 (금지 문장 속 예시만 허용) | `grep -rnE "cmake -S\|-B build\|--build build"` 결과가 모두 금지 문장 |
| AC-3 | 규칙·진입 문서·`CMakePresets.json`에 머신 절대 경로가 없다 (금지 문장 속 예시만 허용) | grep, Step 5 이후 lint 스크립트 |
| AC-4 | 템플릿에 `approved`, Assumptions, Acceptance Criteria, Out of Scope, Documentation Updates가 있다 | grep |
| AC-5 | `agent_todo.md`의 모든 작업 줄이 문법을 따르고 ID가 유일하다 | lint 스크립트 |
| AC-6 | `delegation.md`가 C++ 위험 목록, 프롬프트 규칙, 작성자≠검증자 규칙을 담고 워크플로가 이를 참조한다 | 리뷰 |
| AC-7 | `diagrams.md`가 생성기 예산·뷰어 정책·문서 한도를 담고 020-04 스펙이 이를 구현 범위로 가진다 | 리뷰 |
| AC-8 | lint 스크립트 exit 0, sanitizer preset 빌드·테스트 통과, hook이 금지 명령을 차단한다 | 실행 기록 |
| AC-9 | ai_sec 역적용 후보 목록이 이 스펙 §11에 있다 | 리뷰 |

## 6. Out of Scope
- 기존 snake_case 함수 이름 변경 — 090-02
- Mermaid 포매터 코드 변경 — 020-04
- 누락된 `docs/cpp_evolution/*` 문서 작성 — KI-001 / Phase 5
- `main` 브랜치 갱신(fast-forward) — 사용자 결정, KI-003

## 7. Dependencies & Adapters
없음. 서브에이전트 호출은 ai_sec의 `subagent_run.py`와 같은 방식을 쓸 수 있으나 이식 여부는 Step 3에서 결정.

## 8. Technical Constraints
- 스크립트: Python 3 표준 라이브러리만 (`.venv` 의존 없음)
- hook: Claude Code `settings.json` (프로젝트 `.claude/settings.json`)

## 9. Documentation Updates
| Document | Section | Change |
|---|---|---|
| `README.md` | 프로젝트 구조 / 진행 상황 | 에이전트 진입점과 boot 문서 언급 |
| `.agent/rules/*`, `.agent/workflows/*` | 전체 | 위 Step 1–5 |
| `docs/specs/00_template.md` | 전체 | Step 2 |
| `docs/tasks/agent_todo.md` | 전체 | 새 문법으로 변환 |

## 10. Context & References
- [boot 문서](/docs/agent_start_prompt.md)
- [작업 목록](/docs/tasks/agent_todo.md)
- [알려진 이슈](/docs/known_issues.md)

## 11. ai_sec 역적용 후보 (back-port review list)
cpp에서 먼저 바꾸고 ai_sec 규칙 검토 때 비교할 항목. 각 항목은 Step 완료 시 갱신한다.

| # | 주제 | cpp에서 바꾼 방향 | ai_sec 현재 | 검토 포인트 |
|---|---|---|---|---|
| B-1 | boot 비용 | boot 1페이지 + 규칙 trigger 표 | boot 시 약 700줄 읽기 | 매 세션 토큰·누락 위험 비교 |
| B-2 | 수용 기준 | 템플릿에 `AC-n` 표, testrecord에 AC→증거 대응표 | 워크플로는 "acceptance criteria"를 요구하나 템플릿은 번호 없는 Verification Plan | AC id 도입 |
| B-3 | 상태 수 | 7개 | 12개 | INTEGRATED/REGRESSION_PASSED 분리가 실제로 잡아낸 사례가 있는지 |
| B-4 | 산출물 | 3종 + 섹션 | 6종 | handoff 파일이 다음 단계에서 실제로 읽히는지 |

## 12. Implementation Plan
- [x] Step 1: 진입점, 모순 정리
- [x] Step 2: 템플릿, todo 문법, known_issues, spec 규칙
- [ ] Step 3: delegation.md, 워크플로
- [ ] Step 4: diagrams.md, 020-04 스펙 초안
- [ ] Step 5: lint, 빌드 스크립트, presets, hooks

## 13. Verification Plan
- [ ] AC-1–AC-9 증거를 `docs/tasks/feature_090-01-agent-process/testrecord.md`에 기록

## History / Amendments
- 2026-10-28: 사용자가 채팅에서 1–5단계 적용 순서와 camelCase 명명을 승인. 이 스펙은 그 결정을 기록한 것.
