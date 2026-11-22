#!/usr/bin/env python3
"""Printed parts as OrcaSlicer projects (vt350#217): one 3MF per work unit, a plate per material, and a staleness check.

  python3 platform/parts/orca_projects.py <sets.json>              # regenerate the stale projects (needs Orca)
  python3 platform/parts/orca_projects.py <sets.json> --all        # regenerate every project
  python3 platform/parts/orca_projects.py <sets.json> --only a,b   # regenerate the named projects
  python3 platform/parts/orca_projects.py <sets.json> --list       # print the projects and plates, no Orca
  python3 platform/parts/orca_projects.py <sets.json> --check      # CI: fail when a project is stale, no Orca
  python3 platform/parts/orca_projects.py <sets.json> --check --reuse REUSE.toml   # also each project's licence label

The sets file is the printer's data. It names the parts manifest (a CSV with at least `path`, `qty` and
`material` columns, paths relative to `stl_root`), the OrcaSlicer presets (`orca`, the orca.json that
slice-check.py reads: vendors, machine, process), the output folder, the bed (`bed_mm`: [x, y]), and:
  - `units`: {id: description}: the work units, one project each (`<out>/<unit>.3mf`).
  - `parts`: {manifest path: unit id}. Every manifest row with a path and a qty other than 0 must be here, or in
    `skip`.
  - `materials`: [{match, id, label, filament}]. A row's `material` is matched by prefix, first match wins;
    `filament` is the material's filament preset, relative to orca.json's folder. Each material of a unit gets
    its own plate(s), in `materials` order.
  - `qty`: {manifest path: copies} for a row whose qty isn't a whole number (e.g. "as-needed").
  - `skip`: {manifest path: reason} for a row not to place (e.g. one of two alternatives the printer doesn't use).
  - `own_plate`: [manifest path]: a part that gets a plate of its own (e.g. one plate per clip size).
  - `slots`: {manifest path: slot}: a part printed in another filament than its plate's material, e.g. "accent"
    (an accent colour) or "clear". `slot_filaments`: {slot: filament preset, or null for the material's own}.
    A plate uses its material's filament, then each other slot its parts use, in `slot_filaments` order;
    `max_filaments` (default 1) caps the filaments per plate, e.g. 4 for a 4-lane MMU, and a plate that would need
    more is an error. More than one filament on a plate also needs a machine preset with `change_filament_gcode`.
    The project's filament list is every plate's filaments, each (preset, material, slot) once.
  - `spdx`: {manifest licence name: SPDX id}, for --reuse (a name not in it is taken as an SPDX id).
  - `fill` (default 0.6): the share of the bed the parts' footprints (XY bounding boxes plus `gap_mm`) may cover
    on one plate; a material's parts that need more spill onto more plates, copies split as needed. This
    deterministic split decides each copy's plate, so --check can follow it without Orca.
Relative paths in the sets file are relative to the sets file's folder.

OrcaSlicer's own CLI builds each project from an assemble list (--load-assemble-list): one entry per plate, each
part with its copies and its filament number, arranged on that plate by Orca (need_arrange), every part as its
STL stands (the committed STLs are print-oriented). The 3MF carries the machine, process and filament presets.

The index, `<out>/index.json`, records each project's filaments, the sha256 of the presets it uses, its licences
(the manifest's `license` column, for the printer's REUSE annotations) and its plates: each plate's material,
filaments and STLs with their sha256, copies and filament. --check compares it with the manifest, the sets file,
the STLs on disk and the presets, and fails ("orca-projects: FAILED", exit 1) when:
  - an STL's sha256 differs from the one its project recorded, or its qty, plate, filament or unit changed;
  - a manifest row (path, qty > 0) has no project, or no entry in `parts`;
  - the index lists a part, or a project, that the manifest and sets no longer give;
  - a preset changed, or a project's .3mf is missing;
  - with --reuse REUSE.toml: a project's .3mf has no REUSE label of its own (only the catch-all default), or its
    label's SPDX ids miss a licence of its parts (the manifest's `license` names, mapped by the sets file's `spdx`:
    {manifest name: SPDX id}). Moving a part or renaming a project can do either.
It names the projects to regenerate. Otherwise the last line is "orca-projects: OK".

Plain regeneration rewrites only the stale projects (Orca 2.5.1's output is byte-identical on a rerun, so this
saves time, not diffs), and deletes the .3mf of a project that no longer exists. Orca is the flatpak
(com.orcaslicer.OrcaSlicer) or ORCA_SLICER, as in slice-check.py; the flatpak can't see /tmp, so the output folder
must be under $HOME. Stdlib only.
"""
import argparse
import csv
import hashlib
import importlib.util
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import tomllib
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
INDEX = "index.json"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def stl_bbox(path):
    """((min x, y, z), (max x, y, z)) of an STL, binary or ASCII; ((0, 0, 0), (0, 0, 0)) when it has no vertices"""
    data = open(path, "rb").read()
    n = struct.unpack_from("<I", data, 80)[0] if len(data) >= 84 else -1
    pts = []
    if n >= 0 and len(data) == 84 + 50 * n:
        for i in range(n):
            v = struct.unpack_from("<9f", data, 84 + 50 * i + 12)
            pts += [v[0:3], v[3:6], v[6:9]]
    else:
        pts = [tuple(float(c) for c in m.groups())
               for m in re.finditer(rb"vertex\s+(\S+)\s+(\S+)\s+(\S+)", data)]
    if not pts: return (0.0, 0.0, 0.0), (0.0, 0.0, 0.0)
    return tuple(min(p[i] for p in pts) for i in range(3)), tuple(max(p[i] for p in pts) for i in range(3))


