# Reference pages

Styled HTML write-ups: comparisons and part explainers, built from vendor manuals and the model. Each page
stands alone, with its CSS inline, light and dark themes, and its sources listed at the bottom.

| Page | What it covers |
|---|---|
| [toolboard-o2s-vs-nitehawk36.html](toolboard-o2s-vs-nitehawk36.html) | Orbitool O2S vs LDO Nitehawk-36 on the Orbiter 2.5: chamber rating, Smart Sensor, CAD, and what a switch would cost (https://github.com/dvystrcil/vt350/issues/6, 2026-11-10) |

## Viewing a page rendered

GitHub shows `.html` files as source. To see the page:

- **From a clone:** open the file in a browser, e.g. `xdg-open notes/reference/toolboard-o2s-vs-nitehawk36.html`.
  It works offline; without network access the fonts fall back to system fonts.
- **Online, no clone:**
  https://htmlpreview.github.io/?https://github.com/dvystrcil/vt350/blob/main/notes/reference/toolboard-o2s-vs-nitehawk36.html
  This is a third-party previewer that works on public repos.

## Adding a page

Same structure as this one:
- `<title>` = the subject's name;
- colours as `:root` tokens with dark-mode overrides;
- one reading column;
- a verdict or summary first;
- sources with commit SHAs or document versions at the bottom.

Render images (part explainers) go next to the page in a folder of the same name. Keep them small: PNG renders
are around 2 MB each.
