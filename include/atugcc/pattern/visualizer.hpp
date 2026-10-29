/**
 * @file visualizer.hpp
 * @brief atugcc::pattern::viz — 디자인 패턴 런타임 트레이서
 *
 * 이 헤더 하나로 패턴 실행 흐름을 기록하고, 여러 형식의 문자열로
 * 변환(터미널 ASCII / PlantUML, Mermaid, D2)할 수 있다.
 *
 * 사람이 읽는 출력(터미널 텍스트, 다이어그램 문자열)의 출력 책임은 호출자에게 있다:
 *   std::cout << tracer.formatTerminal();
 *   atugcc::core::Logger::global().log("{}", tracer.formatDiagram());
 *
 * 긴 trace는 예산(DiagramBudget) 안의 조각으로 나뉜다 (.agent/rules/diagrams.md):
 *   for (const auto& part : tracer.diagramParts(DiagramBackend::Mermaid, {.maxMessages = 30}))
 *       render(part.title, part.source);   // 웹 뷰어는 조각마다 블록 하나
 *   연속 반복 메시지와 같은 상태 간선은 "label ×N" 으로 합쳐지고, 순서는 유지된다.
 *
 * 이벤트 스트림 (JSON Lines, 웹 플레이그라운드용):
 *   환경변수 ATUGCC_TRACE_OUT=<파일> 이 있으면 모든 Tracer 가 이벤트를 한 줄씩 그 파일에 쓴다.
 *   코드 수정 없이 켜고 끈다. 줄마다 flush 되고, Tracer 소멸 시 Mermaid 조각이 "diagram" 줄로 나간다.
 *   직접 연결: tracer.setEventSink(JsonLinesEventSink::open("trace.jsonl"));
 *   이벤트마다 seq(프로세스 전역 순번)와 tracerId 가 붙는다. 스키마: docs/specs/020_05_tracer_event_stream.md §2.2
 *
 * 구간 시간 측정 (span, docs/specs/020_06_tracer_span_timing.md):
 *   { auto span = tracer.timeScope("parse"); parse(); }   // 스코프가 끝날 때 기록 (span.stop() 으로 일찍 끝낼 수도 있다)
 *   std::cout << tracer.formatTimings();                  // (위치, 라벨, 측정기)별 count/total/mean/min/max 표
 *   - 측정기: 기본 "wall"(steady_clock). tracer.setSpanMeter(makeSpanMeter("cpu")) 또는 ATUGCC_SPAN_METER=cpu 로
 *     스레드 CPU 시간. 구간은 시작할 때의 측정기로 끝난다. 다른 방식으로 잰 값은 (void)recordSpan(label, dur, loc, "perf") ([[nodiscard]] Result).
 *   - live 출력이 켜져 있으면 "⏱ parse  1.235 ms  (main.cpp:42)" 한 줄, 이벤트 스트림에는 "span" 줄.
 *   - 핫 루프에서는 ATUGCC_TRACE_FLUSH_MS=100 으로 스트림 flush 간격을 둔다 (기본 0 = 줄마다 flush).
 *   - 수명: ScopedSpan 은 Tracer& 를 보관한다. Tracer 보다 짧은 스코프에서만 쓴다 (Debug 빌드는 Tracer 소멸 시 assert).
 *   - 개별 span 은 저장하지 않고 sink 로만 흘려보낸다. Tracer 에는 집계만 남는다 (spanStats()).
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
 * [7] 이벤트 스트림 — TraceEventSink 인터페이스 / JsonLinesEventSink, 함수 내부 static 으로
 *     프로세스 공용 sink 를 한 번만 연다(environmentEventSink), EventSink concept 은 static_assert 로 확인
 * [8] 구간 측정 — RAII(ScopedSpan), std::atomic<std::shared_ptr> 로 Tracer 락 없이 측정기 교체(lock-free 보장은 아님),
 *     transparent comparator(is_transparent)로 할당 없는 map 조회, 복사·이동 불가 타입을
 *     보장된 복사 생략(C++17)으로 반환(timeScope)
 * ==========================================================================
 */
