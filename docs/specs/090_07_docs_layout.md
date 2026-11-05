---
id: 090-07
title: 문서 구조 정리 — learning 폴더를 cpp_evolution으로 합치고 한/영 두 벌로, 색인 문서를 docs/ 바로 아래로
depends_on: []
unblocks: []
approved: 2026-11-05
---

# Spec 090-07: 문서 구조 정리

사용자 요청(2026-11-05): 지금까지 구현한 내용으로 프로젝트를 다시 공부하려는데, `docs/learning/`과 `docs/cpp_evolution/`의 구조가 맞지 않는다. `learning/`을 없애고 내용은 `cpp_evolution/`으로, `learning/cpp_evolution.md`는 `docs/`로 옮기고, 각 문서는 한/영 모두로 설명한다. `docs/tasks/agent_todo.md`의 위치와 나머지 구조도 점검한다.

점검 결과(2026-11-05, 이 스펙의 근거):
- `docs/learning/`의 두 학습 문서는 한국어만, `docs/cpp_evolution/`의 9개 문서는 영어만 있다. 성격은 같다.
- `docs/learning/cpp_evolution.md`는 "(예정)" 표만 있고, 그 표의 concepts·format·expected는 이미 문서가 있다. 실제 페이지 목록 역할을 못 한다.
- `docs/tasks/`에는 태스크 기록 폴더(`feature_*`) 사이에 프로젝트 색인 `agent_todo.md`와 커리큘럼 계획 `lesson_candidates.md`가 섞여 있다. 같은 성격의 `known_issues.md`는 이미 `docs/`에 있다.
- `docs/artifacts/`(설계 개요, Linux 설치 안내)는 부트 문서가 "Task artifacts"라고 부르는 `docs/tasks/feature_*/`와 이름이 겹친다.
- 스크립트 폴더가 세 곳(`scripts/`, `tools/`, `.agent/scripts/`)이고 `scripts/`에는 옛 덤프 형식 파서 하나뿐이다. `libs/`에는 `CMakeLists.txt`만 있다. 둘 다 이 작업에서는 KI로만 남긴다(§6).

## 0. Assumptions (please review)
사용자가 정한 것(2026-11-05 질문 답): 한/영은 파일 두 개, `agent_todo.md`와 `lesson_candidates.md`는 둘 다 `docs/`로, `docs/artifacts/`는 `docs/guides/`로, 이 답을 스펙 승인으로 본다.

