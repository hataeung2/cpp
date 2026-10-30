/**
 * @file thread_crash_prep.cpp
 * @brief Platform-specific crash preparation and environment configuration reading.
 */

#include "atugcc/core/detail/log_registry.hpp"

#include <charconv>
#include <cstdint>
#include <cstdlib>
#include <cstring>

#if defined(__linux__)
#include <signal.h>
#elif defined(_WIN32)
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#endif

namespace atugcc::core::detail {

void prepareThreadForCrash(void*& altStack) noexcept {
#if defined(__linux__)
    constexpr std::size_t kAltStackSize = 65536;
    if (altStack == nullptr) {
        altStack = std::malloc(kAltStackSize);
    }
    if (altStack != nullptr) {
        stack_t ss{};
        ss.ss_sp = altStack;
        ss.ss_size = kAltStackSize;
        ss.ss_flags = 0;
        sigaltstack(&ss, nullptr);
    }
#elif defined(_WIN32)
    (void)altStack;
    ULONG size = 65536;
    SetThreadStackGuarantee(&size);
#else
    (void)altStack;
#endif
}

std::uint32_t readEnvSlots() noexcept {
#if defined(_WIN32)
    char* buf = nullptr;
    std::size_t len = 0;
    if (_dupenv_s(&buf, &len, "ATUGCC_LOG_SLOTS") != 0 || buf == nullptr) {
        return 0;
    }
    const char* str = buf;
#else
    const char* str = std::getenv("ATUGCC_LOG_SLOTS");
    if (str == nullptr) {
        return 0;
    }
#endif

    const char* p = str;
    while (*p == ' ' || *p == '\t') {
        ++p;
    }
    if (*p == '\0') {
#if defined(_WIN32)
        std::free(buf);
#endif
        return 0;
    }

    std::uint32_t parsed = 0;
    const std::size_t remainingLen = std::strlen(p);
    auto [ptr, ec] = std::from_chars(p, p + remainingLen, parsed);

    bool ok = (ec == std::errc{});
    if (ok) {
        while (*ptr == ' ' || *ptr == '\t' || *ptr == '\r' || *ptr == '\n') {
            ++ptr;
        }
        if (*ptr != '\0') {
            ok = false;
        }
    }

#if defined(_WIN32)
    std::free(buf);
#endif

    if (ok && parsed >= kMinSlots && parsed <= kMaxSlots && (parsed & (parsed - 1)) == 0) {
        return parsed;
    }
    return 0;
}

} // namespace atugcc::core::detail
