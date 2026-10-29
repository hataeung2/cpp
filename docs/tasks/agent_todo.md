# atugcc — Agent Task List

프로젝트: **atugcc** (C++20/23 기반 프레임워크 라이브러리)

## Grammar
- Task line: `- !STATE | NNN-SS | Title` or `- !STATE | NNN-SS | [Title](/docs/specs/<file>.md)`, optionally followed by ` — note` and `(branch: \`...\`)`.
- **ID**: `NNN` = group = Phase × 10 + sub-phase (Phase 1 → `010`, Phase 2.3 → `023`); `SS` = two-digit sequence in the group. Amendment of a task: `NNN-SS-PP`, as an indented line under the original ([spec.md](/.agent/rules/spec.md) §4).
- **States**: `BACKLOG` → `SPEC_DRAFT` → `APPROVED` → `DEV` → `TEST` → `DONE`; `BLOCKED` (note: reason, owner, unblock condition).
- Group heading ends with `(k/n DONE)`. Only the lead agent moves states.
- `legacy` = done before 090-01: no task ID in its branch or spec name, no approval record.

---

## Phase 0: 프로젝트 기반 설정 (1/1 DONE)
- !DONE | 000-01 | [프로젝트 구조 재배치 및 CMake 현대화](/docs/specs/01_project_restructure.md) — legacy (branch: `feature/01_project_restructure`)

## Phase 1: 코어 모듈 전환 (atugcc::core) (7/7 DONE)
- !DONE | 010-01 | [RingBuffer 모듈 C++20 전환](/docs/specs/03_ring_buffer_modernize.md) — legacy (branch: `feature/ring-buffer-modernize`)
- !DONE | 010-02 | [TimeStamp 모듈 C++20 전환](/docs/specs/04_timestamp_modernize.md) — legacy (branch: `feature/timestamp-modernize`)
- !DONE | 010-03 | [MemoryDump 플랫폼 추상화](/docs/specs/05_memory_dump_refactor.md) — legacy, 010-01 브랜치에서 함께 진행 (branch: `feature/ring-buffer-modernize`)
- !DONE | 010-04 | [dlog 매크로 → std::source_location 기반 함수 전환](/docs/specs/06_dlog_modernize.md) — legacy, 010-01 브랜치에서 함께 진행 (branch: `feature/ring-buffer-modernize`)
- !DONE | 010-05 | [ErrorCode / std::expected 통일 오류 처리 레이어](/docs/specs/09_error_expected.md) — legacy, 제안 상태로 구현 (branch: `feature/error-expected`)
- !DONE | 010-06 | [Logger 통합 퍼사드 (RingBuffer + dlog + MemoryDump)](/docs/specs/10_logger_facade.md) — legacy, 제안 상태로 구현 (branch: `feature/logger-facade`)
- !DONE | 010-07 | [Crash Dump 포맷 & 즉시 덤프](/docs/specs/09_001_dump_format.md) — legacy, todo 누락분 보충 (branch: `feature/error-expected-dump-impl`)

## Phase 2.0: 패턴 시각화 도구 (atugcc::pattern::viz) (5/6 DONE)
- !DONE | 020-01 | [패턴 시각화 도구 구현: 터미널 트리·상태 흐름 트레이서(ANSI), 다이어그램 스니펫(PlantUML 기본, Mermaid/D2 선택)](/docs/specs/08_pattern_visualizer.md) — legacy (branch: `feature/pattern-visualizer`)
- !DONE | 020-02 | [전용 콘솔](/docs/specs/08_001_dedicated_console.md) — legacy (branch: `feature/dedicated-console`)
- !SPEC_DRAFT | 020-03 | [벤치마크 옵션](/docs/specs/08_002_benchmark.md)
- !DONE | 020-04 | [다이어그램 가독성: 생성 예산 기반 분할, 반복 횟수 표기](/docs/specs/020_04_diagram_readability.md) — main에 병합 (branch: `feature/020-04-diagram-readability`)
- !DONE | 020-05 | [Tracer 이벤트 스트림: JSON Lines 구조화 출력](/docs/specs/020_05_tracer_event_stream.md) — main에 병합, 070-02 선행 (branch: `feature/020-05-tracer-event-stream`)
- !DONE | 020-06 | [Tracer 구간 시간 측정: span 이벤트와 집계](/docs/specs/020_06_tracer_span_timing.md) — main에 병합, 070-06 선행 (branch: `feature/020-06-tracer-span-timing`)

