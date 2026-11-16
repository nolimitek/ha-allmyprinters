"""Event entity per printer: print started / finished / failed / cancelled — for automations."""

from __future__ import annotations

from typing import Any

from homeassistant.components.event import EventEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import EVENT_CANCELLED, EVENT_FAILED, EVENT_FINISHED, EVENT_STARTED
from .coordinator import AllMyPrintersConfigEntry, AllMyPrintersCoordinator
from .entity import PrinterEntity, add_printer_entities


async def async_setup_entry(
    hass: HomeAssistant, entry: AllMyPrintersConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    """Set up event entities."""
    coordinator = entry.runtime_data

    def factory(printer_id: str, printer: dict[str, Any]) -> dict[str, EventEntity]:
        return {f"{printer_id}_print": PrintEvent(coordinator, printer_id)}

    add_printer_entities(entry, coordinator, async_add_entities, factory)


def _event_type(job: dict[str, Any]) -> str | None:
    status = job.get("status")
    if status == "failed" and job.get("how") == "cancelled":
        return EVENT_CANCELLED   # stopped by someone, not a printer error
    return {"printing": EVENT_STARTED, "finished": EVENT_FINISHED, "failed": EVENT_FAILED}.get(status)


class PrintEvent(PrinterEntity, EventEntity):
    """Fires when the agent's last job of this printer starts or ends.

    Based on the agent's job history (not on state changes seen by Home Assistant), so a print that ended while
    Home Assistant was restarting is still reported once. Nothing fires for the job that was already known when
    the integration started.
    """

    _attr_event_types = [EVENT_STARTED, EVENT_FINISHED, EVENT_FAILED, EVENT_CANCELLED]

    def __init__(self, coordinator: AllMyPrintersCoordinator, printer_id: str) -> None:
        super().__init__(coordinator, printer_id, "print")
        self._seen = self._key(self.printer.get("last_job"))

    @staticmethod
    def _key(job: dict[str, Any] | None) -> tuple[Any, Any] | None:
        return (job.get("id"), job.get("status")) if job else None

    @callback
    def _handle_coordinator_update(self) -> None:
        job = self.printer.get("last_job")
        key = self._key(job)
        if job and key != self._seen:
            new_job = self._seen is None or key[0] != self._seen[0]
            event = _event_type(job)
            # A new job that is already over (short print between two polls) only reports its end
            if event and (event != EVENT_STARTED or new_job):
                self._trigger_event(event, {"job_name": job.get("title"), "start": job.get("start"),
                                            "end": job.get("end"), "filament_g": job.get("grams"),
                                            "reason": job.get("how")})
        self._seen = key
        super()._handle_coordinator_update()
