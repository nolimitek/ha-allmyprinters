"""Small client for the Home Assistant endpoint of the AllMyPrinters agent (http://<host>:<port>/ha, local network)."""

from __future__ import annotations

import asyncio
from typing import Any

import aiohttp
from yarl import URL

# The agent answers from its own 15 s state; only when that is stale does it ask the printers first
TIMEOUT = aiohttp.ClientTimeout(total=30)
IMAGE_TIMEOUT = aiohttp.ClientTimeout(total=15)


class AllMyPrintersError(Exception):
    """Generic error talking to the agent."""

    def __init__(self, code: str = "unknown") -> None:
        super().__init__(code)
        self.code = code


class AllMyPrintersAuthError(AllMyPrintersError):
    """The key is wrong or was regenerated in the agent."""


def parse_host(raw: str) -> tuple[str, int | None]:
    """Accept "192.168.1.5", "192.168.1.5:8090", "http://nas.local:8090/" or a bare IPv6 address.

    Returns (host, port given in the text or None).
    """
    text = raw.strip().rstrip("/")
    if text.count(":") > 1 and "[" not in text and "://" not in text:
        return text, None   # bare IPv6 address
    try:
        url = URL(text if "://" in text else f"http://{text}")
    except ValueError:
        return text, None
    return (url.host or text), url.explicit_port


def agent_url(host: str, port: int) -> URL:
    """Base URL of the agent (IPv6 hosts get their brackets from yarl)."""
    return URL.build(scheme="http", host=host, port=int(port))


class AllMyPrintersApi:
    """Read the printer/spool state and send commands with the agent's Home Assistant key."""

    def __init__(self, session: aiohttp.ClientSession, host: str, port: int, token: str) -> None:
        self._session = session
        self._token = token.strip()
        self.url = agent_url(host, port) / "ha"

    async def _request(self, method: str, json: dict[str, Any] | None = None) -> dict[str, Any]:
        try:
            async with self._session.request(
                method,
                self.url,
                json=json,
                headers={"Authorization": f"Bearer {self._token}", "Accept": "application/json"},
                timeout=TIMEOUT,
            ) as resp:
                try:
                    data = await resp.json(content_type=None)
                except ValueError:
                    data = None
                if resp.status in (401, 403):
                    raise AllMyPrintersAuthError((data or {}).get("error", "auth") if isinstance(data, dict) else "auth")
                if resp.status >= 400 or not isinstance(data, dict):
                    raise AllMyPrintersError(
                        data.get("error", f"http_{resp.status}") if isinstance(data, dict) else f"http_{resp.status}"
                    )
                return data
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise AllMyPrintersError("connection") from err

    async def status(self) -> dict[str, Any]:
        """Return printers, slots, boxes, fans/lights and the spool stock in one call."""
        return await self._request("GET")

    async def command(self, printer_id: str, cmd: str, **params: Any) -> None:
        """pause | resume | stop | dry_start | dry_stop | light | fan."""
        await self._request("POST", {"printer": printer_id, "cmd": cmd, **params})

    async def image(self, kind: str, printer_id: str) -> tuple[bytes, str] | None:
        """Camera snapshot (kind "cam", JPEG) or the running job's model picture ("thumb"); None when there is none.

        The first camera picture can take a few seconds: the agent starts reading the printer's video stream on demand.
        """
        try:
            async with self._session.get(
                self.url / kind / printer_id,
                headers={"Authorization": f"Bearer {self._token}"},
                timeout=IMAGE_TIMEOUT,
            ) as resp:
                if resp.status in (401, 403):
                    raise AllMyPrintersAuthError("auth")
                if resp.status != 200:
                    return None
                body = await resp.read()
                return (body, resp.content_type or "image/jpeg") if body else None
        except (aiohttp.ClientError, asyncio.TimeoutError):
            return None
