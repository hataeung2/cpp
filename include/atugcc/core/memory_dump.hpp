#pragma once

#include <cstdint>
#include <filesystem>
#include <string>

#include "atugcc/core/error.hpp"

template <typename T>
inline void ignoreResult(T&&) noexcept {}

namespace alog {

class MemoryDump {
public:
    MemoryDump() {
        ignoreResult(ensurePrepared("log"));
    }

    ~MemoryDump() = default;

    [[nodiscard]] static atugcc::core::Result ensurePrepared(const std::filesystem::path& dir) noexcept;
    [[nodiscard]] static std::filesystem::path preparedPath() noexcept;
    [[nodiscard]] static int getDumpFd() noexcept;
    [[nodiscard]] static void* getDumpHandle() noexcept;
    [[nodiscard]] static const char* getExePath() noexcept;
    [[nodiscard]] static std::uint64_t getModuleBase() noexcept;

    [[nodiscard]] static atugcc::core::Result prepareDumpFile(const std::filesystem::path& path) noexcept;
    [[nodiscard]] static atugcc::core::Result prepareDumpFileWin(const std::wstring& path) noexcept;

    [[nodiscard]] static atugcc::core::Result dump(const std::filesystem::path& dir = "log") noexcept;

    static void writeDumpNow(const char* eventType, std::uint64_t eventCode) noexcept;
};

} // namespace alog
