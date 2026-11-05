# Plan: 090-07 문서 구조 정리

- Spec: [/docs/specs/090_07_docs_layout.md](/docs/specs/090_07_docs_layout.md) (approved 2026-11-05)
- Branch: `feature/090-07-docs-layout` (from `main` at `0776a27`)
- Baseline (main): `lint_docs.py` 0 error, 0 warning, 21 info; script tests OK.

## Files
- [MOVE] spec §2.2 표 전체 (`git mv`, 이름만 바꾼 커밋 `35658fd`를 먼저 둬서 영어판 이력이 `.en.md`로 이어짐)
- [NEW] `docs/cpp_evolution/<topic>.md` 9개 (한국어 번역), `const_return_type.en.md`, `modern_ring_buffer_architecture.en.md` (영어 번역), `docs/cpp_evolution.en.md`
- [MODIFY] `docs/cpp_evolution.md` (목차로 다시 씀)
- [MODIFY] `.agent/scripts/lint_docs.py` — `TODO` 경로, `check_evolution_pairs`, `page_shape`
- [MODIFY] `.agent/scripts/test_agent_scripts.py` — todo 경로, `test_evolution_pages_come_in_pairs`
- [MODIFY] 링크만: spec §8 표의 문서들, legacy가 아닌 스펙 16개, `07_game_engine_adapters.md`(SPEC_DRAFT, 봉인 아님)
- 봉인된 기록(`docs/tasks/feature_*` 중 이 태스크 아닌 것, DONE legacy 스펙)은 바꾸지 않는다 (Assumption 8)

## Design decisions
- D1 링크 바꾸기는 스크립트로(sed 6개 치환, 대상은 `git grep -l`로 고른 봉인되지 않은 파일). 결과는 문서 게이트의 링크 검사로 확인한다.
- D2 언어별 링크: `*.en.md`와 루트 `README.md`에서 `/docs/cpp_evolution/<x>.md` → `<x>.en.md`, 링크 글자도 파일 이름에 맞춤. 한국어 레슨 README의 "(영어)", 영어 const_correctness README의 "(Korean)" 삭제.
- D3 한국어 번역(영어 원문 9개)의 코드 블록은 원문과 같은 바이트로 둔다(주석 포함). 한국어 원문 2개의 영어판은 코드 주석도 영어로 옮긴다. Assumption 3이 허용하는 범위다.
- D4 `known_issues.md`는 영어로 쓴 기록이지만 링크를 `.md`(한국어판)로 둔다. 끊기지 않고, AC-3의 영어 문서 범위(`*.en.md`, 루트 README, `.agent/` 규칙)에 들지 않는다.

## Units
| Unit | File | Change (what, where, AC) | Check | Risky | Author | Reviewer | Tokens (in / out) | Status |
|---|---|---|---|---|---|---|---|---|
| U1 | spec §2.2 파일, 링크 대상 30개 | `git mv`, 옛 경로 치환, 영어 문서 `.en.md` 링크 (AC-1, AC-3, AC-4) | `git ls-files docs`; AC-3·AC-4 `git grep` | no | lead (scripted) | 문서 게이트 링크 검사 | — | done |
| U2 | `.agent/scripts/lint_docs.py` | `TODO` 경로, `check_evolution_pairs` (AC-2, AC-6) | 짝 없는 12건 WARN 확인 | no | lead (small), review fixes lead (small) | cpp-reviewer R2: 4건(3건 고침), R3: none | — | done |
| U3 | `.agent/scripts/test_agent_scripts.py` | 짝 검사 테스트 (AC-2) | unittest 71 OK | no | lead (small), review fixes lead (small) | cpp-reviewer R2: 4건(3건 고침), R3: none | — | done |
| U4 | `docs/cpp_evolution/<topic>.md` ×9 | 한국어 번역 (AC-2, AC-7) | 코드 블록이 원문과 같음(스크립트), 짝 WARN 0 | no | lead | cpp-reviewer R1: 표현 3건, 고침 | — | done |
| U5 | `const_return_type.en.md`, `modern_ring_buffer_architecture.en.md` | 영어 번역 (AC-2, AC-7) | 짝 WARN 0 | no | lead | cpp-reviewer R2: 3건 고침, "(in Korean)" 유지 | — | done |
| U6 | `docs/cpp_evolution.md`, `.en.md` | 목차 (AC-2) | 링크 오류 0 | no | lead | cpp-reviewer R2: 2건 고침, 행 모두 사실 | — | done |
| U7 | spec §8 규칙·README·KI | 규칙 문구, 새 KI 두 개 | 문서 게이트 0/0 | no | lead | 문서 게이트(링크), R2가 목차 행의 근거 확인 | — | done |
