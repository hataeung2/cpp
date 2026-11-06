# Tasks (Archive)

DONE tasks. `py -3 .agent/scripts/archive_docs.py` moves a task here from docs/agent_todo.md when it and all its patch lines are DONE (workflow step 6). Group counts in agent_todo.md include these lines. A sealed record: do not edit entries.

---

## Phase 0: 프로젝트 기반 설정
- !DONE | 000-01 | [프로젝트 구조 재배치 및 CMake 현대화](/docs/specs/01_project_restructure.md) — legacy (branch: `feature/01_project_restructure`)

## Phase 1: 코어 모듈 전환 (atugcc::core)
- !DONE | 010-01 | [RingBuffer 모듈 C++20 전환](/docs/specs/03_ring_buffer_modernize.md) — legacy (branch: `feature/ring-buffer-modernize`)
- !DONE | 010-02 | [TimeStamp 모듈 C++20 전환](/docs/specs/04_timestamp_modernize.md) — legacy (branch: `feature/timestamp-modernize`)
- !DONE | 010-03 | [MemoryDump 플랫폼 추상화](/docs/specs/05_memory_dump_refactor.md) — legacy, 010-01 브랜치에서 함께 진행 (branch: `feature/ring-buffer-modernize`)
- !DONE | 010-04 | [dlog 매크로 → std::source_location 기반 함수 전환](/docs/specs/06_dlog_modernize.md) — legacy, 010-01 브랜치에서 함께 진행 (branch: `feature/ring-buffer-modernize`)
- !DONE | 010-05 | [ErrorCode / std::expected 통일 오류 처리 레이어](/docs/specs/09_error_expected.md) — legacy, 제안 상태로 구현 (branch: `feature/error-expected`)
- !DONE | 010-06 | [Logger 통합 퍼사드 (RingBuffer + dlog + MemoryDump)](/docs/specs/10_logger_facade.md) — legacy, 제안 상태로 구현 (branch: `feature/logger-facade`)
- !DONE | 010-07 | [Crash Dump 포맷 & 즉시 덤프](/docs/specs/09_001_dump_format.md) — legacy, todo 누락분 보충 (branch: `feature/error-expected-dump-impl`)
- !DONE | 010-08 | [Logger 정비: 호출 위치, 공유 계약, crash dump 준비, 로그 큐, 공유/스레드별 성능 측정](/docs/specs/010_08_logger_cleanup.md) — main에 병합, KI-013·014·021·025 종료, 측정 결과는 testrecord (branch: `feature/010-08-logger-cleanup`)
- !DONE | 010-09 | [Logger 스레드별 버퍼와 소비자 스레드: 잠금 없는 기록, 모든 스레드의 crash dump, 실패 유형별 로그 보존](/docs/specs/010_09_logger_thread_buffers.md) — main에 병합, KI-026·027 종료, 공유 Logger p99 4–8스레드 1.1–3.9µs, 처리량 한계 KI-028 (branch: `feature/010-09-logger-thread-buffers`)
  - !DONE | 010-09-01 | [Logger 전달 순서: 먼저 일어난 기록을 먼저 전달 (스레드 교대, KI-030)](/docs/specs/010_09_01_thread_handoff_order.md) — main에 병합, KI-030 종료, 두 단계 drain(묶음 상한), 같은 시계 눈금의 다른 스레드 호출만 예외 (branch: `feature/010-09-01-thread-handoff-order`)
- !DONE | 010-10 | [메모리 매핑 파일 로그 버퍼와 다음 실행 때 복구 (SIGKILL·강제 종료 대비)](/docs/specs/010_10_logger_mapped_buffers.md) — main에 병합, `configureLogBuffers({.mappedDir})` / `ATUGCC_LOG_MAP_DIR`, 복구 파일 `recovered_<시각>_<pid>.log`, KI-029·KI-030 (branch: `feature/010-10-logger-mapped-buffers`)

