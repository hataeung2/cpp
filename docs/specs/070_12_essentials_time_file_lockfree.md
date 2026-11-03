---
id: 070-12
title: essentials 3차 레슨 — 시간·파일·동시성 (chrono, filesystem, lock-free 링 버퍼)
depends_on: [070-03]
unblocks: [070-13]
approved: null
---

# Spec 070-12: essentials 3차 레슨 — 시간·파일·동시성 (chrono, filesystem, lock-free 링 버퍼)

## 0. Assumptions (please review)
| # | Decision | Rejected alternative | Why |
|---|---|---|---|
| 1 | **범위**: 070-03이 비워 둔 자리 3개에 레슨 3개를 만든다: `09_chrono_time`(E8), `10_filesystem_paths`(E9), `13_lock_free_buffer`(E12). 기존 레슨, 폴더 번호, `lessons.py`는 바꾸지 않는다 | 070-11과 한 작업으로 | 070-03 Assumption 1의 분할 그대로다 |
| 2 | 070-11과 의존이 없다. 어느 쪽이든 먼저 할 수 있고 070-13은 둘 다 끝난 뒤다. **진행 순서 자리는 사용자가 정한다** | 이 스펙이 순서를 정함 | 070-03 Assumption 16 |
| 3 | 새 레슨은 070-03의 규칙을 따른다: 유닛 없음(`main.cpp` 하나), 출력 영어, 주석 한국어 줄 + 영어 줄, README 두 판, 두 preset에서 경고 없이 빌드. `chrono_time`과 `filesystem_paths`는 `quick`, `lock_free_buffer`는 `long`(Assumption 10) | 레슨마다 유닛 | 070-03 Assumption 9·12 |
| 4 | **GCC 13.3에 있는 것과 없는 것**(2026-11-03 WSL GCC 13.3 시험 컴파일): 달력 타입, `zoned_time`, `current_zone()`, 이름으로 찾는 시간대(`"Asia/Seoul"`), chrono `std::format`은 **있다**. `std::chrono::parse`와 `std::chrono::clock_cast`는 **없다**. 없는 것은 README와 MSVC 전용 연습에만 쓰고 KI-033에 더한다(`file_clock` → `system_clock`은 GCC 13에도 있는 `file_clock::to_sys`로) | `#ifdef`로 MSVC에서만 | 레슨은 두 preset에서 같은 소스로 빌드돼야 한다. 070-11 Assumption 5와 같은 처리 |
| 5 | **E8 `chrono_time`**: 다섯 단계. (1) duration: 리터럴, `duration_cast`(버림)·`round`·`floor`, 단위 합치기, (2) 시계: `steady_clock`으로 `sleep_for(20ms)` 재기와 `system_clock`의 차이, (3) 달력: `2024y/February/29`의 `ok()`, `2023y/February/29`, `February/last`, 한 달 더하기가 `2026-02-31`(무효)을 만드는 것과 고치는 법, 요일, 두 날짜 사이 일수, (4) 시간대: **고정된 순간**(`2026-11-03 09:00 UTC`)을 `UTC`, `Asia/Seoul`, `America/New_York`, `Europe/Berlin`으로, 서머타임 시작으로 없는 현지 시각(`America/New_York` 2026-03-08 02:30)의 `nonexistent_local_time`과 `choose::earliest`, (5) `std::format`의 chrono 지정자(`%F %T`, `%A`, `%j`, `hh_mm_ss`). 마지막에 `current_zone()->name()`과 라이브러리 `TimeStamp::str()`을 한 줄씩 | 현재 시각만 출력 | 현재 시각과 기계의 시간대는 실행마다, 기계마다 다르다. 고정된 순간으로 계산하면 두 OS의 출력이 같아 비교할 수 있다(AC-3). "지금" 줄은 두 개뿐이고 README가 다르게 나온다고 적는다 |
| 6 | 예전 방식(`time_t`, `localtime_r`/`_localtime64_s`, `strftime`)은 **README에만** 쓴다([`chrono_format.md`](/docs/cpp_evolution/chrono_format.md)에 이미 있음) | 레슨 코드에 `#ifdef _WIN32`로 | 플랫폼 전용 API를 레슨 코드에 쓰지 않는다(lessons/README.md). 표준의 `std::localtime`은 MSVC에서 C4996 경고가 나고 경고는 오류다 |
| 7 | **E9 `filesystem_paths`**: 다섯 단계. (1) `path` 합치기(`/`)와 나누기(`filename`, `stem`, `extension`, `parent_path`, `replace_extension`), (2) 작업 폴더 `fs_sandbox/`를 `remove_all` 후 `create_directories`, 크기를 아는 파일 세 개 쓰기, (3) `directory_iterator`와 `recursive_directory_iterator`(`depth()`)로 나열, `file_size`, `is_directory`, (4) 오류 처리: 예외(`filesystem_error`의 `path1()`)와 `std::error_code` 오버로드, 그리고 `fileSize(path) -> core::Expected<std::uintmax_t>`(실패는 `CoreError::FileIOFailure`)로 감싸기, (5) `last_write_time`을 `file_clock::to_sys`로 바꿔 날짜 출력, 끝에 `remove_all`이 지운 개수. `uses = ["lib:atugcc/core/error.hpp", "lib:atugcc/core/memory_dump.hpp"]`(dump 폴더를 `std::filesystem`으로 준비하는 실제 코드) | 임시 폴더(`temp_directory_path`) | 웹은 레슨 폴더에서 실행한다(`runner.py`). 레슨 폴더 아래면 사용자가 무엇이 생겼는지 찾을 수 있다. `.gitignore`에 `fs_sandbox/`를 더한다 |
| 8 | 나열 순서는 표준이 정하지 않으므로 **모아서 정렬한 뒤** 출력한다. 경로는 `generic_string()`으로 출력해 두 OS가 같게 한다. 구분자가 다르다는 것은 `preferred_separator`를 찍는 한 줄로만 보인다(이 줄만 OS마다 다름) | `native()` 그대로 | 출력이 OS마다 같아야 비교와 AC가 쉽다. 차이는 한 줄로 충분히 보인다 |
| 9 | 오류 메시지(`ec.message()`, `what()`)는 OS·라이브러리마다 다르므로 찍지 않고 **`ec == std::errc::no_such_file_or_directory`** 같은 비교 결과를 찍는다. 메시지는 README의 예시로만 | 메시지 그대로 | AC가 출력 전문을 비교한다. 070-11 §4와 같은 처리 |
| 10 | **E12 `lock_free_buffer`**: 레슨 안에 작은 `SpscRing<T, N>`(슬롯 배열, 생산자만 쓰는 `tail_`과 소비자만 쓰는 `head_`를 `alignas(64)`로 떨어뜨린 `std::atomic<std::size_t>`, 2의 거듭제곱 마스크, 슬롯을 쓴 뒤 `release` 저장, 읽기 전 `acquire` 읽기)와 비교용 `MutexQueue<T>`(`std::mutex` + 고정 크기 배열)를 쓰고, **정해진 시간**(경우마다 300 ms) 동안 처리량을 잰다: (1) 1:1 mutex 큐, (2) 1:1 SPSC, (3) 1:1 SPSC인데 `head_`/`tail_`이 한 캐시 줄(false sharing), (4) 생산자 4 → mutex 큐 하나, (5) 생산자 4 → 스레드별 SPSC 4개 + 소비자 하나(010-09 Logger와 같은 구조). 결과 표(items/s)와 검증 줄(생산자마다 순번이 늘기만 함, 잃은 것 0)을 출력 | 라이브러리 `detail::ThreadLogBuffer`를 직접 씀 | `detail`은 공개 계약이 아니고 슬롯 형식이 로그 전용이다. 50줄 남짓의 버퍼가 개념을 다 보인다. 실제 구현은 `uses = ["lib:atugcc/core/detail/thread_log_buffer.hpp", "lib:atugcc/core/ring_buffer.hpp"]`로 읽게 한다 |
| 11 | `lock_free_buffer`는 **`profile = "long"`, `timeout = 120`**이다. 웹은 최적화 빌드로 실행한다 | `quick`(전체 2초 남짓이라 10초 안) | Debug(-O0) 처리량은 비교를 왜곡한다(lessons/README.md "실행 프로필"). 정해진 시간 동안 돌므로 Debug·TSan smoke test에서도 실행 시간이 거의 같다 |
| 12 | 스레드는 `std::jthread` + `stop_token`(레슨 `11_thread_and_log`), 시간은 `steady_clock`(레슨 `09_chrono_time`)으로 잰다. 바쁜 대기 루프는 `std::this_thread::yield()`를 넣는다 | 조건 변수로 깨우기 | 앞 레슨에서 배운 것만 쓴다. 코어가 적은 기계(웹 호스트)에서 생산자와 소비자가 서로를 굶기지 않게 한다. 조건 변수 동기화는 patterns 후보 P3의 주제다 |
| 13 | 처리량 **숫자는 AC가 아니다**(기계, 부하, 빌드마다 다름). AC는 검증 줄(순서, 잃은 것 0), TSan 경고 0, 표의 다섯 행이다. README는 "보통 SPSC가 mutex보다 빠르고 false sharing 행이 느리다, 아니면 왜인지 보라"로 쓴다 | 몇 배 빠름을 AC로 | 숫자 AC는 플레이키하다. 이 레슨이 가르치는 것은 정확성(메모리 순서)과 측정 방법이다 |
| 14 | 태그 3개를 더한다(§2.3): `chrono`, `filesystem`, `lock_free`. `lock_free_buffer`에 기존 `thread`, `performance`도 붙인다 | 기존 태그만 | 070-10 검색이 `zoned_time`, `directory_iterator`, `memory_order`로 새 레슨을 찾게 한다 |
| 15 | 오래 남길 해설: **E9만 새 페이지** `docs/cpp_evolution/filesystem.md`(영어, KI-001의 `filesystem_format.md` 중 filesystem 절반, 070-03이 나눈 것). E8은 기존 [`chrono_format.md`](/docs/cpp_evolution/chrono_format.md), E12는 기존 [`lock_free_logging.md`](/docs/cpp_evolution/lock_free_logging.md)에 레슨 링크를 더한다 | 세 주제 모두 새 페이지 | 이미 있는 페이지에 같은 내용을 두 번 쓰지 않는다 |
| 16 | 사실과 다른 기존 문서 둘을 고친다: (a) [`src/core/timestamp.cpp`](/src/core/timestamp.cpp)의 주석 "GCC 14+ support `current_zone()`" — GCC 13.3에서 된다(Assumption 4). (b) [`modern_ring_buffer_architecture.md`](/docs/learning/modern_ring_buffer_architecture.md)는 010-09가 없앤 `boost::lockfree::spsc_queue` 전역 큐를 지금 구조로 설명한다(KI-025). 문서를 다시 쓰지 않고 맨 위에 "옛 구조의 기록, 지금 구조는 `lock_free_logging.md`와 010-09"라는 안내를 둔다 | 그대로 두기, 학습 문서를 다시 쓰기 | 레슨이 이 문서들을 링크하므로 틀린 내용으로 이어지면 안 된다. 다시 쓰는 것은 레슨과 `lock_free_logging.md`가 이미 하는 일이다 |

