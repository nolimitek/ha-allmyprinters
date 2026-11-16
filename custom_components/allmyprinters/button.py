"""Buttons: pause, resume and cancel the running print (the agent can do this for every printer kind)."""

from __future__ import annotations

from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import AllMyPrintersConfigEntry, AllMyPrintersCoordinator
from .entity import PrinterEntity, add_printer_entities

# key → (agent command, printer states in which the button makes sense)
BUTTONS: dict[str, tuple[str, tuple[str, ...]]] = {
    "pause": ("pause", ("printing",)),
    "resume": ("resume", ("paused",)),
    "cancel": ("stop", ("printing", "paused")),
}


async def async_setup_entry(
    hass: HomeAssistant, entry: AllMyPrintersConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    """Set up buttons for printers the agent can control."""
    coordinator = entry.runtime_data

    def factory(printer_id: str, printer: dict[str, Any]) -> dict[str, ButtonEntity]:
        if not printer.get("control"):
            return {}
        return {f"{printer_id}_{k}": PrinterButton(coordinator, printer_id, k) for k in BUTTONS}

    add_printer_entities(entry, coordinator, async_add_entities, factory)


class PrinterButton(PrinterEntity, ButtonEntity):
    """Only available while it makes sense: pause while printing, resume while paused."""

    def __init__(self, coordinator: AllMyPrintersCoordinator, printer_id: str, key: str) -> None:
        super().__init__(coordinator, printer_id, key)
        self.cmd, self.states = BUTTONS[key]

    @property
    def available(self) -> bool:
        return super().available and self.printer.get("state") in self.states

    async def async_press(self) -> None:
        await self.coordinator.async_command(self.printer_id, self.cmd)
