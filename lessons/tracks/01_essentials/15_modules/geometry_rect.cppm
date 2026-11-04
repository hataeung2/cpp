/**
 * @file geometry_rect.cppm
 * @brief 레슨 modules — 모듈 파티션 인터페이스 유닛 (:rect)
 * @brief Lesson modules — module partition interface unit (:rect)
 *
 * Rect 구조체와 describe 인라인 함수를 제공하는 모듈 파티션이다.
 * A module partition providing the Rect struct and the inline describe function.
 */
module;

#include <format>
#include <string>

// 모듈 파티션 인터페이스 유닛 선언: modules.geometry 모듈의 :rect 파티션
// Module partition interface unit declaration: :rect partition of modules.geometry module
export module modules.geometry:rect;

export namespace modules::geometry {

// 2차원 사각형을 나타내는 구조체
// Struct representing a 2D rectangle
struct Rect {
    double width{0.0};
    double height{0.0};
};

// 파티션은 주 모듈 인터페이스를 import 할 수 없으므로(순환 종속 방지), Rect 를 사용하는 describe 함수를 파티션 안에 인라인으로 정의한다
// Because a partition cannot import the primary module interface (prevents circular dependency), describe which uses Rect is defined inline within the partition
[[nodiscard]] inline std::string describe(const Rect& r) {
    return std::format("Rect {} x {}", r.width, r.height);
}

} // namespace modules::geometry
