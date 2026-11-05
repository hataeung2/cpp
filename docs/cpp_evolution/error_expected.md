# C++ Evolution: core 오류 처리의 std::expected

## Why
core 모듈은 예전에 예외 던지기와 드러나지 않는 실패 동작이 섞여 있었습니다. 이 변화는 예상할 수 있는 실패 경로를 C++23 `std::expected<T, E>`로 통일합니다.

## C++17 (Legacy)
```cpp
RingBuffer makeRingBuffer(std::size_t capacity) {
  if (capacity == 0) {
    throw std::invalid_argument("capacity must be positive");
  }
  return RingBuffer{};
}

void dump(const std::filesystem::path& dir) {
  std::ofstream out(dir / "dump.log");
  if (!out.is_open()) {
    return; // silent failure
  }
  out << DbgBuf::dump();
}
```

## C++20 (Transitional)
```cpp
enum class CoreError { InvalidArgument, FileIOFailure };

std::optional<RingBuffer> makeRingBuffer(std::size_t capacity) {
  if (capacity == 0) {
    return std::nullopt;
  }
  return RingBuffer{};
}
```

## C++23 (Current)
```cpp
enum class CoreError {
  InvalidArgument,
  FileIOFailure,
  PlatformUnsupported,
  Unexpected,
};

template <typename T>
using Expected = std::expected<T, CoreError>;

using Result = std::expected<void, CoreError>;

Expected<RingBuffer<>> makeRingBuffer(std::size_t capacity);
Result dump(const std::filesystem::path& dir = "log");
```

## Benefits
- 실패 경로가 드러나고 조합할 수 있습니다(`and_then`, `transform`, `or_else`).
- 파일 출력 작업이 조용히 실패하지 않습니다.
- core 모듈 전체가 같은 오류 어휘를 씁니다.
- 레슨: [`error_expected`](/lessons/tracks/01_essentials/04_error_expected/README.md)(essentials 트랙)는 같은 파서의 예외 버전과 `std::expected` 버전을 비교하고, `and_then`, `transform`, `or_else`로 단계를 잇습니다.
