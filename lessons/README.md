# lessons — 학습·연습용 레슨

atugcc를 직접 고치고 빌드하면서 익히는 레슨 모음입니다. 같은 레슨을 **로컬 preset 빌드**와 **웹 플레이그라운드**(070-02)에서 같은 소스, 같은 CMake 타깃으로 빌드하고 실행합니다. 스펙: [070-01](/docs/specs/070_01_lesson_structure.md).

## 구조
```text
lessons/
  CMakeLists.txt              레슨 자동 발견: 타깃 lesson_<id>, 테스트 lesson.<id>
  units/<unit>/               재사용 유닛: unit.toml, README.md, <unit>.hpp
  tracks/<NN_track>/          트랙: track.toml
    <NN_lesson>/              레슨: lesson.toml, README.md, main.cpp (실행 파일 하나)
```
- **트랙**은 학습 순서입니다. `01_essentials`(core, 문법, 스레드·로그 관리)를 먼저, 그다음 `02_patterns`(상황에 맞는 패턴 적용과 변형)를 봅니다.
- **유닛**은 트랙과 무관하게 여러 레슨이 가져다 씁니다. 예: `jthread_worker`는 essentials의 `thread_and_log`와 patterns의 `device_state_machine`이 함께 씁니다.
- 라이브러리 헤더는 복사하지 않고 `lib:atugcc/...`로 참조합니다. 라이브러리를 고치면 레슨에 바로 반영됩니다.
- 순서는 폴더 이름의 숫자 접두사로 정합니다.

## 매니페스트
```toml
# lessons/tracks/02_patterns/01_device_state_machine/lesson.toml
id      = "device_state_machine"        # [a-z0-9_], 레슨끼리 유일 (유닛과는 같아도 됨)
title   = "..."
summary = "..."
sources = ["main.cpp"]                  # 첫 항목이 진입점. 반드시 한 줄로
uses    = ["unit:jthread_worker", "lib:atugcc/pattern/state.hpp"]
tags    = ["state", "tracer"]

[run]                                   # 선택. 없으면 quick
profile = "quick"                       # "quick" | "long"
timeout = 300                           # 초, long에서만 의미 (1..1800)
```
```toml
# lessons/units/jthread_worker/unit.toml
id    = "jthread_worker"
title = "..."
files = ["jthread_worker.hpp"]
uses  = ["lib:atugcc/core/logger.hpp"]   # 유닛도 다른 유닛·라이브러리를 참조할 수 있음
```
- `uses`는 웹에서 "관련 파일" 탭으로 열리는 목록입니다. 실제 컴파일 의존성은 `#include`가 정합니다.
  - 유닛: `#include "units/<unit>/<unit>.hpp"` (include 경로: `lessons/`)
  - 라이브러리: `#include "atugcc/..."` (include 경로: `include/`)
- CMake는 TOML을 읽지 못해서 `id`, `sources`, `profile`, `timeout`을 줄 단위 정규식으로 읽습니다. 이 키들은 한 줄에 쓰세요.

## 새 레슨 추가
1. 비슷한 레슨 폴더를 복사해 `tracks/<track>/<NN_name>/`을 만듭니다.
2. `lesson.toml`의 `id`, `title`, `sources`, `uses`를 고칩니다.
3. `py -3 tools/lessons.py check` (Linux: `python3`)로 확인합니다. 스키마, id 중복, 없는 파일, `uses` 대상, 유닛 순환을 검사하고, `#include`가 `uses`에 빠져 있으면 경고합니다. 이 검사는 `lint_docs.py`에도 들어 있습니다.
4. 빌드하면 CMake 파일을 고치지 않아도 `lesson_<id>`와 테스트 `lesson.<id>`가 생깁니다.

## 실행
| 무엇 | 명령 |
|---|---|
| 레슨 하나 빌드 | `py -3 .agent/scripts/build.py --preset <preset> --target lesson_<id>` |
| 실행 | `out/build/<preset>/bin/lessons/lesson_<id>` (Windows: `.exe`) |
| 모든 레슨 smoke test | `ctest --preset <preset> -L lesson` |
| 오래 걸리는 레슨 빼고 | `ctest --preset <preset> -LE long` |
| 레슨 빌드 끄기 | configure 때 `-DATUGCC_BUILD_LESSONS=OFF` |
| 레슨 인덱스(JSON) | `py -3 tools/lessons.py index` → `out/lessons/index.json` |

## 실행 프로필
- `quick`(기본): 짧은 예제입니다. smoke test 제한은 10초이고, 웹(070-02)에서도 10초로 제한합니다.
- `long`: 성능 측정처럼 오래 걸리는 레슨입니다. 제한은 `timeout`이고, ctest 라벨 `long`이 붙습니다. 웹의 장시간 실행과 구간 시간 화면은 070-06에서 다룹니다.

