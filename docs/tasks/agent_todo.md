# atugcc — Agent Task List

프로젝트: **atugcc** (C++20/23 기반 프레임워크 라이브러리)

## Grammar
- Task line: `- !STATE | NNN-SS | Title` or `- !STATE | NNN-SS | [Title](/docs/specs/<file>.md)`, optionally followed by ` — note` and `(branch: \`...\`)`.
- **ID**: `NNN` = group = Phase × 10 + sub-phase (Phase 1 → `010`, Phase 2.3 → `023`); `SS` = two-digit sequence in the group. Amendment of a task: `NNN-SS-PP`, as an indented line under the original ([spec.md](/.agent/rules/spec.md) §4).
- **States**: `BACKLOG` → `SPEC_DRAFT` → `APPROVED` → `DEV` → `TEST` → `DONE`; `BLOCKED` (note: reason, owner, unblock condition).
- Group heading ends with `(k/n DONE)`. Only the lead agent moves states.
- `legacy` = done before 090-01: no task ID in its branch or spec name, no approval record.

## 진행 순서 (2026-10-30, [090-05](/docs/specs/090_05_backlog_sync.md))
방향(사용자, 2026-10-30): 기존 레슨 기반을 먼저 확실히 다진 뒤, 레슨을 하나씩 더하면서 게임 엔진도 함께 만들어 간다. 순서를 바꾸는 것은 사용자 결정이다. 열린 KI의 주인은 [known_issues.md](/docs/known_issues.md) 표에 있다.

**A. 기반 다지기** (차례대로)
1. ~~010-08 Logger 정비~~ (DONE 2026-10-30).
1a. **010-09 Logger 스레드별 버퍼와 소비자 스레드**: 070-03보다 먼저(사용자 2026-10-30).
1b. **010-10 메모리 매핑 버퍼와 복구**: 010-09 바로 뒤(사용자 2026-10-30).
2. **090-06 개발 도구 정비** (KI-008, KI-011, KI-012): 작고 독립적이다. 1과 순서를 바꿔도 된다.
3. **070-03 essentials 커리큘럼**: 주제는 [레슨 후보 목록](/docs/tasks/lesson_candidates.md)의 essentials에서 고른다.
4. **040-02 CTest 시나리오 테스트**: 이후 레슨·패턴·엔진 작업이 시나리오 테스트를 바로 쓰게 한다.

**B. 레슨과 엔진 병행** (A가 끝나면 060-01 스펙 재검토부터. 그 뒤 두 줄에서 번갈아 하나씩 고른다)
- 레슨 줄: 헤더가 있는 패턴(023-02 Observer 레슨 → 021-01 → 022-01 → 023-03 → 023-05 → 024-01, 각자 KI-023의 몫을 닫음) → 070-07 단계별 다이어그램 재생 → 070-04 patterns 트랙 구성 → 새 패턴(021-02, 021-03, 022-02 ~ 022-05, 023-04, 023-06) → 040-01 shape/sound 현대화.
- 엔진 줄(제안 순서: 지금의 텍스트 플레이그라운드에서 바로 실습할 수 있는 것부터): 060-01 → 060-04 수학 → 060-05 ECS → 060-02 창·루프 → 070-09 엔진 출력 보기 → 060-03 입력 → 060-06 RHI → 060-07 자원 → 060-08 물리 → 060-09 씬 → 060-10 Steam. 엔진 기능마다 레슨을 하나씩 더한다.
- backend 레이어: 030-01은 060-01과 같은 원칙이므로 060-01과 함께 또는 바로 뒤에, 030-02(KI-009)는 DB가 필요해질 때.

**그 밖**
- 사용자 결정 대기: 070-05 공개 여부(KI-015), KI-024 CI 도입.
- 재발하면 조사: KI-018, KI-020. 계기가 생기면: KI-006, KI-010, KI-016, KI-022.

