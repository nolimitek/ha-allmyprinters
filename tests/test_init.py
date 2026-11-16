"""Setup, entities, print events, buttons, wrong keys, printers added later and deleting gone printers."""

from __future__ import annotations

import copy

import pytest

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr
from pytest_homeassistant_custom_component.common import MockConfigEntry

from .conftest import AGENT_ID, DOMAIN, ENTRY_DATA, URL


async def _setup(hass: HomeAssistant, aioclient_mock, payload) -> MockConfigEntry:
    entry = MockConfigEntry(domain=DOMAIN, unique_id=AGENT_ID, data=ENTRY_DATA, title="AllMyPrinters Agent")
    entry.add_to_hass(hass)
    aioclient_mock.get(URL, json=payload)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def _refresh(hass: HomeAssistant, entry, aioclient_mock, payload=None, status=200) -> None:
    aioclient_mock.clear_requests()
    aioclient_mock.get(URL, json=payload if payload is not None else {"error": "auth"}, status=status)
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()


def _device(hass: HomeAssistant, entry, ident: str):
    reg = dr.async_get(hass)
    get = getattr(reg, "async_get_device_by_identifier", None)   # HA 2026.10+, async_get_device is deprecated there
    return get((DOMAIN, ident), entry.entry_id) if get else reg.async_get_device(identifiers={(DOMAIN, ident)})


async def test_entities(hass: HomeAssistant, aioclient_mock, payload2) -> None:
    entry = await _setup(hass, aioclient_mock, payload2)
    assert entry.state is ConfigEntryState.LOADED

    status = hass.states.get("sensor.kobra_s1_status")
    assert status.state == "printing"
    assert status.attributes["provider"] == "moonraker" and status.attributes["last_update"] == "2026-11-16T08:28:43Z"
    assert "image" not in status.attributes
    assert hass.states.get("sensor.kobra_s1_progress").state == "60"
    assert hass.states.get("sensor.kobra_s1_remaining_time").state == "12"
    assert hass.states.get("sensor.kobra_s1_estimated_end").state == "2026-11-16T08:40:47+00:00"
    assert hass.states.get("sensor.kobra_s1_job").state == "benchy"
    layer = hass.states.get("sensor.kobra_s1_current_layer")
    assert layer.state == "72" and layer.attributes["total_layers"] == 120
    assert hass.states.get("sensor.kobra_s1_nozzle_temperature").state == "220"
    assert hass.states.get("sensor.kobra_s1_bed_temperature").state == "60"
    assert hass.states.get("sensor.kobra_s1_total_prints").state == "108"
    assert float(hass.states.get("sensor.kobra_s1_total_print_time").state) == 400

    slot1 = hass.states.get("sensor.kobra_s1_slot_1")
    assert slot1.state == "1000"
    assert slot1.attributes["material"] == "PLA" and slot1.attributes["spool_name"] == "Elegoo PLA"
    assert slot1.attributes["in_use"] is True
    assert slot1.attributes["entity_picture"].startswith("data:image/svg+xml;base64,")
    assert hass.states.get("sensor.kobra_s1_slot_2").state == STATE_UNKNOWN   # no spool assigned
    assert hass.states.get("sensor.kobra_s1_slot_4") is not None

    assert hass.states.get("binary_sensor.kobra_s1_online").state == "on"
    assert hass.states.get("binary_sensor.kobra_s1_printing").state == "on"
    assert hass.states.get("binary_sensor.kobra_s1_problem").state == "off"

    assert hass.states.get("button.kobra_s1_pause_print").state != STATE_UNAVAILABLE
    assert hass.states.get("button.kobra_s1_resume_print").state == STATE_UNAVAILABLE   # not paused
    assert hass.states.get("button.kobra_s1_cancel_print").state != STATE_UNAVAILABLE

    # Lights and fans from ctl
    light = hass.states.get("light.kobra_s1_light")
    assert light.state == "on" and light.attributes["supported_color_modes"] == ["onoff"]
    part = hass.states.get("fan.kobra_s1_part_fan")
    assert part.state == "off" and part.attributes["percentage"] == 0
    filt = hass.states.get("fan.kobra_s1_air_filter")
    assert filt.state == "on" and filt.attributes["percentage"] == 60
    assert hass.states.get("fan.kobra_s1_enclosure_fan").state == "off"

    # Second printer: offline, no ctl → no lights/fans, but buttons exist (the agent controls every printer)
    assert hass.states.get("sensor.x1c_status").state == "offline"
    assert hass.states.get("binary_sensor.x1c_online").state == "off"
    assert hass.states.get("button.x1c_pause_print").state == STATE_UNAVAILABLE
    assert not [s for s in hass.states.async_all(["light", "fan"]) if s.entity_id.startswith(("light.x1c", "fan.x1c"))]

    # Agent device
    assert hass.states.get("sensor.allmyprinters_agent_spools_in_stock").state == "2"
    stock = hass.states.get("sensor.allmyprinters_agent_filament_in_stock")
    assert float(stock.state) == 2.0 and stock.attributes["unit_of_measurement"] == "kg"
    assert hass.states.get("sensor.allmyprinters_agent_spools_almost_empty").state == "0"

    agent = _device(hass, entry, f"agent_{AGENT_ID}")
    assert agent.name == "AllMyPrinters Agent" and agent.sw_version == "0.5.7" and agent.model == "Agent"
    assert agent.configuration_url == "http://192.168.1.50:8090/"
    printer = _device(hass, entry, f"{AGENT_ID}_p1")
    assert printer.manufacturer == "Anycubic" and printer.model == "Anycubic Kobra S1" and printer.sw_version == "v0.12.0"

    assert await hass.config_entries.async_unload(entry.entry_id)
    assert entry.state is ConfigEntryState.NOT_LOADED


