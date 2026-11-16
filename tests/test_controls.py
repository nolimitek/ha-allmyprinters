"""Lights and fans: commands to the agent, errors, optimistic state and the refresh shortly after a command."""

from __future__ import annotations

from datetime import timedelta

import pytest

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed

from .conftest import AGENT_ID, DOMAIN, ENTRY_DATA, URL


async def _setup(hass: HomeAssistant, aioclient_mock, payload) -> MockConfigEntry:
    entry = MockConfigEntry(domain=DOMAIN, unique_id=AGENT_ID, data=ENTRY_DATA)
    entry.add_to_hass(hass)
    aioclient_mock.get(URL, json=payload)
    aioclient_mock.post(URL, json={"ok": True})
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def _posts(aioclient_mock) -> list[dict]:
    return [c[2] for c in aioclient_mock.mock_calls if c[0] == "POST"]


def _gets(aioclient_mock) -> int:
    return len([c for c in aioclient_mock.mock_calls if c[0] == "GET"])


async def test_light_turn_off_and_on(hass: HomeAssistant, aioclient_mock, payload) -> None:
    await _setup(hass, aioclient_mock, payload)
    await hass.services.async_call("light", "turn_off", {"entity_id": "light.kobra_s1_light"}, blocking=True)
    assert _posts(aioclient_mock)[-1] == {"cmd": "light", "printer": "p1", "id": "power:chamber_light", "on": False}
    assert hass.states.get("light.kobra_s1_light").state == "off"   # shown right away, before the agent confirms

    await hass.services.async_call("light", "turn_on", {"entity_id": "light.kobra_s1_light"}, blocking=True)
    assert _posts(aioclient_mock)[-1] == {"cmd": "light", "printer": "p1", "id": "power:chamber_light", "on": True}
    assert hass.states.get("light.kobra_s1_light").state == "on"


async def test_fan_percentage(hass: HomeAssistant, aioclient_mock, payload) -> None:
    await _setup(hass, aioclient_mock, payload)
    fan = "fan.kobra_s1_part_fan"
    await hass.services.async_call("fan", "set_percentage", {"entity_id": fan, "percentage": 40}, blocking=True)
    assert _posts(aioclient_mock)[-1] == {"cmd": "fan", "printer": "p1", "id": "fan", "pct": 40}
    st = hass.states.get(fan)
    assert st.state == "on" and st.attributes["percentage"] == 40

    await hass.services.async_call("fan", "turn_off", {"entity_id": "fan.kobra_s1_air_filter"}, blocking=True)
    assert _posts(aioclient_mock)[-1] == {"cmd": "fan", "printer": "p1", "id": "fan_generic air_filter_fan", "pct": 0}
    # Turned on without a speed: back to the speed it ran at (60 %)
    await hass.services.async_call("fan", "turn_on", {"entity_id": "fan.kobra_s1_air_filter"}, blocking=True)
    assert _posts(aioclient_mock)[-1]["pct"] == 60
    # A fan that never ran goes to full speed
    await hass.services.async_call("fan", "turn_on", {"entity_id": "fan.kobra_s1_enclosure_fan"}, blocking=True)
    assert _posts(aioclient_mock)[-1] == {"cmd": "fan", "printer": "p1", "id": "fan_generic box_fan", "pct": 100}


async def test_print_only_error(hass: HomeAssistant, aioclient_mock, payload) -> None:
    await _setup(hass, aioclient_mock, payload)
    aioclient_mock.clear_requests()
    aioclient_mock.get(URL, json=payload)
    aioclient_mock.post(URL, status=400, json={"error": "print_only"})
    with pytest.raises(HomeAssistantError) as err:
        await hass.services.async_call("fan", "set_percentage", {"entity_id": "fan.kobra_s1_part_fan", "percentage": 80},
                                       blocking=True)
    assert err.value.translation_domain == DOMAIN and err.value.translation_key == "print_only"
    assert hass.states.get("fan.kobra_s1_part_fan").attributes["percentage"] == 0   # nothing optimistic on failure

    aioclient_mock.clear_requests()
    aioclient_mock.get(URL, json=payload)
    aioclient_mock.post(URL, status=400, json={"error": "bad_command"})
    with pytest.raises(HomeAssistantError) as err:
        await hass.services.async_call("light", "turn_off", {"entity_id": "light.kobra_s1_light"}, blocking=True)
    assert err.value.translation_key == "command_failed" and err.value.translation_placeholders == {"error": "bad_command"}
    assert hass.states.get("light.kobra_s1_light").state == "on"


async def test_refresh_after_command(hass: HomeAssistant, aioclient_mock, payload) -> None:
    """The agent applies a command and updates itself ~1.5 s later — Home Assistant asks again shortly after."""
    entry = await _setup(hass, aioclient_mock, payload)
    gets = _gets(aioclient_mock)
    await hass.services.async_call("light", "turn_off", {"entity_id": "light.kobra_s1_light"}, blocking=True)
    assert _gets(aioclient_mock) == gets   # not at once: that would still return the old state

    payload["printers"][0]["ctl"]["lights"][0]["on"] = False
    aioclient_mock.clear_requests()
    aioclient_mock.get(URL, json=payload)
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=3))
    await hass.async_block_till_done()
    assert _gets(aioclient_mock) == 1
    assert hass.states.get("light.kobra_s1_light").state == "off"
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_pending_refresh_cancelled_on_unload(hass: HomeAssistant, aioclient_mock, payload) -> None:
    entry = await _setup(hass, aioclient_mock, payload)
    await hass.services.async_call("light", "turn_off", {"entity_id": "light.kobra_s1_light"}, blocking=True)
    assert await hass.config_entries.async_unload(entry.entry_id)
    aioclient_mock.clear_requests()
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=3))
    await hass.async_block_till_done()
    assert _gets(aioclient_mock) == 0


async def test_two_lights_of_one_kind(hass: HomeAssistant, aioclient_mock, payload) -> None:
    """Two lights of the same kind are named after the printer's own names, not "Light" twice."""
    payload["printers"][0]["ctl"]["lights"].append({"id": "led2", "k": "chamber", "name": "top_led", "on": False})
    await _setup(hass, aioclient_mock, payload)
    assert hass.states.get("light.kobra_s1_chamber_light").state == "on"
    assert hass.states.get("light.kobra_s1_top_led").state == "off"