## 1. Objective
essentials 트랙의 core 기능 구간(`09_` 시간, `10_` 파일)과 스레드·로그 구간의 빈자리(`13_` lock-free 버퍼)를 채운다. 시간과 파일은 로그·덤프 코드(`TimeStamp`, `MemoryDump`, `configureLogBuffers({.mappedDir})`)가 쓰는 표준 기능이고, lock-free 버퍼는 010-09 Logger의 핵심 구조를 작은 코드로 직접 재 보게 한다. 이 작업과 070-11이 끝나면 essentials 트랙 14개가 다 찬다.

## 2. Requirement Details

### 2.1 트랙 안의 자리
| 폴더 | 레슨 id | 후보 | 태그 | profile |
|---|---|---|---|---|
| `09_chrono_time` | `chrono_time` | E8 | `chrono`, `format` | quick |
| `10_filesystem_paths` | `filesystem_paths` | E9 | `filesystem`, `error` | quick |
| `13_lock_free_buffer` | `lock_free_buffer` | E12 | `lock_free`, `thread`, `performance` | long (120 s) |

다른 폴더는 옮기지 않는다. [lesson_candidates.md](/docs/tasks/lesson_candidates.md)의 essentials 표에서 세 행의 **폴더**와 **상태**(`레슨 있음`)를 바꾼다.

