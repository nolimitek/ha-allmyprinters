"""Every language file has exactly the keys of strings.json; the card file is consistent."""

from __future__ import annotations

import json
from pathlib import Path

BASE = Path(__file__).parent.parent / "custom_components" / "allmyprinters"


def _keys(node, prefix=""):
    if isinstance(node, dict):
        out = set()
        for k, v in node.items():
            out |= _keys(v, f"{prefix}.{k}")
        return out
    return {prefix}


def test_translations_complete() -> None:
    reference = _keys(json.loads((BASE / "strings.json").read_text(encoding="utf-8")))
    files = sorted((BASE / "translations").glob("*.json"))
    assert {f.stem for f in files} == {"de", "en", "es", "fr", "it", "nl"}
    for f in files:
        keys = _keys(json.loads(f.read_text(encoding="utf-8")))
        assert keys == reference, (f.name, keys ^ reference)


def test_card_file() -> None:
    """The dashboard card ships with the integration; custom element names must start with a letter."""
    import re

    js = (BASE / "frontend" / "allmyprinters-card.js").read_text(encoding="utf-8")
    tags = re.findall(r'\["([a-z0-9-]+)", AllMyPrinters', js)
    assert set(tags) == {"allmyprinters-printer-card", "allmyprinters-stock-card", "allmyprinters-printer-card-editor",
                         "allmyprinters-job-card", "allmyprinters-slots-card", "allmyprinters-box-card"}
    assert all(re.match(r"^[a-z][a-z0-9]*-[a-z0-9-]+$", t) for t in tags)
    manifest = json.loads((BASE / "manifest.json").read_text(encoding="utf-8"))
    assert f'const VERSION = "{manifest["version"]}"' in js
    assert 'const DOMAIN = "allmyprinters"' in js


def test_entity_names_for_every_kind() -> None:
    """Every fan/light kind the agent reports has a name, and no text still talks about 3DSEARCH."""
    from custom_components.allmyprinters.const import FAN_KINDS, LIGHT_KINDS

    for f in [BASE / "strings.json", *(BASE / "translations").glob("*.json")]:
        data = json.loads(f.read_text(encoding="utf-8"))
        assert {f"fan_{k}" for k in FAN_KINDS} | {"fan_other"} == set(data["entity"]["fan"]), f.name
        assert {f"light_{k}" for k in LIGHT_KINDS} | {"light_other"} == set(data["entity"]["light"]), f.name
        assert "3dsearch" not in f.read_text(encoding="utf-8").lower(), f.name
