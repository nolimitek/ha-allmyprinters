# AllMyPrinters for Home Assistant

Brings the 3D printers, filament slots, filament boxes and spools of your **AllMyPrinters agent** into Home Assistant: status, progress, temperatures, light and fans, pause/resume/cancel, box drying and your spool stock. Every printer the agent is connected to works the same way (Klipper/Moonraker, OctoPrint, PrusaLink, Bambu Lab, Elegoo, Creality, Flashforge, Anycubic).

The integration talks only to the agent in your home network (`local_polling`). No cloud account is involved.

## Requirements

The AllMyPrinters agent must be running. Two ways:

- **As a Home Assistant app** (Home Assistant OS / Supervised). The app lives in this same repository:

  [![Add this repository to your Home Assistant](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2Fnolimitek%2Fha-allmyprinters)

  Then install **AllMyPrinters Agent** from the app store and start it.
- **In Docker** on any computer in your network: see the [installation guide](https://allmyprinters.com/en/agent/install/). The agent listens on port 8090 by default.

## Installation

1. In HACS: ⋮ → **Custom repositories** → add `https://github.com/nolimitek/ha-allmyprinters`, type **Integration**.

   [![Open this repository in HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=nolimitek&repository=ha-allmyprinters&category=integration)
2. Install **AllMyPrinters** and restart Home Assistant.

## Setup

- **With the AllMyPrinters Agent app:** the agent announces itself. Go to **Settings → Devices & services**, where AllMyPrinters shows up under **Discovered**, and confirm. Address and key come along. If the app was installed before the integration, it shows up after the restart in step 2.
- **Agent in Docker or elsewhere:** **Settings → Devices & services → Add integration → AllMyPrinters**, then enter the host (IP address or name of the computer running the agent), the port (8090) and the key from the agent's **Settings → Home Assistant** (starts with `amp_ha_`).

The key allows reading the agent's state and sending printer commands (pause/resume/cancel, drying, light, fans). If you generate a new key in the agent, the app passes it on automatically; otherwise Home Assistant asks for the new key. If the agent moves to another address, add the integration again with the new address: the existing entry is updated, entities and automations stay.

Options: update interval, 15 seconds by default (5–120 s).

## Entities

Per printer (one device each, below the agent device):

| Entity | |
|---|---|
| `sensor` Status | idle / printing / paused / error / offline |
| `sensor` Progress, Remaining time, Estimated end, Job, Current layer | while printing |
| `sensor` Nozzle / Bed temperature | |
| `sensor` Slot 1…n | remaining grams of the spool in that slot, shown as a spool picture in its real colour; material, colour, brand as attributes |
| `binary_sensor` Online, Printing, Problem | Problem = printer error (e.g. Klipper not ready), with the message |
| `button` Pause / Resume / Cancel print | available only when it makes sense |
| `light` Light, Head light, Camera light | for printers whose lights the agent can switch |
| `fan` Part fan, Aux fan, Enclosure fan, Chamber fan, Air filter, Exhaust | speed in percent. Some printers only accept fan changes during a print; Home Assistant then shows an error |
| `event` Print | `started`, `finished`, `failed`, `cancelled` — for automations |
| `switch` *Box* drying | start/stop drying (e.g. Anycubic ACE) using the two settings below |
| `number` *Box* drying temperature / duration | 35–55 °C, 1–24 h, kept in Home Assistant |
| `sensor` *Box* temperature / humidity / drying time remaining | where the box reports them |
| `sensor` Total prints / Total print time | the printer's own counters, where it reports them |

Lights and fans appear as soon as a printer reports them and are unavailable while the printer is offline. Lights and fans whose kind the agent doesn't know are named after the printer's own name for them.

On the agent device: **Spools in stock**, **Filament in stock**, **Spools almost empty** (with the list), **Spools to dry**, **Filament printed** (all-time, for long-term statistics), **Print costs this month**, and **one sensor per spool** (remaining grams; brand, material, colour, location, level and, when loaded, printer and slot as attributes). New spools appear automatically; archived ones become unavailable.

## Dashboard cards

The integration brings its cards along and registers them; they appear in the card picker after the restart.

```yaml
type: custom:allmyprinters-printer-card
device: <printer device>   # pick it in the visual editor
```

State with a drawn printer that moves while printing, progress ring with remaining time and end, temperatures, light and fans (tap a light to switch it, a fan to set its speed), the filament slots in their real colours, one block per filament box with climate and drying (presets or your own values), and pause/resume/cancel (cancel needs a second tap).

Every part can be switched off in the visual editor, or in YAML:

```yaml
type: custom:allmyprinters-printer-card
device: <printer device>
name: Workshop            # optional
hide: [temps, controls]   # any of: head, image, job, temps, controls, slots, boxes, boximage, buttons
```

Smaller cards with a single part, same `device` and `name` options:

| Card | Shows |
|---|---|
| `custom:allmyprinters-job-card` | the running print with progress, remaining time and buttons |
| `custom:allmyprinters-slots-card` | only the filament slots |
| `custom:allmyprinters-box-card` | the filament box with climate and drying |
| `custom:allmyprinters-stock-card` | filament in stock and all spools; low ones first (`rows: 12` to show more before folding) |

## Example automation

```yaml
triggers:
  - trigger: state
    entity_id: event.kobra_s1_print
    attribute: event_type
    to: finished
actions:
  - action: notify.mobile_app_phone
    data:
      message: "{{ state_attr('event.kobra_s1_print', 'job_name') }} is done"
```

## Notes

- After a command (pause, light, fan …) Home Assistant asks the agent again a few seconds later, so the new state shows up quickly.
- A printer you remove in the agent stays in Home Assistant with unavailable entities. Delete it on its device page (⋮ → Delete). Current printers and the agent device can't be deleted.
- Translated into English, German, French, Spanish, Italian and Dutch.

## License

GPL-3.0 — see [LICENSE](LICENSE).
