# C++ Evolution & Implementation Learning

본 문서는 `atugcc` 프레임워크를 구현하며 학습한 내용과, 과거 C++ 방식에서 Modern C++(20/23) 방식으로 넘어오면서 어떻게 코드가 진화했는지 복기하기 위한 공간입니다.

---

## 1. 학습 목적
- 실제 아키텍처 구현 과정에서 발생한 이슈와 해결책 복기
- 기존 C++11/14/17 개발 관습을 C++20/23의 새로운 관용구로 리팩토링한 근거 정리
- `atugcc` 라이브러리에 적용된 패턴들의 이론적 배경 스터디

---

## 2. 주제별 상세 리뷰 문서 (예정)

구현이 진행됨에 따라 아래 주제들에 대한 상세한 학습 노트와 비교 코드가 추가될 예정입니다:

| 스터디 주제 | 비교 대상 (Before vs After) | 연관 모듈 |
|-------------|----------------------------|-----------|
| **템플릿 제약** | SFINAE (`std::enable_if`) vs C++20 **Concepts** | `atugcc::pattern`, `core` |
| **문자열 포맷팅** | `iostream` / `fmt` vs C++20 **`std::format`** | `TimeStamp`, `MemoryDump` |
| **스레드 관리** | `std::thread` vs C++20 **`std::jthread`** | 비동기 로깅 |
| **에러 핸들링** | Exceptions vs C++23 **`std::expected`** | `Factory` 패턴, 초기화 로직 |
| **순회 및 뷰** | Raw loops / Iterators vs C++20 **`std::ranges`** | `Iterator` 패턴, 데이터 조작 |
| **다형성** | Virtual Dispatch vs **`std::variant` + `std::visit`** | `State` 패턴 |

> **참고**: 실제 프로젝트의 전체적인 아키텍처 구조와 구상은 `docs/artifacts/project_blueprint.md`를 참고하세요.
