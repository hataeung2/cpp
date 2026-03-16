# C++ Evolution: README

이 디렉터리에는 C++ 표준별 기능 진화를 비교하는 문서가 위치합니다.

각 파일은 하나의 C++ 기능에 대해 **이전 방식 → C++20 → C++23** 변화를 side-by-side로 보여줍니다.

## 목적
- 기존 C++11/14/17 개발자가 C++20/23의 새로운 관용구를 이해할 수 있도록 돕기
- `atugcc` 라이브러리에서 실제 적용한 패턴의 근거 문서

## 파일 목록 (예정)
| 파일명 | 주제 |
|--------|------|
| `concepts_vs_sfinae.md` | Concepts vs SFINAE (enable_if) |
| `format_vs_iostream.md` | std::format vs iostream / fmt |
| `jthread_vs_thread.md` | std::jthread vs std::thread |
| `expected_vs_exceptions.md` | std::expected vs exceptions |
| `ranges_vs_loops.md` | std::ranges vs raw loops |
| `variant_visit_vs_virtual.md` | std::variant+visit vs virtual dispatch |
