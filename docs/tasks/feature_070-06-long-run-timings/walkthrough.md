# Walkthrough: 070-06 장시간 실행 프로필과 구간 시간(Timings) 화면

- Spec: [/docs/specs/070_06_long_run_timings.md](/docs/specs/070_06_long_run_timings.md) (design record for span aggregation: §2.4)
- Evidence: [testrecord.md](/docs/tasks/feature_070-06-long-run-timings/testrecord.md) (AC-1–AC-11 all Pass)
- Branch: `feature/070-06-long-run-timings`, merged into `main` by fast-forward

## Result
- **Long profile**: `[run] profile = "long"` runs up to the lesson's `timeout`, with an optimized build (`linux-x64-playground-release`, RelWithDebInfo) unless `[run] build = "debug"`, 8 MiB of output and the last 5,000 lines on the page. The page's **길게 실행** toggle switches the profile for one run; **측정기** passes `ATUGCC_SPAN_METER`.
- **Server span aggregation** ([spans.py](/web/server/spans.py), [runner.py](/web/server/runner.py)): span lines never travel one by one. Per (file, line, label, meter): exact count/total/min/max and a 1,024-value uniform sample for p50/p95 and the distribution. Changed keys go out as `spans` events; memory depends on the number of keys. Reads are bounded (4 MiB pieces, more while behind), lag is reported, and a 1 GiB trace-file budget stops a run that writes too much.
- **Timings tab** ([timings.ts](/web/frontend/src/timings.ts)): live table with sorting, jump to the line, distribution bars and the change against the previous run (browser storage; "빌드 다름" across build types). The editor shows `⏱ mean avg ×count` after each span line.
- **Lesson** [`span_timing`](/lessons/tracks/01_essentials/03_span_timing/README.md): `push_back` vs `reserve`, `std::map` vs `std::unordered_map`, timed for 15 s.
- Verified: MSVC and GCC builds, ASan, TSan, 52 server tests, 37 vitest, 17 browser checks plus a 60 s load check, 10/10 mutants killed.

## Notes
- The first AC-7 run showed the server falling behind a 100k spans/s flood (per-line path conversion); fixed by caching, per-piece publishing and catching up within a tick. Measured server throughput: about 150k span lines/s.
- Monaco 0.57 did not render `after` injected text for the inline times in this page; they use `afterContentClassName` with a generated `::after` rule per line.
- The AC-7 flood test is skipped on sanitizer builds (a sanitizer-built fixture cannot reach the rate; AC-7 measures the Python server).
- `[run] build` is passed to the page as written; page and runner apply the same rule.
- The p50 ±5 % bound of AC-9 holds for most seeds only (sampling spread with 1,024 values); see the testrecord's sampling note.

## Follow-ups
- KI-016: flush interval tail (070-06 shows a notice; C++ unchanged).
- KI-015: an escaped descendant can also delay `done` (note added).
- Spec §2.4 lists when to reconsider the aggregation design (C++ aggregate stream, FIFO, punch hole).
- No `lead (fallback)` units.