## Phase 2.0: 패턴 시각화 도구 (atugcc::pattern::viz)
- !DONE | 020-01 | [패턴 시각화 도구 구현: 터미널 트리·상태 흐름 트레이서(ANSI), 다이어그램 스니펫(PlantUML 기본, Mermaid/D2 선택)](/docs/specs/08_pattern_visualizer.md) — legacy (branch: `feature/pattern-visualizer`)
- !DONE | 020-02 | [전용 콘솔](/docs/specs/08_001_dedicated_console.md) — legacy (branch: `feature/dedicated-console`)
- !DONE | 020-04 | [다이어그램 가독성: 생성 예산 기반 분할, 반복 횟수 표기](/docs/specs/020_04_diagram_readability.md) — main에 병합 (branch: `feature/020-04-diagram-readability`)
- !DONE | 020-05 | [Tracer 이벤트 스트림: JSON Lines 구조화 출력](/docs/specs/020_05_tracer_event_stream.md) — main에 병합, 070-02 선행 (branch: `feature/020-05-tracer-event-stream`)
- !DONE | 020-06 | [Tracer 구간 시간 측정: span 이벤트와 집계](/docs/specs/020_06_tracer_span_timing.md) — main에 병합, 070-06 선행, 취소된 020-03의 목적도 맡음 (branch: `feature/020-06-tracer-span-timing`)

## Phase 2.3: 행동 패턴 (Behavioral Patterns)
- !DONE | 023-01 | [State — std::variant + std::visit 상태 머신 전이(기존 상태 -> 새 상태) 흐름도 출력](/docs/specs/08_pattern_visualizer.md) — legacy, 020-01에서 구현(`state.hpp`, Tracer, `StateMachineTest`), 레슨 `02_patterns/01_device_state_machine`; 090-05에서 동기화 (branch: `feature/pattern-visualizer`)

## Phase 4: 범용 라이브러리 (`libs/`, [후보 목록](/docs/lib_candidates.md)) / 시나리오 테스트
- !DONE | 040-01 | [shape / sound를 `sample/`로 옮기고 `libs/`를 라이브러리별 폴더 구조로 (KI-044)](/docs/specs/040_01_shape_sound_to_sample.md) — main에 병합. `sample/libs/`(samples를 켤 때만 빌드), `namespace sample`(Windows GDI `Rectangle()`과의 충돌), camelCase, `libs/CMakeLists.txt`는 구조 주석만. 후보를 고르면 `040-SS` 줄을 더한다([후보 목록](/docs/lib_candidates.md)). KI-044 종료, KI-046 (branch: `feature/040-01-shape-sound-to-sample`)
- !DONE | 040-02 | [CTest 시나리오 테스트: 단위 테스트 외에 시나리오를 추가하고 실행하는 기능 (GoogleTest 기반)](/docs/specs/040_02_ctest_scenario_tests.md) — main에 병합. 단계 도우미 `atugcc::test::Scenario`, 첫 시나리오 S1·S2, 별도 실행 파일 `atugcc_scenarios`, 시나리오마다 프로세스 하나(`scenario.<Suite>.<Name>`), label `unit`/`scenario`/`probe`, `build.py --label`, 테스트 리포트 `build.py --report`(`out/test-reports/`), 사용 안내 `tests/README.md`. KI-041 (branch: `feature/040-02-ctest-scenario-tests`)

## Phase 7: 웹 플레이그라운드 (로컬 전용)
- !DONE | 070-01 | [레슨 구조: 트랙·레슨·유닛, preset 빌드, 레슨 인덱스](/docs/specs/070_01_lesson_structure.md) — main에 병합 (branch: `feature/070-01-lesson-structure`)
- !DONE | 070-02 | [로컬 웹 플레이그라운드: 편집·빌드·실행·시각화](/docs/specs/070_02_web_playground.md) — main에 병합, `py -3 tools/playground.py --open` (branch: `feature/070-02-web-playground`)
  - !DONE | 070-02-01 | [플레이그라운드 --port를 페이지 포트로 (dev 모드 포함)](/docs/specs/070_02_01_playground_port.md) — main에 병합, KI-017 종료 (branch: `feature/070-02-01-playground-port`)
  - !DONE | 070-02-02 | [플레이그라운드가 WSL 서버에 닿지 않을 때 알려 주기](/docs/specs/070_02_02_playground_wsl_reach.md) — main에 병합. Windows에서 `/api/health`가 10초 안에 닿지 않으면 `wsl --shutdown` 안내와 함께 exit 1, KI-040 종료 (branch: `feature/070-02-02-playground-wsl-reach`)
