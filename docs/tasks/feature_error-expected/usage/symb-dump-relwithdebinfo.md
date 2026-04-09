# 사용법 — RelWithDebInfo 빌드, 크래시 덤프 생성, 심볼화 (Windows / Linux / WSL)

목적
- RelWithDebInfo 빌드로 디버그 심볼 정보를 포함한 바이너리를 만들고,
- 샘플 실행으로 덤프를 생성한 뒤,
- tools/symbolize_dump.py로 IP를 함수/소스 라인으로 매핑하는 과정을 Windows와 Linux/WSL 공통으로 정리합니다.

전제 조건
- 공통
  - CMake 사용 가능
  - 저장소 루트에서 작업
  - vcpkg를 사용하는 경우 CMakePresets.json의 toolchainFile이 로컬 경로와 일치
- Windows
  - Visual Studio Build Tools 또는 MSVC 툴체인
  - PowerShell 또는 개발자 명령 프롬프트
- Linux/WSL
  - C++ 빌드 도구체인(g++, make 또는 ninja)
  - python3
  - addr2line 포함(binutils)
- WSL 경로
  - Windows 저장소 E:\cpp는 WSL에서 /mnt/e/cpp

1) RelWithDebInfo 빌드

Windows 예시
```powershell
$cmake = 'C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe'
New-Item -ItemType Directory -Force out\windows\x64\relwithdebinfo
& $cmake -S . -B out\windows\x64\relwithdebinfo -A x64 -DCMAKE_BUILD_TYPE=RelWithDebInfo -DCMAKE_TOOLCHAIN_FILE='C:/vcpkg/scripts/buildsystems/vcpkg.cmake' -DVCPKG_TARGET_TRIPLET='x64-windows'
& $cmake --build out\windows\x64\relwithdebinfo --config RelWithDebInfo
```

Linux/WSL 예시
```bash
cmake -S . -B out/linux/x64/relwithdebinfo -DCMAKE_BUILD_TYPE=RelWithDebInfo
cmake --build out/linux/x64/relwithdebinfo -j
```

2) 덤프 파일 준비 및 충돌 트리거

Windows 예시
```powershell
out\windows\x64\relwithdebinfo\bin\RelWithDebInfo\atugcc_sample.exe --prepare-dump log\manual_crash2.bin --trigger-segfault
```

Linux/WSL 예시
```bash
./out/linux/x64/relwithdebinfo/bin/atugcc_sample --prepare-dump log/manual_crash2.bin --trigger-segfault
```

기대 출력 예시
- Prepared dump HANDLE at: "log/manual_crash2.bin"
- Triggering access violation to exercise crash handler...
- program crashed!

생성된 덤프
- log/manual_crash2.bin
- 포맷: UTF-8 헤더 + --BINARY-BLOCKS-- + (옵션) --CONTEXT-BINARY-- + (옵션) --MODULES--

3) 덤프 심볼화

Windows에서 실행
```powershell
python tools\symbolize_dump.py log\manual_crash2.bin out\windows\x64\relwithdebinfo\bin\RelWithDebInfo\atugcc_sample.exe
```

Linux/WSL에서 실행
```bash
python3 tools/symbolize_dump.py log/manual_crash2.bin out/linux/x64/relwithdebinfo/bin/atugcc_sample
```

WSL에서 Windows 빌드 결과를 해석하는 예시
```bash
cd /mnt/e/cpp
python3 tools/symbolize_dump.py log/manual_crash2.bin out/windows/x64/relwithdebinfo/bin/RelWithDebInfo/atugcc_sample.exe
```

성공 시 출력 예시
- Context IP: 0x7ff778fff333
- Recorded module base: 0x7ff778fb0000
- Using exe: Z:\cpp\out\windows\x64\relwithdebinfo\bin\RelWithDebInfo\atugcc_sample.exe
- Symbol: main + 0xa63
- Source: Z:\cpp\main.cpp:266

4) 문제 해결
- No context marker found in dump
  - 덤프에 --CONTEXT-BINARY--가 없습니다. 덤프 생성 경로와 옵션을 확인하세요.
- SymFromAddr failed: 126 (Windows)
  - PDB 로드 실패 가능성이 큽니다. exe/PDB 쌍, 경로 접근성, 빌드 타입(RelWithDebInfo)을 확인하세요.
- addr2line not found (Linux/WSL)
  - binutils 설치가 필요합니다.

덤프 구조 빠른 확인
```powershell
python scripts\parse_dump.py log\manual_crash2.bin --block-size 128 --show 5
```

5) 파일 위치 요약
- Windows exe: out/windows/x64/relwithdebinfo/bin/RelWithDebInfo/atugcc_sample.exe
- Windows pdb: out/windows/x64/relwithdebinfo/bin/RelWithDebInfo/atugcc_sample.pdb
- Linux exe: out/linux/x64/relwithdebinfo/bin/atugcc_sample
- 덤프 예시: log/manual_crash2.bin

6) 참고
- 상세 심볼러 설명: docs/tasks/feature_error-expected/usage/symbolize_dump_cross_platform.md
- 덤프 파서: scripts/parse_dump.py