## 작업 공통 원칙 (090-05)
- 패턴 작업(021–024)은 헤더(`atugcc::pattern`), Tracer 연결, 테스트, patterns 트랙 레슨까지 포함한다.
- 외부 의존은 교체 가능한 backend 뒤에 둔다([impl.md](/.agent/rules/impl.md) §5). Phase 3과 060-01이 같은 원칙을 따른다. "adapter"는 GoF Adapter 패턴(022-02)에만 쓴다.
- 엔진 기능(Phase 6)은 레슨으로도 실습할 수 있게 만든다. 플레이그라운드 쪽 연결은 070-09.

## 취소된 작업
ID는 다시 쓰지 않는다.
- 020-03 벤치마크 옵션 ([스펙](/docs/specs/08_002_benchmark.md)) — 2026-10-29 취소(사용자 결정, 090-05). Tracer 성능 측정은 020-06(`SpanMeter`, `SpanCost`)이 맡는다. 020-06이 재지 않는 나머지는 KI-022.

---

## Phase 0: 프로젝트 기반 설정 (1/1 DONE)
- !DONE | 000-01 | [프로젝트 구조 재배치 및 CMake 현대화](/docs/specs/01_project_restructure.md) — legacy (branch: `feature/01_project_restructure`)

## Phase 1: 코어 모듈 전환 (atugcc::core) (8/10 DONE)
- !DONE | 010-01 | [RingBuffer 모듈 C++20 전환](/docs/specs/03_ring_buffer_modernize.md) — legacy (branch: `feature/ring-buffer-modernize`)
- !DONE | 010-02 | [TimeStamp 모듈 C++20 전환](/docs/specs/04_timestamp_modernize.md) — legacy (branch: `feature/timestamp-modernize`)
- !DONE | 010-03 | [MemoryDump 플랫폼 추상화](/docs/specs/05_memory_dump_refactor.md) — legacy, 010-01 브랜치에서 함께 진행 (branch: `feature/ring-buffer-modernize`)
- !DONE | 010-04 | [dlog 매크로 → std::source_location 기반 함수 전환](/docs/specs/06_dlog_modernize.md) — legacy, 010-01 브랜치에서 함께 진행 (branch: `feature/ring-buffer-modernize`)
- !DONE | 010-05 | [ErrorCode / std::expected 통일 오류 처리 레이어](/docs/specs/09_error_expected.md) — legacy, 제안 상태로 구현 (branch: `feature/error-expected`)
- !DONE | 010-06 | [Logger 통합 퍼사드 (RingBuffer + dlog + MemoryDump)](/docs/specs/10_logger_facade.md) — legacy, 제안 상태로 구현 (branch: `feature/logger-facade`)
- !DONE | 010-07 | [Crash Dump 포맷 & 즉시 덤프](/docs/specs/09_001_dump_format.md) — legacy, todo 누락분 보충 (branch: `feature/error-expected-dump-impl`)
- !DONE | 010-08 | [Logger 정비: 호출 위치, 공유 계약, crash dump 준비, 로그 큐, 공유/스레드별 성능 측정](/docs/specs/010_08_logger_cleanup.md) — main에 병합, KI-013·014·021·025 종료, 측정 결과는 testrecord (branch: `feature/010-08-logger-cleanup`)
- !DEV | 010-09 | [Logger 스레드별 버퍼와 소비자 스레드: 잠금 없는 기록, 모든 스레드의 crash dump, 실패 유형별 로그 보존](/docs/specs/010_09_logger_thread_buffers.md) — 070-03보다 먼저(사용자 2026-10-30). KI-026, KI-027 (branch: `feature/010-09-logger-thread-buffers`)
- !BACKLOG | 010-10 | 메모리 매핑 파일 로그 버퍼와 다음 실행 때 복구 (SIGKILL·강제 종료 대비) — 010-09 선행. 사용자 결정 2026-10-30: 한다. 복구한 줄은 별도 파일에 남겨 따로 확인

