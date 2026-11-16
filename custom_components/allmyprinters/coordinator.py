"""Polls the AllMyPrinters agent and keeps the latest state for all entities."""

from __future__ import annotations

from datetime import datetime, timedelta
import ipaddress
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import CALLBACK_TYPE, HassJob, HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import AllMyPrintersApi, AllMyPrintersAuthError, AllMyPrintersError, agent_url
from .const import COMMAND_REFRESH_DELAY, CONF_SCAN_INTERVAL, CONF_SLUG, DEFAULT_PORT, DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)

type AllMyPrintersConfigEntry = ConfigEntry[AllMyPrintersCoordinator]


class AllMyPrintersCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """One request per interval returns every printer and the spool stock."""

    config_entry: AllMyPrintersConfigEntry

    def __init__(self, hass: HomeAssistant, entry: AllMyPrintersConfigEntry, api: AllMyPrintersApi) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)),
        )
        self.api = api
        self.agent_device_id: str | None = None
        self._unsub_command_refresh: CALLBACK_TYPE | None = None
        # cancel_on_shutdown: Home Assistant drops a pending refresh when it stops
        self._command_refresh_job = HassJob(self._async_command_refresh, f"{DOMAIN} refresh after command",
                                            cancel_on_shutdown=True)

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            data = await self.api.status()
        except AllMyPrintersAuthError as err:
            raise ConfigEntryAuthFailed(translation_domain=DOMAIN, translation_key="auth_failed") from err
        except AllMyPrintersError as err:
            raise UpdateFailed(translation_domain=DOMAIN, translation_key="update_failed",
                               translation_placeholders={"error": err.code}) from err
        printers = {str(p["id"]): p for p in data.get("printers", []) if isinstance(p, dict) and p.get("id")}
        spools = data.get("spools") or {}
        items = {str(s["id"]): s for s in spools.get("items") or [] if isinstance(s, dict) and s.get("id") is not None}
        return {
            "account": data.get("account") or {},
            "agent": data.get("agent") or {},
            "printers": printers,
            "spools": spools,
            "spool_items": items,
            "features": data.get("features") or {},
            "usage": data.get("usage") or {},
            "time": data.get("time"),
        }

    @property
    def account_id(self) -> str:
        """Id of the agent (also the config entry unique id)."""
        return str((self.data or {}).get("account", {}).get("id") or self.config_entry.unique_id)

    @property
    def configuration_url(self) -> str | None:
        """Where "Visit" on the device page leads: the App's sidebar page, or the agent's web interface."""
        if slug := self.config_entry.data.get(CONF_SLUG):
            return f"homeassistant://hassio/ingress/{slug}"
        host = self.config_entry.data.get(CONF_HOST, "")
        try:
            if ipaddress.ip_address(host).is_loopback:
                return None   # 127.0.0.1 is Home Assistant's own host, not the browser's
        except ValueError:
            pass
        if host == "localhost":
            return None
        return str(agent_url(host, self.config_entry.data.get(CONF_PORT, DEFAULT_PORT))) + "/"

    def printer(self, printer_id: str) -> dict[str, Any] | None:
        """Latest data of one printer, None if it is gone."""
        return (self.data or {}).get("printers", {}).get(printer_id)

    def spool(self, spool_id: str) -> dict[str, Any] | None:
        """Latest data of one active spool, None once it is archived or deleted in the agent."""
        return (self.data or {}).get("spool_items", {}).get(spool_id)

    async def async_command(self, printer_id: str, cmd: str, **params: Any) -> None:
        """Send a command; errors become a translated HomeAssistantError, success schedules a refresh."""
        try:
            await self.api.command(printer_id, cmd, **params)
        except AllMyPrintersError as err:
            if err.code == "print_only":
                raise HomeAssistantError(translation_domain=DOMAIN, translation_key="print_only") from err
            raise HomeAssistantError(translation_domain=DOMAIN, translation_key="command_failed",
                                     translation_placeholders={"error": err.code}) from err
        self.async_refresh_after_command()

    @callback
    def async_refresh_after_command(self) -> None:
        """Poll again shortly: the agent applies a command and updates its own state about 1.5 s later.

        An immediate refresh would only return the old state, and the regular one can be up to 2 minutes away.
        """
        if self._unsub_command_refresh:
            self._unsub_command_refresh()
        self._unsub_command_refresh = async_call_later(self.hass, COMMAND_REFRESH_DELAY, self._command_refresh_job)

    async def _async_command_refresh(self, _now: datetime) -> None:
        self._unsub_command_refresh = None
        await self.async_refresh()

    async def async_shutdown(self) -> None:
        """Cancel a pending refresh as well."""
        await super().async_shutdown()
        if self._unsub_command_refresh:
            self._unsub_command_refresh()
            self._unsub_command_refresh = None


def optimistic(real: Any, pending: tuple[Any, float] | None, now: float) -> tuple[Any, tuple[Any, float] | None]:
    """Show a value just sent until the agent reports it (or the wait runs out).

    Returns (value to show, pending to keep).
    """
    if pending is None:
        return real, None
    wanted, until = pending
    if real == wanted or now > until:
        return real, None
    return wanted, pending
