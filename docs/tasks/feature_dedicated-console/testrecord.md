# Test Record: Dedicated Console Output Control

## Environment
- Repository: `cpp`
- Branch: `feature/dedicated-console`
- Host OS: Linux
- Configure preset: `linux-x64-relwithdebinfo`
- Build preset: `linux-x64-relwithdebinfo`

## Commands
1. `cmake --preset linux-x64-relwithdebinfo`
2. `cmake --build --preset linux-x64-relwithdebinfo`
3. `ctest --test-dir out/build/linux-x64-relwithdebinfo --output-on-failure`
4. `./out/build/linux-x64-relwithdebinfo/bin/atugcc_pattern_example`

## Results
- Configure: passed
- Build: passed
- Tests: passed (`1/1` CTest entry)
- Manual example run: passed

## Manual Verification Notes
- Demo 1 emitted live state/message lines through the dedicated console sink and still printed formatted snapshots.
- Demo 2 suppressed live sink output while keeping observer snapshots and PlantUML output intact.
- Demo 3 re-enabled live sink output and printed tree events plus formatted object tree output.
- Dedicated desktop sink now supports file-only fallback if a new terminal window cannot be launched; fallback path is exposed via `logPath()` and shown by the example.
- Desktop window behavior is configurable (`KeepOpen`/`AutoClose`) via `DesktopConsoleWindowMode`.

## Regression Notes
- Existing formatting APIs remained callable without sink configuration.
- Snapshot-based tests and observer/state integration tests remained green.