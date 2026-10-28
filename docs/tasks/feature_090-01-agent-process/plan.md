# Plan: 090-01 에이전트 운영 규칙 개선

- Spec: [/docs/specs/090_01_agent_process.md](/docs/specs/090_01_agent_process.md) (approved 2026-10-28)
- Branch: `feature/090-01-agent-process` (from `feature/dedicated-console` tip, KI-003)

## Files

### Step 1 — 진입점, 규칙 모순
- [NEW] `/CLAUDE.md`, `/AGENTS.md`: 진입 파일, boot 문서만 가리킴
- [NEW] `/docs/agent_start_prompt.md`: 단일 boot 문서, 규칙 trigger 표, non-negotiable 6개
- [MODIFY] `/.agent/rules/test.md`: 즉석 cmake 제거, 실제 경고 수준(`/W4`, `-Wall -Wextra`), `atugcc_tests` 좁은 실행, AC 증거표
- [MODIFY] `/.agent/workflows/start-develop-one-task.md`: 5단계 중복 제거, 상태 전이, 스펙 승인 확인
- [MODIFY] `/.agent/rules/config.md`: 절대 경로 → `%VSDEVCMD%`, `VCPKG_ROOT`, binaryDir 예시를 실제 preset과 일치
- [MODIFY] `/.agent/rules/impl.md`: camelCase 확정, legacy snake_case는 090-02

### Step 2 — 스펙·작업 관리
- [MODIFY] `/docs/specs/00_template.md`: frontmatter, Assumptions, AC, Out of Scope, Documentation Updates, History
- [MODIFY] `/.agent/rules/spec.md`: `NNN_SS` 이름, 승인 절차, 재오픈, legacy 번호
- [MODIFY] `/docs/tasks/agent_todo.md`: 새 문법, 누락 작업 010-07 보충, 020-04 / 090-01 / 090-02 추가
- [NEW] `/docs/known_issues.md`: KI-001–KI-005
- [MODIFY] `/docs/specs/08_002_benchmark.md`, `/docs/specs/07_game_engine_adapters.md`: frontmatter (`approved: null`)
- [MODIFY] `/README.md`: docs 트리, 에이전트 진입점 안내

### Step 3 — 위임·검토·테스트 순서
- [NEW] `/.agent/rules/delegation.md`: 작성자≠검증자, 위험도 기준 작성자 배정, C++ 위험 목록, 호출 규칙, 모델 체인, 단위표 형식
- [NEW] `/.agent/scripts/subagent_run.py`: ai_sec에서 그대로 복사 (출처 주석만 추가)
- [NEW] `/.agent/scripts/test_agent_scripts.py`: ai_sec `SubagentRunTest` 이식 (24 tests)
- [NEW] `/.claude/agents/cpp-reviewer.md`: Claude 읽기 전용 리뷰어
- [MODIFY] `/.agent/workflows/start-develop-one-task.md`: 단위표 → 단위별 실행·검토·확인 → Tester 단계(AC 기준) → 통합
- [MODIFY] `/docs/agent_start_prompt.md`: 규칙 표에 delegation 추가

### Step 4 — 시각화 가독성
- [NEW] `/.agent/rules/diagrams.md`: 사실 보존, 생성 예산, 뷰어 정책, 문서 한도, 백엔드 함정
- [NEW] `/docs/specs/020_04_diagram_readability.md`: 초안, `approved: null`
- [MODIFY] `/docs/tasks/agent_todo.md`: 020-04 → `SPEC_DRAFT`
- [MODIFY] `/docs/known_issues.md`: KI-005 문구 정정, KI-006 추가
- [MODIFY] `/docs/agent_start_prompt.md`: 규칙 표에 diagrams 추가

### Step 5 — 기계 검증
- [NEW] `/.agent/scripts/agent_common.py`: lint·hook·build 공용 판정(절대 경로, 즉석 cmake, frontmatter, todo 문법)
- [NEW] `/.agent/scripts/lint_docs.py`: 링크, 절대 경로, todo 문법·개수, 스펙 승인 상태, KI id; 봉인 기록은 INFO; `--status`
- [NEW] `/.agent/scripts/build.py`: preset 선택, VsDevCmd, Windows→WSL, 복사된/중단된 빌드 디렉터리 감지
- [NEW] `/.claude/hooks/guard.py`, `/.claude/settings.json`: PreToolUse 차단(즉석 cmake, main 커밋, 절대 경로 쓰기)
- [MODIFY] `/.agent/scripts/test_agent_scripts.py`: +15 tests (39 total)
- [MODIFY] `/CMakeLists.txt`: vcpkg 툴체인 탐색(`ATUGCC_VCPKG_ROOT` → `VCPKG_ROOT` → 시스템), `ATUGCC_WARNINGS_AS_ERRORS`, `ATUGCC_SANITIZERS`
- [MODIFY] `/CMakePresets.json`: 절대 경로 제거, `linux-x64-asan`/`-tsan`, 경고=오류, testPresets
- [MODIFY] `/tests/CMakeLists.txt`: TSan 테스트를 `setarch -R`로 실행
- [DELETE] `/.agent/rules/CMakePresets.example.json`
- [MODIFY] `/.agent/rules/config.md`(build.py 중심으로 재작성), `test.md`(sanitizer 행렬, docs gate), 워크플로, boot, README, known_issues(KI-004 CLOSED, KI-007–009)

## Decisions during implementation
- 상태 문법은 ai_sec의 `!STATE | ID |`를 따르되 상태를 7개로 줄임 (spec Assumption 3).
- legacy 스펙 링크(`ring_buffer.h`)는 고치지 않고 KI-002로 기록 (spec.md §5).
- 툴체인은 preset이 아니라 `CMakeLists.txt`가 고른다: `CMakeUserPresets.json`은 같은 이름의 preset을 덮어쓸 수 없고, VS 개발자 환경이 `VCPKG_ROOT`를 번들 vcpkg로 바꾸기 때문에 `ATUGCC_VCPKG_ROOT`를 우선한다 (KI-004, KI-007).
- 경고=오류를 모든 preset에 켰다: Linux 세 preset이 GCC 13에서 경고 없이 빌드됨을 확인한 뒤.