async def test_print_events(hass: HomeAssistant, aioclient_mock, payload) -> None:
    entry = await _setup(hass, aioclient_mock, payload)
    ev = "event.kobra_s1_print"
    assert hass.states.get(ev).state == STATE_UNKNOWN   # the job known at start-up fires nothing

    payload["printers"][0]["last_job"].update(status="finished", how="completed", end="2026-11-16T08:41:00Z", grams=11.3)
    payload["printers"][0].update(state="idle", job=None)
    await _refresh(hass, entry, aioclient_mock, payload)
    st = hass.states.get(ev)
    assert st.attributes["event_type"] == "finished"
    assert st.attributes["job_name"] == "benchy" and st.attributes["filament_g"] == 11.3
    assert st.attributes["reason"] == "completed"
    assert hass.states.get("sensor.kobra_s1_progress").state == STATE_UNKNOWN
    assert hass.states.get("button.kobra_s1_pause_print").state == STATE_UNAVAILABLE

    # Same data again: no second event
    first = st.state
    await _refresh(hass, entry, aioclient_mock, payload)
    assert hass.states.get(ev).state == first

    # Next job starts …
    payload["printers"][0]["last_job"] = {"id": 3, "title": "Cube", "status": "printing", "how": None,
                                          "start": "2026-11-16T09:00:00Z", "end": None, "grams": None}
    await _refresh(hass, entry, aioclient_mock, payload)
    assert hass.states.get(ev).attributes["event_type"] == "started"
    # … and is cancelled
    payload["printers"][0]["last_job"].update(status="failed", how="cancelled", end="2026-11-16T09:03:00Z")
    await _refresh(hass, entry, aioclient_mock, payload)
    assert hass.states.get(ev).attributes["event_type"] == "cancelled"
    # A job that fails with a printer error
    payload["printers"][0]["last_job"] = {"id": 4, "title": "Vase", "status": "printing", "how": None, "start": "x", "end": None, "grams": None}
    await _refresh(hass, entry, aioclient_mock, payload)
    payload["printers"][0]["last_job"].update(status="failed", how="klippy_shutdown", end="y")
    await _refresh(hass, entry, aioclient_mock, payload)
    assert hass.states.get(ev).attributes["event_type"] == "failed"
    # A short job that started and ended between two polls only reports its end
    payload["printers"][0]["last_job"] = {"id": 5, "title": "Clip", "status": "finished", "how": "completed", "start": "x", "end": "y", "grams": 1.0}
    await _refresh(hass, entry, aioclient_mock, payload)
    assert hass.states.get(ev).attributes["event_type"] == "finished"


