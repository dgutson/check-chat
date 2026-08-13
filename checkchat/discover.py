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

**"Other sessions" means other sessions on this machine, not other sessions in this
folder.** That distinction is subtle enough to have cost the cross-session detector its
entire working life — it measured zero on every real session for as long as it shipped,
and the reason was here rather than in the detector. See `siblings()`.
"""

from __future__ import annotations

import json
import os
import zlib
from pathlib import Path
from typing import Callable, Iterable

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
    return _newest_first(d.glob("*.jsonl"))


def all_transcripts() -> list[Path]:
    """Every transcript on this machine, newest first.

    The right population for a cross-session question, and a different one from
    `transcripts()`. That answers "what else happened in this folder"; this answers "what
    else have I done", which is what a question whose payoff is a user-level skill is
    actually asking.

    **Subagent logs are not sessions, and are excluded** — the harness writes them one level
    deeper, at `projects/<dir>/<session-id>/subagents/agent-*.jsonl`, so the `*/*.jsonl`
    glob leaves them out. On this machine that is 64 of 319 files. Counting them would
    inflate every base rate and would let a subagent's own tool calls stand in as "another
    session that probed `--help`". Said out loud because the exclusion was a property of the
    glob's depth rather than of anything anyone decided, and a deliberate scope that only a
    glob knows about is item 12's failure waiting for a new route.
    """
    return _newest_first((_claude_home() / "projects").glob("*/*.jsonl"))


def _newest_first(paths) -> list[Path]:
    files = [f for f in paths if f.is_file() and f.stat().st_size > 0]
    return sorted(files, key=lambda f: f.stat().st_mtime, reverse=True)


def contains_bytes(path: Path, needle: bytes) -> bool:
    """Whether the raw bytes hold `needle`, read in bounded chunks.

    Overlaps the chunk boundary by `len(needle) - 1`, because a needle straddling two
    reads would otherwise be missed — a silent false negative in a pre-filter, which is
    the kind that looks like a real zero.

    Public because `sweep` memoises it: a corpus pass calls `siblings()` once per session,
    which would otherwise rescan every file's raw bytes once per session.
    """
    if not needle:
        return True
    try:
        with path.open("rb") as fh:
            tail = b""
            while chunk := fh.read(1 << 20):
                if needle in tail + chunk:
                    return True
                tail = chunk[-(len(needle) - 1):] if len(needle) > 1 else b""
    except OSError:
        return False
    return False


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
    cwd: str | Path,
    exclude: Path | None = None,
    limit: int = 25,
    scope: str = "machine",
    contains: str | None = None,
    exclude_forks_of: transcript.Session | None = None,
    loader: Callable[[Path], transcript.Session] = transcript.load,
    prefilter: Callable[[Path, bytes], bool] = contains_bytes,
) -> list[transcript.Session]:
    """Other sessions to compare this one against, forks already collapsed.

    The longest member of each fork family is kept: it is the one that actually contains
    the shared history plus whatever came after the split.

    `exclude` drops one *file*; `exclude_forks_of` drops every log that shares the session
    under test's history. Both are needed and the second is not obvious: resuming or
    rewinding copies the whole prefix, so a session's own fork is a second file containing
    the same evidence, and excluding only the path leaves it in the pool to corroborate
    its original. A cross-session finding built on that is one session counted twice — the
    exact artifact this module's header describes, arriving by a route the path exclusion
    does not cover.

    `scope="machine"` (the default) draws from every project on this machine;
    `scope="project"` restricts to `cwd`, which is what this function used to do
    unconditionally and is preserved only so a caller can ask the narrower question
    deliberately. Nothing asks it today — a cross-session check wants the whole machine,
    for the reason in `detect.cli_probes`.

    `contains` pre-rejects any transcript whose raw bytes lack that substring. **This is
    correctness, not just speed.** `limit` bounds the scan, and before the pre-filter it
    bounded it over *all* candidates — so the budget was mostly spent parsing sessions
    that could not contribute, and the ones that could sat outside the window and went
    unseen. Filtering first means every slot is spent on a session that might actually
    match. The trade is that the needle is one check's knowledge held by the caller: if a
    second cross-session check ever wants different data, this pre-filter will silently
    starve it, and that is the moment to make the requirement something a check declares
    rather than something `__main__` passes.

    `loader` and `prefilter` exist so a corpus pass can call *this* function instead of a
    corpus-wide model of it — the mistake `sweep`'s header is about. Their defaults are the
    shipping behaviour; `sweep` injects memos, which changes cost and not semantics.
    """
    candidates = transcripts(cwd) if scope == "project" else all_transcripts()
    ex = Path(exclude).resolve() if exclude is not None else None
    needle = contains.encode() if contains else b""

    # Filled lazily, newest first, and the walk stops at `limit`. Filtering the whole
    # corpus first and slicing afterwards costs a full read of every transcript to find
    # candidates that are then thrown away — so cost would scale with history rather than
    # with the budget, which is the one thing `limit` exists to prevent.
    chosen: list[Path] = []
    for f in candidates:
        if len(chosen) >= limit:
            break
        # Excluded before `limit`, so the session under test does not eat a scan slot.
        if ex is not None and f.resolve() == ex:
            continue
        if needle and not prefilter(f, needle):
            continue
        chosen.append(f)

    mine = fingerprint(exclude_forks_of) if exclude_forks_of is not None else None
    return collapse_forks((loader(f) for f in chosen), exclude_fp=mine)


def collapse_forks(sessions: Iterable[transcript.Session],
                   exclude_fp: str | None = None) -> list[transcript.Session]:
    """One session per fork family — the longest, since it holds the shared history plus
    whatever came after the split.

    Extracted from `siblings()` when `sweep` needed it, and extracted rather than copied
    for the reason in this module's header: ONE forked pair manufactured 100% of the
    apparent cross-session CLI-probing signal in the development corpus, and a corpus pass
    is where that mistake would scale. A second implementation of this is the last thing
    this project should own.

    `exclude_fp` drops a whole family rather than a file, which is what "not another
    session" has to mean when resuming copies a prefix.
    """
    keep: dict[str, transcript.Session] = {}
    for sess in sessions:
        if not sess.steps:
            continue
        fp = fingerprint(sess)
        if fp == exclude_fp:    # a fork of the session under test is not another session
            continue
        best = keep.get(fp)
        if best is None or len(sess.calls) > len(best.calls):
            keep[fp] = sess
    return list(keep.values())


__all__ = ["project_dir", "transcripts", "all_transcripts", "current", "fingerprint",
           "siblings"]
