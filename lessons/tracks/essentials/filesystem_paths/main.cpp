/**
 * @file main.cpp
 * @brief 레슨 filesystem_paths — std::filesystem의 경로 조작, 순회 및 오류 처리
 * @brief Lesson filesystem_paths — std::filesystem path manipulation, traversal, and error handling
 *
 * 경로 분해와 조합, directory_iterator를 통한 순회, 예외 및 error_code 기반 오류 처리를 다룬다
 * Covers path decomposition and composition, traversal via directory_iterator, and error handling with exceptions and error_code
 * Expected 모나드 연산(and_then, or_else)과 C++20 clock_cast를 통한 파일 시각 변환을 살펴본다
 * Explores Expected monadic operations (and_then, or_else) and file timestamp conversion via C++20 clock_cast
 */
#include <algorithm>
#include <chrono>
#include <cstdint>
#include <filesystem>
#include <format>
#include <fstream>
#include <iostream>
#include <string>
#include <string_view>
#include <system_error>
#include <utility>
#include <vector>

#include "atugcc/core/error.hpp"

namespace fs = std::filesystem;
namespace core = atugcc::core;

namespace {

constexpr std::string_view kSandbox = "fs_sandbox";

// fs::file_size 의 std::error_code 오버로드를 감싸 실패 시 FileIOFailure 를 반환한다
// Wraps the std::error_code overload of fs::file_size to return FileIOFailure on failure
[[nodiscard]] core::Expected<std::uintmax_t> fileSize(const fs::path& path) {
    std::error_code ec;
    const auto size = fs::file_size(path, ec);
    if (ec) {
        return std::unexpected(core::CoreError::FileIOFailure);
    }
    return size;
}

// 0바이트 크기의 파일은 비어 있는 것으로 간주하여 InvalidArgument 오류를 반환한다
// Treats zero-byte files as empty and returns an InvalidArgument error
[[nodiscard]] core::Expected<std::uintmax_t> requireNonEmpty(std::uintmax_t size) {
    if (size == 0) {
        return std::unexpected(core::CoreError::InvalidArgument);
    }
    return size;
}

} // namespace

