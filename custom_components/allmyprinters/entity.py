"""Base entities: one device for the agent (spool stock) and one per printer below it."""

from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, TITLE
from .coordinator import AllMyPrintersCoordinator

_VIA_DEVICE_ID = "via_device_id" in DeviceInfo.__annotations__


def agent_identifier(coordinator: AllMyPrintersCoordinator) -> tuple[str, str]:
    return (DOMAIN, f"agent_{coordinator.account_id}")


def printer_identifier(coordinator: AllMyPrintersCoordinator, printer_id: str) -> tuple[str, str]:
    """Printer ids (p1, p2 …) are only unique within one agent, so the agent id is part of the identifier."""
    return (DOMAIN, f"{coordinator.account_id}_{printer_id}")


def agent_device(coordinator: AllMyPrintersCoordinator) -> DeviceInfo:
    """The agent as a service device; printers hang below it."""
    agent = (coordinator.data or {}).get("agent") or {}
    return DeviceInfo(
        identifiers={agent_identifier(coordinator)},
        name=TITLE,
        manufacturer="AllMyPrinters",
        model="Home Assistant App" if agent.get("app") else "Agent",
        sw_version=agent.get("version"),
        entry_type=DeviceEntryType.SERVICE,
        configuration_url=coordinator.configuration_url,
    )


class AgentEntity(CoordinatorEntity[AllMyPrintersCoordinator]):
    """Entity on the agent device."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: AllMyPrintersCoordinator, key: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.account_id}_{key}"
        self._attr_translation_key = key
        self._attr_device_info = agent_device(coordinator)


class PrinterEntity(CoordinatorEntity[AllMyPrintersCoordinator]):
    """Entity on a printer device."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: AllMyPrintersCoordinator, printer_id: str, key: str) -> None:
        super().__init__(coordinator)
        self.printer_id = printer_id
        p = coordinator.printer(printer_id) or {}
        self._attr_unique_id = f"{coordinator.account_id}_{printer_id}_{key}"
        self._attr_translation_key = key
        info = DeviceInfo(
            identifiers={printer_identifier(coordinator, printer_id)},
            name=p.get("name") or printer_id,
            manufacturer=p.get("brand"),
            model=p.get("model"),
            sw_version=p.get("fw"),
            configuration_url=coordinator.configuration_url,
        )
        # HA 2026.9 replaced via_device (identifier tuple) by via_device_id; older versions only know via_device
        if _VIA_DEVICE_ID and coordinator.agent_device_id:
            info["via_device_id"] = coordinator.agent_device_id
        else:
            info["via_device"] = agent_identifier(coordinator)
        self._attr_device_info = info

    @property
    def printer(self) -> dict[str, Any]:
        """Latest printer data (empty when the printer disappeared)."""
        return self.coordinator.printer(self.printer_id) or {}

    @property
    def available(self) -> bool:
        return super().available and self.coordinator.printer(self.printer_id) is not None

    @property
    def job(self) -> dict[str, Any]:
        """Running job or empty dict."""
        return self.printer.get("job") or {}


def add_spool_entities(entry, coordinator: AllMyPrintersCoordinator, async_add_entities, factory) -> None:
    """Create one entity per active spool now and for spools added later in the agent."""
    known: set[str] = set()

    def _add() -> None:
        new = [factory(spool_id) for spool_id in (coordinator.data or {}).get("spool_items", {}) if spool_id not in known]
        known.update((coordinator.data or {}).get("spool_items", {}))
        if new:
            async_add_entities(new)

    _add()
    entry.async_on_unload(coordinator.async_add_listener(_add))


