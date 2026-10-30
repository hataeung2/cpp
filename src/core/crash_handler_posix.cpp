#include "crash_internal.hpp"

#include <atomic>
#include <cerrno>
#include <csignal>
#include <cstddef>
#include <cstdint>
#include <signal.h>
#include <ucontext.h>
#include <unistd.h>

namespace {

struct SavedAction {
    int sig{0};
    struct sigaction action{};
};

constexpr int kSignals[] = {SIGSEGV, SIGBUS, SIGFPE, SIGILL, SIGABRT};
constexpr std::size_t kSignalCount = sizeof(kSignals) / sizeof(kSignals[0]);

SavedAction gSavedActions[kSignalCount] = {
    {SIGSEGV, {}},
    {SIGBUS, {}},
    {SIGFPE, {}},
    {SIGILL, {}},
    {SIGABRT, {}},
};

struct sigaction gDefaultAction{};

const struct sigaction* findSavedAction(int sig) noexcept {
    for (std::size_t i = 0; i < kSignalCount; ++i) {
        if (gSavedActions[i].sig == sig) {
            return &gSavedActions[i].action;
        }
    }
    return nullptr;
}

void writeStderr(const char* data, std::size_t size) noexcept {
    if (data == nullptr || size == 0) {
        return;
    }
    const char* ptr = data;
    std::size_t remaining = size;
    while (remaining > 0) {
        ssize_t ret = ::write(STDERR_FILENO, ptr, remaining);
        if (ret <= 0) {
            if (ret < 0 && errno == EINTR) {
                continue;
            }
            break;
        }
        ptr += ret;
        remaining -= static_cast<std::size_t>(ret);
    }
}

void writeStderrDecimal(std::uint64_t val) noexcept {
    char buf[32];
    std::size_t pos = 0;
    if (val == 0) {
        buf[pos++] = '0';
    } else {
        char temp[32];
        std::size_t tpos = 0;
        while (val > 0) {
            temp[tpos++] = static_cast<char>('0' + (val % 10));
            val /= 10;
        }
        while (tpos > 0) {
            buf[pos++] = temp[--tpos];
        }
    }
    writeStderr(buf, pos);
}

void posixCrashHandler(int sig, [[maybe_unused]] siginfo_t* info, [[maybe_unused]] void* uctx) noexcept {
    if (alog::detail::claimDump()) {
        constexpr char kCrashPrefix[] = "program crashed! signal ";
        writeStderr(kCrashPrefix, sizeof(kCrashPrefix) - 1);
        writeStderrDecimal(static_cast<std::uint64_t>(sig));
        constexpr char kNewline[] = "\n";
        writeStderr(kNewline, 1);

        std::uint64_t ip = 0;
#if defined(__x86_64__)
        if (uctx != nullptr) {
            auto* uc = static_cast<ucontext_t*>(uctx);
            ip = static_cast<std::uint64_t>(uc->uc_mcontext.gregs[REG_RIP]);
        }
#elif defined(__aarch64__)
        if (uctx != nullptr) {
            auto* uc = static_cast<ucontext_t*>(uctx);
            ip = static_cast<std::uint64_t>(uc->uc_mcontext.pc);
        }
#endif
        alog::detail::writeDump("signal", static_cast<std::uint64_t>(sig), &ip, sizeof(ip));
    }

    const struct sigaction* restoreAction = findSavedAction(sig);
    if (restoreAction == nullptr) {
        restoreAction = &gDefaultAction;
    }
    (void)::sigaction(sig, restoreAction, nullptr);
    (void)std::raise(sig);
}

} // namespace

namespace alog::detail {

void installCrashHandlers() noexcept {
    static std::atomic<bool> installed{false};
    if (installed.exchange(true, std::memory_order_relaxed)) {
        return;
    }

    gDefaultAction.sa_handler = SIG_DFL;
    sigemptyset(&gDefaultAction.sa_mask);
    gDefaultAction.sa_flags = 0;

    struct sigaction sa{};
    sa.sa_sigaction = posixCrashHandler;
    sigemptyset(&sa.sa_mask);
    sa.sa_flags = SA_SIGINFO | SA_ONSTACK;

    for (std::size_t i = 0; i < kSignalCount; ++i) {
        (void)::sigaction(kSignals[i], &sa, &gSavedActions[i].action);
        if (gSavedActions[i].action.sa_handler == SIG_IGN) {
            gSavedActions[i].action = gDefaultAction;
        }
    }
}

} // namespace alog::detail
