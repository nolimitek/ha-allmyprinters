# Changelog

## 0.19.4

- Flashforge: "Level the bed before printing" is now a checkbox in the print screens (on by default). Until now the app always asked the printer to level.
- Flashforge Creator 5 / 5 Pro: when every tool prints from its own head, the app sends plain G-code again – this way is confirmed on a real Creator 5 Pro. The complete project file (0.19.3) is used when a tool prints from a different head.

## 0.19.3

- Flashforge Creator 5 / 5 Pro: prints sliced in the app are now sent as the complete project file (.3mf with the G-code inside), exactly as the Flashforge slicer sends them, with the filament-to-head map always included. Needs AllMyPrinters Slicer 1.0.11 – the default slicer already has it; update your own slicer container if you host one.
- Flashforge Creator 5 / 5 Pro: further attempt to fix prints that the printer accepted but never started.

## 0.19.2

- Flashforge: the print screens now show that Flashforge support is still in testing – please check on the printer that a print really starts.
- Flashforge Creator 5 / 5 Pro: when every tool prints from its own head (tool 1 from head 1 …), the app now sends plain G-code instead of a packed .gcode.3mf.
- Flashforge Creator 5 / 5 Pro: a packed .gcode.3mf now carries the full slice information Flash Studio writes (all four heads, filament-to-head map, layers).
- Flashforge Creator 5 / 5 Pro: attempt to fix prints that the printer accepted but never started (it stopped responding for a few minutes).

## 0.19.1

- Elegoo Centauri Carbon 2: new switch “Level bed before printing” when printing from the app. Untick it to skip the full bed probing, the same as ElegooSlicer’s “Auto bed leveling” box. The app remembers your choice per printer.
- Setup checklist: the spool steps are now marked “Optional” – printing works without setting up spools.
- Elegoo Centauri Carbon 2: every print started from the app levelled the bed first, even with a saved bed mesh.
- Setup checklist: “First print deducted” was ticked although nothing had been deducted from a spool yet.

## 0.19.0

- Print speed: while a print is running, choose Silent, Standard, Sport or Ludicrous right in the app (Anycubic Kobra: three levels; Bambu Lab, Elegoo, Creality, Flashforge and Klipper printers: four).
- Before printing: tick “Vibration compensation” (Anycubic LAN, Bambu Lab) and “Flow calibration” (Anycubic LAN, Bambu Lab, Flashforge AD5X and Creator 5). The app remembers your choice per printer.

## 0.18.2

- Elegoo Centauri Carbon 2: the anonymous print start report now says whether “busy” came from the printer status, the upload or the start command.
- Flashforge Creator 5 / 5 Pro: “Print” only uploaded the file, the printer did not start. The app now uploads first and then starts the print with the head assignment, the way the FlashForge app does.
- Flashforge Creator 5 / 5 Pro: a print only counts as started (and filament is only deducted) once the printer really runs; otherwise you get a clear message.
- “Report a problem”: send errors in the log now include the step and the error message (home network addresses removed).

## 0.18.1

- On a computer: printers on the left; on the right, for each printer, “Controls” with fans, light and the filament box (drying) – open, above “Running low” and “Recently printed”.
- The camera button now sits right under the print, above the slots.

## 0.18.0

- Maintenance: plan recurring tasks for each printer – due after print hours, kilograms of filament, a number of prints or days, whichever comes first. Counted from your real print history; eight templates to start with.
- The printer card shows when maintenance is due or coming up; “Done” starts the count again and keeps a short history with your note.
- With the agent: a notification on your phone when maintenance is due (can be switched off under Settings → Notifications).
- On a computer, each printer card has a column on the right: the camera first, below it fans, light and the filament box – open, without tapping “Controls”.
- Model search on a computer: areas start folded, like the platforms.

## 0.17.0

- Back to the familiar teal look and app icon – with a tidier layout.
- Printers: the heading switches between overview, print jobs, library and adding a printer; Print sits right next to it.
- The setup steps fold into one slim line that names the next step.
- Each slot appears once, as a spool with material and grams – tap a slot without a spool to assign one.
- Fans, light and the filament box (drying) sit behind “Controls”; the camera has its own button.
- On a computer, printers sit side by side with “Running low” and “Recently printed” next to them, and the top menu is shorter (Statistics, Settings and Community under “More”).
- Spools open as a list, with “+ Spool” next to the heading and the filter inside the search field.
- Library: Upload next to the heading, storage below it; on phones, file type, fits-on, tags and sorting sit behind the filter button.
- Model search: “Trending” as a grid instead of a swipe row, one small bookmark button per card, platforms folded on a computer.

## 0.16.0

- New look in the familiar 3DSEARCH colours and font: light grey, white cards, orange buttons.
- Slots sit like spools on a shelf, and the progress bar of a running print takes the colour of the filament that is printing.
- On a computer the menu moves into a sidebar on the left.
- Calmer pages: printer status shown as a word, no extra sentence under every heading, a flat bar at the bottom on phones.
- The Home Assistant side panel keeps its Home Assistant look.

## 0.15.0