#pragma once

#include <algorithm>
#include <array>
#include <atomic>
#include <chrono>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <deque>
#include <filesystem>
#include <format>
#include <fstream>
#include <map>
#include <memory>
#include <mutex>
#include <optional>
#include <ostream>
#include <shared_mutex>
#include <source_location>
#include <string>
#include <string_view>
#include <thread>
#include <tuple>
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
// 다이어그램 분할 예산 및 조각 정보
// C++20 Designated Initializers 로 개별 필드만 지정(변경) 가능:
//   tracer.formatDiagram(DiagramBackend::Mermaid, {.maxMessages = 30})
// ============================================================================
struct DiagramBudget {
    std::size_t maxParticipants = 5;
    std::size_t maxMessages = 15;
    std::size_t maxStates = 12;
    std::size_t maxNodes = 12;
    std::size_t labelWrap = 24;
};

/// 다이어그램 종류
enum class DiagramKind {
    Sequence,
    State,
    Structure,
};

/// 분할된 다이어그램 조각 정보
struct DiagramPart {
    DiagramKind    kind;
    DiagramBackend backend;
    std::string    title;
    std::string    source;
    bool           overBudget;
};

// ============================================================================
// 이벤트 메타데이터
// C++20 Designated Initializer 로 초기화:
//   EventMeta meta{ .location = std::source_location::current() };
// ============================================================================
struct EventMeta {
    std::source_location location;
    std::chrono::system_clock::time_point timestamp{ std::chrono::system_clock::now() };
    std::uint64_t seq{ 0 };
    std::uint32_t tracerId{ 0 };
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

/// 측정기: 구간의 시작과 끝에서 읽는 단조 증가 눈금(ns). 같은 스레드에서 읽는다
class SpanMeter {
public:
    virtual ~SpanMeter() = default;
    [[nodiscard]] virtual std::string_view name() const noexcept = 0;   // "wall", "cpu", ...
    [[nodiscard]] virtual std::uint64_t nowNs() const noexcept = 0;
};

class WallSpanMeter final : public SpanMeter {
public:
    [[nodiscard]] std::string_view name() const noexcept override {
        return "wall";
    }
    [[nodiscard]] std::uint64_t nowNs() const noexcept override;
};

class ThreadCpuSpanMeter final : public SpanMeter {
public:
    [[nodiscard]] std::string_view name() const noexcept override {
        return "cpu";
    }
    [[nodiscard]] std::uint64_t nowNs() const noexcept override;
};

/// "wall" | "cpu" → 측정기, 모르는 이름은 nullptr
[[nodiscard]] inline std::shared_ptr<SpanMeter> makeSpanMeter(std::string_view name);

/// 구간 측정 이벤트 레코드
struct Span {
    std::string   label;
    std::string   meter;
    std::uint64_t durationNs{ 0 };
    std::uint64_t threadId{ 0 };
    EventMeta     meta;
};

/// 구간 통계 레코드
struct SpanStats {
    std::string   label;
    std::string   meter;
    std::string   file;
    std::uint32_t line{ 0 };
    std::uint64_t count{ 0 };
    std::uint64_t totalNs{ 0 };
    std::uint64_t minNs{ 0 };
    std::uint64_t maxNs{ 0 };
};

namespace detail {

struct LiveTerminalFormatter {
    [[nodiscard]] static std::string formatMessage(const Message& message);
    [[nodiscard]] static std::string formatTransition(const Transition& transition);
    [[nodiscard]] static std::string formatNode(const Node& node);
    [[nodiscard]] static std::string formatSpan(const Span& span);
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
//   void T::onEvent(const Message&) 가 존재해야 한다.
// ============================================================================
template <typename T, typename Event>
concept EventSink = requires(T& sink, const Event& e) {
    { sink.onEvent(e) } -> std::same_as<void>;
};

inline constexpr std::string_view kTraceOutEnv   = "ATUGCC_TRACE_OUT";
inline constexpr std::string_view kSpanMeterEnv  = "ATUGCC_SPAN_METER";
inline constexpr std::string_view kTraceFlushEnv = "ATUGCC_TRACE_FLUSH_MS";

class TraceEventSink {
public:
    virtual ~TraceEventSink() = default;
    virtual void onEvent(const Message& event) = 0;
    virtual void onEvent(const Transition& event) = 0;
    virtual void onEvent(const Node& event) = 0;
    virtual void onEvent(const Span& /*event*/) {}
    virtual void onDiagramParts(std::uint32_t tracerId, const std::vector<DiagramPart>& parts) = 0;
};

[[nodiscard]] inline std::string toJsonLine(const Message& event);
[[nodiscard]] inline std::string toJsonLine(const Transition& event);
[[nodiscard]] inline std::string toJsonLine(const Node& event);
[[nodiscard]] inline std::string toJsonLine(const Span& event);
// part = 0-based index within parts of the same DiagramKind, parts = count of that kind
[[nodiscard]] inline std::string toJsonLine(std::uint32_t tracerId, std::size_t part, std::size_t parts, const DiagramPart& diagram);

class JsonLinesEventSink final : public TraceEventSink {
public:
    [[nodiscard]] static std::shared_ptr<JsonLinesEventSink> open(
        const std::filesystem::path& path,
        std::chrono::milliseconds flushInterval = std::chrono::milliseconds{ 0 });
    ~JsonLinesEventSink() override;
    void onEvent(const Message& event) override;      // writeLine(toJsonLine(event))
    void onEvent(const Transition& event) override;
    void onEvent(const Node& event) override;
    void onEvent(const Span& event) override;
    void onDiagramParts(std::uint32_t tracerId, const std::vector<DiagramPart>& parts) override;
private:
    explicit JsonLinesEventSink(
        std::ofstream stream,
        std::chrono::milliseconds flushInterval) noexcept;
    void writeLine(std::string_view line);            // lock; write line + '\n'; flush
    std::mutex                            mutex_;
    std::ofstream                         stream_;
    std::chrono::milliseconds             flush_interval_{ 0 };
    std::chrono::steady_clock::time_point last_flush_{};
};

// ATUGCC_TRACE_OUT set and openable -> one process-wide sink; otherwise nullptr. Opened once.
[[nodiscard]] inline std::shared_ptr<TraceEventSink> environmentEventSink();

namespace detail {
[[nodiscard]] inline std::uint64_t nextEventSeq() noexcept;    // 1, 2, 3, ... process-wide
[[nodiscard]] inline std::uint32_t nextTracerId() noexcept;    // 1, 2, 3, ... process-wide
[[nodiscard]] inline std::shared_ptr<SpanMeter> defaultSpanMeter();
[[nodiscard]] inline std::shared_ptr<SpanMeter> environmentSpanMeter();
[[nodiscard]] inline std::uint64_t currentThreadOrdinal() noexcept;

struct SpanKey {
    std::string   file;
    std::uint32_t line{ 0 };
    std::string   label;
    std::string   meter;
};

struct SpanKeyView {
    std::string_view file;
    std::uint32_t    line{ 0 };
    std::string_view label;
    std::string_view meter;
};

struct SpanKeyLess {
    using is_transparent = void;

