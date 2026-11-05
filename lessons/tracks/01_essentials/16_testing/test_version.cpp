/**
 * @file test_version.cpp
 * @brief 레슨 testing — Version 타입과 파서에 대한 GoogleTest 단위 테스트
 * @brief Lesson testing — GoogleTest unit tests for the Version type and parser
 *
 * TEST, EXPECT/ASSERT, TEST_P(표 기반 매개변수화 테스트), TEST_F(테스트 픽스처)의 작성법을 배운다
 * Teaches how to write TEST, EXPECT/ASSERT, TEST_P (table-driven parameterized tests), and TEST_F (test fixtures)
 */
#include <gtest/gtest.h>

#include <algorithm>
#include <array>
#include <span>
#include <string_view>
#include <vector>

#include "version.hpp"

namespace {

namespace core = atugcc::core;
using testing_lesson::newestVersion;
using testing_lesson::parseVersion;
using testing_lesson::Version;

// 점으로 구분된 3개 숫자를 올바르게 파싱하는지 검증한다
// Verifies that three numbers separated by dots are parsed correctly
TEST(ParseVersion, ReadsThreeNumbers) {
    const auto result = parseVersion("1.2.3");
    // [학습] 뒤따르는 코드에서 결과(*result)를 역참조하므로 실패 시 테스트를 즉시 중단하도록 ASSERT를 사용한다. EXPECT를 쓰면 실패 후에도 진행되어 미정의 동작(UB)이 발생한다
    // [Learn] Use ASSERT because the lines below dereference the result; with EXPECT a failure would go on to *result (undefined behaviour)
    ASSERT_TRUE(result) << "error: " << core::to_string(result.error());
    // [학습] unsigned와 int를 비교하면 gtest 템플릿 내부에서 -Wsign-compare 경고가 발생하므로 1이 아닌 1u를 지정한다 (이 프로젝트는 경고를 오류로 취급)
    // [Learn] Use 1u not 1: comparing unsigned with int is a -Wsign-compare warning inside the gtest template and this project treats warnings as errors
    EXPECT_EQ(result->major, 1u);
    EXPECT_EQ(result->minor, 2u);
    EXPECT_EQ(result->patch, 3u);
}

// [학습] 매개변수화 테스트(TEST_P): 하나의 검증 로직에 여러 테스트 케이스 데이터를 표(테이블) 형태로 주입한다
// [Learn] Parameterized tests (TEST_P): inject multiple test case inputs as a table into a single verification logic
// 문자열 리터럴은 정적 수명을 가지므로 std::string_view 매개변수가 댕글링되지 않는다
// String literals have static storage duration so a string_view parameter does not dangle
class ParseVersionRejects : public ::testing::TestWithParam<std::string_view> {};

// 잘못된 형식의 문자열이 주어졌을 때 파서가 거부하고 InvalidArgument 오류를 반환하는지 검증한다
// Verifies that the parser rejects malformed text and returns an InvalidArgument error
TEST_P(ParseVersionRejects, BadText) {
    const auto result = parseVersion(GetParam());
    ASSERT_FALSE(result) << "accepted: " << GetParam();
    EXPECT_EQ(result.error(), core::CoreError::InvalidArgument);
}

// [학습] 한 행마다 자체 이름을 가진 독립된 테스트 케이스가 생성된다 (예: Table/ParseVersionRejects.BadText/3)
// [Learn] One row = one test case with its own name (e.g. Table/ParseVersionRejects.BadText/3)
// 각 행의 입력: 빈 문자열, 2개 부분, 4개 부분, 비숫자 문자, 음수, 연속된 점, unsigned 범위 초과
// Input for each row: empty string, two parts, four parts, non-digit character, negative number, consecutive dots, unsigned range overflow
INSTANTIATE_TEST_SUITE_P(
    Table,
    ParseVersionRejects,
    ::testing::Values(
        "",
        "1.2",
        "1.2.3.4",
        "1.x.3",
        "-1.2.3",
        "1..3",
        "99999999999.0.0"
    )
);

// 버전 비교 시 사전순 문자열 비교가 아닌 각 숫자의 크기를 비교하는지 검증한다
// Verifies that version comparison compares numeric values rather than lexicographical text
TEST(VersionOrder, ComparesNumbersNotText) {
    const auto older = parseVersion("1.9.0");
    const auto newer = parseVersion("1.10.0");
    ASSERT_TRUE(older);
    ASSERT_TRUE(newer);
    EXPECT_LT(*older, *newer);
    // [학습] 매크로 전처리기가 중괄호 {} 내부의 쉼표를 매크로 인자 구분자로 취급하는 것을 방지하기 위해 추가 괄호가 필요하다
    // [Learn] The extra parentheses are needed because the preprocessor splits macro arguments at the commas inside {}
    EXPECT_EQ(*newer, (Version{1, 10, 0}));
    // 실패할 수 없는 줄이다: 글자로 비교하면 "1.9.0"이 "1.10.0"보다 크다는 사실을 보여 주려고 둔다. 그래서 Version은 숫자로 비교한다
    // This line cannot fail: it shows that as text "1.9.0" is greater than "1.10.0", which is why Version compares numbers
    EXPECT_GT(std::string_view{"1.9.0"}, std::string_view{"1.10.0"});
}

// [학습] 테스트 픽스처(TEST_F): 여러 테스트에서 공유하는 데이터 설정 로직을 캡슐화한다
// [Learn] Test fixture (TEST_F): encapsulates data setup logic shared across multiple tests
// [학습] GoogleTest는 각 TEST_F마다 새로운 픽스처 객체를 생성하므로 하나의 테스트가 releases_를 수정해도 다른 테스트에 영향을 주지 않는다
// [Learn] GoogleTest makes a new fixture object for every TEST_F, so one test changing releases_ cannot affect another
class ReleaseListTest : public ::testing::Test {
protected:
    void SetUp() override;
    std::vector<Version> releases_;
};

void ReleaseListTest::SetUp() {
    constexpr std::array<std::string_view, 3> kReleaseTexts = {"1.2.0", "1.10.0", "1.9.3"};
    for (const auto text : kReleaseTexts) {
        const auto result = parseVersion(text);
        // SetUp에서의 치명적 실패(FAIL)는 해당 테스트 본문의 실행을 건너뛰게 만든다
        // A fatal failure in SetUp skips the test body
        if (!result) {
            FAIL() << "cannot parse " << text;
        }
        releases_.push_back(*result);
    }
}

// 픽스처의 버전 목록에서 newestVersion이 가장 높은 버전을 반환하는지 검증한다
// Verifies that newestVersion returns the highest version in the fixture's release list
TEST_F(ReleaseListTest, NewestIsHighest) {
    const auto newest = newestVersion(releases_);
    ASSERT_TRUE(newest.has_value());
    EXPECT_EQ(*newest, (Version{1, 10, 0}));
}

// 픽스처의 버전 목록을 오름차순으로 정렬했을 때 가장 낮은 버전과 가장 높은 버전의 위치를 검증한다
// Verifies the positions of the lowest and highest versions when sorting the fixture's release list ascending
TEST_F(ReleaseListTest, SortsAscending) {
    std::ranges::sort(releases_);
    ASSERT_EQ(releases_.size(), 3u);
    EXPECT_EQ(releases_.front(), (Version{1, 2, 0}));
    EXPECT_EQ(releases_.back(), (Version{1, 10, 0}));
}

// 빈 버전 목록에 대해 newestVersion이 빈 std::optional(std::nullopt)을 반환하는지 검증한다
// Verifies that newestVersion returns an empty std::optional (std::nullopt) for an empty version span
TEST(NewestVersion, EmptyListHasNone) {
    EXPECT_FALSE(newestVersion(std::span<const Version>{}).has_value());
}

} // namespace
