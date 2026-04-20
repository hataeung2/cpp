## Purpose
This file documents a concise, reliable sequence the agent should use to configure, build,
test and package the project locally on Windows or Linux. It prioritizes using
`CMakePresets.json` when available and provides an explicit fallback when presets are absent.

## Preconditions (Required)
- Visual Studio Build Tools (or Visual Studio) installed (Windows).
- `VsDevCmd.bat` or `vcvarsall.bat` available to initialize MSVC (Windows only).
- `cmake` available on PATH or via an explicit path.
- Preferably a `CMakePresets.json` file exists at the project root. If a preset uses a toolchain file
  (e.g. vcpkg), ensure that path exists on disk.

## Design Principles (Summary)
- `CMakePresets.json` is the authoritative source for configure/build settings (`toolchain`, `generator`, `binaryDir`).
- Follow a simple ordered sequence: select preset → init environment (if MSVC) → configure → build → test → package.
- Provide a clear fallback path when presets are not available.

## Recommended Agent Build Procedure (Mechanical Sequence)

When `CMakePresets.json` is present, prefer the preset-driven workflow below. The agent should
extract `binaryDir`, `cacheVariables.CMAKE_BUILD_TYPE`, and any `toolchainFile` from the selected preset.

1) Select a configure preset
- Load `CMakePresets.json` from project root and detect the host OS (`Windows` or `Linux`).
- Use a priority list of names (examples):
  - Windows: `windows-x64-debug`, `windows-x64-release`, `windows-x64-relwithdebinfo`.
  - Linux: `linux-x64-debug`, `linux-x64-release`, `linux-x64-relwithdebinfo`.
- If no preferred name matches, select the first preset with a condition matching the host, or fall back to `base`.

2) Initialize environment (Windows/MSVC only)
- If the chosen preset targets MSVC, initialize the MSVC developer environment before running `cmake --preset`.
- Example (cmd):
  ```
  cmd.exe /c '"C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\Common7\Tools\VsDevCmd.bat" -arch=x64 -host_arch=x64 && cmake --preset <configurePreset>'
  ```
- Recommendation: run environment init, configure, and build as separate steps for easier debugging.

3) Configure
- Run: `cmake --preset <configurePreset>`
- If the preset references `CMAKE_TOOLCHAIN_FILE` or `toolchainFile`, verify that path exists before proceeding.

4) Build
- Preferred: `cmake --build --preset <buildPreset> --config <CMAKE_BUILD_TYPE>`
- If the build preset implicitly sets the config, `--config` may be omitted.
- For parallel builds (N jobs): `cmake --build . -- -j N` (ensures Ninja receives `-j`).

5) Test
- Run tests from the preset's `binaryDir`:
  ```
  ctest --test-dir "<binaryDir>" -C <CMAKE_BUILD_TYPE> --output-on-failure
  ```

6) Package
- Prefer using CMake install to populate a deployable `dist` tree. Ensure the project's `CMakeLists.txt` defines `install()` rules for targets, libraries, and headers (for example: `install(TARGETS myapp RUNTIME DESTINATION bin LIBRARY DESTINATION lib ARCHIVE DESTINATION lib)` and `install(DIRECTORY include/ DESTINATION include)`).

- Recommended approaches:
  - Set `CMAKE_INSTALL_PREFIX` in the selected configure preset (for example `${sourceDir}/dist/${presetName}`) so installs go to `dist/<config>` by default.
  - After building, run one of the following to install files into `dist`:
    - `cmake --install "<binaryDir>" --prefix "<sourceDir>/dist/<config>" --config <CMAKE_BUILD_TYPE>`
    - or: `cmake --build "<binaryDir>" --target install --config <CMAKE_BUILD_TYPE>` (or use `cmake --build --preset <buildPreset> --target install --config <CMAKE_BUILD_TYPE>` when using presets)

- Result: the install step produces `dist/<config>/bin`, `dist/<config>/lib`, and `dist/<config>/include` (if install rules exist).

- Optionally create an archive from the `dist` tree:
  - Windows: `Compress-Archive -Path "<sourceDir>/dist/<config>\*" -DestinationPath "artifacts\cpp-windows-<arch>-<config>.zip"`
  - Linux: `zip -r artifacts/cpp-linux-<arch>-<config>.zip dist/<config>`