    template <typename T>
    static auto keyTuple(const T& k) noexcept {
        return std::tuple<std::string_view, std::uint32_t, std::string_view, std::string_view>(
            k.file, k.line, k.label, k.meter);
    }

    template <typename A, typename B>
    bool operator()(const A& lhs, const B& rhs) const noexcept {
        return keyTuple(lhs) < keyTuple(rhs);
    }
};

struct SpanAggregate {
    std::uint64_t count{ 0 };
    std::uint64_t totalNs{ 0 };
    std::uint64_t minNs{ 0 };
    std::uint64_t maxNs{ 0 };
};
}

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
// ScopedSpan (RAII 구간 타이머)
// ============================================================================
class Tracer;

class ScopedSpan {
public:
    ScopedSpan(Tracer& tracer, std::string_view label,
               std::source_location loc = std::source_location::current());
    ~ScopedSpan();

    ScopedSpan(const ScopedSpan&) = delete;
    ScopedSpan& operator=(const ScopedSpan&) = delete;

    void stop() noexcept;

private:
    Tracer*                    tracer_;
    std::string                label_;
    std::source_location       location_;
    std::shared_ptr<SpanMeter> meter_;
    std::uint64_t              start_ns_{ 0 };
    bool                       active_{ true };
};

// ============================================================================
// Tracer
// --------------------------------------------------------------------------
// - record_*(…) : 이벤트를 내부 버퍼에 저장 (write → unique_lock)
// - formatTerminal() : ANSI/ASCII 문자열 반환  (read → shared_lock)
// - diagramParts()   : 분할된 다이어그램 조각 목록 반환
// - formatDiagram()  : 선택한 백엔드(기본 PlantUML) 스니펫 반환
// - formatPlantuml() : PlantUML 스니펫 반환 (thin wrapper)
// - formatMermaid()  : Mermaid 스니펫 반환 (thin wrapper)
// - formatD2()       : D2 스니펫 반환 (thin wrapper)
// - snapshot_*()      : 테스트/검사용 복사본 반환
// - getGlobalTracer(): 프로세스 전역 싱글톤
//
// [학습] std::shared_mutex:
//   여러 스레드가 동시에 format_(read) 를 호출할 수 있도록 공유 락을 허용.
//   record_(write) 는 단독 점유 락(unique_lock) 사용.
// ============================================================================
class Tracer {
public:
    static constexpr std::size_t kDefaultCapacity = 1024;

