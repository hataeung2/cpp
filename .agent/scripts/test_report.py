#!/usr/bin/env python3
"""Summarize test results from a report directory written by build.py --report.

Usage:
    py -3 .agent/scripts/test_report.py <DIR>

Input files in <DIR>:
    - run.json: preset, command, build_dir, started timestamp, steps with exit codes
    - tests.json: output of ctest --show-only=json-v1 (optional)
    - ctest-<n>.junit.xml: ctest JUnit XML reports (zero or more)
    - gtest/*.json: GoogleTest JSON outputs (zero or more)

Writes:
    <DIR>/report.md: human-readable Markdown test report with sections:
      # Test report: <preset>
      ## Steps
      ## Results by label
      ## Failures
      ## Slowest tests
      ## GoogleTest cases
      ## Inputs

Exit code:
    0 on success
    2 if <DIR> does not exist or holds no ctest-*.junit.xml, or CLI arguments are invalid
      (run.json is optional: without it the header and the Steps table say unknown)
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]

POSIX_DIRS = (
    "usr|tmp|home|mnt|opt|var|etc|root|proc|dev|lib|lib64|run|srv|build|builds|workspace|data|"
    "snap|nix|private|Users|Library|Applications|System|Volumes"
)
_SEGMENT = r"[^\s\\/\"'()\[\]<>|*?]+"
EXTERNAL_PATH_RE = re.compile(
    r"(?<![\w/\\.:])"  # not inside a word, a URL (http://) or another path
    r"(?:[A-Za-z]:[\\/](?:" + _SEGMENT + r"(?: " + _SEGMENT + r")*[\\/])*"  # Windows: spaces inside folders
    r"|/(?:" + POSIX_DIRS + r")(?=/|$)(?:/" + _SEGMENT + r")*/?)"
    r"[^\s\"'()\[\]<>]*"
)


def mask_external_paths(text: str) -> str:
    """Replace absolute paths outside the repository with '<abs>/<last_component>'."""

    def _repl(m: re.Match[str]) -> str:
        s = m.group(0)
        match_line = re.match(r"^(.*?)(:\d+(?::\d+)?)$", s)
        if match_line:
            base, suffix = match_line.group(1), match_line.group(2)
        else:
            base, suffix = s, ""
        last = base.replace("\\", "/").rstrip("/").split("/")[-1]
        return f"<abs>/{last}{suffix}"

    return EXTERNAL_PATH_RE.sub(_repl, text)


class PathCleaner:
    """Strips the repository root prefix from strings, normalizing that path to forward slashes."""

    def __init__(self, repo_root: Path) -> None:
        if repo_root.drive:
            drive = repo_root.drive[0]
            rest_posix = repo_root.as_posix()[2:].strip("/")
            parts = [re.escape(p) for p in rest_posix.split("/") if p]
            parts_pat = "[\\\\/]+".join(parts)
            win_pat = rf"[{drive.lower()}{drive.upper()}]:[\\\\/]+{parts_pat}"
            wsl_pat = rf"/mnt/[{drive.lower()}{drive.upper()}][\\\\/]+{parts_pat}"
            self.root_pat = re.compile(
                rf"(?:{win_pat}|{wsl_pat})(?:[\\\\/]+([^\s\"'\(\)\[\]<>]*))?"
            )
        else:
            parts = [
                re.escape(p)
                for p in repo_root.as_posix().strip("/").split("/")
                if p
            ]
            parts_pat = "/+".join(parts)
            self.root_pat = re.compile(
                rf"/{parts_pat}(?:[\\\\/]+([^\s\"'\(\)\[\]<>]*))?"
            )

    def clean(self, text: str) -> str:
        if not text:
            return ""

        def _repl(m: re.Match[str]) -> str:
            tail = m.group(1)
            if tail is None:
                return ""
            return tail.replace("\\", "/")

        stripped = self.root_pat.sub(_repl, text)
        return mask_external_paths(stripped)


def table_cell(text: str) -> str:
    """Text safe inside a Markdown table cell: a | (label regexes such as unit|scenario) would end
    the cell, also inside backticks."""
    return text.replace("|", "\\|")


def to_display_path(path: Path, repo_root: Path, report_dir: Path) -> str:
    """Format path relative to repo root if inside repo, else relative to report dir."""
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        try:
            return path.resolve().relative_to(report_dir.resolve()).as_posix()
        except ValueError:
            return path.name


def query_git_commit(repo_root: Path) -> str:
    """Return '<short hash>[ (uncommitted changes)]' or 'unknown'."""
    try:
        res_head = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if res_head.returncode != 0:
            return "unknown"
        short_hash = res_head.stdout.strip()
        if not short_hash:
            return "unknown"

        res_status = subprocess.run(
            ["git", "-C", str(repo_root), "status", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if res_status.returncode != 0:
            return "unknown"
        has_changes = bool(res_status.stdout.strip())
        return f"{short_hash} (uncommitted changes)" if has_changes else short_hash
    except Exception:
        return "unknown"


def parse_cmake_version(version_str: str) -> tuple[int, ...]:
    """Parse a version string like '4.10.0' or '4.9.2' into a tuple of ints for numeric sorting."""
    parts = re.findall(r"\d+", version_str)
    return tuple(int(p) for p in parts) if parts else (0,)


def query_compiler(repo_root: Path, build_dir: str | None) -> str:
    """Read CMAKE_CXX_COMPILER_ID and CMAKE_CXX_COMPILER_VERSION from the compiler file that
    CMake writes at configure time (CMakeFiles/<cmake version>/CMakeCXXCompiler.cmake); they are
    not cache entries."""
    if not build_dir:
        return "unknown"
    found = list(
        (repo_root / build_dir / "CMakeFiles").glob("*/CMakeCXXCompiler.cmake")
    )
    if not found:
        return "unknown"
    best_file = max(found, key=lambda p: parse_cmake_version(p.parent.name))
    try:
        text = best_file.read_text(encoding="utf-8", errors="replace")
        m_id = re.search(
            r'^set\(CMAKE_CXX_COMPILER_ID "([^"]*)"\)', text, re.MULTILINE
        )
        m_ver = re.search(
            r'^set\(CMAKE_CXX_COMPILER_VERSION "([^"]*)"\)', text, re.MULTILINE
        )
        if m_id:
            cid = m_id.group(1).strip()
            cver = m_ver.group(1).strip() if m_ver else ""
            res = f"{cid} {cver}".strip()
            return res if res else "unknown"
        return "unknown"
    except Exception:
        return "unknown"


def parse_tests_json(
    tests_json_path: Path,
) -> tuple[dict[str, list[str]], dict[str, list[str]], bool]:
    """Parse tests.json: returns (name -> labels, name -> command, is_valid)."""
    try:
        data = json.loads(tests_json_path.read_text(encoding="utf-8"))
        labels_map: dict[str, list[str]] = {}
        command_map: dict[str, list[str]] = {}
        for t in data.get("tests", []):
            name = t.get("name")
            if not name:
                continue
            lbls: list[str] = []
            for prop in t.get("properties", []):
                if prop.get("name") == "LABELS":
                    lbls = [str(v) for v in prop.get("value", [])]
                    break
            labels_map[name] = lbls
            writes_no_gtest_json = any(
                prop.get("name") == "ENVIRONMENT_MODIFICATION"
                and "GTEST_OUTPUT=unset:" in prop.get("value", [])
                for prop in t.get("properties", [])
            )
            if isinstance(t.get("command"), list) and not writes_no_gtest_json:
                command_map[name] = [str(c) for c in t["command"]]
        return labels_map, command_map, True
    except Exception:
        return {}, {}, False


def gtest_cases(gdata: dict[str, Any]) -> list[tuple[str, list[str]]]:
    """Every case of a GoogleTest JSON object as ('<Suite>.<Name>', failure messages).
    Raises TypeError / AttributeError for a file of the wrong shape (the caller skips it)."""
    cases: list[tuple[str, list[str]]] = []
    for suite in gdata.get("testsuites", []):
        for case in suite.get("testsuite", []):
            msgs = [str(f["failure"]) for f in case.get("failures", []) if f.get("failure")]
            cases.append((f"{suite.get('name', '')}.{case.get('name', '')}", msgs))
    return cases


def gtest_totals(gdata: dict[str, Any]) -> tuple[int, int, int]:
    """(cases, failed, disabled) of a GoogleTest JSON object; ValueError / TypeError if malformed."""
    return tuple(int(gdata.get(key, 0) or 0) for key in ("tests", "failures", "disabled"))  # type: ignore[return-value]


def gtest_file_order(path: Path) -> tuple[str, int]:
    """atugcc_tests.json, atugcc_tests_1.json, ..., _10: the order gtest created them in."""
    m = re.fullmatch(r"(.*?)(?:_(\d+))?", path.stem)
    return (m.group(1).lower(), int(m.group(2) or 0)) if m else (path.stem.lower(), 0)


def assign_gtest_files(
    testcases: list[dict[str, Any]],
    gtest_data: list[tuple[Path, dict[str, Any]]],
    commands: dict[str, list[str]],
    has_tests_json: bool,
) -> dict[int, list[tuple[dict[str, Any], str | None]]]:
    """Which gtest file belongs to which CTest test (by index in testcases). A scenario.<S>.<N> test
    gets the file holding case <S>.<N> (only that case); every other test that runs a GoogleTest
    program gets the next unused file of that program, in run order. Never by the files' top-level
    "name" (always "AllTests")."""
    out: dict[int, list[tuple[dict[str, Any], str | None]]] = {i: [] for i in range(len(testcases))}
    used: set[int] = set()
    for i, tc in enumerate(testcases):
        if tc["name"].startswith("scenario."):
            case = tc["name"].removeprefix("scenario.")
            for j, (_, gdata) in enumerate(gtest_data):
                if j not in used and any(name == case for name, _ in gtest_cases(gdata)):
                    out[i].append((gdata, case))
                    used.add(j)
                    break
    for i, tc in enumerate(testcases):
        if tc["name"].startswith("scenario."):
            continue
        if has_tests_json:
            # any argument, so a launcher prefix (setarch x86_64 -R <program>) does not matter
            stems = {Path(arg).stem.lower() for arg in commands.get(tc["name"], [])}
        else:
            stems = {"atugcc_tests"} if tc["name"] == "AllTests" else set()
        for j, (gpath, gdata) in enumerate(gtest_data):
            if j not in used and gtest_file_order(gpath)[0] in stems:
                out[i].append((gdata, None))
                used.add(j)
                break
    return out


def write_report(report_dir: Path, repo_root: Path) -> Path:
    """Read inputs in report_dir, write report.md, and return its path.

    Never raises for broken or missing input files. Raises only if report_dir
    cannot be written to.
    """
    inputs_read: list[str] = []
    broken_inputs: list[str] = []

    # 1. run.json
    run_file = report_dir / "run.json"
    run_data: dict[str, Any] = {}
    if run_file.is_file():
        try:
            loaded = json.loads(run_file.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                run_data = loaded
                inputs_read.append(to_display_path(run_file, repo_root, report_dir))
            else:
                broken_inputs.append(to_display_path(run_file, repo_root, report_dir))
        except Exception:
            broken_inputs.append(to_display_path(run_file, repo_root, report_dir))
    else:
        broken_inputs.append(to_display_path(run_file, repo_root, report_dir))

    preset = str(run_data.get("preset") or "unknown")
    command = str(run_data.get("command") or "unknown")
    build_dir = run_data.get("build_dir")
    started = str(run_data.get("started") or "unknown")
    steps: list[dict[str, Any]] = [
        step for step in (run_data.get("steps") if isinstance(run_data.get("steps"), list) else [])
        if isinstance(step, dict)
    ]

    cleaner = PathCleaner(repo_root)

    # 2. tests.json (optional)
    tests_file = report_dir / "tests.json"
    tests_labels: dict[str, list[str]] = {}
    tests_commands: dict[str, list[str]] = {}
    has_tests_json = False
    if tests_file.is_file():
        tests_labels, tests_commands, valid = parse_tests_json(tests_file)
        if valid:
            has_tests_json = True
            inputs_read.append(to_display_path(tests_file, repo_root, report_dir))
        else:
            broken_inputs.append(to_display_path(tests_file, repo_root, report_dir))

    # 3. ctest-<n>.junit.xml
    junit_files = sorted(report_dir.glob("ctest-*.junit.xml"), key=lambda p: p.name)
    raw_testcases: list[dict[str, Any]] = []

    for jf in junit_files:
        try:
            tree = ET.parse(jf)
            file_testcases: list[dict[str, Any]] = []
            for tc in tree.iter("testcase"):
                name = tc.get("name", "")
                raw_time = tc.get("time", "0")
                time_val = float(raw_time) if raw_time is not None else 0.0
                status_attr = tc.get("status", "").lower()
                has_failure = tc.find("failure") is not None
                has_skipped = tc.find("skipped") is not None

                if status_attr == "fail" or has_failure:
                    status = "Failed"
                elif status_attr in ("notrun", "disabled") or has_skipped:
                    status = "Not run"
                else:
                    status = "Passed"

                sys_out_elem = tc.find("system-out")
                system_out = (
                    sys_out_elem.text
                    if (sys_out_elem is not None and sys_out_elem.text)
                    else ""
                )

                # Determine labels
                labels: list[str] = []
                if has_tests_json and name in tests_labels:
                    labels = list(tests_labels[name])
                else:
                    cmake_labels_elem = tc.find(
                        "./properties/property[@name='cmake_labels']"
                    )
                    if (
                        cmake_labels_elem is not None
                        and cmake_labels_elem.get("value")
                    ):
                        raw_lbls = cmake_labels_elem.get("value", "")
                        labels = [
                            lbl.strip()
                            for lbl in raw_lbls.split(";")
                            if lbl.strip()
                        ]
                if not labels:
                    labels = ["(no label)"]

                file_testcases.append(
                    {
                        "name": name,
                        "time": time_val,
                        "status": status,
                        "system_out": system_out,
                        "labels": labels,
                    }
                )
            inputs_read.append(to_display_path(jf, repo_root, report_dir))
            raw_testcases.extend(file_testcases)
        except Exception:
            broken_inputs.append(to_display_path(jf, repo_root, report_dir))

    # 4. gtest/*.json
    gtest_dir = report_dir / "gtest"
    gtest_files = (
        sorted(gtest_dir.glob("*.json"), key=gtest_file_order)
        if gtest_dir.is_dir()
        else []
    )
    gtest_data_list: list[tuple[Path, dict[str, Any]]] = []

    for gf in gtest_files:
        try:
            gdata = json.loads(gf.read_text(encoding="utf-8"))
            if not isinstance(gdata, dict):
                broken_inputs.append(to_display_path(gf, repo_root, report_dir))
                continue
            gtest_cases(gdata)  # shape check: a malformed file is skipped as a whole
            gtest_totals(gdata)
            inputs_read.append(to_display_path(gf, repo_root, report_dir))
            gtest_data_list.append((gf, gdata))
        except Exception:
            broken_inputs.append(to_display_path(gf, repo_root, report_dir))

    # Git & Compiler info
    commit_str = query_git_commit(repo_root)
    compiler_str = query_compiler(repo_root, build_dir)

    lines: list[str] = []

    # Section 1: Header
    lines.append(f"# Test report: {preset}")
    lines.append("")
    lines.append("| | |")
    lines.append("|---|---|")
    lines.append(f"| Date | {started} |")
    lines.append(f"| Commit | {commit_str} |")
    lines.append(f"| Compiler | {compiler_str} |")
    clean_command = table_cell(cleaner.clean(command))
    lines.append(f"| Command | `{clean_command}` |")
    lines.append("")

    # Section 2: Steps
    lines.append("## Steps")
    lines.append("| # | Command | Exit code |")
    lines.append("|---|---|---|")
    for idx, step in enumerate(steps, start=1):
        argv = step.get("argv", [])
        code = step.get("code")
        code_str = "not run" if code is None else str(code)
        cleaned_argv = [cleaner.clean(a) for a in argv]
        cmd_str = table_cell(" ".join(cleaned_argv))
        lines.append(f"| {idx} | `{cmd_str}` | {code_str} |")
    lines.append("")

    # Section 3: Results by label
    lines.append("## Results by label")
    lines.append("| Label | Tests | Passed | Failed | Not run | Time (s) |")
    lines.append("|---|---|---|---|---|---|")

    # Aggregate by label
    label_stats: dict[str, dict[str, float]] = {}
    for tc in raw_testcases:
        st = tc["status"]
        t_val = tc["time"]
        for lbl in tc["labels"]:
            if lbl not in label_stats:
                label_stats[lbl] = {
                    "tests": 0,
                    "passed": 0,
                    "failed": 0,
                    "not_run": 0,
                    "time": 0.0,
                }
            label_stats[lbl]["tests"] += 1
            if st == "Passed":
                label_stats[lbl]["passed"] += 1
            elif st == "Failed":
                label_stats[lbl]["failed"] += 1
            elif st == "Not run":
                label_stats[lbl]["not_run"] += 1
            label_stats[lbl]["time"] += t_val

    # Ordering labels: unit, scenario, probe, lesson if present, then sorted others, then (no label)
    ordered_labels: list[str] = []
    predefined = ["unit", "scenario", "probe", "lesson"]
    for p in predefined:
        if p in label_stats:
            ordered_labels.append(p)
    other_labels = sorted(
        [
            lbl
            for lbl in label_stats
            if lbl not in predefined and lbl != "(no label)"
        ]
    )
    ordered_labels.extend(other_labels)
    if "(no label)" in label_stats:
        ordered_labels.append("(no label)")

    for lbl in ordered_labels:
        st = label_stats[lbl]
        lines.append(
            f"| {table_cell(lbl)} | {int(st['tests'])} | {int(st['passed'])} | "
            f"{int(st['failed'])} | {int(st['not_run'])} | {st['time']:.2f} |"
        )

    # **All** row
    all_tests = len(raw_testcases)
    all_passed = sum(1 for tc in raw_testcases if tc["status"] == "Passed")
    all_failed = sum(1 for tc in raw_testcases if tc["status"] == "Failed")
    all_not_run = sum(1 for tc in raw_testcases if tc["status"] == "Not run")
    all_time = sum(tc["time"] for tc in raw_testcases)
    lines.append(
        f"| **All** | {all_tests} | {all_passed} | {all_failed} | "
        f"{all_not_run} | {all_time:.2f} |"
    )
    lines.append("")

    # Section 4: Failures
    lines.append("## Failures")
    failed_testcases = [tc for tc in raw_testcases if tc["status"] == "Failed"]
    if not failed_testcases:
        lines.append("(none)")
    else:
        gtest_files_of = assign_gtest_files(raw_testcases, gtest_data_list, tests_commands, has_tests_json)
        for index, tc in enumerate(raw_testcases):
            if tc["status"] != "Failed":
                continue
            tname = tc["name"]
            lines.append(f"### {tname}")

            failed_gtest_cases = [
                (name, [cleaner.clean(m).strip() for m in msgs])
                for gdata, only_case in gtest_files_of[index]
                for name, msgs in gtest_cases(gdata)
                if msgs and (only_case is None or name == only_case)
            ]

            if failed_gtest_cases:
                for case_id, msgs in failed_gtest_cases:
                    joined = "\n".join(msgs)
                    lines.append(f"- `{case_id}`:")
                    lines.append("```")
                    lines.append(joined)
                    lines.append("```")
            else:
                raw_out = tc["system_out"].strip()
                out_lines = raw_out.splitlines() if raw_out else []
                tail_lines = out_lines[-30:]
                cleaned_tail = [cleaner.clean(line) for line in tail_lines]
                lines.append("```")
                lines.append("\n".join(cleaned_tail))
                lines.append("```")
    lines.append("")

    # Section 5: Slowest tests
    lines.append("## Slowest tests")
    lines.append("| Test | Time (s) |")
    lines.append("|---|---|")
    sorted_by_time = sorted(raw_testcases, key=lambda x: x["time"], reverse=True)
    for tc in sorted_by_time[:5]:
        lines.append(f"| {table_cell(tc['name'])} | {tc['time']:.2f} |")
    lines.append("")

    # Section 6: GoogleTest cases
    lines.append("## GoogleTest cases")
    lines.append("| Program | Cases | Failed | Disabled |")
    lines.append("|---|---|---|---|")
    total_gtest_cases = 0
    total_gtest_failed = 0
    total_gtest_disabled = 0
    for gpath, gdata in gtest_data_list:
        c_cases, c_failed, c_disabled = gtest_totals(gdata)
        total_gtest_cases += c_cases
        total_gtest_failed += c_failed
        total_gtest_disabled += c_disabled
        lines.append(
            f"| {table_cell(gpath.name)} | {c_cases} | {c_failed} | {c_disabled} |"
        )
    lines.append(
        f"| **All** | {total_gtest_cases} | {total_gtest_failed} | {total_gtest_disabled} |"
    )
    lines.append("")

    # Section 7: Inputs
    lines.append("## Inputs")
    for inp in inputs_read:
        lines.append(f"- {inp}")
    for brk in broken_inputs:
        lines.append(f"- could not read: {brk}")

    content = "\n".join(lines) + "\n"
    out_file = report_dir / "report.md"
    out_file.write_text(content, encoding="utf-8")
    return out_file


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if not args or args[0] in ("-h", "--help"):
        print("Usage: py -3 .agent/scripts/test_report.py <DIR>")
        return 0 if args and args[0] in ("-h", "--help") else 2

    raw_dir = Path(args[0])
    if raw_dir.is_absolute():
        report_dir = raw_dir
    else:
        if (REPO_ROOT / raw_dir).exists():
            report_dir = (REPO_ROOT / raw_dir).resolve()
        else:
            report_dir = (Path.cwd() / raw_dir).resolve()

    # run.json is optional (a run made without build.py, tests/README.md 4.4); results are not
    if not report_dir.is_dir() or not any(report_dir.glob("ctest-*.junit.xml")):
        sys.stderr.write(f"error: {report_dir} does not exist or holds no ctest-*.junit.xml\n")
        return 2

    out_path = write_report(report_dir, REPO_ROOT)
    try:
        rel = out_path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
        print(f"report: {rel}")
    except ValueError:
        print(f"report: {out_path.as_posix()}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
