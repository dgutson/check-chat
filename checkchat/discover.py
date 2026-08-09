"""Find the transcript for the session that is running right now, and its siblings.

Two things here are less obvious than they look.

**Which file is "this session".** Claude Code writes one JSONL per session under
`~/.claude/projects/<mangled-cwd>/<session-id>.jsonl`, mangling by replacing `/` and
`.` with `-`. The live session's file is the one still being appended to, so newest
mtime wins. When the mangling guess misses, fall back to reading each candidate's
first record and matching its recorded `cwd` — slower, but it cannot be fooled.

**Forked logs are not independent sessions.** Resuming or rewinding a session copies
the whole prefix into a new file. Counting both as evidence double-counts one piece
of history, and cross-session claims are exactly where that bites: in the corpus this
plugin was built from, ONE forked pair manufactured 100% of the apparent
cross-session CLI-probing signal. Anything that counts across sessions must dedupe
first, so `siblings()` does it by default rather than leaving it to the caller.
"""

from __future__ import annotations

import json
import os
import zlib
from pathlib import Path

from . import transcript


def _claude_home() -> Path:
    return Path(os.environ.get("CLAUDE_CONFIG_DIR") or (Path.home() / ".claude"))


def project_dir(cwd: str | Path) -> Path | None:
    """The transcript directory for a working directory, or None if it has none."""
    root = _claude_home() / "projects"
    guess = root / str(Path(cwd).resolve()).replace("/", "-").replace(".", "-")
    if guess.is_dir():
        return guess

    want = str(Path(cwd).resolve())
    best: tuple[float, Path] | None = None
    for d in root.glob("*/"):
        for f in d.glob("*.jsonl"):
            if _first_cwd(f) == want and (best is None or f.stat().st_mtime > best[0]):
                best = (f.stat().st_mtime, d)
            break
    return best[1] if best else None


def _first_cwd(path: Path) -> str:
    try:
        with path.open("r", errors="replace") as fh:
            for line in fh:
                if '"cwd"' not in line:
                    continue
                rec = json.loads(line)
                if isinstance(rec, dict) and rec.get("cwd"):
                    return rec["cwd"]
    except Exception:
        pass
    return ""


def transcripts(cwd: str | Path) -> list[Path]:
    """Every transcript for this directory, newest first."""
    d = project_dir(cwd)
    if not d:
        return []
    files = [f for f in d.glob("*.jsonl") if f.stat().st_size > 0]
    return sorted(files, key=lambda f: f.stat().st_mtime, reverse=True)


def current(cwd: str | Path, session_id: str | None = None) -> Path | None:
    """The transcript of the running session — newest by mtime, since it is still open."""
    files = transcripts(cwd)
    if session_id:
        for f in files:
            if f.stem == session_id:
                return f
    return files[0] if files else None


def fingerprint(sess: transcript.Session) -> str:
    """Identity of a session's *history*, so a fork collapses onto its parent.

    Start time plus the first ten tool inputs: a fork shares both, and two genuinely
    separate sessions realistically share neither.
    """
    seed = "|".join(
        f"{c.tool}:{zlib.crc32(json.dumps(c.params, sort_keys=True, default=str).encode()):x}"
        for c in sess.calls[:10]
    )
    return f"{sess.started[:19]}|{zlib.crc32(seed.encode()):x}"


def siblings(
    cwd: str | Path, exclude: Path | None = None, limit: int = 25
) -> list[transcript.Session]:
    """Other sessions in this directory, forks already collapsed.

    The longest member of each fork family is kept: it is the one that actually
    contains the shared history plus whatever came after the split.
    """
    keep: dict[str, transcript.Session] = {}
    for f in transcripts(cwd)[:limit]:
        if exclude and f.resolve() == Path(exclude).resolve():
            continue
        sess = transcript.load(f)
        if not sess.steps:
            continue
        fp = fingerprint(sess)
        best = keep.get(fp)
        if best is None or len(sess.calls) > len(best.calls):
            keep[fp] = sess
    return list(keep.values())


__all__ = ["project_dir", "transcripts", "current", "fingerprint", "siblings"]
