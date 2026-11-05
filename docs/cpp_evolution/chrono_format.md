# C++ Evolution: 시간 다루기와 포맷팅

이 문서는 타임스탬프를 만드는 코드가 C 스타일 레거시 코드에서 Modern C++20/23으로 어떻게 바뀌었는지 보여 줍니다.

## 1. Legacy (C++11/17)
레거시 C++에서는 C 스타일의 `time_t`와 `struct tm`에 의존했고, 스레드 안전하게 쓰려면 플랫폼마다 다른 함수(`localtime_r` vs `_localtime64_s`)가 필요했습니다.

```cpp
#include <chrono>
#include <ctime>
#include <iomanip>
#include <sstream>

std::string getTimeStamp() {
    auto now = std::chrono::system_clock::now();
    auto in_time_t = std::chrono::system_clock::to_time_t(now);
    
    struct tm buf;
#ifdef _WIN32
    _localtime64_s(&buf, &in_time_t);
#else
    localtime_r(&in_time_t, &buf);
#endif

    std::ostringstream ss;
    ss << std::put_time(&buf, "%Y-%m-%d %H:%M:%S");
    return ss.str();
}
```

## 2. Modern (C++20)
C++20은 `<chrono>`에 달력과 시간대 지원을, 그리고 `<format>`을 더했습니다. 덕분에 플랫폼에 상관없고 타입 안전한 방식으로 쓸 수 있습니다.

```cpp
#include <chrono>
#include <format>

std::string getTimeStamp() {
    auto now = std::chrono::system_clock::now();
    // zoned_time automatically handles time zone database and local time
    auto zt = std::chrono::zoned_time{std::chrono::current_zone(), now};
    
    // std::format provides high-performance, type-safe string generation
    return std::format("{:%Y-%m-%d %H:%M:%S}", zt.get_local_time());
}
```

### C++20에서 좋아진 점
- **플랫폼 매크로 없음**: `std::chrono::current_zone()`이 OS 차이를 처리합니다.
- **스레드 안전**: `std::chrono` API 전체가 스레드 안전하게 설계되어 있습니다.
- **타입 안전**: `std::format`이 컴파일 시간에 타입을 검사합니다(최신 컴파일러에서).
- **밀리초 지원**: `duration_cast`나 `std::format` 지정자로 바로 쓸 수 있습니다.

## 3. Future (C++23)
C++23은 `std::print`로 출력을 한층 더 간단하게 만듭니다.

```cpp
#include <chrono>
#include <print>

void printTimeStamp() {
    auto now = std::chrono::system_clock::now();
    auto zt = std::chrono::zoned_time{std::chrono::current_zone(), now};
    
    // Direct printing without manual string conversion
    std::println("{:%Y-%m-%d %H:%M:%S}", zt.get_local_time());
}
```

레슨: [`chrono_time`](/lessons/tracks/01_essentials/09_chrono_time/README.md)(essentials 트랙)은 duration을 변환하고, `steady_clock`으로 sleep 시간을 재고, 달력 날짜를 만들고 바로잡고, 고정된 한 순간을 여러 시간대 사이에서 변환하고(일광 절약 시간의 빈 구간 포함), 시간을 포맷하고 파싱합니다.