def write_centred(src, dst):
    """a binary copy of an STL moved so its bounding box is centred on X 0, Y 0 and sits on Z 0, the same shape and
    file name: Orca's assemble list keeps an STL's own (CAD) coordinates, so it gets these copies instead"""
    lo, hi = stl_bbox(src)
    off = (-(lo[0] + hi[0]) / 2, -(lo[1] + hi[1]) / 2, -lo[2])
    data = open(src, "rb").read()
    n = struct.unpack_from("<I", data, 80)[0] if len(data) >= 84 else -1
    if n >= 0 and len(data) == 84 + 50 * n:
        tris = [struct.unpack_from("<12f", data, 84 + 50 * i) for i in range(n)]
        tris = [t[3:] for t in tris]
    else:
        v = [tuple(float(c) for c in m.groups()) for m in re.finditer(rb"vertex\s+(\S+)\s+(\S+)\s+(\S+)", data)]
        tris = [v[i] + v[i + 1] + v[i + 2] for i in range(0, len(v) - 2, 3)]
    out = bytearray(b"centred copy for orca_projects.py".ljust(80, b" ")) + struct.pack("<I", len(tris))
    for t in tris:
        moved = [t[i] + off[i % 3] for i in range(9)]
        out += struct.pack("<3f", 0, 0, 0) + struct.pack("<9f", *moved) + b"\0\0"
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(dst, "wb") as f: f.write(out)


def footprint(path):
    """(x, y) size of an STL's bounding box"""
    lo, hi = stl_bbox(path)
    return hi[0] - lo[0], hi[1] - lo[1]


def load_sets(path):
    """the sets file, with its paths made absolute (relative to the file's folder)"""
    path = os.path.abspath(path)
    cfg = json.load(open(path))
    base = os.path.dirname(path)
    for k in ("manifest", "stl_root", "orca", "out"):
        if k not in cfg: raise ValueError(f"{path}: needs `{k}`")
        cfg[k] = os.path.normpath(os.path.join(base, cfg[k]))
    for k in ("materials", "units", "parts", "bed_mm"):
        if k not in cfg: raise ValueError(f"{path}: needs `{k}`")
    for k, v in (("qty", {}), ("skip", {}), ("slots", {}), ("slot_filaments", {}), ("own_plate", []),
                 ("max_filaments", 1), ("fill", 0.6), ("gap_mm", 6), ("spdx", {})):
        cfg.setdefault(k, v)
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


