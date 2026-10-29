"""Repository file access for the web playground (spec 070-02 §2.2).

Paths come in repo-relative with '/'. Reads are allowed anywhere in the repository except
hidden folders; writes only under lessons/ (existing files, or new .cpp/.hpp/.md/.toml files).
`sha` is the SHA-256 of the bytes on disk, so an edit made in another editor is detected as a
conflict (409) instead of being overwritten. The editor always works on LF text; a file keeps
its own line ending (CRLF or LF) when it is saved.
"""
from __future__ import annotations

import hashlib
import os
import re
import stat
import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

WRITABLE_ROOT = "lessons"
NEW_FILE_SUFFIXES = (".cpp", ".hpp", ".md", ".toml")
_DRIVE = re.compile(r"^[A-Za-z]:")


class PathError(Exception):
    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


@dataclass
class Conflict(Exception):
    """The file on disk is not the one the editor started from."""
    content: str | None
    sha: str | None


def sha_of(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _to_lf(text: str) -> str:
    return text.replace("\r\n", "\n")


class RepoFiles:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        # one save at a time: two PUTs with the same baseSha cannot both pass the sha check
        # (an editor outside the server can still write between the check and the replace)
        self.write_lock = threading.Lock()

    def resolve(self, path: str) -> tuple[str, Path]:
        """Normalized repo-relative path and its absolute location, or PathError(400)."""
        if not path or "\x00" in path:
            raise PathError(400, "empty path or NUL byte")
        if "\\" in path:
            raise PathError(400, "use '/' as the separator")
        if path.startswith("/") or _DRIVE.match(path):
            raise PathError(400, "absolute paths are not allowed")
        parts = PurePosixPath(path).parts
        if any(p in ("..", ".") or p.startswith(".") for p in path.split("/") if p):
            raise PathError(400, "'..', '.' and hidden path components are not allowed")
        if not parts:
            raise PathError(400, "empty path")
        target = self.root.joinpath(*parts)
        try:  # where the path really leads, after symlinks
            real = target.resolve().relative_to(self.root)
        except ValueError:
            raise PathError(400, "path leaves the repository") from None
        if any(p.startswith(".") for p in real.parts):
            raise PathError(400, "path leads into a hidden folder")
        return "/".join(parts), target

    def writable(self, rel: str, target: Path) -> bool:
        if rel.split("/")[0] != WRITABLE_ROOT or "/" not in rel:
            return False
        try:  # a symlinked folder under lessons/ must not lead elsewhere (lessons/x -> ../include)
            target.resolve().relative_to(self.root / WRITABLE_ROOT)
        except ValueError:
            return False
        if target.is_file():
            return True
        return not target.exists() and target.suffix in NEW_FILE_SUFFIXES

    def read(self, path: str) -> dict:
        rel, target = self.resolve(path)
        if not target.is_file():
            raise PathError(404, f"{rel}: no such file")
        data = target.read_bytes()
        return {
            "path": rel,
            "content": _to_lf(data.decode("utf-8", errors="replace")),
            "sha": sha_of(data),
            "eol": "crlf" if b"\r\n" in data else "lf",
            "writable": self.writable(rel, target),
        }

    def write(self, path: str, content: str, base_sha: str | None) -> dict:
        with self.write_lock:
            return self._write(path, content, base_sha)

    def _write(self, path: str, content: str, base_sha: str | None) -> dict:
        rel, target = self.resolve(path)
        if not self.writable(rel, target):
            raise PathError(403, f"{rel}: not writable from the web (lessons/ only)")
        if target.is_file():
            data = target.read_bytes()
            if base_sha != sha_of(data):
                raise Conflict(_to_lf(data.decode("utf-8", errors="replace")), sha_of(data))
            eol = "\r\n" if b"\r\n" in data else "\n"
            mode = stat.S_IMODE(target.stat().st_mode)
        else:
            if base_sha is not None:
                raise Conflict(None, None)  # the file was removed since it was opened
            eol = "\n"
            mode = 0o644
            # the folders created here are inside lessons/ (resolve() checked the full path)
            target.parent.mkdir(parents=True, exist_ok=True)
        out = _to_lf(content).replace("\n", eol).encode("utf-8")
        fd, tmp = tempfile.mkstemp(dir=target.parent, prefix=f".{target.name}.", suffix=".tmp")
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(out)
            os.chmod(tmp, mode)  # mkstemp creates 0600
            os.replace(tmp, target)
        except BaseException:
            Path(tmp).unlink(missing_ok=True)
            raise
        return {"sha": sha_of(out)}
