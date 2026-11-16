"""Printer camera: pictures through the agent, so it works for every camera the agent can show.

The agent reads the printer's stream only while Home Assistant asks for pictures (dashboard open) and stops ~20 s after.
Without stream support Home Assistant's live view is built from these pictures (about two per second).
"""

from __future__ import annotations

from homeassistant.components.camera import Camera
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .api import AllMyPrintersAuthError
from .coordinator import AllMyPrintersConfigEntry, AllMyPrintersCoordinator
from .entity import PrinterEntity, add_printer_entities


async def async_setup_entry(
    hass: HomeAssistant, entry: AllMyPrintersConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    """One camera per printer that has one."""
    coordinator = entry.runtime_data

    def factory(printer_id: str, printer: dict) -> dict:
        return {f"{printer_id}_camera": PrinterCamera(coordinator, printer_id)} if printer.get("cam") else {}

    add_printer_entities(entry, coordinator, async_add_entities, factory)


class PrinterCamera(PrinterEntity, Camera):
    """Live picture of the printer."""

    _attr_content_type = "image/jpeg"

    def __init__(self, coordinator: AllMyPrintersCoordinator, printer_id: str) -> None:
        PrinterEntity.__init__(self, coordinator, printer_id, "camera")
        Camera.__init__(self)

    @property
    def available(self) -> bool:
        p = self.printer
        return super().available and bool(p.get("cam")) and bool(p.get("online"))

    async def async_camera_image(self, width: int | None = None, height: int | None = None) -> bytes | None:
        try:
            got = await self.coordinator.api.image("cam", self.printer_id)
        except AllMyPrintersAuthError:
            return None   # the coordinator's next poll starts the re-authentication
        return got[0] if got else None
