#!/usr/bin/env python3
"""Printed parts as OrcaSlicer projects (vt350#217): one 3MF per print set, and a staleness check.

  python3 platform/parts/orca_projects.py <sets.json>              # regenerate the stale projects (needs Orca)
  python3 platform/parts/orca_projects.py <sets.json> --all        # regenerate every project
  python3 platform/parts/orca_projects.py <sets.json> --only a,b   # regenerate the named projects
  python3 platform/parts/orca_projects.py <sets.json> --list       # print the sets, no Orca
  python3 platform/parts/orca_projects.py <sets.json> --check      # CI: fail when a project is stale, no Orca

The sets file is the printer's data. It names the parts manifest (a CSV with at least `path`, `qty` and
`material` columns, paths relative to `stl_root`), the OrcaSlicer presets (`orca`, the orca.json that
slice-check.py reads: vendors, machine, process), the output folder, and:
  - `materials`: [{match, id, label, filament}]. A row's `material` is matched by prefix, first match wins;
    `filament` is the filament preset for that material's sets, relative to orca.json's folder.
  - `subassemblies`: {id: description}.
  - `parts`: {manifest path: subassembly id}. Every manifest row with a path and a qty other than 0 must be here.
  - `qty`: {manifest path: copies} for a row whose qty isn't a whole number (e.g. "as-needed").
  - `skip`: {manifest path: reason} for a row not to place (e.g. one of two alternatives the printer doesn't use).
  - `slots`: {manifest path: slot}: a part printed in another filament than its set's main one, e.g. "accent"
    (an accent colour) or "clear". `slot_filaments`: {slot: filament preset, or null for the set's main one}.
    A project carries its main filament as slot 1, then each other slot its parts use, in `slot_filaments` order;
    every part is assigned its slot's filament. `max_filaments` (default 1) caps the slots per project, e.g. 4
    for a 4-lane MMU: a set that would need more is an error. More than one slot also needs a machine preset with
    a `change_filament_gcode`.
Relative paths in the sets file are relative to the sets file's folder.

A set is one (subassembly, material) pair: project `<out>/<subassembly>-<material id>.3mf`. OrcaSlicer's own CLI
loads the set's STLs, clones each to its quantity (--clone-objects), keeps each part as the STL stands (--orient 0:
the committed STLs are print-oriented), gives each its filament slot (--load-filaments, --load-filament-ids) and
arranges them on the machine's bed (--arrange 1, several filaments allowed on one plate). What doesn't fit goes
onto more plates of the same project; the machine, process and filament presets are selected, and the 3MF carries
their settings.

The index, `<out>/index.json`, records for each project its STLs with their sha256, copies and filament slot, its
filaments, the sha256 of the presets it used, its plate count, and the licences of its parts (the manifest's `license` column, so the
printer's REUSE annotations can name them). --check compares it with the manifest, the sets file, the STLs on disk
and the presets, and fails ("orca-projects: FAILED", exit 1) when:
  - an STL's sha256 differs from the one its project recorded, or its qty, slot or set changed;
  - a manifest row (path, qty > 0) has no project, or no entry in `parts`;
  - the index lists a part, or a project, that the manifest and sets no longer give;
  - a preset changed, or a project's .3mf is missing.
It names the projects to regenerate. Otherwise the last line is "orca-projects: OK".

Plain regeneration rewrites only the stale projects (Orca 2.5.1's output is byte-identical on a rerun, so this
saves time, not diffs), and deletes the .3mf of a set that no longer exists. Orca is the flatpak (com.orcaslicer.OrcaSlicer) or
ORCA_SLICER, as in slice-check.py; the flatpak can't see /tmp, so the output folder must be under $HOME.
Stdlib only.
"""
import argparse
import csv
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
INDEX = "index.json"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_sets(path):
    """the sets file, with its paths made absolute (relative to the file's folder)"""
    path = os.path.abspath(path)
    cfg = json.load(open(path))
    base = os.path.dirname(path)
    for k in ("manifest", "stl_root", "orca", "out"):
        if k not in cfg: raise ValueError(f"{path}: needs `{k}`")
        cfg[k] = os.path.normpath(os.path.join(base, cfg[k]))
    for k in ("materials", "subassemblies", "parts"):
        if k not in cfg: raise ValueError(f"{path}: needs `{k}`")
    cfg.setdefault("qty", {}); cfg.setdefault("skip", {}); cfg.setdefault("slots", {})
    cfg.setdefault("slot_filaments", {}); cfg.setdefault("max_filaments", 1)
    bad = sorted(set(cfg["slots"].values()) - set(cfg["slot_filaments"]))
    if bad: raise ValueError(f"{path}: slots {bad} have no entry in `slot_filaments`")
    ids = [m["id"] for m in cfg["materials"]]
    if len(set(ids)) != len(ids): raise ValueError(f"{path}: material ids repeat: {ids}")
    cfg["_path"] = path
    return cfg


