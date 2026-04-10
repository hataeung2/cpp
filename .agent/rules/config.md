## Purpose
This file is a mechanical execution procedure and troubleshooting checklist to help the agent reliably
build, test, and package the project locally (Windows/Linux).

## Preconditions (Required)
- Visual Studio Build Tools (or Visual Studio) must be installed.
- `VsDevCmd.bat` or `vcvarsall.bat` must be available to initialize the MSVC environment (Windows).
- `cmake` must be on the system PATH or available via an explicit path.
- A `CMakePresets.json` file must exist at the project root. If using the vcpkg toolchain, ensure `C:/vcpkg`
	or the `toolchainFile` path referenced by the preset exists.

## Design Principles (Summary)
- `CMakePresets.json` is the authoritative source for build settings (toolchain, generator, `binaryDir`).
- This file (`.agent/rules/config.md`) contains procedural rules, environment initialization steps, and
	exception handling guidance the agent should follow.
- The agent should first parse `CMakePresets.json` to select an appropriate preset and then run the
	sequence: environment initialization (VS dev cmd etc) → configure → build → test → package.

## Recommended Agent Build Procedure (Mechanical Sequence)
1) Parse `CMakePresets.json`
	 - Load `CMakePresets.json` from the project root.
	 - Detect the host OS (`Windows` or `Linux`).
	 - Prefer an OS-appropriate configure preset. Example priority:
		 - Windows: `windows-x64-debug`, `windows-x64-release`, `windows-x64-relwithdebinfo`, or presets
			 with a condition for `Windows`.
		 - Linux: `linux-x64-debug`, `linux-x64-release`, `linux-x64-relwithdebinfo`, or presets with a
			 condition for `Linux`.
	 - Extract `binaryDir`, `cacheVariables.CMAKE_BUILD_TYPE`, `toolchainFile`, and any other relevant
		 cache variables from the selected preset.

2) Windows + MSVC (environment initialization)
	 - If the selected preset uses MSVC, initialize the toolchain environment by running `VsDevCmd.bat`.
	 - Example (single-line cmd chain):
		 ```
		 cmd.exe /c '"C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\Common7\Tools\VsDevCmd.bat" -arch=x64 -host_arch=x64 && cmake --preset windows-x64-debug'
		 ```
	 - Recommendation: run environment initialization, configure, and build as separate steps to simplify
		 debugging.

3) Configure
	 - Run `cmake --preset <configurePreset>`.
	 - If the preset specifies a `CMAKE_TOOLCHAIN_FILE` or a `toolchainFile`, verify the file exists before
		 proceeding.

4) Build
	 - Run `cmake --build --preset <buildPreset> --config <CMAKE_BUILD_TYPE>` or
		 `cmake --build --preset <buildPreset>` if the preset determines the config.
	 - For parallel builds, pass the job count as: `cmake --build . -- -j N`.

5) Test
	 - Run tests using the `binaryDir`:
		 ```
		 ctest --test-dir "<binaryDir>" -C <CMAKE_BUILD_TYPE> --output-on-failure
		 ```

6) Package
	 - Windows: `Compress-Archive -Path "<binaryDir>\*" -DestinationPath "artifacts\cpp-windows-<arch>-<config>.zip"`
	 - Linux: `zip -r artifacts/cpp-linux-<arch>-<config>.zip <binaryDir>`

## Agent implementation notes (simple selection algorithm example, Python pseudocode)
```python
import json
import platform
import pathlib
import subprocess

presets = json.load(open("CMakePresets.json"))
host = "Windows" if platform.system() == "Windows" else "Linux"

def pick_preset(presets, host):
		# Priority: name-based preferred list -> condition filter -> first match
		preferred = ["windows-x64-debug", "windows-x64-release", "windows-x64-relwithdebinfo"] if host == "Windows" else ["linux-x64-debug", "linux-x64-release", "linux-x64-relwithdebinfo"]
		for p in presets.get("configurePresets", []):
				if p.get("name") in preferred:
						return p
		for p in presets.get("configurePresets", []):
				cond = p.get("condition", {})
				if cond.get("lhs") == "${hostSystemName}" and cond.get("rhs") == host:
						return p
		raise RuntimeError("No suitable preset found")

# Next steps: check toolchain file existence, run VsDevCmd on Windows, execute cmake commands
```

## Common issues and recommended fixes (Quick fixes)
- Cannot find standard headers (e.g., `<atomic>`):
	- Cause: MSVC environment not initialized. Run `VsDevCmd.bat -arch=x64 -host_arch=x64` and rebuild.

- Linker errors (missing symbols) / architecture mismatch:
	- Cause: wrong toolset/environment (e.g., x86 vs x64). Ensure `VsDevCmd.bat` is called with correct
		`-arch`/`-host_arch` flags.

- `toolchainFile` specified in `CMakePresets.json` is missing (vcpkg):
	- Check the preset's `toolchainFile` or `cacheVariables.CMAKE_TOOLCHAIN_FILE`.
	- Fix: install vcpkg or update the preset to point to a valid toolchain file (for example
		`C:/vcpkg/scripts/buildsystems/vcpkg.cmake`).

- PowerShell argument/quoting issues:
	- Fix: wrap complex chains in `cmd.exe /c '... && ...'` or invoke processes with argument arrays to
		avoid shell parsing issues.

- Ninja `-j` failed to be passed:
	- Recommendation: use `cmake --build . -- -j N` so the `-j` flag is passed to Ninja reliably.

- `ctest` shows no tests or tests fail:
	- Verify `binaryDir` and `-C <config>` are correct, and re-run with `--output-on-failure` for details.

- Packaging / permission issues:
	- On Windows prefer `Compress-Archive`; watch for file locks and path length limitations.

## How the agent should reference this file (Recommended rules)
- Pre-execution sequence:
	1. Parse `CMakePresets.json` → select preset
	2. If Windows+MSVC: initialize environment with `VsDevCmd.bat` (verify architecture)
	3. `cmake --preset <configurePreset>`
	4. `cmake --build --preset <buildPreset> [--config <...>]`
	5. Run `ctest` → compress artifacts

- Exceptions / fallback:
	- If a suitable preset is not found use the `base` preset or the first configurePreset matching conditions.
	- If the toolchain file is missing return a clear error asking the user to install or provide the path.

--- 
If you'd like, I can also create a small Python or PowerShell helper script that parses `CMakePresets.json`
and runs the recommended sequence automatically.
