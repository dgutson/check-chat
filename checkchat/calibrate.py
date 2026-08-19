"""Item 27 — the one file a busy volunteer marks, and the merge that reads a stack of them.

`--sweep` already carries item 9's first half: how often each check fires on somebody
else's corpus. What no transcript contains is the second half — **whether the finding was
right**. `partial_use` fires on a `proof` tier and item 21 found 6 of 48 of its proofs
bogus, so the tier's honesty is currently unknown and is reaching users. Only a person who
was in the conversation can settle it, and the entire cost of settling it is their
attention. Every decision in this module spends that budget as if it were the scarce thing,
because it is.

**One command, one file, and the fast path is to mark nothing.** Marking forty boxes in a
text editor is fiddly enough that the file comes back empty, so the protocol inverts: a
blank row means *the tool was right*, and the volunteer marks only the rows it got wrong.
That is worth one honest caveat, stated here, in the file and in `render_merge` rather than
discovered later — **the rate this produces is biased low.** A row skimmed and a row
confirmed leave the same mark. `READ_ALL` is what keeps it from being meaningless: blanks
count as `ok` only in a file whose reader said they read every row, and `merge` scores an
unmarked file's blanks as `unjudged` instead of quietly crediting the checks with them.

**The rows are the shipping renderer's rows, not a richer form of them.** `checks.run`
returns `specifics` already capped by `evidence_rows`, and those are what `--text` puts in
front of a user — so a false positive among them is a false positive that reached somebody,
which is the quantity item 9 wants. It also keeps this module honest by construction: it
has no per-check knowledge at all, the same property `sweep` is built on. What it costs is
that a row longer than `SPECIFIC_WIDTH` arrives shortened, and "a truncated echo of a value
is not the value" is one of this project's own lab notes. The file says which rows were cut.

**Recall decay is the risk that decides the layout.** A proof from three weeks ago cannot
be judged from the finding alone, so every row also carries the date, the project directory
and the session id — and the footer says how to reopen that session, which is a stronger
memory aid than a turn number. Turn numbers appear only where the check itself put one in
its row; there is no generic way to extract one without knowing what each check computed,
and inventing per-check extraction here is how a second copy of the checks gets born.

**Selection is round-robin across checks, never "the first N".** `partial_use` at a 37%
firing rate would otherwise eat the whole budget and the rare checks would come back with
nothing, which is a calibration of one check wearing the costume of a calibration of six.
The cap and what it cut are printed per check, because a silent truncation reads as "that
was all of them" — the confident total this project keeps finding in its own output.

**What may be asked about is declared in the registry.** A check says what a row of its
evidence can disclose (`Check.discloses`), so the file's "what is in this file" paragraph is
composed from the checks actually present rather than from a sentence someone remembered to
update. And a check whose specifics are *pointers* rather than findings says so
(`Check.unjudgeable`) — `sycophancy` is one, since a candidate is not a finding until a
judge has ruled on it, and asking a volunteer to rule on unjudged candidates would collect
verdicts on a question the tool never asked.
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

from . import checks, sweep

# How many rows a volunteer is asked to judge. Not `LEDGER_ROWS`' 120: that cap bounds a
# machine's reading, and this one bounds a person's. Forty rows at roughly fifteen seconds
# of cold recall each is ten minutes, which is the most that can be asked of somebody who
# agreed to help and is short of time. Raised with `--calibrate-rows` by anyone who has more.
CALIBRATE_ROWS = 40
SECONDS_PER_ROW = 15

# How wide a row may be here, against `checks.SPECIFIC_WIDTH`'s 160 for the report. Measured
# over the development corpus's 300 evidence rows: p50 123, p90 175, p99 233, max 319. The
# report's 160 truncates 19% of all rows and **57% of the rows this file selects**, because
# selection favours `partial_use`, whose row carries a path and a command. A proof cut
# mid-argument cannot be answered and comes back `?`, so the cap that protects a summary is
# the cap that empties a calibration. 240 leaves 1% cut, and the file says how many.
CALIBRATE_WIDTH = 240

# The tiers that claim to be right about something specific, which is the same pair the
# skill is required to report with their specifics quoted. `ranked` and `descriptive` are
# excluded because they make no claim a person could call wrong: `dumps` says a payload cost
# what it cost, and "is that bogus?" has no answer.
JUDGEABLE_TIERS = ("proof", "evidenced")

# The sentinel that turns a blank box into a verdict. Identifier-shaped so one regex reads
# it and every row alike, and named in the file beside the box rather than in a legend
# somewhere else.
READ_ALL = "read_all"

DATA_MARK = "--- checkchat data, do not edit below this line ---"
SCHEMA = "checkchat-calibration-1"
PROJECT_WIDTH = 24

# What a mark in a box means. Spelled generously because the legend asks for one character
# and people type the word — but `x` is deliberately *not* here for a row box. It is the
# natural way to tick a `[ ]` and it says nothing about which verdict was meant, so it comes
# back as `unclear` and is counted apart rather than guessed at. On the `read_all` box, where
# there is only one thing it can mean, it is accepted.
_MARKS = {
    "ok": {"o", "ok", "y", "yes", "right", "correct", "✓", "v"},
    "bogus": {"b", "bogus", "n", "no", "wrong", "bad", "fp"},
    "unsure": {"?", "??", "u", "unsure", "dunno", "idk", "-"},
}
_AFFIRM = {"x", "✓", "y", "yes", "o", "ok", "done", "v"}

_ROW = re.compile(r"^\s*\[(?P<mark>[^\]]*)\]\s+(?P<check>[A-Za-z_][A-Za-z0-9_]*)\s*(?P<rest>.*)$")


def _mark(raw: str) -> str:
    m = raw.strip().lower()
    if not m:
        return "blank"
    for verdict, words in _MARKS.items():
        if m in words:
            return verdict
    return "unclear"


def _project(path: str) -> str:
    """The volunteer's own directory name, which is the half of "which session was this"
    that a file path in the row does not always carry — `producers` quotes a command and
    nothing else. Kept from the right: the harness encodes the whole cwd into one name, so
    the specific end is the tail."""
    name = Path(path).parent.name.lstrip("-") or "?"
    return name if len(name) <= PROJECT_WIDTH else "…" + name[-(PROJECT_WIDTH - 1):]


def _tool_version() -> str | None:
    """Which build produced this file, read from the manifest that sits beside the package.

    From the filesystem rather than a literal here, for the reason a literal fails: a second
    copy of `plugin.json`'s version goes stale exactly at the moment it matters, a release.
    `None` when the package is installed without the plugin manifest around it — a fact the
    merge prints rather than a default it invents, since "built by an unknown checkchat" and
    "built by 0.2.0" are different things to know about somebody else's file.

    R-010 generalises this to every report and to `--emit`, and will own it; the version lives
    here until then because this is the one output that cannot wait for it. A calibration file
    outlives the machine that made it and comes back weeks later from a volunteer whose
    install nobody can inspect.
    """
    manifest = Path(__file__).resolve().parent.parent / ".claude-plugin" / "plugin.json"
    try:
        data = json.loads(manifest.read_text())
    except (OSError, ValueError):
        return None
    version = data.get("version") if isinstance(data, dict) else None
    return str(version) if version else None


def _select(by_check: dict[str, list], cap: int) -> list[dict]:
    """Round-robin, so the loudest check cannot spend the whole of somebody's attention.

    Deterministic in check name and, within a check, in the order the sweep met the sessions
    — which is newest first, so a corpus that outgrows the cap is judged on its freshest
    rows. That is the same direction the recall-decay risk points in, and it is the reason
    this is not a random sample: a uniform sample of two years of sessions would be an
    unbiased sample of things nobody remembers.
    """
    out: list[dict] = []
    depth = 0
    while len(out) < cap and any(len(rows) > depth for rows in by_check.values()):
        for name in sorted(by_check):
            if len(by_check[name]) > depth and len(out) < cap:
                out.append(by_check[name][depth])
        depth += 1
    return out


def build(limit: int = 0, siblings: int = 12, cap: int = CALIBRATE_ROWS) -> dict:
    """The whole corpus, once, into everything the file needs.

    One pass, because `sweep.run` already walks the population *and* owns the two refusals
    and the fork collapse that make it the right population. Re-walking it here would be a
    second copy of that logic and would drift from it; `observe` exists so the aggregate
    stays byte-identical to the one `--sweep` sends while the rows come out beside it.
    """
    by_check: dict[str, list[dict]] = {}
    found: dict[str, int] = {}
    skipped: dict[str, str] = {}

    def observe(sess, results: dict) -> None:
        date = (sess.started or "")[:10] or "undated"
        for name, r in results.items():
            chk = checks.REGISTRY.get(name)
            if not chk or chk.evidence not in JUDGEABLE_TIERS or not r.get("fired"):
                continue
            if chk.unjudgeable:
                skipped[name] = chk.unjudgeable
                continue
            # Only the real rows. `evidence_rows` appends a sentence about its own cut when
            # it truncates, and that sentence is not a finding — handing it to somebody to
            # rule on would collect a verdict on the renderer. Sliced by the same constant
            # that produced it rather than matched by its text, so a reworded cut note cannot
            # turn into a judgeable row.
            for text in (r.get("specifics") or [])[:checks.SPECIFIC_ROWS]:
                found[name] = found.get(name, 0) + 1
                by_check.setdefault(name, []).append({
                    "check": name,
                    "date": date,
                    "project": _project(sess.path),
                    "session": (sess.session_id or "?")[:8],
                    "text": text,
                })

    aggregate = sweep.run(limit=limit, siblings=siblings, observe=observe,
                          evidence_width=CALIBRATE_WIDTH)
    rows = _select(by_check, cap)
    shown: dict[str, int] = {}
    for row in rows:
        shown[row["check"]] = shown.get(row["check"], 0) + 1

    return {
        "generated": time.strftime("%Y-%m-%d"),
        "version": _tool_version(),
        "cap": cap,
        "sessions": aggregate["sessions"],
        "minutes": max(1, round(len(rows) * SECONDS_PER_ROW / 60)),
        "rows": rows,
        "counts": {name: {"found": found[name], "shown": shown.get(name, 0)}
                   for name in sorted(found)},
        # Composed from the checks whose rows are actually in the file, so a file that
        # happens to contain no `specification` row does not warn about prompts it does not
        # carry — and a check added tomorrow cannot be disclosed by an old sentence.
        "discloses": sorted({checks.REGISTRY[name].discloses for name in shown
                             if checks.REGISTRY[name].discloses}),
        "truncated_rows": sum(1 for r in rows if r["text"].endswith("…")),
        "skipped": dict(sorted(skipped.items())),
        "aggregate": aggregate,
    }


def _data_block(d: dict) -> str:
    """The aggregate, verbatim, for the merge to read without re-parsing prose.

    Only the aggregate and the counts. The verdicts are read from the marked lines above and
    from nowhere else, because two places to learn the same fact is two answers when a file
    comes back edited — and the marked lines are the ones the volunteer can see.

    `version` is additive and `SCHEMA` deliberately does not move for it: `parse` reads every
    key with `.get`, so an old build reading this block ignores the field and a new build
    reading an old block sees `None`, which is the fact it should see. Bumping the schema
    would turn every file already in flight into a mismatch warning about a key that changed
    nothing for the reader.
    """
    return json.dumps({"schema": SCHEMA, "generated": d["generated"], "cap": d["cap"],
                       "version": d["version"],
                       "sessions": d["sessions"], "rows_shown": len(d["rows"]),
                       "counts": d["counts"], "aggregate": d["aggregate"]}, default=str)


def render(d: dict) -> str:
    """Everything `build` computes, because nothing a producer computes is rendered by
    default — item 19's rule, and this producer's only renderer is the file itself.

    The rows come *before* the aggregate, which is the one place this departs from item 27's
    wording. The aggregate needs nothing from the reader and the rows are the entire ask; a
    screen of statistics between the instructions and the boxes is a screen of somebody's
    ten minutes.
    """
    rows = d["rows"]
    disclosure = [f"  - {s}" for s in d["discloses"]] or ["  - (nothing fired; no rows)"]
    out = [
        f"checkchat calibration — {len(rows)} findings, {d['minutes']} min. Send this file "
        f"back as it is, or mark it first.",
        "",
        f"FROM {d['sessions']} session transcripts on this machine, read on {d['generated']} "
        f"by checkchat {d['version'] or '(version unknown)'}. "
        f"NOT anonymous — each row carries:",
        *disclosure,
        "  - the date, the project directory name and the session id of each one",
        "No assistant replies, no file contents.",
        "",
        "TO MARK IT:",
        f"  [ ] {READ_ALL}   put an x here once you have read every row below",
        "  then  b  in the box of any row the tool got WRONG,  ?  in any row you cannot tell "
        "about, blank = right.",
        "  Blanks count only if the box above is marked; otherwise every row scores as "
        "unjudged.",
        "",
    ]

    for name in sorted(d["counts"]):
        c = d["counts"][name]
        mine = [r for r in rows if r["check"] == name]
        chk = checks.REGISTRY.get(name)
        if not mine:
            # A check the cap starved. It says so rather than being absent, because a check
            # missing from this file is indistinguishable from a check that never fired.
            out.append(f"--- {name} — {c['found']} found, 0 shown (the {d['cap']}-row cap "
                       f"was reached) — raise it with --calibrate-rows")
            out.append("")
            continue
        out.append(f"--- {name} — {chk.evidence if chk else '?'} — "
                   f"{chk.question if chk else ''}")
        out.append(f"    showing {c['shown']} of {c['found']} found "
                   f"(cap {d['cap']} rows, spread evenly across checks)")
        for r in mine:
            out.append(f" [ ] {name}  {r['date']}  {r['project']:<{PROJECT_WIDTH}}  "
                       f"{r['session']}  {r['text']}")
        out.append("")

    out = out + ["--- notes " + "-" * 68,
                 "To see a session again: cd into that project and `claude --resume <the "
                 "8-char id above>`."]
    if d["truncated_rows"]:
        out.append(f"{d['truncated_rows']} rows end in … — evidence longer than "
                   f"{CALIBRATE_WIDTH} chars. Mark those ? if the cut took what you needed.")
    for name, why in d["skipped"].items():
        out.append(f"Not asked about: {name} — {why}")

    out += ["", "--- the aggregate, which needs nothing from you " + "-" * 31, "",
            sweep.render(d["aggregate"]), "", DATA_MARK, _data_block(d), ""]
    return "\n".join(out)


# ------------------------------------------------------------------ the other end

def parse(text: str, name: str = "") -> dict:
    """A returned file, back into verdicts.

    Tolerant on purpose: this reads a file a person has edited in whatever editor they had,
    so an unrecognised mark, a missing data block or a deleted section is a *warning* beside
    the rows that did survive, never an exception. A stack of files where one is unparseable
    must still produce the rate for the rest — Daniel is handed files, and a merge that dies
    on the third one is the hand-merging this exists to end.
    """
    warnings: list[str] = []
    rows: list[dict] = []
    unknown: set[str] = set()
    read_all = False
    for line in text.splitlines():
        m = _ROW.match(line)
        if not m:
            continue
        check, raw = m.group("check"), m.group("mark")
        if check == READ_ALL:
            read_all = raw.strip().lower() in _AFFIRM
            if raw.strip() and not read_all:
                warnings.append(f"{name or 'file'}: the {READ_ALL} box holds "
                                f"{raw.strip()!r}, which is not a yes — blanks below are "
                                f"scored as unjudged")
            continue
        if check not in checks.REGISTRY:
            # Kept, not dropped. A file can come back from a build with a check this one has
            # not got, and a verdict silently discarded for that reason is worse than a row
            # under an unfamiliar name — the merge prints the name, so an unknown one is
            # visible rather than absent. A stray line someone typed lands here too, which
            # is what the warning is for.
            unknown.add(check)
        rows.append({"check": check, "mark": _mark(raw), "raw": raw.strip(),
                     "text": m.group("rest").strip()})

    if unknown:
        warnings.append(f"{name or 'file'}: rows name {len(unknown)} check(s) this build does "
                        f"not have ({', '.join(sorted(unknown))}) — counted under those names")
    unclear = [r["raw"] for r in rows if r["mark"] == "unclear"]
    if unclear:
        warnings.append(f"{name or 'file'}: {len(unclear)} boxes hold a mark the legend does "
                        f"not define ({', '.join(sorted(set(unclear))[:5])}) — counted as "
                        f"unclear, not as a verdict")

    aggregate = None
    version = None
    if DATA_MARK in text:
        try:
            block = json.loads(text.split(DATA_MARK, 1)[1].strip().splitlines()[0])
            aggregate = block.get("aggregate")
            version = block.get("version")
            if block.get("schema") != SCHEMA:
                warnings.append(f"{name or 'file'}: data block says schema "
                                f"{block.get('schema')!r}, this build writes {SCHEMA!r}")
        except (ValueError, IndexError) as exc:
            warnings.append(f"{name or 'file'}: the data block did not parse ({exc}) — "
                            f"verdicts below are still counted")
    else:
        warnings.append(f"{name or 'file'}: no data block, so this corpus contributes "
                        f"verdicts but no base rate")

    return {"name": name, "read_all": read_all, "rows": rows,
            "aggregate": aggregate, "version": version, "warnings": warnings}


def merge(files: list[dict]) -> dict:
    """A stack of returned files into one false-positive rate per check.

    The `read_all` gate is applied here rather than in `parse` so that the raw marks stay
    readable: a file that came back with the box unticked is not thrown away, it just cannot
    lend its blanks to anybody's precision. `unsure` and `unclear` are counted and never
    folded into either side — the whole reason a third verdict exists is that a forced binary
    on a half-remembered row is a coin flip wearing a number's clothes.
    """
    per_file: list[dict] = []
    per_check: dict[str, dict] = {}
    shares: dict[str, list] = {}
    skipped: dict[str, str] = {}
    warnings: list[str] = []

    def bucket(name: str) -> dict:
        return per_check.setdefault(name, {"ok": 0, "bogus": 0, "unsure": 0,
                                           "unclear": 0, "unjudged": 0})

    for f in files:
        warnings += f["warnings"]
        tally = {"ok": 0, "bogus": 0, "unsure": 0, "unclear": 0, "unjudged": 0}
        for r in f["rows"]:
            mark = r["mark"]
            if mark == "blank":
                mark = "ok" if f["read_all"] else "unjudged"
            tally[mark] += 1
            bucket(r["check"])[mark] += 1
        agg = f.get("aggregate") or {}
        per_file.append({"name": f["name"], "rows": len(f["rows"]),
                         "read_all": f["read_all"], "version": f.get("version"),
                         "sessions": agg.get("sessions"), **tally})
        # Kept per file rather than per check, so a check that first appears in the third
        # file still lines its shares up with the corpora they came from. A file with no
        # data block contributes no share and says so as a gap, not as a zero — a corpus
        # where a check fired 0% and a corpus that never reported are different facts.
        # The tier is read from the *aggregate*, not from this build's registry: the file
        # came from somebody else's machine and it says what its own checks were. A local
        # lookup would silently drop a check this build has not got, which is the same
        # discard the row parser refuses. The one thing the local registry is asked is
        # whether a check is `unjudgeable` — `sycophancy` fires in half of all sessions and
        # would otherwise sit in this table at a permanent 0/0, which reads as a check
        # nobody bothered to judge rather than one the file never asked about.
        for name, c in (agg.get("checks") or {}).items():
            chk = checks.REGISTRY.get(name)
            if chk is not None and chk.unjudgeable:
                skipped[name] = chk.unjudgeable
                continue
            if isinstance(c, dict) and c.get("share") is not None \
                    and c.get("evidence") in JUDGEABLE_TIERS:
                bucket(name)
                shares.setdefault(name, []).append(c["share"])

    for name, c in per_check.items():
        c["shares"] = shares.get(name, [])
        judged = c["ok"] + c["bogus"]
        c["judged"] = judged
        c["fp_rate"] = round(c["bogus"] / judged, 3) if judged else None

    # One rate over files from different builds is one number over two populations. Trap 8 is
    # the case that proves it rather than the case that worries about it: recovering the brief
    # typed after a slash command changed *which turns exist*, so a check's rows before and
    # after it are counts of different things and pool into a figure describing neither. Said
    # as a warning and not as a refusal — a stack that spans builds is still the best evidence
    # anyone has, and a merge that dies on it is the hand-merging this module exists to end.
    builds = sorted({str(f["version"] or "unknown") for f in per_file})
    if len(builds) > 1:
        warnings.append(f"the stack spans {len(builds)} builds ({', '.join(builds)}) — a rate "
                        f"pooled across them assumes every build counted the same turns, and "
                        f"trap 8 is a build where that is false")

    return {"files": per_file, "checks": dict(sorted(per_check.items())),
            "corpora": len(per_file),
            "rows": sum(f["rows"] for f in per_file),
            "builds": builds,
            "skipped": dict(sorted(skipped.items())),
            "warnings": warnings}


def render_merge(m: dict) -> str:
    """What the merge computed, all of it — including the sentence that says what the number
    is not. A precision figure with no protocol beside it is the kind of clean number this
    project has been fooled by three times."""
    out = [f"checkchat calibration merge — {m['corpora']} files, {m['rows']} rows, "
           f"built by {', '.join(m['builds']) or '—'}", "",
           f"{'file':<28} {'built':>7} {'rows':>5} {'read_all':>9} {'sessions':>9} {'ok':>4} "
           f"{'bogus':>6} {'unsure':>7} {'unclear':>8} {'unjudged':>9}"]
    for f in m["files"]:
        # The basename, not the tail of the path: `--calibrate-merge received/*.txt` gives
        # every file the same last 28 characters otherwise, and a table whose rows cannot be
        # told apart is a table that cannot be acted on.
        out.append(f"{Path(f['name'] or '?').name[:28]:<28} "
                   f"{str(f['version'] or 'unknown'):>7} {f['rows']:>5} "
                   f"{'yes' if f['read_all'] else 'NO':>9} "
                   f"{(f['sessions'] if f['sessions'] is not None else '?'):>9} "
                   f"{f['ok']:>4} {f['bogus']:>6} {f['unsure']:>7} {f['unclear']:>8} "
                   f"{f['unjudged']:>9}")
    out += ["", f"{'check':<16} {'judged':>7} {'bogus':>6}  {'false positive':<16} "
                f"{'unsure':>7} {'unclear':>8} {'unjudged':>9}  fired share per corpus"]
    for name, c in m["checks"].items():
        rate = "n/a, none judged" if c["fp_rate"] is None else \
            f"{c['fp_rate']:.0%} ({c['bogus']}/{c['judged']})"
        shares = ", ".join(f"{s:.0%}" for s in c["shares"]) or "—"
        out.append(f"{name:<16} {c['judged']:>7} {c['bogus']:>6}  {rate:<16} "
                   f"{c['unsure']:>7} {c['unclear']:>8} {c['unjudged']:>9}  {shares}")
    for name, why in m["skipped"].items():
        out.append(f"{name:<16} not asked about — {why}")
    out += ["",
            "WHAT THIS RATE IS NOT. The file asks for a mark only on rows the tool got "
            "wrong, so a",
            "row skimmed and a row confirmed leave the same blank: the rate is biased LOW "
            "and is an",
            "optimistic bound on precision, not a measurement of it. A file with read_all "
            "NO lends no",
            "blanks at all. `unsure` and `unclear` are outside the rate on purpose and are "
            "never folded in.",
            "The shares are each corpus's own firing rate, printed side by side and not "
            "pooled: medians",
            "do not average."]
    for w in m["warnings"]:
        out.append(f"! {w}")
    return "\n".join(out)


__all__ = ["build", "render", "parse", "merge", "render_merge", "CALIBRATE_ROWS",
           "JUDGEABLE_TIERS", "READ_ALL", "DATA_MARK", "SCHEMA"]