    explicit Tracer(std::size_t capacity = kDefaultCapacity)
        : capacity_(capacity)
        , id_(detail::nextTracerId())
        , event_sink_(environmentEventSink())
        , span_meter_(detail::environmentSpanMeter())
    {}

    Tracer(const Tracer&) = delete;
    Tracer& operator=(const Tracer&) = delete;

    ~Tracer();

    void setOutputSink(std::shared_ptr<TraceOutputSink> sink) {
        std::unique_lock lock(mutex_);
        output_sink_ = std::move(sink);
    }

    [[nodiscard]] std::shared_ptr<TraceOutputSink> outputSink() const {
        std::shared_lock lock(mutex_);
        return output_sink_;
    }

    void setEventSink(std::shared_ptr<TraceEventSink> sink) {
        std::unique_lock lock(mutex_);
        event_sink_ = std::move(sink);
    }

    [[nodiscard]] std::shared_ptr<TraceEventSink> eventSink() const {
        std::shared_lock lock(mutex_);
        return event_sink_;
    }

    [[nodiscard]] std::uint32_t id() const noexcept {
        return id_;
    }

    void setLiveTerminalOutputEnabled(bool enabled) {
        std::unique_lock lock(mutex_);
        live_terminal_output_enabled_ = enabled;
    }

    [[nodiscard]] bool isLiveTerminalOutputEnabled() const {
        std::shared_lock lock(mutex_);
        return live_terminal_output_enabled_;
    }

    void setSpanMeter(std::shared_ptr<SpanMeter> meter) {
        span_meter_.store(meter ? std::move(meter) : detail::defaultSpanMeter());
    }

    [[nodiscard]] std::shared_ptr<SpanMeter> spanMeter() const {
        return span_meter_.load();
    }

    [[nodiscard]] ScopedSpan timeScope(
        std::string_view label,
        std::source_location loc = std::source_location::current());

    // ------------------------------------------------------------------
    // record API — 실패 시 core::Result 로 표현
    // [학습] std::expected<void, CoreError>:
    //   예외 대신 값으로 실패를 전달. capacity 초과 시 Unexpected 반환.
    // ------------------------------------------------------------------