def split_plates(parts, cfg, size_fn):
    """[[(part, copies)]]: the parts' copies in order, a new plate when the footprints pass `fill` of the bed"""
    cap = cfg["fill"] * cfg["bed_mm"][0] * cfg["bed_mm"][1]; g = cfg["gap_mm"]
    plates, cur, used = [], [], 0.0
    for p in parts:
        w, d = size_fn(p)
        a = (w + g) * (d + g)
        for _ in range(p["qty"]):
            if cur and used + a > cap:
                plates.append(cur); cur, used = [], 0.0
            if cur and cur[-1][0] is p: cur[-1] = (p, cur[-1][1] + 1)
            else: cur.append((p, 1))
            used += a
    if cur: plates.append(cur)
    return plates


def plan(rows, cfg, hash_fn=sha256, size_fn=None):
    """({unit: {unit, label, filaments: [{preset, label}], plates: [{material, label, filaments: [n],
    parts: [{path, qty, sha256, filament, license}]}]}}, [errors])"""
    size_fn = size_fn or (lambda p: footprint(os.path.join(cfg["stl_root"], p["path"])))
    errors, byunit = [], {}
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
        if p in cfg["skip"]: continue                            # not placed, on purpose (the reason is in the file)
        unit = cfg["parts"].get(p)
        if unit is None:
            errors.append(f"{p}: no work unit (add it to the sets file's `parts`)"); continue
        if unit not in cfg["units"]:
            errors.append(f"{p}: unknown work unit {unit!r}"); continue
        mat = material_of(r.get("material"), cfg["materials"])
        if mat is None:
            errors.append(f"{p}: material {r.get('material')!r} matches no `materials` entry"); continue
        stl = os.path.join(cfg["stl_root"], p)
        if not os.path.isfile(stl):
            errors.append(f"{p}: STL missing ({stl})"); continue
        byunit.setdefault(unit, []).append(dict(path=p, qty=n, sha256=hash_fn(stl), material=mat,
                                                license=(r.get("license") or "").strip(),
                                                slot=cfg["slots"].get(p, "main")))
    paths = {(r.get("path") or "").strip() for r in rows}
    for k in ("parts", "skip", "slots", "qty"):
        for p in cfg[k]:
            if p not in paths: errors.append(f"{p}: in the sets file's `{k}` but not in the manifest")
    for p in cfg["own_plate"]:
        if p not in paths: errors.append(f"{p}: in the sets file's `own_plate` but not in the manifest")
    projects = {}
    for unit in sorted(byunit):
        pr = projects[unit] = dict(unit=unit, label=cfg["units"][unit], filaments=[], plates=[])
        for mat in cfg["materials"]:
            mine = [p for p in byunit[unit] if p["material"] is mat]
            shared = [p for p in mine if p["path"] not in cfg["own_plate"]]
            groups = (split_plates(shared, cfg, size_fn) if shared else []) + \
                     [[(p, p["qty"])] for p in mine if p["path"] in cfg["own_plate"]]
            for grp in groups:
                errors += add_plate(pr, mat, grp, cfg)
    return projects, errors