async def test_pause_button(hass: HomeAssistant, aioclient_mock, payload) -> None:
    await _setup(hass, aioclient_mock, payload)
    aioclient_mock.post(URL, json={"ok": True})
    await hass.services.async_call("button", "press", {"entity_id": "button.kobra_s1_pause_print"}, blocking=True)
    post = [c for c in aioclient_mock.mock_calls if c[0] == "POST"]
    assert post[0][2] == {"printer": "p1", "cmd": "pause"}

    aioclient_mock.clear_requests()
    aioclient_mock.get(URL, json=payload)
    aioclient_mock.post(URL, status=404, json={"error": "not_found"})
    with pytest.raises(HomeAssistantError) as err:
        await hass.services.async_call("button", "press", {"entity_id": "button.kobra_s1_cancel_print"}, blocking=True)
    assert err.value.translation_key == "command_failed"
    assert err.value.translation_placeholders == {"error": "not_found"}


async def test_wrong_key_starts_reauth(hass: HomeAssistant, aioclient_mock, payload) -> None:
    entry = await _setup(hass, aioclient_mock, payload)
    await _refresh(hass, entry, aioclient_mock, None, status=401)
    flows = hass.config_entries.flow.async_progress_by_handler(DOMAIN)
    assert flows and flows[0]["context"]["source"] == "reauth"


async def test_agent_down_marks_unavailable(hass: HomeAssistant, aioclient_mock, payload) -> None:
    entry = await _setup(hass, aioclient_mock, payload)
    aioclient_mock.clear_requests()
    aioclient_mock.get(URL, exc=TimeoutError())
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()
    assert hass.states.get("sensor.kobra_s1_status").state == STATE_UNAVAILABLE
    assert hass.states.get("light.kobra_s1_light").state == STATE_UNAVAILABLE
    await _refresh(hass, entry, aioclient_mock, payload)
    assert hass.states.get("sensor.kobra_s1_status").state == "printing"


async def test_new_printer_slot_and_controls(hass: HomeAssistant, aioclient_mock, payload) -> None:
    """Printers, slots, lights and fans that show up later get entities; a printer going offline greys them out."""
    p1 = payload["printers"][0]
    ctl = p1.pop("ctl")
    p1.update(online=False, state="offline", ctl=None)
    entry = await _setup(hass, aioclient_mock, payload)
    assert hass.states.get("light.kobra_s1_light") is None

    p1.update(online=True, state="printing", ctl=ctl)
    p1["slots"].append({"index": 4, "label": "5", "material": "TPU", "color": None, "spool": None, "remain_pct": None, "in_use": False})
    payload["printers"].append(copy.deepcopy({**p1, "id": "p3", "name": "Voron", "provider": "moonraker", "brand": "Voron",
                                              "ctl": {"fans": [], "lights": [{"id": "led", "k": None, "name": "case_leds", "on": False}]}}))
    await _refresh(hass, entry, aioclient_mock, payload)
    assert hass.states.get("sensor.kobra_s1_slot_5") is not None
    assert hass.states.get("light.kobra_s1_light").state == "on"
    assert hass.states.get("fan.kobra_s1_air_filter").state == "on"
    assert hass.states.get("sensor.voron_status").state == "printing"
    assert hass.states.get("light.voron_case_leds").state == "off"   # unknown kind: the printer's own name

    # Offline again: the agent drops ctl → lights/fans unavailable; printer removed in the agent → unavailable
    p1.update(online=False, state="offline", ctl=None)
    payload["printers"] = payload["printers"][:1]
    await _refresh(hass, entry, aioclient_mock, payload)
    assert hass.states.get("light.kobra_s1_light").state == STATE_UNAVAILABLE
    assert hass.states.get("fan.kobra_s1_part_fan").state == STATE_UNAVAILABLE
    assert hass.states.get("sensor.voron_status").state == STATE_UNAVAILABLE


