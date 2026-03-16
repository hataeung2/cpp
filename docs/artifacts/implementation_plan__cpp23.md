# atugcc — C++20/23 프레임워크 기반 라이브러리 재구성 계획

**atugcc**: 새로운 프레임워크 작성을 위한 기반 라이브러리. 기존 C++20 샘플 프로젝트를 현대화합니다.

---

## 핵심 방향 (사용자 요구사항 반영)

| 항목 | 결정 |
|------|------|
| **프로젝트명** | `atugcc` |
| **C++ 표준** | C++23 타겟 / C++20 최소 호환 |
| **Windows 컴파일러** | MSVC — Visual Studio 2026 |
| **Linux 컴파일러** | GCC (latest stable) |
| **빌드 시스템** | CMake (IDE 아님, 컴파일러 기반) |
| **외부 의존성** | 모두 Adapter 패턴 (갈아 끼울 수 있는 구조) |
| **표준 진화 문서** | `docs/cpp_evolution/` — 이전 방식 vs C++20 vs C++23 비교 |
| **구현 순서** | `.agent` 규칙 → 단계별 (Phase 0~5) |

---

## 완료: .agent 규칙/워크플로우 업데이트

| 파일 | 변경 내용 |
|------|----------|
| [impl.md](/.agent/rules/impl.md) | TypeScript/Python → **C++20/23** 코딩 규칙, 네이밍, 어댑터 패턴, `using namespace std` 금지 등 |
| [spec.md](/.agent/rules/spec.md) | Webapp spec → **C++ 모듈/클래스** 스펙, C++ 표준 진화 섹션 추가 |
| [test.md](/.agent/rules/test.md) | pytest/npm → **GoogleTest/CMake** 빌드 검증, MSVC/GCC 호환성 체크 |
| [start-develop-one-task.md](/.agent/workflows/start-develop-one-task.md) | FastAPI/React → **include → src → tests → sample** 순서의 C++ 워크플로우 |

---

## 생성: docs 구조

```
docs/
├── tasks/
│   └── agent_todo.md          ← 전체 작업 목록 (Phase 0~5)
├── specs/
│   └── 00_template.md         ← C++ 스펙 작성 템플릿
└── cpp_evolution/
    └── README.md              ← C++ 표준별 진화 문서 인덱스
```

---

## 구현 로드맵 (Phase별)

### Phase 0: 프로젝트 기반 설정
- 디렉터리 재배치: `includes/` → `include/atugcc/`, 구현 파일 → `src/`
- CMake 현대화: `target_*` 함수 사용, pqxx optional, `CMAKE_CXX_STANDARD 23`
- `CMakePresets.json`: MSVC 2026 + GCC 프리셋

### Phase 1: 코어 모듈 (atugcc::core)
- `RingBuffer` — `std::scoped_lock`, `concept` 제약
- `TimeStamp` — `std::chrono::format` (C++20), `std::format` 통일
- `MemoryDump` — 헤더/구현 분리, 플랫폼 추상화 레이어
- `dlog` — 매크로 → `std::source_location` 기반 함수

### Phase 2: 디자인 패턴 현대화 (atugcc::pattern)
- State → `std::variant` + `std::visit`
- Observer → `concept` 기반
- Factory → `std::expected` + `concept`
- Command → `std::function` / `std::move_only_function`
- Iterator → `std::ranges`
- 모든 패턴에 **이전 방식 → C++20/23** 진화 문서 작성

### Phase 3: Adapter 레이어 (atugcc::adapter)
- 순수 가상 인터페이스 → 구체 어댑터 분리
- pqxx를 `IDatabaseAdapter` 뒤에 숨김
- 어댑터 교체 시 리빌드만으로 전환 가능

### Phase 4: 라이브러리/테스트 현대화
- shape/sound — `constexpr`, `[[nodiscard]]`, `GenerateExportHeader`
- GoogleTest 테스트 확장 (각 모듈별)

### Phase 5: C++ Evolution 문서
- 6개 주요 기능의 **before vs after** 문서:
  - concepts vs SFINAE
  - `std::format` vs iostream/fmt  
  - `std::jthread` vs `std::thread`
  - `std::expected` vs exceptions
  - `std::ranges` vs raw loops
  - `std::variant`+`visit` vs virtual dispatch

---

## Verification Plan

### 빌드 검증 (각 Phase 완료 시)
```powershell
# 옵션 1: VS Code CMake Tools 활용
# - 하단 상태 바에서 컴파일러 (MSVC/GCC) 선택
# - 빌드 단추 (또는 F7) 클릭
# - 테스트 탭에서 CTest 실행

# 옵션 2: 터미널 수동 빌드 (Ninja 제네레이터 권장)
cmake -S . -B build -G Ninja
cmake --build build --config Debug
cd build && ctest -C Debug --output-on-failure
```

### 테스트
- GoogleTest: 각 모듈별 `test_*.cpp`
- Zero warnings: `/W3` (MSVC) / `-Wall` (GCC)

### 워크플로우 실행
```
/start-develop-one-task
```
→ `agent_todo.md` 에서 최상위 미완료 작업을 자동 선택하여 실행