- More manufacturer accounts, view only: Anycubic, Creality, Elegoo and Prusa Connect join Bambu Lab under Printers → Add printer → “Through your manufacturer account”. Status, slots (ACE, CFS, CANVAS, MMU) and temperatures, finished prints are booked off your spools.
- No LAN mode needed, so the manufacturer’s app keeps working – including Anycubic’s AI detection. Printing and controlling stay with the manufacturer’s app; to print from AllMyPrinters, connect the printer on your home network.
- Sign-in: Anycubic and Creality with the access key from their website, Elegoo and Prusa Connect with email and password (sent only to the manufacturer, not stored). The agent keeps just the access key on your computer.
- Renewed access keys are saved right away, so a restart never logs you out.
- Passwords are no longer trimmed when signing in.

## 0.14.0

- Bambu Lab through your Bambu account (view only): under Printers → Add printer → “Through your manufacturer account”, sign in with your email and the code Bambu emails you – no password needed. Pick the printers from your account; they show live status, AMS slots and temperatures, and finished prints are booked off your spools.
- No LAN mode or Developer mode needed, and Bambu Handy keeps working. Printing and controlling stay with Bambu Handy / Bambu Studio – for printing from AllMyPrinters, connect the printer on your home network instead.
- The agent talks to Bambu directly from your home – your sign-in only goes to Bambu, the access key stays on your computer and isn’t part of backups.
- Plate editor on the phone: the printer row no longer runs past the screen edge when the plate size is unknown.

## 0.13.1

- When the computer running the agent blocks connections to your home network (firewall, antivirus or VPN), the printer card, the printer search and “Check address” now say so and explain what to change, instead of only “not reachable”.
- On Windows the agent names the program that most likely blocks it (an active VPN, the firewall of your antivirus, or the Windows firewall itself) and whether Windows treats your Wi-Fi as “Public”. “Report a problem” includes this too.

## 0.13.0

- Edit 3MF files on the plate: the project keeps its colors, painting, modifiers and print settings. Move, rotate, copy or remove objects, switch to another plate of the file and choose which slot prints each color.
- Add STL parts from the library or your device to a 3MF plate (Bambu Studio and OrcaSlicer projects).
- “New plate”: start with an empty plate in the library or in the print view and add STL or 3MF files.
- “Save as new file” keeps the edited 3MF in your library; the original stays unchanged.
- Library: filter by file type (STL, 3MF, G-code). On the computer a filter sidebar like in the model search – views, file type, “fits on”, folders and tags; active filters as chips you can remove one by one.
- Every model card shows its file type.
- Plate editor: the filament slots sit in the left column, visible without scrolling.
- Plate editor: the bed size stayed “unknown” after updating the slicer container; it is checked again after an hour.
- “1 part” instead of “1 parts”.

## 0.12.1

- Plate editor: parts now follow the mouse or finger while you drag them (before they only jumped to the new spot on release).

## 0.12.0

- Edit plates: move, rotate, tilt, scale, mirror and copy parts on the print plate, lay a part on any face (tap it or let the app pick the best one).
- Choose the slot per part on multi-color printers and supports per part (off, automatic, from plate only).
- Warns when a part sticks out over the edge or parts overlap, and shows which of your other printers the plate also fits on.
- “Slice & print” prints exactly this layout; saved plates keep it, so “Print” in the library repeats the same arrangement.

## 0.11.0

- Find models like on 3DSEARCH: a filter sidebar on the computer (platforms with checkboxes, sort, price, categories, your library), active filters as chips you can remove one by one.
- Contests: running and past design contests from MakerWorld, Printables, Creality Cloud, NexPrint and MakerOnline with prizes, deadline and the submitted models – bookmark them or add them to a collection.
- Model cards show platform, designer, likes, makes and tags, with “Bookmark” and “Add to collection” right on the card.
- Printers: a clear “Turn on live view” button; on the computer the camera picture is smaller.

## 0.10.0

- New library: views “Recently printed”, “Never printed”, “Multi-color” and “Plates” (sidebar on the computer, dropdown on the phone).
- “Fits on”: pick a printer and the library shows which models fit on its bed.
- “Print again”: your latest prints at the top of the library, one tap opens the model with the printer it was last printed on.
- Quick actions on every card (“Print”, “Onto a plate”); model details show size, last print and whether it fits your printers.

## 0.9.0

- Build plates from your library: select several STL models and tap “Onto one plate”, or add models in the print view with “From the library”. Each model keeps its own count and slot.
- “Save as plate” keeps the combination as a library entry with a picture of its parts and its own print log; “Print” loads everything again.
- Print preview: the whole print bed is visible at the start (surface, 25 mm grid, outline), the model at its real position.
- Print preview: single-color prints in the color of the chosen slot, with a switch back to the line types.

## 0.8.4

- Library on a NAS: if the NAS sends no data for 60 seconds, “Print” stops waiting and says so in the window (before: up to 5 minutes on “Loading file …”). The seconds count up while loading; a file that's gone from the NAS gets its own message.
- Klipper printers that answer the start command late (e.g. Kobra S1 with Rinkhals): the agent checks for about 30 seconds whether the print runs, instead of once after 4 seconds.
- Settings → About shows “AllMyPrinters Agent” with its version, and in the paired Android app the app's version too.

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