| # | Decision | Rejected alternative | Why |
|---|---|---|---|
| 1 | **한/영 두 파일**: `<topic>.md` = 한국어, `<topic>.en.md` = 영어. `docs/cpp_evolution.md`(목차)도 `docs/cpp_evolution.en.md`와 짝 | 한 파일에 두 언어 | 사용자 결정. 레슨의 `README.md`/`README.en.md`와 같은 규칙이라 링크 고르는 법이 하나다 |
| 2 | **지금 영어 페이지 9개는 `git mv`로 `.en.md`가 되고, 같은 이름의 `.md`는 새 한국어 번역**. learning의 한국어 두 문서는 `.md`로 남고 `.en.md` 번역을 새로 쓴다 | 영어를 `.md`로 두고 한국어를 `.ko.md`로 | 1번 규칙을 따른다. 옛 링크 `/docs/cpp_evolution/<topic>.md`(스펙, 봉인된 기록)는 깨지지 않고 같은 주제의 한국어판을 가리킨다 |
| 3 | **원문이 기준이고 번역은 내용을 더하거나 빼지 않는다.** 두 파일은 제목 구조(제목 수준의 순서)와 코드 블록 수가 같다. 코드 블록 안의 코드는 같고, 주석만 그 언어로 옮길 수 있다 | 번역하며 내용 손질 | 두 판이 다른 말을 하면 어느 쪽이 맞는지 알 수 없다. 내용 수정은 별도 작업이 한다 |
| 4 | **링크는 같은 언어끼리**: 한국어 페이지 → 레슨 `README.md`, 다른 evolution 페이지 `.md`; 영어 페이지 → `README.en.md`, `.en.md`. 레슨 README도 같다. 지금 붙어 있는 "(영어)"/"(Korean)" 표시는 지운다 | 모두 한 언어로 링크 | 읽는 사람이 언어를 바꿔 가며 읽지 않게 |
| 5 | **문서 게이트가 짝을 검사한다**: `lint_docs.py`가 `docs/cpp_evolution/`와 `docs/cpp_evolution.md`에서 짝이 없는 파일, 그리고 짝의 제목 수준 순서나 코드 블록 수가 다른 경우를 WARN으로 낸다 | 검사 없음 / ERROR | `lessons.py check`가 `README.en.md` 없음을 WARN으로 내는 것과 같은 수준(070-03). 완료 조건이 경고 0이라 사실상 막는다 |
| 6 | **새 이름**: `learning/const_return_type_guide.md` → `cpp_evolution/const_return_type.md`(다른 페이지처럼 주제 이름만). `learning/modern_ring_buffer_architecture.md`는 이름 그대로 `cpp_evolution/`로. 목차에 "옛 구조의 기록"으로 표시 | 링 버퍼 문서 이름도 바꿈 | 그 문서는 이미 첫 줄에서 옛 구조라고 밝히고, 이름을 바꿀 이유가 위치 말고는 없다 |
| 7 | **`docs/cpp_evolution.md`는 목차로 다시 쓴다**: 페이지마다 주제, 예전 방식 → 지금 방식, 관련 레슨 링크. 옛 "(예정)" 표에서 아직 페이지가 없는 주제(jthread, ranges, variant)는 "페이지 없음, 레슨 있음"으로 적는다 | 내용 그대로 옮김 | 옮기기만 하면 틀린 "(예정)" 표가 그대로 남는다 |
| 8 | **옮기는 경로의 링크는 봉인되지 않은 파일에서만 고친다**: 규칙, README, 레슨, 색인 문서, legacy가 아닌 스펙(DONE 포함, 링크 경로만 고침, 내용과 History는 그대로). **봉인된 기록**(DONE 태스크의 `docs/tasks/feature_*/`, legacy 스펙)은 고치지 않는다. 그곳의 끊긴 링크는 문서 게이트가 INFO로만 낸다 | 봉인된 기록도 고침 | spec.md §4: 원래 태스크의 기록 폴더는 봉인되어 쓰지 않는다. 링크 경로만 바뀌는 스펙 수정은 요구사항 변경이 아니다 |
| 9 | **`docs/README.md` 색인은 만들지 않는다.** 루트 README의 Project Structure 트리를 새 구조에 맞게 고치고, 학습용 입구는 `docs/cpp_evolution.md`가 맡는다 | docs 색인 추가 | 같은 목록을 두 곳에서 관리하게 된다 |
| 10 | **`.agent/scripts/` 밖의 도구는 바꾸지 않는다.** 경로를 코드에 박은 곳은 `lint_docs.py`의 `TODO` 상수와 그 테스트 데이터뿐이다(2026-11-05 `git grep`) | — | — |

## 1. Objective
- C++ 학습 문서가 한 폴더(`docs/cpp_evolution/`)에 한/영 두 벌로 있고, `docs/cpp_evolution.md`(+ `.en.md`)가 그 목차다.
- `docs/` 바로 아래에는 프로젝트 전체에 대한 문서(부트, 태스크 목록, KI, 레슨 후보, evolution 목차)만, `docs/tasks/`에는 태스크 기록 폴더만 있다.
- 폴더 이름이 내용과 맞는다(`docs/guides/`).

## 2. Requirement Details

### 2.1 Public API Surface
none (C++ 코드 변경 없음).

### 2.2 Internal Implementation
옮기기(`git mv`):

| 지금 | 새 위치 |
|---|---|
| `docs/learning/cpp_evolution.md` | `docs/cpp_evolution.md` (목차로 다시 씀, 한국어) + 새 `docs/cpp_evolution.en.md` |
| `docs/learning/const_return_type_guide.md` | `docs/cpp_evolution/const_return_type.md` + 새 `.en.md` |
| `docs/learning/modern_ring_buffer_architecture.md` | `docs/cpp_evolution/modern_ring_buffer_architecture.md` + 새 `.en.md` |
| `docs/cpp_evolution/<topic>.md` 9개(영어) | `docs/cpp_evolution/<topic>.en.md` + 새 한국어 `<topic>.md` |
| `docs/tasks/agent_todo.md` | `docs/agent_todo.md` |
| `docs/tasks/lesson_candidates.md` | `docs/lesson_candidates.md` |
| `docs/artifacts/` | `docs/guides/` |

9개: `chrono_format`, `concepts`, `designated_initializers`, `error_expected`, `filesystem`, `format`, `lock_free_logging`, `modules`, `source_location`.

