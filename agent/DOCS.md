# AllMyPrinters Agent

The agent talks to your printers on your home network, books the filament each print used and keeps your spools,
print history and model library. It is the same agent as the Docker version, packaged as a Home Assistant app.

## Install

1. Start the app. Open it from the sidebar (**AllMyPrinters**).
2. Add your printers under **Printers → Add printer**. The agent searches your network.
3. Optional: pair the AllMyPrinters phone app under **Settings → Pair devices** (scan the QR code).

## Home Assistant integration

With the app running, Home Assistant offers the **AllMyPrinters** integration by itself:
**Settings → Devices & services → Discovered**. Confirm it and you get your printers, slots, spools and filament boxes
as entities, with pause / resume / stop, lights, fans and drying.

The integration itself comes from HACS: add `https://github.com/nolimitek/ha-allmyprinters` as a custom repository
(type *Integration*), install **AllMyPrinters**, restart Home Assistant.

## Options

| Option | |
|---|---|
| Language | Language of notifications and texts the agent writes itself. The interface follows your browser. |
| Access from anywhere | Paired phones and browsers reach the agent when you are away, end-to-end encrypted through allmyprinters.com. Turn off to use it only at home. |
| Password for direct access | Optional. Asked when you open `http://<home-assistant>:8090` directly. Not needed in the sidebar. |

## Network

The app uses the host network so it can find printers (Bambu Lab, Elegoo and network search) and phones can pair
over Wi-Fi. It listens on port **8090**; if another program already uses that port, the app cannot start.

## Data and backups

Spools, printers, history and library live in the app's data folder and are part of Home Assistant backups.
Moving from the Docker agent: in the old agent use **Settings → Backup → Save as file**, then **Load backup** here.

## Help

Community: https://allmyprinters.com/en/community/ · Issues: https://github.com/nolimitek/ha-allmyprinters/issues
