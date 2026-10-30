#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN // MACRO: Lean Windows headers
#endif
#ifndef NOMINMAX
#define NOMINMAX // MACRO: Suppress min/max macros
#endif
#include <Windows.h>

#include "crash_internal.hpp"

#include <atomic>
#include <csignal>
#include <cstddef>
#include <cstdint>
#include <cstring>

namespace {

LPTOP_LEVEL_EXCEPTION_FILTER gPreviousFilter = nullptr;
void (*gPreviousAbortHandler)(int) = SIG_DFL;
alignas(std::uint64_t) std::uint8_t gCrashContextBuffer[8 + sizeof(CONTEXT)]{};

void writeStderr(const char* data, std::size_t size) noexcept {
    if (data == nullptr || size == 0) {
        return;
    }
    HANDLE h = ::GetStdHandle(STD_ERROR_HANDLE);
    if (h == INVALID_HANDLE_VALUE || h == nullptr) {
        return;
    }
    const char* ptr = data;
    std::size_t remaining = size;
    while (remaining > 0) {
        DWORD chunk = (remaining > static_cast<std::size_t>(MAXDWORD))
                          ? MAXDWORD
                          : static_cast<DWORD>(remaining);
        DWORD written = 0;
        if (!::WriteFile(h, ptr, chunk, &written, nullptr) || written == 0) {
            break;
        }
        ptr += written;
        remaining -= written;
    }
}

LONG WINAPI filter(EXCEPTION_POINTERS* ep) noexcept {
    if (alog::detail::claimDump()) {
        constexpr char kCrashMsg[] = "program crashed!\n";
        writeStderr(kCrashMsg, sizeof(kCrashMsg) - 1);

        std::uint64_t code = 0;
        if (ep != nullptr && ep->ExceptionRecord != nullptr) {
            code = static_cast<std::uint64_t>(ep->ExceptionRecord->ExceptionCode);
        }

        std::uint64_t ip = 0;
        std::size_t ctxSize = sizeof(ip);
        if (ep != nullptr && ep->ContextRecord != nullptr) {
#if defined(_M_X64) || defined(__x86_64__)
            ip = static_cast<std::uint64_t>(ep->ContextRecord->Rip);
#elif defined(_M_ARM64) || defined(__aarch64__)
            ip = static_cast<std::uint64_t>(ep->ContextRecord->Pc);
#endif
            std::memcpy(gCrashContextBuffer + sizeof(ip), ep->ContextRecord, sizeof(CONTEXT));
            ctxSize += sizeof(CONTEXT);
        }
        std::memcpy(gCrashContextBuffer, &ip, sizeof(ip));
        alog::detail::writeDump("exception", code, gCrashContextBuffer, ctxSize);
    }

    if (gPreviousFilter != nullptr) {
        return gPreviousFilter(ep);
    }
    return EXCEPTION_CONTINUE_SEARCH;
}

void abortHandler([[maybe_unused]] int sig) noexcept {
    if (alog::detail::claimDump()) {
        alog::detail::writeDump("signal", static_cast<std::uint64_t>(SIGABRT), nullptr, 0);
    }

    if (gPreviousAbortHandler != nullptr && gPreviousAbortHandler != SIG_ERR && gPreviousAbortHandler != SIG_IGN) {
        std::signal(SIGABRT, gPreviousAbortHandler);
    } else {
        std::signal(SIGABRT, SIG_DFL);
    }
    std::raise(SIGABRT);
}

} // namespace

namespace alog::detail {

void installCrashHandlers() noexcept {
    static std::atomic<bool> installed{false};
    if (installed.exchange(true, std::memory_order_relaxed)) {
        return;
    }

    gPreviousFilter = ::SetUnhandledExceptionFilter(filter);
    gPreviousAbortHandler = std::signal(SIGABRT, abortHandler);
}

} // namespace alog::detail
