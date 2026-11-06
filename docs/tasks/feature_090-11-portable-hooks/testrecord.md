# Test Record 090-11: 어느 agent에서나 같은 guard

- Spec: [/docs/specs/090_11_portable_hooks.md](/docs/specs/090_11_portable_hooks.md) · Plan: [plan.md](plan.md)

C++ 변경 없음: preset 빌드·ctest 대상이 아니다. 검증은 스크립트 게이트([test.md](/.agent/rules/test.md) §6)와 사용자 확인(AC-5)이다.

## Spec과 다르게 한 것
- **codex 이벤트를 실제로 기록하지 않았다**(spec §0의 3번, §11 U1). scratch 임시 저장소에서 `codex exec --dangerously-bypass-hook-trust`로 기록 전용 hook을 한 번 돌리려 했으나 자동 권한 검사가 신뢰 우회 플래그라 거부했다. 사용자 결정(2026-11-06): 공식 문서 기준으로 fixture를 만들고, 실제 동작은 AC-5에서 확인.
- **강제로 add한 무시 대상 파일도 검사한다**. spec §0의 4번 "무시된 파일 제외, guard와 같은 예외"를 `git check-ignore`(index에 있는 파일은 무시 대상이 아니다)로 읽었다. `git add -f`로 올린 파일은 commit되므로 rule 1("commit되는 파일에 machine path 금지")이 적용된다. git hook에서는 무시된 파일 예외가 실제로는 발동하지 않는다: 무시된 파일은 강제로 올리지 않는 한 staged되지 않는다.
- `--status`·`--boot`의 안내 줄은 plan 문구(`…; the user decides per clone`)이고, spec §0의 5번 문구보다 한 구절 길다.

## Runs (2026-11-06)

| Run | Expected | Actual | Status |
|---|---|---|---|
| `py -3 .agent/scripts/test_agent_scripts.py` (Windows) | 전부 통과 | `Ran 155 tests`, OK | Pass |
| WSL Linux: `GitPrecommitAndSetupHooksTest CodexGuardHookTest GuardHookTest` (임시 폴더는 ext4, `"`가 든 경로 사례 포함) | 전부 통과 | `Ran 27 tests`, OK | Pass |
| 테스트 먼저: U3 전 codex 8개, U5 전 git hook 10개 | 실패 | 각각 8·10개 FAIL, 나머지 OK | Pass |
| 실제 `.githooks/pre-commit`을 거친 `git commit`(임시 저장소, Git for Windows sh) | main 거부, feature 깨끗하면 통과, machine path 거부 | 셋 다 그대로(`test_precommit_review_real_hook_through_git_commit`) | Pass |
| 이 저장소의 `core.hooksPath` | 바뀌지 않음(사용자 결정) | 설정 없음(`git config --local --get` exit 1) | Pass |
| `py -3 .agent/scripts/lint_docs.py` | 0 error, 0 warning | `0 error(s), 0 warning(s), 33 info` | Pass |
| `py -3 .agent/scripts/naming_check.py` | 0 | 0 | Pass |

## AC evidence

| AC | Criterion | Evidence | Result |
|---|---|---|---|
| AC-1 | 기존 GuardHookTest·CommandPositionTest가 바뀌지 않고 통과 | U2 뒤 테스트 파일 무변경으로 통과; lead가 guard.py를 다시 쓴 뒤에도 통과(파일을 읽기 전에 대상 여부 판정, HEAD와 같은 순서) | Pass |
| AC-2 | codex adapter: 즉석 configure·main commit·machine path patch 거부, 허용 사례 통과 | `CodexGuardHookTest` 10개(정확한 이유 비교, 목록 명령 `bash -lc`, cwd 기준 경로, Move to, 여러 파일 블록, 절대 경로, Delete, BOM, 문맥 줄 ` *** End Patch`, form feed, hooks.json 형식) | Pass (문서 기준 fixture) |
| AC-3 | git pre-commit: main 거부, machine path 거부, 깨끗하면 허용, 무시된 파일, 스크립트 오류 시 거부 | `GitPrecommitAndSetupHooksTest`의 precommit 사례(정확한 stderr 줄, detached HEAD의 경로 검사, 바이너리, 한글·공백·따옴표 경로, `+++` 내용 줄, 사용자 diff 접두사 설정, symbolic-ref 오류 fail closed), 실제 hook을 거친 `git commit` | Pass |
| AC-4 | `setup_hooks.py`가 설정을 쓰고 다른 값은 바꾸지 않음, 미설치 안내 줄 | setup 사례(메시지, 두 번째 실행, 다른 값 이름을 알리고 exit 1, 저장소 아님 → None), lint 줄(`--status`, `--boot`, 설치 뒤 없음, 저장소 아님 → 없음) | Pass |
| AC-5 | codex에서 `/hooks` 신뢰 뒤 main commit 거부 | **사용자 수동 확인 대기** | — |
| AC-6 | 회귀 없음 | 155 tests OK, lint 0/0 | Pass |

## Reviews

| Unit | Reviewer | Findings | Resolution |
|---|---|---|---|
| U2 | cpp-reviewer | 판정 결과는 같음. 저장소 밖·무시된 파일을 먼저 읽음, 죽은 대체 코드, 테스트를 위해 공용 함수를 바꿔치기 | lead가 guard.py를 다시 씀; guard_rules에 `is_checked_file`·`machine_path_reason`·`protected_branch_reason` |
| U3 | cpp-reviewer | 이유를 정확히 비교하지 않음, cwd·Move to·config 형식이 느슨함; 브랜치 patch는 실제 git 호출에 닿음 | lead 테스트 추가 |
| U4 | cpp-reviewer | 목록 명령을 공백으로 이어 `["bash","-lc","git commit"]`을 놓침, 별칭과 matcher 모순, patch 시작 조건, 죽은 대체 코드; Claude adapter의 대상 판정이 공용 함수 복사 | lead가 adapter를 다시 씀 + 테스트. Claude adapter는 테스트가 patch하는 이름을 거쳐야 해서 주석을 남김 |
| U5 | cpp-reviewer | case 4의 해석이 틀림(강제 add 파일 예외), setup `--root` 계약, 바이너리·detached 사례 약함, stderr 형식, 메시지, 실행 비트 | case 4를 "검사함"으로 바로잡음(작성자가 그 잘못된 테스트에 맞추려 `agent_common.is_ignored`에 `--no-index`를 넣은 것을 되돌림), 테스트 보강 |
| U6·U7·최종 | cpp-reviewer | diff 해석: `+++` 내용 줄, `mnemonicPrefix`/`noprefix`/textconv, 공백 경로의 TAB, 따옴표 경로, `splitlines`, symbolic-ref 128; codex adapter의 문맥 줄 머리 오인; 문서: 충돌 merge 뒤 commit, Antigravity가 덮는 규칙, master, 문구, plan의 Antigravity 줄 | lead 수정: 파일별 고정 형식 diff와 첫 hunk 뒤의 `+` 줄만, `\n`으로만 자르기, 0열 머리 줄, 문서 고침, 실제 hook을 거친 commit 테스트. §6.3에 따라 이 마지막 수정은 재검토하지 않음 |

작성자 agy(Gemini 계열), 검토자 cpp-reviewer(Claude 계열): 계열이 다른 검토.
