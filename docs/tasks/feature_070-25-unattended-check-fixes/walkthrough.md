# Walkthrough: 070-25 무인 확인을 흐리는 KI 정리

Spec: [/docs/specs/070_25_unattended_check_fixes.md](/docs/specs/070_25_unattended_check_fixes.md) · Plan: [plan.md](plan.md) · Test record: [testrecord.md](testrecord.md)

## Result
- **KI-050**: `lessons/support/crt_report.cpp`, linked into every lesson and practice target through `atugcc_lesson_console`, sends Debug CRT error and assert reports to stderr and switches off Windows Error Reporting when no debugger is attached. An uncaught exception in a `windows-x64-debug` lesson now prints `abort() has been called` and ends with exit code 3 in about 0.1 s. Under a debugger the dialog stays. `thread_and_log` `remove_join` is an automatic exercise now (`exit = "nonzero"`, `thread_.join()` gone from `legacy_worker.hpp`).
- **KI-052**: the cause was the case of the drive letter in the working directory, not `--prefix`. `npm test` starts Vitest through `web/frontend/scripts/vitest.mjs`, which moves to the upper-case spelling first. The documented command did not change.
- **KI-053**: `device_state_machine` waits on a `std::latch` for tick `kTicks` (6) instead of 120 ms.

## Deviations from the spec
- `_WRITE_ABORT_MSG` is kept on (spec Assumption 2 listed it as cleared); without it nothing is printed and AC-1's "one stderr line" fails. Recorded in plan.md.
- AC-6 in WSL could not run: WSL's Node 18 is below Vitest 5's minimum. The frontend tests have only ever run on Windows. Upgrading WSL's Node was not part of this task; no KI, since no check depends on it (CI task 090-14 will pick its own Node).

## Follow-ups
None new. KI-050, KI-052, KI-053 closed.

## Lead (fallback) units
None.