def add_plate(pr, mat, grp, cfg):
    """one plate of material `mat` with [(part, copies)]: its filaments (the material's, then each other slot its
    parts use, in `slot_filaments` order), numbered in the project's filament list"""
    used = {p["slot"] for p, _ in grp}
    order = ["main"] + [k for k in cfg["slot_filaments"] if k in used and k != "main"]
    nums = {}
    for k in order:
        f = dict(preset=mat["filament"], label=mat["label"]) if k == "main" else \
            dict(preset=cfg["slot_filaments"][k] or mat["filament"],
                 label=f"{mat['label']}, {k}" if cfg["slot_filaments"][k] is None else k)
        if f not in pr["filaments"]: pr["filaments"].append(f)
        nums[k] = pr["filaments"].index(f) + 1
    pr["plates"].append(dict(material=mat["id"], label=mat["label"], filaments=[nums[k] for k in order],
                             parts=[dict(path=p["path"], qty=c, sha256=p["sha256"], filament=nums[p["slot"]],
                                         license=p["license"]) for p, c in grp]))
    n = len(pr["plates"])
    if len(order) > cfg["max_filaments"]:
        return [f"{pr['unit']} plate {n}: needs {len(order)} filaments ({', '.join(order)}), "
                f"the machine takes {cfg['max_filaments']}"]
    return []


def preset_shas(cfg, presets):
    """sha256 of the machine, process and filament presets a project uses"""
    orca = json.load(open(cfg["orca"])); d = os.path.dirname(cfg["orca"])
    out = {"machine": sha256(os.path.join(d, orca["machine"])), "process": sha256(os.path.join(d, orca["process"]))}
    for f in presets:
        out["filament: " + f] = sha256(os.path.join(d, f))
    return out


def machine_changes_filament(cfg):
    """True when the machine preset has a filament-change G-code (an MMU), so a plate can use several filaments"""
    orca = json.load(open(cfg["orca"]))
    m = json.load(open(os.path.join(os.path.dirname(cfg["orca"]), orca["machine"])))
    return bool((m.get("change_filament_gcode") or "").strip())


def index_entry(name, pr, presets, orca_plates):
    plates = [dict(material=pl["material"], label=pl["label"], filaments=pl["filaments"],
                   parts=[dict(path=p["path"], qty=p["qty"], sha256=p["sha256"], filament=p["filament"])
                          for p in pl["parts"]]) for pl in pr["plates"]]
    return dict(file=name + ".3mf", unit=pr["unit"], label=pr["label"], filaments=pr["filaments"], presets=presets,
                plates=plates, orca_plates=orca_plates,
                copies=sum(p["qty"] for pl in pr["plates"] for p in pl["parts"]),
                licenses=sorted({p.get("license") or "?" for pl in pr["plates"] for p in pl["parts"]}))


def _placed(plates):
    """{path: [(plate number, copies, sha256, filament)]}"""
    out = {}
    for i, pl in enumerate(plates, 1):
        for p in pl["parts"]:
            out.setdefault(p["path"], []).append((i, p["qty"], p["sha256"], p.get("filament")))
    return out


def stale(projects, index, presets_for, out_dir=None):
    """{project: [reasons]} for every project that must be regenerated (or deleted)"""
    have_all = index.get("projects", {})
    why = {}
    for name, pr in projects.items():
        got = have_all.get(name)
        if got is None:
            why.setdefault(name, []).append("no project yet"); continue
        want, have = _placed(pr["plates"]), _placed(got.get("plates", []))
        for p in sorted(want):
            w, h = want[p], have.get(p)
            if h is None: why.setdefault(name, []).append(f"{p}: not in the project")
            elif {x[2] for x in h} != {x[2] for x in w}: why.setdefault(name, []).append(f"{p}: STL changed (sha256)")
            elif sum(x[1] for x in h) != sum(x[1] for x in w):
                why.setdefault(name, []).append(f"{p}: qty {sum(x[1] for x in h)} -> {sum(x[1] for x in w)}")
            elif [x[3] for x in h] != [x[3] for x in w]:
                why.setdefault(name, []).append(f"{p}: filament {[x[3] for x in h]} -> {[x[3] for x in w]}")
            elif [(x[0], x[1]) for x in h] != [(x[0], x[1]) for x in w]:
                why.setdefault(name, []).append(f"{p}: plates {[x[0] for x in h]} -> {[x[0] for x in w]}")
        for p in sorted(set(have) - set(want)):
            why.setdefault(name, []).append(f"{p}: in the project but no longer in this work unit")
        if [(pl["material"], pl["filaments"]) for pl in got.get("plates", [])] != \
                [(pl["material"], pl["filaments"]) for pl in pr["plates"]] and name not in why:
            why.setdefault(name, []).append("plates changed")
        pz = presets_for(pr)
        for k in sorted(set(pz) | set(got.get("presets", {}))):
            if got.get("presets", {}).get(k) != pz.get(k): why.setdefault(name, []).append(f"{k} preset changed")
        if got.get("filaments") != pr["filaments"]: why.setdefault(name, []).append("filaments changed")
        if out_dir and not os.path.isfile(os.path.join(out_dir, got.get("file", name + ".3mf"))):
            why.setdefault(name, []).append(".3mf missing")
    for name in sorted(set(have_all) - set(projects)):
        why.setdefault(name, []).append("work unit no longer exists: delete the project")
    return why