- !DONE | 070-03 | [essentials 트랙 커리큘럼: 트랙 순서, 1차 레슨 4개(포맷, 오류, 호출 위치, 로그 복구), 기존 레슨·유닛 영어판](/docs/specs/070_03_essentials_curriculum.md) — main에 병합. 폴더 번호 = 최종 순서(빈 번호는 070-11·070-12), 새 레슨 `format_text`·`error_expected`·`source_location`·`log_recovery`, 레슨·유닛 모두 `README.en.md`, 출력 영어, 코드 주석 한/영, `lessons.py check`가 영어판 없음·한글 리터럴 경고. KI-033, KI-034 (branch: `feature/070-03-essentials-curriculum`)
- !DONE | 070-06 | [장시간 실행 프로필과 구간 시간(Timings) 화면](/docs/specs/070_06_long_run_timings.md) — main에 병합, 서버 span 집계(설계 기록 §2.4), 레슨 `span_timing` (branch: `feature/070-06-long-run-timings`)
- !DONE | 070-08 | [플레이그라운드 소개 페이지 (이 페이지와 라이브러리·레슨의 관계)](/docs/specs/070_08_playground_intro.md) — main에 병합, `lessons/intro.md` + ⓘ 소개, 루트 README Workflow (branch: `feature/070-08-playground-intro`)
- !DONE | 070-10 | [플레이그라운드 레슨·기능 검색과 한/영 전환](/docs/specs/070_10_lesson_search_i18n.md) — main에 병합. 매니페스트 `title_en`·`summary_en`, 태그 어휘 `lessons/tags.toml`, 검색창(`/`, 태그 칩), UI 사전 `i18n.ts`와 `EN`/`한` 버튼, `intro.en.md`. 레슨 출력은 영어(070-03이 기존 레슨을 고침) (branch: `feature/070-10-lesson-search-i18n`)
- !DONE | 070-11 | [essentials 2차 레슨: 문법 (E14 `const`의 위치, E1 concepts, E5 ranges, E6 variant)](/docs/specs/070_11_essentials_syntax_lessons.md) — main에 병합. 레슨 `const_correctness`(deducing this, `const` 반환의 복사·이동 표), `concepts`, `ranges_views`(C++23 뷰, 호출 형식 `ranges::to`, `dangling`/`owning_view`), `variant_visit`, 태그 `const`·`concepts`·`ranges`·`variant`, `concepts.md`, `const_return_type_guide.md` 수정. KI-033에 `std::forward_like` (branch: `feature/070-11-essentials-syntax`)
- !DONE | 070-12 | [essentials 3차 레슨: 시간·파일·동시성 (E8 chrono, E9 filesystem, E12 lock-free 링 버퍼)](/docs/specs/070_12_essentials_time_file_lockfree.md) — main에 병합. 레슨 `chrono_time`(고정된 순간의 시간대 변환, `%z`, `parse`), `filesystem_paths`(`fs_sandbox`, 예외·`error_code`·`Expected`, `clock_cast`), `lock_free_buffer`(long, release/acquire SPSC vs mutex 큐, false sharing, TSan과 `relaxed` 사본), 태그 `chrono`·`filesystem`·`lock_free`, `filesystem.md`. essentials 14개 완성. MSVC `file_clock`에 `to_sys` 없음(스펙 History) (branch: `feature/070-12-essentials-time-file-lockfree`)
- !DONE | 070-13 | [C++20 modules를 Windows·Linux 양쪽에서 (Linux 툴체인 Clang 20, CMake 4)](/docs/specs/070_13_modules_clang_toolchain.md) — main에 병합. Linux preset 전부 Clang 20 + libstdc++ 14, CMake 4.0+, 모듈 스캔 항상 켬(끄면 configure 실패), `import atugcc.core;`(`modules/atugcc/core.cppm`, 헤더 래퍼)와 `tests/modules/`. KI-035 종료, KI-036–038 (branch: `feature/070-13-modules-clang-toolchain`)
- !DONE | 070-14 | [essentials modules 레슨(`.cppm` 레슨 소스 지원)과 `format_text`의 `std::print` 단계 (KI-033)](/docs/specs/070_14_essentials_modules_lesson.md) — main에 병합. 레슨 `modules`(`15_modules`: 주 인터페이스, 파티션 `:rect`, 구현 유닛, `import atugcc.core;`), `.cppm` 레슨 소스(`CXX_MODULES` file set), `uses`의 `mod:`, `lessons.py` 모듈 검사, 웹 `.cppm`, `format_text` 7단계 `std::print`. 연습 3의 오류는 Clang 기준(MSVC 19.51은 export하지 않은 import를 새게 함). KI-033 갱신, KI-039 (branch: `feature/070-14-essentials-modules-lesson`)
- !DONE | 070-15 | [essentials 테스트 레슨(단위·시나리오 테스트 작성과 테스트 리포트 읽기)과 레슨 빌드의 GoogleTest](/docs/specs/070_15_essentials_testing_lesson.md) — main에 병합. 레슨 `testing`(`16_testing`): 버전 파서에 단위 테스트(`TEST`, `EXPECT`/`ASSERT`, `TEST_P`, `TEST_F`, `PrintTo`)와 4단계 시나리오, README는 GoogleTest·CTest·리포트 튜토리얼(사용자 요청 2026-11-05, 명령마다 실제 실행). GoogleTest는 `cmake/atugcc_googletest.cmake` 한 곳(tests/와 레슨), 매니페스트 `gtest = true`, `uses`의 `test:`, `lessons.py` 검사 12개, 웹은 실패 줄 표시와 `GTEST_*` 제거. KI-042 (branch: `feature/070-15-essentials-testing-lesson`)

