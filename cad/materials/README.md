# Material cards (vt350#60)

FreeCAD material cards (`.FCMat`) for the filament the VT350 is printed in: **Ambrosia** (West3D), every grade
with a datasheet and every colour West3D has in stock. Each grade has a card with its density and source; each
colour has a card that inherits its grade and adds the colour. Picking a colour card gives a part the colour and the
right density together.

## Use them

A model stores only a part's material UUID, so **register this folder** before opening a model, or the parts fall
back to "Default" with no warning:

- **GUI:** Edit > Preferences > Material > tick "Use materials from user defined directory" and set it to this
  folder. The cards then show under **Custom** in the material editor and selector, for any model.
- **Scripts:** `matlib.use_dir("<repo>/cad/materials")` (`platform/freecad/matlib.py`).

## The colours are estimates

West3D hasn't published colour codes yet (they're working on it). Each colour's value is an **estimate from its
name**, and every card says so in its description and reference. Exceptions: "Black (Pantone 7C)" uses Pantone
Black 7 C, and British Racing Green the conventional value. Multi-colour and effect filaments (Rainbow, Marble,
Easter Egg, Autumn Shift) get one stand-in colour.

## Change them

Everything under `Ambrosia/` is generated from `ambrosia.json`. Don't edit a card; edit the data and rebuild:

```sh
python3 cad/materials/fetch_west3d.py   # refresh what's in stock (adds new colours with "rgb": null)
python3 cad/materials/build_cards.py    # rewrite the cards (refuses while a colour has no value)
```

- **A real colour code:** set that colour's `rgb` and `basis` in `palette` (shared by every grade with that colour name).
- **A density:** each grade's `density_kg_m3` (PCTG's datasheet says TBD, so its cards have none).
- A card's UUID comes from its name, so rebuilding never changes it, and models keep their materials.

Checks: `test_cards.py` (plain python, CI: the cards match the data, unique UUIDs, a density and source on each,
every colour valued) and `test_cards_fc.py` (FreeCAD loads all of them: `$APP freecadcmd $PWD/cad/materials/test_cards_fc.py`).

## Bought parts (`Bought/`)

A bought part's solids in the model are a mockup: their volume isn't the real part's, and most carry FreeCAD's
weightless "Default" material. Where the maker publishes a mass, `bought.json` records it with its source, and
`build_cards.py` writes one card per part with an **effective density**: the one that makes the part's Default
solids, plus its solids already in another material, add up to that mass. It is **not a real material**, and each
card says so.

| Card | Published mass | Source | Effective density |
|---|---|---|---|
| Bought LDO Orbiter v2.5 with motor | ~135 g | orbiterprojects.com, Orbiter v2.0 ("Weight reduced to ~135 grams"; v2.5 uses the v2.0 body; the motor isn't named, the owner's is the 36STH20) | 2403.5 kg/m³ |
| Bought Beacon RevH Normal | 3.5 g | beacon3d.com ("the 3.5g Beacon"; the cable not counted) | 1389.8 kg/m³ |

The density depends on the modelled volume, measured on the model named in `bought.json` (`measured_on`). The pass
that assigns these cards re-measures it and refuses to save if it differs. If a part's mockup changes, update
`default_mm3` / `known_g` and rebuild. Parts with no published mass (the blowers, the hotend, the O2S, the Smart
Sensor) stay Default until the owner weighs them (#60 AC6). `test_cards.py` checks that each card gives its
published mass.