`lint_docs.py`:
- `TODO = Path("docs/agent_todo.md")`.
- `check_evolution_pairs(root, report)`: `docs/cpp_evolution/*.md`와 `docs/cpp_evolution.md`에 대해 (a) `<x>.md`에 `<x>.en.md`가 없거나 그 반대면 WARN, (b) 둘 다 있으면 코드 밖 제목의 수준 순서(`#` 개수의 목록)와 코드 블록 수를 비교해 다르면 WARN. 메시지는 짝의 경로와 다른 항목을 적는다.

### 2.3 Platform Specifics
none.

## 3. C++ Standard Evolution
N/A (문서 구조 작업. evolution 페이지 내용은 바꾸지 않고 번역만 한다).

## 4. Edge Cases
- [x] 옛 링크: `/docs/cpp_evolution/<topic>.md`는 한국어판으로 계속 열린다(Assumption 2). 옮긴 경로를 가리키는 봉인된 기록의 링크는 끊기고 INFO로 남는다(Assumption 8).
- [x] 대소문자·확장자: `<x>.en.md`의 한국어 짝은 `<x>.md`. `README.en.md` 같은 이름이 `docs/cpp_evolution/`에 생기지 않는다.
- [x] Windows `git mv`로 이름만 바꾼 파일 위에 같은 이름의 새 파일을 쓰는 순서: 먼저 `.en.md`로 옮겨 커밋 대상에 올린 뒤 새 `.md`를 쓴다(이력이 영어판을 따라간다).
- N/A Thread safety, lifetime, ODR, UB, templates: C++ 코드 변경 없음.

## 5. Acceptance Criteria
| ID | Criterion | Verified by |
|---|---|---|
| AC-1 | `docs/learning/`, `docs/artifacts/`가 없고, §2.2 표의 새 위치에 모든 파일이 있다. `docs/tasks/` 바로 아래에는 `feature_*` 폴더만 있다 | `git ls-files docs` 목록 |
| AC-2 | `docs/cpp_evolution/`의 11개 주제와 `docs/cpp_evolution.md`가 모두 `.md`/`.en.md` 짝이고, 짝마다 제목 수준 순서와 코드 블록 수가 같다 | `lint_docs.py` 경고 0; 짝 검사 단위 테스트(짝 없음, 제목 다름, 코드 블록 수 다름, 정상) |
| AC-3 | 한국어 문서(`docs/cpp_evolution/*.md` 중 `.en.md`가 아닌 것, `docs/cpp_evolution.md`, 레슨 `README.md`)는 evolution 페이지와 레슨에 한국어판으로, 영어 문서(`*.en.md`, 루트 `README.md`, 영어로 쓴 `.agent/` 규칙)는 영어판으로 링크한다 | `git grep` 두 개: 한국어 문서에서 `cpp_evolution/[a-z_]*\.en\.md` 또는 `README\.en\.md` 링크 0, 영어 문서에서 `cpp_evolution/[a-z_]*\.md`(`.en.md` 아님) 링크 0 |
| AC-4 | 봉인되지 않은 파일에 옛 경로(`docs/learning`, `docs/tasks/agent_todo`, `docs/tasks/lesson_candidates`, `docs/artifacts`)가 없다. 이 스펙과 이 태스크의 기록 폴더는 옮긴 내용을 설명하므로 뺀다. DONE 스펙이 당시의 기각한 대안으로 적은 문장(070-15 Assumption 18의 `docs/learning/`)은 기록이라 그대로 둔다 | `git grep` (봉인된 기록과 이 태스크 파일 제외) 0 |
| AC-5 | 문서 게이트: 오류 0, 경고 0. 새 INFO는 모두 봉인된 기록에 있다 | `py -3 .agent/scripts/lint_docs.py`, INFO 목록을 기준선(21건)과 비교 |
| AC-6 | 스크립트 테스트가 모두 통과한다(옮긴 `TODO` 경로, 새 짝 검사) | `py -3 -m unittest discover -s .agent/scripts -p "test_*.py"` |
| AC-7 | 번역은 원문과 같은 내용을 담는다: 빠진 문장, 더한 주장, 바뀐 숫자·이름·코드가 없다 | `cpp-reviewer`가 짝마다 대조, 결과는 testrecord Reviews |
| AC-8 | 레슨 검사와 플레이그라운드 레슨 목록은 그대로다 | `py -3 tools/lessons.py check` 오류·경고 0 |

