# atugcc — Agent Task List

프로젝트: **atugcc** (C++20/23 기반 프레임워크 라이브러리)

---

## Phase 0: 프로젝트 기반 설정
- [x] [프로젝트 구조 재배치 및 CMake 현대화](/docs/specs/01_project_restructure.md)

## Phase 1: 코어 모듈 전환 (atugcc::core)
- [ ] [RingBuffer 모듈 C++20 전환](/docs/specs/03_ring_buffer_modernize.md)
- [ ] [TimeStamp 모듈 C++20 전환](/docs/specs/04_timestamp_modernize.md)
- [ ] [MemoryDump 플랫폼 추상화](/docs/specs/05_memory_dump_refactor.md)
- [ ] [dlog 매크로 → std::source_location 기반 함수 전환](/docs/specs/06_dlog_modernize.md)

## Phase 2: 디자인 패턴 현대화 (atugcc::pattern)
- [ ] State 패턴 — std::variant + std::visit 버전
- [ ] Observer 패턴 — concept 기반 이벤트 시스템
- [ ] Factory 패턴 — std::expected + concept 제약
- [ ] Command 패턴 — std::function / std::move_only_function
- [ ] Iterator 패턴 — std::ranges 전환
- [ ] Decorator 패턴 — CRTP / concept 기반
- [ ] DI (Dependency Injection) — concept 기반 DI 컨테이너

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
