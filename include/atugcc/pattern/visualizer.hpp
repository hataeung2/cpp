/**
 * @file visualizer.hpp
 * @brief atugcc::pattern::viz — 디자인 패턴 런타임 트레이서
 *
 * 이 헤더 하나로 패턴 실행 흐름을 기록하고, 여러 형식의 문자열로
 * 변환(터미널 ASCII / PlantUML, Mermaid, D2)할 수 있다.
 *
 * 출력 책임은 호출자에게 있다:
 *   std::cout << tracer.format_terminal();
 *   atugcc::core::Logger::global().log("{}", tracer.format_diagram());
 *
 * ==========================================================================
 * 학습 포인트 (C++20/23)
 * --------------------------------------------------------------------------
 * [1] Concept  — EventSink concept: Tracer 내부 저장 방식을 추상화할 때 사용
 * [2] std::expected — record_* API 는 Result 반환(버퍼 오버플로 등 실패 표현)
 * [3] std::string_view — 입력은 항상 string_view, 내부 저장은 std::string
 * [4] std::mutex + std::shared_mutex — record(write) vs format(read) 분리 락
 * [5] std::source_location — EventMeta 에 자동 주입
 * [6] Designated Initializers (C++20) — EventMeta 구조체 초기화 시 활용
 * ==========================================================================
 */
#pragma once

#include <algorithm>
#include <array>
#include <atomic>
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <deque>
#include <format>
#include <memory>
#include <mutex>
#include <ostream>
#include <shared_mutex>
#include <source_location>
#include <string>
#include <string_view>
#include <vector>

#ifdef _WIN32
#  ifndef WIN32_LEAN_AND_MEAN
#    define WIN32_LEAN_AND_MEAN
#  endif
#  include <windows.h>
#  include <io.h>
#  include <fcntl.h>
#else
#  include <unistd.h>
#endif

#include "atugcc/core/error.hpp"

namespace atugcc::pattern::viz {

enum class DiagramBackend {
    PlantUML,
    Mermaid,
    D2,
};

// ============================================================================
// 이벤트 메타데이터
// C++20 Designated Initializer 로 초기화:
//   EventMeta meta{ .location = std::source_location::current() };
// ============================================================================
struct EventMeta {
    std::source_location location;
    std::chrono::system_clock::time_point timestamp{ std::chrono::system_clock::now() };
};

// ============================================================================
// 세 가지 이벤트 타입
// ============================================================================

/// 시퀀스 메시지: A가 B에게 어떤 요청을 보냈는가
struct Message {
    std::string from;       ///< 송신자 (ex. "Subject", "Invoker")
    std::string to;         ///< 수신자 (ex. "Observer1", "Receiver")
    std::string action;     ///< 메시지/행위 (ex. "notify()", "execute()")
    EventMeta   meta;
};

/// 상태 전이: 어떤 이벤트로 상태가 바뀌었는가
struct Transition {
    std::string old_state;  ///< 이전 상태 (ex. "LOCKED")
    std::string new_state;  ///< 다음 상태 (ex. "UNLOCKED")
    std::string trigger;    ///< 전이 원인 (ex. "coin_inserted")
    EventMeta   meta;
};

/// 구조 노드: 객체 계층 트리 (Decorator, Composite 등)
struct Node {
    std::string parent;         ///< 상위 컴포넌트
    std::string child;          ///< 하위 컴포넌트
    std::string relation_type;  ///< 관계 종류 (ex. "wraps", "contains", "delegates")
    EventMeta   meta;
};

namespace detail {

struct LiveTerminalFormatter {
    [[nodiscard]] static std::string formatMessage(const Message& message);
    [[nodiscard]] static std::string formatTransition(const Transition& transition);
    [[nodiscard]] static std::string formatNode(const Node& node);
};

} // namespace detail

// ============================================================================
// EventSink Concept
// --------------------------------------------------------------------------
// [학습] Concept 는 함수 호환성을 컴파일 타임에 검사한다.
// Tracer 가 기록한 이벤트를 외부 싱크(Logger, 파일, 테스트 mock 등)로
// 흘려보낼 때 이 concept 를 활용한다.
//
// T 가 EventSink<Message> 를 만족하려면:
//   void T::on_event(const Message&) 가 존재해야 한다.
// ============================================================================
template <typename T, typename Event>
concept EventSink = requires(T& sink, const Event& e) {
    { sink.on_event(e) } -> std::same_as<void>;
};

class TraceOutputSink {
public:
    virtual ~TraceOutputSink() = default;