### 2.2 새 레슨
출력 영어, 표준 라이브러리와 `atugcc_core`만 사용, 플랫폼 전용 API 없음. README 두 판에 무엇을 보여 주는지, 예전 방식과 C++20/23 방식의 비교 표, 실행 방법, 볼 것(단계별), 연습 2–3개.

**`chrono_time`** (E8): `uses = ["lib:atugcc/core/timestamp.hpp"]`
- 단계는 Assumption 5. 고정된 순간과 날짜로 계산한 줄은 OS와 무관하게 같다.
- 시간대를 찾지 못하면(`locate_zone`이 던지는 `std::runtime_error`, 시간대 DB가 없는 컨테이너) `time zone database unavailable: <zone>`을 찍고 다음 단계로 간다(종료 코드 0).
- "지금" 줄 두 개(`current_zone()->name()`, `TimeStamp::str()`)는 실행마다 다르다고 README가 적는다. 웹 플레이그라운드는 WSL의 시간대를 쓴다.
- 2단계는 `elapsed >= 20ms: true`와 반올림한 ms 값을 찍는다(값은 다름).
- 연습: (1) `std::chrono::seconds s = 1500ms;`가 왜 컴파일 오류인지(손실 변환), (2) 다른 도시의 시간대를 더하고 서머타임 끝(겹치는 시각, `ambiguous_local_time`) 보기, (3) MSVC에서 `std::chrono::parse`로 `"2026-11-03 09:00"` 읽기(GCC 13에 없음).

