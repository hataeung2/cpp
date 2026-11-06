---
name: add-known-issue
description: Register a follow-up or non-blocking finding in atugcc as a new KI-NNN entry, or change a known issue's status (OPEN, PLANNED, DEFERRED, CLOSED). Use when a task, review or test leaves something for later, or when a deferred issue's condition happens.
---
# Add or change a known issue

Rules: the header of [`docs/known_issues.md`](/docs/known_issues.md). The status decides the file; `archive_docs.py` moves entries, never move them by hand.

## New entry
1. Next free id = the highest `KI-NNN` in all three files + 1:
   `grep -ho "^| KI-[0-9]*" docs/known_issues.md docs/known_issues_deferred.md docs/archive/known_issues_closed.md | sort | tail -1`
2. In `docs/known_issues.md`: a table row at the bottom of the table, `| KI-NNN | STATUS | Area | Found (task id) | Owner |`, and a section at the bottom of the file, `## KI-NNN — <one-line title>`, with what happens, why it matters and a `**Next**:` line.
3. Status and Owner:
   - `OPEN`: Owner `—` or the person or task to decide.
   - `PLANNED`: Owner = the task that will fix it.
   - `DEFERRED`: Owner = the condition to revisit it, e.g. `— (when the runner moves into a shared kit)`. A DEFERRED entry without a condition fails the docs gate.
4. Run `py -3 .agent/scripts/archive_docs.py`: a new `DEFERRED` entry moves to `docs/known_issues_deferred.md` (left in `docs/known_issues.md` it is a docs-gate WARN).
5. Refer to it by id (`KI-NNN`) from the walkthrough, testrecord or spec.

## Change a status
1. Edit only the Status cell (and the Owner cell: the closing task, `dropped: <reason>`, or the revisit condition). Add a closing line to the section when closing.
2. Run `py -3 .agent/scripts/archive_docs.py`: the row and section move to the file of the new status.

## Then
`py -3 .agent/scripts/lint_docs.py` exits 0. At task selection, `lint_docs.py --boot` shows a `BUDGET:` line when open or deferred entries exceed their limits.