## Phase 2.0: 패턴 시각화 도구 (atugcc::pattern::viz) (5/5 DONE)
- !DONE | 020-01 | [패턴 시각화 도구 구현: 터미널 트리·상태 흐름 트레이서(ANSI), 다이어그램 스니펫(PlantUML 기본, Mermaid/D2 선택)](/docs/specs/08_pattern_visualizer.md) — legacy (branch: `feature/pattern-visualizer`)
- !DONE | 020-02 | [전용 콘솔](/docs/specs/08_001_dedicated_console.md) — legacy (branch: `feature/dedicated-console`)
- !DONE | 020-04 | [다이어그램 가독성: 생성 예산 기반 분할, 반복 횟수 표기](/docs/specs/020_04_diagram_readability.md) — main에 병합 (branch: `feature/020-04-diagram-readability`)
- !DONE | 020-05 | [Tracer 이벤트 스트림: JSON Lines 구조화 출력](/docs/specs/020_05_tracer_event_stream.md) — main에 병합, 070-02 선행 (branch: `feature/020-05-tracer-event-stream`)
- !DONE | 020-06 | [Tracer 구간 시간 측정: span 이벤트와 집계](/docs/specs/020_06_tracer_span_timing.md) — main에 병합, 070-06 선행, 취소된 020-03의 목적도 맡음 (branch: `feature/020-06-tracer-span-timing`)

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
- !DONE | 023-01 | [State — std::variant + std::visit 상태 머신 전이(기존 상태 -> 새 상태) 흐름도 출력](/docs/specs/08_pattern_visualizer.md) — legacy, 020-01에서 구현(`state.hpp`, Tracer, `StateMachineTest`), 레슨 `02_patterns/01_device_state_machine`; 090-05에서 동기화 (branch: `feature/pattern-visualizer`)
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

## Phase 4: 라이브러리 샘플 현대화 / 시나리오 테스트 (0/2 DONE)
- !BACKLOG | 040-01 | shape / sound 라이브러리를 최신 C++로 현대화 — 지금은 헤더 11·23줄 스텁. 표준 수준(C++23과 컴파일러가 지원하는 C++26 기능)은 스펙에서 정한다
- !BACKLOG | 040-02 | CTest 시나리오 테스트: 단위 테스트 외에 시나리오를 추가하고 실행하는 기능 (GoogleTest 기반) — 지금은 gtest 전체가 CTest 테스트 하나(`AllTests`)다. `gtest_discover_tests`와 CTest label(`ctest -L scenario`)로 시나리오를 따로 등록·선택할 수 있다

## Phase 6: Game Engine Core (atugcc::engine) — 모든 기능을 플레이그라운드에서도 실습 (0/10 DONE)
- !SPEC_DRAFT | 060-01 | [교체 가능한 백엔드(pluggable backend) 기반 엔진 아키텍처 설계](/docs/specs/07_game_engine_adapters.md) — 2026-10-29 용어 변경(adapter → backend), 착수 전에 스펙 재검토
- !BACKLOG | 060-02 | 윈도우 생성 및 메인 게임 루프 관리 (Window & Loop)
- !BACKLOG | 060-03 | 게임 입력 시스템 추상화 (Input Manager - Keyboard/Mouse/Gamepad)
- !BACKLOG | 060-04 | C++20 기반 고속 게임 수학 라이브러리 (atugcc::math - Vector, Matrix)
- !BACKLOG | 060-05 | 엔티티 컴포넌트 시스템 (ECS - Entity Component System) 설계
- !BACKLOG | 060-06 | 그래픽스 렌더링 추상화 레이어 (RHI - Vulkan/OpenGL 기반)
- !BACKLOG | 060-07 | 비동기 자원 관리자 (Asset Manager - Texture, Mesh, Audio)
- !BACKLOG | 060-08 | 충돌 처리 및 기본 물리 연산 시스템 (Physics & Collision)
- !BACKLOG | 060-09 | 씬 / 상태 전환 관리자 (Scene & State Manager)
- !BACKLOG | 060-10 | Steamworks SDK 연동 백엔드 (atugcc::backend::steam)

