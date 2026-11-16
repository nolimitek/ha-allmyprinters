"""Drying switch per filament box: on = start drying with the box's temperature/duration settings, off = stop."""

from __future__ import annotations

import time
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN, DRY_HOURS_DEFAULT, DRY_TEMP_DEFAULT
from .coordinator import AllMyPrintersConfigEntry, AllMyPrintersCoordinator, optimistic
from .entity import BoxEntity, add_printer_entities

OPTIMISTIC_SECONDS = 120   # the printer applies the command after a few seconds; show the new state meanwhile


async def async_setup_entry(
    hass: HomeAssistant, entry: AllMyPrintersConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    """Set up drying switches for boxes the agent can dry (box.control)."""
    coordinator = entry.runtime_data

    def factory(printer_id: str, printer: dict[str, Any]) -> dict[str, SwitchEntity]:
        return {f"{printer_id}_box{box['id']}_drying": DryingSwitch(coordinator, printer_id, box)
                for box in printer.get("boxes") or [] if box.get("control")}

    add_printer_entities(entry, coordinator, async_add_entities, factory)


class DryingSwitch(BoxEntity, SwitchEntity):
    """Drying of one box."""

    def __init__(self, coordinator: AllMyPrintersCoordinator, printer_id: str, box: dict[str, Any]) -> None:
        super().__init__(coordinator, printer_id, box, "drying")
        self._pending: tuple[bool, float] | None = None

    @property
    def available(self) -> bool:
        # An offline printer cannot take the command — show the switch greyed out like pause/resume/cancel
        return super().available and bool(self.printer.get("online"))

    @property
    def is_on(self) -> bool:
        value, self._pending = optimistic(bool(self.box.get("drying")), self._pending, time.monotonic())
        return value

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        box = self.box
        return {**self.box_attributes, "target_temperature": box.get("dry_target"),
                "remaining_minutes": box.get("dry_remain_min"), "duration_minutes": box.get("dry_duration_min")}

    def _setting(self, key: str, default: float) -> float:
        """Current value of this box's number entity (temperature / duration)."""
        reg = er.async_get(self.hass)
        uid = self.unique_id.removesuffix("drying") + key
        entity_id = reg.async_get_entity_id("number", DOMAIN, uid)
        state = self.hass.states.get(entity_id) if entity_id else None
        try:
            return float(state.state) if state else default
        except ValueError:
            return default

    async def _send(self, cmd: str, wanted: bool, **params: Any) -> None:
        await self.coordinator.async_command(self.printer_id, cmd, box=self.box_id, **params)
        self._pending = (wanted, time.monotonic() + OPTIMISTIC_SECONDS)
        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs: Any) -> None:
        temp = round(self._setting("dry_temperature", DRY_TEMP_DEFAULT))
        hours = self._setting("dry_duration", DRY_HOURS_DEFAULT)
        await self._send("dry_start", True, temp=temp, minutes=round(hours * 60))

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._send("dry_stop", False)
