"""Camera (pictures through the agent) and the model picture of the running print."""

from __future__ import annotations

from datetime import timedelta
from http import HTTPStatus

import pytest

from homeassistant.components.camera import async_get_image
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed

from .conftest import AGENT_ID, DOMAIN, ENTRY_DATA, URL

JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 64 + b"\xff\xd9"
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
CAM = "camera.kobra_s1_camera"
MODEL = "image.kobra_s1_model"


async def _setup(hass: HomeAssistant, aioclient_mock, payload) -> MockConfigEntry:
    entry = MockConfigEntry(domain=DOMAIN, unique_id=AGENT_ID, data=ENTRY_DATA)
    entry.add_to_hass(hass)
    aioclient_mock.get(URL, json=payload)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


@pytest.fixture
def cam_payload(payload):
    payload["printers"][0]["cam"] = True
    payload["printers"][0]["job"]["thumb"] = "aaaaaaaaaaaa"
    return payload


async def test_camera_picture_from_agent(hass: HomeAssistant, aioclient_mock, cam_payload) -> None:
    aioclient_mock.get(f"{URL}/cam/p1", content=JPEG, headers={"Content-Type": "image/jpeg"})
    await _setup(hass, aioclient_mock, cam_payload)
    assert hass.states.get(CAM) is not None
    image = await async_get_image(hass, CAM)
    assert image.content == JPEG and image.content_type == "image/jpeg"
    call = [c for c in aioclient_mock.mock_calls if str(c[1]).endswith("/ha/cam/p1")][-1]
    assert call[3]["Authorization"] == "Bearer " + ENTRY_DATA["token"]


async def test_camera_without_picture(hass: HomeAssistant, aioclient_mock, cam_payload) -> None:
    aioclient_mock.get(f"{URL}/cam/p1", status=HTTPStatus.NO_CONTENT)
    await _setup(hass, aioclient_mock, cam_payload)
    with pytest.raises(HomeAssistantError):
        await async_get_image(hass, CAM)


async def test_no_camera_entity_without_camera(hass: HomeAssistant, aioclient_mock, payload) -> None:
    payload["printers"][0]["cam"] = False
    await _setup(hass, aioclient_mock, payload)
    assert hass.states.get(CAM) is None


async def test_camera_unavailable_when_printer_offline(hass: HomeAssistant, aioclient_mock, cam_payload) -> None:
    cam_payload["printers"][0]["online"] = False
    await _setup(hass, aioclient_mock, cam_payload)
    assert hass.states.get(CAM).state == "unavailable"


async def test_model_picture_follows_the_job(hass: HomeAssistant, hass_client, aioclient_mock, cam_payload) -> None:
    aioclient_mock.get(f"{URL}/thumb/p1", content=PNG, headers={"Content-Type": "image/png"})
    await _setup(hass, aioclient_mock, cam_payload)
    state = hass.states.get(MODEL)
    assert state.state not in ("unavailable", "unknown")
    client = await hass_client()
    resp = await client.get(f"/api/image_proxy/{MODEL}")
    assert resp.status == 200 and await resp.read() == PNG

    # next print with another preview → new timestamp, picture fetched again
    first = state.state
    cam_payload["printers"][0]["job"]["thumb"] = "bbbbbbbbbbbb"
    aioclient_mock.clear_requests()
    aioclient_mock.get(URL, json=cam_payload)
    aioclient_mock.get(f"{URL}/thumb/p1", content=PNG, headers={"Content-Type": "image/png"})
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=20))
    await hass.async_block_till_done()
    assert hass.states.get(MODEL).state != first
    resp = await client.get(f"/api/image_proxy/{MODEL}")
    assert resp.status == 200
    assert any(str(c[1]).endswith("/ha/thumb/p1") for c in aioclient_mock.mock_calls)

    # print over → no picture
    cam_payload["printers"][0]["job"] = None
    aioclient_mock.clear_requests()
    aioclient_mock.get(URL, json=cam_payload)
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=40))
    await hass.async_block_till_done()
    assert hass.states.get(MODEL).state == "unavailable"


