#!/usr/bin/env python3
"""Function naming check (impl.md: functions are camelCase).

Usage:
    py -3 .agent/scripts/naming_check.py            report snake_case function names (exit 1 if any)
    py -3 .agent/scripts/naming_check.py --map      print the snake_case -> camelCase map
    py -3 .agent/scripts/naming_check.py --apply    rename them in code and comments (task 090-02)

A candidate is a snake_case identifier followed by `(` in code (not in a string or char
literal, not in a comment). Names fixed by the standard library, POSIX, Boost or
GoogleTest are allowed (ALLOWED). `--apply` rewrites identifiers in code and comments and
never touches string or char literals, so program output stays the same. It refuses to
run when a new name already exists as an identifier.
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCOPE = ("include", "src", "tests", "sample", "modules", "main.cpp")
SUFFIXES = {".hpp", ".h", ".cpp", ".cppm", ".ixx"}
SNAKE_RE = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)+$")

# Names fixed by an external convention (std, POSIX, Boost, GoogleTest, keywords).
ALLOWED = frozenset("""
and_then any_cast any_of all_of none_of arrive_and_wait as_const back_inserter binary_search
bit_cast c_str const_cast consume_all create_directories current_zone dynamic_cast emplace_back
enable_shared_from_this ends_with erase_if file_name find_if for_each format_to function_name
get_if has_value holds_alternative is_constant_evaluated is_open is_same_v localtime_r
localtime_s gmtime_r lock_guard make_format_args make_pair make_shared make_tuple make_unique
move_only_function notify_all notify_one or_else pop_back push_back put_time regex_match
reinterpret_cast runtime_error scoped_lock shared_lock sleep_for source_location starts_with
static_assert static_cast string_view system_clock steady_clock temp_directory_path
time_point time_since_epoch to_string to_time_t to_underlying transform_error unique_lock
value_or weak_ptr this_thread get_local_time count_if remove_if copy_if max_element min_element
lower_bound upper_bound equal_range adjacent_find fetch_add find_first_not_of sleep_until
call_once count_down current_path directory_iterator file_size from_chars hardware_concurrency
is_directory parent_path remove_all remove_prefix try_wait
""".split())

# Not functions: snake_case variables direct-initialized with `(` (variables keep snake_case).
NOT_FUNCTIONS = frozenset({"out_file"})  # std::ofstream in core/memory_dump.hpp

TOKEN_RE = re.compile(
    r'(?P<rawstr>R"(?P<delim>[^()\\ ]{0,16})\((?:.|\n)*?\)(?P=delim)")'
    r'|(?P<str>"(?:\\.|[^"\\\n])*")'
    r"|(?P<chr>'(?:\\.|[^'\\\n])+')"
    r"|(?P<line>//[^\n]*)"
    r"|(?P<block>/\*(?:.|\n)*?\*/)"
    r"|(?P<ident>[A-Za-z_][A-Za-z0-9_]*)"
)


def camel(name: str) -> str:
    head, *rest = name.split("_")
    return head + "".join(part[:1].upper() + part[1:] for part in rest)


def source_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for entry in SCOPE:
        path = root / entry
        if path.is_file():
            files.append(path)
        elif path.is_dir():
            files += sorted(p for p in path.rglob("*") if p.suffix in SUFFIXES and p.is_file())
    return files


def candidates(root: Path) -> dict[str, list[tuple[Path, int]]]:
    found: dict[str, list[tuple[Path, int]]] = defaultdict(list)
    for path in source_files(root):
        text = path.read_text(encoding="utf-8-sig")
        for m in TOKEN_RE.finditer(text):
            name = m.group("ident")
            if not name or not SNAKE_RE.match(name) or name in ALLOWED or name in NOT_FUNCTIONS:
                continue
            if re.match(r"\s*\(", text[m.end():m.end() + 64]):
                found[name].append((path, text.count("\n", 0, m.start()) + 1))
    return dict(found)


def rename_text(text: str, mapping: dict[str, str]) -> str:
    out: list[str] = []
    pos = 0
    for m in TOKEN_RE.finditer(text):
        out.append(text[pos:m.start()])
        piece = m.group(0)
        if m.group("ident") and piece in mapping:
            piece = mapping[piece]
        elif m.group("line") or m.group("block"):
            piece = re.sub(r"\b[a-z][a-z0-9_]*\b", lambda w: mapping.get(w.group(0), w.group(0)), piece)
        out.append(piece)
        pos = m.end()
    out.append(text[pos:])
    return "".join(out)


def existing_identifiers(root: Path) -> set[str]:
    names: set[str] = set()
    for path in source_files(root):
        names |= {m.group("ident") for m in TOKEN_RE.finditer(path.read_text(encoding="utf-8-sig")) if m.group("ident")}
    return names


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help=argparse.SUPPRESS)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--map", action="store_true")
    mode.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    root = args.root.resolve()

    found = candidates(root)
    mapping = {name: camel(name) for name in sorted(found)}
    if args.map:
        for old, new in mapping.items():
            print(f"{old} -> {new}  ({len(found[old])} call/decl sites)")
        return 0
    if args.apply:
        clashes = sorted(new for new in mapping.values() if new in existing_identifiers(root))
        if clashes:
            print("error: new names already exist: " + ", ".join(clashes), file=sys.stderr)
            return 2
        changed = 0
        for path in source_files(root):
            raw = path.read_bytes()
            bom = raw.startswith(b"\xef\xbb\xbf")
            text = raw.decode("utf-8-sig")
            new_text = rename_text(text, mapping)
            if new_text != text:
                newline = "\r\n" if "\r\n" in text else "\n"
                data = new_text.replace("\r\n", "\n").replace("\n", newline).encode("utf-8")
                path.write_bytes((b"\xef\xbb\xbf" if bom else b"") + data)
                changed += 1
        print(f"renamed {len(mapping)} names in {changed} files")
        return 0

    for name in sorted(found):
        sites = ", ".join(f"{p.relative_to(root).as_posix()}:{line}" for p, line in found[name][:3])
        print(f"{name} -> {camel(name)}: {sites}{' ...' if len(found[name]) > 3 else ''}")
    print(f"naming_check: {len(found)} snake_case function name(s)")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
