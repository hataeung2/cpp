# 사용법 — RelWithDebInfo 빌드, 크래시 덤프 생성, 심볼화

목적
- RelWithDebInfo 빌드로 디버그 심볼(PDB)을 생성하고, 샘플 실행으로 즉시 덤프를 만들며, 제공된 심볼러로 덤프의 IP를 소스 라인으로 매핑하는 절차를 문서화합니다.

전제 조건
- Windows (Visual Studio Build Tools / MSVC 설치)
- CMake (프리셋/명시적 경로 사용 가능)
- vcpkg가 `C:/vcpkg`에 설치되어 있고 `CMakePresets.json`의 `toolchainFile` 항목이 동일하게 설정되어 있음
- (권장) Visual Studio 개발자 명령 프롬프트 또는 PowerShell에서 실행

1) RelWithDebInfo 빌드
- 예시(명시적 CMake 경로 사용):
```powershell
$cmake = 'C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe'
New-Item -ItemType Directory -Force out\windows\x64\relwithdebinfo
& $cmake -S . -B out\windows\x64\relwithdebinfo -A x64 -DCMAKE_BUILD_TYPE=RelWithDebInfo -DCMAKE_TOOLCHAIN_FILE='C:/vcpkg/scripts/buildsystems/vcpkg.cmake' -DVCPKG_TARGET_TRIPLET='x64-windows'
& $cmake --build out\windows\x64\relwithdebinfo --config RelWithDebInfo
```
- 빌드 결과(예):
  - `out\windows\x64\relwithdebinfo\bin\RelWithDebInfo\atugcc_sample.exe`
  - `out\windows\x64\relwithdebinfo\bin\RelWithDebInfo\atugcc_sample.pdb`
  - `out\windows\x64\relwithdebinfo\RelWithDebInfo\symbolize_dump.exe`

2) 덤프 파일 준비 및 충돌 트리거
- 준비 및 트리거(샘플 실행):
```powershell
out\windows\x64\relwithdebinfo\bin\RelWithDebInfo\atugcc_sample.exe --prepare-dump log\manual_crash2.bin --trigger-segfault
```
- 기대 출력 예시:
  - "Prepared dump HANDLE at: \"log\\manual_crash2.bin\""
  - "Triggering access violation to exercise crash handler..."
  - "program crashed!"
- 생성된 덤프: `log\manual_crash2.bin` (UTF-8 텍스트 헤더 + `--CONTEXT-BINARY--` + CONTEXT 구조체 및 `--MODULES--` 기록 포함)

3) 덤프 심볼화 (심볼 매핑)
- 제공된 심볼러 사용 예:
```powershell
out\windows\x64\relwithdebinfo\RelWithDebInfo\symbolize_dump.exe log\manual_crash2.bin out\windows\x64\relwithdebinfo\bin\RelWithDebInfo\atugcc_sample.exe
```
- 성공 시 출력 예시:
  - `Context IP: 0x7ff778fff333`
  - `Recorded module base: 0x7ff778fb0000`
  - `Recorded module filename: Z:\cpp\out\windows\x64\relwithdebinfo\bin\RelWithDebInfo\atugcc_sample.exe`
  - `Symbol: main + 0xa63`
  - `Source: Z:\cpp\main.cpp:266`
- 설명: 심볼러는 덤프에 기록된 CONTEXT에서 IP를 읽고, 덤프에 기록된 모듈 base와 실행파일 경로를 이용해 `SymLoadModuleEx`로 모듈을 로드한 뒤 `SymFromAddr`/`SymGetLineFromAddr64`로 심볼과 소스 라인을 출력합니다.

4) 문제 해결 팁
- `SymFromAddr failed: 126` 같은 오류가 나오면:
  - 덤프에 `--CONTEXT-BINARY--` 및 `--MODULES--` 섹션이 있는지 확인하세요.
  - PDB 파일이 빌드 출력 폴더에 있는지 확인하세요 (`*.pdb`).
  - `symbolize_dump.exe`가 같은 머신에서 실행되어야 하며 DbgHelp로 심볼을 로드할 수 있어야 합니다.
- 덤프의 헤더/블록을 빠르게 확인하려면 프로젝트의 파서 사용:
```powershell
python scripts/parse_dump.py log\manual_crash2.bin --block-size 128 --show 5
```

5) Visual Studio / WinDbg로 확인하기
- 이 덤프는 Windows 미니덤프 포맷이 아니므로 Visual Studio에서 바로 열 수는 없습니다. 대신 다음을 권장합니다:
  - `atugcc_sample.exe`와 해당 `atugcc_sample.pdb`를 Visual Studio에 로드(또는 심볼 경로로 지정)한 뒤, 덤프에서 얻은 IP를 주소로 조회하여 소스 위치 확인
  - 또는 WinDbg에서 실행 파일과 PDB를 로드한 뒤 `ln <address>`로 심볼/라인을 조회
- 더 간단한 방법: 위 `symbolize_dump.exe`를 사용하면 PDB를 자동으로 참조해 소스라인을 출력합니다.

6) 파일 위치(요약)
- 빌드 출력: `out/windows/x64/relwithdebinfo/bin/RelWithDebInfo/atugcc_sample.exe`
- PDB: `out/windows/x64/relwithdebinfo/bin/RelWithDebInfo/atugcc_sample.pdb`
- 심볼러: `out/windows/x64/relwithdebinfo/RelWithDebInfo/symbolize_dump.exe`
- 덤프(예): `log/manual_crash2.bin`

7) 참고
- 이 저장소의 파서: `scripts/parse_dump.py` (덤프 헤더 + 고정 블록 파싱)
- 덤프 포맷: 텍스트 헤더, `--BINARY-BLOCKS--`, 블록(기본 128바이트), 임의 순서의 `--CONTEXT-BINARY--` 및 `--MODULES--`(모듈베이스+UTF-8 경로)

