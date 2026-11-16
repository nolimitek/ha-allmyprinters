"""Printer fans (part cooling, auxiliary, enclosure, chamber, air filter, exhaust) with speed in percent."""

from __future__ import annotations

import time
from typing import Any

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import FAN_KINDS
from .coordinator import AllMyPrintersConfigEntry, optimistic
from .entity import ControlEntity, add_control_entities

OPTIMISTIC_SECONDS = 20   # show the new speed until the agent confirms it


async def async_setup_entry(
    hass: HomeAssistant, entry: AllMyPrintersConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    """Set up one fan per ctl.fans entry."""
    add_control_entities(entry, entry.runtime_data, async_add_entities, PrinterFan)


class PrinterFan(ControlEntity, FanEntity):
    """A printer fan. Some fans can only be set while printing; the agent then answers print_only."""

    _list = "fans"
    _kinds = FAN_KINDS
    _prefix = "fan"
    _attr_supported_features = FanEntityFeature.SET_SPEED | FanEntityFeature.TURN_ON | FanEntityFeature.TURN_OFF
    _pending: tuple[int, float] | None = None
    _last_on: int | None = None

    @property
    def percentage(self) -> int | None:
        real = self.item.get("pct")
        real = None if real is None else round(real)
        value, self._pending = optimistic(real, self._pending, time.monotonic())
        if value:
            self._last_on = value
        return value

    async def async_set_percentage(self, percentage: int) -> None:
        pct = max(0, min(100, round(percentage)))
        await self.coordinator.async_command(self.printer_id, "fan", id=self.item_id, pct=pct)
        self._pending = (pct, time.monotonic() + OPTIMISTIC_SECONDS)
        self.async_write_ha_state()

    async def async_turn_on(self, percentage: int | None = None, preset_mode: str | None = None, **kwargs: Any) -> None:
        # Without a speed: back to the last speed it ran at, otherwise full speed
        await self.async_set_percentage(percentage if percentage is not None else self._last_on or 100)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.async_set_percentage(0)