def _glob(pattern):
    """REUSE.toml globbing: ** crosses folders, * doesn't (as platform/library/check_library.py)"""
    rx = "".join(".*" if tok == "**" else "[^/]*" if tok == "*" else re.escape(tok)
                 for tok in re.split(r"(\*\*|\*)", pattern))
    return re.compile(rx + r"\Z")


def reuse_label(reuse_path, rel):
    """the REUSE.toml label of a repo-relative path: (SPDX expression, the matching annotation's paths), from the
    last matching annotation, or (None, None)"""
    with open(reuse_path, "rb") as f:
        data = tomllib.load(f)
    got = (None, None)
    for a in data.get("annotations", []):
        paths = a["path"] if isinstance(a["path"], list) else [a["path"]]
        if any(_glob(x).match(rel) for x in paths):
            got = (a.get("SPDX-License-Identifier"), paths)
    return got


def spdx_ids(expr):
    """the licence ids in an SPDX expression ("A AND (B OR C)" -> {A, B, C})"""
    return {t for t in re.split(r"[\s()]+", expr or "") if t and t not in ("AND", "OR", "WITH")}


def check_reuse(projects, cfg, reuse_path):
    """[problems]: each project's .3mf needs its own REUSE label (not the catch-all `**` default) naming every
    licence of the parts in it; the manifest's licence names map to SPDX ids through the sets file's `spdx`"""
    root = os.path.dirname(os.path.abspath(reuse_path)); probs = []
    for name, pr in projects.items():
        rel = os.path.relpath(os.path.join(cfg["out"], name + ".3mf"), root).replace(os.sep, "/")
        expr, paths = reuse_label(reuse_path, rel)
        if expr is None or all(x.strip("*/") == "" for x in paths):
            probs.append(f"{name}: {rel} has no REUSE label of its own (only the repo default): add an annotation "
                         f"naming its licences"); continue
        need = {cfg["spdx"].get(p["license"], p["license"]) for pl in pr["plates"] for p in pl["parts"] if p["license"]}
        miss = sorted(need - spdx_ids(expr))
        if miss:
            probs.append(f"{name}: REUSE label {expr!r} for {rel} lacks {', '.join(miss)} (licences of its parts)")
    return probs


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


PLATE_GAP = 0.2        # Orca's LOGICAL_PART_PLATE_GAP: plates sit on a grid, a fifth of a bed apart


def plate_centre(k, count, bed):
    """the centre of plate k (0-based) of `count` in Orca's plate grid: ceil(sqrt(count)) columns, rows going -Y"""
    cols = 1
    while cols * cols < count: cols += 1
    row, col = divmod(k, cols)
    return col * bed[0] * (1 + PLATE_GAP) + bed[0] / 2, -row * bed[1] * (1 + PLATE_GAP) + bed[1] / 2


