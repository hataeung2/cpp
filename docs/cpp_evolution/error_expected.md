# C++ Evolution: std::expected for Core Error Handling

## Why
The core module previously mixed exception throwing and implicit failure behavior. This evolution standardizes expected failure paths with C++23 `std::expected<T, E>`.

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
- Explicit and composable failure path (`and_then`, `transform`, `or_else`).
- No silent failures for file output operations.
- Shared error vocabulary across core modules.
