# atugcc — Project Blueprint & Design Plan

**atugcc**: 새로운 프레임워크 작성을 위한 기반 라이브러리. 최신 C++20/23 기능을 활용하여 현대적인 아키텍처를 구성합니다. 본 문서는 프로젝트의 핵심 구조와 설계 구상을 요약합니다.

---

## 1. 아키텍처 및 핵심 방향

| 항목 | 결정 |
|------|------|
| **프로젝트명** | `atugcc` |
| **C++ 표준** | C++23 타겟 / C++20 최소 호환 |
| **컴파일러/빌드** | MSVC(Windows), GCC(Linux) / CMakePresets 기반 |
| **외부 의존성** | 모두 Adapter 패턴을 통해 분리 (ex: `IDatabaseAdapter`) |

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

### Phase 3: Adapter 레이어 (`atugcc::adapter`)
- 외부 라이브러리(PostgreSQL의 `pqxx` 등)와의 강결합 방지.
- 순수 가상 인터페이스를 두고, 구체적인 어댑터 클래스는 컴파일 타임 혹은 런타임에 주입 가능하도록 설계.

### Phase 4: 라이브러리 및 테스트
- `shape`, `sound` 등의 하위 라이브러리에 `constexpr`, `[[nodiscard]]` 적극 적용.
- GoogleTest 기반의 단위 테스트 커버리지 확보.

---

> **참고**: 구현 과정에서 겪은 문제 해결 과정이나 C++ 기능의 발전(이전 방식 vs C++20/23 비교) 등에 대한 상세한 스터디 내용은 `docs/learning/` 폴더에서 관리합니다.
