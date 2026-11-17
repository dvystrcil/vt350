"""FreeCAD loads every card in cad/materials (vt350#60). Needs FreeCAD: $APP freecadcmd $PWD/cad/materials/test_cards_fc.py"""
import FreeCAD  # noqa: F401  (FreeCAD-only: the CI test runner skips files that import it)
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in dir() else os.path.join(os.getcwd(), "cad", "materials")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "platform", "freecad"))
sys.path.insert(0, HERE)
import matlib, build_cards  # noqa: E402

want = {t.split('Name: "')[1].split('"')[0]: t for t in build_cards.cards().values()}
mm = matlib.use_dir(HERE)
got = {m.Name: m for _, m in mm.Materials.items() if m.LibraryName == "Custom"}
bad = []
missing = set(want) - set(got)
if missing: bad.append(f"not loaded: {sorted(missing)[:5]} ({len(missing)})")
for name, t in want.items():
    m = got.get(name)
    if m is None: continue
    rho = t.split('Density: "')[1].split(" ")[0] if 'Density: "' in t else None
    d = m.PhysicalProperties.get("Density")
    if rho and (not d or abs(float(d.split()[0]) - float(rho) * 1e-9) > 1e-12): bad.append(f"{name}: density {d}, want {rho}")
    if "DiffuseColor" in t:
        dc = m.AppearanceProperties.get("DiffuseColor", "")
        if not dc: bad.append(f"{name}: no colour")
    if "Inherits:" in t and not m.Parent: bad.append(f"{name}: no parent")
print(f"RESULT {len(got)} custom cards loaded, {len(want)} expected, {len(bad)} problem(s)")
for b in bad[:20]: print("   ", b)
if bad: sys.exit(1)
