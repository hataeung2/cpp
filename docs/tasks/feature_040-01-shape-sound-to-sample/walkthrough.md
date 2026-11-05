# Walkthrough: 040-01 shape / sound를 sample로

- Spec: [/docs/specs/040_01_shape_sound_to_sample.md](/docs/specs/040_01_shape_sound_to_sample.md) (사용자 지시 2026-11-05: 스펙 검토 없이 이번 세션에서 완료)
- Test record: [testrecord.md](/docs/tasks/feature_040-01-shape-sound-to-sample/testrecord.md)

## 결과
- `shape`(STATIC)와 `sound`(SHARED)는 `sample/libs/` 한 폴더에 있고, `ATUGCC_BUILD_SAMPLES`를 켤 때만 빌드된다. `include/atugcc/libs/`, `src/libs/`는 없어졌고, 설치되는 헤더에서도 빠졌다.
- 두 클래스는 `namespace sample` 안에 있다. Windows에서 `Rectangle`이 `<Windows.h>`의 GDI 함수와 부딪혀, `main.cpp`의 예시 줄을 풀면 빌드되지 않던 문제를 확인 실행에서 찾았다.
- 함수 이름은 camelCase(`getSize`, `makeNoise`).
- `libs/CMakeLists.txt`에는 라이브러리별 폴더 구조를 적은 주석만 있다. 첫 라이브러리가 `add_subdirectory(<name>)`을 더한다([lib_candidates.md](/docs/lib_candidates.md)).

## 검증
두 preset 경고 0, 전체 ctest 35/35. 예시 줄을 풀어 두 호스트에서 실행: `rectangle size: 2`, `sound volume: 10`, Linux는 `libsound.so`를 동적 링크. 문서 게이트 0/0, `naming_check.py` 0. `cpp-reviewer`는 부르지 않았다(plan.md).

## Follow-ups
- KI-046: 첫 Windows 전체 실행에서 `lesson.testing`이 한 번 시간 초과. 그 뒤 다섯 번 통과. 이 작업은 레슨 코드를 바꾸지 않았다.
- KI-044 종료.

`lead (fallback)` 단위 없음.
