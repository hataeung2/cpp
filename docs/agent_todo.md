# atugcc — Agent Task List

프로젝트: **atugcc** (C++20/23 기반 프레임워크 라이브러리)

## Grammar
- Task line: `- !STATE | NNN-SS | Title` or `- !STATE | NNN-SS | [Title](/docs/specs/<file>.md)`, optionally followed by ` — note` and `(branch: \`...\`)`.
- **ID**: `NNN` = group = Phase × 10 + sub-phase (Phase 1 → `010`, Phase 2.3 → `023`); `SS` = two-digit sequence in the group. Amendment of a task: `NNN-SS-PP`, as an indented line under the original ([spec.md](/.agent/rules/spec.md) §4).
- **States**: `BACKLOG` → `SPEC_DRAFT` → `APPROVED` → `DEV` → `TEST` → `DONE`; `BLOCKED` (note: reason, owner, unblock condition).
- Group heading ends with `(k/n DONE)`. Only the lead agent moves states.
- DONE tasks move to [archive/agent_todo_done.md](/docs/archive/agent_todo_done.md) under the same group name (`py -3 .agent/scripts/archive_docs.py`); `(k/n DONE)` counts both files. The next free `SS` in a group is checked in both.
- `legacy` = done before 090-01: no task ID in its branch or spec name, no approval record.

## 진행 순서 (2026-10-30, [090-05](/docs/specs/090_05_backlog_sync.md))
방향(사용자, 2026-10-30): 기존 레슨 기반을 먼저 확실히 다진 뒤, 레슨을 하나씩 더하면서 게임 엔진도 함께 만들어 간다. 순서를 바꾸는 것은 사용자 결정이다. 열린 KI의 주인은 [known_issues.md](/docs/known_issues.md) 표에 있다.

**A. 기반 다지기**: 2026-11-05에 끝남(010-08 ~ 070-15, 기록은 [archive](/docs/archive/agent_todo_done.md)).

**B. 레슨과 엔진 병행** (060-01 스펙 재검토부터. 그 뒤 두 줄에서 번갈아 하나씩 고른다)
- 레슨 줄: 헤더가 있는 패턴(023-02 Observer 레슨 → 021-01 → 022-01 → 023-03 → 023-05 → 024-01, 각자 KI-023의 몫을 닫음) → 070-07 단계별 다이어그램 재생 → 070-04 patterns 트랙 구성 → 새 패턴(021-02, 021-03, 022-02 ~ 022-05, 023-04, 023-06).
- 엔진 줄(제안 순서: 지금의 텍스트 플레이그라운드에서 바로 실습할 수 있는 것부터): 060-01 → 060-04 수학 → 060-05 ECS → 060-02 창·루프 → 070-09 엔진 출력 보기 → 060-03 입력 → 060-06 RHI → 060-07 자원 → 060-08 물리 → 060-09 씬 → 060-10 Steam. 엔진 기능마다 레슨을 하나씩 더한다.
- backend 레이어: 030-01은 060-01과 같은 원칙이므로 060-01과 함께 또는 바로 뒤에, 030-02(KI-009)는 DB가 필요해질 때.

**C. 에이전트 설정 정비** (2026-11-06 사용자 요청, B보다 먼저, 차례대로): 090-08 → 090-09 → 090-10 → 090-11. 앞 task가 main에 병합된 뒤 다음 task의 브랜치를 만든다(같은 파일을 고친다).

**그 밖**
- 사용자 결정 대기: 070-05 공개 여부(KI-015), KI-024 CI 도입.
- 조건이 오면 다시 보는 KI는 DEFERRED: `py -3 .agent/scripts/lint_docs.py --deferred`.

## 작업 공통 원칙 (090-05)
- 패턴 작업(021–024)은 헤더(`atugcc::pattern`), Tracer 연결, 테스트, patterns 트랙 레슨까지 포함한다.
- 패턴 작업(021–024)과 엔진 작업(Phase 6)은 단위 테스트에 더해 시나리오 테스트(`tests/scenario/`)를 하나 이상 더한다 (040-02, [test.md](/.agent/rules/test.md) §2).
- 외부 의존은 교체 가능한 backend 뒤에 둔다([impl.md](/.agent/rules/impl.md) §5). Phase 3과 060-01이 같은 원칙을 따른다. "adapter"는 GoF Adapter 패턴(022-02)에만 쓴다.
- 엔진 기능(Phase 6)은 레슨으로도 실습할 수 있게 만든다. 플레이그라운드 쪽 연결은 070-09.