# ── live view (0.3.0): H.264 cameras as stream source, the others as the agent's MJPEG stream ──
MJPEG_CT = "multipart/x-mixed-replace; boundary=ampframe"
MJPEG = b"--ampframe\r\nContent-Type: image/jpeg\r\nContent-Length: " + str(len(JPEG)).encode() + b"\r\n\r\n" + JPEG + b"\r\n"


async def test_video_camera_is_a_stream_source(hass: HomeAssistant, aioclient_mock, cam_payload) -> None:
    from homeassistant.components.camera import CameraEntityFeature, async_get_stream_source

    cam_payload["printers"][0]["cam_stream"] = "video"
    await _setup(hass, aioclient_mock, cam_payload)
    state = hass.states.get(CAM)
    assert state.attributes["supported_features"] & CameraEntityFeature.STREAM
    src = await async_get_stream_source(hass, CAM)
    assert src == f"{URL}/live/p1?t=" + ENTRY_DATA["token"]


async def test_mjpeg_camera_proxies_the_agent_stream(hass: HomeAssistant, hass_client, aioclient_mock, cam_payload) -> None:
    from homeassistant.components.camera import CameraEntityFeature, async_get_stream_source

    cam_payload["printers"][0]["cam_stream"] = "mjpeg"
    aioclient_mock.get(f"{URL}/mjpeg/p1", content=MJPEG * 3, headers={"Content-Type": MJPEG_CT})
    await _setup(hass, aioclient_mock, cam_payload)
    state = hass.states.get(CAM)
    assert not state.attributes.get("supported_features", 0) & CameraEntityFeature.STREAM
    assert await async_get_stream_source(hass, CAM) is None
    client = await hass_client()
    resp = await client.get(f"/api/camera_proxy_stream/{CAM}")
    assert resp.status == 200 and resp.headers["Content-Type"] == MJPEG_CT
    assert (await resp.read()) == MJPEG * 3
    call = [c for c in aioclient_mock.mock_calls if str(c[1]).endswith("/ha/mjpeg/p1")][-1]
    assert call[3]["Authorization"] == "Bearer " + ENTRY_DATA["token"]


async def test_old_agent_without_stream_falls_back_to_stills(hass: HomeAssistant, hass_client, aioclient_mock, cam_payload) -> None:
    from homeassistant.components.camera import CameraEntityFeature

    # agent before the live streams: no cam_stream, /ha/mjpeg answers 401 (unknown path) → Home Assistant builds MJPEG from stills
    aioclient_mock.get(f"{URL}/mjpeg/p1", status=HTTPStatus.UNAUTHORIZED, json={"error": "auth"})
    aioclient_mock.get(f"{URL}/cam/p1", content=JPEG, headers={"Content-Type": "image/jpeg"})
    await _setup(hass, aioclient_mock, cam_payload)
    assert not hass.states.get(CAM).attributes.get("supported_features", 0) & CameraEntityFeature.STREAM
    client = await hass_client()
    resp = await client.get(f"/api/camera_proxy_stream/{CAM}")
    assert resp.status == 200 and resp.headers["Content-Type"].startswith("multipart/x-mixed-replace")
    chunk = await resp.content.read(4096)
    assert JPEG[:4] in chunk
    resp.close()


async def test_stream_support_follows_the_agent(hass: HomeAssistant, aioclient_mock, cam_payload) -> None:
    from homeassistant.components.camera import CameraEntityFeature

    await _setup(hass, aioclient_mock, cam_payload)
    assert not hass.states.get(CAM).attributes.get("supported_features", 0) & CameraEntityFeature.STREAM
    # the agent learned the camera type (first picture) → next poll offers the stream
    cam_payload["printers"][0]["cam_stream"] = "video"
    aioclient_mock.clear_requests()
    aioclient_mock.get(URL, json=cam_payload)
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=60))
    await hass.async_block_till_done()
    assert hass.states.get(CAM).attributes["supported_features"] & CameraEntityFeature.STREAM