    virtual void setEnabled(bool enabled) noexcept = 0;
    [[nodiscard]] virtual bool isEnabled() const noexcept = 0;
    virtual void emit(std::string_view text) = 0;
};

class ConsoleTraceSink final : public TraceOutputSink {
public:
    explicit ConsoleTraceSink(std::ostream& stream, bool auto_flush = false) noexcept
        : stream_(&stream)
        , auto_flush_(auto_flush)
    {}

    void setEnabled(bool enabled) noexcept override {
        enabled_.store(enabled, std::memory_order_relaxed);
    }

    [[nodiscard]] bool isEnabled() const noexcept override {
        return enabled_.load(std::memory_order_relaxed);
    }

    void setAutoFlush(bool auto_flush) noexcept {
        auto_flush_ = auto_flush;
    }

    [[nodiscard]] bool isAutoFlush() const noexcept {
        return auto_flush_;
    }

    void emit(std::string_view text) override {
        if (!isEnabled() || stream_ == nullptr || text.empty()) {
            return;
        }

        std::lock_guard lock(mutex_);
        (*stream_) << text;
        if (auto_flush_) {
            stream_->flush();
        }
    }

private:
    std::ostream*      stream_;
    std::atomic_bool   enabled_{ true };
    bool               auto_flush_{ false };
    mutable std::mutex mutex_;
};

enum class DesktopConsoleWindowMode {
    KeepOpen,
    AutoClose,
};

class DesktopConsoleTraceSink final : public TraceOutputSink {
public:
    [[nodiscard]] static std::shared_ptr<DesktopConsoleTraceSink> create(
        std::string_view title = "atugcc tracer",
        bool auto_flush = true,
        DesktopConsoleWindowMode window_mode = DesktopConsoleWindowMode::KeepOpen)
    {
        auto sink = std::shared_ptr<DesktopConsoleTraceSink>(new DesktopConsoleTraceSink(auto_flush, window_mode));
        if (!sink->openDesktopConsole(title)) {
            return {};
        }
        return sink;
    }

    ~DesktopConsoleTraceSink() override {
        closeDesktopConsole();
    }

    void setEnabled(bool enabled) noexcept override {
        enabled_.store(enabled, std::memory_order_relaxed);
    }

    [[nodiscard]] bool isEnabled() const noexcept override {
        return enabled_.load(std::memory_order_relaxed);
    }

    void setAutoFlush(bool auto_flush) noexcept {
        auto_flush_ = auto_flush;
    }

    [[nodiscard]] bool isAutoFlush() const noexcept {
        return auto_flush_;
    }

    [[nodiscard]] bool isOpen() const noexcept {
        return file_ != nullptr;
    }

    [[nodiscard]] bool isWindowAttached() const noexcept {
        return window_attached_;
    }

    [[nodiscard]] const std::string& logPath() const noexcept {
        return log_path_;
    }

    [[nodiscard]] DesktopConsoleWindowMode windowMode() const noexcept {
        return window_mode_;
    }

    void emit(std::string_view text) override {
        if (!isEnabled() || text.empty()) {
            return;
        }

        std::lock_guard lock(mutex_);

        if (file_ == nullptr) {
            return;
        }
        (void)std::fwrite(text.data(), sizeof(char), text.size(), file_);
        if (auto_flush_) {
            std::fflush(file_);
        }
    }

private:
    explicit DesktopConsoleTraceSink(bool auto_flush, DesktopConsoleWindowMode window_mode) noexcept
        : auto_flush_(auto_flush)
        , window_mode_(window_mode)
    {}

    [[nodiscard]] static unsigned long processId() noexcept {
#ifdef _WIN32
        return static_cast<unsigned long>(GetCurrentProcessId());
#else
        return static_cast<unsigned long>(::getpid());
#endif
    }

