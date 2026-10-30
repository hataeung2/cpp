# Test Record: 090-04 문서 게이트가 `lessons/` Markdown 링크도 검사

- Spec: [/docs/specs/090_04_lessons_doc_links.md](/docs/specs/090_04_lessons_doc_links.md)
- Plan: [plan.md](/docs/tasks/feature_090-04-lessons-doc-links/plan.md)
- Date: 2026-10-29; host Windows 11, Python 3.15

## Runs
| # | Command | Expected | Actual | Status |
|---|---|---|---|---|
| R1 | dry run: `lint()` with `"lessons"` added, before the change | — | 8 files under `lessons/` checked, 0 findings | Info |
| R2 | `py -3 .agent/scripts/test_agent_scripts.py` | pass | 51 tests OK | Pass |
| R3 | mutant: `DOC_DIRS` without `"lessons"` (scratch copy, restored, `cmp` identical) | killed | `test_lesson_markdown_links_are_checked` fails, the other 50 pass | Pass |
| R4 | `py -3 .agent/scripts/lint_docs.py`, `naming_check.py` | exit 0 | 0 errors, 0 warnings; 0 | Pass |

## Acceptance Criteria
| AC | Evidence | Status |
|---|---|---|
| AC-1 | R2 `test_lesson_markdown_links_are_checked`: a root-relative and a relative broken link in `lessons/intro.md` are ERRORs, gone once the files exist (relative `../` link from a lesson README also resolves); R3 kills the mutant | Pass |
| AC-2 | R2, R4 | Pass |

## Reviews
| Unit | Reviewer | Result |
|---|---|---|
| U1–U3 | lead | one-line change; R3 mutant check instead of a reviewer call |