    [[nodiscard]] core::Result recordMessage(
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
        std::shared_ptr<TraceEventSink>  event_sink;
        bool live_terminal_output_enabled = false;

        {
            std::unique_lock lock(mutex_);
            if (messages_.size() >= capacity_) {
                return std::unexpected(core::CoreError::Unexpected);
            }
            event.meta.seq = detail::nextEventSeq();
            event.meta.tracerId = id_;
            messages_.push_back(event);
            event_sink = event_sink_;
            sink = output_sink_;
            live_terminal_output_enabled = live_terminal_output_enabled_;
        }

        if (live_terminal_output_enabled && sink) {
            sink->emit(detail::LiveTerminalFormatter::formatMessage(event));
        }
        if (event_sink) {
            event_sink->onEvent(event);
        }
        return {};
    }

    [[nodiscard]] core::Result recordTransition(
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
        std::shared_ptr<TraceEventSink>  event_sink;
        bool live_terminal_output_enabled = false;

        {
            std::unique_lock lock(mutex_);
            if (transitions_.size() >= capacity_) {
                return std::unexpected(core::CoreError::Unexpected);
            }
            event.meta.seq = detail::nextEventSeq();
            event.meta.tracerId = id_;
            transitions_.push_back(event);
            event_sink = event_sink_;
            sink = output_sink_;
            live_terminal_output_enabled = live_terminal_output_enabled_;
        }

        if (live_terminal_output_enabled && sink) {
            sink->emit(detail::LiveTerminalFormatter::formatTransition(event));
        }
        if (event_sink) {
            event_sink->onEvent(event);
        }
        return {};
    }

    [[nodiscard]] core::Result pushNode(
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
        std::shared_ptr<TraceEventSink>  event_sink;
        bool live_terminal_output_enabled = false;

        {
            std::unique_lock lock(mutex_);
            if (nodes_.size() >= capacity_) {
                return std::unexpected(core::CoreError::Unexpected);
            }
            event.meta.seq = detail::nextEventSeq();
            event.meta.tracerId = id_;
            nodes_.push_back(event);
            event_sink = event_sink_;
            sink = output_sink_;
            live_terminal_output_enabled = live_terminal_output_enabled_;
        }

        if (live_terminal_output_enabled && sink) {
            sink->emit(detail::LiveTerminalFormatter::formatNode(event));
        }
        if (event_sink) {
            event_sink->onEvent(event);
        }
        return {};
    }

    [[nodiscard]] core::Result recordSpan(
        std::string_view label,
        std::chrono::nanoseconds duration,
        std::source_location loc = std::source_location::current(),
        std::string_view meter = "manual")
    {
        if (duration < std::chrono::nanoseconds{ 0 }) {
            return std::unexpected(core::CoreError::InvalidArgument);
        }

        const auto duration_ns = static_cast<std::uint64_t>(duration.count());
        Span span{
            .label      = std::string(label),
            .meter      = std::string(meter),
            .durationNs = duration_ns,
            .threadId   = detail::currentThreadOrdinal(),
            .meta       = EventMeta{ .location = loc },
        };

        std::shared_ptr<TraceOutputSink> sink;
        std::shared_ptr<TraceEventSink>  event_sink;
        bool live_terminal_output_enabled = false;

        {
            std::unique_lock lock(mutex_);
            span.meta.seq = detail::nextEventSeq();
            span.meta.tracerId = id_;

            detail::SpanKeyView key_view{
                .file  = loc.file_name(),
                .line  = loc.line(),
                .label = label,
                .meter = meter,
            };
            auto it = span_stats_.find(key_view);
            if (it == span_stats_.end()) {
                detail::SpanKey new_key{
                    .file  = std::string(loc.file_name()),
                    .line  = loc.line(),
                    .label = std::string(label),
                    .meter = std::string(meter),
                };
                it = span_stats_.emplace(std::move(new_key), detail::SpanAggregate{}).first;
            }

            auto& agg = it->second;
            if (agg.count == 0) {
                agg.minNs = duration_ns;
                agg.maxNs = duration_ns;
            } else {
                if (duration_ns < agg.minNs) {
                    agg.minNs = duration_ns;
                }
                if (duration_ns > agg.maxNs) {
                    agg.maxNs = duration_ns;
                }
            }
            agg.count += 1;
            agg.totalNs += duration_ns;

            event_sink = event_sink_;
            sink = output_sink_;
            live_terminal_output_enabled = live_terminal_output_enabled_;
        }

        if (live_terminal_output_enabled && sink) {
            sink->emit(detail::LiveTerminalFormatter::formatSpan(span));
        }
        if (event_sink) {
            event_sink->onEvent(span);
        }
        return {};
    }