**`filesystem_paths`** (E9): `uses = ["lib:atugcc/core/error.hpp", "lib:atugcc/core/memory_dump.hpp"]`
- 단계는 Assumption 7. 작업 폴더는 실행 폴더의 `fs_sandbox/`이고, 시작할 때 지우고 끝날 때 지운다. 끝에 `fs_sandbox exists: false`.
- 4단계의 `core::Expected` 감싸기는 레슨 `04_error_expected`와 같은 방식으로 `and_then`/`or_else`를 쓴다.
- 연습: (1) 3단계에서 정렬을 빼고 여러 번 실행해 순서 보기, (2) `fs::copy`와 `copy_options::recursive`로 하위 폴더 복사, (3) MSVC에서 `std::chrono::clock_cast<std::chrono::system_clock>`로 5단계를 바꾸기(GCC 13에 없음).

**`lock_free_buffer`** (E12): `uses = ["lib:atugcc/core/detail/thread_log_buffer.hpp", "lib:atugcc/core/ring_buffer.hpp"]`, `[run] profile = "long"`, `timeout = 120`
- 단계는 Assumption 10. 항목은 `{producerId, seq}`. 소비자는 생산자마다 마지막 `seq`를 기억해 늘기만 하는지 보고, 멈춘 뒤 남은 항목을 다 꺼내 `produced == consumed`를 확인한다.
- 표: `case | producers | items | items/s | verified`. `std::format` 폭 지정(레슨 `02_format_text`).
- README: 슬롯을 쓰고 `tail_`을 `release`로 올리면 소비자의 `acquire` 읽기가 슬롯 내용까지 보이게 하는 이유(happens-before), 인덱스를 계속 늘리고 마스크로 자르는 이유(가득 참과 빔 구분), `alignas(64)`의 이유, 생산자가 여럿일 때 하나의 SPSC를 함께 쓰면 안 되는 이유(KI-025의 역사), 010-09의 `ThreadLogBuffer`에서 같은 줄 찾기.
- 연습: (1) `release`/`acquire`를 `relaxed`로 바꾸고 `linux-x64-tsan` preset으로 실행해 TSan 보고 읽기, (2) 생산자가 소비자의 `head_`를 매번 읽지 않도록 캐시 사본을 두고 처리량 비교, (3) 버퍼 크기 `N`을 줄여 가득 참이 처리량에 주는 영향 보기.

