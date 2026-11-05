#!/usr/bin/env python3
"""Configure, build and test through CMakePresets.json, the same way on every host.

Usage:
    py -3 .agent/scripts/build.py [--preset auto|<name>] [--target <t>] [--test] [--label <L>] [--gtest-filter <f>] [--report [DIR]] [--fresh] [--dry-run]

- `auto` picks `<host>-x64-debug`.
- Windows presets run inside the MSVC developer environment: VsDevCmd.bat from VSDEVCMD,
  or found with vswhere.
- Linux presets on a Windows host run in WSL (distribution: ATUGCC_WSL_DISTRO, else the default).
- Configure runs when the build directory has no cache (plain), after an interrupted
  configure (fresh), when a preset file is newer than the cache (plain: re-applies the
  preset's cacheVariables; a variable *removed* from a preset needs --fresh), with --fresh,
  or when any cache in it was recorded at another location (a copied checkout: the
  directory is removed first).
- --gtest-filter runs `ctest --preset <p> -R ^AllTests$ --verbose` with GTEST_FILTER=<f>, so the
  test command gets the launcher and environment that CMake gives AllTests (setarch -R and
  TSAN_OPTIONS under TSan; spec 090-06, KI-012). A filter with %, " or a line break is refused
  (exit 2): gtest filters do not need them and the Windows batch would change them.
- --label <L> runs `ctest --preset <p> -L <L> --no-tests=error` instead of the full ctest of --test:
  unit, scenario, probe, lesson (spec 040-02). A label that matches nothing fails. The same
  characters as for --gtest-filter are refused.
- --report [DIR] records ctest JUnit XML, per-program gtest JSON, tests.json and a markdown
  summary report.md into DIR (default: out/test-reports/<preset>/<timestamp>/; relative to the
  repository root only; exit 2 for absolute paths). It requires at least one of --test, --label
  or --gtest-filter. The report is written even when tests fail, as long as at least one
  test-running ctest step ran.

Exit code: the first failing step's exit code, 0 when every step passes.
Rules: .agent/rules/config.md, .agent/rules/test.md.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path, PurePosixPath, PureWindowsPath

REPO_ROOT = Path(__file__).resolve().parents[2]
# A step is (argv, extra environment) or (argv, extra environment, stdout file).
Step = tuple[list[str], dict[str, str]] | tuple[list[str], dict[str, str], Path]


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


def bad_filter(gtest_filter: str, option: str = "--gtest-filter") -> str | None:
    """Why a --gtest-filter (or --label) value is refused, or None."""
    for ch, name in (("%", "%"), ('"', '"'), ("\r", "a line break"), ("\n", "a line break")):
        if ch in gtest_filter:
            return f"{option} must not contain {name}"
    return None


def build_steps(preset: str, mode: str | None, target: str | None, test: bool,
                gtest_filter: str | None, label: str | None = None,
                report: Path | None = None) -> list[Step]:
    steps: list[Step] = []
    if mode is not None:
        steps.append((["cmake", "--preset", preset] + (["--fresh"] if mode in ("fresh", "stale") else []), {}))
    steps.append((["cmake", "--build", "--preset", preset] + (["--target", target] if target else []), {}))

    test_steps: list[Step] = []
    if label:
        # replaces the full run of --test; --no-tests=error: a mistyped label must not pass
        test_steps.append((["ctest", "--preset", preset, "-L", label, "--no-tests=error"], {}))
    elif test:
        test_steps.append((["ctest", "--preset", preset], {}))
    if gtest_filter:
        # --verbose: GoogleTest 1.14 passes a filter that matches nothing, so its output must show.
        test_steps.append((["ctest", "--preset", preset, "-R", "^AllTests$", "--verbose"],
                           {"GTEST_FILTER": gtest_filter}))
    if report is not None and test_steps:
        # spec 040-02: absolute paths (ctest reads a relative --output-junit from the build directory);
        # the trailing slash makes gtest write one file per program into the directory
        steps.append((["ctest", "--preset", preset, "--show-only=json-v1"], {}, report / "tests.json"))
        test_steps = [(argv + ["--output-junit", (report / f"ctest-{n}.junit.xml").as_posix()],
                       {**env, "GTEST_OUTPUT": f"json:{(report / 'gtest').as_posix()}/"})
                      for n, (argv, env) in enumerate(test_steps, start=1)]
    steps += test_steps
    return steps


def show(step: Step) -> str:
    argv, env = step[0], step[1]
    cmd = " ".join([f"{k}={v}" for k, v in env.items()] + argv)
    if len(step) > 2:
        return f"{cmd} > {step[2].as_posix()}"
    return cmd


def batch_script(vsdevcmd: str, steps: list[Step], step_codes_file: Path | None = None) -> str:
    # The check is on its own line: %errorlevel% on the command's own line would be expanded
    # before the command runs. `neq 0` also catches negative codes (crashes, NTSTATUS),
    # which `if errorlevel 1` misses.
    check = "if %errorlevel% neq 0 exit /b %errorlevel%"
    lines = ["@echo off", f'call "{vsdevcmd}" -arch=x64 -host_arch=x64 -no_logo', check]
    for i, step in enumerate(steps):
        argv, env = step[0], step[1]
        lines += [f'set "{k}={v}"' for k, v in env.items()]  # bad_filter keeps % and " out
        line = " ".join(batch_arg(a) for a in argv)
        if len(step) > 2:
            line += f' > "{step[2].as_posix()}"'
        lines.append(line)
        if step_codes_file is not None:
            # redirection first: `echo 1 0>>file` would redirect handle 0; echo leaves %errorlevel% as is
            lines.append(f'>>"{step_codes_file.as_posix()}" echo {i} %errorlevel%')
        lines.append(check)
    return "\r\n".join(lines) + "\r\n"


def batch_arg(arg: str) -> str:
    """One argument for a batch line. cmd removes an unquoted ^ (`-R ^AllTests$` arrived as
    `AllTests$`) and splits at & | < > ( ); inside double quotes they are literal."""
    if '"' not in arg and re.search(r"[\s^&|<>()]", arg):
        return f'"{arg}"'
    return subprocess.list2cmdline([arg])


def forwarded_args(args: argparse.Namespace, preset: str) -> list[str]:
    out = ["--preset", preset]
    if getattr(args, "target", None):
        out += ["--target", args.target]
    if getattr(args, "test", False):
        out.append("--test")
    if getattr(args, "label", None):
        out += ["--label", args.label]
    if getattr(args, "gtest_filter", None):
        out += ["--gtest-filter", args.gtest_filter]
    if getattr(args, "fresh", False):
        out.append("--fresh")
    if getattr(args, "dry_run", False):
        out.append("--dry-run")
    if getattr(args, "report", None) is not None:
        out += ["--report", args.report] if args.report else ["--report"]
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


def run(steps: list[Step], root: Path, codes: list[int] | None = None) -> int:
    for step in steps:
        argv, env = step[0], step[1]
        print("+ " + show(step), flush=True)
        out_f = None
        if len(step) > 2:
            out_f = open(step[2], "w", encoding="utf-8")
        try:
            code = subprocess.run(argv, cwd=root, env={**os.environ, **env} if env else None,
                                  stdout=out_f).returncode
        finally:
            if out_f is not None:
                out_f.close()
        if codes is not None:
            codes.append(code)
        if code != 0:
            return code
    return 0


def report_dir_problem(rel_dir: str, root: Path) -> str | None:
    """Why --report DIR is refused, or None. DIR is emptied before the run, so it must lie inside
    the repository (not the repository itself) and, if it exists, be an earlier report or empty."""
    root = root.resolve()
    target = (root / rel_dir).resolve()
    # case-insensitive: drvfs (/mnt/c in WSL) and NTFS accept .GIT for .git
    if target == root or root not in target.parents or ".git" in (p.lower() for p in target.relative_to(root).parts):
        return f"--report {rel_dir} must be a folder inside the repository (not in .git)"
    unresolved = root / rel_dir
    if unresolved.is_symlink() or (hasattr(os.path, "isjunction") and os.path.isjunction(unresolved)):
        return f"--report {rel_dir} is a link"
    if target.exists():
        if not target.is_dir():
            return f"--report {rel_dir} is a file"
        if any(target.iterdir()) and not (target / "run.json").is_file():
            return f"--report {rel_dir} exists and is not an earlier test report (no run.json)"
    return None


def read_step_codes(step_codes_file: Path, run_data: dict) -> None:
    """Fill run_data's step codes from the `<index> <code>` lines the Windows batch appended."""
    if not step_codes_file.is_file():
        return
    for line in step_codes_file.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[0].isdigit() and parts[1].lstrip("-").isdigit():
            if (idx := int(parts[0])) < len(run_data["steps"]):
                run_data["steps"][idx]["code"] = int(parts[1])