    // ------------------------------------------------------------------
    // 출력 문자열 생성 — 포맷터에 위임
    // 선언만 여기에, 구현은 detail/*_formatter.hpp 에서 인라인 제공.
    // ------------------------------------------------------------------
    [[nodiscard]] std::string formatTerminal() const;
    [[nodiscard]] std::vector<DiagramPart> diagramParts(
        DiagramBackend backend = DiagramBackend::PlantUML,
        const DiagramBudget& budget = {}) const;
    [[nodiscard]] std::string formatDiagram(
        DiagramBackend backend = DiagramBackend::PlantUML,
        const DiagramBudget& budget = {}) const;
    [[nodiscard]] std::string formatPlantuml() const;
    [[nodiscard]] std::string formatMermaid() const;
    [[nodiscard]] std::string formatD2() const;
    [[nodiscard]] std::vector<SpanStats> spanStats() const;
    [[nodiscard]] std::string formatTimings() const;

    // ------------------------------------------------------------------
    // 스냅샷 — 테스트용 복사본 반환
    // [학습] std::shared_lock 으로 다중 독자 허용
    // ------------------------------------------------------------------
    [[nodiscard]] std::vector<Message>    snapshotMessages()    const {
        std::shared_lock lock(mutex_);
        return { messages_.begin(), messages_.end() };
    }
    [[nodiscard]] std::vector<Transition> snapshotTransitions() const {
        std::shared_lock lock(mutex_);
        return { transitions_.begin(), transitions_.end() };
    }
    [[nodiscard]] std::vector<Node>       snapshotNodes()       const {
        std::shared_lock lock(mutex_);
        return { nodes_.begin(), nodes_.end() };
    }

    void clear() {
        std::unique_lock lock(mutex_);
        messages_.clear();
        transitions_.clear();
        nodes_.clear();
        span_stats_.clear();
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
    std::uint32_t             id_;
    std::deque<Message>       messages_;
    std::deque<Transition>    transitions_;
    std::deque<Node>          nodes_;
    std::shared_ptr<TraceOutputSink> output_sink_;
    std::shared_ptr<TraceEventSink>  event_sink_;
    std::atomic<std::shared_ptr<SpanMeter>>                               span_meter_;
    std::map<detail::SpanKey, detail::SpanAggregate, detail::SpanKeyLess> span_stats_;
    std::atomic<std::size_t>                                              live_spans_{ 0 };
    bool                      live_terminal_output_enabled_{ false };
    mutable std::shared_mutex mutex_;
    friend class ScopedSpan;
};

// ============================================================================
// 편의 접근자
// ============================================================================
[[nodiscard]] inline Tracer& getGlobalTracer() noexcept {
    return Tracer::global();
}

} // namespace atugcc::pattern::viz

// 포맷터 구현 포함 — 이 순서가 중요: Tracer 정의 이후에 포함해야 한다.
#include "atugcc/pattern/detail/diagram_split.hpp"
#include "atugcc/pattern/detail/terminal_formatter.hpp"
#include "atugcc/pattern/detail/d2_formatter.hpp"
#include "atugcc/pattern/detail/mermaid_formatter.hpp"
#include "atugcc/pattern/detail/plantuml_formatter.hpp"
#include "atugcc/pattern/detail/diagram_parts.hpp"
#include "atugcc/pattern/detail/event_stream.hpp"
#include "atugcc/pattern/detail/span_timing.hpp"
