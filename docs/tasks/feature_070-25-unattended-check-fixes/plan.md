# Plan 070-25: 무인 확인을 흐리는 KI 정리 (KI-050, KI-052, KI-053)

Spec: [070_25_unattended_check_fixes.md](/docs/specs/070_25_unattended_check_fixes.md) (approved 2026-11-16)
Branch: `feature/070-25-unattended-check-fixes`

## Files
- [NEW] `lessons/support/crt_report.cpp` — Windows Debug에서 `_CRT_ERROR`·`_CRT_ASSERT` 보고를 stderr로, `_CALL_REPORTFAULT` 끔, 디버거가 있으면 그대로 (KI-050, AC-1, AC-4)
- [MODIFY] `lessons/CMakeLists.txt` — `atugcc_lesson_console`에 새 파일
- [MODIFY] `lessons/tracks/01_essentials/11_thread_and_log/exercises.toml` — `remove_join`을 자동 과제로(`exit = "nonzero"`, `legacy_worker.hpp`에 `thread_.join()` 없음), 해설 문장 (AC-2)
- [MODIFY] `04_error_expected/exercises.toml`, `12_log_recovery/exercises.toml` — 대화상자 문장 (AC-7)
- [MODIFY] `lessons/tracks/02_patterns/01_device_state_machine/main.cpp` — `sleep_for(120ms)` 대신 `std::latch`로 `kTicks`(6)번째 틱을 기다림 (KI-053, AC-5)
- [MODIFY] 그 레슨의 `README.md`, `README.en.md`, `exercises.toml` — 기다리는 방식, 연습 1의 "대기를 늘리세요" 삭제
- [NEW] `web/frontend/scripts/vitest.mjs`, [MODIFY] `web/frontend/package.json` — Vitest를 대문자 드라이브 경로에서 시작 (KI-052, AC-6)
- [MODIFY] `lessons/README.md`, `web/README.md` — §8 Documentation Updates
- [MODIFY] `docs/known_issues.md` — KI-050, 052, 053 CLOSED

C++20/23: `std::latch`(C++20). evolution 페이지 없음(spec §3).

## Decisions made while implementing
- **`_WRITE_ABORT_MSG`는 끄지 않는다.** spec Assumption 2는 `_set_abort_behavior(0, _WRITE_ABORT_MSG | _CALL_REPORTFAULT)`라고 적었지만, 그러면 아무 줄도 찍히지 않아 같은 spec의 "한 줄을 stderr에 쓰고"(Assumption 2, AC-1)와 맞지 않는다. 메시지는 남기고 `_CRT_ERROR`를 stderr로 보내며 `_CALL_REPORTFAULT`만 끈다. 결과: stderr `abort() has been called`, 종료 코드 3 (testrecord R2).
- **KI-052의 원인은 `--prefix`가 아니라 드라이브 글자의 대소문자다.** 작업 디렉터리의 드라이브 글자가 소문자이면 두 명령 형태(`npm --prefix web/frontend test`, `cd web/frontend && npm test`) 모두 13 파일이 실패하고, 대문자이면 통과한다(cmd `cd /d`로 재현, testrecord R5). 이 세션의 Bash 도구가 처음에 소문자 드라이브로 시작해 한 번 재현됐다. `vite.config.ts`의 `root`나 `process.chdir`로는 고쳐지지 않았다(CLI가 이미 소문자 경로로 Vitest를 읽은 뒤). 그래서 `npm test`가 작은 시작 파일을 거쳐, 대문자 경로로 옮긴 뒤 Vitest CLI를 연다. 문서의 명령은 그대로 둔다.
- **KI-053 edge case "워커가 마지막 틱 전에 끝나는 경우"**: 원본에서 워커를 멈추는 것은 `main`뿐이고 `main`은 latch를 기다린 뒤에 멈추므로 생기지 않는다. 연습에서 `requestStop`을 앞으로 옮기면 기다림이 끝나지 않을 수 있지만, 그때는 웹의 10초 제한이 실행을 멈춘다. 신호를 하나 더 두는 대신 코드를 짧게 둔다(사용자 선호: 같은 동작이면 읽기 쉬운 쪽).

## Unit table
| Unit | File | Change (what, where, AC) | Check | Risky | Author | Reviewer | Tokens (in / out) | Status |
|---|---|---|---|---|---|---|---|---|
| U1 | `lessons/support/crt_report.cpp`, `lessons/CMakeLists.txt` | CRT 보고를 stderr로 (AC-1, AC-3, AC-4) | build `lesson_error_expected` 경고 0; 고친 사본을 직접 실행해 stderr 줄과 종료 코드 3, 114 ms | yes (platform branch) | lead (small) | codex luna | — | done |
| U2 | `11_thread_and_log/exercises.toml`, `04_error_expected/exercises.toml`, `12_log_recovery/exercises.toml`, `lessons/README.md` | `remove_join` 자동 과제, 대화상자 문장 (AC-2, AC-7) | `lessons.py check`; 풀이 스크립트 `remove_join` pass; `exercises_verify` | no | lead | cpp-reviewer | — | done |
| U3 | `device_state_machine/main.cpp` | `std::latch` 대기 (AC-5) | 20회 실행 모두 6틱 이상, `final state: RUN`; 풀이 `emergency_state` pass | yes (thread) | lead (small) | codex luna | — | done |
| U4 | 그 레슨의 README 두 개, `exercises.toml` | 대기 방식 설명, 연습 1 문장 (AC-5, AC-7) | `lessons.py check` | no | lead | cpp-reviewer | — | done |
| U5 | `web/frontend/scripts/vitest.mjs`, `web/frontend/package.json` | 대문자 드라이브로 옮긴 뒤 Vitest 시작 (AC-6) | 소문자·대문자 드라이브 × 두 명령 형태, 13 / 13 | no | lead (small) | cpp-reviewer | — | done |
| U6 | `web/README.md`, `docs/known_issues.md` | 시험 표 한 줄, KI 세 개 CLOSED (AC-6, AC-7) | `lint_docs.py` | no | lead | — | — | done |

U1, U3, U5는 한 함수 크기라 모델에 코드 작성을 맡기는 것보다 lead가 쓰는 쪽이 싸다(delegation.md §1 small change). U1·U3은 위험 단위라 다른 계열(codex luna)이 검토한다.