## Agent implementation notes (selection + examples)

Keep the preset-selection algorithm simple and deterministic:

- Preferred-name -> condition match -> first configurePreset -> error/fallback to `base`.

Example Python pseudocode (concise):

```python
import json, platform
presets = json.load(open('CMakePresets.json'))
host = 'Windows' if platform.system() == 'Windows' else 'Linux'
def pick_preset(presets, host):
	preferred = ['windows-x64-debug','windows-x64-release','windows-x64-relwithdebinfo'] if host=='Windows' else ['linux-x64-debug','linux-x64-release','linux-x64-relwithdebinfo']
	for p in presets.get('configurePresets',[]):
		if p.get('name') in preferred:
			return p
	for p in presets.get('configurePresets',[]):
		cond = p.get('condition',{})
		if cond.get('lhs')=='${hostSystemName}' and cond.get('rhs')==host:
			return p
	# fallback
	for p in presets.get('configurePresets',[]):
		if p.get('name')=='base':
			return p
	raise RuntimeError('No suitable preset found')

# Next steps: verify toolchainFile exists, init MSVC if needed, then run cmake commands
```

## Common issues and recommended fixes (Quick fixes)

- Cannot find standard headers (e.g., `<atomic>`):
  - Cause: MSVC environment not initialized. Run `VsDevCmd.bat -arch=x64 -host_arch=x64` and rebuild.

- Linker errors / architecture mismatch:
  - Cause: wrong toolset/environment (e.g., x86 vs x64). Ensure `VsDevCmd.bat` is called with correct `-arch`/`-host_arch` flags.

- Missing `toolchainFile` (vcpkg):
  - Check `toolchainFile` or `cacheVariables.CMAKE_TOOLCHAIN_FILE` in the preset.
  - Fix: install vcpkg or update the preset to a valid path (e.g. `C:/vcpkg/scripts/buildsystems/vcpkg.cmake`).

- PowerShell quoting issues:
  - Wrap complex chains with `cmd.exe /c '... && ...'` or use argument arrays to avoid shell parsing problems.

- Ninja `-j` not passed:
  - Use `cmake --build . -- -j N` to forward `-j` to Ninja reliably.

- `ctest` shows no tests or tests fail:
  - Verify the `binaryDir` and `-C <config>` values; re-run with `--output-on-failure` for details.

- Packaging / permission issues:
  - On Windows prefer `Compress-Archive` and watch for file locks and path length limits.

## How the agent should reference this file (Recommended rules)

Pre-execution sequence when presets are available:
1. Parse `CMakePresets.json` and select a configure preset.
2. If the preset targets MSVC: initialize the MSVC environment (`VsDevCmd.bat`) before configure.
3. Run `cmake --preset <configurePreset>`.
4. Run `cmake --build --preset <buildPreset> [--config <...>]`.
5. Run tests with `ctest --test-dir "<binaryDir>" -C <CMAKE_BUILD_TYPE> --output-on-failure` and then package.

Exceptions / preset guidance:
- If no suitable preset exists, do NOT run ad-hoc fallback commands (for example `cmake -S . -B build ...`). Instead, create a configure preset and a corresponding build preset in `CMakePresets.json` so the configuration is reproducible and IDE/CI-friendly.

- Minimal example to add to `CMakePresets.json` (edit paths as needed):

```json
{
  "version": 3,
  "configurePresets": [
    {
      "name": "linux-x64-debug",
      "displayName": "Linux x64 Debug",
      "generator": "Ninja",
      "binaryDir": "${sourceDir}/build/linux-x64-debug",
      "cacheVariables": {
        "CMAKE_BUILD_TYPE": "Debug"
      },
      "condition": {
        "lhs": "${hostSystemName}",
        "rhs": "Linux"
      }
    }
  ],
  "buildPresets": [
    {
      "name": "linux-x64-debug",
      "configurePreset": "linux-x64-debug"
    }
  ]
}
```

- If a required `toolchainFile` is missing, return a clear error and request that the user provide or install it.