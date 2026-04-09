# symbolize_dump.py 공용 사용 가이드 (Windows / Linux / WSL)

목적
- 커스텀 크래시 덤프 파일에서 IP를 읽어 심볼/소스 라인으로 매핑하는 도구 tools/symbolize_dump.py의 공용 사용법을 정리합니다.

지원 플랫폼과 동작 방식
- Windows
  - DbgHelp API를 ctypes로 호출해 PDB 기반 심볼과 라인을 조회합니다.
  - 내부적으로 SymLoadModuleEx, SymFromAddr, SymGetLineFromAddr64를 사용합니다.
- Linux/WSL/macOS
  - addr2line -f -C를 호출해 심볼과 소스 라인을 조회합니다.
  - 덤프에 기록된 모듈 베이스가 있으면 IP에서 베이스를 빼서 상대 주소로 변환합니다.

입력 형식
- 명령: python tools/symbolize_dump.py <dump-file> <exe-path>
- dump-file
  - 크래시 핸들러가 생성한 바이너리 덤프 경로
  - 덤프 내에 --CONTEXT-BINARY--, --MODULES-- 섹션이 있어야 정확한 매핑이 가능합니다.
- exe-path
  - 심볼 해석 대상 실행 파일 경로
  - Windows에서는 해당 exe와 매칭되는 PDB가 접근 가능해야 합니다.

Windows 사용 예시
```powershell
python tools\symbolize_dump.py log\manual_crash2.bin out\windows\x64\relwithdebinfo\bin\RelWithDebInfo\atugcc_sample.exe
```

Linux 사용 예시
```bash
python3 tools/symbolize_dump.py log/manual_crash2.bin out/linux/x64/relwithdebinfo/bin/atugcc_sample
```

WSL 사용 예시
- 저장소가 E:\cpp라면 WSL 경로는 /mnt/e/cpp 입니다.
```bash
cd /mnt/e/cpp
python3 tools/symbolize_dump.py log/manual_crash2.bin out/windows/x64/relwithdebinfo/bin/RelWithDebInfo/atugcc_sample.exe
```

출력 예시
```text
Context IP: 0x7ff778fff333
Recorded module base: 0x7ff778fb0000
Using exe: Z:\cpp\out\windows\x64\relwithdebinfo\bin\RelWithDebInfo\atugcc_sample.exe
Symbol: main + 0xa63
Source: Z:\cpp\main.cpp:266
```

필수 점검 사항
- 덤프 파일에 --CONTEXT-BINARY-- 섹션이 존재해야 합니다.
- 모듈 베이스/경로를 안정적으로 쓰려면 --MODULES-- 섹션도 있어야 합니다.
- Windows
  - DbgHelp.dll 사용 가능 환경이어야 합니다.
  - exe와 맞는 PDB를 찾을 수 있어야 합니다.
- Linux/WSL
  - addr2line 설치 필요 (binutils 패키지)

자주 발생하는 오류
- No context marker found in dump
  - 덤프가 잘못 생성되었거나 포맷이 다릅니다.
- SymFromAddr failed: 126
  - PDB 로드 실패 가능성이 큽니다. exe/PDB 쌍과 접근 경로를 확인하세요.
- addr2line not found
  - Linux/WSL에서 binutils를 설치하세요.

덤프 내용 빠른 점검
```powershell
python scripts\parse_dump.py log\manual_crash2.bin --block-size 128 --show 5
```

관련 파일
- 심볼러: tools/symbolize_dump.py
- 덤프 파서: scripts/parse_dump.py
