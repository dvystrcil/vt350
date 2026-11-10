# Reference pages

Styled HTML write-ups: comparisons and part explainers, built from vendor manuals and the model. Each page
stands alone, with its CSS inline, light and dark themes, and its sources listed at the bottom.

| Page | What it covers |
|---|---|
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
(`.github/scripts/check_index.py`, tested by `test_check_index.py`) fails the build if any of these is missing:
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
