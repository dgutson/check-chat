"""`python3 -m checkchat` — everything computable about this session, in one pass.

Output is JSON by default because the consumer is a skill, not a person. `--text`
exists for eyeballing it during development.

The whole run is deterministic and local. Nothing here calls a model, and nothing
leaves the machine: that is the point of the split. The skill spends model tokens on
exactly one thing this cannot do — judging whether the assistant folded under
pushback, and whether it is still working on what was asked.

Nothing in this file knows which checks exist. It walks the registry, so adding a
check never means editing the CLI.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

from . import checks, detect, digest, discover, inventory, transcript, verdict


def collect(cwd: str, session_id: str | None = None, siblings: int = 12) -> dict:
    started = time.time()
    path = discover.current(cwd, session_id)
    if path is None:
        return {
            "error": "no transcript found for this directory",
            "cwd": cwd,
            "hint": "pass --session <id>, or --cwd the directory the session was started in",
        }

    sess = transcript.load(path)
    if not sess.steps:
        return {"error": "transcript parsed but contains no assistant responses", "path": str(path)}

    # Machine-wide, not this directory: the one cross-session check asks whether syntax was
    # re-derived *before*, and its payoff is a skill, which is per user rather than per
    # folder. `contains` spends the scan budget only on transcripts that could match —
    # `detect.PROBE_NEEDLE` is that check's needle, and the coupling is deliberate and
    # documented in `discover.siblings`, which says what to do when a second one appears.
    others = discover.siblings(
        cwd, exclude=path, limit=siblings, contains=detect.PROBE_NEEDLE,
        exclude_forks_of=sess,
    ) if siblings else []
    results = checks.run(checks.Context(session=sess, others=others))

    out = {
        "session": {"path": str(path), "id": sess.session_id, **digest.stats(sess)},
        "checks": results,
        "catalog": checks.catalog(),
        "fired": sorted(n for n, r in results.items() if r.get("fired")),
        "capabilities": inventory.summary(cwd),
        "digest": digest.build(sess),
    }
    out["session"]["analysis_ms"] = int((time.time() - started) * 1000)
    return out


def _text(d: dict) -> str:
    if "error" in d:
        return f"error: {d['error']}"
    s = d["session"]
    partial = "  [PARTIAL]" if s.get("truncated") else ""
    lines = [
        f"session {(s.get('id') or '?')[:8]} | turns {s['turns']} responses {s['responses']} "
        f"calls {s['calls']} | depth {s['depth_tokens']:,} tok | {s['analysis_ms']}ms{partial}",
    ]

    # A `caveat` check qualifies every number below it, so it goes above them. Selected
    # by evidence level rather than by name, so the next one of its kind needs no edit.
    hoisted = [n for n, r in d["checks"].items()
               if r.get("evidence") == "caveat" and r.get("fired") and r.get("line")]
    for name in hoisted:
        lines.append(f"! {d['checks'][name]['line']}")

    # Dimensions come from the registry, never a literal list here: a hardcoded one
    # silently drops any check registered under a dimension nobody remembered to add.
    order = {"opportunity": 0, "specification": 1, "rot": 2, "sycophancy": 3, "context": 4}
    seen = dict.fromkeys(r.get("dimension", "") for r in d["checks"].values())
    for dim in sorted(seen, key=lambda x: (order.get(x, 99), x)):
        for name, r in d["checks"].items():
            if r.get("dimension") == dim and r.get("line") and name not in hoisted:
                mark = "*" if r.get("fired") else " "
                lines.append(f"{mark} {r['line']}")
    fired = d.get("fired") or []
    lines.append(f"\nfired: {', '.join(fired) if fired else 'nothing'}")
    return "\n".join(lines)


def _evidence(path: str) -> tuple[str | None, str]:
    """What the judge was shown, for checking its quotations against.

    Both `--emit` files count: the judge is told to read the digest *and* the candidates,
    so a quote from either is faithful. An unreadable path returns a reason rather than
    raising — a broken `--against` must not cost a usable verdict, only its verification.
    """
    p = Path(path)
    if p.is_dir():
        parts = [(p / n).read_text(errors="replace")
                 for n in ("digest.txt", "candidates.txt") if (p / n).is_file()]
        if not parts:
            return None, f"no digest.txt or candidates.txt in {p}"
        return "\n".join(parts), ""
    if p.is_file():
        return p.read_text(errors="replace"), ""
    return None, f"--against path does not exist: {p}"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="checkchat", description=__doc__)
    ap.add_argument("--cwd", default=os.getcwd(), help="directory the session runs in")
    ap.add_argument("--session", default=None, help="session id, if the newest is not the one")
    ap.add_argument("--siblings", type=int, default=12,
                    help="how many other sessions on this machine to scan for recurring "
                         "work, newest first, counting only those that could match "
                         "(0 disables). Recall of cross-session findings scales with it")
    ap.add_argument("--text", action="store_true", help="human-readable summary instead of JSON")
    ap.add_argument("--digest-only", action="store_true", help="print just the blinded excerpt")
    ap.add_argument("--catalog", action="store_true", help="list registered checks and exit")
    ap.add_argument("--verdict", metavar="PATH", nargs="?", const="-", default=None,
                    help="validate the judge's reply (PATH, or '-' for stdin) and exit "
                         "0 ok / 1 salvaged / 2 unusable")
    ap.add_argument("--against", metavar="PATH", default=None,
                    help="with --verdict, the evidence the judge was given (the --emit DIR, "
                         "or one file) — its quotations are checked against it")
    ap.add_argument("--json", action="store_true",
                    help="with --verdict, emit the normalised verdict as JSON")
    ap.add_argument("--emit", metavar="DIR", default=None,
                    help="write the judge's evidence to DIR and print only a summary, so the "
                         "excerpt never passes through the calling session's context")
    a = ap.parse_args(argv)

    if a.catalog:
        for c in checks.catalog():
            print(f"{c['name']:<14} {c['dimension']:<12} [{c['evidence']}]  {c['question']}")
        return 0

    if a.verdict is not None:
        raw = sys.stdin.read() if a.verdict == "-" else Path(a.verdict).read_text(errors="replace")
        excerpt, why = _evidence(a.against) if a.against else (None, "")
        v = verdict.check(raw, excerpt)
        if why:
            v.warnings.insert(0, f"quotes were NOT checked — {why}")
        print(json.dumps(v.as_dict(), indent=1) if a.json else verdict.render(v))
        return v.status

    d = collect(a.cwd, a.session, a.siblings)

    # The excerpt is the single biggest thing the calling session would otherwise have
    # to hold just to hand it onward. Writing it to disk and passing a path keeps the
    # diagnosing session's own context nearly free — which matters because that session
    # is often the one being diagnosed.
    if a.emit and "error" not in d:
        out = Path(a.emit)
        out.mkdir(parents=True, exist_ok=True)
        (out / "digest.txt").write_text(d["digest"])
        cands = d["checks"].get("sycophancy", {}).get("candidates", [])
        (out / "candidates.txt").write_text("\n\n".join(
            f"--- candidate {i} [selected_by={c.get('selected_by', '?')}]\n"
            f"CHALLENGE: {c['challenge']}\n\n"
            f"POSITION BEFORE: {c['position_before']}\n\n"
            f"REPLY AFTER: {c['reply_after']}"
            for i, c in enumerate(cands, 1)
        ) or "(no candidates located)")
        print(_text(d))
        print(f"\nevidence for the judge:\n  {out / 'digest.txt'}\n  {out / 'candidates.txt'}"
              f"\n  ({len(d['digest']):,} chars + {len(cands)} candidates, not shown here)")
        return 0

    if a.digest_only:
        print(d.get("digest", d.get("error", "")))
    elif a.text:
        print(_text(d))
    else:
        json.dump(d, sys.stdout, indent=1, default=str)
        print()
    return 1 if "error" in d else 0


if __name__ == "__main__":
    raise SystemExit(main())