def assemble_list(pr, cfg, stl_dir=None):
    """Orca's --load-assemble-list JSON for a project (Orca's src/libslic3r/Format/AssembleList.cpp): one entry per
    plate (plate_name and need_arrange are required), each part with its copies, its filament number and a start
    position at the centre of its own plate. Orca keeps an STL's own coordinates and files each object under the
    plate its start position lies on, before arranging, so the parts are given as centred copies (`stl_dir`,
    write_centred) placed on their plate's centre. No assemble_index: objects sharing one are merged into one."""
    plates = []
    for k, pl in enumerate(pr["plates"]):
        cx, cy = plate_centre(k, len(pr["plates"]), cfg["bed_mm"])
        objs = [{"path": os.path.join(stl_dir or cfg["stl_root"], p["path"]), "count": p["qty"],
                 "filaments": [p["filament"]], "pos_x": [round(cx, 4)] * p["qty"], "pos_y": [round(cy, 4)] * p["qty"],
                 "pos_z": [0.0] * p["qty"]} for p in pl["parts"]]
        name = pl["label"] if len(pl["parts"]) > 1 else f"{pl['label']}: {os.path.basename(pl['parts'][0]['path'])}"
        plates.append({"plate_name": name, "need_arrange": True, "objects": objs})
    return {"plates": plates}


def plate_members(path3mf):
    """[number of objects on each plate] of an Orca 3MF"""
    with zipfile.ZipFile(path3mf) as z:
        t = z.read("Metadata/model_settings.config").decode("utf-8", "replace")
    return [len(re.findall(r'key="object_id"', pl)) for pl in re.findall(r"<plate>(.*?)</plate>", t, re.S)]


