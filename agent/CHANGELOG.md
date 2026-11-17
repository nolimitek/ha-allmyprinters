# Changelog

## 0.8.3

- Models: new “Just added” list below “Trending now” – the newest models as a grid, with “Load more”.
- Warns when your own slicer container runs 1.0.4–1.0.7: with those versions Bambu Lab printers don't load filament from the AMS. Update the container to 1.0.8.

## 0.8.2

- Tidier settings: six groups you can open and close; only one is open at a time.

## 0.8.1

- Settings → Monitoring links straight to the setup guide for the detection service and says when it can’t be reached.

## 0.8.0

- New card **Monitoring** in the settings: before every print the agent compares the camera image with a picture of the empty plate and asks first if something still seems to be on it.
- Failure detection (spaghetti) is prepared too, but it needs the Obico detection service as a separate container. Home Assistant OS can't run it inside this app; if you run it elsewhere on your network, enter its address under Settings → Monitoring.

## 0.7.4

- Anycubic printers in LAN mode: new checkbox “Level the bed before printing” in the print view and for G-code files; the choice is remembered per printer.
- The anonymous print-start report now also covers prints with your own slicer and G-code files you print directly. Switch it off under Settings → Slicer.

## 0.7.3

- After a job sliced on the AllMyPrinters server is sent to a printer, the agent reports anonymously whether the printer started or which error came up (printer type, model, firmware, number of colours; no file, address or ID). It helps us find printers that still cause trouble. Nothing is sent with your own slicer; switch it off under Settings → Slicer.
- Anycubic ACE: an emptied slot no longer shows the material and colour of the last spool.

## 0.7.2

- Spools you assign to a slot are also set on the printer (Bambu Lab AMS, Elegoo Centauri Carbon 2). Bambu spools with an RFID tag are left alone; can be switched off in the settings.
- More reliable printing on Flashforge AD5X/Creator 5 (multi-colour), Bambu Lab, Elegoo Centauri Carbon 2 and Creality.

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
