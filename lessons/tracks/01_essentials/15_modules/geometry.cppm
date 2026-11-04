/**
 * @file geometry.cppm
 * @brief 레슨 modules — 주 모듈 인터페이스 유닛 (modules.geometry)
 * @brief Lesson modules — primary module interface unit (modules.geometry)
 *
 * modules.geometry 주 모듈 인터페이스로, :rect 파티션을 re-export 하고 공개 함수를 선언한다.
 * Primary module interface of modules.geometry, re-exporting the :rect partition and declaring public functions.
 */
export module modules.geometry;

// 파티션을 re-export 하여 modules.geometry 를 import 하는 사용자에게 Rect 와 describe 를 함께 공개한다
// Re-exports the partition so users importing modules.geometry also get Rect and describe
export import :rect;

// 라이브러리를 import 하되 export 하지 않으므로 import 가 외부로 전이되지 않는다
// Imports the library without exporting it, so the import is non-transitive to external importers
import atugcc.core;

// 모듈은 매크로를 export 하지 않으므로 이 매크로는 모듈 외부로 전달되지 않는다
// Modules never export macros, so this macro does not leak outside the module
#define GEOMETRY_UNIT_CM 1

export namespace modules::geometry {

// 사각형의 넓이를 계산한다 (정의는 구현 유닛 geometry.cpp 에 위치)
// Calculates the area of the rectangle (defined in implementation unit geometry.cpp)
[[nodiscard]] double area(const Rect& r);

// 너비와 높이를 검증하여 Rect 객체를 생성한다 (유효하지 않으면 CoreError 반환)
// Validates width and height to construct a Rect (returns CoreError on invalid input)
[[nodiscard]] atugcc::core::Expected<Rect> makeRect(double width, double height);

} // namespace modules::geometry

namespace modules::geometry::detail {

// 변의 길이를 최대 허용치 이하로 제한한다 (export 되지 않아 모듈 외부에 노출되지 않음)
// Clamps side length to maximum allowed value (not exported, so not visible outside the module)
[[nodiscard]] double clampSide(double side);

} // namespace modules::geometry::detail
