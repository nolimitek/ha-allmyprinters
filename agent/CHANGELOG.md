# Changelog

## 0.7.1

- The print view warns when the spool in a slot won’t last for a print (with a 5 g reserve). You can still print.

## 0.7.0

- New card “Plan” in the settings. During the beta every feature is free; later the agent will be part of an AllMyPrinters subscription.

## 0.6.2

- The app's log is in English now.

## 0.6.1

- Camera and model picture for Home Assistant: the integration (0.2.0) shows each printer's camera and the model that is printing, ready for dashboards.

## 0.6.0

- First version as a Home Assistant app: sidebar via ingress, Home Assistant discovers the integration by itself.
- Home Assistant interface for the integration (printers, slots, boxes, spools, pause/resume/stop, light, fan, drying).
- Fixed: warnings "filament box too humid" and "printer not reachable" were never sent.
