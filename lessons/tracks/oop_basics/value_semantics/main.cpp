/**
 * @file main.cpp
 * @brief 레슨 value_semantics — 값 의미론과 연산자: operator<=>, 연산자 오버로딩
 * @brief Lesson value_semantics — Value semantics and operators: operator<=>, operator overloading
 *
 * int 처럼 복사가 서로 독립인 값 타입을 만들고, 비교 연산자 여섯 개를 직접 쓸 때의 실수, 기본 비교 operator<=>,
 * 직접 쓰는 <=> 와 ==, 값 타입의 산술 연산자와 출력 연산자를 출력으로 확인한다
 * Build value types whose copies are independent, like int, then see the mistake of writing six comparison operators by hand,
 * defaulted operator<=>, a hand-written <=> with ==, and the arithmetic and output operators of a value type through the output
 */
#include <algorithm>
#include <compare>
#include <format>
#include <iostream>
#include <memory>
#include <ostream>
#include <string>
#include <vector>

namespace {

// 1. 값 타입: 복사하면 서로 독립이고, 같음은 주소가 아니라 값으로 정한다(== 기본 비교)
// 1. A value type: copies are independent, and equality is decided by value, not by address (defaulted ==)
struct Point {
    int x = 0;
    int y = 0;

    [[nodiscard]] bool operator==(const Point&) const = default;
};

[[nodiscard]] std::string pointText(const Point& point) {
    return std::format("({}, {})", point.x, point.y);
}

// 2. 흔한 실수: 비교 연산자 여섯 개를 직접 쓴다. operator< 가 day 를 잊어서 == / != 와 나머지 넷이 서로 맞지 않는다
// 2. The common mistake: write the six comparison operators by hand. operator< forgets day, so == and != disagree with the other four
class OldDate {
public:
    OldDate(int year, int month, int day) : year_(year), month_(month), day_(day) {}

    [[nodiscard]] bool operator==(const OldDate& other) const {
        return year_ == other.year_ && month_ == other.month_ && day_ == other.day_;
    }

    [[nodiscard]] bool operator!=(const OldDate& other) const {
        return !(*this == other);
    }

    [[nodiscard]] bool operator<(const OldDate& other) const {
        if (year_ != other.year_) {
            return year_ < other.year_;
        }
        return month_ < other.month_;
    }

    [[nodiscard]] bool operator>(const OldDate& other) const {
        return other < *this;
    }

    [[nodiscard]] bool operator<=(const OldDate& other) const {
        return !(other < *this);
    }

    [[nodiscard]] bool operator>=(const OldDate& other) const {
        return !(*this < other);
    }

private:
    int year_ = 0;
    int month_ = 0;
    int day_ = 0;
};

// 3. 바른 방식: operator<=> 를 = default 로 두면 멤버를 선언 순서대로 비교하는 여섯 연산자가 모두 생긴다
// 3. The right way: = default on operator<=> gives all six operators, comparing the members in declaration order
struct Date {
    int year = 0;
    int month = 0;
    int day = 0;

    [[nodiscard]] auto operator<=>(const Date&) const = default;
};

[[nodiscard]] std::string dateText(const Date& date) {
    return std::format("{:04}-{:02}-{:02}", date.year, date.month, date.day);
}

// 4. 멤버별 비교가 뜻과 다르면 <=> 와 == 를 직접 쓴다: 1/2 과 2/4 는 멤버가 달라도 같은 값이다
// 4. When memberwise comparison is not the meaning, write <=> and == yourself: 1/2 and 2/4 have different members but the same value
// 5. 값 타입의 연산자: += 는 멤버, + 는 += 로 만든 비멤버, << 는 출력
// 5. The operators of a value type: += is a member, + is a non-member built on +=, << prints
class Fraction {
public:
    // 분모는 0 보다 크고 값은 작다고 둔다(분모와 곱셈의 넘침은 이 레슨이 검사하지 않는다)
    // The denominator is taken to be greater than 0 and the values small (this lesson checks neither the denominator nor multiplication overflow)
    Fraction(int numerator, int denominator) : numerator_(numerator), denominator_(denominator) {}