## 취소된 작업
ID는 다시 쓰지 않는다.
- 020-03 벤치마크 옵션 ([스펙](/docs/specs/08_002_benchmark.md)) — 2026-10-29 취소(사용자 결정, 090-05). Tracer 성능 측정은 020-06(`SpanMeter`, `SpanCost`)이 맡는다. 020-06이 재지 않는 나머지는 KI-022.

---

## Phase 0: 프로젝트 기반 설정 (1/1 DONE)

## Phase 1: 코어 모듈 전환 (atugcc::core) (11/11 DONE)

## Phase 2.0: 패턴 시각화 도구 (atugcc::pattern::viz) (5/5 DONE)

## Phase 2.1: 생성 패턴 (Creational Patterns) (0/3 DONE)
- !BACKLOG | 021-01 | Factory Method / Abstract — std::expected + concept (생성 과정 추적) — 있음: `factory.hpp`(legacy, 샘플 동작 확인 2026-10-29). 남은 일: `atugcc::pattern` 이전, Tracer 연결, 테스트, 레슨 (KI-023)
- !BACKLOG | 021-02 | Builder — Fluent API + C++20 Designated Initializers 연결 시각화 — 새로 작성
- !BACKLOG | 021-03 | Singleton — Thread-safe Singleton & Monostate 로깅 추적 — 새로 작성

## Phase 2.2: 구조 패턴 (Structural Patterns) (0/5 DONE)
- !BACKLOG | 022-01 | Decorator — CRTP / concept 기반 (실행 시간 조합 시각화 아스키 트리) — 있음: `decorator.hpp`(legacy, 샘플 동작 확인 2026-10-29). 남은 일: `atugcc::pattern` 이전, Tracer 연결, 테스트, 레슨 (KI-023)
- !BACKLOG | 022-02 | Adapter — concept 인터페이스 매핑 및 호환성 브릿지 로깅 — 새로 작성. GoF 패턴이며, 외부 의존을 감싸는 backend(Phase 3, 060-01)와는 다르다
- !BACKLOG | 022-03 | Facade — 서브시스템 캡슐화 후단 호출 컴포넌트 시퀀스 시각화 — 새로 작성
- !BACKLOG | 022-04 | Proxy — Lazy initialization 및 자원 접근 제어 이벤트 트레이싱 — 새로 작성
- !BACKLOG | 022-05 | Flyweight — 메모리 풀 및 공유 상태(객체 재사용) 추적 로깅 — 새로 작성

## Phase 2.3: 행동 패턴 (Behavioral Patterns) (1/6 DONE)
- !BACKLOG | 023-02 | Observer — concept 기반 이벤트 시스템 브로드캐스트 및 수신부 시퀀스 시각화 — 있음: `observer.hpp`(concept, Tracer, `ObserverTest`, 020-01). 남은 일: 레슨
- !BACKLOG | 023-03 | Command — std::move_only_function 기반 Undo/Redo 실행 스택 추적 — 있음: `command.hpp`(legacy, 샘플 동작 확인 2026-10-29). 남은 일: `atugcc::pattern` 이전, Tracer 연결, 테스트, 레슨 (KI-023)
- !BACKLOG | 023-04 | Strategy — 런타임 알고리즘 객체 교체 및 호출 추적 — 새로 작성
- !BACKLOG | 023-05 | Iterator — std::ranges 뷰 파이프라인(`|`) 데이터 변환 과정 시각화 — 있음: `iterator_concept.hpp`(legacy, 샘플 동작 확인 2026-10-29). 남은 일: `atugcc::pattern` 이전, ranges 파이프라인, Tracer 연결, 테스트, 레슨 (KI-023)
- !BACKLOG | 023-06 | Memento — 객체 상태 스냅샷 저장 및 구조 복원 과정 시각화 — 새로 작성

