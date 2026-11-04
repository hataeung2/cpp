/**
 * @file main.cpp
 * @brief 레슨 modules — C++20 모듈 인터페이스, 파티션, 구현 유닛과 import atugcc.core
 * @brief Lesson modules — C++20 module interfaces, partitions, implementation units, and import atugcc.core
 *
 * 모듈 분할(인터페이스, 파티션, 구현 유닛)과 라이브러리 import, 매크로 격리를 출력으로 확인한다.
 * Demonstrates module division (interface, partition, implementation unit), library imports, and macro isolation.
 */
#include <format>
#include <iostream>

// 한 소스 파일 내에서 모든 #include 는 모든 import 보다 앞에 와야 한다 (impl.md §2a)
// Within a single source file, every #include must come before every import (impl.md §2a)
import modules.geometry;
import atugcc.core;

int main() {
    // 1. 모듈 import: modules.geometry 모듈의 export 된 함수와 타입을 사용한다
    // 1. Import a module: use exported functions and types from modules.geometry
    std::cout << std::format("== 1. import a module ==\n");
    const auto rectResult = modules::geometry::makeRect(3.0, 4.0);
    if (!rectResult) {
        std::cout << std::format("makeRect(3, 4) failed: {}\n", atugcc::core::to_string(rectResult.error()));
        return 1;
    }
    const auto& rect = *rectResult;
    std::cout << std::format(
        "makeRect(3, 4) -> area = {} (area is defined in geometry.cpp, an implementation unit)\n",
        modules::geometry::area(rect));

    // 2. 파티션 재내보내기: 주 인터페이스가 export import :rect 한 함수를 호출한다
    // 2. Partition re-exported: call function from :rect re-exported by the primary interface
    std::cout << std::format("== 2. partition re-exported ==\n");
    std::cout << std::format(
        "describe(rect) -> {} (describe lives in the partition :rect)\n",
        modules::geometry::describe(rect));

    // 3. 매크로는 import 되지 않음: geometry.cppm 에서 정의한 매크로는 main.cpp 로 전달되지 않는다
    // 3. Macros do not cross import: macros defined in geometry.cppm do not leak into main.cpp
    std::cout << std::format("== 3. macros do not cross import ==\n");
#ifdef GEOMETRY_UNIT_CM
    std::cout << std::format("GEOMETRY_UNIT_CM is defined in main.cpp\n");
#else
    std::cout << std::format("GEOMETRY_UNIT_CM is not defined in main.cpp\n");
#endif

    // 4. atugcc.core import: geometry 의 import atugcc.core 는 re-export 되지 않으므로 직접 import 해야 한다
    // 4. Import atugcc.core: geometry's import atugcc.core is not re-exported, so main.cpp imports it directly
    std::cout << std::format("== 4. import atugcc.core ==\n");
    const auto invalidResult = modules::geometry::makeRect(-1.0, 2.0);
    if (!invalidResult) {
        std::cout << std::format(
            "makeRect(-1, 2) -> error: {}\n",
            atugcc::core::to_string(invalidResult.error()));
    }
    std::cout << std::format("main.cpp imports atugcc.core itself: geometry's import is not re-exported\n");

    return 0;
}
