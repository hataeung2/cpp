# 레슨: 람다 캡처

캡처 방식 네 가지를 실행해서, closure가 무엇을 복사하고 무엇을 가리키는지 출력으로 확인합니다. 설명 표는 [유닛 README](../../../units/lambda_capture/README.md)에 있습니다.

## 실행
- 로컬: `cmake --build --preset <preset> --target lesson_lambda_capture` 후 `bin/lessons/lesson_lambda_capture` 실행, 또는 `ctest --preset <preset> -R lesson.lambda_capture`
- 웹 플레이그라운드(070-02): 레슨 트리에서 선택 후 Run

## 볼 것
- `second = first`로 복사한 counter는 `first`와 따로 셉니다(출력 `11, 12 / 11`).
- 참조로 캡처한 `add`는 `main`의 `total`을 바꿉니다.
- `unique_ptr`을 가진 closure는 `std::function`에는 담기지 않고 `std::move_only_function`에는 담깁니다.

## 연습
1. `makeCounterByValue`에서 `mutable`을 지우고 컴파일 오류 메시지를 읽어 보세요. 왜 `count`를 바꿀 수 없을까요?
2. 지역 변수를 참조로 캡처한 람다를 **반환**하는 함수를 하나 만들어 호출해 보고, 무엇이 dangling이 되는지 설명해 보세요. `linux-x64-asan` preset으로 빌드한 뒤 `ASAN_OPTIONS=detect_stack_use_after_return=1`을 주고 **실행**하면 ASan이 `stack-use-after-return`으로 알려 줍니다(빌드만으로는 드러나지 않습니다).
3. `holder`의 타입을 `std::function<int()>`로 바꾸면 어떤 오류가 나는지 확인하고, 이유를 적어 보세요.
