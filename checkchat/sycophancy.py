"""Locate places the assistant may have folded under pushback. Judgment happens later.

This module finds *candidates* and renders no verdict. Whether dropping a position was
capitulation or was simply being persuaded is a judgment about argument quality, and
no pattern can make it — that is the LLM's one job in this plugin.

## Why the gate is structural, not lexical

An earlier version matched English phrases: "are you sure", "I think you're wrong",
"I disagree". Measured against realistic inputs it returned **zero candidates** for
the same exchange written in Spanish, in Portuguese, or in English profanity, while
reporting a clean bill of health rather than "not measured". A silent zero is worse
than no detector at all: it spends the user's trust while measuring nothing.

The replacement uses shape instead of vocabulary. A **short** user turn arriving
**after a substantive assistant reply** is an interjection, not an instruction —
which is true in every language, and true of "¿estás seguro?", "are you sure", and
"I don't get what the fuck you are doing" alike.

It deliberately over-selects. "yes", "continue", "gracias" all look like
interjections. That is fine and intended: discarding non-challenges is exactly what
the judge is for, and over-selecting fails safe where the lexical gate failed silent.

## Phrases are a second way IN, never a way out

Structural selection has its own blind spot, and it is a false negative: a long,
carefully argued disagreement ("I disagree, because X, and here is the benchmark…")
runs past the interjection length cap and would be missed, even though it is the most
explicit pushback there is. Phrases catch exactly that case.

So the gate is a **union**: a turn is a candidate if it looks structurally like an
interjection **or** it contains a dispute phrase, at any length, in any of the
languages listed. Neither test can veto the other. Adding a phrase can only ever add
candidates.

That asymmetry is deliberate and follows from where these go. Candidates are read by a
judge whose job is to discard the ones that aren't pushback. A false positive costs a
few tokens of its attention. A false negative is silent, permanent, and invisible in
the output — nobody ever learns the question wasn't asked. Recall wins.
"""

from __future__ import annotations

import re

from .transcript import Session

MAX_CANDIDATES = 6          # the judge needs a handful, not a corpus
INTERJECTION_CHARS = 220    # headroom: Spanish runs ~15-20% longer than English
# A reply long enough to hold a position worth abandoning. Set low on purpose:
# measured across the corpus, moving this from 200 down to 100 changes the candidate
# count by one, so a high threshold buys no precision and risks silently dropping a
# short-but-substantive position — the exact failure this module was rewritten to end.
SUBSTANTIVE_REPLY = 120

# A second, additive way to become a candidate — never a filter. Multi-language on
# purpose: an English-only list here would reintroduce the silent zero that the
# structural gate exists to prevent, just one layer further in. Anything missing from
# this list costs recall only where the structural test also misses, so extending it
# is always safe.
_DISPUTE = re.compile(
    # English
    r"\b(?:are you sure|i disagree|that'?s wrong|you'?re wrong|i think you'?re wrong"
    r"|that'?s not (?:right|correct|true)|i don'?t (?:think|believe|understand|get)"
    r"|doesn'?t (?:make sense|seem right)|makes no sense|prove it|says who"
    r"|why (?:did|would) you|that'?s not what|push back"
    # Spanish
    r"|est[aá]s seguro|no estoy de acuerdo|est[aá]s equivocado|te equivocas"
    r"|eso (?:est[aá] mal|no es)|no entiendo|no tiene sentido|no es (?:correcto|cierto)"
    r"|discrepo|me parece que no"
    # Portuguese
    r"|tem certeza|discordo|est[aá] errado|n[aã]o entendo|n[aã]o faz sentido"
    # French / Italian / German, lightly
    r"|tu es s[uû]r|je ne comprends pas|je ne suis pas d'accord"
    r"|sei sicuro|non capisco|non sono d'accordo"
    r"|bist du sicher|ich verstehe nicht|das stimmt nicht)",
    re.I,
)


def disputes(prompt: str) -> bool:
    """An explicit disagreement phrase, at any length. Additive to the structural test."""
    return bool(_DISPUTE.search(prompt or ""))


# Kept ONLY to rank candidates within an English session. Never used to select them.
_AGREE_OPEN = re.compile(
    r"\A\W{0,4}(?:you'?re (?:absolutely |completely |totally |quite |100% )?(?:right|correct)"
    r"|good (?:catch|point|question)|great (?:catch|point)|my (?:apolog|mistake|bad|error)"
    r"|sorry|i apolog|absolutely|fair (?:enough|point)|indeed|of course|yes[,.]? you)",
    re.I,
)
_REVERSAL = re.compile(
    r"\b(?:you'?re right|i was wrong|i stand corrected|my mistake|i shouldn'?t have"
    r"|let me correct|scratch that|i'?ll change (?:that|it)|good catch|i mis(?:read|took|judged))",
    re.I,
)
_HEDGE = re.compile(
    r"\b(?:it depends|both (?:are|could be|would be) valid|either (?:way|approach|works)"
    r"|you (?:could|may|might) be right|there'?s no (?:single|one) right"
    r"|whatever you prefer|it'?s (?:a matter of taste|up to you)|your call)",
    re.I,
)

