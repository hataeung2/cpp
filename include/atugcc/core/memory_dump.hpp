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

    /**
     * @brief Writes a crash dump immediately to the prepared target.
     *
     * Returns immediately without effect if no target has been prepared.
     * If eventType is exactly "manual", the dump is written without claiming
     * the one-time crash dump token. For any other event type, the dump is
     * written only if claimDump() succeeds (once per process).
     * A "manual" dump is a diagnostic call: do not run it while another thread may be
     * crashing, the two dumps would share the target and could interleave (codex review
     * of 010-09 U5a). Async-signal-safe.
     *
     * @param eventType Description of the event (e.g. "manual", "crash", "terminate").
     * @param eventCode Platform- or signal-specific code associated with the event.
     */
    static void writeDumpNow(const char* eventType, std::uint64_t eventCode) noexcept;
};

} // namespace alog