## Phase 9: 개발 프로세스 / 유지보수
- !DONE | 090-01 | [에이전트 운영 규칙 개선 (ai_sec 규칙 비교 반영)](/docs/specs/090_01_agent_process.md) — main에 병합 (branch: `feature/090-01-agent-process`)
- !DONE | 090-02 | [함수 명명 camelCase 통일](/docs/specs/090_02_camelcase_rename.md) — main에 병합 (branch: `feature/090-02-camelcase-rename`)
- !DONE | 090-03 | [vcpkg manifest로 Boost 자동 공급](/docs/specs/090_03_vcpkg_manifest.md) — main에 병합 (branch: `feature/090-03-vcpkg-manifest`)
- !DONE | 090-04 | [문서 게이트가 lessons/ Markdown 링크도 검사 (KI-019)](/docs/specs/090_04_lessons_doc_links.md) — main에 병합, KI-019 종료 (branch: `feature/090-04-lessons-doc-links`)
- !DONE | 090-05 | [백로그 동기화와 진행 순서 정리 (2026-10-29 점검)](/docs/specs/090_05_backlog_sync.md) — main에 병합(사용자 검토 2026-10-30). 020-03 취소, Phase 5 → 레슨 후보 목록, adapter → backend, KI-021–KI-024 (branch: `feature/090-05-backlog-sync`)
- !DONE | 090-06 | [개발 도구 정비: guard hook 명령 위치 판정(KI-008), 레슨 콘솔 UTF-8(KI-011), `build.py --gtest-filter`를 ctest로(KI-012)](/docs/specs/090_06_dev_tools_cleanup.md) — main에 병합, KI-008·011·012 종료, guard는 `shell_commands.py`로 실행되는 명령만 판정, `--gtest-filter`는 ctest+`GTEST_FILTER`, 레슨이 Windows 콘솔을 UTF-8로 바꾸고 되돌림, 새 KI-031·032 (branch: `feature/090-06-dev-tools-cleanup`)
- !DONE | 090-07 | [문서 구조 정리: learning → cpp_evolution 한/영 두 벌, agent_todo·lesson_candidates를 docs/로, artifacts → guides](/docs/specs/090_07_docs_layout.md) — main에 병합. evolution 페이지 11쌍 `<x>.md`(한)·`<x>.en.md`(영), 목차 `docs/cpp_evolution.md`(+`.en.md`), `lint_docs.py`가 짝·모양 검사, 봉인된 기록의 옮긴 경로 링크는 INFO. KI-043, KI-044 (branch: `feature/090-07-docs-layout`)
- !DONE | 090-08 | [부트와 편집 때의 읽기 줄이기: `lint_docs.py --boot`·`--ki`, CLOSED KI·DONE task archive, 서브 에이전트는 부트를 건너뜀](/docs/specs/090_08_boot_read_budget.md) — main에 병합. 부트는 `lint_docs.py --boot`(77 KB → 5.5 KB), `--ki`·`--deferred`; `archive_docs.py`가 상태에 따라 KI·DONE task를 옮김(DEFERRED 파일, archive); 한도는 task 선택 때 `BUDGET:` 줄; 첫 정리로 열린 KI 25 → 5. KI-047 (branch: `feature/090-08-boot-read-budget`)
- !DONE | 090-09 | [Antigravity 진입 rule: `always_on` rule 하나, rule frontmatter·트리거 표 검사](/docs/specs/090_09_antigravity_entry_rule.md) — main에 병합. `.agent/rules/boot.md`(always_on, 172 B), 문서 게이트가 rule frontmatter·트리거 표 검사. Antigravity 확인은 사용자(2026-11-06) (branch: `feature/090-09-antigravity-entry-rule`)
