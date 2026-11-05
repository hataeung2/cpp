# C++ Evolution: 파일과 디렉터리 (`std::filesystem`)

## Why
로그, crash dump, 복구한 로그 맵은 모두 존재하는 폴더, 여러 조각으로 만든 파일 이름, 그리고 디스크가 거부할 때의 분명한 답이 필요합니다. C++17 이전에는 그 단계 하나하나가 플랫폼 호출이었고, 경로 타입과 오류 규칙도 제각각이었습니다. `std::filesystem`(C++17)은 `path` 타입 하나, 이식 가능한 디렉터리 작업, 그리고 고를 수 있는 두 가지 오류 방식(예외 또는 `std::error_code`)을 줍니다. atugcc는 이것으로 덤프 폴더를 준비하고, 오류 코드를 자신의 `Expected` 값으로 바꿉니다.

레슨: [`filesystem_paths`](/lessons/tracks/01_essentials/10_filesystem_paths/README.md)(essentials 트랙).

## C++11/14 (Legacy): 문자열과 플랫폼 API
```cpp
std::string path = dir + "/" + name;                 // "\\" on Windows? both work, but not everywhere
#ifdef _WIN32
CreateDirectoryA(dir.c_str(), nullptr);              // one level only, BOOL + GetLastError()
WIN32_FIND_DATAA fd; HANDLE h = FindFirstFileA((dir + "\\*").c_str(), &fd);
#else
mkdir(dir.c_str(), 0755);                            // one level only, -1 + errno
DIR* d = opendir(dir.c_str()); while (dirent* e = readdir(d)) { /* ... */ } closedir(d);
#endif
```
- 경로가 그냥 문자열입니다. 잇기, 확장자나 상위 폴더 꺼내기가 모두 문자열 수술이고, 구분자도 다릅니다.
- `a/b/c`를 만들려면 반복문이 필요하고, 폴더 목록을 보려면 API 두 개와 손으로 하는 정리가 필요합니다.
- 오류는 `BOOL`/`-1`과 `GetLastError()`/`errno`로 돌아오고, 바로 읽지 않으면 잃습니다.

## C++17: `std::filesystem`
```cpp
namespace fs = std::filesystem;
fs::path p = fs::path{"logs"} / "2026" / "app.log";   // p.filename(), p.stem(), p.extension(), p.parent_path()
fs::create_directories(dir);                          // every missing level
for (const auto& entry : fs::recursive_directory_iterator(dir)) { /* entry.path(), entry.file_size() */ }
fs::remove_all(dir);                                  // returns how many entries it removed

std::uintmax_t size = fs::file_size(p);               // throws fs::filesystem_error (path1(), code())
std::error_code ec;
std::uintmax_t size2 = fs::file_size(p, ec);          // no throw: ec set, returns static_cast<std::uintmax_t>(-1)
if (ec == std::errc::no_such_file_or_directory) { /* ... */ }
```
- `path`는 네이티브 형식을 저장합니다. `generic_string()`은 늘 `/`를 쓰고, `string()`은 저장된 형식을 그대로 돌려주며, `operator/`는 `fs::path::preferred_separator`(Windows에서는 `\`)로 잇습니다.
- 모든 작업에 예외 오버로드와 `std::error_code&` 오버로드가 있습니다. 파일 시스템 오류로 예외를 던지면 안 되는 코드(crash handler의 준비, `noexcept` 함수)는 두 번째를 씁니다. 그런 오버로드 중 몇 개(`create_directories`, `remove_all`)는 아직 `noexcept`가 아니라서 `std::bad_alloc`을 던질 수 있고, 그래서 `memory_dump.cpp`는 `try`도 둡니다.
- 디렉터리 순회 순서는 **정해져 있지 않습니다**: 순서가 중요하면 정렬합니다.
- `fs::last_write_time`은 `fs::file_time_type`을 돌려주는데, 그 시계(`file_clock`)의 기준 시점은 표준이 정하지 않습니다.

## C++20: 파일 시간을 달력 시간으로
```cpp
auto ft = fs::last_write_time(p);
auto sys = std::chrono::clock_cast<std::chrono::system_clock>(ft);   // works with every standard library
std::string day = std::format("{:%F}", sys);
```
- `clock_cast`는 변환할 줄 아는 어느 두 시계 사이에서든 변환합니다(`file_clock`, `system_clock`, `utc_clock`, …). `file_clock`에는 이것이 이식 가능한 선택입니다. 표준은 라이브러리마다 `file_clock`에 `to_sys`/`from_sys`(libstdc++)나 `to_utc`/`from_utc`(MSVC) 중 하나를 주도록 허용하고, `clock_cast`는 있는 쪽을 씁니다. MSVC와 Linux 툴체인(Clang 20 + libstdc++ 14)에서 빌드됩니다(GCC 13의 libstdc++에는 `clock_cast`가 없었습니다).

## C++23 (Current, atugcc)
- [`memory_dump.hpp`](/include/atugcc/core/memory_dump.hpp) / [`memory_dump.cpp`](/src/core/memory_dump.cpp): `MemoryDump::ensurePrepared(dir)`는 `noexcept` 함수 안에서 `fs::create_directories(dir, ec)`를 부르고, 실패를 `std::unexpected(CoreError::FileIOFailure)`로 바꿉니다([`error.hpp`](/include/atugcc/core/error.hpp), [error_expected.md](/docs/cpp_evolution/error_expected.md)).
- [`log_buffer_config.hpp`](/include/atugcc/core/log_buffer_config.hpp): `configureLogBuffers({.mappedDir = …})`는 메모리 매핑 로그 폴더로 `std::filesystem::path`를 받습니다.
