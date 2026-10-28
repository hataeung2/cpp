#!/usr/bin/env python3
"""Configure, build and test through CMakePresets.json, the same way on every host.

Usage:
    py -3 .agent/scripts/build.py [--preset auto|<name>] [--target <t>] [--test] [--gtest-filter <f>] [--fresh] [--dry-run]

- `auto` picks `<host>-x64-debug`.
- Windows presets run inside the MSVC developer environment: VsDevCmd.bat from VSDEVCMD,
  or found with vswhere.
- Linux presets on a Windows host run in WSL (distribution: ATUGCC_WSL_DISTRO, else the default).
- Configure runs when the build directory has no cache (plain), after an interrupted
  configure (fresh), when a preset file is newer than the cache (plain: re-applies the
  preset's cacheVariables; a variable *removed* from a preset needs --fresh), with --fresh,
  or when any cache in it was recorded at another location (a copied checkout: the
  directory is removed first).

Exit code: the first failing step's exit code, 0 when every step passes.
Rules: .agent/rules/config.md, .agent/rules/test.md.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path, PurePosixPath, PureWindowsPath

REPO_ROOT = Path(__file__).resolve().parents[2]
TEST_EXE = "atugcc_tests"


def host_system() -> str:
    return "Windows" if platform.system() == "Windows" else "Linux"


def configure_presets(root: Path) -> list[str]:
    """Visible configure presets of CMakePresets.json and the untracked CMakeUserPresets.json."""
    names: list[str] = []
    for file in ("CMakePresets.json", "CMakeUserPresets.json"):
        path = root / file
        if path.is_file():
            data = json.loads(path.read_text(encoding="utf-8"))
            names += [p["name"] for p in data.get("configurePresets", []) if not p.get("hidden")]
    return names


def pick_preset(requested: str, host: str, available: list[str]) -> str:
    name = f"{host.lower()}-x64-debug" if requested == "auto" else requested
    if name not in available:
        raise ValueError(f"unknown preset {name!r}; available: {', '.join(available)}")
    return name


def preset_platform(preset: str) -> str:
    return "Windows" if preset.startswith("windows-") else "Linux"


def same_dir(a: str, b: str) -> bool:
    """Same directory: by file identity when both exist (junctions, subst drives,
    symlinks), else by text; case-insensitive only for drive-letter paths."""
    try:
        if Path(a).exists() and Path(b).exists():
            return os.path.samefile(a, b)
    except OSError:
        pass

    def norm(p: str) -> str:
        p = p.replace("\\", "/").rstrip("/")
        return p.lower() if re.match(r"^[A-Za-z]:", p) else p
    return norm(a) == norm(b)


def cache_value(cache: Path, key: str) -> str | None:
    if not cache.is_file():
        return None
    m = re.search(rf"^{key}:INTERNAL=(.*)$", cache.read_text(encoding="utf-8", errors="replace"), re.MULTILINE)
    return m.group(1).strip() if m else None


def cache_source_dir(cache: Path) -> str | None:
    return cache_value(cache, "CMAKE_HOME_DIRECTORY")


def moved_caches(build_dir: Path) -> list[Path]:
    """Caches (top level and FetchContent sub-builds) recorded at another location."""
    moved = []
    for cache in build_dir.rglob("CMakeCache.txt"):
        recorded = cache_value(cache, "CMAKE_CACHEFILE_DIR")
        if recorded and not same_dir(recorded, cache.parent.as_posix()):
            moved.append(cache)
    return moved


def configure_mode(build_dir: Path, source_dir: str, fresh: bool,
                   preset_files: tuple[Path, ...] = ()) -> str | None:
    """How to configure: None (reuse the build directory), 'plain', 'fresh', or 'stale'.

    'stale' = the build directory was made for another source directory (a copied
    checkout). `--fresh` is not enough there: FetchContent sub-builds keep their own
    caches, so the whole build directory is removed first.
    A cache without generated Ninja files is an interrupted configure: run it again fresh.
    A preset file newer than the cache: configure again ('plain' re-applies cacheVariables),
    because `cmake --build` does not watch preset files.
    """
    recorded = cache_source_dir(build_dir / "CMakeCache.txt")
    if (recorded is not None and not same_dir(recorded, source_dir)) or (build_dir.is_dir() and moved_caches(build_dir)):
        return "stale"
    if fresh:
        return "fresh"
    if recorded is None:
        return "plain"
    complete = (build_dir / "build.ninja").is_file() and (build_dir / "CMakeFiles" / "rules.ninja").is_file()
    if not complete:
        return "fresh"
    cache_time = (build_dir / "CMakeCache.txt").stat().st_mtime
    if any(f.is_file() and f.stat().st_mtime > cache_time for f in preset_files):
        return "plain"
    return None


def build_steps(preset: str, mode: str | None, target: str | None, test: bool,
                gtest_filter: str | None, exe_suffix: str) -> list[list[str]]:
    steps: list[list[str]] = []
    if mode is not None:
        steps.append(["cmake", "--preset", preset] + (["--fresh"] if mode in ("fresh", "stale") else []))
    steps.append(["cmake", "--build", "--preset", preset] + (["--target", target] if target else []))
    if test:
        steps.append(["ctest", "--preset", preset])
    if gtest_filter:
        exe = f"out/build/{preset}/bin/{TEST_EXE}{exe_suffix}"
        steps.append([exe, f"--gtest_filter={gtest_filter}"])
    return steps


def batch_script(vsdevcmd: str, steps: list[list[str]]) -> str:
    # The check is on its own line: %errorlevel% on the command's own line would be expanded
    # before the command runs. `neq 0` also catches negative codes (crashes, NTSTATUS),
    # which `if errorlevel 1` misses.
    check = "if %errorlevel% neq 0 exit /b %errorlevel%"
    lines = ["@echo off", f'call "{vsdevcmd}" -arch=x64 -host_arch=x64 -no_logo', check]
    for step in steps:
        exe = step[0].replace("/", "\\") if step[0].startswith("out/") else step[0]
        lines.append(subprocess.list2cmdline([exe, *step[1:]]))
        lines.append(check)
    return "\r\n".join(lines) + "\r\n"


def forwarded_args(args: argparse.Namespace, preset: str) -> list[str]:
    out = ["--preset", preset]
    if args.target:
        out += ["--target", args.target]
    if args.test:
        out.append("--test")
    if args.gtest_filter:
        out += ["--gtest-filter", args.gtest_filter]
    if args.fresh:
        out.append("--fresh")
    if args.dry_run:
        out.append("--dry-run")
    return out


def find_vsdevcmd(env: dict[str, str]) -> str | None:
    explicit = env.get("VSDEVCMD")
    if explicit and Path(explicit).is_file():
        return explicit
    program_files = env.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
    vswhere = Path(program_files) / "Microsoft Visual Studio" / "Installer" / "vswhere.exe"
    if not vswhere.is_file():
        return None
    result = subprocess.run(
        [str(vswhere), "-latest", "-products", "*",
         "-requires", "Microsoft.VisualStudio.Component.VC.Tools.x86.x64",
         "-find", r"Common7\Tools\VsDevCmd.bat"],
        capture_output=True, text=True,
    )
    found = result.stdout.strip().splitlines()
    return found[0] if found else None


def wsl_command(argv: list[str], root: Path, distro: str | None) -> list[str]:
    cmd = ["wsl.exe"]
    if distro:
        cmd += ["-d", distro]
    script = PurePosixPath(".agent/scripts/build.py")
    return cmd + ["--cd", str(PureWindowsPath(root)), "--exec", "python3", str(script)] + argv


def run(steps: list[list[str]], root: Path) -> int:
    for step in steps:
        print("+ " + " ".join(step), flush=True)
        code = subprocess.run(step, cwd=root).returncode
        if code != 0:
            return code
    return 0


def main(argv: list[str] | None = None) -> int:
    raw = sys.argv[1:] if argv is None else argv
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--preset", default="auto")
    parser.add_argument("--target")
    parser.add_argument("--test", action="store_true", help="run ctest --preset after building")
    parser.add_argument("--gtest-filter", help=f"run {TEST_EXE} with this --gtest_filter after building")
    parser.add_argument("--fresh", action="store_true", help="reconfigure from scratch")
    parser.add_argument("--dry-run", action="store_true", help="print the steps without running them")
    args = parser.parse_args(raw)

    host = host_system()
    try:
        preset = pick_preset(args.preset, host, configure_presets(REPO_ROOT))
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    target_platform = preset_platform(preset)

    if host == "Windows" and target_platform == "Linux":
        cmd = wsl_command(forwarded_args(args, preset), REPO_ROOT, os.environ.get("ATUGCC_WSL_DISTRO"))
        print("+ " + " ".join(cmd), flush=True)
        return subprocess.run(cmd).returncode
    if host == "Linux" and target_platform == "Windows":
        print(f"error: {preset} needs a Windows host", file=sys.stderr)
        return 2

    build_dir = REPO_ROOT / "out" / "build" / preset
    preset_files = (REPO_ROOT / "CMakePresets.json", REPO_ROOT / "CMakeUserPresets.json")
    mode = configure_mode(build_dir, REPO_ROOT.as_posix(), args.fresh, preset_files)
    exe_suffix = ".exe" if target_platform == "Windows" else ""
    steps = build_steps(preset, mode, args.target, args.test, args.gtest_filter, exe_suffix)
    if mode == "stale":
        print(f"build directory was made at another location (copied checkout); removing {build_dir}", flush=True)
        if not args.dry_run:
            try:
                shutil.rmtree(build_dir)
            except OSError as exc:
                print(f"error: could not remove {build_dir}: {exc}", file=sys.stderr)
                print("close programs that hold files in it (IDE, clangd, a running test) and retry",
                      file=sys.stderr)
                return 2

    if target_platform == "Linux":
        if args.dry_run:
            print("\n".join("+ " + " ".join(s) for s in steps))
            return 0
        return run(steps, REPO_ROOT)

    vsdevcmd = find_vsdevcmd(dict(os.environ))
    if vsdevcmd is None:
        print("error: VsDevCmd.bat not found; set VSDEVCMD or install the MSVC build tools", file=sys.stderr)
        return 2
    script = batch_script(vsdevcmd, steps)
    if args.dry_run:
        print(script)
        return 0
    fd, bat = tempfile.mkstemp(prefix="atugcc_build_", suffix=".bat")
    with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
        f.write(script)
    try:
        print("\n".join("+ " + " ".join(s) for s in steps), flush=True)
        return subprocess.run(["cmd.exe", "/d", "/c", bat], cwd=REPO_ROOT).returncode
    finally:
        os.remove(bat)


if __name__ == "__main__":
    sys.exit(main())