async def test_printer_hangs_below_agent(hass: HomeAssistant, aioclient_mock, payload, caplog) -> None:
    entry = await _setup(hass, aioclient_mock, payload)
    agent = _device(hass, entry, f"agent_{AGENT_ID}")
    printer = _device(hass, entry, f"{AGENT_ID}_p1")
    assert agent and printer and printer.via_device_id == agent.id
    assert "deprecated `via_device`" not in caplog.text


async def test_spool_sensors(hass: HomeAssistant, aioclient_mock, payload) -> None:
    entry = await _setup(hass, aioclient_mock, payload)
    pla = hass.states.get("sensor.allmyprinters_agent_elegoo_pla")
    assert pla.state == "1000" and pla.attributes["unit_of_measurement"] == "g"
    assert pla.attributes["printer"] == "Kobra S1" and pla.attributes["slot"] == "1" and pla.attributes["level"] == "ok"
    import base64

    svg = base64.b64decode(pla.attributes["entity_picture"].split(",", 1)[1]).decode()
    assert "#3366ff" in svg and "<script" not in svg
    petg = hass.states.get("sensor.allmyprinters_agent_sunlu_petg")
    assert petg.state == "1000" and petg.attributes["printer"] is None

    # Spool runs low → listed; new spool → new entity; archived spool → unavailable
    low = {**payload["spools"]["items"][0], "left": 80, "pct": 8, "lvl": 2}
    payload["spools"]["items"][0] = low
    payload["spools"]["low"] = [low]
    payload["spools"]["items"].append({"id": 50, "name": "PETG Green", "brand": "Elegoo", "material": "PETG", "color": "#1baf7a",
                                       "left": 900, "total": 1000, "pct": 90, "value": None, "location": "Shelf", "lvl": 0,
                                       "dry": None, "loaded": None})
    payload["spools"]["items"] = [x for x in payload["spools"]["items"] if x["id"] != 1]
    await _refresh(hass, entry, aioclient_mock, payload)
    assert hass.states.get("sensor.allmyprinters_agent_sunlu_petg").attributes["level"] == "critical"
    almost = hass.states.get("sensor.allmyprinters_agent_spools_almost_empty")
    assert almost.state == "1" and almost.attributes["spools"][0]["level"] == "critical"
    assert hass.states.get("sensor.allmyprinters_agent_petg_green").state == "900"
    assert hass.states.get("sensor.allmyprinters_agent_elegoo_pla").state == STATE_UNAVAILABLE


async def test_drying(hass: HomeAssistant, aioclient_mock, payload2) -> None:
    entry = await _setup(hass, aioclient_mock, payload2)
    sw = "switch.kobra_s1_ace_1_drying"
    assert hass.states.get(sw).state == "off"
    assert hass.states.get("number.kobra_s1_ace_1_drying_temperature").state == "45"
    assert hass.states.get("number.kobra_s1_ace_1_drying_duration").state == "4"
    assert hass.states.get("sensor.kobra_s1_ace_1_temperature").state == "26"
    assert hass.states.get("sensor.kobra_s1_ace_1_humidity").state == "38"
    # Bambu AMS: climate + drying state, but read-only (no switch, no settings)
    rem = hass.states.get("sensor.x1c_ams_1_drying_time_remaining")
    assert rem.state == "128" and rem.attributes["target_temperature"] == 65 and rem.attributes["controllable"] is False
    assert hass.states.get("switch.x1c_ams_1_drying") is None

    await hass.services.async_call("number", "set_value", {"entity_id": "number.kobra_s1_ace_1_drying_temperature", "value": 55}, blocking=True)
    await hass.services.async_call("number", "set_value", {"entity_id": "number.kobra_s1_ace_1_drying_duration", "value": 6}, blocking=True)
    aioclient_mock.post(URL, json={"ok": True})
    await hass.services.async_call("switch", "turn_on", {"entity_id": sw}, blocking=True)
    post = [c for c in aioclient_mock.mock_calls if c[0] == "POST"]
    assert post[-1][2] == {"printer": "p1", "cmd": "dry_start", "box": 0, "temp": 55, "minutes": 360}
    assert hass.states.get(sw).state == "on"

    payload2["printers"][0]["boxes"][0].update(drying=True, dry_target=55, dry_remain_min=359, dry_duration_min=360)
    await _refresh(hass, entry, aioclient_mock, payload2)
    assert hass.states.get(sw).attributes["remaining_minutes"] == 359
    aioclient_mock.post(URL, json={"ok": True})
    await hass.services.async_call("switch", "turn_off", {"entity_id": sw}, blocking=True)
    post = [c for c in aioclient_mock.mock_calls if c[0] == "POST"]
    assert post[-1][2] == {"printer": "p1", "cmd": "dry_stop", "box": 0}


