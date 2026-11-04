/**
 * @file geometry.cpp
 * @brief 레슨 modules — 모듈 구현 유닛 (modules.geometry)
 * @brief Lesson modules — module implementation unit (modules.geometry)
 *
 * area, makeRect 및 detail::clampSide 함수의 실제 정의를 담고 있는 구현 유닛이다.
 * Implementation unit containing actual definitions of area, makeRect, and detail::clampSide.
 */
module;
// std::unexpected는 <expected>에서 직접 가져온다: import atugcc.core;는 표준 라이브러리 이름을 내보내지 않는다
// std::unexpected comes from <expected> directly: import atugcc.core; does not export standard library names
#include <expected>
module modules.geometry;

// 구현 유닛은 주 인터페이스의 모든 선언(비공개 선언 포함)을 보며, 수정 시 사용자 재컴파일 범위를 줄인다
// Implementation units see all declarations of the primary interface (including private ones) and reduce rebuild cascade on changes
// 주 인터페이스의 import atugcc.core;도 이 유닛에 그대로 적용되므로 CoreError, Expected를 쓸 수 있다
// The primary interface's import atugcc.core; applies to this unit as well, so CoreError and Expected are usable here

namespace {

// 사각형 변의 최대 허용 길이
// Maximum allowed length for a rectangle side
constexpr double kMaxSide = 1000.0;

} // namespace

namespace modules::geometry {

namespace detail {

// 변의 길이를 kMaxSide 이하로 제한한다
// Clamps the side length to kMaxSide or less
double clampSide(double side) {
    return side > kMaxSide ? kMaxSide : side;
}

} // namespace detail

// 사각형의 넓이를 계산한다
// Calculates the area of the rectangle
double area(const Rect& r) {
    return r.width * r.height;
}

// 너비와 높이를 검증하여 Rect 객체를 생성한다 (유효하지 않으면 CoreError 반환)
// Validates width and height to construct a Rect (returns CoreError on invalid input)
atugcc::core::Expected<Rect> makeRect(double width, double height) {
    if (width <= 0.0 || height <= 0.0) {
        return std::unexpected(atugcc::core::CoreError::InvalidArgument);
    }
    return Rect{detail::clampSide(width), detail::clampSide(height)};
}

} // namespace modules::geometry