### 2.3 태그 어휘 (`lessons/tags.toml`에 더함)
| 키 | ko | en | aliases |
|---|---|---|---|
| `chrono` | 시간 | Time (chrono) | `std::chrono`, `duration`, `time_point`, `steady_clock`, `system_clock`, `zoned_time`, `current_zone`, `time zone`, `시간대`, `calendar`, `달력`, `year_month_day`, `time_t`, `localtime`, `TimeStamp` |
| `filesystem` | 파일 시스템 | Filesystem | `std::filesystem`, `path`, `경로`, `directory_iterator`, `recursive_directory_iterator`, `create_directories`, `디렉터리`, `file_time_type`, `std::error_code` |
| `lock_free` | lock-free | Lock-free | `std::atomic`, `atomic`, `memory_order`, `acquire`, `release`, `SPSC`, `ring buffer`, `링 버퍼`, `RingBuffer`, `ThreadLogBuffer`, `false sharing`, `cache line`, `캐시 라인`, `원자적 연산`, `잠금 없는` |

070-10의 중복 별칭 경고를 지킨다(`span` 태그의 `timing`, `시간 측정`과 겹치지 않음).

### 2.4 Platform Specifics
- 시간대 DB: Linux는 `/usr/share/zoneinfo`(libstdc++), Windows MSVC는 OS의 ICU(Windows 10 1903+). 고정된 순간의 변환 결과는 두 DB에서 같아야 한다(2026년 규칙, AC-3). 다르면 DB 버전 차이로 보고 testrecord에 적는다.
- `filesystem_paths`의 `preferred_separator` 한 줄만 OS마다 다르다(Assumption 8).
- `lock_free_buffer`: `std::atomic<std::size_t>`가 두 플랫폼에서 lock-free임을 `static_assert(std::atomic<std::size_t>::is_always_lock_free)`로 둔다. 캐시 줄은 64바이트 상수로 쓴다(`std::hardware_destructive_interference_size`는 GCC가 헤더에서 쓰면 `-Winterference-size`를 내므로 README의 설명으로만).

## 3. C++ Standard Evolution
| Approach | Standard | Description |
|----------|----------|-------------|
| Legacy | C++11/17 | `time_t`·`localtime_r`/`_localtime64_s`·`strftime`, `opendir`/`FindFirstFile`과 문자열 경로, `std::mutex` 큐, `volatile`(오해) |
| Modern | C++17/20 | `std::filesystem`(17), chrono 달력·시간대·`std::format`(20), `std::atomic`의 `memory_order`(11)와 `std::jthread`(20) |
| Latest | C++23 | (README에서만, GCC 13에 없음) `std::chrono::parse`, `clock_cast`; `std::print` |

Reference: 새 `docs/cpp_evolution/filesystem.md`(§8), 기존 [`chrono_format.md`](/docs/cpp_evolution/chrono_format.md), [`lock_free_logging.md`](/docs/cpp_evolution/lock_free_logging.md).

