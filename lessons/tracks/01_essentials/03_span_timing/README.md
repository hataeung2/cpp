# 레슨: 구간 시간 측정

같은 일을 두 방식으로 하는 코드 구간을 `tracer.timeScope("이름")`으로 15초 동안 번갈아 재고, 어느 쪽이 얼마나 빠른지 비교합니다.
- `push_back`과 `reserve + push_back`: 벡터 원소 10만 개 채우기
- `std::map::find`와 `std::unordered_map::find`: 원소 10만 개에서 1만 번 찾기

span 사용법과 비용은 [020-06 스펙](../../../../docs/specs/020_06_tracer_span_timing.md)과 [lessons/README.md](../../../README.md)의 "성능 측정 레슨 작성"에 있습니다.

## 실행
- 웹 플레이그라운드: 레슨 트리에서 선택 후 Run.
  - 이 레슨은 `profile = "long"`이라 실행 제한은 120초입니다. 빌드는 최적화 빌드(`linux-x64-playground-release`, RelWithDebInfo)로 합니다.
  - 실행 중에 **Timings** 탭이 열리고 값이 계속 갱신됩니다. 같은 구간의 시간은 에디터의 `timeScope` 줄 끝에도 `⏱ … avg ×N`으로 나옵니다.
- 로컬:
  - `cmake --build --preset <preset> --target lesson_span_timing` 후 `bin/lessons/lesson_span_timing`을 실행합니다. 끝에 `formatTimings()` 표가 출력됩니다.
  - smoke test로 돌리려면 `ctest --preset <preset> -R lesson.span_timing`(라벨 `long`)을 씁니다.

## 볼 것
- `reserve + push_back`의 mean이 `push_back`보다 작습니다. 다시 할당하고 옮기는 비용이 사라지기 때문입니다.
- `std::unordered_map::find`가 `std::map::find`보다 빠릅니다. 해시 한 번으로 찾고, 트리를 따라 내려가지 않습니다.
- p95가 mean보다 크게 튀는 구간은 할당이나 캐시 때문에 가끔 느려지는 구간입니다. 행의 ▸를 누르면 분포가 보입니다.
- 상단의 측정기를 `cpu`로 바꿔 다시 실행하면 값이 `wall`과 거의 같습니다. 이 구간들은 기다리지 않고 계산만 하기 때문입니다.

## 연습
1. `fillWithReserve`의 `reserve` 줄을 주석 처리하고(`// values.reserve(kElements);`) Run을 누르세요. Timings의 "이전 대비" 열에서 `reserve + push_back`의 변화율을 확인합니다. 줄을 지우면 아래 span들의 줄 번호가 바뀌어 다른 행이 되므로 비교되지 않습니다.
2. 이 레슨의 `lesson.toml`에서 `[run]` 아래에 `build = "debug"`를 넣고 실행해 보세요. 시간이 몇 배로 늘고, 이전 대비 열에는 "빌드 다름"이 나옵니다. Debug 시간으로 성능을 판단하면 안 되는 이유를 적어 보세요. 확인이 끝나면 그 줄은 지웁니다.
3. `lookUp` 안의 `for` 문 한 바퀴를 따로 span으로 재도록 바꿔 보세요. 같은 15초 동안 rounds가 얼마나 줄어드는지, 화면이 무엇을 보여 주는지 보고 "핫 루프 안쪽 대신 바깥 구간을 재라"는 안내의 이유를 설명해 보세요.
