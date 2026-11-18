#!/usr/bin/env python3
"""Refresh cad/materials/ambrosia.json's inventory from West3D's product pages (vt350#60). Plain python, by hand:

    python3 cad/materials/fetch_west3d.py          # then: python3 cad/materials/build_cards.py

Reads each grade's public Shopify product data (<page>.js, with curl) and records the colours that are in stock today, with
SKU and variant id. Densities and colour values are kept: a colour that's new to the palette is added with
"rgb": null, and build_cards.py refuses to run until it has a value.
"""
import datetime, json, os, re, subprocess, time

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "ambrosia.json")


def variants(handle, tries=4):
    """The product's variants. Fetched with curl: West3D's Cloudflare answers python's urllib with 429 every time
    (measured 2026-11-17), curl is served. Waits and retries if curl gets a 429 too."""
    url = f"https://west3d.com/products/{handle}.js"
    for i in range(tries):
        r = subprocess.run(["curl", "-sS", "-A", "Mozilla/5.0", "-w", "\n%{http_code}", url], capture_output=True,
                           text=True, check=True)
        body, code = r.stdout.rsplit("\n", 1)
        if code == "200": return json.loads(body)["variants"]
        if code != "429" or i == tries - 1: raise SystemExit(f"{url}: HTTP {code}")
        time.sleep(60)


def colour_of(v):
    t = v["option1"]
    return None if t == "Default Title" else re.sub(r"\s+", " ", t).strip()


def main():
    d = json.load(open(DATA))
    for g in d["grades"]:
        seen = {}
        for v in variants(g["handle"]):
            c = colour_of(v) or g.get("only_colour")
            if c is None: raise SystemExit(f"{g['grade']}: no colour option and no only_colour")
            if v["available"] and c not in seen: seen[c] = {"colour": c, "sku": v["sku"], "variant": v["id"]}
        g["colours"] = list(seen.values())
        for c in seen: d["palette"].setdefault(c, {"rgb": None, "basis": "new: needs a value"})
        print(f"{g['grade']:10} {len(seen):3} colours in stock")
        time.sleep(5)
    d["inventory_read"] = datetime.date.today().isoformat()
    json.dump(d, open(DATA, "w"), indent=1, ensure_ascii=False); open(DATA, "a").write("\n")


if __name__ == "__main__":
    main()
