# 1. 빌드 (CMakePresets 사용)
"C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe" --build --preset windows-x64-debug
=> vscode에서 제공하는 cmake 확장(CMakePresets.json)으로 실행 및 관리 중입니다. 빌드 결과물은 `/out/windows/x64/debug` 하위에 저장됩니다.

# 2. 단위 테스트
z:\cpp\out\windows\x64\debug\bin\atugcc_tests.exe
=>@[z:\cpp\tests\CMakeLists.txt:L2] 이 파일로 exe 생성.