## 4. Edge Cases
- [x] Thread safety / memory ordering — `lock_free_buffer`가 주제다. `SpscRing`은 생산자 하나·소비자 하나만 쓴다(5단계는 생산자마다 링 하나). 슬롯은 `release`/`acquire` 쌍으로만 넘긴다. AC-5가 TSan으로 확인한다. 다른 두 레슨은 스레드를 만들지 않는다
- [x] Resource lifetime — `jthread`가 소멸할 때 멈추고 합류한다. 소비자를 생산자보다 나중에 멈춰 남은 항목을 다 꺼낸다. `fs_sandbox`의 `ofstream`은 블록을 닫은 뒤 `file_size`를 읽는다(닫기 전 크기는 버퍼 때문에 0일 수 있음)
- [x] Platform differences — §2.4. 오류 메시지를 찍지 않는다(Assumption 9)
- [x] Template / concept — `SpscRing<T, N>`은 `requires (std::has_single_bit(N))`과 `std::is_trivially_copyable_v<T>`로 제한한다(070-11 `concepts` 레슨과 같은 모양)
- [x] ODR — 레슨마다 실행 파일 하나, 새 유닛·헤더 없음
- [x] Undefined behaviour — 인덱스는 `std::size_t`로 계속 늘린다(부호 없는 넘침은 정의됨, 300 ms 안에 넘치지 않음). false sharing 경우도 같은 원자적 연산만 쓴다(구조만 다름)
- [x] 코어가 적은 기계 — `hardware_concurrency()`가 5보다 작으면 4·5단계 행에 `(oversubscribed: N cores)`를 덧붙인다. `yield()`로 진행은 된다. 검증 줄은 그대로 맞아야 한다
- [x] TSan 속도 — TSan 빌드는 10배쯤 느리지만 정해진 시간 동안 돌므로 실행 시간이 늘지 않는다(처리량만 낮다)
- [x] 바쁜 대기 중 멈춤 요청 — 생산자는 가득 찬 링에서 `stop_requested()`를 함께 본다. 소비자가 먼저 멈추면 생산자가 영원히 기다릴 수 있으므로 멈추는 순서를 생산자 → 소비자로 고정한다
- [x] 서머타임 경계 — `zoned_time{zone, local}`은 없는 시각에 `nonexistent_local_time`을 던진다. 레슨은 잡아서 `nonexistent local time` 출력 후 `choose::earliest`로 다시 만든다. 메시지는 찍지 않는다
- [x] 시간대 DB 없음 — §2.2 `chrono_time`. 레슨은 실패하지 않는다
- [x] `fs_sandbox`가 남아 있음(앞 실행이 강제 종료) — 시작할 때 `remove_all`. 같은 폴더에서 동시에 두 번 실행하면 서로의 폴더를 지울 수 있다. README에 적고 받아들인다(ctest와 웹을 같은 레슨에 동시에 돌리는 경우뿐)
- [x] 웹 실행의 작업 폴더 — 레슨 폴더(`runner.py`). `fs_sandbox/`는 `.gitignore`에 들어간다. 트리는 매니페스트 파일만 보이므로 나타나지 않는다
- [x] `last_write_time` 해상도 — 파일 시스템마다 다르므로 5단계는 날짜(`%F`)와 `modified within the last minute: true`만 찍는다

