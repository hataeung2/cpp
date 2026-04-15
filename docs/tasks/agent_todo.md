# atugcc — Agent Task List

프로젝트: **atugcc** (C++20/23 기반 프레임워크 라이브러리)

---

## Phase 0: 프로젝트 기반 설정
- [x] [프로젝트 구조 재배치 및 CMake 현대화](/docs/specs/01_project_restructure.md)

## Phase 1: 코어 모듈 전환 (atugcc::core)
- [x] [RingBuffer 모듈 C++20 전환](/docs/specs/03_ring_buffer_modernize.md) (branch: `feature/ring-buffer-modernize`)
- [x] [TimeStamp 모듈 C++20 전환](/docs/specs/04_timestamp_modernize.md) (branch: `feature/timestamp-modernize`)
- [x] [MemoryDump 플랫폼 추상화](/docs/specs/05_memory_dump_refactor.md) (branch: `feature/ring-buffer-modernize`)
- [x] [dlog 매크로 → std::source_location 기반 함수 전환](/docs/specs/06_dlog_modernize.md) (branch: `feature/ring-buffer-modernize`)
- [x] [ErrorCode / std::expected 통일 오류 처리 레이어](/docs/specs/09_error_expected.md) *(제안)* (branch: `feature/error-expected`)
- [x] [Logger 통합 퍼사드 (RingBuffer + dlog + MemoryDump)](/docs/specs/10_logger_facade.md) *(제안)* (branch: `feature/logger-facade`)

## Phase 2: 디자인 패턴 시각화 및 현대화 (atugcc::pattern)
- [x] [Phase 2.0: 패턴 시각화 도구 구현 (atugcc::pattern::visualizer)](/docs/specs/08_pattern_visualizer.md) (branch: `feature/pattern-visualizer`)
  - [x] 터미널 기반 객체 계층형 트리 / 상태 흐름 트레이서 (ANSI Color 지원)
  - [x] 마크다운(D2) 메시지/상태 흐름 스니펫 출력 생성기
- [ ] Phase 2.1: 생성 패턴 (Creational Patterns)
  - [ ] Factory Method / Abstract — std::expected + concept (생성 과정 추적)
  - [ ] Builder — Fluent API + C++20 Designated Initializers 연결 시각화
  - [ ] Singleton — Thread-safe Singleton & Monostate 로깅 추적
- [ ] Phase 2.2: 구조 패턴 (Structural Patterns)
  - [ ] Decorator — CRTP / concept 기반 (실행 시간 조합 시각화 아스키 트리)
  - [ ] Adapter — concept 인터페이스 매핑 및 호환성 브릿지 로깅
  - [ ] Facade — 서브시스템 캡슐화 후단 호출 컴포넌트 시퀀스 시각화
  - [ ] Proxy — Lazy initialization 및 자원 접근 제어 이벤트 트레이싱
  - [ ] Flyweight — 메모리 풀 및 공유 상태(객체 재사용) 추적 로깅
- [ ] Phase 2.3: 행동 패턴 (Behavioral Patterns)
  - [ ] State — std::variant + std::visit 상태 머신 전이(기존 상태 -> 새 상태) 흐름도 출력
  - [ ] Observer — concept 기반 이벤트 시스템 브로드캐스트 및 수신부 시퀀스 시각화
  - [ ] Command — std::move_only_function 기반 Undo/Redo 실행 스택 추적
  - [ ] Strategy — 런타임 알고리즘 객체 교체 및 호출 추적
  - [ ] Iterator — std::ranges 뷰 파이프라인(`|`) 데이터 변환 과정 시각화
  - [ ] Memento — 객체 상태 스냅샷 저장 및 구조 복원 과정 시각화
- [ ] Phase 2.4: 아키텍처 패턴 (Architectural Patterns)
  - [ ] DI (Dependency Injection) — concept 기반 컨테이너 의존성 주입 연결 트리 구조 시각화

## Phase 3: Adapter 레이어 (atugcc::adapter)
- [ ] Adapter 인터페이스 설계
- [ ] PostgreSQL (pqxx) Adapter 구현

## Phase 4: 라이브러리 샘플 / 테스트 현대화
- [ ] shape / sound 라이브러리 현대화
- [ ] GoogleTest 테스트 확장

## Phase 5: C++ Evolution 문서
- [ ] concepts vs SFINAE
- [ ] std::format vs iostream/fmt
- [ ] std::jthread vs std::thread
- [ ] std::expected vs exceptions
- [ ] std::ranges vs raw loops
- [ ] std::variant+visit vs virtual dispatch

## Phase 6: Game Engine Core (atugcc::engine)
- [ ] [어댑터 기반 엔진 아키텍처 설계 (Adapter Framework)](/docs/specs/07_game_engine_adapters.md)
- [ ] 윈도우 생성 및 메인 게임 루프 관리 (Window & Loop)
- [ ] 게임 입력 시스템 추상화 (Input Manager - Keyboard/Mouse/Gamepad)
- [ ] C++20 기반 고속 게임 수학 라이브러리 (atugcc::math - Vector, Matrix)
- [ ] 엔티티 컴포넌트 시스템 (ECS - Entity Component System) 설계
- [ ] 그래픽스 렌더링 추상화 레이어 (RHI - Vulkan/OpenGL 기반)
- [ ] 비동기 자원 관리자 (Asset Manager - Texture, Mesh, Audio)
- [ ] 충돌 처리 및 기본 물리 연산 시스템 (Physics & Collision)
- [ ] 씬 / 상태 전환 관리자 (Scene & State Manager)
- [ ] Steamworks SDK 연동 어댑터 (atugcc::adapter::steam)
