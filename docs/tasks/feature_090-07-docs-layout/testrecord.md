# Test Record: 090-07 문서 구조 정리

- Spec: [/docs/specs/090_07_docs_layout.md](/docs/specs/090_07_docs_layout.md)
- Host: Windows 11, Python 3 (`py -3`). C++ 빌드와 ctest는 돌리지 않았다: `git diff main --name-only`에서 CMake 입력(`CMakeLists.txt`, `*.cmake`, `CMakePresets.json`, C++ 소스)이 0개이고, Markdown이 아닌 변경은 `.agent/scripts/lint_docs.py`, `test_agent_scripts.py` 둘뿐이다(spec §12).

## Runs — 2026-11-05
| Command | Result |
|---|---|
| `py -3 .agent/scripts/lint_docs.py` (main, 기준선) | 0 error, 0 warning, 21 info |
| `py -3 .agent/scripts/lint_docs.py` (U2 직후, 번역 전) | 66 error(끊긴 `.md` 링크), 12 warning(짝 없음 12건: 짝 검사 동작 확인) |
| `py -3 .agent/scripts/lint_docs.py` (최종) | 0 error, 0 warning, 33 info |
| `py -3 -m unittest discover -s .agent/scripts -p "test_*.py"` | 71 tests OK (새 `test_evolution_pages_come_in_pairs` 포함; R2 수정 뒤 다시 71 OK) |
| `py -3 tools/lessons.py check` | 0 error, 0 warning; 2 tracks, 17 lessons, 2 units |
| 코드 블록 대조 스크립트(영어 원문 9쌍) | 9쌍 모두 코드 블록 수 같고 내용 바이트 단위로 같음 |

새 INFO 12건(main 기준선 21건과 `comm`으로 비교, 없어진 것 0): 모두 봉인된 기록 `docs/tasks/feature_{070-03,070-10,070-11,070-12,070-13,090-05}*`에서 옮긴 경로(`docs/tasks/lesson_candidates.md` 7, `docs/learning/*` 2, `docs/artifacts/*` 2, `docs/tasks/agent_todo.md` 1)를 가리키는 링크. Assumption 8대로 고치지 않았다.

## AC evidence
| AC | Evidence | Result |
|---|---|---|
| AC-1 | `git ls-files docs`: `docs/learning`·`docs/artifacts` 0개; `docs/tasks/` 바로 아래는 `feature_*`만; `docs/cpp_evolution/`에 11쌍 22개 | pass |
| AC-2 | 최종 lint 경고 0; 단위 테스트가 짝 없음(양방향, 목차 포함), 제목 수준 다름, 코드 블록 수 다름, 정상을 확인 | pass |
| AC-3 | 한국어 문서 → `.en.md`/`README.en.md` 링크 `git grep` 0건; 영어 문서(`*.en.md`, 루트 README, `.agent/*.md`) → 한국어 `cpp_evolution/<x>.md`·`lessons/.../README.md` 링크 `git grep` 0건 | pass |
| AC-4 | 옛 경로 `git grep`(봉인된 기록, 이 태스크 파일 제외): 1건, 070-15 Assumption 18의 기각한 대안 문장(AC-4에 적은 예외) | pass |
| AC-5 | 위 Runs: 0 error, 0 warning, 새 INFO 12건 모두 봉인된 기록 | pass |
| AC-6 | unittest 71 OK | pass |
| AC-7 | Reviews R1, R2: 뜻이 바뀐 번역 0건. 표현이 약하거나 빠진 곳 6건을 고침 | pass |
| AC-8 | `lessons.py check` 0/0, 레슨 17개 그대로 | pass |

## Reviews
| Unit | Reviewer | Question | Findings | Resolution |
|---|---|---|---|---|
| U4 | cpp-reviewer (R1) | 한국어 번역 9개가 영어 원문과 같은 말을 하는가(빠짐, 더함, 뜻 바뀜, 잘못된 언어 링크) | 뜻이 바뀐 곳·잘못된 언어 링크 없음. 표현 위험 3건: `concepts.md` "같은 식"(글자가 같은 식으로 읽힐 수 있음), `lock_free_logging.md` "한도"(1 ms 한도로만 읽힐 수 있음, 원문은 기준과 1 ms 중 늦은 쪽), "처리량 26 %"(비교 대상 빠짐) | 3건 모두 lead가 고침 |
| U2, U3, U5, U6 | cpp-reviewer (R2) | 짝 검사가 §2.2와 맞는가, 테스트가 비교를 빼도 통과하는가; 영어 번역 2개와 목차 한 쌍의 내용·사실 | 코드: (1) `cpp_evolution.en.md`만 있을 때 경고 없음(§2.2 위반), (2) UTF-8이 아닌 페이지를 `check_file`과 두 번 보고, (3) `x.md` 이름의 폴더면 예외, (4) `~~~`·4-backtick 펜스와 `#\t` 제목 미지원(지금 페이지에 없음). 테스트: 비교 둘 다 빼면 실패함(yes), 그러나 "코드 밖" 처리와 (1)은 시험하지 않음. 번역: `.en.md`에 "(in Korean)" 추가 3곳, "완벽하게"·"C++에서" 빠짐, 목차 영어판 주어("the pages go from"), 목차 양쪽 "이 폴더". 목차의 모든 행은 사실(레슨 폴더, 페이지, 코드 이름 확인) | (1)–(3) lead가 고침(`review fixes lead (small)`), 테스트에 펜스 안 `## ` 줄과 목차 반대 방향 추가, `strip_code`를 빼는 변형으로 실패 확인. (4)는 지금 쓰지 않는 문법이라 그대로. "(in Korean)"은 한국어로만 있는 스펙·blueprint·후보 목록을 가리키는 안내라 유지(기존 `12_log_recovery/README.en.md`와 같은 표기, Assumption 4는 짝이 있는 문서 사이의 표시만 다룸). 나머지 번역 4건 고침 |
| U2, U3 fixes | cpp-reviewer (R3) | lead의 수정이 (1)–(3)을 고쳤는가, 새 문제가 있는가, 테스트가 `strip_code`·반대 방향 검사를 빼면 실패하는가 | none: (1)–(3) 고쳐짐, 목차 중복 보고 없음, UTF-8 아닌 `.en.md`도 `check_file`이 ERROR로 냄, 두 변형 모두 테스트 실패 | — (lead가 `strip_code` 변형을 직접 돌려 실패 확인, unittest 71 OK) |

리뷰는 모두 Claude `cpp-reviewer`(lead와 같은 모델 계열). 이 작업은 문서와 스크립트만 바꾸고 risky 단위가 없어서 다른 계열 리뷰(delegation.md §6.2)를 쓰지 않았다.