## Phase 2.1: 생성 패턴 (Creational Patterns) (0/3 DONE)
- !BACKLOG | 021-01 | Factory Method / Abstract — std::expected + concept (생성 과정 추적)
- !BACKLOG | 021-02 | Builder — Fluent API + C++20 Designated Initializers 연결 시각화
- !BACKLOG | 021-03 | Singleton — Thread-safe Singleton & Monostate 로깅 추적

## Phase 2.2: 구조 패턴 (Structural Patterns) (0/5 DONE)
- !BACKLOG | 022-01 | Decorator — CRTP / concept 기반 (실행 시간 조합 시각화 아스키 트리)
- !BACKLOG | 022-02 | Adapter — concept 인터페이스 매핑 및 호환성 브릿지 로깅
- !BACKLOG | 022-03 | Facade — 서브시스템 캡슐화 후단 호출 컴포넌트 시퀀스 시각화
- !BACKLOG | 022-04 | Proxy — Lazy initialization 및 자원 접근 제어 이벤트 트레이싱
- !BACKLOG | 022-05 | Flyweight — 메모리 풀 및 공유 상태(객체 재사용) 추적 로깅

## Phase 2.3: 행동 패턴 (Behavioral Patterns) (0/6 DONE)
- !BACKLOG | 023-01 | State — std::variant + std::visit 상태 머신 전이(기존 상태 -> 새 상태) 흐름도 출력
- !BACKLOG | 023-02 | Observer — concept 기반 이벤트 시스템 브로드캐스트 및 수신부 시퀀스 시각화
- !BACKLOG | 023-03 | Command — std::move_only_function 기반 Undo/Redo 실행 스택 추적
- !BACKLOG | 023-04 | Strategy — 런타임 알고리즘 객체 교체 및 호출 추적
- !BACKLOG | 023-05 | Iterator — std::ranges 뷰 파이프라인(`|`) 데이터 변환 과정 시각화
- !BACKLOG | 023-06 | Memento — 객체 상태 스냅샷 저장 및 구조 복원 과정 시각화

## Phase 2.4: 아키텍처 패턴 (Architectural Patterns) (0/1 DONE)
- !BACKLOG | 024-01 | DI (Dependency Injection) — concept 기반 컨테이너 의존성 주입 연결 트리 구조 시각화

## Phase 3: Adapter 레이어 (atugcc::adapter) (0/2 DONE)
- !BACKLOG | 030-01 | Adapter 인터페이스 설계
- !BACKLOG | 030-02 | PostgreSQL (pqxx) Adapter 구현

## Phase 4: 라이브러리 샘플 / 테스트 현대화 (0/2 DONE)
- !BACKLOG | 040-01 | shape / sound 라이브러리 현대화
- !BACKLOG | 040-02 | GoogleTest 테스트 확장

## Phase 5: C++ Evolution 문서 (0/6 DONE)
- !BACKLOG | 050-01 | concepts vs SFINAE
- !BACKLOG | 050-02 | std::format vs iostream/fmt
- !BACKLOG | 050-03 | std::jthread vs std::thread
- !BACKLOG | 050-04 | std::expected vs exceptions
- !BACKLOG | 050-05 | std::ranges vs raw loops
- !BACKLOG | 050-06 | std::variant+visit vs virtual dispatch

