"""Diagnostics end up in public GitHub issues: neither the key nor the agent's address may be in them."""

from __future__ import annotations

import json

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.allmyprinters import diagnostics

from .conftest import AGENT_ID, DOMAIN, ENTRY_DATA, HOST, KEY, URL


async def _diagnostics(hass: HomeAssistant, aioclient_mock, payload) -> dict:
    entry = MockConfigEntry(domain=DOMAIN, unique_id=AGENT_ID, data=ENTRY_DATA, title="AllMyPrinters Agent")
    entry.add_to_hass(hass)
    aioclient_mock.get(URL, json=payload)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return await diagnostics.async_get_config_entry_diagnostics(hass, entry)


async def test_key_and_personal_data_are_removed(hass: HomeAssistant, aioclient_mock, payload) -> None:
    payload["spools"]["items"][0]["location"] = "Shelf 3"
    result = await _diagnostics(hass, aioclient_mock, payload)
    dumped = json.dumps(result)
    # The model ("Anycubic Kobra S1") stays; the name the user gave the printer goes
    for secret in (KEY, HOST, AGENT_ID, '"Kobra S1"', "Shelf 3", "benchy"):
        assert secret not in dumped, secret
    assert result["entry"]["token"] == "**REDACTED**"
    assert result["entry"]["host"] == "**REDACTED**"
    assert result["entry"]["port"] == 8090


async def test_useful_data_stays(hass: HomeAssistant, aioclient_mock, payload) -> None:
    result = await _diagnostics(hass, aioclient_mock, payload)
    first = result["data"]["printers"][0]
    assert isinstance(result["data"]["printers"], list)
    assert first["provider"] == "moonraker" and first["model"] == "Anycubic Kobra S1" and first["state"] == "printing"
    assert first["fw"] == "v0.12.0" and first["slots"] and first["ctl"]["fans"][0]["k"] == "part"
    assert result["data"]["agent"]["version"] == "0.5.7"
    assert result["data"]["features"] == {"panel": False, "light": True, "fan": True}
