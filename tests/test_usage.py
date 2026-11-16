"""Counters, filament printed, costs of the month and spools to dry."""

from __future__ import annotations

from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from .conftest import AGENT_ID, DOMAIN, ENTRY_DATA, URL


async def _setup(hass: HomeAssistant, aioclient_mock, payload) -> MockConfigEntry:
    entry = MockConfigEntry(domain=DOMAIN, unique_id=AGENT_ID, data=ENTRY_DATA)
    entry.add_to_hass(hass)
    aioclient_mock.get(URL, json=payload)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_counters_only_where_reported(hass: HomeAssistant, aioclient_mock, payload2) -> None:
    await _setup(hass, aioclient_mock, payload2)
    prints = hass.states.get("sensor.kobra_s1_total_prints")
    assert prints.state == "108" and prints.attributes["state_class"] == "total_increasing"
    hours = hass.states.get("sensor.kobra_s1_total_print_time")
    assert float(hours.state) == 400 and hours.attributes["unit_of_measurement"] == "h"
    # The Bambu printer reports no counters → no empty sensors for it; nobody reports maintenance or filament metres
    assert hass.states.get("sensor.x1c_total_prints") is None
    assert hass.states.get("sensor.kobra_s1_total_filament") is None
    assert hass.states.get("sensor.kobra_s1_next_maintenance") is None


async def test_usage_and_costs(hass: HomeAssistant, aioclient_mock, payload) -> None:
    payload["usage"] = {"filament_g": 12623, "prints": 140,
                        "month": {"start": "2026-11-01T00:00:00Z", "prints": 20, "grams": 908, "material": 13.13, "run": 2.4,
                                  "cost": 15.53, "currency": "EUR"}}
    payload["spools"]["dry_due"] = [{"id": 2, "name": "Sunlu PETG", "brand": "Sunlu", "material": "PETG", "days": 21, "limit": 14}]
    payload["spools"]["items"][0]["dry"] = {"days": 21, "limit": 14, "due": True}
    await _setup(hass, aioclient_mock, payload)
    printed = hass.states.get("sensor.allmyprinters_agent_filament_printed")
    assert float(printed.state) == 12.623 and printed.attributes["unit_of_measurement"] == "kg"   # suggested unit
    assert printed.attributes["state_class"] == "total" and printed.attributes["prints"] == 140
    cost = hass.states.get("sensor.allmyprinters_agent_print_costs_this_month")
    assert float(cost.state) == 15.53 and cost.attributes["unit_of_measurement"] == "EUR"
    assert cost.attributes["state_class"] == "total" and cost.attributes["device_class"] == "monetary"
    assert cost.attributes["filament"] == 13.13 and cost.attributes["operating"] == 2.4

    dry = hass.states.get("sensor.allmyprinters_agent_spools_to_dry")
    assert dry.state == "1" and dry.attributes["spools"][0] == {"name": "Sunlu PETG", "brand": "Sunlu", "material": "PETG",
                                                                "days": 21, "limit_days": 14}
    spool = hass.states.get("sensor.allmyprinters_agent_sunlu_petg")
    assert spool.attributes["dry_due"] is True and spool.attributes["days_open"] == 21


async def test_fixture_values(hass: HomeAssistant, aioclient_mock, payload) -> None:
    """The real agent answer: nothing printed this month yet."""
    await _setup(hass, aioclient_mock, payload)
    assert hass.states.get("sensor.allmyprinters_agent_filament_printed").state == "0.0"
    assert float(hass.states.get("sensor.allmyprinters_agent_print_costs_this_month").state) == 0
    assert hass.states.get("sensor.allmyprinters_agent_spools_to_dry").state == "0"


async def test_old_agent_without_new_fields(hass: HomeAssistant, aioclient_mock, payload) -> None:
    """An agent without usage/dry/ctl data must not break anything — the sensors just stay unknown."""
    payload.pop("usage")
    payload["spools"].pop("dry_due")
    for p in payload["printers"]:
        p.pop("counters", None)
        p.pop("ctl", None)
    await _setup(hass, aioclient_mock, payload)
    assert hass.states.get("sensor.allmyprinters_agent_filament_printed").state == STATE_UNKNOWN
    assert hass.states.get("sensor.allmyprinters_agent_print_costs_this_month").state == STATE_UNKNOWN
    assert hass.states.get("sensor.allmyprinters_agent_spools_to_dry").state == STATE_UNKNOWN
    assert hass.states.get("sensor.kobra_s1_total_prints") is None
    assert hass.states.get("light.kobra_s1_light") is None
    assert hass.states.get("sensor.kobra_s1_status").state != STATE_UNAVAILABLE
