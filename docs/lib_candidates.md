# 라이브러리 후보 목록

`libs/`에 만들 범용 라이브러리 후보 목록이다(KI-044, 사용자 결정 2026-11-05). atugcc는 게임 엔진, 나아가 어떤 프로그램이든 만들 수 있는 프레임워크를 목표로 하므로, 게임이 아닌 프로그램에도 필요한 라이브러리를 하나씩 더해 간다.

- 후보를 하나 고르면 `agent_todo.md` Phase 4에 `040-SS` 줄을 올리고 스펙을 쓴다. 다 만들면 **상태**를 바꾼다.
- `shape`, `sound`는 이 목록에 들지 않는다. STATIC·SHARED 빌드를 보여 주는 sample이며 `sample/libs/`에 있다(040-01).
- 상태: `후보`, `일부`(관련 코드가 다른 모듈에 있음), `작업 있음`(todo 줄이 있음), `완료`.

## 층 나누기
| 층 | 들어가는 것 | 의존 |
|---|---|---|
| `core` (`atugcc::core`) | 모든 모듈이 쓰는 바닥: 로그, 오류(`Expected`), 시간, 링 버퍼, crash dump | 표준 라이브러리와 core 안의 것만 |
| `libs` (`atugcc::<name>`) | 골라서 링크하는 범용 라이브러리. 게임 개념(창, 씬, 엔티티)은 모른다 | `core`, 다른 `libs` |
| `engine` (`atugcc::engine`) | 게임 전용 기능 (Phase 6) | `core`, `libs`. 반대 방향 의존은 금지 |

어느 층인지 헷갈리면 "게임이 아닌 프로그램(서버, 도구, 데스크톱 앱)도 이것을 쓰는가"로 정한다. 쓰면 `libs`다.

## 폴더 구조
라이브러리마다 폴더 하나를 둔다. 하나를 더해도 다른 라이브러리를 건드리지 않게 하기 위해서다.

```
libs/
  CMakeLists.txt            # add_subdirectory(<name>)만 둔다
  <name>/
    CMakeLists.txt          # 타깃 atugcc_<name>
    include/atugcc/<name>/  # 공개 헤더: #include <atugcc/<name>/...>
    src/
    tests/
```

`core`, `pattern`의 `include/atugcc/<module>/` + `src/<module>/` 구조와는 다르다. `core`는 모두가 쓰는 하나의 덩어리이고, `libs`는 따로 골라 쓰는 여러 덩어리이기 때문이다. 타깃 이름, 테스트 등록, 모듈(`.cppm`) 제공 방식은 첫 라이브러리 작업의 스펙에서 정하고, 그 뒤의 라이브러리는 그것을 따른다.

## 직접 만들기와 감싸기
후보마다 직접 만들지, vcpkg 라이브러리를 감쌀지 스펙에서 정한다. 감쌀 때는 외부 의존 규칙([impl.md](/.agent/rules/impl.md) §5)대로 교체 가능한 backend 뒤에 둔다. 아래 표의 **방식**은 지금의 제안이다.
- 직접: 만드는 과정 자체가 레슨이 되고, 표준 라이브러리만으로 충분한 것.
- 감싸기: 표준 형식(JSON, TOML)이나 플랫폼 차이 때문에 다시 만드는 비용이 큰 것.

## 후보
| # | 분야 | 후보 | 내용 | 방식 | 관련 | 상태 |
|---|---|---|---|---|---|---|
| L01 | 메모리 | allocator | arena, pool, `std::pmr::memory_resource` 기반 | 직접 | 060-05 ECS, 060-07 자원 | 후보 |
| L02 | 메모리 | slot map | 세대 번호가 있는 handle (지워진 객체를 가리키면 알아챔) | 직접 | 060-05 ECS | 후보 |
| L03 | 동시성 | thread pool → job system | 작업 큐, 의존 관계가 있는 작업 그래프, work stealing | 직접 | 레슨 `thread_and_log`(E3) | 후보 |
| L04 | 동시성 | 동시성 큐 | MPSC·MPMC 큐 | 직접 | core `RingBuffer`·`ThreadLogBuffer`(SPSC), 레슨 `lock_free_buffer`(E12) | 일부 |
| L05 | 이벤트 | signal/slot, event bus | 연결 수명(scoped connection), 지연 전달 | 직접 | 023-02 Observer | 후보 |
| L06 | 데이터 | config | JSON·TOML 설정 읽기, 형식이 틀린 곳을 `Expected`로 | 감싸기 | 030-01 backend | 후보 |
| L07 | 데이터 | 직렬화 | 바이너리 직렬화, 버전이 바뀐 데이터 읽기 | 직접 | 060-07 자원, 060-09 씬 저장 | 후보 |
| L08 | 데이터 | reflection | 멤버 순회. C++26 reflection을 컴파일러가 지원하면 그것으로, 아니면 매크로·concept | 직접 | L06, L07 | 후보 |
| L09 | 파일 | VFS | 디렉터리와 패키지 파일을 같은 경로로 읽기 | 직접 | 060-07 자원, 레슨 `filesystem_paths`(E9) | 후보 |
| L10 | 수학 | math | vector, matrix, quaternion | 직접 | 060-04 (`libs`로 옮길지 결정 필요) | 후보 |
| L11 | 실행 | plugin | 공유 라이브러리 동적 로딩, ABI 경계 | 직접 | sample `sound`(SHARED) | 후보 |
| L12 | 실행 | CLI 인자 | 인자 정의와 도움말, 오류를 `Expected`로 | 직접 | `main.cpp`의 플래그 | 후보 |
| L13 | 문자열 | 텍스트 | UTF-8 순회·검사, Windows `wchar_t` 변환 | 직접 | 레슨 `format_text`(E2) | 후보 |
| L14 | 기타 | hash, UUID | 안정적인 해시(실행마다 같은 값), UUID 만들기·읽기 | 직접 | L07 | 후보 |
| L15 | 기타 | random | seed로 다시 만들 수 있는 난수, 분포 | 직접 | 060-08 물리, 테스트 | 후보 |
| L16 | 기타 | profiler | 구간 시간을 프레임·스레드별로 모아 보기 | 직접 | 020-06 `SpanMeter`(구간 시간), 070-06 Timings | 일부 |

## 정할 것
- L10 수학: 060-04는 지금 Phase 6에 `atugcc::math`로 있다. 위 기준으로는 `libs`다. 060-01 스펙 재검토 때 정한다.
- 첫 라이브러리: 엔진 줄의 앞쪽(060-04 수학, 060-05 ECS)을 받치는 L10, L01, L02 중에서 고르는 것을 제안한다.
