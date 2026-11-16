"""Config flow: address + key, wrong key, agent down, duplicate agent, Supervisor discovery, reauth, options."""

from __future__ import annotations

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers.service_info.hassio import HassioServiceInfo
from pytest_homeassistant_custom_component.common import MockConfigEntry

from .conftest import AGENT_ID, DOMAIN, ENTRY_DATA, HOST, KEY, PORT, URL

NEW_KEY = "amp_ha_" + "b2" * 20


def _discovery(token: str = KEY, port: int = PORT, agent_id: str = AGENT_ID) -> HassioServiceInfo:
    return HassioServiceInfo(
        config={"host": "127.0.0.1", "port": port, "token": token, "id": agent_id, "version": "0.5.7",
                "addon": "AllMyPrinters Agent"},
        name="AllMyPrinters Agent",
        slug="a1b2c3d4_allmyprinters_agent",
        uuid="5f2e2c1e0d6a4c3b9a8f7e6d5c4b3a29",
    )


async def test_user_flow_ok(hass: HomeAssistant, aioclient_mock, payload) -> None:
    aioclient_mock.get(URL, json=payload)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] is FlowResultType.FORM and result["step_id"] == "user"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"host": f" {HOST} ", "port": 8090.0,
                                                                                "token": f"  {KEY} "})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "AllMyPrinters Agent"
    assert result["data"] == {"host": HOST, "port": PORT, "token": KEY}
    assert result["result"].unique_id == AGENT_ID
    assert aioclient_mock.mock_calls[0][3]["Authorization"] == f"Bearer {KEY}"
    await hass.async_block_till_done()


async def test_user_flow_url_with_port(hass: HomeAssistant, aioclient_mock, payload) -> None:
    """A pasted address like http://host:port/ works as well."""
    aioclient_mock.get("http://nas.local:9000/ha", json=payload)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"host": "http://nas.local:9000/",
                                                                                "port": 8090, "token": KEY})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {"host": "nas.local", "port": 9000, "token": KEY}
    await hass.async_block_till_done()   # let the new entry finish its setup


async def test_user_flow_errors(hass: HomeAssistant, aioclient_mock) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    form = {"host": HOST, "port": PORT}
    # Wrong format: not even sent to the agent
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {**form, "token": "3ds_" + "a1" * 20})
    assert result["errors"] == {"token": "invalid_key"}
    assert not aioclient_mock.mock_calls

    aioclient_mock.get(URL, status=401, json={"error": "auth"})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {**form, "token": KEY})
    assert result["errors"] == {"base": "invalid_key"}

    aioclient_mock.clear_requests()
    aioclient_mock.get(URL, status=502, text="Bad gateway")
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {**form, "token": KEY})
    assert result["errors"] == {"base": "cannot_connect"}

    aioclient_mock.clear_requests()
    aioclient_mock.get(URL, json={"something": "else"})   # another web server at that address
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {**form, "token": KEY})
    assert result["errors"] == {"base": "cannot_connect"}
    assert result["type"] is FlowResultType.FORM


async def test_already_configured_updates_address(hass: HomeAssistant, aioclient_mock, payload) -> None:
    entry = MockConfigEntry(domain=DOMAIN, unique_id=AGENT_ID, data={"host": "10.0.0.9", "port": PORT, "token": KEY})
    entry.add_to_hass(hass)
    aioclient_mock.get(URL, json=payload)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"host": HOST, "port": PORT, "token": KEY})
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert entry.data["host"] == HOST


async def test_hassio_discovery_new_entry(hass: HomeAssistant, aioclient_mock, payload) -> None:
    aioclient_mock.get("http://127.0.0.1:8090/ha", json=payload)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_HASSIO},
                                                       data=_discovery())
    assert result["type"] is FlowResultType.FORM and result["step_id"] == "hassio_confirm"
    assert result["description_placeholders"] == {"addon": "AllMyPrinters Agent"}
    assert not aioclient_mock.mock_calls   # nothing is checked before the user confirms
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "AllMyPrinters Agent"
    assert result["data"] == {"host": "127.0.0.1", "port": 8090, "token": KEY, "slug": "a1b2c3d4_allmyprinters_agent"}
    assert result["result"].unique_id == AGENT_ID
    await hass.async_block_till_done()
    # The App's sidebar page is the device's "Visit" link
    from homeassistant.helpers import device_registry as dr

    devices = dr.async_entries_for_config_entry(dr.async_get(hass), result["result"].entry_id)
    agent = next(d for d in devices if (DOMAIN, f"agent_{AGENT_ID}") in d.identifiers)
    assert agent.configuration_url == "homeassistant://hassio/ingress/a1b2c3d4_allmyprinters_agent"


async def test_hassio_discovery_confirm_fails(hass: HomeAssistant, aioclient_mock) -> None:
    aioclient_mock.get("http://127.0.0.1:8090/ha", status=401, json={"error": "auth"})
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_HASSIO},
                                                       data=_discovery())
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.FORM and result["errors"] == {"base": "invalid_key"}


async def test_hassio_discovery_updates_existing_entry(hass: HomeAssistant, aioclient_mock, payload) -> None:
    """A key regenerated in the App (or a new port) reaches the existing entry without asking."""
    entry = MockConfigEntry(domain=DOMAIN, unique_id=AGENT_ID, data=ENTRY_DATA)
    entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_HASSIO},
                                                       data=_discovery(token=NEW_KEY, port=8091))
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert entry.data == {"host": "127.0.0.1", "port": 8091, "token": NEW_KEY, "slug": "a1b2c3d4_allmyprinters_agent"}


async def test_hassio_discovery_incomplete(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_HASSIO},
                                                       data=_discovery(agent_id=""))
    assert result["type"] is FlowResultType.ABORT and result["reason"] == "invalid_discovery_info"


async def test_reauth(hass: HomeAssistant, aioclient_mock, payload) -> None:
    entry = MockConfigEntry(domain=DOMAIN, unique_id=AGENT_ID, data={**ENTRY_DATA, "token": "amp_ha_" + "00" * 20})
    entry.add_to_hass(hass)
    aioclient_mock.get(URL, json=payload)
    result = await entry.start_reauth_flow(hass)
    assert result["step_id"] == "reauth_confirm"
    assert result["description_placeholders"]["host"] == f"{HOST}:{PORT}"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"token": "nonsense"})
    assert result["errors"] == {"token": "invalid_key"}
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"token": KEY})
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data["token"] == KEY
    await hass.async_block_till_done()   # the entry reloads with the new key
    assert aioclient_mock.mock_calls[0][3]["Authorization"] == f"Bearer {KEY}"


async def test_reauth_wrong_agent(hass: HomeAssistant, aioclient_mock, payload) -> None:
    entry = MockConfigEntry(domain=DOMAIN, unique_id="0123456789ab", data=ENTRY_DATA)
    entry.add_to_hass(hass)
    aioclient_mock.get(URL, json=payload)
    result = await entry.start_reauth_flow(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"token": KEY})
    assert result["reason"] == "wrong_account"


async def test_options(hass: HomeAssistant, aioclient_mock, payload) -> None:
    entry = MockConfigEntry(domain=DOMAIN, unique_id=AGENT_ID, data=ENTRY_DATA)
    entry.add_to_hass(hass)
    aioclient_mock.get(URL, json=payload)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.runtime_data.update_interval.total_seconds() == 15
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.options.async_configure(result["flow_id"], {"scan_interval": 30})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options == {"scan_interval": 30}
    await hass.async_block_till_done()
    assert entry.runtime_data.update_interval.total_seconds() == 30
