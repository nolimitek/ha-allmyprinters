"""Printer camera through the agent, so it works for every camera the agent can show.

Live view (since 0.3.0, before: still pictures, about two per second):
- cameras with H.264 (Anycubic, Bambu Lab X1/H2/P2S): the agent passes the original stream on unchanged (/ha/live, FLV);
  it is this entity's stream source, so Home Assistant shows it via WebRTC (go2rtc) or HLS — as smooth as in the agent.
- all others: an MJPEG stream at the camera's frame rate (/ha/mjpeg), proxied for the live view.
Still pictures (dashboard tiles) keep coming from /ha/cam. The agent reads the printer only while Home Assistant asks.
"""

from __future__ import annotations

from aiohttp import web

from homeassistant.components.camera import Camera, CameraEntityFeature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_aiohttp_proxy_stream
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .api import AllMyPrintersAuthError, AllMyPrintersError
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
        self._kind = self._stream_kind()

    def _stream_kind(self) -> str | None:
        """'video' (H.264 stream), 'mjpeg' or None (older agent or camera type not known yet)."""
        return (self.printer or {}).get("cam_stream")

    @property
    def available(self) -> bool:
        p = self.printer
        return super().available and bool(p.get("cam")) and bool(p.get("online"))

    @property
    def supported_features(self) -> CameraEntityFeature:
        return CameraEntityFeature.STREAM if self._stream_kind() == "video" else CameraEntityFeature(0)

    async def stream_source(self) -> str | None:
        return self.coordinator.api.live_url(self.printer_id) if self._stream_kind() == "video" else None

    @callback
    def _handle_coordinator_update(self) -> None:
        kind = self._stream_kind()
        if kind != self._kind:
            # stream support changed (e.g. the agent learned the camera type): let Home Assistant pick WebRTC/HLS again
            self._kind = kind
            if hasattr(self, "async_refresh_providers"):
                self.hass.async_create_task(self.async_refresh_providers())
        super()._handle_coordinator_update()

    async def async_camera_image(self, width: int | None = None, height: int | None = None) -> bytes | None:
        try:
            got = await self.coordinator.api.image("cam", self.printer_id)
        except AllMyPrintersAuthError:
            return None   # the coordinator's next poll starts the re-authentication
        return got[0] if got else None

    async def handle_async_mjpeg_stream(self, request: web.Request) -> web.StreamResponse | None:
        """Live view without a video stream: the agent's MJPEG stream; older agents → Home Assistant builds it from stills."""
        resp = None
        try:
            resp = await self.coordinator.api.mjpeg(self.printer_id)
        except AllMyPrintersError:
            resp = None
        if resp is None or resp.status != 200 or not (resp.content_type or "").startswith("multipart/"):
            if resp is not None:
                resp.release()
            return await super().handle_async_mjpeg_stream(request)
        try:
            return await async_aiohttp_proxy_stream(self.hass, request, resp.content, resp.headers.get("Content-Type"))
        finally:
            resp.close()
