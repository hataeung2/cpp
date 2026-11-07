---
id: 090-12-01
title: 서브 에이전트가 프로젝트 규칙을 빠짐없이 받는다 — Core 하나, 러너가 단위 종류별로 붙임
depends_on: [090-12]
unblocks: []
approved: 2026-11-06
---

# Spec 090-12-01: 서브 에이전트가 프로젝트 규칙을 빠짐없이 받는다

원래 스펙: [090-12 서브 에이전트는 부트를 읽지 않는다](/docs/specs/090_12_runner_subagent_preamble.md) (그 앞: [090-08](/docs/specs/090_08_boot_read_budget.md) Assumption 7).

**다시 여는 이유** (2026-11-06, ai_sec에서 090-08~12를 옮기며 한 평가, 사용자 요청으로 다시 조사):
- 090-08이 서브 에이전트의 부트를 "프롬프트만 따른다"로 바꿨다. 부트를 돌던 때는 트리거 표를 보고 `impl.md` 등을 읽을 수 있었지만, 그 대신 규칙을 전달하는 장치는 만들지 않았다. 090-12는 같은 문장("follow this prompt only")을 진입 파일과 러너에 넣어 서브 에이전트가 스스로 규칙을 찾을 여지도 없앴다.
- [delegation.md](/.agent/rules/delegation.md) §4 "Every prompt states"는 행동 제약(git 금지, 범위, "모르면 모른다")만 있고, 그것도 lead가 매번 손으로 쓴다.
- 서브 에이전트별로 빠진 것:
  - agy `flash`(코드·테스트·레슨 작성): `impl.md`(naming, `#pragma once`, `using namespace std` 금지, 빈 catch 금지, `std::expected`, `std::format`, `#ifdef`, module, backend), 테스트 단위의 `test.md` §2, 레슨 단위의 `lessons/README.md` 작성 안내, preset으로만 빌드. agy에는 hook이 없다(090-11).
  - codex `luna`(위험 단위 리뷰): §6.2 질문은 spec·AC 일치뿐이다. 위험 목록과 naming 체크리스트를 받지 않는다.
  - `cpp-reviewer`: 정의에 위험 목록과 naming은 있지만 `impl.md`의 나머지는 없다.
- 사후 검사(`naming_check`는 함수 이름만, 컴파일러 경고, commit 때 machine path)로 잡히지 않는 것이 많다. 020-04에서는 agy 코드의 lambda 이름 7개를 사후에 고쳤다. fix 라운드 한 번은 115k token이다(010-10).
- camelCase 줄이 `CLAUDE.md`에만 있다(원본은 `impl.md`). Codex·Antigravity lead는 부트 때 보지 못한다.

## 0. Assumptions (please review)