int main() {
    std::cout << std::boolalpha;

    const fs::path box{kSandbox};

    std::cout << "== 1. paths ==\n";
    // 경로 객체 생성 및 슬래시(/) 연산자로 하위 경로를 연결한다
    // Construct path objects and append subpaths using the division operator (/)
    const fs::path p = fs::path{"logs"} / "2026" / "app.log";
    std::cout << std::format("p = {}\n", p.generic_string());
    std::cout << std::format("filename() = {}\n", p.filename().generic_string());
    std::cout << std::format("stem() = {}\n", p.stem().generic_string());
    std::cout << std::format("extension() = {}\n", p.extension().generic_string());
    std::cout << std::format("parent_path() = {}\n", p.parent_path().generic_string());

    // replace_extension 으로 확장자를 교체한 사본을 만든다
    // Create a copy with the extension replaced using replace_extension
    auto backup = p;
    backup.replace_extension(".bak");
    std::cout << std::format("replace_extension(\".bak\") = {}\n", backup.generic_string());

    // 운영체제 기본 디렉터리 구분자: Windows 는 '\\', POSIX 는 '/' 이다
    // Preferred directory separator: '\\' on Windows, '/' on POSIX systems
    std::cout << std::format("preferred_separator = '{}'\n",
                             static_cast<char>(fs::path::preferred_separator));

    std::cout << "== 2. create a sandbox ==\n";
    // 이전 실행의 잔여 폴더를 정리하고 하위 디렉터리를 생성한다
    // Clean up any leftover folder from previous runs and create subdirectories
    fs::remove_all(box);
    fs::create_directories(box / "logs" / "old");

    // 줄바꿈 변환을 막기 위해 이진 모드로 열고 블록을 벗어나 닫힌 뒤 크기를 읽는다
    // Open in binary mode to prevent newline translation and close via block exit before reading size
    bool written = false;
    {
        std::ofstream fileA(box / "a.txt", std::ios::binary);
        fileA << "hello";
        std::ofstream fileApp(box / "logs" / "app.log", std::ios::binary);
        fileApp << "line1line2";
        std::ofstream fileOld(box / "logs" / "old" / "app.1.log", std::ios::binary);
        fileOld << "old";
        // 짧은 내용은 버퍼에 남아 있다가 닫을 때 디스크로 가므로, 닫은 뒤에 실패를 확인한다
        // Short contents stay in the buffer until close, so check for failure after closing
        fileA.close();
        fileApp.close();
        fileOld.close();
        written = !fileA.fail() && !fileApp.fail() && !fileOld.fail();
    }
    // 쓰기에 실패하면 뒤의 크기가 모두 틀리므로 여기서 멈춘다(종료 코드 1)
    // If a write failed, every size below would be wrong, so stop here (exit code 1)
    if (!written) {
        std::cout << "cannot write the files in fs_sandbox\n";
        std::error_code cleanupError;
        fs::remove_all(box, cleanupError);
        return 1;
    }
    std::cout << "created fs_sandbox with 3 files\n";

    std::cout << "== 3. list the sandbox ==\n";
    // directory_iterator 로 직속 항목을 나열한다 (표준 순서가 없으므로 정렬 후 출력)
    // List direct entries via directory_iterator (sort before printing as order is unspecified)
    std::vector<std::string> directEntries;
    for (const auto& entry : fs::directory_iterator(box)) {
        const auto rel = entry.path().lexically_relative(box);
        if (entry.is_directory()) {
            directEntries.push_back(std::format("[dir]  {}", rel.generic_string()));
        } else {
            directEntries.push_back(
                std::format("[file] {} ({} bytes)", rel.generic_string(), fs::file_size(entry.path())));
        }
    }
    std::ranges::sort(directEntries);
    for (const auto& line : directEntries) {
        std::cout << line << '\n';
    }

    // recursive_directory_iterator 로 모든 하위 항목을 재귀 순회한다 (depth() 와 상대 경로)
    // Recursively traverse all descendant entries via recursive_directory_iterator (depth() and relative path)
    std::vector<std::pair<std::string, std::string>> recursiveEntries;
    for (fs::recursive_directory_iterator it(box), end; it != end; ++it) {
        const auto& entry = *it;
        const auto rel = entry.path().lexically_relative(box);
        const auto relStr = rel.generic_string();
        if (entry.is_directory()) {
            recursiveEntries.emplace_back(relStr, std::format("depth {}: {}", it.depth(), relStr));
        } else {
            recursiveEntries.emplace_back(
                relStr,
                std::format("depth {}: {} ({} bytes)", it.depth(), relStr, fs::file_size(entry.path())));
        }
    }
    std::ranges::sort(recursiveEntries);
    for (const auto& entry : recursiveEntries) {
        std::cout << entry.second << '\n';
    }

    std::cout << "== 4. errors ==\n";
    // (a) 예외 방식: 존재하지 않는 파일의 크기를 조회하면 filesystem_error 가 발생한다
    // (a) Exception approach: querying size of a non-existent file throws filesystem_error
    try {
        [[maybe_unused]] const auto s = fs::file_size(box / "missing.txt");
    } catch (const fs::filesystem_error& e) {
        std::cout << std::format("filesystem_error, path1 = {}\n", e.path1().generic_string());
    }

    // (b) std::error_code 오버로드: 예외를 던지지 않고 오류 코드를 채운다
    // (b) std::error_code overload: fills error code instead of throwing an exception
    const fs::path missing = box / "missing.txt";
    std::error_code ec;
    const auto size = fs::file_size(missing, ec);
    std::cout << std::format("error_code: no_such_file_or_directory = {}, returned (uintmax_t)-1 = {}\n",
                             ec == std::errc::no_such_file_or_directory,
                             size == static_cast<std::uintmax_t>(-1));

    // (c) core::Expected 로 감싸기: 모나드 연산(and_then, or_else)으로 오류 처리를 합성한다
    // (c) Wrapping in core::Expected: compose error handling via monadic operations (and_then, or_else)
    const auto sizeA = fileSize(box / "a.txt");
    if (sizeA.has_value()) {
        std::cout << std::format("fileSize(a.txt) -> {}\n", *sizeA);
    }

    const auto sizeMissing = fileSize(missing);
    if (!sizeMissing.has_value()) {
        std::cout << std::format("fileSize(missing.txt) -> error {}\n",
                                 core::to_string(sizeMissing.error()));
    }

    const auto withFallback = fileSize(missing).or_else([](core::CoreError) -> core::Expected<std::uintmax_t> {
        return std::uintmax_t{0};
    });
    std::cout << std::format("fileSize(missing.txt).or_else(0) -> {}\n", *withFallback);

    const auto chained = fileSize(box / "a.txt").and_then(requireNonEmpty);
    if (chained.has_value()) {
        std::cout << std::format("fileSize(a.txt).and_then(requireNonEmpty) -> {}\n", *chained);
    }

    std::cout << "== 5. timestamps and cleanup ==\n";
    // last_write_time 으로 파일 수정 시각을 읽고 C++20 clock_cast 로 system_clock 으로 변환한다
    // Read file modification time via last_write_time and convert to system_clock using C++20 clock_cast
    // file_clock 은 구현에 따라 to_sys(libstdc++) 또는 to_utc(MSVC) 중 하나만 갖는다
    // file_clock has either to_sys (libstdc++) or to_utc (MSVC), depending on the implementation
    // clock_cast 는 있는 쪽을 골라 쓰므로 두 플랫폼에서 같은 코드로 된다
    // clock_cast picks whichever exists, so the same code works on both platforms
    const auto ft = fs::last_write_time(box / "a.txt");
    const auto sys = std::chrono::clock_cast<std::chrono::system_clock>(ft);
    std::cout << std::format("modified (UTC date): {:%F}\n", sys);

    // 파일 생성 직후이므로 현재 시각과 1분 이내 차이임을 확인한다
    // Verify the file was modified within the last minute since it was just created
    const auto now = std::chrono::system_clock::now();
    const auto diff = std::chrono::abs(now - sys);
    std::cout << std::format("modified within the last minute: {}\n",
                             diff < std::chrono::minutes{1});

    // 작업 폴더를 정리하고 삭제된 항목 수와 폴더 부재를 확인한다
    // Clean up the sandbox directory and verify the number of removed entries and its absence
    const auto removed = fs::remove_all(box);
    std::cout << std::format("remove_all removed {} entries\n", removed);
    std::cout << std::format("fs_sandbox exists: {}\n", fs::exists(box));

    return 0;
}
