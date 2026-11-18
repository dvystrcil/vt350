#!/usr/bin/env python3
"""Write the Ambrosia material cards from ambrosia.json (vt350#60). Plain python, by hand:

    python3 cad/materials/build_cards.py

One card per grade (density, source) and one per colour in stock (inherits its grade, adds the colour), under
Ambrosia/<grade>/. And one card per bought part in bought.json, under Bought/, with the effective density that makes
the part's modelled solids weigh its published mass. Every file in both folders is generated: this removes cards
that are no longer in the data.
"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "platform", "freecad"))
import matlib  # noqa: E402

DATA = os.path.join(HERE, "ambrosia.json")
OUT = os.path.join(HERE, "Ambrosia")
BOUGHT = os.path.join(HERE, "bought.json")
OUT_BOUGHT = os.path.join(HERE, "Bought")
NS = "vt350/materials"
AUTHOR = "Daniel Vystrcil (vt350)"
LICENSE = "GPL-3.0-or-later"


def cards(d=None):
    """{relative path under Ambrosia/: card text}."""
    d = d or json.load(open(DATA))
    pal, out = d["palette"], {}
    for g in d["grades"]:
        url = f"https://west3d.com/products/{g['handle']}"
        base = f"Ambrosia {g['grade']}"
        rho = g["density_kg_m3"]
        dens = (f"Density {g['density_method']} {g['density_published_g_cm3']} g/cm3 ({rho / 1000:g} used)" if rho
                else "Density not published (the datasheet says TBD): this card has no density")
        buid = matlib.card_uuid(NS, base)
        out[f"{g['grade']}/{base}.FCMat"] = matlib.card_text(
            {"UUID": buid, "Name": base, "Author": AUTHOR, "License": LICENSE,
             "Description": f"Ambrosia {g['grade']} filament (West3D). Datasheet values: notes/filaments-ambrosia.md. "
                            f"Pick a colour card under it to get the colour too.",
             "SourceURL": url, "ReferenceSource": f"{g['grade']} product page, Technical Specifications, read "
                                                  f"{g['datasheet_read']}: {dens}"},
            father="Thermoplast", density_kg_m3=rho)
        for c in g["colours"]:
            p = pal[c["colour"]]
            if not p.get("rgb"): raise SystemExit(f"palette: no rgb for {c['colour']!r} (fetch_west3d.py added it)")
            name = f"{base} {c['colour']}"
            note = {"multi": " Multi-colour/effect filament: one colour stands in.", "glitter": " Has glitter."}.get(p.get("effect"), "")
            out[f"{g['grade']}/{name}.FCMat"] = matlib.card_text(
                {"UUID": matlib.card_uuid(NS, name), "Name": name, "Author": AUTHOR, "License": LICENSE,
                 "Description": f"Ambrosia {g['grade']}, colour {c['colour']} (SKU {c['sku']}), in stock "
                                f"{d['inventory_read']}. Colour value: {p['basis']}.{note}",
                 "SourceURL": f"{url}?variant={c['variant']}",
                 "ReferenceSource": f"{dens}; colour {p['rgb']} ({p['basis']})"},
                density_kg_m3=rho, inherits=(base, buid), colour=p["rgb"],
                transparency=p.get("transparency", 0.0), shininess=0.05 if "Matte" in g["grade"] else 0.2)
    return out


def effective_density(p):
    """kg/m3 that gives p's Default solids the rest of its published mass: (mass_g - known_g) / default_mm3."""
    return round((p["mass_g"] - p["known_g"]) / p["default_mm3"] * 1e6, 1)


def bought_cards(d=None):
    """{relative path under Bought/: card text}."""
    d = d or json.load(open(BOUGHT))
    out = {}
    for p in d["parts"]:
        rho = effective_density(p)
        out[f"{p['name']}.FCMat"] = matlib.card_text(
            {"UUID": matlib.card_uuid(NS, p["name"]), "Name": p["name"], "Author": AUTHOR, "License": LICENSE,
             "Description": f"NOT A REAL MATERIAL: an effective density for {p['selector']}, so that it weighs its "
                            f"published {p['mass_g']:g} g (cad/materials/bought.json). Modelled volume "
                            f"{p['default_mm3']:g} mm3 on {p['measured_on']}, plus {p['known_g']:g} g already in "
                            f"other materials.",
             "SourceURL": p["source_url"], "ReferenceSource": p["source"]},
            density_kg_m3=rho)
    return out


def write(out_dir, want):
    have = {os.path.relpath(os.path.join(r, f), out_dir) for r, _, fs in os.walk(out_dir) for f in fs if f.endswith(".FCMat")}
    for rel in sorted(have - set(want)): os.remove(os.path.join(out_dir, rel)); print("removed", rel)
    for rel, text in want.items():
        path = os.path.join(out_dir, rel); os.makedirs(os.path.dirname(path), exist_ok=True)
        if not os.path.exists(path) or open(path, encoding="utf-8").read() != text:
            open(path, "w", encoding="utf-8").write(text)
    for r, ds, fs in os.walk(out_dir, topdown=False):
        if not ds and not fs and r != out_dir: os.rmdir(r)
    print(f"{len(want)} cards in {out_dir}")


def main():
    write(OUT, cards())
    write(OUT_BOUGHT, bought_cards())


if __name__ == "__main__":
    main()
