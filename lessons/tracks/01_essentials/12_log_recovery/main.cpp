/**
 * @file main.cpp
 * @brief 레슨 log_recovery — 메모리 매핑 로그 버퍼와 비정상 종료 뒤의 복구를 확인한다
 * @brief Lesson log_recovery — verify memory-mapped log buffers and recovery after an unclean exit
 *
 * configureLogBuffers()로 매핑을 켜고, 이전 실행에서 남은 미전송 로그를 화면에 복구한다.
 * Turn on mapping with configureLogBuffers() and recover undelivered logs from the previous run.
 * 이번 실행은 몇 줄을 flush한 뒤 std::_Exit(0)으로 비정상 종료되어 다음 실행에 복구 대상이 된다.
 * This run flushes a few lines and terminates with std::_Exit(0) to leave records for the next run.
 */
#include <algorithm>
#include <chrono>
#include <cstddef>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <string>
#include <string_view>
#include <system_error>
#include <thread>
#include <vector>

#include "atugcc/core/error.hpp"
#include "atugcc/core/log_buffer_config.hpp"
#include "atugcc/core/logger.hpp"

namespace core = atugcc::core;

namespace {

// 로그 버퍼 매핑 디렉터리 경로
// Directory path for mapped log buffers
constexpr std::string_view kMapDir = "log/map";

// 화면에 출력할 복구된 로그 줄의 최대 개수
// Maximum number of recovered log lines to print to the screen
constexpr std::size_t kMaxRecoveredLines = 20;

// 지정된 디렉터리에서 이전 실행의 복구 파일(recovered_*.log)을 이름순으로 수집한다
// Collect recovered files (recovered_*.log) from the previous run in the given directory sorted by name
[[nodiscard]] std::vector<std::filesystem::path> collectRecoveredFiles(
    const std::filesystem::path& dir) {
    std::vector<std::filesystem::path> files;
    std::error_code iter_ec;
    std::filesystem::directory_iterator it(dir, iter_ec);
    const std::filesystem::directory_iterator end;

    while (!iter_ec && it != end) {
        std::error_code entry_ec;
        if (it->is_regular_file(entry_ec)) {
            const auto filename = it->path().filename().string();
            if (filename.starts_with("recovered_") && filename.ends_with(".log")) {
                files.push_back(it->path());
            }
        }
        it.increment(iter_ec);
    }

    std::sort(files.begin(), files.end());
    return files;
}

// 복구 파일의 내용을 최대 20줄까지 화면에 출력하고 파일을 삭제한다
// Print up to 20 lines from the recovered file and delete the file
void printAndRemoveRecoveredFile(const std::filesystem::path& path) {
    std::cout << "file: " << path.filename().string() << '\n';

    std::ifstream in(path);
    // 읽지 못한 복구 파일은 지우지 않는다: 그 안의 줄이 유일한 사본이다
    // A recovered file that could not be read is not deleted: its lines are the only copy
    if (!in.is_open()) {
        std::cout << "cannot open " << path.filename().string() << "; left in place\n";
        return;
    }
    std::vector<std::string> lines;
    std::string line;
    while (std::getline(in, line)) {
        lines.push_back(line);
    }
    const bool read_failed = in.bad();
    // Windows에서는 열린 파일을 삭제할 수 없으므로 remove 호출 전에 스트림을 닫는다
    // Close the stream before remove because Windows cannot delete an open file
    in.close();
    if (read_failed) {
        std::cout << "cannot read " << path.filename().string() << "; left in place\n";
        return;
    }

    const std::size_t shown = std::min(lines.size(), kMaxRecoveredLines);
    for (std::size_t i = 0; i < shown; ++i) {
        std::cout << "  | " << lines[i] << '\n';
    }
    if (lines.size() > kMaxRecoveredLines) {
        std::cout << "  | (... " << (lines.size() - kMaxRecoveredLines) << " more lines)\n";
    }

    std::error_code remove_ec;
    std::filesystem::remove(path, remove_ec);
    if (remove_ec) {
        std::cout << "cannot remove " << path.filename().string() << ": " << remove_ec.message()
                  << '\n';
    }
}

} // namespace

