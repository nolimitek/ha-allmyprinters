"""Diagnostics download: the key, the agent's address and other personal details are removed."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_HOST, CONF_TOKEN
from homeassistant.core import HomeAssistant

from .coordinator import AllMyPrintersConfigEntry

# People attach this file to public GitHub issues. async_redact_data works by key at every level, so this also covers
# printers, spools, fans and lights; provider, model, firmware, state and slots stay, and those are what a bug report needs.
TO_REDACT = {
    CONF_TOKEN, CONF_HOST, "id", "name", "display_name", "email", "user", "user_id", "username",
    "image", "location", "printer", "title",
}


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: AllMyPrintersConfigEntry) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    data = dict(entry.runtime_data.data)
    # Printers and spools are stored by id, and async_redact_data only looks at values
    data["printers"] = list(data.get("printers", {}).values())
    data["spool_items"] = list(data.get("spool_items", {}).values())
    return {
        "entry": async_redact_data(dict(entry.data), TO_REDACT),
        "options": dict(entry.options),
        "data": async_redact_data(data, TO_REDACT),
    }