    [[nodiscard]] bool openDesktopConsole(std::string_view title) {
        const auto timestamp = std::chrono::duration_cast<std::chrono::milliseconds>(
            std::chrono::system_clock::now().time_since_epoch()).count();

#ifdef _WIN32
        auto escaped_title = std::string(title);
        std::ranges::replace(escaped_title, '"', '_');
        const auto full_title = std::format("{} [pid:{}]", escaped_title, processId());

        char temp_dir[MAX_PATH] = { 0 };
        if (GetTempPathA(MAX_PATH, temp_dir) == 0) {
            return false;
        }

        log_path_ = std::format("{}atugcc_tracer_{}_{}.log",
            temp_dir,
            processId(),
            timestamp);

        // Open via Win32 CreateFile so we can allow other processes to
        // read the log while we write. Then wrap the handle into a
        // CRT `FILE*` with `_open_osfhandle` + `_fdopen` so existing
        // `fwrite`/`fflush` usage continues to work.
        {
            const DWORD shareMode = FILE_SHARE_READ | FILE_SHARE_WRITE;
            const DWORD createFlags = FILE_ATTRIBUTE_NORMAL;
            HANDLE h = CreateFileA(log_path_.c_str(), GENERIC_WRITE, shareMode, nullptr, CREATE_ALWAYS, createFlags, nullptr);
            if (h == INVALID_HANDLE_VALUE) {
                return false;
            }
            int fd = _open_osfhandle(reinterpret_cast<intptr_t>(h), _O_TEXT);
            if (fd == -1) {
                CloseHandle(h);
                return false;
            }
            file_ = _fdopen(fd, "w");
            if (file_ == nullptr) {
                _close(fd); // closes underlying handle
                return false;
            }
            // Optional buffering
            (void)setvbuf(file_, nullptr, _IOFBF, 4096);
        }

        auto escaped_path = log_path_;
        std::string::size_type pos = 0;
        while ((pos = escaped_path.find('\'', pos)) != std::string::npos) {
            escaped_path.replace(pos, 1, "''");
            pos += 2;
        }

        const auto ps_flags = (window_mode_ == DesktopConsoleWindowMode::KeepOpen)
            ? std::string("-NoProfile -NoExit")
            : std::string("-NoProfile");

        const auto command = std::format(
            "cmd.exe /c start \"{}\" powershell {} -Command \"[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new($false); Get-Content -Path '{}' -Encoding UTF8 -Wait\"",
            full_title,
            ps_flags,
            escaped_path);

        if (std::system(command.c_str()) == 0) {
            window_attached_ = true;
            return true;
        }

        // If launching a new window fails, keep file-only mode so the caller
        // can inspect the trace log path.
        window_attached_ = false;
        return true;
#else
        auto escaped_title = std::string(title);
        std::ranges::replace(escaped_title, '\'', '_');
        const auto full_title = std::format("{} [pid:{}]", escaped_title, processId());

        log_path_ = std::format("/tmp/atugcc_tracer_{}_{}.log", static_cast<long long>(::getpid()), timestamp);

        file_ = std::fopen(log_path_.c_str(), "w");
        if (file_ == nullptr) {
            return false;
        }

        const auto escaped_path = std::string(log_path_);
        const auto tail_base = std::format("tail -f '{}' --pid={}", escaped_path, processId());
        const auto tail_command = (window_mode_ == DesktopConsoleWindowMode::KeepOpen)
            ? std::format("{}; exec sh", tail_base)
            : tail_base;

        const auto commands = std::array<std::string, 4>{
            std::format("gnome-terminal --title='{}' -- sh -c \"{}\" >/dev/null 2>&1 &", full_title, tail_command),
            std::format("konsole --new-tab -p tabtitle='{}' -e sh -c \"{}\" >/dev/null 2>&1 &", full_title, tail_command),
            std::format("xfce4-terminal --title='{}' -x sh -c \"{}\" >/dev/null 2>&1 &", full_title, tail_command),
            std::format("x-terminal-emulator -T '{}' -e sh -c \"{}\" >/dev/null 2>&1 &", full_title, tail_command),
        };

        for (const auto& command : commands) {
            if (std::system(command.c_str()) == 0) {
                window_attached_ = true;
                return true;
            }
        }

        // If launching a new window fails, keep file-only mode so the caller
        // can inspect the trace log path.
        window_attached_ = false;
        return true;
#endif
    }