def generate(name, pr, cfg, dd, presets, sc, work):
    """one project: Orca loads the assemble list (plates, copies, filaments), arranges each plate and exports the
    3MF. Returns its plate count. --load-assemble-list takes no transform options (--orient, --arrange): the STLs
    stand as committed, and need_arrange arranges each plate."""
    od = os.path.join(work, name); shutil.rmtree(od, ignore_errors=True); os.makedirs(od)
    al = os.path.join(work, name + ".assemble.json")
    stl_dir = os.path.join(work, name + ".stl")
    for pl in pr["plates"]:
        for p in pl["parts"]:
            write_centred(os.path.join(cfg["stl_root"], p["path"]), os.path.join(stl_dir, p["path"]))
    with open(al, "w") as f: json.dump(assemble_list(pr, cfg, stl_dir), f, indent=1)
    cmd = sc.ORCA_SLICER + ["--datadir", dd, "--load-settings", f"{presets['machine']};{presets['process']}",
                            "--load-filaments", ";".join(presets[f["preset"]] for f in pr["filaments"]),
                            "--allow-multicolor-oneplate", "--allow-mix-temp", "--load-assemble-list", al,
                            "--outputdir", od, "--export-3mf", name + ".3mf"]
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
    g.add_argument("--list", action="store_true", help="print the projects and plates; no Orca")
    g.add_argument("--all", action="store_true", help="regenerate every project")
    g.add_argument("--only", help="regenerate these projects (comma-separated)")
    ap.add_argument("--reuse", help="with --check: a REUSE.toml whose label for each project names its licences")
    a = ap.parse_args(argv)
    if a.reuse and not a.check: ap.error("--reuse goes with --check")
    cfg = load_sets(a.sets)
    projects, errors = plan(load_manifest(cfg["manifest"]), cfg)
    index = load_index(cfg["out"])
    if any(len(pl["filaments"]) > 1 for pr in projects.values() for pl in pr["plates"]) \
            and not machine_changes_filament(cfg):
        errors.append("a plate uses several filaments, but the machine preset has no change_filament_gcode (not an MMU)")
    def presets_for(pr):
        return preset_shas(cfg, sorted({f["preset"] for f in pr["filaments"]}))
    why = stale(projects, index, presets_for, cfg["out"])
    copies = lambda pr: sum(p["qty"] for pl in pr["plates"] for p in pl["parts"])

    if a.list:
        for name, pr in projects.items():
            print(f"{name}: {pr['label']}: {copies(pr)} copies on {len(pr['plates'])} plate(s)")
            for i, f in enumerate(pr["filaments"], 1): print(f"  filament {i}: {f['label']} ({f['preset']})")
            for i, pl in enumerate(pr["plates"], 1):
                print(f"  plate {i}: {pl['label']}, filaments {pl['filaments']}")
                for p in pl["parts"]: print(f"    {p['qty']} x {p['path']}  [filament {p['filament']}]")
        for e in errors: print(f"ERROR {e}")
        return 1 if errors else 0

    if a.check:
        if a.reuse: errors += [f"REUSE {x}" for x in check_reuse(projects, cfg, a.reuse)]
        for e in errors: print(f"ERROR {e}")
        for name, rs in sorted(why.items()):
            print(f"STALE {name}: " + "; ".join(rs))
        if errors or why:
            todo = ",".join(sorted(why)) or "-"
            print(f"regenerate: python3 {os.path.relpath(__file__)} {os.path.relpath(cfg['_path'])}"
                  + (f" --only {todo}" if why else ""))
            print(f"orca-projects: FAILED: {len(errors)} error(s), stale: {todo}")
            return 1
        print(f"{len(projects)} projects, {sum(len(pr['plates']) for pr in projects.values())} plates, "
              f"{sum(copies(pr) for pr in projects.values())} copies: all current")
        print("orca-projects: OK"); return 0

    if errors:
        for e in errors: print(f"ERROR {e}")
        print("orca-projects: FAILED: fix the sets file or manifest first"); return 1
    if a.all: todo = list(projects)
    elif a.only:
        todo = [n.strip() for n in a.only.split(",") if n.strip()]
        bad = [n for n in todo if n not in projects]
        if bad: print(f"orca-projects: FAILED: no such project(s): {bad}"); return 1
    else: todo = [n for n in why if n in projects]
    gone = [n for n in why if n not in projects]
    os.makedirs(cfg["out"], exist_ok=True)
    for n in gone:
        f = os.path.join(cfg["out"], index["projects"][n].get("file", n + ".3mf"))
        if os.path.isfile(f): os.remove(f)
        del index["projects"][n]; print(f"removed {n}")
    fails = []
    if todo:
        sc = _slice_check()
        work = os.path.join(cfg["out"], ".work"); shutil.rmtree(work, ignore_errors=True); os.makedirs(work)
        dd = os.path.join(work, "datadir")
        presets = orca_datadir(dd, cfg, sorted({f["preset"] for pr in projects.values() for f in pr["filaments"]}),
                               sc.orca_profiles_dir())
        index["orca"] = orca_version(sc)
        for n in todo:
            pr = projects[n]
            got = generate(n, pr, cfg, dd, presets, sc, work)
            want = [sum(p["qty"] for p in pl["parts"]) for pl in pr["plates"]]
            have = plate_members(os.path.join(cfg["out"], n + ".3mf"))
            if have != want:                # every copy must be on its own plate, and only there
                fails.append(f"{n}: objects per plate {have}, the plan has {want}")
            index["projects"][n] = index_entry(n, pr, presets_for(pr), got)
            print(f"{n}: {copies(pr)} copies on {got} plate(s), "
                  f"{os.path.getsize(os.path.join(cfg['out'], n + '.3mf')) / 1e6:.1f} MB")
        if not fails: shutil.rmtree(work, ignore_errors=True)
    index["_doc"] = (f"Generated by platform/parts/orca_projects.py from {os.path.basename(cfg['_path'])} (vt350#217): "
                     "each project's filaments, presets' sha256, and plates with their STLs (sha256, copies, "
                     "filament). Don't edit by hand; --check compares it with the manifest and the STLs.")
    write_index(cfg["out"], index)
    if fails:
        print("orca-projects: FAILED: " + " | ".join(fails)); return 1
    if not todo and not gone: print("nothing stale")
    print("orca-projects: OK"); return 0


if __name__ == "__main__":
    sys.exit(main())
