#pragma once

#include <expected>
#include <string_view>

namespace atugcc::core {

enum class CoreError {
    InvalidArgument,
    FileIOFailure,
    PlatformUnsupported,
    Unexpected,
};

[[nodiscard]] inline constexpr std::string_view to_string(CoreError e) noexcept {
    switch (e) {
        case CoreError::InvalidArgument: return "InvalidArgument";
        case CoreError::FileIOFailure: return "FileIOFailure";
        case CoreError::PlatformUnsupported: return "PlatformUnsupported";
        case CoreError::Unexpected: return "Unexpected";
    }
    return "Unknown";
}

template <typename T>
using Expected = std::expected<T, CoreError>;

using Result = std::expected<void, CoreError>;

} // namespace atugcc::core
