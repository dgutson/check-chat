"""What capabilities already exist, so check-chat never proposes building one twice.

The user's rule — don't spend tokens on what a script can do — applies to the
existence check itself. Everything installed is on disk and can be enumerated for
free; only the question "does something like this exist that I *haven't* installed"
needs to leave the machine, and there is already a plugin for that (`plugin-finder`),
so check-chat delegates rather than reimplementing search.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

_FRONTMATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.S)


@dataclass
class Capability:
    name: str
    description: str
    kind: str          # "user-skill" | "project-skill" | "plugin-skill" | "command"
    origin: str        # plugin or marketplace it came from, or "user"
    path: str = ""

    @property
    def label(self) -> str:
        return f"{self.origin}:{self.name}" if self.origin not in ("user", "project") else self.name


def _frontmatter(text: str) -> dict:
    """Minimal YAML front-matter reader — enough for `name:` and `description:`.

    Deliberately not a YAML dependency: two scalar keys, one of which is often a
    folded multi-line block, is not worth an install.
    """
    m = _FRONTMATTER.match(text or "")
    if not m:
        return {}
    out, key, buf = {}, None, []
    for line in m.group(1).splitlines():
        if not line.strip():
            continue
        head = re.match(r"^([A-Za-z_-]+):\s*(.*)$", line)
        if head and not line.startswith((" ", "\t")):
            if key:
                out[key] = " ".join(buf).strip()
            key = head.group(1).strip()
            val = head.group(2).strip()
            buf = [] if val in (">", "|", ">-", "|-", "") else [val]
        elif key:
            buf.append(line.strip())
    if key:
        out[key] = " ".join(buf).strip()
    return out


def _skill_at(d: Path, kind: str, origin: str) -> Capability | None:
    f = d / "SKILL.md"
    try:
        fm = _frontmatter(f.read_text(errors="replace"))
    except Exception:
        return None
    return Capability(
        name=(fm.get("name") or d.name).strip(),
        description=(fm.get("description") or "").strip(),
        kind=kind,
        origin=origin,
        path=str(f),
    )


def _claude_home() -> Path:
    return Path(os.environ.get("CLAUDE_CONFIG_DIR") or (Path.home() / ".claude"))


def installed(cwd: str | Path | None = None) -> list[Capability]:
    """Every skill reachable from this session, deduplicated."""
    home = _claude_home()
    found: dict[tuple[str, str], Capability] = {}

    def add(cap: Capability | None):
        if cap and cap.name:
            found.setdefault((cap.origin, cap.name), cap)

    for d in sorted((home / "skills").glob("*/")):
        add(_skill_at(d, "user-skill", "user"))

    if cwd:
        for d in sorted((Path(cwd) / ".claude" / "skills").glob("*/")):
            add(_skill_at(d, "project-skill", "project"))

    # Plugin skills live under both marketplaces/ and cache/<mp>/<plugin>/<version>/.
    # Keyed by (origin, name) so the same skill from both trees collapses to one.
    for f in (home / "plugins").rglob("skills/*/SKILL.md"):
        parts = f.parts
        origin = "plugin"
        for marker in ("marketplaces", "cache"):
            if marker in parts:
                i = parts.index(marker)
                origin = parts[i + 1] if i + 1 < len(parts) else "plugin"
                break
        add(_skill_at(f.parent, "plugin-skill", origin))

    return sorted(found.values(), key=lambda c: (c.kind, c.origin, c.name))


def enabled_plugins() -> dict:
    try:
        s = json.loads((_claude_home() / "settings.json").read_text())
    except Exception:
        return {}
    return {
        "plugins": sorted(k for k, v in (s.get("enabledPlugins") or {}).items() if v),
        "marketplaces": sorted(s.get("extraKnownMarketplaces") or {}),
    }


def finder_available() -> bool:
    """Is `plugin-finder` installed? If so, delegate discovery to it."""
    return any("plugin-finder" in p for p in enabled_plugins().get("plugins", []))


def summary(cwd: str | Path | None = None) -> dict:
    caps = installed(cwd)
    return {
        "capabilities": [
            {"name": c.name, "kind": c.kind, "origin": c.origin, "description": c.description}
            for c in caps
        ],
        "count": len(caps),
        **enabled_plugins(),
        "plugin_finder": finder_available(),
    }