## 5. Acceptance Criteria
| ID | Criterion | Verified by |
|---|---|---|
| AC-1 | 인덱스의 essentials 순서에 새 레슨 3개가 폴더 번호 자리(§2.1)에 들어간다: `…, chrono_time, filesystem_paths, thread_and_log, log_recovery, lock_free_buffer, span_timing`. 기존 레슨의 id와 서로의 순서는 그대로다 | `py -3 tools/lessons.py index -` 출력, testrecord |
| AC-2 | 새 레슨 3개가 `windows-x64-debug`와 `linux-x64-debug`에서 경고 없이 빌드되고 smoke test가 통과한다(`lock_free_buffer`는 라벨 `long`). 각 레슨의 출력에 §2.2의 단계가 모두 나온다 | 빌드 로그, `ctest -L lesson`, 레슨별 출력 전문을 testrecord에 |
| AC-3 | `chrono_time`: "지금" 줄 두 개와 2단계의 ms 값을 뺀 출력이 두 OS에서 같다. `filesystem_paths`: `preferred_separator` 줄을 뺀 출력이 두 OS에서 같고, 끝난 뒤 `fs_sandbox/`가 없다 | 두 OS 출력의 diff(빼는 줄 표시), `ls`, testrecord |
| AC-4 | `lock_free_buffer`: 표에 다섯 행이 있고 모든 행의 `verified`가 `ok`(순번이 늘기만 함, `produced == consumed`)다. 두 preset의 Debug와 `linux-x64-playground-release`에서 | 출력 전문, testrecord |
| AC-5 | `lock_free_buffer`가 `linux-x64-tsan`에서 TSan 보고 없이 끝난다. 연습 1처럼 `relaxed`로 바꾼 사본은 TSan이 data race를 보고한다(레슨이 가르치는 것이 실제로 보이는지 확인, 사본은 커밋하지 않음) | `ctest --preset linux-x64-tsan -R lesson.lock_free_buffer` 출력, 사본 실행의 보고 첫 줄, testrecord |
| AC-6 | 레슨 3개 모두 `README.en.md`가 있고 한국어판과 절 제목 수, 연습 과제 수, 코드 블록 수가 같다. 영어판의 링크는 영어판이 있는 README면 영어판을 가리킨다 | 070-03의 비교 스크립트, `cpp-reviewer` 번역 검토 한 번 |
| AC-7 | 새 레슨의 stdout·stderr에 한글이 없다. 새 소스에서 한글 주석 줄(또는 문단)마다 바로 다음이 같은 뜻의 영어 주석이다 | 070-03 AC-5의 두 스크립트, testrecord |
| AC-8 | `py -3 tools/lessons.py check`가 ERROR 0, WARN 0이다 | 명령 출력 |
| AC-9 | 웹 검색: `zoned_time`, `directory_iterator`, `memory_order`, `시간대`, `링 버퍼`가 각각 해당 새 레슨을 찾는다. 웹에서 `lock_free_buffer`를 Run하면 Release 빌드(`linux-x64-playground-release`)로 실행되고 표가 나온다. 영어 화면에서 새 레슨 3개의 README가 영어판으로 나온다 | 헤드리스 브라우저: 검색어 5개 결과 기록, 실행 출력, 스크린샷 2장 |
| AC-10 | 전체 suite가 두 preset에서 통과한다. `npm --prefix web/frontend test`, `tools/test_lessons.py` 통과 | 명령 출력, testrecord |
| AC-11 | §8 문서가 갱신되고 `lint_docs.py`가 exit 0이다 | 명령 출력 |

## 6. Out of Scope
- E1, E5, E6, E14(문법) — 070-11
- `std::chrono::parse`, `clock_cast`를 레슨 코드에 — GCC 14+가 플레이그라운드에 들어오면(KI-033, 툴체인은 070-13)
- 다중 생산자 lock-free 큐(MPSC/MPMC), 대기 없는 깨우기(`atomic::wait`) — 필요해지면 레슨 후보로
- 심볼릭 링크, 권한(`fs::permissions`) — Windows에서 링크 만들기에 권한이 필요하다. 필요해지면 연습으로
- 조건 변수 동기화 — patterns 후보 P3(070-04)
- Logger 처리량 한계 — KI-028

## 7. Dependencies & Backends
none. 새 의존성 없음. 레슨은 `atugcc_core`만 링크한다(기존). 시간대 DB는 OS의 것을 쓴다(§2.4).

## 8. Documentation Updates
| Document | Section | Change |
|---|---|---|
| `lessons/tracks/01_essentials/{09_chrono_time,10_filesystem_paths,13_lock_free_buffer}/README.md`, `README.en.md` | 전체 | 새로 씀 |
| [`lessons/tags.toml`](/lessons/tags.toml) | — | 태그 3개(§2.3) |
| [`.gitignore`](/.gitignore) | project related | `fs_sandbox/` |
| [`docs/tasks/lesson_candidates.md`](/docs/tasks/lesson_candidates.md) | Essentials 표 | E8, E9, E12 폴더와 `레슨 있음` |
| `docs/cpp_evolution/filesystem.md` | 새 페이지 | Legacy 플랫폼 API·문자열 경로 → `std::filesystem`, 예외와 `error_code`, 레슨 링크 |
| [`docs/cpp_evolution/chrono_format.md`](/docs/cpp_evolution/chrono_format.md) | 끝 | 레슨 링크 한 줄 |
| [`docs/cpp_evolution/lock_free_logging.md`](/docs/cpp_evolution/lock_free_logging.md) | 끝 | 레슨 링크 한 줄 |
| [`docs/learning/modern_ring_buffer_architecture.md`](/docs/learning/modern_ring_buffer_architecture.md) | 맨 위 | 옛 구조의 기록이라는 안내(Assumption 16) |
| [`src/core/timestamp.cpp`](/src/core/timestamp.cpp) | `current_zone` 주석 | GCC 13.3 사실(Assumption 16). 동작은 바꾸지 않음 |
| [`docs/known_issues.md`](/docs/known_issues.md) | KI-001, KI-033 | KI-001: `filesystem.md` 씀(남은 것은 070-04와 "문서가 맞는 것"). KI-033: `std::chrono::parse`, `clock_cast` 더함(070-11이 먼저 넓히지 않았으면 제목도 넓힘) |
| [`docs/tasks/agent_todo.md`](/docs/tasks/agent_todo.md) | Phase 7 | 070-12 줄(링크, 상태) |

