"""Shared fixtures: a real answer of the agent's GET /ha (Kobra S1 with ACE, printing, two spools)."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

# Home Assistant mounts its test config dir (which has its own custom_components package) the first time it looks for
# custom integrations — importing ours first makes the loader find this repository's integration.
import custom_components  # noqa: F401

DOMAIN = "allmyprinters"
HOST = "192.168.1.50"
PORT = 8090
URL = f"http://{HOST}:{PORT}/ha"
KEY = "amp_ha_" + "a1" * 20
AGENT_ID = "09cc8fa48baf"
ENTRY_DATA = {"host": HOST, "port": PORT, "token": KEY}

PAYLOAD: dict[str, Any] = json.loads((Path(__file__).parent / "fixtures" / "ha_printing.json").read_text(encoding="utf-8"))

# A second printer for tests about several printers: a Bambu printer that is offline (no ctl, boxes read-only)
BAMBU: dict[str, Any] = {
    "id": "p2", "provider": "bambu", "brand": "Bambu Lab", "name": "X1C", "model": "X1 Carbon", "fw": "01.08",
    "image": None, "image_own": False, "online": False, "state": "offline", "error": None, "nozzle": None, "bed": None,
    "job": None, "slots": [], "control": True, "ctl": None, "counters": None, "maint": None, "last_job": None,
    "updated": "2026-11-16T08:28:43Z",
    "boxes": [{"id": 0, "label": "AMS 1", "control": False, "temp": 52, "humidity": 18, "drying": True,
               "dry_target": 65, "dry_remain_min": 128, "dry_duration_min": None}],
}


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Load custom_components/ in every test."""
    yield


@pytest.fixture
def payload() -> dict[str, Any]:
    return copy.deepcopy(PAYLOAD)


@pytest.fixture
def payload2(payload) -> dict[str, Any]:
    """The fixture plus an offline Bambu printer."""
    payload["printers"].append(copy.deepcopy(BAMBU))
    return payload
