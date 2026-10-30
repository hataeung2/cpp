# atugcc — Project Blueprint & Design Plan

**atugcc**: 새로운 프레임워크 작성을 위한 기반 라이브러리. 최신 C++20/23 기능을 활용하여 현대적인 아키텍처를 구성합니다. 본 문서는 프로젝트의 핵심 구조와 설계 구상을 요약합니다.

---

## 1. 아키텍처 및 핵심 방향

| 항목 | 결정 |
|------|------|
| **프로젝트명** | `atugcc` |
| **C++ 표준** | C++23 타겟 / C++20 최소 호환 |
| **컴파일러/빌드** | MSVC(Windows), GCC(Linux) / CMakePresets 기반 |
| **외부 의존성** | 모두 교체 가능한 backend(pluggable backend) 뒤에 분리 (ex: `atugcc::backend`의 DB 인터페이스). "adapter"는 GoF Adapter 패턴에만 쓴다 |
| **최종 목표** | 게임 엔진 기능까지 구현하고, 라이브러리의 모든 기능을 웹 플레이그라운드에서 레슨으로 실습할 수 있게 한다 |

---

## 2. 모듈별 설계 구상

### Phase 1: 코어 모듈 (`atugcc::core`)
- 성능과 스레드 안전성을 고려한 기본 유틸리티.
- **RingBuffer**: 락프리 큐(`boost::lockfree::spsc_queue`) 및 `thread_local`을 활용한 고성능 로깅 기반.
- **TimeStamp/MemoryDump**: `std::format`을 활용한 일관된 포맷팅.
- **dlog**: `std::source_location` 기반으로 매크로를 대체.

### Phase 2: 디자인 패턴 현대화 (`atugcc::pattern`)
- 고전적 GoF 패턴을 Modern C++ 패러다임으로 재해석.
  - State → `std::variant` + `std::visit`
  - Observer → C++20 `concept` 제약 기반
  - Factory → `std::expected` (에러 핸들링 유연성)
  - Command → `std::move_only_function`
  - Iterator → `std::ranges`

### Phase 3: Pluggable Backend 레이어 (`atugcc::backend`)
- 외부 라이브러리(PostgreSQL의 `pqxx` 등)와의 강결합 방지.
- concept 또는 순수 가상 인터페이스를 두고, 구체적인 backend는 컴파일 타임 혹은 런타임에 주입 가능하도록 설계.

### Phase 4: 라이브러리 샘플 / 시나리오 테스트
- `shape`, `sound` 등의 하위 라이브러리를 현재 시점의 최신 C++로 현대화.
- GoogleTest 단위 테스트에 더해, 시나리오를 추가하고 CTest로 골라 실행하는 시나리오 테스트.

### Phase 6: 게임 엔진 코어 (`atugcc::engine`)
- 창·루프, 입력, 수학, ECS, 렌더링(RHI), 자원, 물리, 씬 관리. 창·렌더러·ECS 같은 외부 라이브러리는 Phase 3과 같은 backend 원칙으로 감싼다.
- 각 기능을 플레이그라운드 레슨으로도 실습할 수 있게 만든다.

### Phase 7: 웹 플레이그라운드 (로컬 전용)
- 레슨을 편집·빌드·실행하고, Tracer 이벤트·다이어그램·구간 시간을 페이지에서 본다.
- 트랙 순서: essentials(어느 시스템에나 필요한 것) → patterns(상황에 맞게 적용하기). 레슨 후보는 `docs/tasks/lesson_candidates.md`.

---

> **참고**: 구현 과정에서 겪은 문제 해결 과정이나 C++ 기능의 발전(이전 방식 vs C++20/23 비교) 등에 대한 상세한 스터디 내용은 `docs/learning/` 폴더에서 관리합니다.
