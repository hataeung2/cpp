# atugcc 플레이그라운드

## 여기는
atugcc 저장소의 `lessons/` 폴더를 브라우저에서 고치고, 빌드하고, 실행하는 **로컬 페이지**입니다.
- 따로 복사해 둔 파일이 없습니다. 여기서 저장하면 저장소 파일이 바뀌고, VS Code에서 열어도 같은 내용이며, 변경은 `git diff`로 보입니다.
- 빌드는 저장소의 CMake preset(`linux-x64-playground`, 길게 실행하는 레슨은 `linux-x64-playground-release`)으로 합니다. 로컬에서 빌드하는 레슨과 같은 타깃입니다.
- 이 글도 저장소 파일입니다. 위의 경로를 누르면 에디터에서 열려 바로 고칠 수 있습니다.

## 두 층: 라이브러리와 레슨
| | 라이브러리 | 레슨 |
|---|---|---|
| 위치 | `include/atugcc/`, `src/` (CMake 타깃 `atugcc_core`) | `lessons/` |
| 무엇 | 다른 프로젝트에 그대로 가져다 쓰는 core 기능: 로그, 링 버퍼, 시간, 오류 처리, 패턴 골격(State 등), Tracer(시각화·구간 시간) | 라이브러리를 상황에 적용하는 연습: 패턴 적용과 변형, 구조, 실무 응용. 그리고 그 바탕이 되는 C++ 문법·관용구 |
| 여기서 | 🔒 읽기 전용. 고치는 곳은 VS Code | 편집하고 Run |
| 바꾸면 | 다음 Run부터 모든 레슨에 반영(복사본 없음) | 그 레슨만 |

라이브러리 예: [logger.hpp](/include/atugcc/core/logger.hpp), [state.hpp](/include/atugcc/pattern/state.hpp), [visualizer.hpp](/include/atugcc/pattern/visualizer.hpp)(Tracer)

## 여기서 하는 일
1. **읽기**: 레슨 README와 코드로 라이브러리를 어떻게 쓰는지 봅니다. 에디터에는 레슨 소스와 그 레슨이 쓰는 유닛·라이브러리 헤더가 함께 열립니다.
2. **고쳐 보기**: 코드를 바꾸고 ▶ Run(Ctrl+Enter)을 누릅니다. 수정한 탭을 저장하고 빌드·실행합니다. 컴파일 오류는 에디터에 표시됩니다.
3. **눈으로 보기**: 오른쪽 탭
   - **Output**: 프로그램 출력. 실행 중에 줄 단위로 나옵니다.
   - **Events**: Tracer 이벤트를 순서대로. 누르면 그 소스 줄로 갑니다.
   - **Diagrams**: Tracer가 만든 Mermaid 다이어그램. 프로그램이 정상 종료했을 때 생깁니다.
   - **Timings**: span으로 잰 구간 시간과 이전 실행 대비 변화. 에디터의 그 줄 끝에도 `⏱`로 나옵니다.

   Events·Diagrams·Timings는 레슨이 Tracer를 쓸 때 채워집니다. 레슨 코드에 따로 설정할 것은 없습니다.

## 순서
왼쪽 트리가 트랙 순서입니다.
1. **01_essentials**: core 기능, 자주 쓰는 문법(lambda, concurrency), 스레드·로그 관리. 예: [람다 캡처](/lessons/tracks/01_essentials/01_lambda_capture/README.md)
2. **02_patterns**: 상황에 맞게 패턴을 적용하고 변형하기. 예: [장비 상태 머신](/lessons/tracks/02_patterns/01_device_state_machine/README.md)

트리 아래쪽의 **유닛**은 여러 레슨이 같이 쓰는 코드입니다. "사용: …"에 그 유닛을 쓰는 레슨이 나옵니다.

## 여기서 안 되는 것
- **라이브러리 편집**: `include/`, `src/`는 VS Code에서 고칩니다.
- **외부 공개**: `127.0.0.1`에서만 열립니다. 서버가 레슨 코드를 그대로 빌드하고 실행하므로 다른 네트워크에 열지 않습니다.
- **Windows(MSVC) 빌드**: 웹은 WSL의 GCC로만 빌드합니다. 레슨은 두 컴파일러 모두에서 경고 없이 빌드돼야 하므로, 고친 레슨은 Windows preset으로도 빌드해 보세요.

## 레슨 만들기
- 어떤 코드를 어디에 두는지, 레슨을 추가하는 절차: 저장소 [README.md](/README.md)의 Workflow 섹션
- 매니페스트 형식과 작성 안내: [lessons/README.md](/lessons/README.md)
