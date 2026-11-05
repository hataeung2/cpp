# 레슨: 시간 다루기 — `std::chrono`의 기간, 시계, 달력, 시간대 (`chrono_time`)

로그의 시각, 구간 측정, "다음 달 같은 날", "서울 시각으로 몇 시" 같은 일을 `std::chrono` 하나로 합니다. 이 레슨은 다섯 단계로 기간(duration) 변환, `steady_clock`으로 재기, 달력 날짜와 무효 날짜 고치기, **고정된 순간**을 여러 시간대로 바꾸기(서머타임 때문에 없는 시각 포함), chrono 포맷과 그 역인 `parse`를 출력합니다. 라이브러리의 [`TimeStamp`](/include/atugcc/core/timestamp.hpp)가 같은 `zoned_time`과 `std::format`으로 로그 시각을 만듭니다. 해설: [chrono_format.md](/docs/cpp_evolution/chrono_format.md).

## 예전 방식과 C++20
| | C 시간 함수 | `std::chrono` (C++20) |
|---|---|---|
| 단위 | `time_t`(초)와 정수, 단위는 변수 이름으로만 | `std::chrono::milliseconds`처럼 타입에 단위. 손실 변환은 `duration_cast`·`round`·`floor`로 드러냄 |
| 경과 시간 | `time()`이나 `clock()`: 벽시계가 바뀌면 틀림 | `steady_clock`: 거꾸로 가지 않음 |
| 날짜 | `struct tm`, 달은 0부터, 무효 날짜를 `mktime`이 조용히 고침 | `year_month_day`와 `ok()`, `February/last` |
| 시간대 | `localtime_r` / `_localtime64_s`: 이 기계의 시간대 하나뿐, 플랫폼마다 다른 함수 | `zoned_time{"Asia/Seoul", t}`: 이름으로 아무 시간대나, 서머타임 규칙 포함 |
| 문자열 | `strftime(buf, sizeof buf, "%F %T", &tm)` | `std::format("{:%F %T}", t)`, 읽기는 `std::chrono::parse` |

예전 방식의 코드는 [chrono_format.md](/docs/cpp_evolution/chrono_format.md)에 있습니다. `std::localtime`은 MSVC에서 C4996 경고가 나고 이 저장소는 경고를 오류로 다루므로 레슨 코드에 넣지 않았습니다.

## 실행
- 웹 플레이그라운드: 레슨 트리에서 선택 후 Run
- 로컬: `cmake --build --preset <preset> --target lesson_chrono_time` 후 `bin/lessons/lesson_chrono_time`, 또는 `ctest --preset <preset> -R lesson.chrono_time`

## 볼 것
- 1단계: `1500ms`를 초로 바꾸는 방법이 셋입니다. `duration_cast`는 0 쪽으로 버리고(`1s`, `-1s`), `round`는 가장 가까운 값(`2s`, 정확히 중간이면 짝수 쪽이라 `2500ms`도 `2s`), `floor`는 아래로(`-2s`). 단위가 다른 기간을 더하면 결과는 더 작은 단위(`90min`)가 됩니다.
- 2단계: `sleep_for(20ms)`는 **적어도** 20ms를 잡니다. 반올림한 ms 값은 실행마다 다릅니다. `steady_clock`은 `is_steady`가 참이고, 벽시계인 `system_clock`은 시각 동기화로 뒤로 갈 수 있어 거짓입니다.
- 3단계: 2024년 2월 29일은 있고 2023년은 없습니다. 1월 31일에 한 달을 더하면 `2026-02-31`이 되고 `ok()`가 거짓입니다. `year/month/last`로 그 달의 마지막 날로 맞춥니다.
- 4단계: 같은 순간 `2026-11-03 09:00 UTC`가 서울 18:00(`+0900`), 뉴욕 04:00(`-0500`), 베를린 10:00(`+0100`)입니다. 고정된 순간이라 두 OS의 출력이 같습니다. 2026년 3월 8일 뉴욕은 02:00에 03:00으로 건너뛰므로 02:30은 없는 시각이고, `choose::earliest`로 03:00(`-0400`)을 고릅니다. 시간대 약어(`%Z`)는 쓰지 않았습니다: 같은 서울 시간대가 Linux(libstdc++)에서는 `KST`, Windows(MSVC)에서는 `GMT+9`로 나옵니다. 시간대 데이터가 없는 환경(일부 컨테이너)에서는 `time zone database unavailable: …`을 찍고 계속합니다.
- 5단계: `%A`는 요일, `%j`는 1월 1일부터의 날 수, `hh_mm_ss`는 기간을 시:분:초로 보여 줍니다. `parse`는 포맷의 역으로 문자열을 시각으로 읽고, 4단계의 순간과 같은 값이 됩니다. 마지막 두 줄(`current_zone`, `TimeStamp::str()`)은 **지금**과 이 기계의 시간대라서 실행마다, 기계마다 다릅니다. 웹 플레이그라운드는 WSL의 시간대를 씁니다.

## 연습
1. `std::chrono::seconds s = 1500ms;`를 더하고 빌드해 보세요. 왜 컴파일 오류인가요? `std::chrono::milliseconds m = 2s;`는 왜 되나요?
2. 4단계에 다른 도시(예: `Australia/Sydney`)를 더하고, 뉴욕의 서머타임이 끝나는 2026년 11월 1일 01:30처럼 **두 번 있는** 시각을 만들어 `ambiguous_local_time`을 잡아 보세요. `choose::earliest`와 `choose::latest`의 결과는 어떻게 다른가요?
3. 5단계의 `parse`에 없는 날짜 `"2026-02-30 09:00"`을 넣고 스트림의 `fail()`을 두 호스트에서 비교해 보세요. libstdc++는 실패로 보고 MSVC는 받아들입니다(2026-11-04 확인). 그래서 레슨은 올바른 문자열만 읽습니다. 입력을 믿을 수 없다면 읽은 값을 같은 포맷으로 다시 써서 원래 문자열과 같은지 비교해 보세요(MSVC에서 무엇이 나오는지도 확인).
