/**
 * @file main.cpp
 * @brief 레슨 ranges_views — raw loop에서 std::ranges 알고리즘과 뷰 파이프라인으로
 * @brief Lesson ranges_views — from raw loops to std::ranges algorithms and view pipelines
 *
 * std::ranges 알고리즘의 프로젝션과 뷰 파이프라인의 지연 평가를 살펴본다
 * Examine std::ranges algorithm projections and lazy evaluation in view pipelines
 * C++23에 추가된 뷰와 dangling 반복자 방지 및 owning_view를 확인한다
 * Explore C++23 views alongside dangling iterator protection and owning_view
 */
#include <algorithm>
#include <concepts>
#include <format>
#include <functional>
#include <iostream>
#include <ranges>
#include <string>
#include <string_view>
#include <vector>

namespace views = std::views;

namespace {

struct Item {
    std::string name;
    int price;
    int stock;
};

// dangling 및 owning_view 검사를 위한 임시 벡터를 반환한다
// Returns a temporary vector to inspect dangling and owning_view
[[nodiscard]] std::vector<int> makeNumbers() {
    return {5, 3, 8};
}

} // namespace

int main() {
    std::vector<Item> items{
        {"apple", 300, 4},
        {"bread", 250, 0},
        {"cheese", 900, 2},
        {"dates", 120, 0},
        {"eggs", 200, 6},
    };

    auto inStock = [](const Item& item) {
        return item.stock > 0;
    };

    std::cout << "== 1. raw loop vs ranges algorithms ==\n";
    // raw loop: 재고가 있는 항목 중 가장 저렴한 물건을 직접 순회하며 찾는다
    // Raw loop: traverse items directly to find the cheapest in-stock product
    const Item* cheapest = nullptr;
    for (const auto& item : items) {
        if (inStock(item)) {
            if (!cheapest || item.price < cheapest->price) {
                cheapest = &item;
            }
        }
    }
    if (cheapest != nullptr) {
        std::cout << std::format("raw loop: cheapest in stock = {} ({})\n",
                                 cheapest->name, cheapest->price);
    }

    // std::ranges 알고리즘: 프로젝션(&Item::price)으로 멤버 함수나 멤버 변수를 지정한다
    // std::ranges algorithms: specify member variables or accessors via projections (&Item::price)
    // filter_view 는 borrowed_range 가 아니므로 임시 뷰를 넘기면 dangling 이 된다 (이름 있는 변수 사용)
    // filter_view is not a borrowed_range, so passing a temporary would produce dangling (use named variable)
    auto inStockItems = items | views::filter(inStock);
    const auto minIt = std::ranges::min_element(inStockItems, {}, &Item::price);
    if (minIt != inStockItems.end()) {
        std::cout << std::format("ranges::min_element: cheapest in stock = {} ({})\n",
                                 minIt->name, minIt->price);
    }

    // std::ranges::sort 로 원본 벡터를 가격 오름차순으로 정렬한다
    // Sort original vector in ascending order of price using std::ranges::sort
    std::ranges::sort(items, {}, &Item::price);
    // filter_view 는 begin() 을 캐시하므로 원본 컨테이너가 변경된 뒤 재사용하지 않는다
    // filter_view caches its begin(), so do not reuse it after modifying the underlying container
    std::string sortedNames;
    for (const auto& item : items) {
        if (!sortedNames.empty()) {
            sortedNames += ", ";
        }
        sortedNames += item.name;
    }
    std::cout << std::format("sorted by price: {}\n", sortedNames);

    std::cout << "== 2. a view pipeline ==\n";
    // filter, transform, take 어댑터를 파이프 연산자(|)로 합성하여 뷰를 구성한다
    // Compose filter, transform, and take adaptors into a view pipeline using the pipe operator (|)
    auto pipeline = items | views::filter(inStock) | views::transform(&Item::name) | views::take(3);
    std::string pipelineResult;
    for (const auto& name : pipeline) {
        if (!pipelineResult.empty()) {
            pipelineResult += ", ";
        }
        pipelineResult += name;
    }
    std::cout << std::format("in stock, cheapest first: {}\n", pipelineResult);

    std::cout << "== 3. lazy evaluation ==\n";
    // 변환 람다가 호출되는 시점을 추적하기 위해 호출될 때마다 화면에 출력한다
    // Print to stdout whenever the transform lambda is invoked to trace evaluation timing
    auto noisy = [](const Item& item) -> const std::string& {
        std::cout << std::format("  transform({})\n", item.name);
        return item.name;
    };

    // 파이프라인을 구성하는 시점에는 요소 평가나 변환 연산이 전혀 실행되지 않는다
    // Creating the pipeline performs no element evaluation or transformation yet
    auto lazyPipeline = items | views::filter(inStock) | views::transform(noisy) | views::take(2);
    std::cout << "pipeline built, nothing ran yet\n";

    // 뷰를 순회할 때 필요한 요소만 지연 평가된다 (take(2)로 인해 2개만 변환됨)
    // Elements are lazily evaluated on demand as the view is traversed (take(2) stops after 2)
    std::string lazyResult;
    for (const auto& name : lazyPipeline) {
        if (!lazyResult.empty()) {
            lazyResult += ", ";
        }
        lazyResult += name;
    }
    std::cout << std::format("result: {}\n", lazyResult);

    std::cout << "== 4. C++23 views ==\n";
    // std::ranges::to 호출 형식으로 뷰의 결과를 std::vector 컨테이너에 즉시 실체화한다
    // Materialize the view into a std::vector container using call-syntax std::ranges::to
    // 참고: 파이프 형식(| std::ranges::to<std::vector>())과 range 포맷은 README에서 다룬다
    // Note: Pipe syntax (| std::ranges::to<std::vector>()) and range formatting are covered in README
    const auto names = std::ranges::to<std::vector>(
        items | views::filter(inStock) | views::transform(&Item::name));
    const auto prices = std::ranges::to<std::vector>(
        items | views::filter(inStock) | views::transform(&Item::price));
    std::cout << std::format("ranges::to: {} names in a std::vector<std::string>\n",
                             names.size());

    // views::enumerate: 각 요소에 0부터 시작하는 인덱스를 쌍으로 부여한다
    // views::enumerate: pairs each element with a zero-based index
    std::string enumStr;
    for (const auto [index, name] : views::enumerate(names)) {
        if (!enumStr.empty()) {
            enumStr += ", ";
        }
        enumStr += std::format("{} {}", index, name);
    }
    std::cout << std::format("enumerate: {}\n", enumStr);

    // views::zip: 두 개 이상의 범위를 하나로 묶어 튜플 형태의 참조로 순회한다
    // views::zip: combines multiple ranges into tuple-like references for simultaneous iteration
    std::string zipStr;
    for (const auto& [name, price] : views::zip(names, prices)) {
        if (!zipStr.empty()) {
            zipStr += ", ";
        }
        zipStr += std::format("{}={}", name, price);
    }
    std::cout << std::format("zip: {}\n", zipStr);

    const std::vector<int> numbers{1, 2, 3, 4, 5, 6, 7};

    // views::chunk: 지정한 크기 단위로 겹치지 않게 하위 범위를 분할한다
    // views::chunk: divides a range into non-overlapping subranges of the given size
    std::string chunkStr;
    for (const auto chunk : numbers | views::chunk(2)) {
        if (!chunkStr.empty()) {
            chunkStr += ' ';
        }
        chunkStr += '[';
        bool first = true;
        for (const int n : chunk) {
            if (!first) {
                chunkStr += ' ';
            }
            chunkStr += std::to_string(n);
            first = false;
        }
        chunkStr += ']';
    }
    std::cout << std::format("chunk(2): {}\n", chunkStr);

    // views::slide: 지정한 크기의 슬라이딩 윈도우로 연속된 부분 범위를 순회한다
    // views::slide: iterates with a sliding window of the specified size over contiguous subranges
    std::string slideStr;
    for (const auto window : numbers | views::slide(2)) {
        if (!slideStr.empty()) {
            slideStr += ' ';
        }
        slideStr += '[';
        bool first = true;
        for (const int n : window) {
            if (!first) {
                slideStr += ' ';
            }
            slideStr += std::to_string(n);
            first = false;
        }
        slideStr += ']';
    }
    std::cout << std::format("slide(2): {}\n", slideStr);

    // views::split: 구분자로 문자열을 분할하며, 결과는 원본 문자열의 수명에 의존한다
    // views::split: splits a string by a delimiter; results depend on the lifetime of the underlying string
    const std::string_view csv = "a,b,c";
    std::string splitStr;
    for (const auto part : csv | views::split(',')) {
        if (!splitStr.empty()) {
            splitStr += " | ";
        }
        splitStr += std::string_view(part);
    }
    std::cout << std::format("split(','): {}\n", splitStr);

    // std::ranges::fold_left: 초기값과 이항 연산자로 범위를 왼쪽에서 오른쪽으로 축약한다
    // std::ranges::fold_left: reduces a range from left to right using an initial value and binary op
    const auto sum = std::ranges::fold_left(numbers, 0, std::plus{});
    std::cout << std::format("fold_left(numbers, 0, std::plus{{}}) = {}\n", sum);

    std::cout << "== 5. dangling and owning_view ==\n";
    // 임시 컨테이너에 대해 반복자를 반환하는 알고리즘을 호출하면 std::ranges::dangling 이 반환된다
    // Calling an algorithm that returns an iterator on a temporary produces std::ranges::dangling
    using FindOnTemporary = decltype(std::ranges::find(makeNumbers(), 8));
    static_assert(std::same_as<FindOnTemporary, std::ranges::dangling>);
    std::cout << std::format("find on a temporary vector returns std::ranges::dangling: {}\n",
                             std::same_as<FindOnTemporary, std::ranges::dangling>);

    // lvalue 컨테이너에 views::all 을 적용하면 ref_view 가 되고, 임시 객체는 owning_view 가 된다
    // Applying views::all to an lvalue yields ref_view, while a temporary container becomes owning_view
    std::cout << std::format(
        "views::all(lvalue vector) is ref_view: {}\n",
        std::same_as<std::views::all_t<std::vector<int>&>,
                     std::ranges::ref_view<std::vector<int>>>);
    std::cout << std::format(
        "views::all(temporary vector) is owning_view: {}\n",
        std::same_as<std::views::all_t<std::vector<int>>,
                     std::ranges::owning_view<std::vector<int>>>);

    // owning_view 가 임시 벡터를 내부로 이동(소유)하므로 뷰 파이프라인을 안전하게 순회할 수 있다
    // owning_view takes ownership (moves) of the temporary vector, making pipeline traversal safe
    auto doubled = makeNumbers() | views::transform([](int x) { return x * 2; });
    std::string doubledStr;
    for (const int val : doubled) {
        if (!doubledStr.empty()) {
            doubledStr += ' ';
        }
        doubledStr += std::to_string(val);
    }
    std::cout << std::format("doubled (the view owns the vector): {}\n", doubledStr);

    return 0;
}