## 9. Technical Constraints
- Compiler: MSVC (VS 2026) / GCC 13.3 (플레이그라운드와 `linux-x64-*` preset)
- CMake: 3.26+
- C++ Standard: C++23 (C++20 minimum). 이 레슨들이 쓰는 표준 기능은 C++20까지다

## 10. Context & References
- [070-03 스펙](/docs/specs/070_03_essentials_curriculum.md)(트랙 순서, 레슨 규칙), [070-06 스펙](/docs/specs/070_06_long_run_timings.md)(long 프로필), [레슨 후보 목록](/docs/tasks/lesson_candidates.md), [lessons/README.md](/lessons/README.md)
- [timestamp.hpp](/include/atugcc/core/timestamp.hpp), [timestamp.cpp](/src/core/timestamp.cpp), [memory_dump.hpp](/include/atugcc/core/memory_dump.hpp), [error.hpp](/include/atugcc/core/error.hpp)
- [thread_log_buffer.hpp](/include/atugcc/core/detail/thread_log_buffer.hpp), [ring_buffer.hpp](/include/atugcc/core/ring_buffer.hpp), [010-09 스펙](/docs/specs/010_09_logger_thread_buffers.md)
- [chrono_format.md](/docs/cpp_evolution/chrono_format.md), [lock_free_logging.md](/docs/cpp_evolution/lock_free_logging.md), [modern_ring_buffer_architecture.md](/docs/learning/modern_ring_buffer_architecture.md), [KI-001, KI-025, KI-033](/docs/known_issues.md)

## 11. Implementation Plan
- [ ] Step 1: `tags.toml` 태그 3개, `.gitignore`, `lessons.py check`
- [ ] Step 2: `chrono_time`(코드, 매니페스트), 두 OS 실행과 출력 diff, `timestamp.cpp` 주석, `chrono_format.md`
- [ ] Step 3: `filesystem_paths`, `docs/cpp_evolution/filesystem.md`
- [ ] Step 4: `lock_free_buffer`, Debug·Release·TSan 실행, `relaxed` 사본 TSan 확인(AC-5)
- [ ] Step 5: README 두 판 ×3, 그 밖의 §8 문서(KI-001, KI-033, lesson_candidates, `modern_ring_buffer_architecture.md`, `lock_free_logging.md`)

## 12. Verification Plan
- [ ] `py -3 tools/test_lessons.py`, `py -3 tools/lessons.py check`(ERROR 0, WARN 0)
- [ ] `py -3 .agent/scripts/build.py --preset windows-x64-debug --test`, `--preset linux-x64-debug --test` (0 warnings, 전체 suite)
- [ ] `py -3 .agent/scripts/build.py --preset linux-x64-tsan --test`의 `lesson.lock_free_buffer`(AC-5)
- [ ] `chrono_time`, `filesystem_paths` 두 OS 출력 diff(AC-3)
- [ ] 출력 한글 검사, 주석 짝 검사(AC-7)
- [ ] `npm --prefix web/frontend test`
- [ ] 브라우저(AC-9): 스크린샷을 `docs/tasks/feature_070-12-essentials-time-file-lockfree/screenshots/`에
- [ ] `py -3 .agent/scripts/lint_docs.py` exit 0
- [ ] Every AC row has its evidence in `testrecord.md`

## History / Amendments
- 2026-11-03: 초안