| # | Decision | Rejected alternative | Why |
|---|---|---|---|
| 1 | **Core 하나**: [impl.md](/.agent/rules/impl.md) 맨 앞에 `## Core` 섹션(1.5 KB 이하). 모든 agent(lead와 서브 에이전트)가 지켜야 하고 빠지면 재작업이 되는 것만: C++ 표준, C++ naming 전체, C++ 필수·금지(`#pragma once`, `using namespace std`, C cast·`void*`, 빈 catch, `std::expected`/`optional`, `std::format`, `#ifdef` 남발, public 헤더의 외부 헤더, backend 뒤의 외부 의존, `// MACRO:`), 상대 경로만, 빌드·테스트는 `build.py --preset`으로만, secret 파일을 열지 않음, 범위. 마지막 줄은 "이럴 때 읽을 곳"(module → §2a, backend → §5, `cpp_evolution` → §6) | 새 파일 `core.md` | 규칙 원본은 `.agent/rules/`에 있고 Antigravity가 그대로 읽는다. 새 rule 파일이면 트리거 표와 frontmatter가 하나 더 생긴다 |
| 2 | **Core로 옮긴 규칙은 뒤 절에서 지운다**(naming 목록 등). 뒤 절에는 Core가 담지 못하는 세부만 남긴다 | 두 곳에 둠 | 원본은 하나 |
| 3 | **서브 에이전트 제한도 원본 하나**: delegation.md §4 "Every prompt states"의 목록(모르면 모른다, 직접 편집·도우미 스크립트 금지, git 명령 금지, 루트에 파일 금지, 이름 붙은 파일만)을 `### Sub-agent limits` 소절로 둔다. lead는 이제 쓰지 않는다 | lead가 계속 씀 | 빠뜨릴 수 없다 |
| 4 | **러너가 단위 종류에 따라 붙인다**: `subagent_run.py --kind code\|test\|lesson\|review\|research`(필수). 붙이는 것: 모두 Core + Sub-agent limits; `test`는 `test.md` §2; `lesson`은 `lessons/README.md` "레슨 작성 안내"; `review`는 리뷰 체크리스트(#5). 대응표는 러너의 상수 하나다 | `--kind` 생략 가능 | 생략할 수 있으면 lead가 빠뜨린다. 모델 판단 없이 스크립트가 넣는다 |
| 5 | **리뷰 체크리스트 원본은 delegation.md §8** `### Review checklist`(지금 `cpp-reviewer.md`의 위험 목록과 naming을 옮김). `cpp-reviewer.md`는 목록을 갖지 않고, 시작할 때 `py -3 .agent/scripts/subagent_run.py --print-rules review`(Linux `python3`)를 실행해 그 출력을 따른다 | 목록을 `cpp-reviewer.md`에 둠 | codex 리뷰어와 `cpp-reviewer`가 같은 목록을 받는다. Agent tool 정의는 파일을 포함할 수 없어서 명령 한 번으로 받는다 |
| 6 | **`--print-rules <kind>`**: 러너가 붙일 내용을 그대로 출력하고 끝낸다(모델 호출 없음). lead와 사람이 확인할 때도 쓴다 | — | 붙는 내용을 눈으로 볼 수 있다 |
| 7 | **프롬프트 순서**: 머리말 → `## Project rules (<kind>)`와 묶음 → `Context files:` 목록 → lead의 본문. 묶음 앞뒤는 빈 줄 | 규칙을 맨 끝에 | 작업 전에 규칙을 읽는다 |
| 8 | **머리말과 진입 파일 문장을 바꾼다**: 머리말 "You are a sub-agent started with this task prompt. Do not run the repository's boot sequence. Follow this prompt and the project rules in it." 진입 파일 3개 첫 줄 "A sub-agent started with a task prompt stops here: skip the boot sequence, follow the prompt and the project rules it carries." 이미 같은 머리말로 시작하는 프롬프트는 090-12처럼 한 번만 | 090-12 문장 유지 | "prompt only"가 규칙까지 막지 않게 한다 |
| 9 | **크기 한도**: Core 1.5 KB, 종류별 묶음(Core + limits + 추가 절) 8 KB. 넘으면 문서 게이트 ERROR. agy 프롬프트 한도(30,000자)는 묶음을 포함해서 잰다(090-12와 같음) | 한도 없음 | 지금 가장 큰 `test` 묶음이 약 6 KB(약 1.6k token)다. 묶음이 자라면 모든 호출이 비싸진다 |
| 10 | **문서 게이트가 묶음을 검사**: `lint_docs.py`가 러너의 대응표를 읽어 모든 종류의 묶음을 만들어 본다. 절이 없거나(제목이 바뀜) 한도를 넘으면 ERROR | 테스트만 | 규칙 문서의 제목을 고치는 쪽은 러너를 보지 않는다 |
| 11 | **lead도 Core를 본다**: `lint_docs.py --boot`가 todo 머리말 다음에 Core를 출력한다. `CLAUDE.md`의 camelCase 줄은 지운다 | 진입 파일마다 규칙 | 어느 tool이 lead여도 같은 Core를 같은 길로 받는다 |
| 12 | **레슨 매니페스트 규칙(`lessons/README.md` "매니페스트", 3.9 KB)은 묶음에 넣지 않는다** | `lesson`에 포함 | `tools/lessons.py check`가 문서 게이트에서 기계적으로 검사한다. 매니페스트 단위의 세부는 lead의 프롬프트(설계)에 있다 |
| 13 | **`Explore` 등 읽기만 하는 Claude Code 내장 서브 에이전트는 바꾸지 않는다** | — | 작성·리뷰를 하지 않는다 |

## 1. Objective
서브 에이전트가 작성·리뷰에 필요한 프로젝트 규칙을 모델 판단 없이 받는다. lead가 빠뜨릴 수 없고, 규칙 원본은 하나이며, 부트 비용은 다시 생기지 않는다. 재작업을 줄여 090-12의 목표(토큰 절약)를 이룬다.

## 2. Requirement Details

### 2.1 Public API Surface
라이브러리 API 변경 없음. 러너 CLI: `--kind`(필수, `--print-rules`와 함께일 때는 그 값), `--print-rules <kind>`(다른 인자 없이).

### 2.2 Internal Implementation
- `subagent_run.py`:
  - `RULE_SECTIONS: dict[str, list[tuple[str, str]]]`: kind → (repo-relative 파일, 절 제목) 목록. 공통 앞부분은 `impl.md` `## Core`, `delegation.md` `### Sub-agent limits`.
  - `rule_bundle(kind) -> str`: 각 절을 제목 줄부터 같은 수준 이하의 다음 제목 앞까지 잘라 잇는다. 절이 없으면 `InputError`(exit 2).
  - `build_prompt(text, files, kind)`: §0 #7 순서. 090-12의 중복 머리말 처리는 그대로.
  - Python 스크립트는 지금처럼 snake_case다. camelCase는 C++ 규칙이고 `naming_check`도 C++만 본다. Core의 naming 줄은 "C++"라고 밝힌다.
- `lint_docs.py`: §0 #9, #10 검사; `--boot`에 Core 출력.
- `test_agent_scripts.py`: 종류별 묶음, 필수 `--kind`, `--print-rules`, 절 누락, 한도, 프롬프트 순서, `--boot` 출력.
- 문서: `impl.md` Core와 뒤 절 정리, delegation.md §4·§6.2·§8, `cpp-reviewer.md`, 진입 파일 3개, `CLAUDE.md` camelCase 줄, develop-task skill(+복사본), 부트 문서의 sub-agent 문장과 Quick reference의 러너 행.

### 2.3 Platform Specifics
`cpp-reviewer.md`의 명령은 Windows `py -3`, Linux `python3`(부트 문서 표기와 같음).

## 3. C++ Standard Evolution
N/A

## 4. Edge Cases
- [x] 규칙 문서의 절 제목이 바뀜: 러너는 exit 2, 문서 게이트는 ERROR(§0 #10).
- [x] 묶음 때문에 agy 한도를 넘음: exit 2(지금과 같음). 한도 안의 lead 본문 자리는 약 22,000자.
- [x] `--resume`: 090-12와 같이 매번 붙인다(머리말과 묶음). 같은 대화에 묶음이 다시 들어가지만, resume은 리뷰 지적을 돌려줄 때라 규칙을 다시 보는 편이 낫다.
- [x] `cpp-reviewer`가 `--print-rules`를 실행하지 못함(Python 없음): 정의에 "실행 못 하면 그렇게 답하고 멈춘다".
- [x] 절 안의 코드 블록에 `## `로 시작하는 줄: 펜스 안은 제목으로 보지 않는다.
- N/A Thread safety, lifetime, MSVC/Clang, templates, ODR, UB: C++ 코드 없음.

## 5. Acceptance Criteria

| ID | Criterion | Verified by |
|---|---|---|
| AC-1 | 다섯 종류 모두 묶음 = Core + Sub-agent limits (+ 종류별 절)이고, 프롬프트 순서가 §0 #7이다 | `test_agent_scripts.py` |
| AC-2 | `--kind` 없이 부르면 exit 2; 절이 없으면 exit 2와 파일·제목을 말하는 메시지 | 테스트 |
| AC-3 | `--print-rules <kind>`가 모델을 부르지 않고 묶음을 출력한다 | 테스트(subprocess mock이 불리지 않음) |
| AC-4 | 문서 게이트가 절 누락, Core 1.5 KB 초과, 묶음 8 KB 초과를 ERROR로 낸다; 지금 저장소는 0 error | 테스트 + `lint_docs.py` |
| AC-5 | `--boot`가 Core를 출력하고, `CLAUDE.md`에 camelCase 줄이 없다 | 테스트 + `grep` |
| AC-6 | Core의 규칙이 `impl.md` 뒤 절에 두 번 있지 않다(naming 목록 등); 위험 목록은 delegation.md §8에만 있고 `cpp-reviewer.md`는 `--print-rules review`를 가리킨다; delegation.md §4에 lead가 쓰는 목록이 없다 | `grep`, 읽기 |
| AC-7 | 실제 호출: agy `flash --read-only --kind code`에 "받은 규칙에서 멤버 변수와 상수 이름 규칙, 빌드 명령을 그대로 인용하라"를 물으면 Core 문장을 인용한다(프롬프트 본문에는 규칙을 쓰지 않음) | 응답을 `testrecord.md`에 |
| AC-8 | 실제 호출: `cpp-reviewer`가 `--print-rules review`를 실행하고 체크리스트를 인용한다 | 새 Claude Code 세션(정의 파일을 고친 세션에서는 로드되지 않음, delegation.md §8) — 사용자 확인 또는 다음 세션의 lead |

## 6. Out of Scope
- Python 스크립트의 naming 규칙 — 지금처럼 snake_case, 이 task는 문서화하지 않는다.
- Codex·Antigravity를 lead로 한 확인 — 090-12와 같음(KI-049).
- 다른 저장소 — 사용자 결정(090-12).

## 7. Dependencies & Backends
none.

## 8. Documentation Updates

| Document | Section | Change |
|---|---|---|
| [impl.md](/.agent/rules/impl.md) | 새 `## Core`, §1·§3·§4·§5·§7 | Core; 옮긴 규칙 삭제 |
| [delegation.md](/.agent/rules/delegation.md) | §4, §6.2, §8 | `### Sub-agent limits`, `--kind`, `### Review checklist` |
| [cpp-reviewer](/.claude/agents/cpp-reviewer.md) | 전체 | 목록 대신 `--print-rules review` |
| [CLAUDE.md](/CLAUDE.md), [AGENTS.md](/AGENTS.md), [boot.md](/.agent/rules/boot.md) | 첫 줄; `CLAUDE.md` camelCase 줄 | §0 #8 문장; 삭제 |
| [agent_start_prompt.md](/docs/agent_start_prompt.md) | sub-agent 문장, Boot 2, Quick reference 러너 행 | 규칙은 러너가 붙임; `--boot`가 Core 출력; `--kind` |
| [develop-task skill](/.agent/skills/develop-task/SKILL.md) | 4단계 | `--kind` |
| [090-12 spec](/docs/specs/090_12_runner_subagent_preamble.md) | History | 090-12-01 |

## 9. Technical Constraints
Python 3 (Windows `py -3`, Linux `python3`). C++ 빌드와 무관.

## 10. Context & References
- [subagent_run.py](/.agent/scripts/subagent_run.py), [lint_docs.py](/.agent/scripts/lint_docs.py), [test_agent_scripts.py](/.agent/scripts/test_agent_scripts.py)
- 090-12 기록: [/docs/tasks/feature_090-12-runner-subagent-preamble/walkthrough.md](/docs/tasks/feature_090-12-runner-subagent-preamble/walkthrough.md)

## 11. Implementation Plan
- [ ] U1 `impl.md` Core, 뒤 절 정리 (lead, doc)
- [ ] U2 delegation.md §4 limits, §8 checklist, §6.2 (lead, doc)
- [ ] U3 `subagent_run.py` `--kind`, `--print-rules`, 묶음 (agy flash 또는 lead (small))
- [ ] U4 `lint_docs.py` 검사와 `--boot` Core (agy flash 또는 lead (small))
- [ ] U5 테스트 (U3·U4 확인 뒤)
- [ ] U6 진입 파일, `cpp-reviewer.md`, 부트 문서, skill + `sync_skills.py`, 090-12 History (lead)
- [ ] U7 AC-7 실제 호출; AC-8은 새 세션

## 12. Verification Plan
- [ ] `py -3 .agent/scripts/test_agent_scripts.py`
- [ ] `py -3 .agent/scripts/sync_skills.py --check`
- [ ] `py -3 .agent/scripts/lint_docs.py` exit 0
- [ ] `py -3 .agent/scripts/subagent_run.py --print-rules <kind>` 다섯 종류 출력 크기를 `testrecord.md`에
- [ ] AC-7, AC-8 결과를 `testrecord.md`에

## History / Amendments
- 2026-11-06: 초안.