int main() {
    // 1. 로그 버퍼 매핑: 이전 실행의 .logmap 을 복구하고 이 실행의 버퍼를 매핑한다
    // 1. Map log buffers: recover the previous run's .logmap and map this run's buffers
    //
    // [학습] configureLogBuffers()는 로깅 라이브러리를 건드리는 첫 번째 호출이어야 한다.
    // [Learn] configureLogBuffers() must be the first call touching the logging library.
    // 매핑 전에 생성된 스레드 버퍼는 힙에 남아 복구할 수 없기 때문이다.
    // Thread buffers created before mapping remain on the heap and cannot be recovered.
    std::cout << "== 1. map the log buffers (recovers the previous run) ==\n";
    const auto configured = core::configureLogBuffers({
        .drainInterval = std::chrono::milliseconds{1000},
        .mappedDir = std::filesystem::path{kMapDir},
    });
    if (!configured) {
        std::cout << "configureLogBuffers failed: " << core::to_string(configured.error())
                  << "; continuing without the map\n";
    }

    // 2. 이전 실행에서 복구된 줄 확인 및 복구 파일 삭제
    // 2. Inspect recovered lines from the previous run and remove recovered files
    if (configured) {
        std::cout << "== 2. lines recovered from the previous run ==\n";
        const auto recovered_files = collectRecoveredFiles(std::filesystem::path{kMapDir});
        if (recovered_files.empty()) {
            std::cout << "nothing to recover (first run?)\n";
        } else {
            for (const auto& path : recovered_files) {
                printAndRemoveRecoveredFile(path);
            }
        }
    }

    // 3. 이번 실행의 로그 기록: 앞의 두 줄은 flush하고 뒤의 세 줄은 버퍼에만 둔다
    // 3. Logging for this run: flush the first two lines, leave the next three in the buffer
    std::cout << "== 3. this run ==\n";
    core::Logger logger{core::Logger::Config{
        .liveOutput = &std::cout,
        .enableCrashDump = false,
    }};
    logger.log(core::Level::Info, "step 1 (flushed)");
    logger.log(core::Level::Info, "step 2 (flushed)");
    logger.flush();
    // flush()는 로그 스레드를 깨운다. 그 drain이 끝나고 로그 스레드가 다시 1초 대기에 들어갈 때까지 기다린 뒤
    // 나머지 줄을 쓰고 곧바로 끝내야, 나머지 줄이 drain에 섞여 화면에 나가지 않는다
    // flush() wakes the log thread. Wait until that drain is over and the log thread is back in its
    // one-second wait, then write the remaining lines and end at once, so no drain sends them to the screen
    std::this_thread::sleep_for(std::chrono::milliseconds{100});
    logger.log(core::Level::Info, "step 3 (not flushed)");
    logger.log(core::Level::Info, "step 4 (not flushed)");
    logger.log(core::Level::Info, "step 5 (not flushed)");

    // 4. std::_Exit(0)으로 프로세스 즉시 종료
    // 4. Immediately terminate the process with std::_Exit(0)
    //
    // [학습] std::quick_exit이나 main 반환은 Logger 계약상 정상 종료(clean exit)로 취급된다.
    // [Learn] Under the Logger contract, std::quick_exit and returning from main are clean exits.
    // 정상 종료 시에는 백그라운드 소비자가 남은 로그를 모두 싱크에 전달하고 매핑 파일을 삭제하므로,
    // On a clean exit, the background consumer delivers every line to sinks and deletes the map file,
    // 다음 실행에서 복구할 것이 남지 않는다.
    // leaving nothing to be recovered in the next run.
    // 반면 std::_Exit(0)은 SIGKILL처럼 소멸자, flush, at_quick_exit 핸들러 없이 프로세스를 끝낸다.
    // In contrast, std::_Exit(0) behaves like SIGKILL: ending without destructors, flush, or exit handlers.
    // 따라서 마지막 drain 뒤에 쓴 step 3~5는 로그 스레드가 다음 drain(1000ms 뒤) 전에 가져가지 못해 매핑 파일에 남고,
    // Thus steps 3-5, written after the last drain and before the next one (1000ms later), stay in the mapped file,
    // 다음 실행의 configureLogBuffers()에서 복구 파일(recovered_*.log)로 복원된다.
    // and are restored as a recovered file (recovered_*.log) in the next run's configureLogBuffers().
    std::cout << "ending with std::_Exit(0): no destructors, no flush, no exit handlers\n";
    std::cout << "run the lesson again to see steps 3-5 recovered\n";
    std::cout.flush();
    std::_Exit(0);
}
