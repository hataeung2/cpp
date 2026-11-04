/**
 * @file main.cpp
 * @brief 레슨 format_text — std::format 포맷팅 기능, 커스텀 포맷터, std::print
 * @brief Lesson format_text — std::format formatting features, custom formatters, and std::print
 *
 * 위치 인자, 폭·채움·정렬, 진법, 사용자 정의 포맷터, 버퍼 출력, 런타임 형식, std::print 출력을 비교한다.
 * Compare positional arguments, width/fill/alignment, bases, custom formatters, buffer output, runtime formats, and std::print output.
 */
#include <array>
#include <format>
#include <iostream>
#include <iterator>
#include <print>
#include <string>
#include <string_view>

// 2차원 좌표를 나타내는 사용자 정의 구조체
// User-defined structure representing 2D coordinates
struct Vec2 {
    double x{0.0};
    double y{0.0};
};

// Vec2 에 대한 std::formatter 특수화
// Specialization of std::formatter for Vec2
template <>
struct std::formatter<Vec2> {
    int precision{-1};

    // 포맷 지정자를 파싱한다: 선택적 정밀도 .N (한 자리 숫자)을 읽고, 닫는 중괄호 } 위치를 돌려준다(} 는 소비하지 않음)
    // Parses the format specifier: reads an optional precision .N (one digit) and returns the position of the closing } (without consuming it)
    constexpr auto parse(std::format_parse_context& ctx) {
        auto it = ctx.begin();
        const auto end = ctx.end();
        if (it != end && *it == '.') {
            ++it;
            if (it == end || *it < '0' || *it > '9') {
                throw std::format_error("invalid precision in Vec2 format");
            }
            precision = *it - '0';
            ++it;
        }
        if (it != end && *it != '}') {
            throw std::format_error("invalid format specifier for Vec2");
        }
        return it;
    }

    // 지정된 정밀도로 (x, y) 형태의 문자열을 출력 버퍼에 쓴다
    // Writes (x, y) formatted string into output buffer with the specified precision
    auto format(const Vec2& v, std::format_context& ctx) const {
        if (precision >= 0) {
            return std::format_to(ctx.out(), "({0:.{1}f}, {2:.{1}f})", v.x, precision, v.y);
        }
        return std::format_to(ctx.out(), "({}, {})", v.x, v.y);
    }
};

namespace {

// 표의 한 행을 나타내는 데이터 항목
// Data item representing a single row in the table
struct TableRow {
    std::string_view name;
    int count{0};
    double share{0.0};
};

// 폭과 정렬을 적용하여 표의 한 행을 포맷팅한다
// Formats a single table row applying width and alignment specifications
[[nodiscard]] std::string formatRow(const TableRow& row) {
    return std::format("{:<10} | {:>6} | {:>6.1f}%", row.name, row.count, row.share);
}

} // namespace

int main() {
    // 1. 위치 인자: 같은 인자를 여러 번 참조하거나 순서를 바꾼다
    // 1. Positional arguments: reuse or reorder arguments by index
    std::cout << "== 1. positional arguments ==\n";
    std::cout << std::format("{0} -> {1} -> {0}\n", "idle", "run");

    // 2. 폭, 채움, 정렬: 표 형식 데이터 출력
    // 2. Width, fill, alignment: tabular data display
    std::cout << "== 2. width, fill, alignment ==\n";
    constexpr std::array<TableRow, 3> kRows{{
        {"alpha", 120, 60.0},
        {"beta", 50, 25.0},
        {"gamma", 30, 15.0},
    }};
    std::cout << std::format("{:<10} | {:>6} | {:>7}\n", "name", "count", "share");
    std::cout << std::format("{:-<10}-+-{:->6}-+-{:->7}\n", "", "", "");
    for (const auto& row : kRows) {
        std::cout << formatRow(row) << '\n';
    }

    // 3. 정수 진법과 부동소수점 정밀도
    // 3. Integer bases and floating-point precision
    std::cout << "== 3. integers and floating point ==\n";
    constexpr int kNumber = 255;
    constexpr double kPi = 3.14159265;
    std::cout << std::format("dec: {}, hex: {:#x}, oct: {:#o}, bin: {:012b}\n",
                             kNumber, kNumber, kNumber, kNumber);
    std::cout << std::format("fixed: {:.3f}, exp: {:e}, padded: {:>12.2f}\n",
                             kPi, kPi, kPi);

    // 4. 사용자 정의 타입 포맷팅 (Vec2)
    // 4. User-defined type formatting (Vec2)
    std::cout << "== 4. user type ==\n";
    const Vec2 point{1.5, -2.25};
    std::cout << std::format("default: {}\n", point);
    std::cout << std::format("precision: {:.1}\n", point);

    // 5. std::format_to: 기존 버퍼에 직접 포맷팅하여 추가
    // 5. std::format_to: format directly into an existing buffer
    std::cout << "== 5. std::format_to ==\n";
    std::string buffer;
    for (int i = 1; i <= 3; ++i) {
        std::format_to(std::back_inserter(buffer), "[item {}] ", i);
    }
    std::cout << std::format("buffer: {}\n", buffer);
    std::cout << std::format("size: {}\n", buffer.size());

    // 6. 런타임 형식 문자열: std::vformat 과 std::make_format_args
    // 6. Runtime format string: std::vformat and std::make_format_args
    // std::format 은 형식 문자열을 consteval 생성자로 검사하므로 런타임 문자열을 직접 전달할 수 없다
    // std::format checks format strings at compile time via a consteval constructor, so runtime strings cannot be passed directly
    std::cout << "== 6. runtime format string ==\n";
    // make_format_args 는 인자를 참조로 들고 있으므로 이름 있는 변수(lvalue)만 받는다 (P2905, C++20 결함 보고)
    // make_format_args holds references to its arguments, so it takes named variables (lvalues) only (P2905, a defect report against C++20)
    const int value = 42;
    const std::string_view good_pattern = "runtime pattern: value = {}";
    std::cout << std::vformat(good_pattern, std::make_format_args(value)) << '\n';

    const std::string_view bad_pattern = "{0} {";
    const std::string_view word = "test";
    try {
        const std::string result = std::vformat(bad_pattern, std::make_format_args(word));
        std::cout << result << '\n';
    } catch (const std::format_error& e) {
        std::cout << std::format("format_error: {}\n", e.what());
    }

    // 7. std::print 와 std::println: C++23 직접 출력
    // 7. std::print and std::println: C++23 direct output
    // std::print 는 std::format_string 을 받으므로 std::format 처럼 컴파일 시간에 포맷을 검사한다
    // std::print takes std::format_string, so the format is checked at compile time like std::format
    // std::cout 은 기본적으로 C stdio 와 동기화되므로(std::ios::sync_with_stdio(true)) std::cout 과 섞어 써도 순서가 유지된다
    // Mixing it with std::cout keeps the order because std::cout is synchronized with C stdio by default (std::ios::sync_with_stdio(true))
    // Windows 콘솔에서는 유니코드 콘솔 API(P2093)를 통해 출력하고, 파이프나 파일에는 바이트를 쓴다
    // On a Windows console it writes through the Unicode console API (P2093), and to a pipe or file it writes the bytes
    std::cout << "== 7. std::print / std::println (C++23) ==\n";
    std::println("{}", formatRow(kRows[0]));
    std::cout << formatRow(kRows[0]) << '\n';
    std::println("println: {:.1}", point);
    std::print(stdout, "print to stdout: {} items\n", kRows.size());

    return 0;
}
