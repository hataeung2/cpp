# 레슨: 순회와 뷰 — raw loop에서 `std::ranges`로 (`ranges_views`)

물건 다섯 개(`name`, `price`, `stock`)에서 "재고가 있는 가장 싼 물건"을 찾는 일을 raw loop로 쓰고, 같은 일을 `std::ranges` 알고리즘과 프로젝션(`&Item::price`)으로 씁니다. 이어서 뷰 파이프라인(`filter | transform | take`), 뷰가 필요한 만큼만 계산한다는 것(지연 평가), C++23 뷰(`enumerate`, `zip`, `chunk`, `slide`, `split`, `fold_left`, `ranges::to`), 그리고 임시 컨테이너에서 생기는 수명 문제를 `std::ranges::dangling`과 `owning_view`로 봅니다.

## 예전 방식과 C++20/23
| | 예전 방식 | `std::ranges` |
|---|---|---|
| 찾기·정렬 | `for` 루프, `std::sort(v.begin(), v.end(), [](auto& a, auto& b) { return a.price < b.price; })` | `std::ranges::sort(items, {}, &Item::price)`: 범위 하나와 프로젝션 |
| 걸러서 바꾸기 | 중간 벡터를 만드는 루프 | `items \| views::filter(…) \| views::transform(…)`: 중간 벡터 없음, 순회할 때 계산 |
| 앞의 N개 | 카운터와 `break` | `views::take(N)`: 필요한 만큼만 계산 |
| 번호·짝·묶음 | 인덱스 변수 | C++23 `views::enumerate`, `zip`, `chunk`, `slide` |
| 벡터로 모으기 | `push_back` 루프 | C++23 `std::ranges::to<std::vector>(view)` |
| 임시 객체의 반복자 | 컴파일되고 실행 중에 깨짐 | 결과 타입이 `std::ranges::dangling`: 역참조하면 컴파일 오류 |

## 실행
- 웹 플레이그라운드: 레슨 트리에서 선택 후 Run
- 로컬: `cmake --build --preset <preset> --target lesson_ranges_views` 후 `bin/lessons/lesson_ranges_views`, 또는 `ctest --preset <preset> -R lesson.ranges_views`

## 볼 것
- 1단계: raw loop와 `ranges::min_element`가 같은 답(`eggs`)을 냅니다. `min_element`에 넘긴 걸러진 뷰는 이름 있는 변수입니다. `filter_view`는 빌린 범위(borrowed range)가 아니므로, 임시 뷰에 부르면 결과가 `dangling`이 됩니다(5단계). 그 뒤 `ranges::sort`가 `items`를 가격순으로 바꿉니다.
- 2단계: 파이프라인은 왼쪽에서 오른쪽으로 읽습니다. 재고 있음 → 이름 → 앞의 세 개.
- 3단계: `pipeline built, nothing ran yet`이 `transform(...)` 줄보다 먼저 나옵니다. 뷰를 만드는 것만으로는 아무것도 계산하지 않습니다. 순회할 때 `take(2)`가 두 개를 받으면 멈추므로, 변환 람다는 재고 있는 앞의 두 물건에 대해서만 불립니다.
- 4단계: `ranges::to`가 파이프라인 결과를 `std::vector<std::string>`으로 모읍니다. `enumerate`는 번호와 요소, `zip`은 두 범위의 짝, `chunk(2)`는 겹치지 않는 묶음, `slide(2)`는 겹치는 창입니다. `split(',')`의 각 부분은 원래 `std::string_view`를 가리키므로 그 문자열이 살아 있는 동안만 씁니다.
- 5단계: 임시 벡터에 `ranges::find`를 부르면 반복자 대신 `std::ranges::dangling`이 돌아옵니다. 벡터가 그 문장 끝에서 사라지기 때문입니다. 반대로 임시 벡터에 뷰를 붙이면(`makeNumbers() | views::transform(…)`) `owning_view`가 벡터를 옮겨 가지므로 안전하게 순회할 수 있습니다. 이름 있는 벡터에는 `ref_view`(참조)가 붙습니다.

C++23에는 파이프 형식 `v | std::ranges::to<std::vector>()`와 범위 포맷 `std::format("{}", view)`도 있습니다. 둘 다 MSVC에서는 되지만 Linux 툴체인(Clang 20 + libstdc++ 14.2)에서는 빌드되지 않아 레슨 코드는 호출 형식 `ranges::to`와 요소별 `std::format`을 씁니다([KI-033](/docs/known_issues.md)).

```cpp
auto names = items | views::transform(&Item::name) | std::ranges::to<std::vector>();
std::cout << std::format("{}\n", names);   // ["dates", "eggs", ...]
```

## 연습
1. 3단계에서 `views::take(2)`를 지우고 실행해 보세요. 변환 람다가 몇 번 불리나요? 재고 없는 물건에 대해서는 왜 한 번도 불리지 않나요?
2. 5단계 아래에 `auto it = std::ranges::find(makeNumbers(), 8); std::cout << *it;`를 더하고 빌드해 보세요. 컴파일 오류가 어떤 타입을 말하나요? 같은 일을 `std::find(v.begin(), v.end(), 8)` 시절에는 무엇이 막아 주었나요?
3. MSVC를 쓸 수 있다면 위 코드처럼 파이프 형식 `| std::ranges::to<std::vector>()`와 `std::format("{}", view)`를 써 보세요. Linux preset에서는 어떤 오류가 나는지도 확인하세요.