def finish_report(report_dir: Path, rel_dir: str, run_data: dict, root: Path) -> None:
    """Write run.json and report.md. Never raises: the exit code stays the steps' (spec 040-02 §4)."""
    try:
        (report_dir / "run.json").write_text(json.dumps(run_data, indent=2) + "\n", encoding="utf-8")
        if not any(s["code"] is not None for s in run_data["steps"] if "--output-junit" in s["argv"]):
            print("no test report: no test step ran (an earlier step failed)")
            return
        sys.path.insert(0, str(Path(__file__).resolve().parent))  # also under python -I
        from test_report import write_report
        write_report(report_dir, root)
        print(f"report: {rel_dir}/report.md")
    except Exception as exc:  # a broken report must not change the exit code
        print(f"error: test report: {exc}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    raw = sys.argv[1:] if argv is None else argv
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--preset", default="auto")
    parser.add_argument("--target")
    parser.add_argument("--test", action="store_true", help="run ctest --preset after building")
    parser.add_argument("--label", help="after building, run only the CTest tests with this label "
                                        "(unit, scenario, probe, lesson); replaces the full run of --test")
    parser.add_argument("--gtest-filter", help="after building, run AllTests through ctest with GTEST_FILTER set "
                                               "to this filter (%%, \" and line breaks are refused)")
    parser.add_argument("--report", nargs="?", const="", metavar="DIR",
                        help="record ctest JUnit XML, gtest JSON, tests.json and report.md in DIR "
                             "(default: out/test-reports/<preset>/<timestamp>/; relative to repository root)")
    parser.add_argument("--fresh", action="store_true", help="reconfigure from scratch")
    parser.add_argument("--dry-run", action="store_true", help="print the steps without running them")
    args = parser.parse_args(raw)
    if args.gtest_filter is not None and (reason := bad_filter(args.gtest_filter)):
        print(f"error: {reason}", file=sys.stderr)
        return 2
    if args.label is not None and (reason := bad_filter(args.label, "--label")):
        print(f"error: {reason}", file=sys.stderr)
        return 2
    if args.report is not None:
        if not (args.test or args.label or args.gtest_filter):
            print("error: --report needs --test, --label or --gtest-filter", file=sys.stderr)
            return 2
        if args.report and (
            PurePosixPath(args.report).is_absolute()
            or PureWindowsPath(args.report).is_absolute()
            or args.report.startswith(("/", "\\"))
        ):
            print("error: --report takes a path relative to the repository root", file=sys.stderr)
            return 2
        if reason := bad_filter(args.report, "--report"):  # the path goes into batch lines
            print(f"error: {reason}", file=sys.stderr)
            return 2

    host = host_system()
    try:
        preset = pick_preset(args.preset, host, configure_presets(REPO_ROOT))
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    target_platform = preset_platform(preset)

    if args.report is not None:
        if not args.report:
            args.report = f"out/test-reports/{preset}/{datetime.now():%Y%m%d-%H%M%S}"
        else:
            args.report = PureWindowsPath(args.report).as_posix()
        if not args.dry_run and (reason := report_dir_problem(args.report, REPO_ROOT)):
            print(f"error: {reason}", file=sys.stderr)
            return 2

    if host == "Windows" and target_platform == "Linux":
        cmd = wsl_command(forwarded_args(args, preset), REPO_ROOT, os.environ.get("ATUGCC_WSL_DISTRO"))
        print("+ " + " ".join(cmd), flush=True)
        return subprocess.run(cmd).returncode
    if host == "Linux" and target_platform == "Windows":
        print(f"error: {preset} needs a Windows host", file=sys.stderr)
        return 2

    report_dir = (REPO_ROOT / args.report) if args.report is not None else None
    if report_dir is not None and not args.dry_run:
        if report_dir.exists():
            shutil.rmtree(report_dir)  # report_dir_problem: an earlier report or an empty folder
        (report_dir / "gtest").mkdir(parents=True, exist_ok=True)

    build_dir = REPO_ROOT / "out" / "build" / preset
    preset_files = (REPO_ROOT / "CMakePresets.json", REPO_ROOT / "CMakeUserPresets.json")
    mode = configure_mode(build_dir, REPO_ROOT.as_posix(), args.fresh, preset_files)
    steps = build_steps(preset, mode, args.target, args.test, args.gtest_filter, args.label, report_dir)
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

    run_data: dict | None = None
    if report_dir is not None and not args.dry_run:
        cmd_args = subprocess.list2cmdline(raw) if host == "Windows" else shlex.join(raw)
        run_data = {
            "preset": preset,
            "command": "py -3 .agent/scripts/build.py " + cmd_args,
            "build_dir": f"out/build/{preset}",
            "started": datetime.now().isoformat(timespec="seconds"),
            "steps": [{"argv": s[0], "code": None} for s in steps],
        }
        (report_dir / "run.json").write_text(json.dumps(run_data, indent=2) + "\n", encoding="utf-8")

    if target_platform == "Linux":
        if args.dry_run:
            print("\n".join("+ " + show(s) for s in steps))
            if args.report is not None:
                print(f"report: {args.report} (dry run: not written)")
            return 0
        codes: list[int] = [] if report_dir is not None else None
        ret = run(steps, REPO_ROOT, codes)
        if run_data is not None:
            for i, c in enumerate(codes):
                run_data["steps"][i]["code"] = c
            finish_report(report_dir, args.report, run_data, REPO_ROOT)
        return ret

    vsdevcmd = find_vsdevcmd(dict(os.environ))
    if vsdevcmd is None:
        print("error: VsDevCmd.bat not found; set VSDEVCMD or install the MSVC build tools", file=sys.stderr)
        return 2
    step_codes_file = (report_dir / "step_codes.txt") if report_dir is not None else None
    script = batch_script(vsdevcmd, steps, step_codes_file)
    if args.dry_run:
        print(script)
        if args.report is not None:
            print(f"report: {args.report} (dry run: not written)")
        return 0
    fd, bat = tempfile.mkstemp(prefix="atugcc_build_", suffix=".bat")
    with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
        f.write(script)
    try:
        print("\n".join("+ " + show(s) for s in steps), flush=True)
        ret = subprocess.run(["cmd.exe", "/d", "/c", bat], cwd=REPO_ROOT).returncode
    finally:
        os.remove(bat)
    if run_data is not None:
        try:
            read_step_codes(step_codes_file, run_data)
        except OSError as exc:
            print(f"error: test report: {exc}", file=sys.stderr)
        finish_report(report_dir, args.report, run_data, REPO_ROOT)
    return ret


if __name__ == "__main__":
    sys.exit(main())