## 웹 플레이그라운드에서 보이는 방식
`py -3 tools/playground.py --open`(또는 VS Code 태스크 `Playground: start`)으로 띄운 페이지([web/README.md](/web/README.md))는 이 폴더를 그대로 씁니다.
- 왼쪽 트리: 트랙 순서대로 레슨(`title`), 그 아래 유닛과 "사용: …"(이 유닛을 쓰는 레슨, `uses`를 따라간 결과).
- 에디터 탭: `sources`, 그리고 `uses`를 따라간 파일(유닛 헤더, `lib:` 헤더). `lessons/` 밖 파일(`include/…`)은 🔒 읽기 전용입니다.
- README 탭: 레슨 폴더의 `README.md`. 상대 링크로 다른 README나 소스를 열 수 있습니다.
- Run: 수정한 탭을 저장소 파일에 저장한 뒤 `linux-x64-playground` preset으로 `lesson_<id>`를 빌드해 실행합니다. 출력은 실행 중에 줄 단위로 나옵니다(`stdbuf -oL`). 레슨이 `std::ios::sync_with_stdio(false)`를 쓰면 줄 단위 출력이 꺼져 끝날 때 한꺼번에 나옵니다.
- Events·Diagrams 탭: Tracer를 쓰는 레슨이면 이벤트(소스 줄로 이동)와 Mermaid 다이어그램이 나옵니다. 다이어그램은 Tracer 소멸자가 쓰므로 정상 종료한 경우에만 생깁니다.

## 레슨 작성 안내
- 레슨은 Windows(MSVC)와 Linux(GCC) preset 모두에서 경고 없이 빌드돼야 합니다. 플랫폼 전용 API(`memory_dump`, 데스크톱 콘솔 sink)는 쓰지 않습니다.
- 소스와 README는 UTF-8로 씁니다.
- Tracer를 쓰는 레슨은 환경변수 `ATUGCC_TRACE_OUT`만 설정하면 이벤트가 JSON Lines로 나옵니다([020-05](/docs/specs/020_05_tracer_event_stream.md)). 웹은 이것으로 이벤트와 다이어그램을 보여 줍니다. 레슨 코드는 고칠 필요가 없습니다.
- README에는 무엇을 보여 주는지, 실행 방법, 짧은 연습 과제 2–3개를 적습니다.

## 성능 측정 레슨 작성
코드 구간의 시간은 Tracer의 span으로 잽니다([020-06](/docs/specs/020_06_tracer_span_timing.md)).
```cpp
viz::Tracer tracer;
{
    auto span = tracer.timeScope("parse");   // 스코프가 끝날 때 기록, 위치는 이 줄
    parse(input);
}
std::cout << tracer.formatTimings();          // (위치, 라벨, 측정기)별 count, total, mean, min, max
```
- **측정기**: 기본은 `wall`(경과 시간)입니다. `ATUGCC_SPAN_METER=cpu`로 실행하거나 `tracer.setSpanMeter(viz::makeSpanMeter("cpu"))`로 바꾸면 스레드 CPU 시간을 잽니다. 둘을 비교하면 대기·I/O와 계산을 구분할 수 있습니다. Windows의 `cpu`는 스케줄러 틱(약 15.6 ms) 단위로 올라가서, 짧은 구간은 대개 0이고 틱이 걸리면 약 15.6 ms로 나옵니다. Linux는 ns 단위입니다.
- **다른 방식으로 잰 값**: `(void)tracer.recordSpan("io", duration, loc, "perf");`처럼(반환값은 `core::Result`, `[[nodiscard]]`) 측정기 이름을 붙여 넣으면 같은 표와 스트림에 따로 집계됩니다.
- **핫 루프 안쪽 대신 바깥 구간을 재세요.** span 하나에도 비용이 있습니다(아래 표): sink가 없으면 수백 ns, 이벤트 스트림을 켜면 수 µs입니다. 그보다 짧은 일을 하나씩 재면 측정 비용이 결과를 덮습니다. 루프 전체를 한 구간으로 재고 반복 횟수로 나누세요.
- **스트림 flush**: 이벤트 스트림(`ATUGCC_TRACE_OUT`)을 켜고 span을 많이 쓰면 `ATUGCC_TRACE_FLUSH_MS=100`을 함께 설정합니다. 기본(0)은 줄마다 flush합니다. 간격을 두면 프로그램이 조용해진 뒤 마지막 줄이 늦게 보일 수 있습니다(KI-016).
- **수명**: `ScopedSpan`은 Tracer보다 짧은 스코프에서만 씁니다.

span 하나의 기록 비용(`tests/pattern/span_cost_probe.cpp`, Release, 200,000회 평균, 2026-10-29 측정, 측정기 가상 호출 포함):

| 구성 | Windows (MSVC) | Linux (GCC 13, WSL2) |
|---|---|---|
| 측정기 읽기 1회, `wall` | 18 ns | 23 ns |
| 측정기 읽기 1회, `cpu` | 129 ns | 213 ns |
| span, `wall`, sink 없음 | 278 ns | 148 ns |
| span, `cpu`, sink 없음 | 495 ns | 546 ns |
| span, `wall`, JSON sink + flush 100 ms | 4.1 µs | 2.4 µs |
| span, `wall`, JSON sink, 줄마다 flush | 6.9 µs | 3.0 µs |

값은 기계마다 다릅니다. 직접 재려면 `py -3 .agent/scripts/build.py --preset <os>-x64-release --target span_cost_probe` 후 `out/build/<preset>/bin/span_cost_probe`를 실행합니다.
