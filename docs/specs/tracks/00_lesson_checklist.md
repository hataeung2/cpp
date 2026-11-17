# Lesson checklist: NNN-SS `<lesson id>`

레슨 작업 하나의 기록이다([spec.md](/.agent/rules/spec.md) §6). 이 파일을 `docs/tasks/feature_NNN-SS-<slug>/checklist.md`로 복사해 쓰고, `plan.md`, `testrecord.md`, `walkthrough.md`는 쓰지 않는다. `DONE`이 되려면 아래의 `- [ ]`가 하나도 남지 않아야 한다(문서 gate가 검사). 맞지 않는 항목은 지우지 않고 `- [x] N/A: <이유>`로 쓴다.

- Track spec: `/docs/specs/tracks/<track>.md` (approved YYYY-MM-DD), 행: `<lesson id>`
- Branch: `feature/NNN-SS-<slug>`

## 설계
lead가 정한다. 트랙 spec의 행(주제, 비교)과 공통 규칙 안에서.

| 단계 | 출력으로 보이는 것 |
|---|---|
| 1 | [...] |

| 과제 id | 무엇을 바꾸나 | 자동 / 관찰 | 관찰이면 이유 |
|---|---|---|---|
| `<id>` | [...] | 자동 | — |

- 트랙 spec 행과 다른 점: [없음 / 무엇이 왜]. 주제·순서가 바뀌거나 새 레슨이 필요하면 멈추고 트랙 spec을 고쳐 사용자 승인을 받는다.
- 파일: [레슨 폴더, 새 유닛, 링크 줄을 단 레슨]

## 체크리스트
항목마다 `근거:` 뒤에 명령과 결과(또는 절 이름)를 쓰고 `[x]`로 바꾼다.

- [ ] **C1** 바뀐 파일이 레슨 경로의 범위(spec [090-13](/docs/specs/090_13_lesson_path.md) §2.1) 안에 있다. 근거: `git diff --stat main...` →
- [ ] **C2** 설계 절이 트랙 spec 행(주제, 비교)과 맞고 다른 점이 적혀 있다. 트랙 spec을 고칠 일이면 멈췄다. 근거: 설계 절
- [ ] **C3** `lessons.py check`: ERROR 0, 이 레슨·유닛에 WARN 0(`[scaffold]` 포함). 근거: `py -3 tools/lessons.py check` →
- [ ] **C4** `lesson_<id>`가 `windows-x64-debug`와 `linux-x64-debug`에서 경고 없이 빌드된다. 근거: `build.py --preset <p> --target lesson_<id>` →
- [ ] **C5** 두 OS의 출력이 같다(줄 끝 제외). 주소·시간·해시 없음. 근거: 두 실행의 비교 →
- [ ] **C6** `--label lesson`이 `windows-x64-debug`, `linux-x64-debug`, `linux-x64-asan`에서 통과한다(`lesson.<id>`, `lesson.<id>.exercises_verify`). 근거: `build.py --preset <p> --test --label lesson --report` →
- [ ] **C7** 자동 과제마다 답의 변경으로 두 컴파일러에서 통과한다. 관찰 과제는 이유가 설계 절에 있다. 근거: `tools/exercises.py check <id> --preset <p>` →
- [ ] **C8** README 두 판의 절, 과제, 코드 블록 수가 같고, "연습" 항목 수 = `exercises.toml` 과제 수. 근거: 세어 본 수 →
- [ ] **C9** 레슨 작성 안내([lessons/README.md](/lessons/README.md) "레슨 작성 안내")와 트랙 spec 공통 규칙을 따른다: 영어 출력, 두 언어 주석, UB를 돌리지 않음. 근거: 리뷰 절
- [ ] **C10** fresh reviewer 한 번, 지적은 모두 고쳤거나 이유를 적고 남겼다. 근거: 리뷰 절
- [ ] **C11** 목록 문서(트랙 spec 상태 열, `lesson_candidates.md`, 필요하면 `intro.md`·`intro.en.md`, 링크 줄)가 맞다. 근거: diff, `lint_docs.py` →
- [ ] **C12** 후속은 KI로 등록했다. 근거: KI id 또는 "없음"
- [ ] **C13** `lint_docs.py` exit 0. 근거: 명령 출력 →

## 리뷰
| 리뷰어 | 질문 | 지적 | 처리 |
|---|---|---|---|
| `cpp-reviewer` | [...] | [...] | [...] |

## 후속
- [KI-NNN: ... / 없음]
