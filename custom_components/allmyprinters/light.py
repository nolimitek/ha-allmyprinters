"""Printer lights (chamber, toolhead, camera) the agent can switch."""

from __future__ import annotations

import time
from typing import Any

from homeassistant.components.light import ColorMode, LightEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import LIGHT_KINDS
from .coordinator import AllMyPrintersConfigEntry, optimistic
from .entity import ControlEntity, add_control_entities

OPTIMISTIC_SECONDS = 20   # show the new state until the agent confirms it


async def async_setup_entry(
    hass: HomeAssistant, entry: AllMyPrintersConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    """Set up one light per ctl.lights entry."""
    add_control_entities(entry, entry.runtime_data, async_add_entities, PrinterLight)


class PrinterLight(ControlEntity, LightEntity):
    """On/off light of a printer."""

    _list = "lights"
    _kinds = LIGHT_KINDS
    _prefix = "light"
    _attr_color_mode = ColorMode.ONOFF
    _attr_supported_color_modes = {ColorMode.ONOFF}
    _pending: tuple[bool, float] | None = None

    @property
    def is_on(self) -> bool | None:
        real = self.item.get("on")
        value, self._pending = optimistic(real, self._pending, time.monotonic())
        return value

    async def _switch(self, on: bool) -> None:
        await self.coordinator.async_command(self.printer_id, "light", id=self.item_id, on=on)
        self._pending = (on, time.monotonic() + OPTIMISTIC_SECONDS)
        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._switch(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._switch(False)