    // 값이 같아도 표현(2/4 와 1/2)이 다를 수 있으므로 weak_ordering: 어디에 써도 바꿔 넣을 수 있는 "같다"가 아니라 값이 같은 "동등하다"
    // The same value can have different forms (2/4 and 1/2), so weak_ordering: "equivalent" (same value), not "equal" (interchangeable anywhere)
    [[nodiscard]] std::weak_ordering operator<=>(const Fraction& other) const {
        return numerator_ * other.denominator_ <=> other.numerator_ * denominator_;
    }

    // <=> 를 직접 쓰면 == 는 생기지 않는다. == 도 같은 기준으로 직접 쓴다
    // A hand-written <=> does not give ==. Write == yourself with the same rule
    [[nodiscard]] bool operator==(const Fraction& other) const {
        return numerator_ * other.denominator_ == other.numerator_ * denominator_;
    }

    Fraction& operator+=(const Fraction& other) {
        numerator_ = numerator_ * other.denominator_ + other.numerator_ * denominator_;
        denominator_ *= other.denominator_;
        return *this;
    }

    // 왼쪽 피연산자를 값으로 받아 += 를 쓴다: 덧셈의 규칙이 한 곳에만 있다
    // Take the left operand by value and use +=: the rule for addition lives in one place
    friend Fraction operator+(Fraction left, const Fraction& right) {
        left += right;
        return left;
    }

    friend std::ostream& operator<<(std::ostream& out, const Fraction& fraction) {
        return out << fraction.numerator_ << '/' << fraction.denominator_;
    }

private:
    int numerator_ = 0;
    int denominator_ = 1;
};

} // namespace

int main() {
    std::cout << std::boolalpha;

    std::cout << "== Step 1: values and shared references ==\n";
    Point a{1, 2};
    Point b = a;
    b.x = 10;
    std::cout << "a: " << pointText(a) << ", b after b.x = 10: " << pointText(b) << '\n';
    std::cout << "a == b: " << (a == b) << '\n';
    b = a;
    std::cout << "after b = a, a == b: " << (a == b) << '\n';
    const auto p = std::make_shared<Point>(Point{1, 2});
    const auto q = p;
    q->x = 10;
    std::cout << "*p after q->x = 10: " << pointText(*p) << " (p and q share one Point)\n";

    std::cout << "== Step 2: six hand-written comparison operators ==\n";
    const OldDate oldFirst{2026, 11, 17};
    const OldDate oldSecond{2026, 11, 18};
    std::cout << "2026-11-17 vs 2026-11-18:\n";
    std::cout << std::format("  == {}, != {}, < {}, <= {}, > {}, >= {}\n", oldFirst == oldSecond, oldFirst != oldSecond,
                             oldFirst < oldSecond, oldFirst <= oldSecond, oldFirst > oldSecond, oldFirst >= oldSecond);

    std::cout << "== Step 3: defaulted operator<=> ==\n";
    const Date first{2026, 11, 17};
    const Date second{2026, 11, 18};
    std::cout << "2026-11-17 vs 2026-11-18:\n";
    std::cout << std::format("  == {}, != {}, < {}, <= {}, > {}, >= {}\n", first == second, first != second, first < second,
                             first <= second, first > second, first >= second);
    std::vector<Date> dates{{2026, 11, 18}, {2025, 1, 2}, {2026, 11, 17}, {2026, 2, 1}};
    std::ranges::sort(dates);
    std::cout << "sorted:";
    for (const auto& date : dates) {
        std::cout << ' ' << dateText(date);
    }
    std::cout << '\n';

    std::cout << "== Step 4: a hand-written <=> and == ==\n";
    const Fraction half{1, 2};
    const Fraction twoQuarters{2, 4};
    const Fraction third{1, 3};
    std::cout << half << " == " << twoQuarters << ": " << (half == twoQuarters) << '\n';
    std::cout << half << " < " << twoQuarters << ": " << (half < twoQuarters) << '\n';
    std::cout << third << " < " << half << ": " << (third < half) << '\n';
    std::cout << half << " <=> " << twoQuarters << " is equivalent: " << std::is_eq(half <=> twoQuarters) << '\n';

    std::cout << "== Step 5: arithmetic and output operators ==\n";
    Fraction sum = half;
    sum += Fraction{1, 4};
    std::cout << "1/2 += 1/4 gives " << sum << '\n';
    const Fraction total = half + Fraction{1, 4};
    std::cout << "1/2 + 1/4 gives " << total << '\n';
    std::cout << total << " == 3/4: " << (total == Fraction{3, 4}) << '\n';

    return 0;
}
