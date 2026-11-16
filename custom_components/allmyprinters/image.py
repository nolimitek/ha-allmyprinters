"""Model picture of the running print (the preview in the G-code or on the printer), through the agent."""

from __future__ import annotations

from homeassistant.components.image import ImageEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .api import AllMyPrintersAuthError
from .coordinator import AllMyPrintersConfigEntry, AllMyPrintersCoordinator
from .entity import PrinterEntity, add_printer_entities


async def async_setup_entry(
    hass: HomeAssistant, entry: AllMyPrintersConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    """One model picture per printer."""
    coordinator = entry.runtime_data

    def factory(printer_id: str, printer: dict) -> dict:
        return {f"{printer_id}_model": PrinterModelImage(hass, coordinator, printer_id)}

    add_printer_entities(entry, coordinator, async_add_entities, factory)


class PrinterModelImage(PrinterEntity, ImageEntity):
    """Picture of the model that is printing; unavailable while nothing with a preview prints."""

    _attr_content_type = "image/png"

    def __init__(self, hass: HomeAssistant, coordinator: AllMyPrintersCoordinator, printer_id: str) -> None:
        PrinterEntity.__init__(self, coordinator, printer_id, "model")
        ImageEntity.__init__(self, hass)
        self._thumb: str | None = self.job.get("thumb")
        self._attr_image_last_updated = dt_util.utcnow() if self._thumb else None

    @property
    def available(self) -> bool:
        return super().available and bool(self.job.get("thumb"))

    @callback
    def _handle_coordinator_update(self) -> None:
        thumb = self.job.get("thumb")
        if thumb != self._thumb:
            self._thumb = thumb
            self._cached_image = None
            self._attr_image_last_updated = dt_util.utcnow() if thumb else None
        super()._handle_coordinator_update()

    async def async_image(self) -> bytes | None:
        if not self._thumb:
            return None
        try:
            got = await self.coordinator.api.image("thumb", self.printer_id)
        except AllMyPrintersAuthError:
            return None
        if not got:
            return None
        self._attr_content_type = got[1]
        return got[0]