    void closeDesktopConsole() noexcept {
        if (file_ != nullptr) {
            std::fclose(file_);
            file_ = nullptr;
        }
        // Keep the log file on disk; caller can inspect `log_path_`.
    }

    std::atomic_bool   enabled_{ true };
    bool               auto_flush_{ true };
    DesktopConsoleWindowMode window_mode_{ DesktopConsoleWindowMode::KeepOpen };
    bool               window_attached_{ false };
    mutable std::mutex mutex_;

    std::FILE*  file_{ nullptr };
    std::string log_path_;
};

// ============================================================================
// Tracer
// --------------------------------------------------------------------------
// - record_*(…) : 이벤트를 내부 버퍼에 저장 (write → unique_lock)
// - format_terminal() : ANSI/ASCII 문자열 반환  (read → shared_lock)
// - format_diagram()  : 선택한 백엔드(기본 PlantUML) 스니펫 반환
// - format_plantuml() : PlantUML 스니펫 반환 (thin wrapper)
// - format_mermaid()  : Mermaid 스니펫 반환 (thin wrapper)
// - format_d2()       : D2 스니펫 반환 (thin wrapper)
// - snapshot_*()      : 테스트/검사용 복사본 반환
// - get_global_tracer(): 프로세스 전역 싱글톤
//
// [학습] std::shared_mutex:
//   여러 스레드가 동시에 format_(read) 를 호출할 수 있도록 공유 락을 허용.
//   record_(write) 는 단독 점유 락(unique_lock) 사용.
// ============================================================================
class Tracer {
public:
    static constexpr std::size_t kDefaultCapacity = 1024;

    explicit Tracer(std::size_t capacity = kDefaultCapacity)
        : capacity_(capacity) {}

    void setOutputSink(std::shared_ptr<TraceOutputSink> sink) {
        std::unique_lock lock(mutex_);
        output_sink_ = std::move(sink);
    }

    [[nodiscard]] std::shared_ptr<TraceOutputSink> outputSink() const {
        std::shared_lock lock(mutex_);
        return output_sink_;
    }

    void setLiveTerminalOutputEnabled(bool enabled) {
        std::unique_lock lock(mutex_);
        live_terminal_output_enabled_ = enabled;
    }

    [[nodiscard]] bool isLiveTerminalOutputEnabled() const {
        std::shared_lock lock(mutex_);
        return live_terminal_output_enabled_;
    }

    // ------------------------------------------------------------------
    // record API — 실패 시 core::Result 로 표현
    // [학습] std::expected<void, CoreError>:
    //   예외 대신 값으로 실패를 전달. capacity 초과 시 Unexpected 반환.
    // ------------------------------------------------------------------

    [[nodiscard]] core::Result record_message(
        std::string_view from,
        std::string_view to,
        std::string_view action,
        std::source_location loc = std::source_location::current())
    {
        Message event{
            .from   = std::string(from),
            .to     = std::string(to),
            .action = std::string(action),
            .meta   = EventMeta{ .location = loc },
        };

        std::shared_ptr<TraceOutputSink> sink;
        bool live_terminal_output_enabled = false;

        {
            std::unique_lock lock(mutex_);
            if (messages_.size() >= capacity_) {
                return std::unexpected(core::CoreError::Unexpected);
            }
            messages_.push_back(event);
            sink = output_sink_;
            live_terminal_output_enabled = live_terminal_output_enabled_;
        }

        if (live_terminal_output_enabled && sink) {
            sink->emit(detail::LiveTerminalFormatter::formatMessage(event));
        }
        return {};
    }