## Phase 7: 웹 플레이그라운드 (로컬 전용) (5/10 DONE)
- !DONE | 070-01 | [레슨 구조: 트랙·레슨·유닛, preset 빌드, 레슨 인덱스](/docs/specs/070_01_lesson_structure.md) — main에 병합 (branch: `feature/070-01-lesson-structure`)
- !DONE | 070-02 | [로컬 웹 플레이그라운드: 편집·빌드·실행·시각화](/docs/specs/070_02_web_playground.md) — main에 병합, `py -3 tools/playground.py --open` (branch: `feature/070-02-web-playground`)
  - !DONE | 070-02-01 | [플레이그라운드 --port를 페이지 포트로 (dev 모드 포함)](/docs/specs/070_02_01_playground_port.md) — main에 병합, KI-017 종료 (branch: `feature/070-02-01-playground-port`)
- !BACKLOG | 070-03 | essentials 트랙 커리큘럼 (core, lambda·concurrency 문법, 스레드·로그 관리) — 주제 후보: [lesson_candidates.md](/docs/tasks/lesson_candidates.md), 010-08 선행
- !BACKLOG | 070-04 | patterns 트랙 구성 (도메인·상황별 패턴 적용, main.cpp 샘플·example_visualizer 이전) — 패턴별 레슨은 각 패턴 작업(021–024)이 더한다. 이 작업은 트랙 순서, 여러 패턴을 엮는 도메인 시나리오, 기존 샘플 이전
- !BACKLOG | 070-05 | 웹 플레이그라운드 공개 여부 결정 (샌드박스·호스팅) — 사용자 결정 대기
- !DONE | 070-06 | [장시간 실행 프로필과 구간 시간(Timings) 화면](/docs/specs/070_06_long_run_timings.md) — main에 병합, 서버 span 집계(설계 기록 §2.4), 레슨 `span_timing` (branch: `feature/070-06-long-run-timings`)
- !BACKLOG | 070-07 | 단계별 다이어그램 재생 (N번째 이벤트까지의 다이어그램, C++ diagramParts 범위 지정 필요) — 070-02 선행
- !DONE | 070-08 | [플레이그라운드 소개 페이지 (이 페이지와 라이브러리·레슨의 관계)](/docs/specs/070_08_playground_intro.md) — main에 병합, `lessons/intro.md` + ⓘ 소개, 루트 README Workflow (branch: `feature/070-08-playground-intro`)
- !BACKLOG | 070-09 | 플레이그라운드에서 엔진 출력 보기 (창 프레임과 입력을 페이지와 연결) — 060-02, 060-06 선행. 지금 페이지는 텍스트·이벤트 스트림만 보여 준다

## Phase 9: 개발 프로세스 / 유지보수 (5/6 DONE)
- !DONE | 090-01 | [에이전트 운영 규칙 개선 (ai_sec 규칙 비교 반영)](/docs/specs/090_01_agent_process.md) — main에 병합 (branch: `feature/090-01-agent-process`)
- !DONE | 090-02 | [함수 명명 camelCase 통일](/docs/specs/090_02_camelcase_rename.md) — main에 병합 (branch: `feature/090-02-camelcase-rename`)
- !DONE | 090-03 | [vcpkg manifest로 Boost 자동 공급](/docs/specs/090_03_vcpkg_manifest.md) — main에 병합 (branch: `feature/090-03-vcpkg-manifest`)
- !DONE | 090-04 | [문서 게이트가 lessons/ Markdown 링크도 검사 (KI-019)](/docs/specs/090_04_lessons_doc_links.md) — main에 병합, KI-019 종료 (branch: `feature/090-04-lessons-doc-links`)
- !DONE | 090-05 | [백로그 동기화와 진행 순서 정리 (2026-10-29 점검)](/docs/specs/090_05_backlog_sync.md) — main에 병합(사용자 검토 2026-10-30). 020-03 취소, Phase 5 → 레슨 후보 목록, adapter → backend, KI-021–KI-024 (branch: `feature/090-05-backlog-sync`)
- !BACKLOG | 090-06 | 개발 도구 정비: guard hook 따옴표 처리(KI-008), Windows 콘솔 UTF-8(KI-011), `build.py --gtest-filter`의 TSan launcher(KI-012)
