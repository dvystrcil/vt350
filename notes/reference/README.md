# Reference pages

Styled HTML write-ups: comparisons and part explainers, built from vendor manuals and the model. Each page
stands alone, with its CSS inline, light and dark themes, and its sources listed at the bottom.

| Page | What it covers |
|---|---|
| [bowden-arms.html](bowden-arms.html) | Opens on the dancer (#318): the roof exit clamps each bundle, a 20 g sheave behind the gantry holds the slack, every tool's fixed route and the sheave rising and falling over the walk. `#sliding`, `#tied` or `#stuck` open the earlier arm study's modes, which the index lists as their own entry. The per-tool bowden-arm study: the active bundle's solved shape at every lock position over the bed (roof exit → arm loop → O2S lock), in 3D, side and top views, for T0–T4, EI 700 / 2000 / 7000, and a sliding, tied or stalled loop; bends under R 51 in red; the loop-spacing comparison. Data in `bowden-arms/shapes.js`, from `cad/studies/bowden_arms_shapes.py` (https://github.com/dvystrcil/vt350/issues/312, 2026-11-25) |
| [pi5-models.html](pi5-models.html) | Three Raspberry Pi 5 models (GrabCAD, official Raspberry Pi MIT, Eduard Mandache's simplified CC BY-SA) compared surface by surface after a translation-only best fit; why the simplified one replaces the GrabCAD model (lite-74). Images in `pi5-models/` (https://github.com/dvystrcil/vt350/issues/268, 2026-11-20) |
| [cable-flap-guides.html](cable-flap-guides.html) | The flap-and-guide cable study: bundles sliding through a guide on each ceiling flap, every solved shape in front, side and top views (layouts A/B, EI 700–11 000, 0.2 N or no take-up), findings and the full table. Data in `cable-flap-guides/shapes.js` (2.6 MB), from `cad/studies/flap_guide` at 8eac49b (https://github.com/dvystrcil/vt350/issues/3, 2026-11-16) |
| [roof-exit.html](roof-exit.html) | The roof exit at lite-70: clamps flat on the roof panel, the cable channel lowered (lanes Z 737–763, cables 83–98 mm shorter), printed parts chamfered, the EMU lowered with its bowdens routed clear of the cables; five renders, the before/after table. Images in `roof-exit/` (https://github.com/dvystrcil/vt350/pull/241, 2026-11-18) |
| [frame-colour.html](frame-colour.html) | How the frame colour was chosen: the Fern look vs RAL 6011 Reseda (chosen, in stock at DLLPDF) and RAL 6001 Emerald, rendered on lite-30 so each lit frame bar matches the powder's product photo, plus the 10 closest Prismatic solid powders to Fern, measured. Images in `frame-colour/` (https://github.com/dvystrcil/vt350/issues/101, 2026-11-14) |
| [toolchange-docks.html](toolchange-docks.html) | The tool-change timeline on lite-30, rendered with Blender: a 16 s video of both docks (241 frames, 15 fps) and two 1920×1080 stills of the T0 pickup at park X 21 / attach Y −68.96. Media in `toolchange-docks/` (https://github.com/dvystrcil/vt350/issues/135, 2026-11-10) |
| [orbiter-hub.html](orbiter-hub.html) | What the Orbiter 2.5's hub housing is: renders from lite-30 (in place, pulled apart, alone), checked against LDO's model. Images in `orbiter-hub/` (https://github.com/dvystrcil/vt350/issues/6, 2026-11-10) |
| [toolboard-o2s-vs-nitehawk36.html](toolboard-o2s-vs-nitehawk36.html) | Orbitool O2S vs LDO Nitehawk-36 on the Orbiter 2.5: chamber rating, Smart Sensor, CAD, and what a switch would cost (https://github.com/dvystrcil/vt350/issues/6, 2026-11-10) |

## Viewing a page rendered

**Online:** https://dvystrcil.github.io/vt350/

- The `pages` workflow (`.github/workflows/pages.yml`) publishes this folder, and only this folder, on every push
  to `main` that touches it.
- Pull requests run its check without publishing.

**From a clone:** open the file in a browser, e.g. `xdg-open notes/reference/toolboard-o2s-vs-nitehawk36.html`. It
works offline; without network access the fonts fall back to system fonts.

GitHub itself shows `.html` files as source.

## Adding a page

**Link it from `index.html`** as well as from the table above. The workflow's check
(`platform/pages/check_index.py`, tested by `test_check_index.py`) fails the build if any of these is missing:
- the index doesn't link a page;
- the index links a page that doesn't exist;
- a page lacks `<!doctype html>`, `<meta charset="utf-8">` or a `<title>`. Without the charset, °C shows as
  garbage when the file is opened from a clone.

Same structure as the existing page:
- `<title>` = the subject's name;
- colours as `:root` tokens with dark-mode overrides;
- one reading column;
- a verdict or summary first;
- sources with commit SHAs or document versions at the bottom.

Render images (part explainers) go next to the page in a folder of the same name. Keep them small: PNG renders
are around 2 MB each.