    [[nodiscard]] core::Result record_transition(
        std::string_view old_state,
        std::string_view new_state,
        std::string_view trigger,
        std::source_location loc = std::source_location::current())
    {
        Transition event{
            .old_state = std::string(old_state),
            .new_state = std::string(new_state),
            .trigger   = std::string(trigger),
            .meta      = EventMeta{ .location = loc },
        };

        std::shared_ptr<TraceOutputSink> sink;
        bool live_terminal_output_enabled = false;

        {
            std::unique_lock lock(mutex_);
            if (transitions_.size() >= capacity_) {
                return std::unexpected(core::CoreError::Unexpected);
            }
            transitions_.push_back(event);
            sink = output_sink_;
            live_terminal_output_enabled = live_terminal_output_enabled_;
        }

        if (live_terminal_output_enabled && sink) {
            sink->emit(detail::LiveTerminalFormatter::formatTransition(event));
        }
        return {};
    }

    [[nodiscard]] core::Result push_node(
        std::string_view parent,
        std::string_view child,
        std::string_view relation_type,
        std::source_location loc = std::source_location::current())
    {
        Node event{
            .parent        = std::string(parent),
            .child         = std::string(child),
            .relation_type = std::string(relation_type),
            .meta          = EventMeta{ .location = loc },
        };

        std::shared_ptr<TraceOutputSink> sink;
        bool live_terminal_output_enabled = false;

        {
            std::unique_lock lock(mutex_);
            if (nodes_.size() >= capacity_) {
                return std::unexpected(core::CoreError::Unexpected);
            }
            nodes_.push_back(event);
            sink = output_sink_;
            live_terminal_output_enabled = live_terminal_output_enabled_;
        }

        if (live_terminal_output_enabled && sink) {
            sink->emit(detail::LiveTerminalFormatter::formatNode(event));
        }
        return {};
    }

    // ------------------------------------------------------------------
    // 출력 문자열 생성 — 포맷터에 위임
    // 선언만 여기에, 구현은 detail/*_formatter.hpp 에서 인라인 제공.
    // ------------------------------------------------------------------
    [[nodiscard]] std::string format_terminal() const;
    [[nodiscard]] std::string format_diagram(
        DiagramBackend backend = DiagramBackend::PlantUML) const;
    [[nodiscard]] std::string format_plantuml() const;
    [[nodiscard]] std::string format_mermaid() const;
    [[nodiscard]] std::string format_d2() const;

    // ------------------------------------------------------------------
    // 스냅샷 — 테스트용 복사본 반환
    // [학습] std::shared_lock 으로 다중 독자 허용
    // ------------------------------------------------------------------
    [[nodiscard]] std::vector<Message>    snapshot_messages()    const {
        std::shared_lock lock(mutex_);
        return { messages_.begin(), messages_.end() };
    }
    [[nodiscard]] std::vector<Transition> snapshot_transitions() const {
        std::shared_lock lock(mutex_);
        return { transitions_.begin(), transitions_.end() };
    }
    [[nodiscard]] std::vector<Node>       snapshot_nodes()       const {
        std::shared_lock lock(mutex_);
        return { nodes_.begin(), nodes_.end() };
    }

    void clear() {
        std::unique_lock lock(mutex_);
        messages_.clear();
        transitions_.clear();
        nodes_.clear();
    }

    // ------------------------------------------------------------------
    // 전역 싱글톤
    // [학습] static local variable 초기화는 C++11 이후 스레드 안전 보장.
    //        Meyers Singleton 패턴.
    // ------------------------------------------------------------------
    [[nodiscard]] static Tracer& global() noexcept {
        static Tracer instance{ kDefaultCapacity };
        return instance;
    }

private:
    std::size_t               capacity_;
    std::deque<Message>       messages_;
    std::deque<Transition>    transitions_;
    std::deque<Node>          nodes_;
    std::shared_ptr<TraceOutputSink> output_sink_;
    bool                      live_terminal_output_enabled_{ false };
    mutable std::shared_mutex mutex_;
};

// ============================================================================
// 편의 접근자
// ============================================================================
[[nodiscard]] inline Tracer& get_global_tracer() noexcept {
    return Tracer::global();
}

} // namespace atugcc::pattern::viz

// 포맷터 구현 포함 — 이 순서가 중요: Tracer 정의 이후에 포함해야 한다.
#include "atugcc/pattern/detail/terminal_formatter.hpp"
#include "atugcc/pattern/detail/d2_formatter.hpp"
#include "atugcc/pattern/detail/mermaid_formatter.hpp"
#include "atugcc/pattern/detail/plantuml_formatter.hpp"