async def test_setup_fails_with_bad_key(hass: HomeAssistant, aioclient_mock) -> None:
    entry = MockConfigEntry(domain=DOMAIN, unique_id=AGENT_ID, data=ENTRY_DATA)
    entry.add_to_hass(hass)
    aioclient_mock.get(URL, status=401, json={"error": "auth"})
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.SETUP_ERROR


async def test_card_resource_registered_once_and_updated(hass) -> None:
    """The card module lands in the dashboard resources, follows the version and is never duplicated."""
    from homeassistant.components.lovelace.const import LOVELACE_DATA
    from homeassistant.setup import async_setup_component

    import custom_components.allmyprinters as mod

    assert await async_setup_component(hass, "lovelace", {})
    res = hass.data[LOVELACE_DATA].resources

    await mod._async_register_resource(hass, mod.CARD_URL + "?v=0.1.0")
    await mod._async_register_resource(hass, mod.CARD_URL + "?v=0.1.0")
    items = [r for r in res.async_items() if r["url"].startswith(mod.CARD_URL)]
    assert [(r["type"], r["url"]) for r in items] == [("module", mod.CARD_URL + "?v=0.1.0")]

    await mod._async_register_resource(hass, mod.CARD_URL + "?v=0.1.1")
    items = [r for r in res.async_items() if r["url"].startswith(mod.CARD_URL)]
    assert [r["url"] for r in items] == [mod.CARD_URL + "?v=0.1.1"]


async def test_remove_gone_printer(hass: HomeAssistant, aioclient_mock, payload2, hass_ws_client) -> None:
    """The UI's "Delete" works for printers the agent no longer reports, never for current ones or the agent."""
    from homeassistant.setup import async_setup_component

    assert await async_setup_component(hass, "config", {})
    entry = await _setup(hass, aioclient_mock, payload2)
    client = await hass_ws_client(hass)

    from homeassistant.components.config import device_registry as dr_ws

    async def remove(dev) -> dict:
        # HA 2026.10 deprecated remove_config_entry in favour of remove; both end in async_remove_config_entry_device
        if hasattr(dr_ws, "websocket_remove_device"):
            await client.send_json_auto_id({"type": "config/device_registry/remove", "device_id": dev.id})
        else:
            await client.send_json_auto_id({"type": "config/device_registry/remove_config_entry",
                                            "config_entry_id": entry.entry_id, "device_id": dev.id})
        return await client.receive_json()

    assert not (await remove(_device(hass, entry, f"{AGENT_ID}_p1")))["success"]
    assert not (await remove(_device(hass, entry, f"agent_{AGENT_ID}")))["success"]

    payload2["printers"] = payload2["printers"][:1]   # the Bambu printer is gone in the agent
    await _refresh(hass, entry, aioclient_mock, payload2)
    assert (await remove(_device(hass, entry, f"{AGENT_ID}_p2")))["success"]
    assert _device(hass, entry, f"{AGENT_ID}_p2") is None
    assert _device(hass, entry, f"{AGENT_ID}_p1") is not None