## Phase 6: Game Engine Core (atugcc::engine) (0/10 DONE)
- !SPEC_DRAFT | 060-01 | [어댑터 기반 엔진 아키텍처 설계 (Adapter Framework)](/docs/specs/07_game_engine_adapters.md)
- !BACKLOG | 060-02 | 윈도우 생성 및 메인 게임 루프 관리 (Window & Loop)
- !BACKLOG | 060-03 | 게임 입력 시스템 추상화 (Input Manager - Keyboard/Mouse/Gamepad)
- !BACKLOG | 060-04 | C++20 기반 고속 게임 수학 라이브러리 (atugcc::math - Vector, Matrix)
- !BACKLOG | 060-05 | 엔티티 컴포넌트 시스템 (ECS - Entity Component System) 설계
- !BACKLOG | 060-06 | 그래픽스 렌더링 추상화 레이어 (RHI - Vulkan/OpenGL 기반)
- !BACKLOG | 060-07 | 비동기 자원 관리자 (Asset Manager - Texture, Mesh, Audio)
- !BACKLOG | 060-08 | 충돌 처리 및 기본 물리 연산 시스템 (Physics & Collision)
- !BACKLOG | 060-09 | 씬 / 상태 전환 관리자 (Scene & State Manager)
- !BACKLOG | 060-10 | Steamworks SDK 연동 어댑터 (atugcc::adapter::steam)

## Phase 7: 웹 플레이그라운드 (로컬 전용) (4/8 DONE)
- !DONE | 070-01 | [레슨 구조: 트랙·레슨·유닛, preset 빌드, 레슨 인덱스](/docs/specs/070_01_lesson_structure.md) — main에 병합 (branch: `feature/070-01-lesson-structure`)
- !DONE | 070-02 | [로컬 웹 플레이그라운드: 편집·빌드·실행·시각화](/docs/specs/070_02_web_playground.md) — main에 병합, `py -3 tools/playground.py --open` (branch: `feature/070-02-web-playground`)
  - !DONE | 070-02-01 | [플레이그라운드 --port를 페이지 포트로 (dev 모드 포함)](/docs/specs/070_02_01_playground_port.md) — main에 병합, KI-017 종료 (branch: `feature/070-02-01-playground-port`)
- !BACKLOG | 070-03 | essentials 트랙 커리큘럼 (core, lambda·concurrency 문법, 스레드·로그 관리)
- !BACKLOG | 070-04 | patterns 트랙 커리큘럼 (도메인·상황별 패턴 적용, main.cpp 샘플·example_visualizer 이전)
- !BACKLOG | 070-05 | 웹 플레이그라운드 공개 여부 결정 (샌드박스·호스팅) — 사용자 결정 대기
- !DONE | 070-06 | [장시간 실행 프로필과 구간 시간(Timings) 화면](/docs/specs/070_06_long_run_timings.md) — main에 병합, 서버 span 집계(설계 기록 §2.4), 레슨 `span_timing` (branch: `feature/070-06-long-run-timings`)
- !BACKLOG | 070-07 | 단계별 다이어그램 재생 (N번째 이벤트까지의 다이어그램, C++ diagramParts 범위 지정 필요) — 070-02 선행

## Phase 9: 개발 프로세스 / 유지보수 (3/3 DONE)
- !DONE | 090-01 | [에이전트 운영 규칙 개선 (ai_sec 규칙 비교 반영)](/docs/specs/090_01_agent_process.md) — main에 병합 (branch: `feature/090-01-agent-process`)
- !DONE | 090-02 | [함수 명명 camelCase 통일](/docs/specs/090_02_camelcase_rename.md) — main에 병합 (branch: `feature/090-02-camelcase-rename`)
- !DONE | 090-03 | [vcpkg manifest로 Boost 자동 공급](/docs/specs/090_03_vcpkg_manifest.md) — main에 병합 (branch: `feature/090-03-vcpkg-manifest`)