def load_manifest(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def material_of(text, materials):
    """the first material whose `match` the manifest's material text starts with, or None"""
    t = (text or "").strip().lower()
    for m in materials:
        if t.startswith(m["match"].lower()): return m
    return None


def set_name(sub, mat):
    return f"{sub}-{mat}"


def plan(rows, cfg, hash_fn=sha256):
    """({set name: {subassembly, material, label, filament, parts: [{path, qty, sha256}]}}, [errors])"""
    sets, errors = {}, []
    seen = set()
    for r in rows:
        p = (r.get("path") or "").strip()
        if not p: continue                                       # link-only rows: nothing to place
        q = (r.get("qty") or "").strip()
        if q.isdigit():
            n = int(q)
            if n == 0: continue                                  # a row kept for the record (replaced part)
        elif p in cfg["qty"]:
            n = int(cfg["qty"][p])
        else:
            errors.append(f"{p}: qty {q!r} isn't a whole number; give the copies to place in the sets file's `qty`"); continue
        seen.add(p)
        if p in cfg["skip"]: continue                            # not placed, on purpose (the reason is in the file)
        sub = cfg["parts"].get(p)
        if sub is None:
            errors.append(f"{p}: no subassembly (add it to the sets file's `parts`)"); continue
        if sub not in cfg["subassemblies"]:
            errors.append(f"{p}: unknown subassembly {sub!r}"); continue
        mat = material_of(r.get("material"), cfg["materials"])
        if mat is None:
            errors.append(f"{p}: material {r.get('material')!r} matches no `materials` entry"); continue
        stl = os.path.join(cfg["stl_root"], p)
        if not os.path.isfile(stl):
            errors.append(f"{p}: STL missing ({stl})"); continue
        s = sets.setdefault(set_name(sub, mat["id"]), dict(subassembly=sub, material=mat["id"], label=mat["label"],
                                                             filament=mat["filament"], parts=[]))
        s["parts"].append(dict(path=p, qty=n, sha256=hash_fn(stl), license=(r.get("license") or "").strip(),
                               slot=cfg["slots"].get(p, "main")))
    paths = {(r.get("path") or "").strip() for r in rows}
    for k in ("parts", "skip", "slots", "qty"):
        for p in cfg[k]:
            if p not in paths: errors.append(f"{p}: in the sets file's `{k}` but not in the manifest")
    for name, st in sets.items():
        errors += assign_slots(name, st, cfg)
    return dict(sorted(sets.items())), errors


def assign_slots(name, s, cfg):
    """the set's filaments (slot 1 = its main one, then each other slot its parts use, in `slot_filaments` order),
    and each part's 1-based filament number. Returns errors (too many filaments for the machine)."""
    used = {p["slot"] for p in s["parts"]}
    order = ["main"] + [k for k in cfg["slot_filaments"] if k in used and k != "main"]
    s["slots"] = order
    s["filaments"] = [s["filament"] if k == "main" else (cfg["slot_filaments"][k] or s["filament"]) for k in order]
    for p in s["parts"]: p["filament"] = order.index(p["slot"]) + 1
    if len(order) > cfg["max_filaments"]:
        return [f"{name}: needs {len(order)} filaments ({', '.join(order)}), the machine takes {cfg['max_filaments']}"]
    return []


def preset_shas(cfg, filaments):
    """sha256 of the machine, process and filament presets a set uses (filaments: one path or a list)"""
    orca = json.load(open(cfg["orca"])); d = os.path.dirname(cfg["orca"])
    out = {"machine": sha256(os.path.join(d, orca["machine"])), "process": sha256(os.path.join(d, orca["process"]))}
    for f in ([filaments] if isinstance(filaments, str) else filaments):
        out["filament: " + f] = sha256(os.path.join(d, f))
    return out


def machine_changes_filament(cfg):
    """True when the machine preset has a filament-change G-code (an MMU), so a project can use several slots"""
    orca = json.load(open(cfg["orca"]))
    m = json.load(open(os.path.join(os.path.dirname(cfg["orca"]), orca["machine"])))
    return bool((m.get("change_filament_gcode") or "").strip())


def index_entry(name, s, presets, plates):
    return dict(file=name + ".3mf", subassembly=s["subassembly"], material=s["material"], label=s["label"],
                filament=s["filament"], filaments=s["filaments"], slots=s["slots"], presets=presets, plates=plates,
                copies=sum(p["qty"] for p in s["parts"]),
                licenses=sorted({p.get("license") or "?" for p in s["parts"]}),
                parts=[dict(path=p["path"], qty=p["qty"], sha256=p["sha256"], filament=p["filament"])
                       for p in s["parts"]])


def stale(sets, index, presets_for, out_dir=None):
    """{project: [reasons]} for every project that must be regenerated (or deleted)"""
    projects = index.get("projects", {})
    why = {}
    for name, s in sets.items():
        got = projects.get(name)
        if got is None:
            why.setdefault(name, []).append("no project yet"); continue
        want = {p["path"]: p for p in s["parts"]}
        have = {p["path"]: p for p in got.get("parts", [])}
        for p in sorted(want):
            if p not in have: why.setdefault(name, []).append(f"{p}: not in the project")
            elif have[p]["sha256"] != want[p]["sha256"]: why.setdefault(name, []).append(f"{p}: STL changed (sha256)")
            elif have[p]["qty"] != want[p]["qty"]:
                why.setdefault(name, []).append(f"{p}: qty {have[p]['qty']} -> {want[p]['qty']}")
            elif have[p].get("filament") != want[p]["filament"]:
                why.setdefault(name, []).append(f"{p}: filament slot {have[p].get('filament')} -> {want[p]['filament']}")
        for p in sorted(set(have) - set(want)):
            why.setdefault(name, []).append(f"{p}: in the project but no longer in this set")
        pr = presets_for(s)
        for k in sorted(set(pr) | set(got.get("presets", {}))):
            if got.get("presets", {}).get(k) != pr.get(k): why.setdefault(name, []).append(f"{k} preset changed")
        if got.get("filaments") != s["filaments"]: why.setdefault(name, []).append("filaments changed")
        if out_dir and not os.path.isfile(os.path.join(out_dir, got.get("file", name + ".3mf"))):
            why.setdefault(name, []).append(".3mf missing")
    for name in sorted(set(projects) - set(sets)):
        why.setdefault(name, []).append("set no longer exists: delete the project")
    return why


def load_index(out_dir):
    p = os.path.join(out_dir, INDEX)
    return json.load(open(p)) if os.path.isfile(p) else {"projects": {}}


def write_index(out_dir, index):
    with open(os.path.join(out_dir, INDEX), "w") as f:
        json.dump(index, f, indent=1, sort_keys=True); f.write("\n")


# --- OrcaSlicer (only for generating) ------------------------------------------------------------------------------

def _slice_check():
    spec = importlib.util.spec_from_file_location("slice_check", os.path.join(HERE, "slice-check.py"))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def orca_version(sc):
    r = subprocess.run(sc.ORCA_SLICER + ["--help"], capture_output=True, text=True)
    m = re.search(r"OrcaSlicer-([\w.\-]+)", r.stdout + r.stderr)
    return m.group(1) if m else "?"


def orca_datadir(dd, cfg, filaments, profiles):
    """a fresh datadir: vendor system profiles, and the machine, process and every set's filament as user presets
    (as slice-check.py does, without its support_check override: the projects keep the owner's process as is)"""
    orca = json.load(open(cfg["orca"])); src = os.path.dirname(cfg["orca"])
    os.makedirs(os.path.join(dd, "system"), exist_ok=True)
    for v in orca["vendors"]:
        shutil.copyfile(os.path.join(profiles, v + ".opc"), os.path.join(dd, "system", v + ".opc"))
    out = {}
    for t, rel in [("machine", orca["machine"]), ("process", orca["process"])] + [("filament", f) for f in filaments]:
        d = os.path.join(dd, "user", "default", t); os.makedirs(d, exist_ok=True)
        dst = os.path.join(d, os.path.basename(rel)); shutil.copyfile(os.path.join(src, rel), dst)
        out[rel if t == "filament" else t] = dst
    return out


def plates_in(path3mf):
    """number of plates in an Orca 3MF (Metadata/model_settings.config holds one <plate> per plate)"""
    with zipfile.ZipFile(path3mf) as z:
        try: return len(re.findall(rb"<plate>", z.read("Metadata/model_settings.config"))) or 1
        except KeyError: return 1


def generate(name, s, cfg, dd, presets, sc, work):
    """one project: Orca loads, clones, arranges and exports the 3MF. Returns its plate count."""
    od = os.path.join(work, name); shutil.rmtree(od, ignore_errors=True); os.makedirs(od)
    stls = [os.path.join(cfg["stl_root"], p["path"]) for p in s["parts"]]
    # --load-filament-ids: one filament number per loaded object; each clone keeps its object's filament.
    # --allow-multicolor-oneplate / --allow-mix-temp: arrange keeps several filaments (e.g. PET-GF + clear PETG)
    # on one plate, as the MMU prints them, instead of moving each filament to its own plate.
    cmd = sc.ORCA_SLICER + ["--datadir", dd, "--load-settings", f"{presets['machine']};{presets['process']}",
                            "--load-filaments", ";".join(presets[f] for f in s["filaments"]),
                            "--load-filament-ids", ",".join(str(p["filament"]) for p in s["parts"]),
                            "--allow-multicolor-oneplate", "--allow-mix-temp", "--orient", "0", "--arrange", "1",
                            "--clone-objects", ",".join(str(p["qty"]) for p in s["parts"]),
                            "--outputdir", od, "--export-3mf", name + ".3mf"] + stls
    r = subprocess.run(cmd, capture_output=True, text=True)
    with open(os.path.join(work, name + ".log"), "w") as f: f.write(" ".join(cmd) + "\n\n" + r.stdout + r.stderr)
    got = os.path.join(od, name + ".3mf")
    if r.returncode != 0 or not os.path.isfile(got):
        raise RuntimeError(f"{name}: Orca failed ({r.returncode}): {(r.stdout + r.stderr)[-600:]}")
    dst = os.path.join(cfg["out"], name + ".3mf")
    shutil.move(got, dst); shutil.rmtree(od, ignore_errors=True)
    return plates_in(dst)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("sets", help="the printer's sets file (e.g. parts/slice/sets.json)")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--check", action="store_true", help="fail when a project is stale; no Orca")
    g.add_argument("--list", action="store_true", help="print the sets; no Orca")
    g.add_argument("--all", action="store_true", help="regenerate every project")
    g.add_argument("--only", help="regenerate these projects (comma-separated)")
    a = ap.parse_args(argv)
    cfg = load_sets(a.sets)
    sets, errors = plan(load_manifest(cfg["manifest"]), cfg)
    index = load_index(cfg["out"])
    if any(len(s["filaments"]) > 1 for s in sets.values()) and not machine_changes_filament(cfg):
        errors.append("a set uses several filaments, but the machine preset has no change_filament_gcode (not an MMU)")
    def presets_for(s):
        return preset_shas(cfg, s["filaments"])
    why = stale(sets, index, presets_for, cfg["out"])

    if a.list:
        for name, s in sets.items():
            print(f"{name}: {s['label']}, {sum(p['qty'] for p in s['parts'])} copies of {len(s['parts'])} parts")
            for i, f in enumerate(s["filaments"], 1): print(f"  filament {i} ({s['slots'][i - 1]}): {f}")
            for p in s["parts"]: print(f"    {p['qty']} x {p['path']}  [filament {p['filament']}]")
        for e in errors: print(f"ERROR {e}")
        return 1 if errors else 0

    if a.check:
        for e in errors: print(f"ERROR {e}")
        for name, rs in sorted(why.items()):
            print(f"STALE {name}: " + "; ".join(rs))
        if errors or why:
            todo = ",".join(sorted(why)) or "-"
            print(f"regenerate: python3 {os.path.relpath(__file__)} {os.path.relpath(cfg['_path'])}"
                  + (f" --only {todo}" if why else ""))
            print(f"orca-projects: FAILED: {len(errors)} error(s), stale: {todo}")
            return 1
        print(f"{len(sets)} projects, {sum(len(s['parts']) for s in sets.values())} parts, "
              f"{sum(p['qty'] for s in sets.values() for p in s['parts'])} copies: all current")
        print("orca-projects: OK"); return 0

    if errors:
        for e in errors: print(f"ERROR {e}")
        print("orca-projects: FAILED: fix the sets file or manifest first"); return 1
    if a.all: todo = list(sets)
    elif a.only:
        todo = [n.strip() for n in a.only.split(",") if n.strip()]
        bad = [n for n in todo if n not in sets]
        if bad: print(f"orca-projects: FAILED: no such set(s): {bad}"); return 1
    else: todo = [n for n in why if n in sets]
    gone = [n for n in why if n not in sets]
    os.makedirs(cfg["out"], exist_ok=True)
    for n in gone:
        f = os.path.join(cfg["out"], index["projects"][n].get("file", n + ".3mf"))
        if os.path.isfile(f): os.remove(f)
        del index["projects"][n]; print(f"removed {n}")
    if todo:
        sc = _slice_check()
        work = os.path.join(cfg["out"], ".work"); shutil.rmtree(work, ignore_errors=True); os.makedirs(work)
        dd = os.path.join(work, "datadir")
        presets = orca_datadir(dd, cfg, sorted({f for s in sets.values() for f in s["filaments"]}), sc.orca_profiles_dir())
        index["orca"] = orca_version(sc)
        for n in todo:
            plates = generate(n, sets[n], cfg, dd, presets, sc, work)
            index["projects"][n] = index_entry(n, sets[n], presets_for(sets[n]), plates)
            print(f"{n}: {index['projects'][n]['copies']} copies on {plates} plate(s), "
                  f"{os.path.getsize(os.path.join(cfg['out'], n + '.3mf')) / 1e6:.1f} MB")
        shutil.rmtree(work, ignore_errors=True)
    index["_doc"] = (f"Generated by platform/parts/orca_projects.py from {os.path.basename(cfg['_path'])} (vt350#217): "
                     "each project's STLs with sha256 and copies, and its presets' sha256. Don't edit by hand; "
                     "--check compares it with the manifest and the STLs.")
    write_index(cfg["out"], index)
    if not todo and not gone: print("nothing stale")
    print("orca-projects: OK"); return 0


if __name__ == "__main__":
    sys.exit(main())