## 6. Out of Scope
- `scripts/parse_dump.py`: 010-07의 옛 고정 블록 덤프 형식 파서로, 지금 형식은 `tools/read_dump.py`가 읽는다. 지금 덤프에서 아직 쓸모가 있는지 확인하고 지우거나 `tools/`로 옮기는 일 — 새 KI.
- `libs/`에 `CMakeLists.txt`만 있고 소스는 `src/libs/`, 헤더는 `include/atugcc/libs/`에 있는 배치 — 040-01(shape/sound 현대화)이 함께 정한다, 새 KI.
- `main.cpp`와 `sample/`이 루트에 있는 것 — 이미 070-04에 있음.
- evolution 페이지 내용 수정, 빠진 페이지(KI-001) — 그대로.
- 봉인된 기록의 끊긴 링크 — 고치지 않음(Assumption 8).

## 7. Dependencies & Backends
none.

## 8. Documentation Updates
| Document | Section | Change |
|---|---|---|
| [`docs/agent_start_prompt.md`](/docs/agent_start_prompt.md) | Boot 2, Quick reference | `docs/agent_todo.md`; evolution 노트 `<feature>.md` + `<feature>.en.md`, 목차 `docs/cpp_evolution.md` |
| [`.agent/rules/spec.md`](/.agent/rules/spec.md) | §1 | todo 경로 |
| [`.agent/rules/impl.md`](/.agent/rules/impl.md) | Reference docs | 한/영 두 파일 규칙, 목차에 한 줄 |
| [`.agent/rules/config.md`](/.agent/rules/config.md) | Linux toolchain | `docs/guides/linux_build_setup.md` |
| [`.agent/workflows/start-develop-one-task.md`](/.agent/workflows/start-develop-one-task.md) | 설명, 4 Plan | todo 경로, evolution 두 파일 |
| [`docs/specs/00_template.md`](/docs/specs/00_template.md) | §3 | evolution 두 파일 |
| [`README.md`](/README.md) | Project Structure, Features, Workflow, Roadmap | 새 트리, `.en.md` 링크, todo·후보 경로 |
| [`web/README.md`](/web/README.md), [`lessons/README.md`](/lessons/README.md) | 링크 | guides, lesson_candidates 경로 |
| 레슨 README(`02_format_text`, `03_const_correctness`, `04_error_expected`, `05_source_location`, `06_concepts`, `09_chrono_time`, `10_filesystem_paths`, `12_log_recovery`, `13_lock_free_buffer`, `15_modules`) | 설명 글 링크 | 한국어판 → `.md`, 영어판 → `.en.md`, 언어 표시 삭제 |
| [`docs/lesson_candidates.md`](/docs/lesson_candidates.md) | 머리말, 표의 출처 | evolution 두 파일 규칙, 새 경로 |
| [`docs/guides/project_blueprint.md`](/docs/guides/project_blueprint.md) | 끝 참고 | `docs/cpp_evolution.md` |
| [`docs/known_issues.md`](/docs/known_issues.md) | 표, 본문 | 옛 경로 고침; 새 KI 두 개(§6) |
| legacy가 아닌 스펙의 옛 경로 링크 | 링크만 | 새 경로 |

## 9. Technical Constraints
- 문서와 Python 스크립트만 바꾼다. C++ 빌드에 영향 없음.

## 10. Context & References
- [lint_docs.py](/.agent/scripts/lint_docs.py), [test_agent_scripts.py](/.agent/scripts/test_agent_scripts.py)
- [070-03](/docs/specs/070_03_essentials_curriculum.md): 레슨 `README.en.md` 규칙
- [spec.md](/.agent/rules/spec.md) §4: 봉인된 기록

## 11. Implementation Plan
- [x] U1 옮기기(`git mv`)와 봉인되지 않은 파일의 링크 경로 바꾸기
- [x] U2 `lint_docs.py`: `TODO` 경로, `check_evolution_pairs`
- [x] U3 `test_agent_scripts.py`: todo 경로, 짝 검사 테스트
- [x] U4 한국어 번역 9개
- [x] U5 영어 번역 2개(const_return_type, modern_ring_buffer_architecture)
- [x] U6 목차 `docs/cpp_evolution.md` / `.en.md`
- [x] U7 §8의 규칙·README·레슨 링크, KI 두 개

## 12. Verification Plan
- [x] `py -3 .agent/scripts/lint_docs.py` 오류·경고 0, INFO 비교
- [x] `py -3 -m unittest discover -s .agent/scripts -p "test_*.py"`
- [x] `py -3 tools/lessons.py check`
- [x] AC-3, AC-4 `git grep`
- [x] `cpp-reviewer` 번역 대조(AC-7)
- C++ 빌드와 ctest는 돌리지 않는다: 바뀌는 파일이 CMake 입력이 아니다(`git diff --stat`로 확인).

## History / Amendments
- 2026-11-05: 작성, 같은 날 사용자 승인(질문 답).
