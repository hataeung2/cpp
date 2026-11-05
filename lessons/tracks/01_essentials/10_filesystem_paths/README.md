# 레슨: 파일 시스템 — `std::filesystem`의 경로, 나열, 오류 처리 (`filesystem_paths`)

로그 폴더와 crash dump 폴더를 만들고, 파일 이름을 조립하고, 디스크가 거절하면 이유를 알아내는 일을 `std::filesystem`으로 합니다. 이 레슨은 경로 합치기·나누기, 실행 폴더 아래 작업 폴더 `fs_sandbox/`를 만들어 파일 세 개 쓰기, 그 폴더 나열(재귀 포함), 예외와 `std::error_code` 두 가지 오류 처리와 라이브러리의 `core::Expected`로 감싸기, 수정 시각을 `clock_cast`로 날짜로 바꾸기를 출력하고, 끝에 작업 폴더를 지웁니다. 라이브러리의 [`memory_dump.hpp`](/include/atugcc/core/memory_dump.hpp)(`ensurePrepared`, 구현은 [`memory_dump.cpp`](/src/core/memory_dump.cpp))가 dump 폴더를 같은 방식(`create_directories`와 `error_code`, 실패는 `CoreError::FileIOFailure`)으로 준비합니다. 해설: [filesystem.md](/docs/cpp_evolution/filesystem.md).

## 예전 방식과 C++17/20
| | 플랫폼 API와 문자열 | `std::filesystem` |
|---|---|---|
| 경로 | `std::string`과 `"/"` 이어 붙이기, 구분자가 OS마다 다름 | `fs::path`와 `/` 연산자, `filename()`·`stem()`·`extension()`·`parent_path()` |
| 폴더 만들기 | `mkdir` / `CreateDirectoryA`: 한 단계씩 | `create_directories`: 없는 단계를 모두 |
| 나열 | `opendir`·`readdir` / `FindFirstFile`·`FindNextFile` | `directory_iterator`, `recursive_directory_iterator`(`depth()`) |
| 오류 | `-1`과 `errno` / `FALSE`와 `GetLastError()` | 예외(`filesystem_error`) 또는 `std::error_code&` 오버로드 |
| 수정 시각 | `stat`의 `st_mtime` / `FILETIME` | `last_write_time`과 C++20 `clock_cast<system_clock>` |

## 실행
- 웹 플레이그라운드: 레슨 트리에서 선택 후 Run(작업 폴더는 레슨 폴더 아래 `fs_sandbox/`)
- 로컬: `cmake --build --preset <preset> --target lesson_filesystem_paths` 후 `bin/lessons/lesson_filesystem_paths`, 또는 `ctest --preset <preset> -R lesson.filesystem_paths`(작업 폴더는 빌드 폴더 아래)

`fs_sandbox/`는 실행할 때 지우고 새로 만들며, 끝날 때 지웁니다. 강제로 멈춘 실행이 남긴 폴더도 다음 실행이 지웁니다. 같은 폴더에서 레슨을 동시에 두 번 돌리면(예: ctest와 웹을 같은 폴더에서) 서로의 작업 폴더를 지울 수 있습니다. `.gitignore`에 들어 있습니다.

## 볼 것
- 1단계: 경로를 `/`로 합치고 부분을 꺼냅니다. 출력은 모두 `generic_string()`(구분자 `/`)이라 두 OS가 같고, `preferred_separator` 한 줄만 Windows `\`, Linux `/`로 다릅니다.
- 2단계: 파일을 **이진 모드**로 씁니다. Windows의 텍스트 모드는 `\n`을 `\r\n`으로 바꿔 크기가 OS마다 달라집니다. 파일은 블록 안에서 닫힌 뒤 크기를 읽습니다(닫기 전에는 버퍼 때문에 0일 수 있음).
- 3단계: 나열 순서는 표준이 정하지 않으므로 모아서 정렬한 뒤 출력합니다. `recursive_directory_iterator`의 `depth()`는 시작 폴더에서 몇 단계 아래인지입니다.
- 4단계: 없는 파일의 크기를 예외 오버로드로 물으면 `filesystem_error`가 나고 `path1()`이 그 경로입니다. `error_code` 오버로드는 던지지 않고 `ec`를 채우며 `(uintmax_t)-1`을 돌려줍니다. 레슨은 `ec`를 메시지가 아니라 `std::errc::no_such_file_or_directory`와 비교합니다(메시지는 OS마다 다름. 예: Linux는 `No such file or directory`, Windows는 시스템 언어로 된 다른 문장). `fileSize`는 `error_code`를 `core::Expected`로 바꾸므로 레슨 `error_expected`의 `and_then`·`or_else`로 이어 쓸 수 있습니다.
- 5단계: `file_clock`의 기준 시점은 구현마다 다르므로 `clock_cast<system_clock>`으로 바꾼 뒤 날짜를 찍습니다(UTC 날짜, 실행한 날에 따라 다름). 끝에 `remove_all`이 지운 개수(파일 3, 폴더 2, 작업 폴더 1)를 출력하고 작업 폴더가 없음을 확인합니다.

## 연습
1. 3단계에서 정렬을 빼고 여러 번 실행해 보세요(두 OS에서 하면 더 좋습니다). 순서가 늘 같나요? 같더라도 왜 기대면 안 되나요?
2. `fs::copy(box / "logs", box / "logs_copy", fs::copy_options::recursive)`로 하위 폴더를 복사하고 3단계의 나열에 나오게 해 보세요. `remove_all`이 지운 개수는 어떻게 바뀌나요?
3. 5단계의 `ft.time_since_epoch()`를 그대로 찍어 두 호스트에서 비교해 보세요. 같은 날 만든 파일인데 숫자가 크게 다르다면, `clock_cast`가 왜 필요한지 설명해 보세요.
