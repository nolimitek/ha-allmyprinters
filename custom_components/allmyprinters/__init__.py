"""AllMyPrinters — printers, filament slots, boxes and spool stock from the AllMyPrinters agent in your home network."""

from __future__ import annotations

from datetime import timedelta
import json
import logging
from pathlib import Path

from homeassistant.const import CONF_HOST, CONF_PORT, CONF_TOKEN, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv, device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType

from .api import AllMyPrintersApi
from .const import CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL, DOMAIN
from .coordinator import AllMyPrintersConfigEntry, AllMyPrintersCoordinator
from .entity import agent_device, agent_identifier, printer_identifier

_LOGGER = logging.getLogger(__name__)
PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR, Platform.BUTTON, Platform.CAMERA, Platform.EVENT, Platform.FAN, Platform.IMAGE, Platform.LIGHT,
    Platform.NUMBER, Platform.SENSOR, Platform.SWITCH,
]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)
CARD_URL = "/allmyprinters/allmyprinters-card.js"
CARD_FILE = Path(__file__).parent / "frontend" / "allmyprinters-card.js"


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Serve the dashboard cards (frontend/allmyprinters-card.js) and load them in every dashboard."""
    if "frontend" not in hass.config.components or getattr(hass, "http", None) is None:
        return True   # e.g. tests without a frontend
    from homeassistant.components.frontend import add_extra_js_url  # noqa: PLC0415
    from homeassistant.components.http import StaticPathConfig  # noqa: PLC0415

    manifest = json.loads(await hass.async_add_executor_job((Path(__file__).parent / "manifest.json").read_text))
    await hass.http.async_register_static_paths([StaticPathConfig(CARD_URL, str(CARD_FILE), False)])
    # The version in the URL makes browsers load the new card after an update
    url = f"{CARD_URL}?v={manifest.get('version', '0')}"
    add_extra_js_url(hass, url)
    # The extra module alone is not enough: a page loaded while Home Assistant was starting (typically the
    # companion app reconnecting after a restart) never gets it. Dashboard resources load with every dashboard.
    try:
        await _async_register_resource(hass, url)
    except Exception:  # noqa: BLE001 — the cards must never block the integration
        _LOGGER.warning("Could not register the AllMyPrinters cards as a dashboard resource", exc_info=True)
    _LOGGER.debug("AllMyPrinters cards registered at %s", CARD_URL)
    return True


async def _async_register_resource(hass: HomeAssistant, url: str) -> None:
    """Add (or update to the current version) the card module in the storage-mode dashboard resources."""
    from homeassistant.components.lovelace.const import LOVELACE_DATA  # noqa: PLC0415

    data = hass.data.get(LOVELACE_DATA)
    if data is None or data.resource_mode != "storage":
        return   # YAML resources are the user's to maintain; the extra module still covers normal page loads
    resources = data.resources
    await resources.async_get_info()   # loads the collection from storage
    ours = [r for r in resources.async_items() if str(r.get("url", "")).split("?")[0] == CARD_URL]
    if not ours:
        await resources.async_create_item({"res_type": "module", "url": url})
        return
    if ours[0].get("url") != url:
        await resources.async_update_item(ours[0]["id"], {"res_type": "module", "url": url})
    for extra in ours[1:]:
        await resources.async_delete_item(extra["id"])


async def async_setup_entry(hass: HomeAssistant, entry: AllMyPrintersConfigEntry) -> bool:
    """Set up one AllMyPrinters agent from a config entry."""
    api = AllMyPrintersApi(async_get_clientsession(hass), entry.data[CONF_HOST], entry.data[CONF_PORT], entry.data[CONF_TOKEN])
    coordinator = AllMyPrintersCoordinator(hass, entry, api)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    # Register the agent device first: printers link to it by device id (via_device_id, HA 2026.9+)
    coordinator.agent_device_id = dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id, **agent_device(coordinator)
    ).id
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: AllMyPrintersConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_config_entry_device(
    hass: HomeAssistant, entry: AllMyPrintersConfigEntry, device: dr.DeviceEntry
) -> bool:
    """Let the user delete a printer the agent no longer reports; the agent device and current printers stay."""
    coordinator = entry.runtime_data
    current = {agent_identifier(coordinator)}
    current.update(printer_identifier(coordinator, printer_id) for printer_id in (coordinator.data or {}).get("printers") or {})
    return not device.identifiers & current


async def _async_options_updated(hass: HomeAssistant, entry: AllMyPrintersConfigEntry) -> None:
    """Apply a new polling interval (no reload; new address or key from discovery/reauth reload the entry themselves)."""
    coordinator = entry.runtime_data
    interval = timedelta(seconds=entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL))
    if coordinator.update_interval != interval:
        coordinator.update_interval = interval
        await coordinator.async_request_refresh()   # also schedules the next poll with the new interval