def add_printer_entities(entry, coordinator: AllMyPrintersCoordinator, async_add_entities, factory) -> None:
    """Create entities for every printer now and for printers/slots/fans/lights that show up later.

    ``factory(printer_id, printer)`` returns ``{key: entity}``; a key is only ever added once.
    """
    known: set[str] = set()

    def _add() -> None:
        new = []
        for printer_id, printer in (coordinator.data or {}).get("printers", {}).items():
            for key, entity in factory(printer_id, printer).items():
                if key not in known:
                    known.add(key)
                    new.append(entity)
        if new:
            async_add_entities(new)

    _add()
    entry.async_on_unload(coordinator.async_add_listener(_add))


class BoxEntity(PrinterEntity):
    """Entity of one filament box (ACE, AMS, CFS) of a printer — on the printer device."""

    def __init__(self, coordinator: AllMyPrintersCoordinator, printer_id: str, box: dict[str, Any], key: str) -> None:
        super().__init__(coordinator, printer_id, f"box{box['id']}_{key}")
        self.box_id = box["id"]
        self._attr_translation_key = f"box_{key}"
        self._attr_translation_placeholders = {"box": str(box.get("label") or f"Box {box['id'] + 1}")}

    @property
    def box(self) -> dict[str, Any]:
        """Latest data of this box (empty when it disappeared)."""
        return next((b for b in self.printer.get("boxes") or [] if b.get("id") == self.box_id), {})

    @property
    def available(self) -> bool:
        return super().available and bool(self.box)

    @property
    def box_attributes(self) -> dict[str, Any]:
        """Lets the dashboard card group the entities of one box."""
        return {"box_id": self.box_id, "box": self._attr_translation_placeholders["box"]}


def pretty_name(raw: str | None) -> str:
    """Klipper object name → readable name: "air_filter_fan" → "Air filter fan"."""
    text = " ".join(str(raw or "").replace("_", " ").split())
    return text[:1].upper() + text[1:] if text else ""


class ControlEntity(PrinterEntity):
    """A fan or light of a printer (printer.ctl.fans / printer.ctl.lights).

    Named by its kind (part, filter …) where the agent knows it, otherwise by the printer's own name for it.
    The agent drops ctl while the printer is offline, then the entity is unavailable.
    """

    _list: str   # "fans" | "lights"
    _kinds: tuple[str, ...]
    _prefix: str   # translation key prefix "fan" | "light"

    def __init__(self, coordinator: AllMyPrintersCoordinator, printer_id: str, item: dict[str, Any], unique_kind: bool) -> None:
        self.item_id = str(item["id"])
        super().__init__(coordinator, printer_id, f"{self._prefix}_{self.item_id}")
        kind = item.get("k")
        if kind in self._kinds and unique_kind:
            self._attr_translation_key = f"{self._prefix}_{kind}"
        else:
            # Unknown kind, or two of the same kind on one printer: use the printer's name for it
            self._attr_translation_key = f"{self._prefix}_other"
            self._attr_translation_placeholders = {"name": pretty_name(item.get("name")) or pretty_name(self.item_id)}

    @property
    def item(self) -> dict[str, Any]:
        """Latest data of this fan/light (empty when the printer is offline or it disappeared)."""
        ctl = self.printer.get("ctl") or {}
        return next((x for x in ctl.get(self._list) or [] if str(x.get("id")) == self.item_id), {})

    @property
    def available(self) -> bool:
        return super().available and bool(self.item)


def add_control_entities(entry, coordinator: AllMyPrintersCoordinator, async_add_entities, cls: type[ControlEntity]) -> None:
    """One entity per fan/light a printer reports; appear when the printer first reports them."""

    def factory(printer_id: str, printer: dict[str, Any]) -> dict[str, ControlEntity]:
        items = [x for x in ((printer.get("ctl") or {}).get(cls._list) or []) if isinstance(x, dict) and x.get("id") is not None]
        kinds = [x.get("k") for x in items]
        return {
            f"{printer_id}_{cls._prefix}_{x['id']}": cls(coordinator, printer_id, x, kinds.count(x.get("k")) == 1)
            for x in items
        }

    add_printer_entities(entry, coordinator, async_add_entities, factory)
