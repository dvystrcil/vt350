# Raspberry Pi 5

| Variant | Author | Licence | In git | Used in the model |
|---|---|---|---|---|
| [`simplified-mandache/`](simplified-mandache/source.json) | Eduard Mandache | CC BY-SA 4.0 | yes (24 MB STEP) | **yes, from pass lite-75** (e-box `vt350-ebox-4.FCStd`) |
| [`official-raspberry-pi/`](official-raspberry-pi/source.json) | Raspberry Pi Ltd | MIT | only its `LICENSE.txt` (the STEP is 78 MB; add if wanted) | no: the reference |

**Why the simplified one** (owner, 2026-11-20): it matches the official model to within 0.1 mm over all of its
surface (only the small SMD parts are gone: 25 solids against 2,689), it can be shared, and it replaces the GrabCAD
Pi 5 (Mateusz Zelek), which could only be shown, was ~1.6 mm off vertically and had another vendor's Ethernet jack.
Up to lite-74 (`vt350-ebox-3.FCStd`) the e-box has the GrabCAD part.

The comparison, with renders: [Pi 5 models study page](https://dvystrcil.github.io/vt350/pi5-models.html), and
[vt350#268](https://github.com/dvystrcil/vt350/issues/268).
