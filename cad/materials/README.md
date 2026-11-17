# Material cards (vt350#60)

FreeCAD material cards (`.FCMat`) for the VT350's own materials, each with its source (`SourceURL`,
`ReferenceSource`). A model stores only a part's material UUID, so **register this folder** before opening a model,
or the parts fall back to "Default" with no warning:

- **GUI:** Edit > Preferences > Material > tick "Use materials from user defined directory" and set it to this folder.
  The cards then show in the material editor under "Custom", ready for any model.
- **Scripts:** `matlib.use_dir("<repo>/cad/materials")` (`platform/freecad/matlib.py`).

To add a card, use the material editor's **Inherit New** on the closest built-in material, set the values and the
source, and save it here; or script it (see `platform/freecad/LESSONS.md`, "Materials"). `test_cards.py` checks every
card has a unique UUID, a density and a source.

| Card | Density | Source |
|---|---|---|
| PET-GF (Ambrosia) | 1405 kg/m³ | Ambrosia PET-GF datasheet (ISO 1183, 1.40–1.41), `notes/filaments-ambrosia.md` |
