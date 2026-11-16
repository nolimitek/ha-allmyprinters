"""Constants for the AllMyPrinters integration."""

from __future__ import annotations

import re
from typing import Final

DOMAIN: Final = "allmyprinters"
TITLE: Final = "AllMyPrinters Agent"

DEFAULT_PORT: Final = 8090
# Key shown in the agent under Settings → Home Assistant (also sent along by Supervisor discovery)
TOKEN_RE: Final = re.compile(r"^amp_ha_[0-9a-f]{40}$")

CONF_SCAN_INTERVAL: Final = "scan_interval"
CONF_SLUG: Final = "slug"   # Home Assistant App slug when the entry came from Supervisor discovery
DEFAULT_SCAN_INTERVAL: Final = 15  # seconds; the agent itself polls the printers every 15 s
MIN_SCAN_INTERVAL: Final = 5
MAX_SCAN_INTERVAL: Final = 120
# The agent applies a command and refreshes its own state about 1.5 s later
COMMAND_REFRESH_DELAY: Final = 2.5

# Printer states reported by the agent (sensor "status")
STATES: Final = ["idle", "printing", "paused", "error", "offline"]
# Box drying limits (enforced by the agent as well)
DRY_TEMP_MIN: Final = 35
DRY_TEMP_MAX: Final = 55
DRY_TEMP_DEFAULT: Final = 45
DRY_HOURS_MIN: Final = 1
DRY_HOURS_MAX: Final = 24
DRY_HOURS_DEFAULT: Final = 4

# Fan and light kinds the agent reports (ctl.fans[].k, ctl.lights[].k); anything else is named after the printer's own name
FAN_KINDS: Final = ("part", "aux", "box", "chamber", "filter", "exhaust")
LIGHT_KINDS: Final = ("chamber", "head", "camera")

# Print events (event entity "print")
EVENT_STARTED: Final = "started"
EVENT_FINISHED: Final = "finished"
EVENT_FAILED: Final = "failed"
EVENT_CANCELLED: Final = "cancelled"

# Spool level (spools.items[].lvl)
SPOOL_LEVELS: Final = {0: "ok", 1: "low", 2: "critical"}