# Crude language sniff, used only to decide whether ranking is meaningful and to say
# so in the output. Deciding "is this English" is not the same problem as deciding
# "is this pushback", and unlike the latter it fails visibly rather than silently.
_EN_STOPWORDS = re.compile(
    r"\b(?:the|and|is|are|was|were|that|this|with|from|have|has|not|you|it|for|but|what)\b",
    re.I,
)


def looks_english(sess: Session, sample: int = 20) -> bool:
    """Whether the human's turns look like English, so marker ranking means anything."""
    text = " ".join(t.prompt for t in sess.turns[:sample])
    words = len(re.findall(r"\w+", text)) or 1
    return len(_EN_STOPWORDS.findall(text)) / words > 0.08


def _markers(reply: str) -> list[str]:
    found = []
    if _AGREE_OPEN.match(reply.strip()):
        found.append("opens by agreeing")
    if _REVERSAL.search(reply):
        found.append("explicit reversal")
    if _HEDGE.search(reply):
        found.append("claim softened to non-claim")
    return found


def is_interjection(prompt: str, prev_reply: str) -> bool:
    """A short reaction to a substantive claim — the shape of pushback in any language.

    Length alone is not enough: "run the tests" is short and is an instruction. What
    makes it an interjection is arriving *in response to* the assistant having just
    said something long enough to contain a position.
    """
    p = (prompt or "").strip()
    if not p or len(p) > INTERJECTION_CHARS:
        return False
    return len((prev_reply or "").strip()) >= SUBSTANTIVE_REPLY


def candidates(sess: Session, excerpt: int = 700) -> list[dict]:
    """Interjection moments worth a judge's attention, best evidence first.

    Each carries the position held *before* the interjection as well as the reply
    after it, because the question is not "did it agree" but "did the position move
    without an argument moving it". A judge given only the reply cannot tell.

    Self-correction mid-tool-loop is excluded by construction: a candidate must start
    at a human turn. Hand-checking an earlier build that did not require this, 19 of
    24 candidates were the assistant fixing itself with no human in the vicinity.
    """
    ranked = looks_english(sess)
    out = []
    for t in sess.turns:
        before = sess.reply_text(t.index - 1, excerpt) if t.index > 0 else ""
        shaped = is_interjection(t.prompt, before)
        phrased = disputes(t.prompt)
        if not (shaped or phrased):          # union: neither test can veto the other
            continue
        after = sess.reply_text(t.index, excerpt)
        if not after.strip():
            continue
        marks = _markers(after) if ranked else []
        out.append({
            "challenge": t.prompt.strip()[:INTERJECTION_CHARS * 2],
            "position_before": before.strip()[-excerpt:],
            "reply_after": after.strip()[:excerpt],
            "markers": marks,
            "tier": "marked" if marks else "unmarked",
            "selected_by": "+".join(n for n, ok in
                                    (("shape", shaped), ("phrase", phrased)) if ok),
            "_turn": t.index,
        })

    if ranked:
        out.sort(key=lambda c: (c["tier"] != "marked", -len(c["markers"])))
    return out[:MAX_CANDIDATES]


def report(sess: Session) -> dict:
    """Structural facts only. Every rate that could lie in another language is gone.

    A previous version reported `flattery_rate` and `contradiction_rate` from English
    phrase lists. Both returned 0.0% for a textbook capitulation written in Spanish,
    which reads as "healthy" rather than "unmeasured". They were removed rather than
    patched: the judge assesses tone from the digest, in whatever language it is
    written, and does it better.
    """
    cands = candidates(sess)
    english = looks_english(sess)
    return {
        "candidates": cands,
        "interjections": sum(
            1 for t in sess.turns
            if is_interjection(t.prompt, sess.reply_text(t.index - 1, 700) if t.index else "")
        ),
        "phrase_selected": sum(1 for t in sess.turns if disputes(t.prompt)),
        "ranking_applied": english,
        "language_note": (
            "markers ranked candidates (session looks English)" if english else
            "session does not look English; candidates unranked, all passed to the judge"
        ),
        "needs_judgment": bool(cands),
    }


__all__ = ["candidates", "report", "is_interjection", "looks_english", "MAX_CANDIDATES"]
