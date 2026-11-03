# 레슨: 비정상 종료 뒤의 로그 복구 (`log_recovery`)

**Run을 두 번 누르세요.** 이 레슨은 실행할 때마다 로그 줄 몇 개를 화면에 내보내지 못한 채 끝나고, 다음 실행이 그 줄을 되살려 보여 줍니다.

`printf` 디버깅에서는 프로세스가 죽으면 버퍼에 있던 줄도 같이 사라집니다. `atugcc::core::Logger`는 스레드마다 버퍼에 줄을 넣고 로그 스레드가 나중에 내보내므로(비동기, [11_thread_and_log](../11_thread_and_log/README.md)), 그냥 두면 SIGKILL이나 강제 종료 직전의 줄을 잃습니다. `configureLogBuffers({.mappedDir = …})`를 켜면 그 버퍼가 **메모리 매핑 파일**에 있어서, 프로세스가 어떻게 끝나든 OS가 파일 내용을 남기고, 같은 폴더를 매핑하는 다음 실행이 아직 전달되지 않은 줄을 `recovered_<시각>_<pid>.log`로 씁니다(spec [010-10](/docs/specs/010_10_logger_mapped_buffers.md)). 해설: [lock_free_logging.md](/docs/cpp_evolution/lock_free_logging.md)(영어).

## 실행 순서
1. `configureLogBuffers({.drainInterval = 1000ms, .mappedDir = "log/map"})`: 이 폴더에 끝난 실행의 `.logmap`이 있으면 복구 파일로 바꾸고(이때 라이브러리가 stderr에 `[atugcc] recovered N undelivered lines …`를 씁니다), 이번 실행의 버퍼를 매핑합니다. Logger를 만들거나 로그를 쓰기 **전에** 불러야 합니다. 그 전에 생긴 버퍼는 매핑되지 않습니다.
2. `log/map`의 `recovered_*.log`를 보여 주고 지웁니다. 첫 실행이면 `nothing to recover (first run?)`.
3. 줄 다섯 개를 씁니다. `step 1`, `step 2` 뒤에는 `logger.flush()`로 화면에 내보내고, `step 3`–`step 5`는 flush하지 않습니다. 로그 스레드는 1초마다 버퍼를 비우므로(`drainInterval`) 이 세 줄은 아직 버퍼에만 있습니다.
4. `std::_Exit(0)`으로 끝납니다. 소멸자, flush, 종료 처리기가 하나도 돌지 않아 매핑 파일 쪽에서는 SIGKILL과 같은 상황이 됩니다. Logger 계약은 `_exit`/`_Exit`를 보장 범위 밖(not covered)으로 둡니다. 레슨은 보장이 아니라 OS가 매핑 파일을 남긴다는 사실에 기대고, 두 OS에서 확인했습니다. 종료 코드는 0이라 smoke test와 웹 실행은 성공으로 보입니다.

| 끝내는 방법 | Logger가 보는 것 | 다음 실행에서 |
|---|---|---|
| `main` 반환, `std::exit`, `std::quick_exit` | 정상 종료: 남은 줄을 모두 전달하고 매핑 파일을 지움 | 복구할 것 없음 |
| SIGKILL, 작업 관리자의 강제 종료 | 아무것도 못 함 | 전달되지 않은 줄을 복구(계약이 보장) |
| `std::_Exit` (이 레슨) | 아무것도 못 함 | 전달되지 않은 줄을 복구(계약 밖이지만 매핑 파일은 SIGKILL과 같이 남음) |
| `std::abort`, 잘못된 메모리 접근 (crash dump 켬) | crash 처리기가 dump를 씀 | dump와 함께 복구 파일도 생김("crash handler: yes") |

## 실행
- 웹 플레이그라운드: 레슨 트리에서 선택 후 Run, 그리고 한 번 더 Run. 웹은 레슨 폴더에서 실행하므로 `log/map`은 이 레슨 폴더 아래에 생깁니다(`.gitignore`의 `log/`).
- 로컬: `cmake --build --preset <preset> --target lesson_log_recovery` 후 같은 폴더에서 `bin/lessons/lesson_log_recovery`를 두 번 실행합니다. `log/map`은 실행한 폴더(현재 폴더) 아래에 생깁니다.

## 볼 것
- 첫 실행: 화면의 로그 줄은 `step 1 (flushed)`, `step 2 (flushed)` 둘뿐입니다.
- 두 번째 실행의 2단계: 복구 파일 머리에 `ended without a clean exit; crash handler: no`, 그리고 `3 undelivered lines`. 줄마다 `[delivered]`(이미 화면에 나간 줄, 맥락으로 보여 줌) 또는 `[undelivered]`(어느 sink에도 가지 못한 줄)가 붙습니다. `step 3`–`step 5`가 `[undelivered]`입니다.
- 각 복구 줄에는 호출 위치(파일과 줄 번호, [05_source_location](../05_source_location/README.md))가 그대로 있습니다.
- 실행이 끝난 뒤 `log/map`에는 이번 실행의 `.logmap` 하나만 남습니다. 복구 파일은 레슨이 읽고 지웁니다.
- 레슨은 `flush()` 뒤 100 ms를 기다려 로그 스레드가 다시 1초 대기에 들어간 다음 `step 3`–`step 5`를 씁니다. 기다림은 동기화가 아니므로, 기계가 몹시 바쁘면 드물게 그중 일부가 화면에 나가고 다음 실행의 `undelivered` 줄이 그만큼 줄 수 있습니다.

## 연습
1. 4단계의 `std::_Exit(0)`을 `std::quick_exit(0)`으로 바꾸고 두 번 실행해 보세요. 첫 실행 화면에 `step 3`–`step 5`가 나오는지, 다음 실행에서 복구할 것이 남는지 보고, 왜 그런지 위 표로 설명해 보세요.
2. 1단계에서 `.mappedDir`을 지우고 두 번 실행해 보세요. `step 3`–`step 5`는 어디에도 남지 않습니다. 매핑이 없으면 SIGKILL 직전 drain 간격 동안 쓴 줄은 잃는다는 Logger 계약의 뜻입니다(`logger.hpp` 머리 주석의 SIGKILL 항목).
3. 로컬에서: `enableCrashDump = true`로 바꾸고 `std::_Exit(0)` 대신 `std::abort()`를 부르세요. `log/crash_dump_<시각>.log`가 생기면 `py -3 tools/read_dump.py <파일>`로 읽고, 다음 실행의 복구 파일 머리(`crash handler: yes`)와 비교해 보세요. 종료 코드가 0이 아니므로 웹과 smoke test에서는 실패로 보입니다. 확인한 뒤 되돌립니다.
