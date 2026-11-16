"""Config flow: address + key of the AllMyPrinters agent, or found automatically when the agent runs as a Home Assistant App."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_TOKEN
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)
from homeassistant.helpers.service_info.hassio import HassioServiceInfo

from .api import AllMyPrintersApi, AllMyPrintersAuthError, AllMyPrintersError, parse_host
from .const import (
    CONF_SCAN_INTERVAL,
    CONF_SLUG,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
    TITLE,
    TOKEN_RE,
)

PORT_SELECTOR = NumberSelector(NumberSelectorConfig(min=1, max=65535, step=1, mode=NumberSelectorMode.BOX))
TOKEN_SELECTOR = TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD))
REAUTH_SCHEMA = vol.Schema({vol.Required(CONF_TOKEN): TOKEN_SELECTOR})


def _user_schema(defaults: Mapping[str, Any]) -> vol.Schema:
    return vol.Schema({
        vol.Required(CONF_HOST, default=defaults.get(CONF_HOST, vol.UNDEFINED)): TextSelector(),
        vol.Required(CONF_PORT, default=int(defaults.get(CONF_PORT, DEFAULT_PORT))): PORT_SELECTOR,
        vol.Required(CONF_TOKEN): TOKEN_SELECTOR,
    })


class AllMyPrintersConfigFlow(ConfigFlow, domain=DOMAIN):
    """One entry per agent (unique id = agent id)."""

    VERSION = 1

    def __init__(self) -> None:
        self._discovered: dict[str, Any] = {}

    async def _check(self, host: str, port: int, token: str) -> tuple[dict[str, Any] | None, dict[str, str]]:
        """Validate address and key against the agent; returns (status, errors)."""
        if not TOKEN_RE.match(token.strip()):
            return None, {CONF_TOKEN: "invalid_key"}
        try:
            data = await AllMyPrintersApi(async_get_clientsession(self.hass), host, port, token).status()
        except AllMyPrintersAuthError:
            return None, {"base": "invalid_key"}
        except AllMyPrintersError:
            return None, {"base": "cannot_connect"}
        if not (data.get("account") or {}).get("id"):
            return None, {"base": "cannot_connect"}   # something else answers at that address
        return data, {}

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Address and key from the agent's Settings → Home Assistant."""
        errors: dict[str, str] = {}
        if user_input is not None:
            host, port_in_host = parse_host(user_input[CONF_HOST])
            port = port_in_host or int(user_input[CONF_PORT])
            token = user_input[CONF_TOKEN].strip()
            data, errors = await self._check(host, port, token)
            if data:
                await self.async_set_unique_id(str(data["account"]["id"]))
                # Adding a known agent again with a new address or key updates the existing entry
                self._abort_if_unique_id_configured(updates={CONF_HOST: host, CONF_PORT: port, CONF_TOKEN: token})
                return self.async_create_entry(title=TITLE, data={CONF_HOST: host, CONF_PORT: port, CONF_TOKEN: token})
        return self.async_show_form(step_id="user", data_schema=_user_schema(user_input or {}), errors=errors)

    async def async_step_hassio(self, discovery_info: HassioServiceInfo) -> ConfigFlowResult:
        """The AllMyPrinters Agent app announced itself through Supervisor discovery (service "allmyprinters")."""
        config = discovery_info.config
        agent_id, token = str(config.get("id") or ""), str(config.get("token") or "")
        if not agent_id or not token:
            return self.async_abort(reason="invalid_discovery_info")
        try:
            port = int(config.get("port") or DEFAULT_PORT)
        except (TypeError, ValueError):
            port = DEFAULT_PORT
        self._discovered = {CONF_HOST: str(config.get("host") or "127.0.0.1"), CONF_PORT: port, CONF_TOKEN: token,
                            CONF_SLUG: discovery_info.slug}
        await self.async_set_unique_id(agent_id)
        # A key regenerated in the agent or a new port reaches the existing entry this way (and reloads it)
        self._abort_if_unique_id_configured(updates=self._discovered)
        self.context["title_placeholders"] = {"name": discovery_info.name or TITLE}
        return await self.async_step_hassio_confirm()

    async def async_step_hassio_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Ask before adding the discovered agent."""
        errors: dict[str, str] = {}
        if user_input is not None:
            d = self._discovered
            data, errors = await self._check(d[CONF_HOST], d[CONF_PORT], d[CONF_TOKEN])
            if data:
                self._abort_if_unique_id_configured()   # added by hand in the meantime
                return self.async_create_entry(title=TITLE, data=d)
        self._set_confirm_only()
        return self.async_show_form(step_id="hassio_confirm", errors=errors,
                                    description_placeholders={"addon": self.context.get("title_placeholders", {}).get("name", TITLE)})

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        """The key was regenerated in the agent."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        entry = self._get_reauth_entry()
        if user_input is not None:
            token = user_input[CONF_TOKEN].strip()
            data, errors = await self._check(entry.data[CONF_HOST], entry.data[CONF_PORT], token)
            if data:
                await self.async_set_unique_id(str(data["account"]["id"]))
                self._abort_if_unique_id_mismatch(reason="wrong_account")
                return self.async_update_reload_and_abort(entry, data_updates={CONF_TOKEN: token})
        return self.async_show_form(step_id="reauth_confirm", data_schema=REAUTH_SCHEMA, errors=errors,
                                    description_placeholders={"host": f"{entry.data[CONF_HOST]}:{entry.data[CONF_PORT]}"})

    @staticmethod
    @callback
    def async_get_options_flow(config_entry) -> AllMyPrintersOptionsFlow:
        return AllMyPrintersOptionsFlow()


class AllMyPrintersOptionsFlow(OptionsFlow):
    """Polling interval."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data={CONF_SCAN_INTERVAL: int(user_input[CONF_SCAN_INTERVAL])})
        current = self.config_entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required(CONF_SCAN_INTERVAL, default=current): NumberSelector(NumberSelectorConfig(
                    min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL, step=1, unit_of_measurement="s", mode=NumberSelectorMode.BOX)),
            }),
        )