## Phase 2.4: 아키텍처 패턴 (Architectural Patterns) (0/1 DONE)
- !BACKLOG | 024-01 | DI (Dependency Injection) — concept 기반 컨테이너 의존성 주입 연결 트리 구조 시각화 — 있음: `injection.hpp`(legacy, 샘플 동작 확인 2026-10-29). 남은 일: `atugcc::pattern` 이전, Tracer 연결, 테스트, 레슨 (KI-023)

## Phase 3: Pluggable Backend 레이어 (atugcc::backend) (0/2 DONE)
- !BACKLOG | 030-01 | Backend 인터페이스 설계 (concept 또는 순수 인터페이스, `include/atugcc/backend/`, 구현 `src/backends/`)
- !BACKLOG | 030-02 | PostgreSQL (pqxx) Backend 구현 — KI-009

## Phase 4: 범용 라이브러리 (`libs/`, [후보 목록](/docs/lib_candidates.md)) / 시나리오 테스트 (2/2 DONE)

## Phase 6: Game Engine Core (atugcc::engine) — 모든 기능을 플레이그라운드에서도 실습 (0/10 DONE)
- !SPEC_DRAFT | 060-01 | [교체 가능한 백엔드(pluggable backend) 기반 엔진 아키텍처 설계](/docs/specs/07_game_engine_adapters.md) — 2026-10-29 용어 변경(adapter → backend), 착수 전에 스펙 재검토
- !BACKLOG | 060-02 | 윈도우 생성 및 메인 게임 루프 관리 (Window & Loop)
- !BACKLOG | 060-03 | 게임 입력 시스템 추상화 (Input Manager - Keyboard/Mouse/Gamepad)
- !BACKLOG | 060-04 | C++20 기반 고속 게임 수학 라이브러리 (atugcc::math - Vector, Matrix) — `libs/`로 옮길지 060-01 재검토 때 정한다 ([lib_candidates.md](/docs/lib_candidates.md) L10)
- !BACKLOG | 060-05 | 엔티티 컴포넌트 시스템 (ECS - Entity Component System) 설계
- !BACKLOG | 060-06 | 그래픽스 렌더링 추상화 레이어 (RHI - Vulkan/OpenGL 기반)
- !BACKLOG | 060-07 | 비동기 자원 관리자 (Asset Manager - Texture, Mesh, Audio)
- !BACKLOG | 060-08 | 충돌 처리 및 기본 물리 연산 시스템 (Physics & Collision)
- !BACKLOG | 060-09 | 씬 / 상태 전환 관리자 (Scene & State Manager)
- !BACKLOG | 060-10 | Steamworks SDK 연동 백엔드 (atugcc::backend::steam)

## Phase 7: 웹 플레이그라운드 (로컬 전용) (13/17 DONE)
- !BACKLOG | 070-04 | patterns 트랙 구성 (도메인·상황별 패턴 적용, main.cpp 샘플·example_visualizer 이전) — 패턴별 레슨은 각 패턴 작업(021–024)이 더한다. 이 작업은 트랙 순서, 여러 패턴을 엮는 도메인 시나리오, 기존 샘플 이전
- !BACKLOG | 070-05 | 웹 플레이그라운드 공개 여부 결정 (샌드박스·호스팅) — 사용자 결정 대기
- !BACKLOG | 070-07 | 단계별 다이어그램 재생 (N번째 이벤트까지의 다이어그램, C++ diagramParts 범위 지정 필요) — 070-02 선행
- !BACKLOG | 070-09 | 플레이그라운드에서 엔진 출력 보기 (창 프레임과 입력을 페이지와 연결) — 060-02, 060-06 선행. 지금 페이지는 텍스트·이벤트 스트림만 보여 준다

## Phase 9: 개발 프로세스 / 유지보수 (9/11 DONE)
- !DEV | 090-10 | [어느 agent에서나 쓰는 skill: 원본 `.agent/skills/`, Claude·codex 위치로 복사, 차이 검사](/docs/specs/090_10_portable_skills.md)
- !APPROVED | 090-11 | [어느 agent에서나 같은 guard: 판정 `guard_rules.py`, Claude·codex adapter, git pre-commit hook](/docs/specs/090_11_portable_hooks.md)
